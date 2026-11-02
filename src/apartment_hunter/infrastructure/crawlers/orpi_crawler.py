"""
Orpi — major French real estate advertiser network.

curl_cffi. SSR HTML with article.c-estate-thumb cards.
URL: /location-immobiliere-{city-slug}/
Pagination: ?page=N (up to MAX_PAGES).
Filters: loyer-min, loyer-max, surface-min, nb-pieces-min as query params.
City + postal extracted from listing URL slug.
"""

import re
import urllib.parse
from datetime import datetime
from decimal import Decimal

from bs4 import BeautifulSoup, Tag
from loguru import logger

from ...domain.entities import Listing, SearchFilter
from ...domain.services import detect_furnished, detect_furnished_label
from ...domain.value_objects import DpeRating, Location, Price
from .base_crawler import (
    BaseCrawler,
    ListingDetails,
    MissingCommuneError,
    build_city_slug,
    build_listing_id,
    is_in_department,
    parse_floor,
    parse_rooms,
    parse_surface_m2,
    read_tag_attr,
)
from .french_dates import parse_french_date
from .geo_postal import resolve_postal_code

_BASE_URL = "https://www.orpi.com"
_SEARCH_BASE = f"{_BASE_URL}/location-immobiliere"

# Analytics payload on the detail page, either as raw JS (`dateCreation: "2024-05-06"`)
# or HTML-escaped inside a data attribute (`&quot;dateCreation&quot;:&quot;…&quot;`).
_DATE_CREATION_RE = re.compile(r"dateCreation(?:&quot;)?\s*:\s*(?:&quot;|\")(\d{4}-\d{2}-\d{2})")


class OrpiCrawler(BaseCrawler):
    source_name = "orpi"
    RATE_LIMIT_SECONDS = 2.0
    BASE_URL = _BASE_URL

    async def fetch(self, search_filter: SearchFilter) -> list[Listing]:
        apts = await self._gather_cities(
            search_filter.cities, lambda c: self._fetch_city(c, search_filter)
        )
        if apts:
            apts = await self._enrich_details(apts, self._fetch_details)
        logger.info(f"[orpi] {len(apts)} listings")
        return apts

    async def _fetch_city(self, city: str, f: SearchFilter) -> list[Listing]:
        base_url = f"{_SEARCH_BASE}-{build_city_slug(city)}/"
        # A commune Orpi holds no stock for is padded with listings from elsewhere
        # (Limoges on an Annecy filter); each would cost a detail request for nothing.
        postal = await resolve_postal_code(city)
        department = postal[:2] if postal else ""

        params: dict[str, str] = {}
        if f.min_price:
            params["loyer-min"] = str(int(f.min_price))
        if f.max_price:
            params["loyer-max"] = str(int(f.max_price))
        if f.min_surface_m2:
            params["surface-min"] = str(int(f.min_surface_m2))
        if f.min_rooms:
            params["nb-pieces-min"] = str(f.min_rooms)

        def build_page_url(page: int) -> str:
            page_params = {**params, "page": str(page)} if page > 1 else params
            return f"{base_url}?{urllib.parse.urlencode(page_params)}" if page_params else base_url

        def parse_page(html: str) -> list[Listing]:
            cards = BeautifulSoup(html, "lxml").select("article.c-estate-thumb")
            return [
                listing
                for c in cards
                if (listing := self._parse(c)) and is_in_department(listing, department)
            ]

        # enrichment done once in fetch() across all communes
        return await self._paginate(build_page_url, parse_page, label=city)

    async def _fetch_details(self, url: str) -> ListingDetails | None:
        """Detail page marks the active row of each scale, e.g.
        `.c-dpe__index--active` = "D 213 kWh/m2.an" (DPE) and the same inside
        `.c-dpe--ges` = "B 9 kgeqCO2/m².an" (GES). The leading letter is the class.

        The same page carries the publication date in its analytics payload
        (`dateCreation: "2024-05-06"`). The search-result cards carry that key too, but
        always stamped with the crawl day, so only the detail value is trustworthy.
        """
        html = await self._fetch_html(url)
        if not html:
            return None
        soup = BeautifulSoup(html, "lxml")

        def read_active_letter(scope: Tag | None) -> DpeRating | None:
            if not scope:
                return None
            el = scope.select_one(".c-dpe__index--active")
            if not el:
                return None
            return DpeRating.from_string(el.get_text(" ", strip=True))

        ges_scope = soup.select_one(".c-dpe--ges")
        dpe_scope = next(
            (s for s in soup.select(".c-dpe") if "c-dpe--ges" not in (s.get("class") or [])),
            None,
        )
        published_at = None
        if m := _DATE_CREATION_RE.search(html):
            published_at = parse_french_date(m.group(1))
        return ListingDetails(
            dpe_rating=read_active_letter(dpe_scope),
            ges_rating=read_active_letter(ges_scope),
            published_at=published_at,
            # "Meublé Non" in the criteria list — the search cards never print it.
            furnished=detect_furnished_label(soup.get_text(" ", strip=True)),
        )

    def _parse(self, card: Tag) -> Listing | None:
        try:
            link = card.select_one("a.c-overlay__link")
            if not link:
                return None
            href = read_tag_attr(link, "href")
            if "appartement" not in href:
                return None
            url = self.resolve_url(href)

            # Postal code + city from URL slug: -annecy-74000-{uuid}/
            postal_m = re.search(r"-(\d{5})-[0-9a-f\-]{30,}/$", href)
            postal_code = postal_m.group(1) if postal_m else None

            # Price: .u-h4 span inside price area contains "780 €" (skip badge text)
            price_amount = Decimal(0)
            price_el = card.select_one(".c-estate-thumb__price-tag .u-h4")
            if price_el:
                digits = re.sub(
                    r"[^\d]", "", price_el.get_text(strip=True).replace("\xa0", "").split("€")[0]
                )
                if digits:
                    price_amount = Decimal(digits)

            # Info text: "Appartement 2 pièces 65,41 m²"
            info_el = link.select_one("b")
            info_text = info_el.get_text(" ", strip=True) if info_el else ""

            # m² comes as "m 2" in get_text() due to <sup>2</sup>
            surface = parse_surface_m2(info_text)
            rooms = parse_rooms(info_text)

            # Location: remove SVG/icon content, keep text
            loc_el = card.select_one(".c-estate-thumb__infos__location")
            neighborhood: str | None = None
            city_name = ""
            if loc_el:
                for tag in loc_el.select("svg, i"):
                    tag.decompose()
                loc_text = loc_el.get_text(" ", strip=True)
                # Format: "Annecy - Novel - Teppes" or just "Annecy"
                loc_text = re.sub(r"\s+", " ", loc_text).strip()
                if " - " in loc_text:
                    parts = [p.strip() for p in loc_text.split(" - ", 1)]
                    city_name = parts[0]
                    neighborhood = parts[1] if parts[1] else None
                elif loc_text:
                    city_name = loc_text

            floor = parse_floor(info_text)

            title_parts = []
            if rooms:
                title_parts.append(f"{rooms}P")
            if surface:
                title_parts.append(f"{int(surface)}m²")
            title = (
                "Appartement " + " ".join(title_parts) + f" {city_name}"
                if title_parts
                else f"Appartement {city_name}"
            )

            if not city_name:
                raise MissingCommuneError
            return Listing(
                id=build_listing_id(url),
                url=url,
                title=title,
                source=self.source_name,
                location=Location(
                    city=city_name, postal_code=postal_code, full_address=neighborhood
                ),
                price=Price(amount=price_amount),
                surface_m2=surface,
                rooms=rooms,
                floor=floor,
                furnished=detect_furnished(card.get_text(" ", strip=True)),
                published_at=datetime.now(),
            )
        except Exception as exc:
            self._log_parse_error("", str(card), exc)
            return None
