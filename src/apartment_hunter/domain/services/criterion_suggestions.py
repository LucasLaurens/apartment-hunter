"""Criterion suggestions: when dismissals keep saying the same thing, offer to filter it.

At the third dismissal in force for one reason — and one value, when the reason has one
(same commune, same advertiser, same storey, same furnishing) — the review proposes the
*most prudent* change to a filter: the smallest one that would have hidden those homes.
It is only ever a proposal; the hunter confirms or refuses, and a refusal holds until
three more dismissals of that reason and value (ADR-0009).

Pure: dismissals, filter and past refusals come in, a revised filter comes out.
"""

import math
from collections.abc import Sequence
from dataclasses import dataclass, replace
from datetime import datetime
from decimal import Decimal
from typing import Final

from ..entities import Dismissal, SearchFilter
from ..value_objects import DismissalReason, DpeRating, format_euros
from .commune_names import fold_commune_name

SUGGESTION_THRESHOLD: Final = 3
_PRICE_STEP: Final = 10  # « à la dizaine sous le plus petit total écarté »
_GROUND_FLOOR: Final = 0
_FIRST_FLOOR: Final = 1
# Judged by the eye or by free text: no filter criterion can say it.
_REASONS_WITHOUT_CRITERION: Final = frozenset({DismissalReason.ASPECT, DismissalReason.OTHER})
_ANY_VALUE: Final = ""


@dataclass(frozen=True)
class CriterionRefusal:
    filter_id: str
    reason: DismissalReason
    value: str  # the grouping value, "" for a reason that has none
    refused_at: datetime
    dismissal_count: int  # dismissals in force for this reason and value when refused


@dataclass(frozen=True)
class CriterionSuggestion:
    reason: DismissalReason
    value: str
    dismissal_count: int
    proposal: str  # « exclure Poisy », read after « Suggestion pour « Annecy » : »
    revised_filter: SearchFilter


def read_grouping_value(dismissal: Dismissal) -> str | None:
    """What makes two dismissals « the same » for a reason; None when it is unknown.

    A dismissal for « étage » with no storey read cannot be counted with any other.
    """
    match dismissal.reason:
        case DismissalReason.CITY:
            return dismissal.home_key.city if dismissal.home_key else None
        case DismissalReason.ADVERTISER:
            return dismissal.advertiser.casefold().strip() if dismissal.advertiser else None
        case DismissalReason.FLOOR:
            return str(dismissal.floor_level) if dismissal.floor_level is not None else None
        case DismissalReason.FURNISHED:
            return str(dismissal.furnished) if dismissal.furnished is not None else None
        case _:
            return _ANY_VALUE


def build_criterion_suggestion(
    trigger: Dismissal,
    dismissals: Sequence[Dismissal],
    search_filter: SearchFilter,
    refusals: Sequence[CriterionRefusal],
    city_name: str,
) -> CriterionSuggestion | None:
    """The change to propose for this filter after `trigger`, or None.

    `city_name` is the commune as the listing spells it, for an exclusion the hunter can
    read; the dismissal only keeps its folded form. O(d + r) for d dismissals, r refusals.
    """
    value = read_grouping_value(trigger)
    if value is None or trigger.reason in _REASONS_WITHOUT_CRITERION:
        return None
    group = [
        d for d in dismissals if d.reason is trigger.reason and read_grouping_value(d) == value
    ]
    if len(group) < SUGGESTION_THRESHOLD:
        return None
    refused_at_count = max(
        (
            r.dismissal_count
            for r in refusals
            if r.filter_id == search_filter.id and r.reason is trigger.reason and r.value == value
        ),
        default=None,
    )
    if refused_at_count is not None and len(group) < refused_at_count + SUGGESTION_THRESHOLD:
        return None
    proposed = _propose_change(trigger, group, search_filter, city_name)
    if proposed is None:
        return None
    revised_filter, proposal = proposed
    return CriterionSuggestion(trigger.reason, value, len(group), proposal, revised_filter)


def _propose_change(
    trigger: Dismissal, group: list[Dismissal], f: SearchFilter, city_name: str
) -> tuple[SearchFilter, str] | None:
    """None when the filter already says it, or when no criterion can say it."""
    match trigger.reason:
        case DismissalReason.TOO_EXPENSIVE:
            return _propose_max_price(group, f)
        case DismissalReason.TOO_SMALL:
            return _propose_min_surface(group, f)
        case DismissalReason.FLOOR:
            return _propose_floor_exclusion(trigger, f)
        case DismissalReason.DPE:
            return _propose_dpe_letters(group, f)
        case DismissalReason.CITY:
            return _propose_city_exclusion(city_name, f)
        case DismissalReason.ADVERTISER:
            return _propose_advertiser_exclusion(trigger, f)
        case DismissalReason.FURNISHED:
            return _propose_furnishing(trigger, f)
        case _:
            return None


def _propose_max_price(group: list[Dismissal], f: SearchFilter) -> tuple[SearchFilter, str] | None:
    lowest = min(d.total_price for d in group)
    # Strictly under the cheapest one, so every dismissed home falls out: 1 230 → 1 220.
    new_max = (math.ceil(lowest) - 1) // _PRICE_STEP * _PRICE_STEP
    if new_max <= (f.min_price or 0) or (f.max_price is not None and new_max >= f.max_price):
        return None
    return (
        replace(f, max_price=new_max),
        f"baisser le loyer max à {format_euros(Decimal(new_max))} CC",
    )


def _propose_min_surface(
    group: list[Dismissal], f: SearchFilter
) -> tuple[SearchFilter, str] | None:
    surfaces = [d.surface_m2 for d in group if d.surface_m2]
    if not surfaces:
        return None
    new_min = math.floor(max(surfaces)) + 1
    if f.min_surface_m2 is not None and new_min <= f.min_surface_m2:
        return None
    if f.max_surface_m2 is not None and new_min > f.max_surface_m2:
        return None
    return replace(f, min_surface_m2=float(new_min)), f"monter la surface min à {new_min} m²"


def _propose_floor_exclusion(
    trigger: Dismissal, f: SearchFilter
) -> tuple[SearchFilter, str] | None:
    """Only the ground and first floors have a criterion; any other storey has none."""
    if trigger.floor_level == _GROUND_FLOOR and not f.exclude_ground_floor:
        return replace(f, exclude_ground_floor=True), "exclure le rez-de-chaussée"
    if trigger.floor_level == _FIRST_FLOOR and not f.exclude_first_floor:
        return replace(f, exclude_first_floor=True), "exclure le 1er étage"
    return None


def _propose_dpe_letters(
    group: list[Dismissal], f: SearchFilter
) -> tuple[SearchFilter, str] | None:
    """Drop the best letter dismissed and every worse one."""
    letters = [d.dpe_rating for d in group if d.dpe_rating]
    if not letters:
        return None
    best_dismissed = min(letters)
    accepted = f.accepted_dpe_ratings or set(DpeRating)
    kept = {rating for rating in accepted if rating < best_dismissed}
    # An empty set means « no DPE filter »: dropping every letter would accept them all.
    if not kept or kept == accepted:
        return None
    spelled = ", ".join(rating.value for rating in sorted(kept))
    return replace(f, accepted_dpe_ratings=kept), f"n'accepter que les DPE {spelled}"


def _propose_city_exclusion(city_name: str, f: SearchFilter) -> tuple[SearchFilter, str] | None:
    """Never a commune the filter is centred on: that filter is about it."""
    folded = fold_commune_name(city_name)
    if folded in {fold_commune_name(c) for c in [*f.excluded_cities, *f.cities]}:
        return None
    return replace(f, excluded_cities=[*f.excluded_cities, city_name]), f"exclure {city_name}"


def _propose_advertiser_exclusion(
    trigger: Dismissal, f: SearchFilter
) -> tuple[SearchFilter, str] | None:
    name = (trigger.advertiser or "").strip()
    if not name or name.casefold() in {a.casefold().strip() for a in f.excluded_advertisers}:
        return None
    return (
        replace(f, excluded_advertisers=[*f.excluded_advertisers, name]),
        f"exclure l'annonceur {name}",
    )


def _propose_furnishing(trigger: Dismissal, f: SearchFilter) -> tuple[SearchFilter, str] | None:
    """The inverse of what was dismissed, and only over a filter still indifferent."""
    if f.furnished is not None or trigger.furnished is None:
        return None
    wanted = not trigger.furnished
    return (
        replace(f, furnished=wanted),
        "ne garder que les logements meublés" if wanted else "ne garder que les non meublés",
    )
