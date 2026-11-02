"""
Foncia — major French property-management network with a large rental stock.

curl_cffi. Angular SSR HTML, cards = <app-annonce-card>.
URL: /location/{city-slug}-{postal}/appartement (postal required → geo API).
Pagination: ?page=N up to MAX_PAGES.
Rich cards: price (+ "CC" = charges comprises), surface, rooms, DPE class, postal.
Publication dates live in the SSR state blob, not the cards — see `_parse_publication_dates`.
"""

import re
from datetime import datetime
from decimal import Decimal

from bs4 import BeautifulSoup, Tag
from loguru import logger

from ...domain.entities import Listing, SearchFilter
from ...domain.services import NETWORK_NAMES, detect_furnished
from ...domain.value_objects import DpeRating, Location, Price, PublicationSource, classify_ges
from .base_crawler import (
    BaseCrawler,
    MissingCommuneError,
    build_city_slug,
    build_listing_id,
    is_in_department,
    parse_commune_label,
    parse_rooms,
    parse_surface_m2,
    read_tag_attr,
    read_tag_classes,
)
from .french_dates import parse_french_date
from .geo_postal import resolve_postal_code

_BASE_URL = "https://fr.foncia.com"

# Angular escapes its SSR state as `&q;` instead of a double quote.
_STATE_QUOTE = "&q;"
_CANONICAL_URL_KEY = '"canonicalUrl":"'
_DATE_PUBLICATION_RE = re.compile(r'"datePublication":"([^"]+)"')
# Listing reference at the end of a card URL: /location/annecy-74/appartement/331613405.htm
_URL_REFERENCE_RE = re.compile(r"/(\d+)\.htm")


def _parse_publication_dates(page_html: str) -> dict[str, datetime]:
    """Listing reference → publication date, read from the Angular SSR state blob.

    Cards themselves show no date, but the serialised state behind them gives every
    listing a `canonicalUrl` and, further down the same object, a `datePublication`.
    Slicing on `canonicalUrl` bounds each listing: slicing on its `reference` would
    not, because every listing embeds a nested location object whose own `reference`
    is the region code — that inner key would swallow the date.
    O(n) time in page size, O(k) space for k listings on the page.
    """
    blob = page_html.replace(_STATE_QUOTE, '"')
    dates: dict[str, datetime] = {}
    for slice_ in blob.split(_CANONICAL_URL_KEY)[1:]:
        canonical_url, _, rest = slice_.partition('"')
        reference_match = _URL_REFERENCE_RE.search(canonical_url)
        if not reference_match:
            continue
        if m := _DATE_PUBLICATION_RE.search(rest):
            if published_at := parse_french_date(m.group(1)):
                dates[reference_match.group(1)] = published_at
    return dates


class FonciaCrawler(BaseCrawler):
    source_name = "foncia"
    RATE_LIMIT_SECONDS = 2.0
    BASE_URL = _BASE_URL

    async def fetch(self, search_filter: SearchFilter) -> list[Listing]:
        # DPE/GES come straight from the card, so no detail enrichment needed.
        apts = await self._gather_cities(
            search_filter.cities, lambda c: self._fetch_city(c, search_filter)
        )
        logger.info(f"[foncia] {len(apts)} listings")
        return apts

    async def _fetch_city(self, city: str, f: SearchFilter) -> list[Listing]:
        postal = await resolve_postal_code(city)
        if not postal:
            logger.warning(f"[foncia] No postal code for {city!r}, skipping")
            return []

        base_url = f"{_BASE_URL}/location/{build_city_slug(city)}-{postal}/appartement"

        def parse_page(html: str) -> list[Listing]:
            cards = BeautifulSoup(html, "lxml").select("app-annonce-card")
            dates = _parse_publication_dates(html)
            # An unknown town falls back to Foncia's national stock: keep only the cards
            # whose own postal code sits in the searched department.
            return [
                listing
                for c in cards
                if (listing := self._parse(c, dates)) and is_in_department(listing, postal[:2])
            ]

        apts = await self._paginate(
            lambda page: base_url if page == 1 else f"{base_url}?page={page}",
            parse_page,
            label=city,
        )
        logger.info(f"[foncia] {city}: {len(apts)} listings")
        return apts

    def _parse(self, card: Tag, dates: dict[str, datetime]) -> Listing | None:
        try:
            link = card.select_one("a.foncia-card-title-small") or card.select_one(
                "a.gallery-container"
            )
            if not link:
                return None
            href = read_tag_attr(link, "href")
            if "/appartement/" not in href:
                return None
            url = self.resolve_url(href)

            # Title: "Location Appartement 3 pièces 60.35 m² - 55 RUE ... Annecy 74000"
            title_el = card.select_one("a.foncia-card-title-small h3") or card.select_one("h3")
            title_text = title_el.get_text(" ", strip=True) if title_el else ""
            img = card.select_one("img")
            alt_text = img.get("alt", "") if img else ""
            card_text = card.get_text(" ", strip=True)
            info = f"{title_text} {alt_text} {card_text}"

            surface = parse_surface_m2(info)
            rooms = parse_rooms(info)

            # "Sevrier (74320)": a small commune's page is padded with its neighbours.
            place = card.select_one("p.foncia-card-place")
            commune = parse_commune_label(place.get_text(" ", strip=True)) if place else None
            if commune is None:
                raise MissingCommuneError
            city, postal_code = commune

            # Price: "1 076 €", with sup "/ mois CC" → charges comprises
            price_amount = Decimal(0)
            charges_included: bool | None = None
            price_el = card.select_one("h2.foncia-card-price")
            if price_el:
                price_text = price_el.get_text(" ", strip=True)
                digits = re.sub(r"[^\d]", "", price_text.replace("\xa0", "").split("€")[0])
                if digits:
                    price_amount = Decimal(digits)
                if "CC" in price_text.upper():
                    charges_included = True

            # DPE: <span class="dpe-class dpe-class-B"> is the site's final letter.
            dpe_rating: DpeRating | None = None
            dpe_el = card.select_one("span.dpe-class[class*='dpe-class-']")
            if dpe_el:
                if m := re.search(r"dpe-class-([A-G])", " ".join(read_tag_classes(dpe_el)), re.I):
                    dpe_rating = DpeRating(m.group(1).upper())

            # GES: the card's energy widget holds two figures — consumption (kWh)
            # then emissions (kg CO₂). The second drives the GES letter.
            ges_rating: DpeRating | None = None
            numbers = card.select(".foncia-card-dpe .dpe-number")
            if len(numbers) >= 2:
                emission_text = (
                    numbers[1].get_text(strip=True).replace("\xa0", "").replace(",", ".")
                )
                if emission_text:
                    ges_rating = classify_ges(float(emission_text))

            reference_match = _URL_REFERENCE_RE.search(href)
            published_at = dates.get(reference_match.group(1)) if reference_match else None

            return Listing(
                id=build_listing_id(url),
                url=url,
                title=title_text or f"Appartement {city}",
                source=self.source_name,
                location=Location(city=city, postal_code=postal_code),
                price=Price(amount=price_amount),
                surface_m2=surface,
                rooms=rooms,
                dpe_rating=dpe_rating,
                ges_rating=ges_rating,
                charges_included=charges_included,
                furnished=detect_furnished(info),
                advertiser=NETWORK_NAMES[self.source_name],
                published_at=published_at or datetime.now(),
                published_at_source=(
                    PublicationSource.SITE if published_at else PublicationSource.FIRST_SEEN
                ),
            )
        except Exception as exc:
            self._log_parse_error("", str(card), exc)
            return None
