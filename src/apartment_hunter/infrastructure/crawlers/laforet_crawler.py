"""
Laforêt — major French advertiser network (SSR, no JS needed).

curl_cffi. URL: /ville/location-appartement-{city-slug}-{postal}
(postal required → geo API). The page lists the town's own advertisers *and* the
surrounding ones, so results reach well beyond the commune → `covers_radius = True`
and ListingMatcher narrows them back to the filter radius.

Cards hold no readable text stats; every figure sits on the favourite button's
analytics attributes (`data-gtm-item-price-param`, `-size-param`, `-rooms-nb-param`,
`-city-param`, `-zipcode-param`, `-id-param`). The listing URL ends with that same id,
which is how the two halves are joined. No date and no DPE anywhere: the detail page
serves its DPE as an image (`/ajax/properties/{id}/dpe`), so the letter is unreadable
without OCR and energy stays unknown here. The detail page is still visited — its
description is the only place the storey appears, and its criteria table the only
place the furnishing answer does, as a bare "Meublé" chip (never "Meublé : oui").
"""

import re
from datetime import datetime
from decimal import Decimal

from bs4 import BeautifulSoup, Tag
from loguru import logger

from ...domain.entities import Listing, SearchFilter
from ...domain.services import (
    NETWORK_NAMES,
    detect_furnished,
    detect_furnished_chip,
    detect_furnished_label,
)
from ...domain.value_objects import Location, Price
from .base_crawler import (
    BaseCrawler,
    ListingDetails,
    MissingCommuneError,
    build_city_slug,
    build_listing_id,
    parse_floor,
    read_tag_attr,
)
from .geo_postal import resolve_postal_code

_BASE_URL = "https://www.laforet.com"
_ID_ATTR = "data-gtm-item-id-param"
# Listing id closing a card URL: …/louer/annecy/appartement-4-pieces-52846209[#anchor]
_URL_ID_RE = re.compile(r"-(\d+)(?:#.*)?$")
# Headings of the detail page's criteria sections, whose chips hold the furnishing
# answer. Anything outside them ("Location meublée <ville>" in the footer, a similar
# listing's own feature line) must not be read as this listing's answer.
_CRITERIA_HEADINGS = {"intérieur", "extérieur", "autres"}


def _parse_gtm_number(card: Tag, name: str) -> float | None:
    """A numeric analytics attribute, or None when absent/blank/non-numeric."""
    raw = read_tag_attr(card, f"data-gtm-item-{name}-param").strip()
    try:
        return float(raw)
    except ValueError:
        return None


def _collect_criteria_chips(soup: BeautifulSoup) -> list[str]:
    """The detail page's criteria chips ("Chauffage Gaz de ville", "Terrasse", "Meublé").

    Laforêt never writes "Meublé : oui" — furnishing is one bare chip under
    "Intérieur" — so the whole-page labelled reading finds nothing on every one of its
    pages. The section heading is the anchor: the chips of the listing's own table sit
    under it, the site's "location meublée" links do not.

    O(h + c) — h the page's h3 elements, c the chips under the criteria ones.
    """
    chips: list[str] = []
    for heading in soup.find_all("h3"):
        if heading.get_text(strip=True).lower() not in _CRITERIA_HEADINGS:
            continue
        section = heading.parent
        if section is None:
            continue
        chips.extend(span.get_text(" ", strip=True) for span in section.select("div.grid span"))
    return chips


class LaforetCrawler(BaseCrawler):
    source_name = "laforet"
    RATE_LIMIT_SECONDS = 2.0
    BASE_URL = _BASE_URL
    MAX_PAGES = 3
    covers_radius = True  # town page also lists the surrounding advertisers' stock

    async def fetch(self, search_filter: SearchFilter) -> list[Listing]:
        apts = await self._gather_cities(search_filter.cities, self._fetch_city)
        if apts:
            apts = await self._enrich_details(apts, self._fetch_details)
        logger.info(f"[laforet] {len(apts)} listings")
        return apts

    async def _fetch_details(self, url: str) -> ListingDetails | None:
        """The storey and the furnishing answer — the cards carry neither."""
        html = await self._fetch_html(url)
        if not html:
            return None
        return self.parse_details(BeautifulSoup(html, "lxml"))

    @staticmethod
    def parse_details(soup: BeautifulSoup) -> ListingDetails:
        text = soup.get_text(" ", strip=True)
        furnished = detect_furnished_chip(_collect_criteria_chips(soup))
        if furnished is None:
            furnished = detect_furnished_label(text)
        return ListingDetails(floor=parse_floor(text), furnished=furnished)

    async def _fetch_city(self, city: str) -> list[Listing]:
        postal = await resolve_postal_code(city)
        if not postal:
            logger.warning(f"[laforet] No postal code for {city!r}, skipping")
            return []

        base_url = f"{_BASE_URL}/ville/location-appartement-{build_city_slug(city)}-{postal}"
        # A page beyond the last one repeats the first page's cards (the site ignores
        # an out-of-range `page`), which `_paginate` reads as "done".
        return await self._paginate(
            lambda page: base_url if page == 1 else f"{base_url}?page={page}",
            self._parse_page,
            label=city,
        )

    def _parse_page(self, html: str) -> list[Listing]:
        """Join each card's analytics attributes to its listing URL by listing id.

        Two O(n) passes plus dict lookups — n = elements on the page.
        """
        soup = BeautifulSoup(html, "lxml")
        urls: dict[str, str] = {}
        for link in soup.select('a[href*="/louer/"]'):
            href = read_tag_attr(link, "href")
            if m := _URL_ID_RE.search(href):
                urls.setdefault(m.group(1), href.split("#")[0])

        apts: list[Listing] = []
        for card in soup.select(f"button[{_ID_ATTR}]"):
            card_id = read_tag_attr(card, _ID_ATTR)
            url = urls.get(card_id)
            if not url:
                continue
            if listing := self._parse(card, url):
                apts.append(listing)
        return apts

    def _parse(self, card: Tag, href: str) -> Listing | None:
        try:
            if read_tag_attr(card, "data-gtm-item-type-param").lower() != "appartement":
                return None
            url = self.resolve_url(href)

            price = _parse_gtm_number(card, "price") or 0.0
            surface = _parse_gtm_number(card, "size")
            rooms_count = _parse_gtm_number(card, "rooms-nb")
            rooms = int(rooms_count) if rooms_count else None

            # "ANNECY LE VIEUX" → "Annecy Le Vieux": the site shouts its city names.
            city_name = read_tag_attr(card, "data-gtm-item-city-param").title()
            postal_code = read_tag_attr(card, "data-gtm-item-zipcode-param") or None

            # `meuble` and `non-meuble` are both true on most cards (the tracking
            # layer sets them from the advertiser's search facets, not the listing), so
            # they're unusable — infer from the wording instead.
            criteria = read_tag_attr(card, "data-gtm-item-criteria-param")
            name = read_tag_attr(card, "data-gtm-item-name-param")

            if not city_name:
                raise MissingCommuneError
            return Listing(
                id=build_listing_id(url),
                url=url,
                title=f"Appartement {rooms}P {city_name}" if rooms else f"Appartement {city_name}",
                source=self.source_name,
                location=Location(city=city_name, postal_code=postal_code),
                price=Price(amount=Decimal(str(round(price)))),
                surface_m2=surface,
                rooms=rooms,
                furnished=detect_furnished(f"{name} {criteria}"),
                advertiser=NETWORK_NAMES[self.source_name],
                published_at=datetime.now(),
            )
        except Exception as exc:
            self._log_parse_error(href, str(card), exc)
            return None
