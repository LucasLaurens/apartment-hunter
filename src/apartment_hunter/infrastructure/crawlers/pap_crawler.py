"""
PAP.fr — direct owner listings (no advertiser). Simple server-rendered HTML.
Geo IDs resolved via /json/ac-geo autocomplete endpoint (e.g. Annecy=37473).

Search cards carry price/surface/rooms/DPE but no date; the detail page prints
"Réf. : … / Publié le 3 août 2026" in `p.item-date`, so the publication date costs
one extra (concurrent, cached) fetch per listing.
"""

import re
from datetime import datetime
from decimal import Decimal

import httpx
from bs4 import BeautifulSoup, Tag
from loguru import logger

from ...domain.entities import Listing, SearchFilter
from ...domain.services import detect_furnished, detect_furnished_label
from ...domain.value_objects import DpeRating, Location, Price
from .base_crawler import (
    BaseCrawler,
    ListingDetails,
    MissingCommuneError,
    build_listing_id,
    parse_rooms,
    parse_surface_m2,
    read_tag_attr,
    read_tag_classes,
)
from .french_dates import parse_french_date
from .robots import RobotsDisallowedError

_BASE_URL = "https://www.pap.fr"
_GEO_AC_URL = "https://www.pap.fr/json/ac-geo"

_DATE_SELECTOR = "p.item-date"


class PapCrawler(BaseCrawler):
    source_name = "pap"
    RATE_LIMIT_SECONDS = 2.0
    BASE_URL = _BASE_URL
    covers_radius = True  # native `rayon` param → one search covers surrounding towns

    def __init__(self, timeout: float = 30.0):
        super().__init__(timeout)
        self._geo_cache: dict[str, int | None] = {}

    async def fetch(self, search_filter: SearchFilter) -> list[Listing]:
        results: list[Listing] = []
        for city in search_filter.cities:
            try:
                batch = await self._fetch_city(search_filter, city)
                results.extend(batch)
            except Exception as exc:
                logger.error(f"[pap] Failed fetching {city}: {exc}")
        if results:
            results = await self._enrich_details(results, self._fetch_details)
        return results

    async def _fetch_details(self, url: str) -> ListingDetails | None:
        """Publication date from the detail page's `p.item-date`
        ("Réf. : D43/0192 / Publié le 3 août 2026"), plus the furnishing answer from
        the criteria table. DPE already came from the card.

        Read through the search's own session: PAP refuses a detail page to a client
        that never opened its search (HTTP 403), and serves it to one that did.
        """
        try:
            resp = await self._get_throttled(url)
        except (httpx.HTTPError, RobotsDisallowedError) as exc:
            logger.debug(f"[pap] detail page refused or unreachable: {url} ({exc})")
            return None
        soup = BeautifulSoup(resp.text, "lxml")
        date_el = soup.select_one(_DATE_SELECTOR)
        return ListingDetails(
            published_at=(
                parse_french_date(date_el.get_text(" ", strip=True)) if date_el else None
            ),
            furnished=detect_furnished_label(soup.get_text(" ", strip=True)),
        )

    async def _fetch_city(self, f: SearchFilter, city: str) -> list[Listing]:
        geo_id = await self._resolve_geo_id(city)
        if geo_id is None:
            logger.warning(f"[pap] No geo ID found for {city!r}, skipping")
            return []

        params: dict[str, object] = {}
        if f.max_price:
            params["prix-max"] = f.max_price
        if f.min_price:
            params["prix-min"] = f.min_price
        if f.min_surface_m2:
            params["surface-min"] = int(f.min_surface_m2)
        if f.min_rooms:
            params["nb-pieces-min"] = f.min_rooms
        if f.max_rooms:
            params["nb-pieces-max"] = f.max_rooms
        if f.radius_km and f.radius_km > 0:
            params["rayon"] = int(f.radius_km)

        base_url = f"{_BASE_URL}/annonce/locations-appartement-g{geo_id}"
        all_apts: list[Listing] = []
        seen_urls: set[str] = set()

        for page in range(1, self.MAX_PAGES + 1):
            if page > 1:
                params["page"] = page

            resp = await self._get_throttled(base_url, params=params)
            soup = BeautifulSoup(resp.text, "lxml")
            items = soup.select(".search-list-item-alt")
            if not items:
                break

            page_apts = [listing for item in items if (listing := self._parse(item)) is not None]
            new_apts = [a for a in page_apts if a.url not in seen_urls]
            if not new_apts:
                break
            seen_urls.update(a.url for a in new_apts)
            all_apts.extend(new_apts)

            # Check if there's a next page
            has_next = bool(soup.select_one(".pagination a[rel='next'], .pagination a:last-child"))
            if not has_next and page > 1:
                break

        logger.info(f"[pap] {city}: {len(all_apts)} listings (geo_id={geo_id}, pages={page})")
        return all_apts

    async def _resolve_geo_id(self, city: str) -> int | None:
        """PAP's id for `city`, or None when PAP does not know it or did not answer.

        Only an answer is cached. The crawler lives as long as `hunt watch`, so a
        cached failure (a 403, a timeout) used to switch PAP off for the whole run.
        """
        key = city.lower()
        if key in self._geo_cache:
            return self._geo_cache[key]

        try:
            resp = await self._get_throttled(
                _GEO_AC_URL,
                params={"q": city},
                headers={
                    "Accept": "application/json",
                    "X-Requested-With": "XMLHttpRequest",
                    "Referer": f"{_BASE_URL}/annonce/locations-appartement",
                },
            )
            resp.raise_for_status()
            places = resp.json()
        except Exception as exc:
            logger.warning(f"[pap] Geo ID lookup failed for {city!r}, retried next run: {exc}")
            return None

        geo_id = int(places[0]["id"]) if isinstance(places, list) and places else None
        logger.debug(f"[pap] Resolved {city!r} → geo_id={geo_id}")
        self._geo_cache[key] = geo_id
        return geo_id

    def _parse(self, item: Tag) -> Listing | None:
        try:
            link = item.select_one(
                "a.item-title, a.item-thumb-link, a[href*='/annonces/appartement']"
            )
            if not link:
                return None

            href = read_tag_attr(link, "href")
            # Not a listing, or a room in a shared flat: skipped before any parsing to save
            # the work. The rule itself is `tenancy_scope`, which the matcher applies anyway.
            if "/annonces/" not in href or "/colocation" in href:
                return None

            url = self.resolve_url(href)

            # Price/tags may be inside or outside the anchor — search whole item
            price_el = item.select_one(".item-price")
            price_text = price_el.get_text(strip=True) if price_el else "0"
            # French thousands separator is a period: "1.500 €" → 1500
            price_digits = re.sub(r"[^\d]", "", price_text.replace("\xa0", ""))
            price_amount = Decimal(price_digits) if price_digits else Decimal(0)

            tags = [
                li.get_text(strip=True).replace("\xa0", " ")
                for li in item.select("ul.item-tags li")
            ]
            surface: float | None = None
            rooms: int | None = None
            for tag in tags:
                surface = parse_surface_m2(tag) or surface
                rooms = parse_rooms(tag) or rooms

            dpe_el = item.select_one("[class*='item-thumb-dpe-']")
            dpe: DpeRating | None = None
            if dpe_el:
                dpe_match = re.search(
                    r"item-thumb-dpe-([a-gA-G])", " ".join(read_tag_classes(dpe_el))
                )
                if dpe_match:
                    dpe = DpeRating.from_string(dpe_match.group(1))

            # City — PAP uses <span class="h1"> (class not tag)
            city_el = item.select_one(
                ".h1, .item-localisation, .item-location, .localisation, .location-label, "
                "[class*='localisation'], [class*='location'], [class*='ville'], "
                "[class*='city'], .h4"
            )
            city_raw = city_el.get_text(" ", strip=True) if city_el else ""
            if not city_raw:
                full = item.get_text(" ", strip=True)
                # Try with postal code first
                m = re.search(r"([A-ZÀ-Ÿ][a-zà-ÿ\-]+(?:\s+[A-ZÀ-Ÿa-zà-ÿ\-]+)*)\s*\((\d{5})\)", full)
                city_raw = f"{m.group(1)} ({m.group(2)})" if m else ""

            postal_m = re.search(r"\((\d{5})\)", city_raw)
            postal_code = postal_m.group(1) if postal_m else None
            city_clean = re.sub(r"\s*\(\d+\)\s*$", "", city_raw).strip()
            city_clean = re.sub(r"\s*à\s+\d+\s*km\s+de\s+.*$", "", city_clean, flags=re.I).strip()

            # Split "Quartier - Ville" or "Ville - Quartier" into parts
            neighborhood: str | None = None
            if " - " in city_clean:
                parts = [p.strip() for p in city_clean.split(" - ", 1)]
                city_name = parts[0]
                neighborhood = parts[1]
            else:
                city_name = city_clean

            if not city_name:
                raise MissingCommuneError
            return Listing(
                id=build_listing_id(url),
                url=url,
                title=f"Appartement {city_name}" + (f" – {int(surface)}m²" if surface else ""),
                source=self.source_name,
                location=Location(
                    city=city_name, postal_code=postal_code, full_address=neighborhood
                ),
                price=Price(amount=price_amount),
                surface_m2=surface,
                rooms=rooms,
                dpe_rating=dpe,
                furnished=detect_furnished(item.get_text(" ", strip=True)),
                published_at=datetime.now(),
            )
        except Exception as exc:
            self._log_parse_error("", str(item), exc)
            return None
