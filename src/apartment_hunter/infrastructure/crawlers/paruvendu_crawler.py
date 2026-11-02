"""
ParuVendu — generalist classifieds portal, lightly protected.

curl_cffi. SSR HTML, cards = div.blocAnnonce[data-id].
URL: /immobilier/recherche/location/appartement/{city-slug}-{postal}/ (postal required),
asked directly: the older /immobilier/location/… path only 301s to it. A commune with
listings answers 200 with its own cards; a commune without any 301s to the whole
department page (`haute-savoie-74`), so redirects are not followed (`FOLLOW_REDIRECTS`):
following them downloaded that same department page once per empty commune, 20 of 30
communes around Annecy (2026-11-01). The department page itself is no substitute: it stops
at 5 pages, 150 of 206 listings, and missed 11 of the 40 within 20 km.
Card text carries price (+ "CC" = charges comprises), surface, rooms, city/dept and
the publication date as a plain "03/08/2026" next to a calendar icon.
"""

import re
from datetime import datetime

from bs4 import BeautifulSoup, Tag
from loguru import logger

from ...domain.entities import Listing, SearchFilter
from ...domain.services import detect_furnished, detect_furnished_label
from ...domain.value_objects import DpeRating, Location, Price, PublicationSource, classify_ges
from .base_crawler import (
    BaseCrawler,
    ListingDetails,
    MissingCommuneError,
    build_city_slug,
    build_listing_id,
    parse_commune_label,
    parse_floor,
    parse_price_from_euro_node,
    parse_rooms,
    parse_surface_m2,
    read_tag_attr,
    read_tag_classes,
)
from .french_dates import parse_french_date
from .geo_postal import resolve_postal_code

_BASE_URL = "https://www.paruvendu.fr"
_COMMUNE_URL = f"{_BASE_URL}/immobilier/recherche/location/appartement/{{slug}}-{{postal}}/"
_UPDATE_DATE_TITLE = "Date dernière mise à jour"

# The two energy blocks of the detail page. Each carries its letter in its own class:
# `DPE_consEnerNote NoteEnerg_F`, `DPE_effSerreNote NoteGES2022_E`. Reading the block —
# not the page — is what makes the letter right: the scale drawn above it prints every
# class from `NoteEnerg_A` to `NoteEnerg_G`, so a page-wide search always answers "A".
# The GES class is version-suffixed (`NoteGES2022_`), hence matching on the letter
# suffix rather than on a fixed prefix.
_DPE_NOTE_CLASS = "DPE_consEnerNote"
_GES_NOTE_CLASS = "DPE_effSerreNote"
_NOTE_LETTER_RE = re.compile(r"_([A-G])$")

# Since 2026-10-28 the detail page answers with an anti-scraping captcha, so the card is
# the reliable source: a "DPE : D" badge, and a tooltip with the kWh and the kg CO₂ —
# the GES letter itself is not printed, only derived from those kg on the 2021 scale.
_CARD_DPE_BADGE = "button[aria-describedby^='conso-emission-'] [class*='NoteEnerg_']"
_CARD_EMISSIONS = "[id^='conso-emission-']"
_EMISSIONS_RE = re.compile(r"(\d+(?:[.,]\d+)?)\s*kg")


def _read_note_letter(note: Tag | None) -> DpeRating | None:
    """The rating carried by one energy element's class, or None when it is absent."""
    if note is None:
        return None
    for css_class in read_tag_classes(note):
        if m := _NOTE_LETTER_RE.search(css_class):
            return DpeRating(m.group(1))
    return None


def _read_card_ges(card: Tag) -> DpeRating | None:
    tooltip = card.select_one(_CARD_EMISSIONS)
    m = _EMISSIONS_RE.search(tooltip.get_text(" ", strip=True)) if tooltip else None
    return classify_ges(float(m.group(1).replace(",", "."))) if m else None


class ParuVenduCrawler(BaseCrawler):
    source_name = "paruvendu"
    RATE_LIMIT_SECONDS = 2.0
    BASE_URL = _BASE_URL
    # shortcut: one page (30 cards) per commune; Annecy held 29 on 2026-11-01. A `?p=2` that
    # does not exist answers a full-size 404, so raise this only once a commune overflows.
    MAX_PAGES = 1
    FOLLOW_REDIRECTS = False  # an empty commune redirects to the department page

    async def fetch(self, search_filter: SearchFilter) -> list[Listing]:
        apts = await self._gather_cities(
            search_filter.cities, lambda c: self._fetch_city(c, search_filter)
        )
        if apts:
            apts = await self._enrich_details(apts, self._fetch_details)
        logger.info(f"[paruvendu] {len(apts)} listings")
        return apts

    async def _fetch_city(self, city: str, f: SearchFilter) -> list[Listing]:
        postal = await resolve_postal_code(city)
        if not postal:
            logger.warning(f"[paruvendu] No postal code for {city!r}, skipping")
            return []

        base_url = _COMMUNE_URL.format(slug=build_city_slug(city), postal=postal)

        def parse_page(html: str) -> list[Listing]:
            cards = BeautifulSoup(html, "lxml").select("div.blocAnnonce[data-id]")
            return [listing for c in cards if (listing := self._parse(c))]

        # enrichment done once in fetch() across all communes
        return await self._paginate(
            lambda page: base_url if page == 1 else f"{base_url}?p={page}",
            parse_page,
            label=city,
        )

    async def _fetch_details(self, url: str) -> ListingDetails | None:
        """The listing's energy scales and storey. The date is already on the card,
        so this page is visited for nothing else."""
        html = await self._fetch_html(url)
        if not html:
            return None
        soup = BeautifulSoup(html, "lxml")
        return self.parse_details(soup)

    @staticmethod
    def parse_details(soup: BeautifulSoup) -> ListingDetails:
        text = soup.get_text(" ", strip=True)
        return ListingDetails(
            dpe_rating=_read_note_letter(soup.select_one(f".{_DPE_NOTE_CLASS}")),
            ges_rating=_read_note_letter(soup.select_one(f".{_GES_NOTE_CLASS}")),
            # "Etage : 2" in the characteristics table, "Situé au 2ème étage" in the prose.
            floor=parse_floor(text),
            # "Meublé : non" in the same table — the cards never print it.
            furnished=detect_furnished_label(text),
        )

    def _parse(self, card: Tag) -> Listing | None:
        try:
            link = card.select_one("a[href*='/immobilier/location/']")
            if not link:
                return None
            href = read_tag_attr(link, "href")
            url = self.resolve_url(href)

            text = re.sub(r"\s+", " ", card.get_text(" ", strip=True))

            # The title's last line, "Gaillard (74)": the commune URL redirects to the
            # whole department page, so the searched commune says nothing about a card.
            place = card.select_one("h3 a span")
            commune = (
                parse_commune_label(place.get_text("\n", strip=True).splitlines()[-1])
                if place
                else None
            )
            if commune is None:
                raise MissingCommuneError
            city, department = commune

            # Price: dedicated €-node holds "855 € CC*" (avoids absorbing the photo count)
            price_amount = parse_price_from_euro_node(card)
            charges_included: bool | None = True if "CC" in text.upper() else None

            # "37 m 2" (²/2 collapse to "m 2" in get_text) and "2 pièces"
            surface = parse_surface_m2(text)
            rooms = parse_rooms(text)

            # Date: a clock-icon paragraph holding "03/08/2026". ParuVendu labels it
            # "dernière mise à jour" — the only date it publishes, and the one its own
            # freshness sort uses, so it stands in for the parution date.
            published_at: datetime | None = None
            if clock := card.select_one(f'img[title="{_UPDATE_DATE_TITLE}"]'):
                if clock.parent is not None:
                    published_at = parse_french_date(clock.parent.get_text(" ", strip=True))

            return Listing(
                id=build_listing_id(url),
                url=url,
                title=f"Appartement {city}" + (f" {rooms}P" if rooms else ""),
                source=self.source_name,
                location=Location(city=city, department=department),
                price=Price(amount=price_amount),
                surface_m2=surface,
                rooms=rooms,
                charges_included=charges_included,
                dpe_rating=_read_note_letter(card.select_one(_CARD_DPE_BADGE)),
                ges_rating=_read_card_ges(card),
                furnished=detect_furnished(text),
                published_at=published_at or datetime.now(),
                published_at_source=(
                    PublicationSource.SITE if published_at else PublicationSource.FIRST_SEEN
                ),
            )
        except Exception as exc:
            self._log_parse_error("", str(card), exc)
            return None
