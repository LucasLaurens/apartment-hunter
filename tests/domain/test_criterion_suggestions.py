"""Criterion suggestions after repeated dismissals (ticket 08 of « décider au lieu de lister »)."""

from dataclasses import replace
from datetime import datetime, timedelta

import pytest
from faker import Faker

from apartment_hunter.domain.entities import Dismissal, Listing, SearchFilter
from apartment_hunter.domain.services import (
    SUGGESTION_THRESHOLD,
    CriterionRefusal,
    CriterionSuggestion,
    build_criterion_suggestion,
    build_dismissal,
)
from apartment_hunter.domain.value_objects import DismissalReason, DpeRating, Floor
from tests.fakes.builders import build_listing, build_search_filter

_fake = Faker("fr_FR")


def _dismiss_all(listings: list[Listing], reason: DismissalReason) -> list[Dismissal]:
    start = datetime.now() - timedelta(days=1)
    return [
        build_dismissal(listing, reason, start + timedelta(minutes=n))
        for n, listing in enumerate(listings)
    ]


def _suggest(
    listings: list[Listing],
    reason: DismissalReason,
    search_filter: SearchFilter | None = None,
    refusals: list[CriterionRefusal] | None = None,
) -> CriterionSuggestion | None:
    dismissals = _dismiss_all(listings, reason)
    return build_criterion_suggestion(
        dismissals[-1],
        dismissals,
        search_filter or build_search_filter(max_dpe_rating=None),
        refusals or [],
        listings[-1].location.city,
    )


def test_two_dismissals_suggest_nothing_the_third_does() -> None:
    # Arrange
    homes = [build_listing(price=float(_fake.random_int(1300, 1900))) for _ in range(3)]
    budget = build_search_filter(max_price=2000)

    # Act & Assert
    assert (
        _suggest(homes[: SUGGESTION_THRESHOLD - 1], DismissalReason.TOO_EXPENSIVE, budget) is None
    )
    assert _suggest(homes, DismissalReason.TOO_EXPENSIVE, budget) is not None


def test_too_expensive_lowers_the_max_to_the_ten_under_the_cheapest() -> None:
    # Arrange — cheapest total 1 234 € CC
    homes = [build_listing(price=p, charges=None) for p in (1500.0, 1234.0, 1800.0)]
    homes = [replace(h, charges_included=True) for h in homes]

    # Act
    suggestion = _suggest(homes, DismissalReason.TOO_EXPENSIVE, build_search_filter(max_price=2000))

    # Assert
    assert suggestion is not None
    assert suggestion.revised_filter.max_price == 1230
    assert suggestion.proposal == "baisser le loyer max à 1 230 € CC"


def test_a_round_cheapest_total_still_falls_out() -> None:
    # Arrange — 1 230 € exactly must not survive a max of 1 230
    homes = [build_listing(price=p) for p in (1230.0, 1400.0, 1500.0)]

    # Act
    suggestion = _suggest(homes, DismissalReason.TOO_EXPENSIVE)

    # Assert
    assert suggestion is not None and suggestion.revised_filter.max_price == 1220


def test_too_small_raises_the_min_above_the_largest_dismissed() -> None:
    # Arrange
    homes = [build_listing(surface_m2=s) for s in (28.0, 35.5, 31.0)]

    # Act
    suggestion = _suggest(homes, DismissalReason.TOO_SMALL)

    # Assert
    assert suggestion is not None
    assert suggestion.revised_filter.min_surface_m2 == 36
    assert suggestion.proposal == "monter la surface min à 36 m²"


@pytest.mark.parametrize(
    ("level", "field", "proposal"),
    [
        (0, "exclude_ground_floor", "exclure le rez-de-chaussée"),
        (1, "exclude_first_floor", "exclure le 1er étage"),
    ],
)
def test_a_floor_reason_excludes_that_floor(level: int, field: str, proposal: str) -> None:
    # Arrange
    homes = [replace(build_listing(), floor=Floor.from_int(level)) for _ in range(3)]

    # Act
    suggestion = _suggest(homes, DismissalReason.FLOOR)

    # Assert
    assert suggestion is not None
    assert getattr(suggestion.revised_filter, field) is True
    assert suggestion.proposal == proposal


def test_an_unknown_storey_is_not_counted() -> None:
    # Arrange — two ground floors and one storey nobody read
    ground = [replace(build_listing(), floor=Floor.from_int(0)) for _ in range(2)]
    unknown = replace(build_listing(), floor=None)
    dismissals = _dismiss_all([*ground, unknown], DismissalReason.FLOOR)

    # Act
    suggestion = build_criterion_suggestion(
        dismissals[1], dismissals, build_search_filter(), [], ground[1].location.city
    )

    # Assert
    assert suggestion is None


def test_a_dpe_reason_drops_the_letter_and_every_worse_one() -> None:
    # Arrange
    homes = [build_listing(dpe=letter) for letter in ("F", "E", "G")]

    # Act
    suggestion = _suggest(homes, DismissalReason.DPE)

    # Assert
    assert suggestion is not None
    assert suggestion.revised_filter.accepted_dpe_ratings == {
        DpeRating.A,
        DpeRating.B,
        DpeRating.C,
        DpeRating.D,
    }
    assert suggestion.proposal == "n'accepter que les DPE A, B, C, D"


def test_the_same_commune_three_times_suggests_its_exclusion() -> None:
    # Arrange — sizes differ so the three are three homes, not one
    homes = [build_listing(city="Poisy", surface_m2=float(30 + n * 10)) for n in range(3)]

    # Act
    suggestion = _suggest(homes, DismissalReason.CITY)

    # Assert
    assert suggestion is not None
    assert suggestion.revised_filter.excluded_cities == ["Poisy"]


def test_three_communes_once_each_suggest_nothing() -> None:
    # Arrange
    homes = [build_listing(city=city) for city in ("Poisy", "Argonay", "Villaz")]

    # Act & Assert
    assert _suggest(homes, DismissalReason.CITY) is None


def test_the_same_advertiser_three_times_suggests_its_exclusion() -> None:
    # Arrange
    name = _fake.company()
    homes = [build_listing(advertiser=name) for _ in range(3)]

    # Act
    suggestion = _suggest(homes, DismissalReason.ADVERTISER)

    # Assert
    assert suggestion is not None
    assert suggestion.revised_filter.excluded_advertisers == [name]


def test_dismissing_furnished_homes_suggests_the_inverse_criterion() -> None:
    # Arrange
    homes = [build_listing(furnished=True) for _ in range(3)]

    # Act
    suggestion = _suggest(homes, DismissalReason.FURNISHED)

    # Assert
    assert suggestion is not None
    assert suggestion.revised_filter.furnished is False


@pytest.mark.parametrize("reason", [DismissalReason.ASPECT, DismissalReason.OTHER])
def test_aspect_and_other_never_suggest(reason: DismissalReason) -> None:
    # Arrange
    homes = [build_listing() for _ in range(SUGGESTION_THRESHOLD + 2)]

    # Act & Assert
    assert _suggest(homes, reason) is None


def test_a_filter_that_already_says_it_gets_no_suggestion() -> None:
    # Arrange
    homes = [build_listing(city="Poisy", surface_m2=float(30 + n * 10)) for n in range(3)]
    already = build_search_filter(excluded_cities=["POISY"])

    # Act & Assert
    assert _suggest(homes, DismissalReason.CITY, already) is None


def test_after_a_refusal_the_question_waits_for_three_new_dismissals() -> None:
    # Arrange — refused at 3 dismissals
    search_filter = build_search_filter(max_dpe_rating=None)
    refusal = CriterionRefusal(
        filter_id=search_filter.id,
        reason=DismissalReason.TOO_SMALL,
        value="",
        refused_at=datetime.now(),
        dismissal_count=SUGGESTION_THRESHOLD,
    )
    homes = [build_listing(surface_m2=float(20 + n)) for n in range(2 * SUGGESTION_THRESHOLD)]

    # Act
    at_five = _suggest(homes[:5], DismissalReason.TOO_SMALL, search_filter, [refusal])
    at_six = _suggest(homes, DismissalReason.TOO_SMALL, search_filter, [refusal])

    # Assert
    assert at_five is None
    assert at_six is not None


def test_a_refusal_on_another_filter_does_not_silence_this_one() -> None:
    # Arrange
    refusal = CriterionRefusal(
        filter_id=_fake.lexify("????????"),
        reason=DismissalReason.TOO_SMALL,
        value="",
        refused_at=datetime.now(),
        dismissal_count=SUGGESTION_THRESHOLD,
    )
    homes = [build_listing(surface_m2=float(20 + n)) for n in range(SUGGESTION_THRESHOLD)]

    # Act & Assert
    assert _suggest(homes, DismissalReason.TOO_SMALL, refusals=[refusal]) is not None


def test_a_filter_centred_on_the_commune_is_never_told_to_exclude_it() -> None:
    # Arrange
    homes = [build_listing(city="Poisy", surface_m2=float(30 + n * 10)) for n in range(3)]
    centred = build_search_filter(cities=["Poisy"])

    # Act & Assert
    assert _suggest(homes, DismissalReason.CITY, centred) is None
