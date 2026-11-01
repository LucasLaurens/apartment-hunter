"""
FNAIM — federation of independent agencies; it carries local agencies none of the
networks we crawl list (2A Immobilier, Agence BFM, Entre 2 Lacs, Like My Home…).

Crawled only when the hunter chose to ignore the sites' rules (ADR-0012): the legal
notice forbids reusing its database, and robots.txt disallows rental detail pages.

curl_cffi. SSR HTML, cards = `ul.liste li.item` (the same markup also holds the
site's advice-article teasers, recognised by having no listing link).
URL: /liste-annonces-immobilieres/18-location-appartement-{city-slug}-{postal}.htm
Pagination: …-{postal}-page-{N}.htm. The site's own links append its search state as
query parameters; the path alone serves the same page.
A commune page holds that commune only (Annecy's: 74000 and 74370), so communes are
iterated. Cards: rent per month (CC/HC unstated), surface, rooms, chips (Meublé,
Balcon…), postal code + commune, the agency's name, photos. The detail page adds
DPE + GES and the description where the storey is written.
"""

import re
from datetime import datetime
from decimal import Decimal
from typing import Final

from bs4 import BeautifulSoup, Tag
from loguru import logger

from ...domain.entities import Listing, SearchFilter
from ...domain.services import detect_furnished_chip, detect_furnished_label
from ...domain.value_objects import DpeRating, Location, Price
from .base_crawler import (
    BaseCrawler,
    ListingDetails,
    MissingCommuneError,
    build_city_slug,
    build_listing_id,
    is_in_department,
    parse_floor,
    parse_price_from_euro_node,
    parse_rooms,
    parse_surface_m2,
    read_tag_attr,
)
from .geo_postal import resolve_postal_code

_BASE_URL: Final = "https://www.fnaim.fr"
_SEARCH_PATH: Final = "/liste-annonces-immobilieres/18-location-appartement"
_POSTAL_RE: Final = re.compile(r"\d{5}")
_DPE_RE: Final = re.compile(r"DPE\s*:\s*([A-G])\b")
_GES_RE: Final = re.compile(r"GES\s*:\s*([A-G])\b")


def build_search_url(city: str, postal: str, page: int) -> str:
    """The commune's result page, spelled as the site's own pagination links."""
    suffix = "" if page == 1 else f"-page-{page}"
    return f"{_BASE_URL}{_SEARCH_PATH}-{build_city_slug(city)}-{postal}{suffix}.htm"


class FnaimCrawler(BaseCrawler):
    source_name = "fnaim"
    forbids_reproduction = True
    RATE_LIMIT_SECONDS = 2.0
    BASE_URL = _BASE_URL

    async def fetch(self, search_filter: SearchFilter) -> list[Listing]:
        apts = await self._gather_cities(search_filter.cities, self._fetch_city)
        if apts:
            apts = await self._enrich_details(apts, self._fetch_details)
        logger.info(f"[fnaim] {len(apts)} listings")
        return apts

    async def _fetch_city(self, city: str) -> list[Listing]:
        postal = await resolve_postal_code(city)
        if not postal:
            logger.warning(f"[fnaim] No postal code for {city!r}, skipping")
            return []

        return await self._paginate(
            lambda page: build_search_url(city, postal, page),
            lambda html: self.parse_page(html, postal[:2]),
            label=city,
        )

    def parse_page(self, html: str, department: str) -> list[Listing]:
        """The page's listings in the searched department: a card from elsewhere would
        cost a detail request for a home the radius check drops anyway."""
        cards = BeautifulSoup(html, "lxml").select("ul.liste li.item")
        return [
            listing
            for card in cards
            if (listing := self._parse(card)) and is_in_department(listing, department)
        ]

    async def _fetch_details(self, url: str) -> ListingDetails | None:
        html = await self._fetch_html(url)
        return self.parse_details(html) if html else None

    @staticmethod
    def parse_details(html: str) -> ListingDetails:
        """Energy letters from the « DPE : D (258 kWh/m² an) » list; the storey from the
        description or the criteria table. The page prints no publication date."""
        soup = BeautifulSoup(html, "lxml")
        energy = soup.select_one("ul.dpeListe")
        energy_text = energy.get_text(" ", strip=True) if energy else ""
        dpe = _DPE_RE.search(energy_text)
        ges = _GES_RE.search(energy_text)
        prose = " ".join(
            node.get_text(" ", strip=True)
            for node in soup.select("[itemprop=description], #caracteristiques")
        )
        return ListingDetails(
            dpe_rating=DpeRating.from_string(dpe.group(1)) if dpe else None,
            ges_rating=DpeRating.from_string(ges.group(1)) if ges else None,
            floor=parse_floor(prose),
            furnished=detect_furnished_label(prose),
        )

    def _parse(self, card: Tag) -> Listing | None:
        link = card.select_one("h3 a[href*='/annonce-immobiliere/']")
        if not link:
            return None
        try:
            url = self.resolve_url(read_tag_attr(link, "href"))
            heading = link.get_text(" ", strip=True)

            # "74000 ANNECY HAUTE-SAVOIE AUVERGNE-RHÔNE-ALPES", one <i> between each part
            place = card.select_one("p.lieu a")
            parts = list(place.stripped_strings) if place else []
            postal_code = parts[0] if parts and _POSTAL_RE.fullmatch(parts[0]) else None
            city_name = parts[1].title() if postal_code and len(parts) > 1 else ""
            if not city_name:
                raise MissingCommuneError

            price = card.select_one("p.price")
            agency = card.select_one(".agence .nom")
            description = card.select_one("p.description")
            rooms = parse_rooms(heading)
            return Listing(
                id=build_listing_id(url),
                url=url,
                title=f"Appartement {city_name}" + (f" {rooms}P" if rooms else ""),
                source=self.source_name,
                location=Location(city=city_name, postal_code=postal_code),
                # "807€ par mois": whether charges are included is only on the detail page.
                price=Price(amount=parse_price_from_euro_node(price) if price else Decimal(0)),
                surface_m2=parse_surface_m2(heading),
                rooms=rooms,
                floor=parse_floor(description.get_text(" ", strip=True)) if description else None,
                furnished=detect_furnished_chip(
                    chip.get_text(strip=True) for chip in card.select("p.annonce_criteres span")
                ),
                advertiser=agency.get_text(" ", strip=True) if agency else None,
                images=tuple(
                    src
                    for img in card.select(".itemImage img")
                    if (src := read_tag_attr(img, "src"))
                ),
                published_at=datetime.now(),
            )
        except Exception as exc:
            self._log_parse_error(read_tag_attr(link, "href"), str(card), exc)
            return None
