"""
Bien'ici — a portal fed by agencies, networks and mandataries (private owners too, by
its own schema's `adCreatedByPro`).

The site's front end reads its listings from a public JSON API, no login:
`/realEstateAds.json?filters={…}`. Its `limit` filter takes the zone to search as an
encoded polyline (Google's format), so one query covers a square around the base city
(`covers_radius`) and ListingMatcher narrows it to the circle. The base city's centre is
the middle of its bounding box, read from the site's own place suggester
(`res.bienici.com/suggest.json`).

The terms of use forbid reproducing the listings: the source only runs when the hunter
chose to ignore the sites' rules (ADR-0012).
"""

import json
import math
from collections.abc import Iterable
from datetime import datetime
from decimal import Decimal
from typing import Any, Final
from urllib.parse import urlencode

from loguru import logger

from ...domain.entities import Listing, SearchFilter
from ...domain.services import fold_commune_name
from ...domain.value_objects import DpeRating, Floor, Location, Price, PublicationSource
from .base_crawler import BaseCrawler, build_listing_id, parse_floor
from .geo_postal import resolve_postal_code

_BASE_URL: Final = "https://www.bienici.com"
_SEARCH_URL: Final = f"{_BASE_URL}/realEstateAds.json"
_SUGGEST_URL: Final = "https://res.bienici.com/suggest.json"
_RENT: Final = "rent"
_FLAT: Final = "flat"
_CITY_PLACE: Final = "city"
_PAGE_SIZE: Final = 100
_KM_PER_DEGREE: Final = 111.32
_POLYLINE_PRECISION: Final = 1e5
# The position of a city-wide blur is the commune's centroid, not the home's.
_CITY_WIDE_BLUR: Final = "cityOrArrondissement"


def _format_polyline_value(value: int) -> str:
    shifted = ~(value << 1) if value < 0 else value << 1
    chunks: list[str] = []
    while shifted >= 0x20:
        chunks.append(chr((0x20 | (shifted & 0x1F)) + 63))
        shifted >>= 5
    chunks.append(chr(shifted + 63))
    return "".join(chunks)


def format_polyline(points: Iterable[tuple[float, float]]) -> str:
    """(lat, lon) points in Google's encoded polyline format. O(p): p points."""
    encoded: list[str] = []
    previous_lat = previous_lon = 0
    for lat, lon in points:
        scaled_lat, scaled_lon = round(lat * _POLYLINE_PRECISION), round(lon * _POLYLINE_PRECISION)
        encoded.append(_format_polyline_value(scaled_lat - previous_lat))
        encoded.append(_format_polyline_value(scaled_lon - previous_lon))
        previous_lat, previous_lon = scaled_lat, scaled_lon
    return "".join(encoded)


def build_search_square(lat: float, lon: float, radius_km: float) -> list[tuple[float, float]]:
    """The closed square ring circumscribing the radius around (lat, lon)."""
    half_lat = radius_km / _KM_PER_DEGREE
    half_lon = radius_km / (_KM_PER_DEGREE * math.cos(math.radians(lat)))
    south, north, west, east = lat - half_lat, lat + half_lat, lon - half_lon, lon + half_lon
    return [(south, west), (south, east), (north, east), (north, west), (south, west)]


def find_city_centre(
    places: list[dict[str, Any]], city: str, postal_code: str | None
) -> tuple[float, float] | None:
    """Centre of the suggester's commune named `city` (and holding its postal code, when
    known: four communes are called Saint-Sylvestre). O(s): s suggestions."""
    folded = fold_commune_name(city)
    for place in places:
        if place.get("type") != _CITY_PLACE or fold_commune_name(place.get("name", "")) != folded:
            continue
        if postal_code and postal_code not in place.get("postalCodes", []):
            continue
        box = place["boundingBox"]
        return (box["south"] + box["north"]) / 2, (box["west"] + box["east"]) / 2
    return None


def _read_price(ad: dict[str, Any]) -> tuple[Price, bool | None]:
    """`price` is the rent charges included: on every ad stating both, it equals
    `rentWithoutCharges + charges`. An ad stating no charges keeps a bare, unsettled rent."""
    total = Decimal(str(ad["price"]))
    if ad.get("charges") is None:
        return Price(amount=total), None
    charges = Decimal(str(ad["charges"]))
    return Price(amount=total - charges, charges=charges), True


def _read_floor(ad: dict[str, Any]) -> Floor | None:
    level = ad.get("floor")
    if isinstance(level, int):
        return Floor.from_int(level, is_top=level > 0 and level == ad.get("floorQuantity"))
    return parse_floor(str(ad.get("description") or ""))


def _read_position(ad: dict[str, Any]) -> tuple[float | None, float | None]:
    blur = ad.get("blurInfo") or {}
    position = blur.get("position")
    if not position or blur.get("type") == _CITY_WIDE_BLUR:
        return None, None
    return position["lat"], position["lon"]


class BienIciCrawler(BaseCrawler):
    source_name = "bienici"
    RATE_LIMIT_SECONDS = 3.0
    # Only the base cities are searched, a handful at most: no window to share, so two
    # requests stay a full RATE_LIMIT_SECONDS apart.
    CITY_CONCURRENCY = 1
    BASE_URL = _BASE_URL
    covers_radius = True  # one polygon around the base city; ListingMatcher narrows it
    forbids_reproduction = True  # terms of use: only with the sites' rules ignored

    def __init__(self, timeout: float = 30.0):
        super().__init__(timeout)
        self._centres: dict[str, tuple[float, float]] = {}

    async def fetch(self, search_filter: SearchFilter) -> list[Listing]:
        async def fetch_city(city: str) -> list[Listing]:
            centre = await self._find_centre(city)
            if centre is None:
                logger.info(f"[bienici] no place found for {city!r}")
                return []
            zone = format_polyline(build_search_square(*centre, search_filter.radius_km))
            return await self._paginate(
                lambda page: self.build_search_url(zone, page), self.parse_page, label=city
            )

        listings = await self._gather_cities(search_filter.cities, fetch_city)
        logger.info(f"[bienici] {len(listings)} listings")
        return listings

    async def _find_centre(self, city: str) -> tuple[float, float] | None:
        """Only an answer is cached: a failed lookup is retried at the next crawl."""
        key = city.strip().lower()
        if key in self._centres:
            return self._centres[key]
        body = await self._fetch_html(f"{_SUGGEST_URL}?{urlencode({'q': city})}")
        if not body:
            return None
        centre = find_city_centre(json.loads(body), city, await resolve_postal_code(city))
        if centre is not None:
            self._centres[key] = centre
        return centre

    @staticmethod
    def build_search_url(zone: str, page: int) -> str:
        filters = {
            "size": _PAGE_SIZE,
            "from": (page - 1) * _PAGE_SIZE,
            "page": page,
            "filterType": _RENT,
            "propertyType": [_FLAT],
            "onTheMarket": [True],
            "sortBy": "publicationDate",
            "sortOrder": "desc",
            "mapMode": "enabled",
            "limit": zone,
        }
        return f"{_SEARCH_URL}?{urlencode({'filters': json.dumps(filters)})}"

    def parse_page(self, body: str) -> list[Listing]:
        """One listing per rented flat of the page. O(a): a ads."""
        listings: list[Listing] = []
        for ad in json.loads(body).get("realEstateAds", []):
            if ad.get("adType") != _RENT or ad.get("propertyType") != _FLAT:
                continue
            try:
                listings.append(self._build_listing(ad))
            except (KeyError, TypeError, ValueError, ArithmeticError) as exc:
                self._log_parse_error(str(ad.get("id")), json.dumps(ad), exc)
        return listings

    def _build_listing(self, ad: dict[str, Any]) -> Listing:
        url = f"{_BASE_URL}/annonce/{ad['id']}"
        city = str(ad["city"])
        rooms = ad.get("roomsQuantity")
        price, charges_included = _read_price(ad)
        latitude, longitude = _read_position(ad)
        furnished = ad.get("isFurnished")
        return Listing(
            id=build_listing_id(url),
            url=url,
            title=f"Appartement {rooms} pièces {city}" if rooms else f"Appartement {city}",
            source=self.source_name,
            location=Location(
                city=city,
                postal_code=ad.get("postalCode"),
                latitude=latitude,
                longitude=longitude,
            ),
            price=price,
            charges_included=charges_included,
            surface_m2=ad.get("surfaceArea"),
            rooms=rooms,
            floor=_read_floor(ad),
            dpe_rating=DpeRating.from_string(str(ad.get("energyClassification") or "")),
            ges_rating=DpeRating.from_string(str(ad.get("greenhouseGazClassification") or "")),
            furnished=furnished if isinstance(furnished, bool) else None,
            description=ad.get("description"),
            advertiser=ad.get("accountDisplayName"),
            images=tuple(photo["url"] for photo in ad.get("photos", []) if photo.get("url")),
            published_at=datetime.fromisoformat(str(ad["publicationDate"])),
            published_at_source=PublicationSource.SITE,
        )
