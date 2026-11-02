"""
Century21 — major French advertiser network. No postal code needed in the URL.

curl_cffi. SSR HTML, cards = div.c-the-property-thumbnail.
URL: /annonces/location-appartement/v-{city-slug}/ (slug uses '+' for spaces,
mirroring the site's own canonical links).
Pagination: ?page=N up to MAX_PAGES.
Card text carries price (+ "charges comprises"), surface, rooms ("N pcs"); the
per-card city/department come from the cover image alt ("appartement - POISY - 74").
"""

import re
from datetime import datetime

from bs4 import BeautifulSoup, Tag
from loguru import logger

from ...domain.entities import Listing, SearchFilter
from ...domain.services import NETWORK_NAMES, detect_furnished, detect_furnished_label
from ...domain.value_objects import Location, Price, classify_dpe, classify_ges
from .base_crawler import (
    BaseCrawler,
    ListingDetails,
    MissingCommuneError,
    build_city_slug,
    build_listing_id,
    parse_price_from_euro_node,
    parse_rooms,
    parse_surface_m2,
    read_tag_attr,
)

_BASE_URL = "https://www.century21.fr"
# Century21 canonicalises spaces to '+': 'La Balme de Sillingy' → 'la+balme+de+sillingy'
_SLUG_SEPARATOR = "+"


class Century21Crawler(BaseCrawler):
    source_name = "century21"
    RATE_LIMIT_SECONDS = 2.0
    BASE_URL = _BASE_URL
    covers_radius = True  # /v-{city}/ already returns nearby communes (Poisy, Sillingy…)

    async def fetch(self, search_filter: SearchFilter) -> list[Listing]:
        return await self._gather_cities(search_filter.cities, self._fetch_city)

    async def _fetch_city(self, city: str) -> list[Listing]:
        slug = build_city_slug(city, _SLUG_SEPARATOR)
        base_url = f"{_BASE_URL}/annonces/location-appartement/v-{slug}/"

        def parse_page(html: str) -> list[Listing]:
            cards = BeautifulSoup(html, "lxml").select("div.c-the-property-thumbnail[data-uid]")
            return [listing for c in cards if (listing := self._parse(c))]

        all_apts = await self._paginate(
            lambda page: base_url if page == 1 else f"{base_url}?page={page}",
            parse_page,
            label=city,
        )
        if all_apts:
            # Search cards carry no energy data; the detail page renders it as an
            # SVG whose first two numeric labels are the consumption (kWh/m².an)
            # and emission (kg CO₂/m².an) figures.
            all_apts = await self._enrich_details(all_apts, self._fetch_details)
        logger.info(f"[century21] {city}: {len(all_apts)} listings")
        return all_apts

    async def _fetch_details(self, url: str) -> ListingDetails | None:
        """Energy and furnishing — Century 21 prints no publication date, on the card or
        the detail page (the sole date shown is the DPE's own survey date)."""
        html = await self._fetch_html(url)
        if not html:
            return None
        soup = BeautifulSoup(html, "lxml")
        furnished = detect_furnished_label(soup.get_text(" ", strip=True))
        box = soup.select_one(".c-the-dpe-ges-new-dpe-svg")
        if not box:
            return ListingDetails(furnished=furnished)
        nums = [
            int(t.get_text(strip=True))
            for t in box.select("text")
            if t.get_text(strip=True).isdigit()
        ]
        # The two CO₂ subscripts ("2") are also digits, but consumption/emission
        # render first — and a real consumption figure is never the lone "2".
        figures = [n for n in nums if n != 2][:2]
        if len(figures) < 2:
            return ListingDetails(furnished=furnished)
        consumption, emission = figures[0], figures[1]
        return ListingDetails(
            dpe_rating=classify_dpe(consumption, emission),
            ges_rating=classify_ges(emission),
            furnished=furnished,
        )

    def _parse(self, card: Tag) -> Listing | None:
        try:
            link = card.select_one("a[href*='/trouver_logement/detail/']")
            if not link:
                return None
            href = read_tag_attr(link, "href")
            url = self.resolve_url(href)

            text = re.sub(r"\s+", " ", card.get_text(" ", strip=True))

            # City + department from cover alt: "appartement - POISY - 74"
            city_name = ""
            department: str | None = None
            img = card.select_one("img")
            if img and (alt := read_tag_attr(img, "alt")):
                parts = [p.strip() for p in alt.split(" - ")]
                if len(parts) >= 3:
                    city_name = parts[1].title()
                    department = parts[2] if re.fullmatch(r"\d{2,3}", parts[2]) else None

            # Price: dedicated €-node holds "1 182 €" (avoids absorbing the department code)
            price_amount = parse_price_from_euro_node(card)
            charges_included: bool | None = True if "charges comprises" in text.lower() else None

            # "60,3 m 2" and "3 pcs" / "3 pièces"
            surface = parse_surface_m2(text)
            rooms = parse_rooms(text)

            if not city_name:
                raise MissingCommuneError
            return Listing(
                id=build_listing_id(url),
                url=url,
                title=f"Appartement {city_name}" + (f" {rooms}P" if rooms else ""),
                source=self.source_name,
                location=Location(city=city_name, department=department),
                price=Price(amount=price_amount),
                surface_m2=surface,
                rooms=rooms,
                charges_included=charges_included,
                furnished=detect_furnished(text),
                advertiser=NETWORK_NAMES[self.source_name],
                published_at=datetime.now(),
            )
        except Exception as exc:
            self._log_parse_error("", str(card), exc)
            return None
