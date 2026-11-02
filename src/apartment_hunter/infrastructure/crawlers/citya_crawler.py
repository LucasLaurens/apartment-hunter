"""
Citya Immobilier — national property-management network (SSR, Symfony).

curl_cffi. URL: /annonces/location/appartement/{city-slug}-{postal}
(the postal is Citya's own, resolved via the geo API). Cards = div.property-card, whose
data attributes carry the price, the type and the listing id; the city, postal and
"N pièces X m²" sit in the card's link text.

Careful: when a town has no rental stock Citya still renders cards — its
"biens loués récemment" and cross-city carousels — so a town page can serve listings
from the other side of France. `is_in_department` drops anything whose postal code leaves
the searched department before the matcher ever sees it.

DPE/GES only exist on the detail page, embedded as Inkscape SVGs whose filename holds
the letter (`docname="DPE_E.svg"`). Citya publishes no date anywhere.
"""

import re
from datetime import datetime
from decimal import Decimal

from bs4 import BeautifulSoup, Tag
from loguru import logger

from ...domain.entities import Listing, SearchFilter
from ...domain.services import NETWORK_NAMES, detect_furnished, detect_furnished_label
from ...domain.value_objects import DpeRating, Location, Price
from .base_crawler import (
    BaseCrawler,
    ListingDetails,
    MissingCommuneError,
    build_city_slug,
    build_listing_id,
    is_in_department,
    parse_commune_label,
    parse_rooms,
    parse_surface_m2,
    read_tag_attr,
)
from .geo_postal import resolve_postal_code

_BASE_URL = "https://www.citya.com"
_CARD_SELECTOR = "div.property-card[data-itemid]"
_ENERGY_SVG_RE = re.compile(r'docname="(DPE|GES)_([A-G])\.svg"')


class CityaCrawler(BaseCrawler):
    source_name = "citya"
    RATE_LIMIT_SECONDS = 2.0
    BASE_URL = _BASE_URL
    MAX_PAGES = 3

    async def fetch(self, search_filter: SearchFilter) -> list[Listing]:
        apts = await self._gather_cities(search_filter.cities, self._fetch_city)
        if apts:
            apts = await self._enrich_details(apts, self._fetch_details)
        logger.info(f"[citya] {len(apts)} listings")
        return apts

    async def _fetch_city(self, city: str) -> list[Listing]:
        postal = await resolve_postal_code(city)
        if not postal:
            logger.warning(f"[citya] No postal code for {city!r}, skipping")
            return []

        apts = await self._fetch_city_page(city, postal)
        # Cities split into arrondissements resolve to one of them (Lyon → 69001), which
        # Citya doesn't know as a town: that URL silently serves the national listing
        # page. Its own slug uses the department's round postal, so retry with that.
        umbrella_postal = f"{postal[:2]}000"
        if not apts and postal != umbrella_postal:
            logger.debug(f"[citya] {city}: retrying with {umbrella_postal}")
            apts = await self._fetch_city_page(city, umbrella_postal)
        return apts  # enrichment done once in fetch() across all communes

    async def _fetch_city_page(self, city: str, postal: str) -> list[Listing]:
        base_url = f"{_BASE_URL}/annonces/location/appartement/{build_city_slug(city)}-{postal}"
        department = postal[:2]

        def parse_page(html: str) -> list[Listing]:
            cards = BeautifulSoup(html, "lxml").select(_CARD_SELECTOR)
            return [
                listing
                for c in cards
                if (listing := self._parse(c)) and is_in_department(listing, department)
            ]

        return await self._paginate(
            lambda page: base_url if page == 1 else f"{base_url}?page={page}",
            parse_page,
            label=city,
        )

    async def _fetch_details(self, url: str) -> ListingDetails | None:
        """DPE and GES from the detail page's energy SVG filenames, plus the
        furnishing answer from its criteria table."""
        html = await self._fetch_html(url)
        if not html:
            return None
        letters = dict(_ENERGY_SVG_RE.findall(html))
        return ListingDetails(
            dpe_rating=DpeRating.from_string(letters.get("DPE", "")),
            ges_rating=DpeRating.from_string(letters.get("GES", "")),
            # Text, not raw HTML: a site's own markup links to "location meublée <ville>".
            furnished=detect_furnished_label(BeautifulSoup(html, "lxml").get_text(" ", strip=True)),
        )

    def _parse(self, card: Tag) -> Listing | None:
        try:
            link = card.select_one("a[href]")
            if not link:
                return None
            href = read_tag_attr(link, "href")
            if "/location/appartement/" not in href:
                return None
            url = self.resolve_url(href)

            price_digits = re.sub(r"[^\d]", "", read_tag_attr(card, "data-price"))
            price_amount = Decimal(price_digits) if price_digits else Decimal(0)

            # First link paragraph: "Lyon 8e Arrondissement (69008)"
            paragraphs = [p.get_text(" ", strip=True) for p in link.select("p")]
            commune = next(filter(None, map(parse_commune_label, paragraphs)), None)
            if commune is None:
                raise MissingCommuneError
            city_name, postal_code = commune

            # "Appartement 2 pièces 39.03m²" — also exposed as data-itemname.
            info = read_tag_attr(card, "data-itemname") or " ".join(paragraphs)
            surface = parse_surface_m2(info)
            rooms = parse_rooms(info)

            return Listing(
                id=build_listing_id(url),
                url=url,
                title=f"Appartement {city_name}" + (f" {rooms}P" if rooms else ""),
                source=self.source_name,
                location=Location(city=city_name, postal_code=postal_code),
                price=Price(amount=price_amount),
                surface_m2=surface,
                rooms=rooms,
                furnished=detect_furnished(card.get_text(" ", strip=True)),
                advertiser=NETWORK_NAMES[self.source_name],
                published_at=datetime.now(),
            )
        except Exception as exc:
            self._log_parse_error("", str(card), exc)
            return None
