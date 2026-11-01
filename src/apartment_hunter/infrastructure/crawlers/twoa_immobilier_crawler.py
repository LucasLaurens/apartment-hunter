"""
2A Immobilier — one local agency (Annecy, Aix-les-Bains, Rumilly, Chambéry), Drupal SSR.

curl_cffi, like every SSR crawler. Its legal notice forbids reproducing or using the
site's data without prior express consent, so the source runs only when the hunter chose
to ignore the sites' rules (`forbids_reproduction`, ADR-0012).

The whole rental stock fits in one list, `/location`, 12 cards a page, `?page=N` counted
from 0 (8 pages on 2026-11-01, cellars, parkings and shops included). It is read once
(`covers_radius`) and `ListingMatcher` narrows it to the radius. The search form posts,
so neither the town nor the property type can be put in the URL: apartments are kept by
their link path (`/location/appartement/…`). The list repeats its last page for any
`page` past the end, in a different order, so the walk stops on the missing "next" link
rather than on a page of known cards.

A card gives the rent charges included (« /mois CC »), surface, rooms, the town (no postal
code), a photo and a « Meublé » ribbon when furnished. The detail page adds the DPE letter
(the `id` of its SVG, `dpe-indice-c`) and the storey (« Etage : 6 », « Etage : N.C. »).
No publication date anywhere.

The GES label is not read: the agency leaves the emissions blank, and the site then draws
its GES scale on A with the DPE's kWh figure as kg CO₂ — 37 apartments out of 37 « A » on
2026-11-01. A letter the advertiser never gave would read as the best one.
"""

import re
from datetime import datetime
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
    build_listing_id,
    parse_floor,
    parse_price_from_euro_node,
    parse_rooms,
    parse_surface_m2,
    read_tag_attr,
)

_BASE_URL: Final = "https://www.2a-immo.fr"
_LIST_URL: Final = f"{_BASE_URL}/location"
_FLAT_PATH: Final = "/location/appartement/"
_CARD_SELECTOR: Final = "article.node--realestate--teaser"
_NEXT_PAGE_SELECTOR: Final = 'a[rel="next"]'
_CHARGES_INCLUDED_RE: Final = re.compile(r"\bCC\b")
_DPE_SVG_RE: Final = re.compile(r'<svg[^>]*\bid="dpe-indice-([a-g])"', re.I)
# Read on its own line of the facts table: joined to the line before, « Disponibilité :
# 09/11/2026 Etage : N.C. » would give the 2026th storey.
_STOREY_FACT_RE: Final = re.compile(r"^[ée]tage\b", re.I)
_ADVERTISER: Final = "2A Immobilier"
# A card with no photo shows the site's "no photo" picture: not a photo of the home.
_PLACEHOLDER_PHOTO_PATH: Final = "/default_images/"


def build_list_page_url(page: int) -> str:
    """Page `page` of the list, counted from 0 as the site's own pager does."""
    return _LIST_URL if page == 0 else f"{_LIST_URL}?page={page}"


def has_next_page(html: str) -> bool:
    """Whether the pager still links a next page: the last one shows it disabled."""
    return BeautifulSoup(html, "lxml").select_one(_NEXT_PAGE_SELECTOR) is not None


class TwoAImmobilierCrawler(BaseCrawler):
    source_name = "2a-immobilier"
    BASE_URL = _BASE_URL
    RATE_LIMIT_SECONDS = 2.5
    # One list read page after page, never several communes at once: the whole budget
    # is the spacing between two requests.
    CITY_CONCURRENCY = 1
    MAX_PAGES = 10  # 8 on 2026-11-01
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
        for page in range(self.MAX_PAGES):
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
        """The apartments among a list page's cards; cellars, parkings and shops dropped."""
        cards = BeautifulSoup(html, "lxml").select(_CARD_SELECTOR)
        return [listing for card in cards if (listing := self._parse_card(card))]

    def _parse_card(self, card: Tag) -> Listing | None:
        link = card.select_one("h2 a[href]")
        if link is None:
            return None
        href = read_tag_attr(link, "href")
        if _FLAT_PATH not in href:
            return None
        try:
            return self._build_listing(card, link.get_text(" ", strip=True), href)
        except Exception as exc:
            self._log_parse_error(href, str(card), exc)
            return None

    def _build_listing(self, card: Tag, title: str, href: str) -> Listing:
        city_node = card.select_one(".field--city > div:not(.visually-hidden)")
        if city_node is None:
            raise MissingCommuneError
        city = city_node.get_text(" ", strip=True).title()
        price_node = card.select_one(".field--price")
        price_text = price_node.get_text(" ", strip=True) if price_node else ""
        infos = card.select_one(".infos")
        facts = infos.get_text(" ", strip=True) if infos else title
        photo = card.select_one(f".photo img[src]:not([src*='{_PLACEHOLDER_PHOTO_PATH}'])")
        url = self.resolve_url(href)
        return Listing(
            id=build_listing_id(url),
            url=url,
            title=title,
            source=self.source_name,
            location=Location(city=city),
            price=Price(amount=parse_price_from_euro_node(card)),
            charges_included=True if _CHARGES_INCLUDED_RE.search(price_text) else None,
            surface_m2=parse_surface_m2(facts),
            rooms=parse_rooms(facts),
            furnished=detect_furnished_chip(
                span.get_text(strip=True) for span in card.select(".bandeau span")
            ),
            advertiser=_ADVERTISER,
            images=(self.resolve_url(read_tag_attr(photo, "src")),) if photo else (),
            published_at=datetime.now(),
        )

    @staticmethod
    def parse_details(html: str) -> ListingDetails:
        """DPE from its SVG id, storey and furnishing from the facts table."""
        dpe = _DPE_SVG_RE.search(html)
        facts = [
            info.get_text(" ", strip=True)
            for info in BeautifulSoup(html, "lxml").select("div.infos div.info")
        ]
        storey = next((fact for fact in facts if _STOREY_FACT_RE.match(fact)), "")
        return ListingDetails(
            dpe_rating=DpeRating.from_string(dpe.group(1)) if dpe else None,
            floor=parse_floor(storey),
            furnished=detect_furnished_label(" ".join(facts)),
        )
