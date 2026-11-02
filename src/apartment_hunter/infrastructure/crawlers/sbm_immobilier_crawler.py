"""
SBM Immobilier — one local agency in Annecy, WordPress SSR (RealHomes theme).

curl_cffi, like every SSR crawler. Its legal notice forbids copying or storing any part
of the site without the agency's written consent, so the source runs only when the
hunter chose to ignore the sites' rules (`forbids_reproduction`, ADR-0012). robots.txt
allows everything.

The whole rental stock fits in one list, `/locations-immobilieres/`, 12 cards a page,
`/page/N/` after the first (4 pages on 2026-11-02, garages included). It is read once
(`covers_radius`) and `ListingMatcher` narrows it to the radius. Apartments are kept by
the type line under the title (« Appartement, T2 »); a garage reads « Stationnement ».

A card gives the rent (the total charges included: the detail page splits it into
« Loyer hors charges » and « Provision sur charges »), the type (« T2 », « Studio »),
« 74000 Annecy, France », the map pin's coordinates, surface, a photo and the date it
was added (« Ajout : 30 octobre 2026 »). The detail page adds DPE and GES (classes
`dpe-D`, `ges-D`) and, in its JSON-LD `RealEstateListing`, the storey and the charges.
"""

import json
import re
from datetime import datetime
from typing import Any, Final

from bs4 import BeautifulSoup, Tag
from loguru import logger

from ...domain.entities import Listing, SearchFilter
from ...domain.services import detect_furnished
from ...domain.value_objects import DpeRating, Location, Price, PublicationSource
from .base_crawler import (
    BaseCrawler,
    ListingDetails,
    MissingCommuneError,
    build_listing_id,
    parse_floor,
    parse_price_from_euro_node,
    parse_room_type,
    parse_surface_m2,
    read_tag_attr,
)
from .french_dates import parse_french_date

_BASE_URL: Final = "https://www.sbm-immo.com"
_LIST_URL: Final = f"{_BASE_URL}/locations-immobilieres/"
_CARD_SELECTOR: Final = "div.rh-ultra-property-card"
_NEXT_PAGE_SELECTOR: Final = "a.rh_pagination__next"
_FLAT_TYPE: Final = "Appartement"
_ADDRESS_RE: Final = re.compile(r"(\d{5})\s+(.+?),\s*France")
_ADVERTISER: Final = "SBM Immobilier"
_DPE_CLASS_RE: Final = re.compile(r"\bdetails-dpe dpe-([A-G])\b")
_GES_CLASS_RE: Final = re.compile(r"\bdetails-ges ges-([A-G])\b")
_STOREY_PROPERTY: Final = "Etage"
_CHARGES_PROPERTY: Final = "Provision sur charges"


def build_list_page_url(page: int) -> str:
    """Page `page` of the list, counted from 1 as the site's pager does."""
    return _LIST_URL if page == 1 else f"{_LIST_URL}page/{page}/"


def has_next_page(html: str) -> bool:
    return BeautifulSoup(html, "lxml").select_one(_NEXT_PAGE_SELECTOR) is not None


def read_listing_properties(html: str) -> dict[str, str]:
    """The JSON-LD `RealEstateListing`'s facts, by name ("Etage" → "4"); {} if absent."""
    for script in BeautifulSoup(html, "lxml").select('script[type="application/ld+json"]'):
        try:
            data: Any = json.loads(script.string or "")
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict) and data.get("@type") == "RealEstateListing":
            return {
                str(fact.get("name", "")).strip(): str(fact.get("value", "")).strip()
                for fact in data.get("additionalProperty", [])
                if isinstance(fact, dict)
            } | {"description": str(data.get("description", ""))}
    return {}


class SbmImmobilierCrawler(BaseCrawler):
    source_name = "sbm-immobilier"
    BASE_URL = _BASE_URL
    RATE_LIMIT_SECONDS = 2.5
    # One list read page after page, then one page per apartment: no commune to run in
    # parallel, so the whole budget is the spacing between two requests.
    CITY_CONCURRENCY = 1
    MAX_PAGES = 8  # 4 on 2026-11-02
    covers_radius = True  # the agency's whole stock; ListingMatcher narrows it
    forbids_reproduction = True

    async def fetch(self, search_filter: SearchFilter) -> list[Listing]:
        listings = await self._read_stock()
        if listings:
            listings = await self._enrich_details(listings, self._fetch_details)
        logger.info(f"[{self.source_name}] {len(listings)} listings")
        return listings

    async def _read_stock(self) -> list[Listing]:
        """Every apartment of the list, deduplicated by id. O(pages × cards)."""
        by_id: dict[str, Listing] = {}
        for page in range(1, self.MAX_PAGES + 1):
            html = await self._fetch_html(build_list_page_url(page))
            if not html:
                break
            by_id.update((listing.id, listing) for listing in self.parse_page(html))
            if not has_next_page(html):
                break
        return list(by_id.values())

    async def _fetch_details(self, url: str) -> ListingDetails | None:
        html = await self._fetch_html(url)
        return self.parse_details(html) if html else None

    def parse_page(self, html: str) -> list[Listing]:
        """The apartments among a list page's cards; garages and parkings dropped."""
        cards = BeautifulSoup(html, "lxml").select(_CARD_SELECTOR)
        return [listing for card in cards if (listing := self._parse_card(card))]

    def _parse_card(self, card: Tag) -> Listing | None:
        link = card.select_one("h3 a[href]")
        types = card.select_one(".rh-ultra-property-types")
        if link is None or types is None or _FLAT_TYPE not in types.get_text(" ", strip=True):
            return None
        href = read_tag_attr(link, "href")
        try:
            return self._build_listing(card, link.get_text(" ", strip=True), href)
        except Exception as exc:
            self._log_parse_error(href, str(card), exc)
            return None

    def _build_listing(self, card: Tag, title: str, href: str) -> Listing:
        pin = card.select_one("[data-rhea-map-location]")
        address = _ADDRESS_RE.search(pin.get_text(" ", strip=True)) if pin else None
        if pin is None or address is None:
            raise MissingCommuneError
        latitude, longitude = (
            float(part) for part in read_tag_attr(pin, "data-rhea-map-location").split(",")
        )
        surface = card.select_one('[data-tooltip="Surface"] + .rh-ultra-meta-box')
        types = card.select_one(".rh-ultra-property-types")
        added = card.select_one(".added-date")
        published = parse_french_date(added.get_text(" ", strip=True)) if added else None
        photo = card.select_one("img[data-lazy-src]")
        url = self.resolve_url(href)
        return Listing(
            id=build_listing_id(url),
            url=url,
            title=title,
            source=self.source_name,
            location=Location(
                city=address.group(2).strip(),
                postal_code=address.group(1),
                latitude=latitude,
                longitude=longitude,
            ),
            price=Price(amount=parse_price_from_euro_node(card)),
            surface_m2=parse_surface_m2(surface.get_text(" ", strip=True)) if surface else None,
            rooms=parse_room_type(f"{title} {types.get_text(' ', strip=True) if types else ''}"),
            advertiser=_ADVERTISER,
            images=(read_tag_attr(photo, "data-lazy-src"),) if photo else (),
            published_at=published or datetime.now(),
            published_at_source=(
                PublicationSource.SITE if published else PublicationSource.FIRST_SEEN
            ),
        )

    @staticmethod
    def parse_details(html: str) -> ListingDetails:
        """DPE and GES from their classes; storey, charges and furnishing from JSON-LD.

        A « Provision sur charges » means the card's rent was the total, charges
        included: the site prints « Loyer hors charges » plus the provision, and their
        sum is the card's figure.
        """
        dpe = _DPE_CLASS_RE.search(html)
        ges = _GES_CLASS_RE.search(html)
        facts = read_listing_properties(html)
        storey = facts.get(_STOREY_PROPERTY)
        return ListingDetails(
            dpe_rating=DpeRating.from_string(dpe.group(1)) if dpe else None,
            ges_rating=DpeRating.from_string(ges.group(1)) if ges else None,
            floor=parse_floor(f"Etage : {storey}") if storey else None,
            furnished=detect_furnished(facts.get("description", "")),
            charges_included=True if facts.get(_CHARGES_PROPERTY) else None,
        )
