"""Interactive `hunt filter add` questionnaire."""

import uuid

from rich.prompt import Confirm, Prompt

from ...domain.entities import (
    DEFAULT_MAX_RESULTS,
    DEFAULT_NOTIFICATION_INTERVAL_MINUTES,
    DEFAULT_RADIUS_KM,
    DEFAULT_REFRESH_INTERVAL_MINUTES,
    SearchFilter,
)
from ...domain.value_objects import DpeRating
from ..tri_state import CHOICES, INDIFFERENT, parse_tri_state

FILTER_ID_LENGTH = 8
_DEFAULT_CITY = "Paris"


def ask_filter() -> SearchFilter:
    """Prompt for every criterion and return the (unsaved) filter described."""
    name = Prompt.ask("Filter name")
    cities = _ask_list("Cities (comma-separated)", default=_DEFAULT_CITY)
    radius = float(Prompt.ask("Search radius (km)", default=str(DEFAULT_RADIUS_KM)))
    excluded = _ask_list("Excluded cities (comma-separated, or empty)", default="")

    return SearchFilter(
        id=str(uuid.uuid4())[:FILTER_ID_LENGTH],
        name=name,
        cities=cities,
        radius_km=radius,
        excluded_cities=excluded,
        min_price=_ask_optional_int("Min price (€/mo, or Enter to skip)"),
        max_price=_ask_optional_int("Max price (€/mo, or Enter to skip)"),
        min_surface_m2=_ask_optional_float("Min surface (m², or Enter to skip)"),
        min_rooms=_ask_optional_int("Min rooms (or Enter to skip)"),
        max_rooms=_ask_optional_int("Max rooms (or Enter to skip)"),
        furnished=_ask_tri_state("Furnished?"),
        exclude_ground_floor=Confirm.ask("Exclude ground floor?", default=False),
        exclude_first_floor=Confirm.ask("Exclude 1st floor?", default=False),
        top_floor_only=Confirm.ask("Top floor only?", default=False),
        accepted_dpe_ratings=_ask_accepted_dpe(),
        charges_included=_ask_tri_state("Charges included?"),
        max_results=int(
            Prompt.ask("Max results to show (paginated above 25)", default=str(DEFAULT_MAX_RESULTS))
        ),
        notification_interval_minutes=int(
            Prompt.ask(
                "Notification interval (minutes)",
                default=str(DEFAULT_NOTIFICATION_INTERVAL_MINUTES),
            )
        ),
        refresh_interval_minutes=int(
            Prompt.ask(
                "Auto-refresh interval (minutes)", default=str(DEFAULT_REFRESH_INTERVAL_MINUTES)
            )
        ),
    )


def _ask_list(prompt: str, default: str) -> list[str]:
    raw = Prompt.ask(prompt, default=default)
    return [item.strip() for item in raw.split(",") if item.strip()]


def _ask_tri_state(prompt: str) -> bool | None:
    return parse_tri_state(Prompt.ask(prompt, choices=CHOICES, default=INDIFFERENT))


def _ask_accepted_dpe() -> set[DpeRating]:
    """A worst acceptable letter expands to every rating at least as good."""
    raw = Prompt.ask("Max DPE rating (A/B/C/D or Enter to skip)", default="")
    max_rating = DpeRating.from_string(raw) if raw.strip() else None
    return DpeRating.up_to(max_rating) if max_rating else set()


def _ask_optional_int(prompt: str) -> int | None:
    raw = Prompt.ask(prompt, default="")
    return int(raw) if raw.strip().isdigit() else None


def _ask_optional_float(prompt: str) -> float | None:
    raw = Prompt.ask(prompt, default="")
    try:
        return float(raw) if raw.strip() else None
    except ValueError:
        return None
