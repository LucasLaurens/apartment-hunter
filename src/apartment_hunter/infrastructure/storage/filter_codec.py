"""The JSON shape a saved filter takes on disk.

A `SearchFilter` is stored as one JSON blob in `filters.config`, so the schema does not
change every time a criterion is added. That trade has a price: the encoder enumerates
its keys by hand, and a field added to the entity but forgotten here is lost silently on
every save. `tests/infrastructure/test_filter_codec.py` fails when the two drift.

Lives beside the SQLite adapter rather than inside it: 122 lines of format and legacy-key
handling that never speak SQL, and are pure enough to test without opening a file.
"""

import json
from datetime import datetime
from typing import Any

from loguru import logger

from ...domain.entities import (
    DEFAULT_MAX_RESULTS,
    DEFAULT_NOTIFICATION_INTERVAL_MINUTES,
    DEFAULT_RADIUS_KM,
    DEFAULT_REFRESH_INTERVAL_MINUTES,
    MAX_MAX_RESULTS,
    MAX_RADIUS_KM,
    MIN_INTERVAL_MINUTES,
    MIN_MAX_RESULTS,
    MIN_RADIUS_KM,
    SearchFilter,
    clamp_float,
    clamp_int,
)
from ...domain.value_objects import DpeRating


def filter_to_json(f: SearchFilter) -> str:
    data = {
        "cities": f.cities,
        "radius_km": f.radius_km,
        "excluded_cities": f.excluded_cities,
        "min_price": f.min_price,
        "max_price": f.max_price,
        "min_surface_m2": f.min_surface_m2,
        "max_surface_m2": f.max_surface_m2,
        "min_rooms": f.min_rooms,
        "max_rooms": f.max_rooms,
        "furnished": f.furnished,
        "exclude_ground_floor": f.exclude_ground_floor,
        "exclude_first_floor": f.exclude_first_floor,
        "top_floor_only": f.top_floor_only,
        "accepted_dpe_ratings": sorted(r.value for r in f.accepted_dpe_ratings),
        "charges_included": f.charges_included,
        "collective_heating": f.collective_heating,
        "min_photos": f.min_photos,
        "excluded_advertisers": f.excluded_advertisers,
        "max_age_days": f.max_age_days,
        "max_results": f.max_results,
        "notification_interval_minutes": f.notification_interval_minutes,
        "refresh_interval_minutes": f.refresh_interval_minutes,
    }
    return json.dumps(data)


def _parse_accepted_dpe(data: dict[str, Any]) -> set[DpeRating]:
    """Read the DPE set, falling back to the legacy single `max_dpe_rating` threshold."""
    if "accepted_dpe_ratings" in data:
        parsed = {DpeRating.from_string(v) for v in data["accepted_dpe_ratings"]}
        parsed.discard(None)
        return parsed  # type: ignore[return-value]
    legacy = data.get("max_dpe_rating")
    legacy_rating = DpeRating.from_string(legacy) if legacy else None
    return DpeRating.up_to(legacy_rating) if legacy_rating else set()


def _read_excluded_advertisers(data: dict[str, Any]) -> list[str]:
    """Advertisers the user banned, reading the legacy `exclude_agencies` key too.

    The field was renamed when the glossary settled on *annonceur*: a private landlord
    is not an agency. Filters saved before the rename must keep working — silently
    losing an exclusion would put back listings the user had told us to drop.
    """
    stored = data.get("excluded_advertisers")
    if stored is None:
        stored = data.get("exclude_agencies", [])
    return list(stored)


def filter_from_json(row: dict[str, Any]) -> SearchFilter:
    """A stored filter, its out-of-range values clamped instead of refused.

    `SearchFilter` rejects an interval or radius the crawler can't honour, but a row
    written before those bounds existed must not make the whole app unusable — clamp it
    back into range and log, rather than raise on startup.
    """
    data = json.loads(row["config"])
    accepted_dpe = _parse_accepted_dpe(data)
    return SearchFilter(
        id=row["id"],
        name=row["name"],
        enabled=bool(row["enabled"]),
        created_at=datetime.fromisoformat(row["created_at"]),
        cities=data["cities"],
        radius_km=_read_radius(data),
        excluded_cities=data.get("excluded_cities", []),
        min_price=_keep_positive(data.get("min_price")),
        max_price=_keep_positive(data.get("max_price")),
        min_surface_m2=_keep_positive(data.get("min_surface_m2")),
        max_surface_m2=_keep_positive(data.get("max_surface_m2")),
        min_rooms=_keep_positive(data.get("min_rooms")),
        max_rooms=_keep_positive(data.get("max_rooms")),
        furnished=data.get("furnished"),
        exclude_ground_floor=data.get("exclude_ground_floor", False),
        exclude_first_floor=data.get("exclude_first_floor", False),
        top_floor_only=data.get("top_floor_only", False),
        accepted_dpe_ratings=accepted_dpe,
        charges_included=data.get("charges_included"),
        collective_heating=data.get("collective_heating"),
        min_photos=max(0, int(data.get("min_photos", 0))),
        excluded_advertisers=_read_excluded_advertisers(data),
        max_age_days=_keep_positive(data.get("max_age_days")),
        max_results=clamp_int(
            int(data.get("max_results", DEFAULT_MAX_RESULTS)), MIN_MAX_RESULTS, MAX_MAX_RESULTS
        ),
        notification_interval_minutes=_read_interval(
            data, "notification_interval_minutes", DEFAULT_NOTIFICATION_INTERVAL_MINUTES
        ),
        refresh_interval_minutes=_read_interval(
            data, "refresh_interval_minutes", DEFAULT_REFRESH_INTERVAL_MINUTES
        ),
    )


def _read_radius(data: dict[str, Any]) -> float:
    stored = float(data.get("radius_km", DEFAULT_RADIUS_KM))
    clamped = clamp_float(stored, MIN_RADIUS_KM, MAX_RADIUS_KM)
    if clamped != stored:
        logger.warning(f"Stored radius_km {stored} out of range — clamped to {clamped}")
    return clamped


def _read_interval(data: dict[str, Any], key: str, default: int) -> int:
    """A missing interval takes the default; a stored 0 or negative is raised to the floor."""
    raw = data.get(key)
    if raw is None:
        return default
    minutes = int(raw)
    if minutes < MIN_INTERVAL_MINUTES:
        logger.warning(f"Stored {key} {minutes} below minimum — raised to {MIN_INTERVAL_MINUTES}")
        return MIN_INTERVAL_MINUTES
    return minutes


def _keep_positive[T: (int, float)](value: T | None) -> T | None:
    """A stored bound that turned negative is meaningless — treat it as absent."""
    if value is None:
        return None
    return value if value >= 0 else None
