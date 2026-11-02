from __future__ import annotations

import asyncio
import hashlib
import re
import unicodedata
from abc import ABC
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, replace
from datetime import datetime
from decimal import Decimal
from http import HTTPStatus
from typing import Final, cast

import httpx
from bs4 import Tag
from loguru import logger
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from ...domain.entities import Listing
from ...domain.ports import CrawlerPort
from ...domain.value_objects import DpeRating, Floor, PublicationSource
from ..cache.ttl_cache import DETAIL_CACHE
from .robots import RobotsDisallowedError, RobotsRules

# One honest identity on every request: no browser imitation (TLS fingerprint, client
# hints), no user-agent rotation. A site that refuses it is removed, never worked
# around — docs/technical/crawlers.md, held by tests/infrastructure/test_no_evasion.py.
CRAWLER_USER_AGENT: Final = "apartment-hunter/0.1 (personal home search)"
_ACCEPT_LANGUAGE: Final = "fr-FR,fr;q=0.9"
# Enough of a card to see what the parser choked on, short enough for one log line.
_PARSE_ERROR_PREVIEW_CHARS: Final = 500
_PAGE_TIMEOUT_SECONDS: Final = 15
_PAGE_ATTEMPTS: Final = 3
_FIRST_BACKOFF_SECONDS: Final = 2.0  # doubled after each transient failure


def build_listing_id(url: str) -> str:
    return hashlib.sha256(url.encode()).hexdigest()[:16]


@dataclass(frozen=True)
class ListingDetails:
    """What a listing's detail page adds to what its search-result card already gave.

    All five are optional because sites differ: Orpi's detail page carries the
    energy scales *and* a creation date, Century 21's only the scales, Laforêt's
    only the storey buried in its description. The furnishing answer lives in a
    criteria table the cards never print, so it is read here for every source.
    """

    dpe_rating: DpeRating | None = None
    ges_rating: DpeRating | None = None
    published_at: datetime | None = None
    floor: Floor | None = None
    furnished: bool | None = None


def is_in_department(listing: Listing, department: str) -> bool:
    """True when the listing's postal code stays in the searched department.

    Several sites answer an unknown or empty town query with national filler — Citya
    pads a town page with cross-city carousels, Foncia falls back to its whole stock —
    which would otherwise reach the database labelled with the searched town. A listing
    with no postal code is kept: the radius check in ListingMatcher is the next line
    of defence.
    """
    postal = listing.location.postal_code
    return not postal or postal.startswith(department)


def with_site_date(listing: Listing, published_at: datetime | None) -> Listing:
    """The listing stamped with the site's own publication date.

    Returns it untouched when the site printed no date, so `published_at` keeps its
    first-seen fallback and `published_at_source` keeps saying so.
    """
    if published_at is None:
        return listing
    return replace(listing, published_at=published_at, published_at_source=PublicationSource.SITE)


def merge_details(listing: Listing, details: ListingDetails) -> Listing:
    """The listing with everything its detail page added folded in.

    The detail page wins over the card on every field: the card carries a headline,
    the page carries the criteria table. A field the page didn't state keeps the card's
    value — an unreadable page must never blank what was already known.

    Lives here, not in `_enrich_details`, so a crawler that drives its own
    enrichment loop folds the same fields the same way.
    """
    return with_site_date(
        replace(
            listing,
            dpe_rating=details.dpe_rating or listing.dpe_rating,
            ges_rating=details.ges_rating or listing.ges_rating,
            floor=details.floor or listing.floor,
            furnished=details.furnished if details.furnished is not None else listing.furnished,
        ),
        details.published_at,
    )


def build_city_slug(city: str, separator: str = "-") -> str:
    """'Saint-Jorioz' → 'saint-jorioz' — accent-stripped, lowercased URL slug.

    Sites differ only in the joining character (Century 21 canonicalises spaces to
    '+'), so the separator is a parameter rather than a copy of the function.
    """
    nfd = unicodedata.normalize("NFD", city)
    ascii_city = "".join(c for c in nfd if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]+", separator, ascii_city.lower()).strip(separator)


# "Gaillard (74)", "Sevrier (74320)": a commune, then its department or postal code.
_COMMUNE_LABEL_RE = re.compile(r"^(.+?)\s*\((\d{5}|\d{2,3}|2[AB])\)")


class MissingCommuneError(ValueError):
    """A card naming no commune of its own. It is dropped, never filed under the
    commune that was searched: ParuVendu answers a commune URL with its whole
    department, Foncia pads a small commune with its neighbours."""


def parse_commune_label(text: str) -> tuple[str, str] | None:
    """'Gaillard (74)' → ('Gaillard', '74'); the code is a department or a postal code."""
    if m := _COMMUNE_LABEL_RE.match(text.strip()):
        return m.group(1), m.group(2)
    return None


def build_page_headers(base_url: str) -> dict[str, str]:
    """The HTML-page headers every SSR crawler sends, pointing at the site's own home."""
    return {
        "User-Agent": CRAWLER_USER_AGENT,
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": _ACCEPT_LANGUAGE,
        "Referer": f"{base_url}/",
    }


def build_absolute_url(base_url: str, href: str) -> str:
    """Site-absolute href resolved against the crawler's base URL."""
    return f"{base_url}{href}" if href.startswith("/") else href


_PER_SQUARE_METRE_RE = re.compile(r"/\s*m\s*[²2]", re.I)
_SURFACE_RE = re.compile(r"(\d+[.,]?\d*)\s*m\s*[²2]", re.I)
_ROOMS_RE = re.compile(r"(\d+)\s*(?:pcs|pièce)", re.I)
_GROUND_FLOOR_RE = re.compile(r"\bRDC\b|rez[- ]de[- ]chauss", re.I)
_TOP_FLOOR_RE = re.compile(r"dernier\s+[ée]tage", re.I)
# Structured label of a tag list: "Étage 3", "Etage : 2", "Étage 3/5".
_LABELLED_FLOOR_RE = re.compile(r"[ée]tage(?!s)\s*:?\s*(\d+)\s*(?:/\s*(\d+))?", re.I)
# Prose of a description: "au 4e étage sur 5". The ordinal is whatever the advertiser
# typed — "4e", "4ème", and on Laforêt a mojibake "4?" — so any short token passes,
# while `(?!s)` keeps "immeuble de 5 étages" from being read as a storey.
_ORDINAL_FLOOR_RE = re.compile(
    r"(\d+)\s*(?:[a-zè]{0,3}|\?)\s*[ée]tage(?!s)(?:\s*(?:sur|/)\s*(\d+))?", re.I
)


def parse_surface_m2(text: str) -> float | None:
    """Living area from a card's text ("60,3 m²", "60.3 m 2" once <sup> collapses)."""
    m = _SURFACE_RE.search(text)
    return float(m.group(1).replace(",", ".")) if m else None


def parse_rooms(text: str) -> int | None:
    """Room count from a card's text ("3 pièces", Century 21's "3 pcs")."""
    m = _ROOMS_RE.search(text)
    return int(m.group(1)) if m else None


def parse_floor(text: str) -> Floor | None:
    """The storey a listing sits on, in whichever wording the site used.

    Returns None when the text says nothing about it: an unknown floor must stay
    unknown, because `ListingMatcher` reads it as a pass, not as a rejection —
    inventing a storey here would silently drop listings.

    Ground floor wins over a storey number: a description mentioning both ("…au 2ème,
    commerce en rez-de-chaussée") is ambiguous, and excluding is the safe reading for
    someone who asked not to live on the street.

    O(len(text)) — four linear scans, run once per listing.
    """
    if _GROUND_FLOOR_RE.search(text):
        return Floor.ground()
    m = _LABELLED_FLOOR_RE.search(text) or _ORDINAL_FLOOR_RE.search(text)
    if not m:
        return None
    total = int(m.group(2)) if m.group(2) else None
    level = int(m.group(1))
    return Floor.from_int(level, is_top=level == total or bool(_TOP_FLOOR_RE.search(text)))


def read_tag_attr(tag: Tag, name: str) -> str:
    """A single-valued element attribute as a plain ``str``.

    bs4 types ``Tag.get`` as ``str | list | None`` because some HTML attributes
    (class, rel) are multi-valued. For single-valued ones (href, alt) this narrows
    to the string, returning "" when the attribute is absent or unexpectedly a list.
    """
    value = tag.get(name)
    return value if isinstance(value, str) else ""


def read_tag_classes(tag: Tag) -> list[str]:
    """The element's CSS classes as a list of strings (empty when none)."""
    return tag.get_attribute_list("class")


def parse_price_from_euro_node(card: Tag) -> Decimal:
    """Parse the rent amount from the first €-bearing node in a card.

    Reading the node that actually holds "€" isolates the price from unrelated
    digits elsewhere in the card (photo counts, department codes) that a whole-card
    regex would wrongly absorb. Skips "€/m²" unit-price nodes — but not "€ /mois",
    which a bare "/m" test used to throw away along with them.
    """
    for node in card.find_all(string=re.compile("€")):
        parent = node.parent
        if parent is None:
            continue
        text = parent.get_text(" ", strip=True)
        if _PER_SQUARE_METRE_RE.search(text):
            continue
        m = re.search(r"([\d\s\xa0]+)\s*€", text)
        if not m:
            continue
        digits = re.sub(r"[^\d]", "", m.group(1))
        if digits:
            return Decimal(digits)
    return Decimal(0)


# Worth a second try after a pause: timeouts and rate limits (408/429), server and edge
# errors (5xx, including CDN codes like 534 and Cloudflare's 520-524). A 401/403 is a
# refusal, not an accident: retrying it would be leaning on the door.
_TRANSIENT_STATUS: Final = frozenset({408, 429, 500, 502, 503, 504, 520, 521, 522, 523, 524, 534})


class BaseCrawler(CrawlerPort, ABC):
    RATE_LIMIT_SECONDS: float = 1.5
    BASE_URL: str = ""  # site root — used for headers and href resolution
    MAX_PAGES: int = 4  # pagination cap per search URL (anti-bot + crawl-time bound)
    # A site whose redirect means "not this page" (ParuVendu sends an empty commune to
    # the whole department) turns it off: the redirect then reads as no page at all.
    FOLLOW_REDIRECTS: bool = True

    def __init__(self, timeout: float = 30.0):
        self._client: httpx.AsyncClient | None = None
        self._timeout = timeout
        self._pace_lock = asyncio.Lock()
        self._next_slot_at: float = 0.0
        self._robots = RobotsRules(CRAWLER_USER_AGENT, self._read_robots)
        self._crawl_delay_seconds = 0.0  # what the site's robots.txt asks, if more

    def resolve_url(self, href: str) -> str:
        return build_absolute_url(self.BASE_URL, href)

    def compute_request_spacing_seconds(self) -> float:
        """Minimum delay between two requests this crawler starts.

        `RATE_LIMIT_SECONDS` is the courtesy budget per *window*, and a source is
        crawled `CITY_CONCURRENCY` communes at a time — so the aggregate rate is
        `CITY_CONCURRENCY` requests per `RATE_LIMIT_SECONDS`. Spacing serially at
        `RATE_LIMIT_SECONDS` instead would put 30 communes × 4 pages well past the
        180 s per-source cap and leave every run partial.
        """
        return self.RATE_LIMIT_SECONDS / max(1, self.CITY_CONCURRENCY)

    async def _await_turn(self) -> None:
        """Hold until this crawler is allowed to start another request.

        The lock is held across the sleep on purpose: each waiter books the next free
        slot, so N concurrent callers are spaced instead of all reading the same
        deadline and firing together — which is what the previous `_last_request`
        arithmetic did, unprotected, from four concurrent commune searches.
        """
        async with self._pace_lock:
            loop = asyncio.get_running_loop()
            if (wait := self._next_slot_at - loop.time()) > 0:
                await asyncio.sleep(wait)
            started = max(loop.time(), self._next_slot_at)
            spacing = max(self.compute_request_spacing_seconds(), self._crawl_delay_seconds)
            self._next_slot_at = started + spacing

    async def _is_allowed_by_robots(self, url: str) -> bool:
        """Whether the site's robots.txt lets this crawler fetch `url`; logs a refusal.

        Also adopts the site's `Crawl-delay` when it asks for more than our own pace.
        """
        self._crawl_delay_seconds = await self._robots.find_crawl_delay(url)
        if await self._robots.is_allowed(url):
            return True
        logger.warning(f"[{self.source_name}] robots.txt disallows {url}: skipped")
        return False

    async def _read_robots(self, robots_url: str) -> tuple[int, str] | None:
        from curl_cffi.requests import AsyncSession

        await self._await_turn()
        try:
            async with AsyncSession() as session:
                resp = await session.get(
                    robots_url,
                    headers=build_page_headers(self.BASE_URL),
                    timeout=_PAGE_TIMEOUT_SECONDS,
                    allow_redirects=True,
                )
        except Exception as exc:
            logger.warning(f"[{self.source_name}] robots.txt unreachable, nothing fetched: {exc}")
            return None
        return resp.status_code, resp.text

    async def _fetch_html(self, url: str) -> str | None:
        """The site's HTML for `url`, fetched with this crawler's page headers.

        Paced by `_await_turn`, like `_get_throttled`: every request of a crawler goes
        through the same gate.
        """
        if not await self._is_allowed_by_robots(url):
            return None
        await self._await_turn()
        return await self._fetch_page(url, build_page_headers(self.BASE_URL))

    async def _fetch_page(
        self,
        url: str,
        headers: dict[str, str],
        timeout: int = _PAGE_TIMEOUT_SECONDS,
        attempts: int = _PAGE_ATTEMPTS,
    ) -> str | None:
        """GET `url`, retrying transient codes (429, 5xx) with exponential backoff.

        A refusal (401/403) ends it at once. Returns the body on 200, else None after a
        clear log.
        """
        from curl_cffi.requests import AsyncSession

        backoff = _FIRST_BACKOFF_SECONDS
        for attempt in range(1, attempts + 1):
            try:
                async with AsyncSession() as session:
                    resp = await session.get(
                        url, headers=headers, timeout=timeout, allow_redirects=self.FOLLOW_REDIRECTS
                    )
                if resp.status_code == HTTPStatus.OK:
                    body: str = resp.text
                    return body
                if HTTPStatus.MULTIPLE_CHOICES <= resp.status_code < HTTPStatus.BAD_REQUEST:
                    logger.debug(
                        f"[{self.source_name}] {url} redirects to "
                        f"{resp.headers.get('location')}, not followed"
                    )
                    return None
                if resp.status_code in _TRANSIENT_STATUS and attempt < attempts:
                    logger.debug(
                        f"[{self.source_name}] HTTP {resp.status_code} "
                        f"(attempt {attempt}/{attempts}) — retry in {backoff:.0f}s: {url}"
                    )
                    await asyncio.sleep(backoff)
                    backoff *= 2
                    continue
                logger.warning(
                    f"[{self.source_name}] blocked — HTTP {resp.status_code} after "
                    f"{attempt} attempt(s): {url}"
                )
                return None
            except Exception as exc:
                if attempt < attempts:
                    await asyncio.sleep(backoff)
                    backoff *= 2
                    continue
                logger.warning(f"[{self.source_name}] GET failed after {attempts} attempts: {exc}")
                return None
        return None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=self._timeout,
                follow_redirects=True,
                headers={"User-Agent": CRAWLER_USER_AGENT, "Accept-Language": _ACCEPT_LANGUAGE},
            )
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def _get_throttled(self, url: str, **kwargs: object) -> httpx.Response:
        """GET through this crawler's session. Raises RobotsDisallowedError when the
        site's robots.txt refuses the URL, query included, and httpx errors otherwise."""
        params = cast(dict[str, object] | None, kwargs.get("params"))
        full_url = str(httpx.URL(url, params=params))
        if not await self._is_allowed_by_robots(full_url):
            raise RobotsDisallowedError(full_url)
        await self._await_turn()
        client = await self._get_client()

        @retry(
            stop=stop_after_attempt(3),
            wait=wait_exponential(multiplier=1, min=2, max=10),
            retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError)),
            reraise=True,
        )
        async def _do_get() -> httpx.Response:
            resp = await client.get(url, **kwargs)  # type: ignore[arg-type]
            resp.raise_for_status()
            return resp

        return await _do_get()

    def _log_parse_error(self, url: str, html_snippet: str, error: Exception) -> None:
        preview = html_snippet[:_PARSE_ERROR_PREVIEW_CHARS].replace("\n", " ")
        logger.warning(f"[{self.source_name}] Parse error at {url}: {error} — HTML: {preview}")

    CITY_CONCURRENCY = 4  # max parallel commune searches per source (anti-bot bound)
    ENERGY_CONCURRENCY = 5  # max parallel detail-page fetches per source (anti-bot bound)

    async def _gather_cities(
        self,
        cities: list[str],
        fetch_city: Callable[[str], Awaitable[list[Listing]]],
    ) -> list[Listing]:
        """Run per-commune searches concurrently (bounded) and return deduped listings.

        Replaces the sequential city loop. A failing commune logs and yields nothing.
        Detail-page enrichment is done once afterwards by the caller, so commune
        concurrency and enrichment concurrency never multiply.
        """
        sem = asyncio.Semaphore(self.CITY_CONCURRENCY)

        async def _fetch_one(city: str) -> list[Listing]:
            async with sem:
                try:
                    return await fetch_city(city)
                except Exception as exc:
                    logger.error(f"[{self.source_name}] Failed for {city!r}: {exc}")
                    return []

        batches = await asyncio.gather(*(_fetch_one(c) for c in cities))
        seen: set[str] = set()
        out: list[Listing] = []
        for batch in batches:
            for listing in batch:
                if listing.id not in seen:
                    seen.add(listing.id)
                    out.append(listing)
        return out

    async def _paginate(
        self,
        build_page_url: Callable[[int], str],
        parse_page: Callable[[str], list[Listing]],
        label: str,
        max_pages: int | None = None,
    ) -> list[Listing]:
        """Walk a site's result pages until they stop yielding unseen listings.

        Every SSR source paginates the same way: build page N's URL, parse its cards,
        stop on an unreadable page, an empty page, or a page that only repeats what we
        already hold (sites commonly serve page 1 again for an out-of-range `page`).
        Dedup is by listing id through a set — O(total cards) time, O(kept) space.
        """
        pages = max_pages or self.MAX_PAGES
        kept: list[Listing] = []
        seen_ids: set[str] = set()

        for page in range(1, pages + 1):
            html = await self._fetch_html(build_page_url(page))
            if not html:
                break

            fresh = [listing for listing in parse_page(html) if listing.id not in seen_ids]
            if not fresh:
                break

            seen_ids.update(listing.id for listing in fresh)
            kept.extend(fresh)
            logger.debug(f"[{self.source_name}] {label} p{page}: +{len(fresh)} (total={len(kept)})")

        return kept

    async def _enrich_details(
        self,
        apts: list[Listing],
        fetcher: Callable[[str], Awaitable[ListingDetails | None]],
    ) -> list[Listing]:
        """Fill DPE/GES, the storey, the furnishing answer and the date from each page.

        One request per listing serves both: sites that hide the energy scales on the
        detail page usually hide the "publié le" date there too. Fetches run
        concurrently under a bounded semaphore — the main speed lever. Cached URLs skip
        the network entirely. Listings whose page can't be read keep their card values
        (the matcher treats an unknown DPE as a pass, so they aren't silently dropped).
        """
        sem = asyncio.Semaphore(self.ENERGY_CONCURRENCY)

        async def _fetch_details_for(listing: Listing) -> ListingDetails:
            cached = DETAIL_CACHE.get(listing.url)
            if cached is not None:
                return cast("ListingDetails", cached)
            async with sem:
                try:
                    details = await fetcher(listing.url) or ListingDetails()
                except Exception as exc:
                    logger.debug(
                        f"[{self.source_name}] detail fetch failed for {listing.url}: {exc}"
                    )
                    details = ListingDetails()
            # Cache hits and misses alike — don't re-fetch an unreadable listing each run.
            DETAIL_CACHE.set(listing.url, details)
            return details

        all_details = await asyncio.gather(*(_fetch_details_for(a) for a in apts))
        enriched = [
            merge_details(listing, details)
            for listing, details in zip(apts, all_details, strict=True)
        ]
        rated = sum(1 for a in enriched if a.dpe_rating or a.ges_rating)
        dated = sum(1 for a in enriched if a.has_site_publication_date)
        furnishing = sum(1 for a in enriched if a.furnished is not None)
        logger.debug(
            f"[{self.source_name}] detail enriched — energy {rated}/{len(enriched)}, "
            f"date {dated}/{len(enriched)}, furnishing {furnishing}/{len(enriched)}"
        )
        return enriched
