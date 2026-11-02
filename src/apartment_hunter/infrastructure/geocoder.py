import asyncio
import functools
import json
import urllib.parse
import urllib.request
from typing import Any

from geopy.distance import geodesic
from geopy.exc import GeocoderServiceError, GeocoderTimedOut
from geopy.extra.rate_limiter import RateLimiter
from geopy.geocoders import Nominatim
from loguru import logger

from .cache.ttl_cache import GEOCODING_CACHE
from .config import get_settings
from .crawlers.geo_postal import seed_postal_code

_COMMUNES_API = "https://geo.api.gouv.fr/communes"
_DEPT_COMMUNES_API = "https://geo.api.gouv.fr/departements/{dept}/communes"
_DELEGATED_COMMUNES_API = "https://geo.api.gouv.fr/communes_associees_deleguees"
_MAX_COMMUNES = 30  # cap on nearest towns to crawl (matching is uncapped)
# Nominatim's usage policy: at most one request a second, or the IP gets banned.
_NOMINATIM_MIN_DELAY_SECONDS = 1.0


def _make_geocoder() -> Nominatim:
    return Nominatim(user_agent=get_settings().geocoding_user_agent, timeout=5)


async def geocode_cities(city_names: list[str]) -> dict[str, tuple[float, float]]:
    """Return {city_name: (lat, lon)} for all cities. Cached 24h."""
    result: dict[str, tuple[float, float]] = {}
    geocode = RateLimiter(_make_geocoder().geocode, min_delay_seconds=_NOMINATIM_MIN_DELAY_SECONDS)

    for city in city_names:
        key = f"geo:{city.lower()}"
        cached = GEOCODING_CACHE.get(key)
        if cached is not None:
            result[city.lower()] = cached  # type: ignore[assignment]
            continue

        try:
            location = await asyncio.get_event_loop().run_in_executor(
                None, functools.partial(geocode, f"{city}, France")
            )
            if location:
                coords = (location.latitude, location.longitude)
                GEOCODING_CACHE.set(key, coords)
                result[city.lower()] = coords
                logger.debug(f"Geocoded {city}: {coords}")
            else:
                logger.warning(f"Could not geocode city: {city}")
        except (GeocoderTimedOut, GeocoderServiceError) as exc:
            logger.error(f"Geocoding error for {city}: {exc}")

    return result


async def _fetch_json(url: str) -> Any:
    raw = await asyncio.get_event_loop().run_in_executor(
        None, lambda: urllib.request.urlopen(url, timeout=15).read()
    )
    return json.loads(raw)


async def _resolve_dept_of_point(lat: float, lon: float) -> str | None:
    """INSEE department code for a coordinate (geo.api.gouv.fr). Cached 24h."""
    cache_key = f"dept_of:{round(lat, 3)},{round(lon, 3)}"
    cached = GEOCODING_CACHE.get(cache_key)
    if isinstance(cached, str):
        return cached or None
    dept = None
    try:
        data = await _fetch_json(f"{_COMMUNES_API}?lat={lat}&lon={lon}&fields=codeDepartement")
        if data:
            dept = data[0].get("codeDepartement")
    except Exception as exc:
        logger.warning(f"Department lookup failed for {lat},{lon}: {exc}")
    GEOCODING_CACHE.set(cache_key, dept or "")
    return dept


async def _fetch_dept_communes(dept: str) -> list[tuple[str, float, float, str, str]]:
    """[(name, lat, lon, postal, INSEE code)] for every commune of a department. Cached 24h.

    geo.api.gouv.fr has no native radius filter, so we pull the whole department
    (with `centre` coordinates) once and filter by geodesic distance in-process.
    The postal code rides along in the same request: it costs nothing here and lets
    the crawlers skip an ambiguous name-only lookup (see `seed_postal_code`). So does the
    INSEE code, the key of the Carte des loyers (ADR-0010).
    """
    cache_key = f"dept_communes:{dept}"
    cached = GEOCODING_CACHE.get(cache_key)
    if cached is not None:
        return cached  # type: ignore[return-value]
    out: list[tuple[str, float, float, str, str]] = []
    try:
        url = (
            f"{_DEPT_COMMUNES_API.format(dept=dept)}"
            "?fields=nom,code,centre,codesPostaux&format=json"
        )
        for c in await _fetch_json(url):
            centre = c.get("centre", {}).get("coordinates")  # [lon, lat]
            if c.get("nom") and centre and len(centre) == 2:
                postals = c.get("codesPostaux") or []
                out.append(
                    (
                        c["nom"],
                        centre[1],
                        centre[0],
                        postals[0] if postals else "",
                        c.get("code", ""),
                    )
                )
        GEOCODING_CACHE.set(cache_key, out)
    except Exception as exc:
        logger.warning(f"Department {dept} commune fetch failed: {exc}")
    return out


async def _find_communes_within_radius(
    base_cities: list[str],
    radius_km: float,
    excluded_cities: list[str],
    geocoded: dict[str, tuple[float, float]],
) -> list[tuple[str, float, float]]:
    """[(name, lat, lon)] for communes within radius_km of any base city, minus
    excluded ones, sorted by distance to the nearest base centre (closest first)."""
    excluded_lower = {c.strip().lower() for c in excluded_cities}
    centres = [geocoded[c.lower()] for c in base_cities if geocoded.get(c.lower())]
    if not centres:
        return []

    found: dict[str, tuple[float, float, float]] = {}  # name → (lat, lon, best_dist)
    for centre in centres:
        dept = await _resolve_dept_of_point(*centre)
        if not dept:
            continue
        for name, lat, lon, postal, _ in await _fetch_dept_communes(dept):
            if name.lower() in excluded_lower:
                continue
            dist = geodesic(centre, (lat, lon)).km
            if dist <= radius_km and dist < found.get(name, (0, 0, 1e9))[2]:
                found[name] = (lat, lon, dist)
                # This is the commune the search actually means, so hand the crawlers
                # its postal code — a name-only lookup could land on a homonym in
                # another department and send them searching hundreds of km away.
                seed_postal_code(name, postal)

    ordered = sorted(found.items(), key=lambda kv: kv[1][2])
    return [(name, lat, lon) for name, (lat, lon, _) in ordered]


async def expand_crawl_cities(
    base_cities: list[str],
    radius_km: float,
    excluded_cities: list[str],
    geocoded: dict[str, tuple[float, float]],
) -> list[str]:
    """Town names to crawl: the base cities plus the nearest communes within radius.

    Capped at _MAX_COMMUNES nearest towns to keep crawl time bounded — matching
    (geocode_radius_cities) still keeps listings from *any* town in radius.
    """
    excluded_lower = {c.strip().lower() for c in excluded_cities}
    communes = await _find_communes_within_radius(base_cities, radius_km, excluded_cities, geocoded)
    names = [name for name, _, _ in communes[:_MAX_COMMUNES]]
    for city in base_cities:  # always crawl the base cities, even if dept fetch failed
        if city.lower() not in excluded_lower and city not in names:
            names.append(city)
    logger.debug(f"Expanded {base_cities} +{radius_km}km → {len(names)} towns to crawl")
    return names


async def geocode_radius_cities(
    base_cities: list[str],
    radius_km: float,
    excluded_cities: list[str],
) -> dict[str, tuple[float, float]]:
    """{city_lower: (lat, lon)} for the base cities AND every commune within radius,
    so the matcher can place listings whose only location hint is a town name."""
    base = await geocode_cities(base_cities + excluded_cities)
    result: dict[str, tuple[float, float]] = dict(base)
    for name, lat, lon in await _find_communes_within_radius(
        base_cities, radius_km, excluded_cities, base
    ):
        result.setdefault(name.lower(), (lat, lon))
    return result


async def _fetch_delegated_communes(dept: str) -> list[tuple[str, str]]:
    """[(former commune name, code of the commune it merged into)]. Cached 24h.

    "Seynod" is no commune any more: it is a delegated commune of Annecy (74010), and
    neither `/communes?nom=` nor the Carte des loyers knows its own code.
    """
    cache_key = f"delegated_communes:{dept}"
    cached = GEOCODING_CACHE.get(cache_key)
    if cached is not None:
        return cached  # type: ignore[return-value]
    out: list[tuple[str, str]] = []
    try:
        url = f"{_DELEGATED_COMMUNES_API}?codeDepartement={dept}&fields=nom,chefLieu"
        out = [(c["nom"], c["chefLieu"]) for c in await _fetch_json(url) if c.get("chefLieu")]
        GEOCODING_CACHE.set(cache_key, out)
    except Exception as exc:
        logger.warning(f"Department {dept} delegated commune fetch failed: {exc}")
    return out


async def find_commune_codes(base_cities: list[str]) -> dict[str, str]:
    """{commune name: INSEE code} for every commune of the base cities' departments.

    Former communes map to the commune they merged into. Department-wide rather than
    radius-wide: same two cached calls, and a listing just outside the radius still
    gets its reference. O(c) for c communes in those departments (~300 each).
    """
    codes: dict[str, str] = {}
    for lat, lon in (await geocode_cities(base_cities)).values():
        dept = await _resolve_dept_of_point(lat, lon)
        if not dept:
            continue
        for name, _, _, _, code in await _fetch_dept_communes(dept):
            if code:
                codes[name] = code
        # A current commune keeps its own entry: "Annecy" is both a commune and the
        # delegated commune of the merged Annecy, with the same code anyway.
        for name, chef_lieu in await _fetch_delegated_communes(dept):
            codes.setdefault(name, chef_lieu)
    return codes
