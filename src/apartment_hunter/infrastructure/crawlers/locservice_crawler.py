"""
Locservice — private landlords' rental portal (SSR, no JS needed).

Its legal notice forbids reproducing the site without written consent, so the source is
`forbids_reproduction`: crawled only when the hunter chose to ignore the sites' rules
(ADR-0012). robots.txt allows the listing and detail pages.

URL: /{department-slug}-{code}/location-appartement-{commune-slug}.html, then `-p2.html`,
`-p3.html`. The department part (`haute-savoie-74`) comes from geo.api.gouv.fr; the
commune slug spells "Saint" as "st" (`st-jorioz`, `menthon-st-bernard`). A page past the
last one redirects to the last one, which `_paginate` reads as "nothing new" and stops.

The commune page lists the commune's own ads, then its neighbours' up to ~20 km away,
each card saying "À 6km de Annecy" — hence `covers_radius`, ListingMatcher narrows it.
Neighbours across a department border (Arith, Savoie, for Annecy) are real and kept.

Cards (`li.accommodation-ad`): title "Appartement T2 meublé à louer", commune with its
postal code, surface, a bare rent "1 200 € / mois", an excerpt, a thumbnail. Cards marked
"Logement partenaire" are agency ads syndicated from elsewhere (the detail page says
"Professionnel" and names the agent): left out, so the source stays private-only.

The detail page adds DPE and GES (`.energy-bar-item--active`), the full description
(storey), the furnishing chip, and the "charges comprises" that the card never prints.
No publication date anywhere: only a "Récent" badge.
"""

import re
from datetime import datetime
from typing import Final

from bs4 import BeautifulSoup, Tag
from loguru import logger

from ...domain.entities import Listing, SearchFilter
from ...domain.services import detect_furnished, detect_furnished_chip
from ...domain.value_objects import DpeRating, Location, Price
from .base_crawler import (
    BaseCrawler,
    ListingDetails,
    MissingCommuneError,
    build_city_slug,
    build_listing_id,
    parse_commune_label,
    parse_floor,
    parse_price_from_euro_node,
    parse_room_type,
    parse_surface_m2,
    read_tag_attr,
)
from .geo_postal import resolve_department, resolve_postal_code

_BASE_URL: Final = "https://www.locservice.fr"
_PARTNER_MARK: Final = "Logement partenaire"
_SAINT_RE: Final = re.compile(r"(?<![a-z])saint(?![a-z])")
_CHARGES_INCLUDED: Final = "charges comprises"
_CHARGES_EXCLUDED: Final = "hors charges"


def build_search_url(city: str, department_code: str, department_name: str) -> str:
    """The commune's first listing page: '/haute-savoie-74/location-appartement-annecy.html'."""
    department = f"{build_city_slug(department_name)}-{department_code}"
    commune = _SAINT_RE.sub("st", build_city_slug(city))
    return f"{_BASE_URL}/{department}/location-appartement-{commune}.html"


def build_page_url(first_page: str, page: int) -> str:
    return first_page if page == 1 else f"{first_page.removesuffix('.html')}-p{page}.html"


def _read_widest_image(card: Tag) -> tuple[str, ...]:
    """The largest JPEG of the card's srcset; a card without a photo has a placeholder."""
    img = card.select_one("img")
    if img is None:
        return ()
    candidates = [c.split()[0] for c in read_tag_attr(img, "srcset").split(",") if c.strip()]
    widest = candidates[-1] if candidates else read_tag_attr(img, "src")
    return (widest,) if widest else ()


def _read_letter(soup: BeautifulSoup, bar: str) -> DpeRating | None:
    """The selected letter of one energy bar; "NA" (not given) reads as unknown."""
    letter = soup.select_one(f".{bar}-item--active .{bar}-letter")
    return DpeRating.from_string(letter.get_text(strip=True)) if letter else None


def _detect_charges_included(soup: BeautifulSoup) -> bool | None:
    frequency = soup.select_one("#accommodation-ad-rent .rent-frequency")
    text = frequency.get_text(" ", strip=True).lower() if frequency else ""
    if _CHARGES_INCLUDED in text:
        return True
    if _CHARGES_EXCLUDED in text:
        return False
    return None


class LocserviceCrawler(BaseCrawler):
    source_name = "locservice"
    RATE_LIMIT_SECONDS = 2.0
    BASE_URL = _BASE_URL
    MAX_PAGES = 4  # ~47 cards a page; Annecy and its surroundings filled 3 (2026-11-01)
    covers_radius = True  # a commune page also lists its neighbours, ~20 km around
    forbids_reproduction = True  # legal notice: no reproduction without written consent

    async def fetch(self, search_filter: SearchFilter) -> list[Listing]:
        apts = await self._gather_cities(search_filter.cities, self._fetch_city)
        if apts:
            apts = await self._enrich_details(apts, self._fetch_details)
        logger.info(f"[locservice] {len(apts)} listings")
        return apts

    async def _fetch_city(self, city: str) -> list[Listing]:
        postal = await resolve_postal_code(city)
        department = await resolve_department(postal) if postal else None
        if department is None:
            logger.warning(f"[locservice] No department for {city!r}, skipping")
            return []
        return await self.fetch_listing_pages(build_search_url(city, *department), label=city)

    async def fetch_listing_pages(self, first_page: str, label: str) -> list[Listing]:
        return await self._paginate(
            lambda page: build_page_url(first_page, page), self.parse_page, label=label
        )

    async def _fetch_details(self, url: str) -> ListingDetails | None:
        html = await self._fetch_html(url)
        return self.parse_details(html) if html else None

    @staticmethod
    def parse_details(html: str) -> ListingDetails:
        """DPE, GES, storey, furnishing and the charges answer of one detail page.

        The storey is read from the listing's own description and badges only: the page
        also carries tenants' reviews and other homes, whose wording is not this one's.
        """
        soup = BeautifulSoup(html, "lxml")
        badges = [
            li.get_text(" ", strip=True)
            for li in soup.select("#accommodation-ad-characteristics li")
        ]
        description = soup.select_one("#accommodation-ad-description")
        own_text = " ".join([*badges, description.get_text(" ", strip=True) if description else ""])
        return ListingDetails(
            dpe_rating=_read_letter(soup, "energy-bar"),
            ges_rating=_read_letter(soup, "pollution-bar"),
            floor=parse_floor(own_text),
            furnished=detect_furnished_chip(badges),
            charges_included=_detect_charges_included(soup),
        )

    def parse_page(self, html: str) -> list[Listing]:
        cards = BeautifulSoup(html, "lxml").select("li.accommodation-ad")
        return [listing for card in cards if (listing := self._parse(card))]

    def _parse(self, card: Tag) -> Listing | None:
        link = card.select_one(".accommodation-ad-title a")
        if link is None:
            return None
        url = self.resolve_url(read_tag_attr(link, "href"))
        try:
            facts = [
                li.get_text(" ", strip=True)
                for li in card.select(".accommodation-ad-characteristic")
            ]
            if _PARTNER_MARK in facts:
                return None
            commune = next((c for fact in facts if (c := parse_commune_label(fact))), None)
            if commune is None:
                raise MissingCommuneError
            city, postal = commune
            title = link.get_text(" ", strip=True)
            excerpt = card.select_one(".accommodation-ad-description")
            description = excerpt.get_text(" ", strip=True) if excerpt else None
            return Listing(
                id=build_listing_id(url),
                url=url,
                title=title,
                source=self.source_name,
                location=Location(city=city, postal_code=postal),
                # A bare "€ / mois": the card does not say whether charges are in it.
                price=Price(amount=parse_price_from_euro_node(card)),
                surface_m2=parse_surface_m2(" ".join(facts)),
                rooms=parse_room_type(title),
                floor=parse_floor(f"{title} {description or ''}"),
                furnished=detect_furnished(title),
                description=description,
                images=_read_widest_image(card),
                published_at=datetime.now(),
            )
        except Exception as exc:
            self._log_parse_error(url, str(card), exc)
            return None
