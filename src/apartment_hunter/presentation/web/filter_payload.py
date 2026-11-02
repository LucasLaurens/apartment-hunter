"""Translate the web form's JSON body into a domain SearchFilter.

The create and edit forms post the same shape, so one translator serves both routes
and a new field is added in a single place.

The form shows only some criteria. An edit applies what the form holds *onto the stored
filter*, so the ones it never shows (surface max, charges, photos, excluded agencies,
age, on/off) survive: rebuilding from defaults used to erase them silently (W4).
"""

from dataclasses import replace
from typing import Any, Final

from ...domain.entities import (
    DEFAULT_FILTER_NAME,
    DEFAULT_MAX_RESULTS,
    DEFAULT_NOTIFICATION_INTERVAL_MINUTES,
    DEFAULT_RADIUS_KM,
    DEFAULT_REFRESH_INTERVAL_MINUTES,
    MAX_AGE_DAYS,
    MAX_CITIES,
    MAX_MAX_RESULTS,
    MAX_RADIUS_KM,
    MIN_INTERVAL_MINUTES,
    MIN_MAX_RESULTS,
    MIN_RADIUS_KM,
    FilterBoundError,
    SearchFilter,
)
from ...domain.value_objects import DpeRating
from ..tri_state import parse_tri_state


def _read_cities(raw: object) -> list[str]:
    """ "Annecy, Poisy , " → ["Annecy", "Poisy"]."""
    if not isinstance(raw, str):
        return []
    return [city.strip() for city in raw.split(",") if city.strip()]


def _read_optional_int(raw: object) -> int | None:
    """A blank form field means "no bound", not zero."""
    return int(str(raw)) if raw else None


def _read_optional_float(raw: object) -> float | None:
    return float(str(raw)) if raw else None


def _parse_accepted_dpe(raw: object) -> set[DpeRating]:
    values = raw if isinstance(raw, list) else []
    return {rating for v in values if (rating := DpeRating.from_string(str(v))) is not None}


def filter_from_payload(filter_id: str, body: dict[str, Any]) -> SearchFilter:
    """A new SearchFilter from the form body, blank fields falling back to defaults."""
    return SearchFilter(id=filter_id, **_read_form(body))


def apply_payload(stored: SearchFilter, body: dict[str, Any]) -> SearchFilter:
    """The stored filter with the form's criteria applied; the others are kept."""
    return replace(stored, **_read_form(body))


def _read_form(body: dict[str, Any]) -> dict[str, Any]:
    """Every criterion the web form edits — the only list of them."""
    return {
        "name": str(body.get("name") or "").strip() or DEFAULT_FILTER_NAME,
        "cities": _read_cities(body.get("cities")),
        "radius_km": float(str(body.get("radius_km") or DEFAULT_RADIUS_KM)),
        "excluded_cities": _read_cities(body.get("excluded_cities")),
        "min_price": _read_optional_int(body.get("min_price")),
        "max_price": _read_optional_int(body.get("max_price")),
        "min_surface_m2": _read_optional_float(body.get("min_surface_m2")),
        "max_surface_m2": _read_optional_float(body.get("max_surface_m2")),
        "min_rooms": _read_optional_int(body.get("min_rooms")),
        "max_rooms": _read_optional_int(body.get("max_rooms")),
        "furnished": parse_tri_state(body.get("furnished")),
        "exclude_ground_floor": bool(body.get("exclude_ground_floor", False)),
        "exclude_first_floor": bool(body.get("exclude_first_floor", False)),
        "top_floor_only": bool(body.get("top_floor_only", False)),
        "accepted_dpe_ratings": _parse_accepted_dpe(body.get("accepted_dpe_ratings")),
        "charges_included": parse_tri_state(body.get("charges_included")),
        "collective_heating": parse_tri_state(body.get("collective_heating")),
        "min_photos": _read_optional_int(body.get("min_photos")) or 0,
        "excluded_advertisers": _read_cities(body.get("excluded_advertisers")),
        "max_age_days": _read_optional_int(body.get("max_age_days")),
        "max_results": max(1, int(str(body.get("max_results") or DEFAULT_MAX_RESULTS))),
        "notification_interval_minutes": int(
            str(body.get("notification_interval_minutes") or DEFAULT_NOTIFICATION_INTERVAL_MINUTES)
        ),
        "refresh_interval_minutes": int(
            str(body.get("refresh_interval_minutes") or DEFAULT_REFRESH_INTERVAL_MINUTES)
        ),
    }


# What the form says under a field the domain refused, in the hunter's words (W10).
_FIELD_MESSAGES: Final[dict[str, str]] = {
    "radius_km": f"Le rayon va de {MIN_RADIUS_KM:g} à {MAX_RADIUS_KM:g} km.",
    "max_results": f"Entre {MIN_MAX_RESULTS} et {MAX_MAX_RESULTS} résultats.",
    "notification_interval_minutes": f"Au moins {MIN_INTERVAL_MINUTES} minutes.",
    "refresh_interval_minutes": f"Au moins {MIN_INTERVAL_MINUTES} minutes.",
    "max_age_days": f"Au plus {MAX_AGE_DAYS} jours, ou laissez vide.",
    "cities": f"Au plus {MAX_CITIES} villes.",
}
_NEGATIVE_MESSAGE: Final = "Une valeur positive, ou laissez vide."


def format_filter_error(error: FilterBoundError) -> dict[str, str]:
    """The refused field and a sentence that says how to fix it."""
    return {
        "field": error.field_name,
        "message": _FIELD_MESSAGES.get(error.field_name, _NEGATIVE_MESSAGE),
    }
