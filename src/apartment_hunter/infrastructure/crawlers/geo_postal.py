"""
City → postal code resolver via the free French government geo API.

Some crawlers (Foncia, ParuVendu, Laforêt, Citya) build search URLs that require a
postal code slug (e.g. `annecy-74000`). SearchFilter only carries city names, so we
resolve the principal postal code on demand and cache it process-wide.

A name alone can be ambiguous — four French communes are called Saint-Sylvestre, in
four different departments — so the radius expansion, which knows *which* commune it
selected, seeds the right code via `seed_postal_code` before any crawl starts.
"""

import asyncio

from loguru import logger

_GEO_API = "https://geo.api.gouv.fr/communes"
_GEO_API_TIMEOUT_SECONDS = 10
_cache: dict[str, str | None] = {}
_department_cache: dict[str, tuple[str, str]] = {}  # postal → (code, name)
_lock = asyncio.Lock()


def seed_postal_code(city: str, postal: str) -> None:
    """Record a commune's postal code from a source that resolved it unambiguously.

    Overwrites any cached value: a code that came with the commune's own coordinates
    beats one guessed from a name shared by several departments.
    """
    if postal:
        _cache[city.strip().lower()] = postal


async def resolve_postal_code(city: str) -> str | None:
    """Return the principal postal code for a city name, or None if unknown.

    Only an answer is cached: the cache lives as long as `hunt watch`, so a cached
    failure (a 500, a timeout) used to drop the commune from every later tick.
    """
    key = city.strip().lower()
    if key in _cache:
        return _cache[key]

    async with _lock:
        if key in _cache:  # re-check after acquiring the lock
            return _cache[key]
        try:
            postal = await _run_query(city)
        except Exception as exc:
            logger.warning(f"[geo_postal] lookup failed for {city!r}, retried next call: {exc}")
            return None
        _cache[key] = postal
        return postal


async def _run_query(city: str) -> str | None:
    from curl_cffi.requests import AsyncSession

    async with AsyncSession() as session:
        resp = await session.get(
            _GEO_API,
            params={"nom": city, "fields": "codesPostaux", "limit": 1},
            timeout=_GEO_API_TIMEOUT_SECONDS,
        )
    resp.raise_for_status()
    data = resp.json()
    postals = (data[0].get("codesPostaux") or []) if isinstance(data, list) and data else []
    return str(postals[0]) if postals else None


async def resolve_department(postal: str) -> tuple[str, str] | None:
    """('74', 'Haute-Savoie') for the department holding `postal`, or None if unknown.

    Asked by postal code, never cut from its first two digits: Corsica (20xxx → 2A/2B)
    and the overseas departments (97x) do not split that way. Only an answer is cached.
    """
    if postal in _department_cache:
        return _department_cache[postal]
    try:
        department = await _run_department_query(postal)
    except Exception as exc:
        logger.warning(f"[geo_postal] department lookup failed for {postal!r}: {exc}")
        return None
    if department:
        _department_cache[postal] = department
    return department


async def _run_department_query(postal: str) -> tuple[str, str] | None:
    from curl_cffi.requests import AsyncSession

    async with AsyncSession() as session:
        resp = await session.get(
            _GEO_API,
            params={"codePostal": postal, "fields": "departement", "limit": 1},
            timeout=_GEO_API_TIMEOUT_SECONDS,
        )
    resp.raise_for_status()
    data = resp.json()
    department = (data[0].get("departement") or {}) if isinstance(data, list) and data else {}
    code, name = department.get("code"), department.get("nom")
    return (str(code), str(name)) if code and name else None
