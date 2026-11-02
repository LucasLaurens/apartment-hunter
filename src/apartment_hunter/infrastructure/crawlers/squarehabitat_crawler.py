"""
Square Habitat — the Crédit Agricole network's own agencies (SSR Angular, no JS needed).

curl_cffi, like every SSR crawler. The listings sit in the
page's `<script id="ng-state">` JSON under `apiBienUrl/bien`: price charges included,
surface, rooms, the town *with its coordinates*, and a creation date. The detail page's
own ng-state adds the DPE and GES letters, the storey and the furnishing answer.

One department page covers the radius (`covers_radius`): its path carries region and
department slugs a filter does not know (`…/auvergne-rhone-alpes/haute-savoie-74`), so
it is read from the location sitemap rather than built. `robots.txt` forbids
`/resultat-location` and `*/immo/*`; the `/annonces/location/bien/…` route falls under
neither.
"""

import json
import re
from collections.abc import Callable
from datetime import datetime
from decimal import Decimal
from typing import Any, Final

from loguru import logger

from ...domain.entities import Listing, SearchFilter
from ...domain.value_objects import DpeRating, Floor, Location, Price, PublicationSource
from .base_crawler import BaseCrawler, ListingDetails, build_listing_id
from .geo_postal import resolve_postal_code

_BASE_URL: Final = "https://www.squarehabitat.fr"
_SITEMAP_URL: Final = f"{_BASE_URL}/sitemap-location-appartement-localisation.xml"
_PHOTO_URL: Final = f"{_BASE_URL}/medias/biens/m/{{external_id}}.{{extension}}"
_NG_STATE_RE: Final = re.compile(
    r'<script id="ng-state" type="application/json">(.*?)</script>', re.S
)
_LIST_KEY: Final = "apiBienUrl/bien"
_DETAIL_KEY_PREFIX: Final = "apiUrl/page/details-page"
_RENTAL: Final = "LOCATION"
_FLAT: Final = "appartement"
_DEPARTMENT_DIGITS: Final = 2
_ADVERTISER: Final = "Square Habitat"


def _read_ng_state(html: str) -> dict[str, Any]:
    match = _NG_STATE_RE.search(html)
    return json.loads(match.group(1)) if match else {}


def _format_city(raw: str) -> str:
    """'ANNECY  LE VIEUX' → 'Annecy Le Vieux': the site shouts, and doubles its spaces."""
    return " ".join(raw.split()).title()


def _parse_floor(level: object, building_floors: object) -> Floor | None:
    try:
        storey = int(str(level))
    except (TypeError, ValueError):
        return None
    return Floor.from_int(storey, is_top=storey > 0 and storey == building_floors)


def _build_page_url(first_page: str) -> Callable[[int], str]:
    return lambda page: first_page if page == 1 else f"{first_page}?page={page}"


def find_department_page(sitemap: str, department: str) -> str | None:
    """The department-wide listing page, as the sitemap spells its path."""
    match = re.search(rf"<loc>([^<]*/annonces/location/[^<]*-{department})</loc>", sitemap)
    return match.group(1) if match else None


class SquareHabitatCrawler(BaseCrawler):
    source_name = "squarehabitat"
    RATE_LIMIT_SECONDS = 2.5
    BASE_URL = _BASE_URL
    covers_radius = True  # one department page; ListingMatcher narrows it to the radius

    async def fetch(self, search_filter: SearchFilter) -> list[Listing]:
        departments = {
            postal[:_DEPARTMENT_DIGITS]
            for city in search_filter.cities
            if (postal := await resolve_postal_code(city))
        }
        sitemap = await self._fetch_html(_SITEMAP_URL) if departments else None
        if not sitemap:
            return []
        listings: list[Listing] = []
        for department in sorted(departments):
            page_url = find_department_page(sitemap, department)
            if page_url is None:
                logger.info(f"[squarehabitat] no page for department {department}")
                continue
            listings += await self._paginate(
                _build_page_url(page_url), self.parse_page, label=department
            )
        if listings:
            listings = await self._enrich_details(listings, self._fetch_details)
        logger.info(f"[squarehabitat] {len(listings)} listings")
        return listings

    async def _fetch_details(self, url: str) -> ListingDetails | None:
        html = await self._fetch_html(url)
        return self.parse_details(html) if html else None

    def parse_page(self, html: str) -> list[Listing]:
        """One listing per rental flat of the page's ng-state. O(b + h): b listings, h HTML."""
        biens = _read_ng_state(html).get(_LIST_KEY, {}).get("biens", [])
        # The detail URL holds a town slug the JSON does not: read it from the page's links.
        hrefs = {
            href.rsplit("/", 1)[-1]: href
            for href in re.findall(r'href="(/[^"]*/annonces/biens/location/[^"]+)"', html)
        }
        listings: list[Listing] = []
        for bien in biens:
            if bien.get("codeCategorie") != _RENTAL or bien.get("typeBien") != _FLAT:
                continue
            href = hrefs.get(str(bien.get("codeRef")))
            if href is None:
                continue
            try:
                listings.append(self._build_listing(bien, self.resolve_url(href)))
            except (KeyError, TypeError, ValueError) as exc:
                self._log_parse_error(href, json.dumps(bien), exc)
        return listings

    def _build_listing(self, bien: dict[str, Any], url: str) -> Listing:
        city = _format_city(str(bien["ville"]))
        rooms = int(bien["nbPieces"]) if bien.get("nbPieces") else None
        return Listing(
            id=build_listing_id(url),
            url=url,
            title=f"Appartement {rooms} pièces {city}" if rooms else f"Appartement {city}",
            source=self.source_name,
            location=Location(
                city=city,
                postal_code=str(bien.get("codePostal") or "") or None,
                latitude=bien.get("latitude"),
                longitude=bien.get("longitude"),
            ),
            # `prix` is the monthly rent charges included (the detail page's
            # `loyerAvecChargesComprises`), so the total is settled.
            price=Price(amount=Decimal(str(bien["prix"]))),
            charges_included=True,
            surface_m2=bien.get("surfaceHabitable"),
            rooms=rooms,
            description=bien.get("texteAnnonce"),
            advertiser=_ADVERTISER,
            images=tuple(
                _PHOTO_URL.format(external_id=media["externalId"], extension=media["extension"])
                for media in bien.get("medias", [])
                if media.get("type") == "Photo" and media.get("externalId")
            ),
            published_at=datetime.fromisoformat(str(bien["dateCreation"])),
            published_at_source=PublicationSource.SITE,
        )

    @staticmethod
    def parse_details(html: str) -> ListingDetails:
        """DPE, GES, storey and furnishing from the detail page's ng-state."""
        state = _read_ng_state(html)
        page: dict[str, Any] = next(
            (v for k, v in state.items() if k.startswith(_DETAIL_KEY_PREFIX)), {}
        )
        details = page.get("bienDetails") or {}
        energy = details.get("dpeInfos") or {}
        home = details.get("logementInfos") or {}
        furnished = home.get("meuble")
        return ListingDetails(
            dpe_rating=DpeRating.from_string(str(energy.get("dpeLettre") or "")),
            ges_rating=DpeRating.from_string(str(energy.get("gesLettre") or "")),
            floor=_parse_floor(home.get("etage"), home.get("nbEtagesBatiment")),
            furnished=furnished if isinstance(furnished, bool) else None,
        )
