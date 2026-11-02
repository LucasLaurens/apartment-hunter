"""Re-publications of one home are grouped for display — never merged, never dropped."""

import pytest
from faker import Faker

from apartment_hunter.domain.services import DismissedHomes, build_dismissal, group_duplicates
from apartment_hunter.domain.value_objects import DismissalReason

from ..fakes.builders import build_listing

_fake = Faker("fr_FR")

# One commune, two spellings: the geo API's INSEE name, then a site's own (Laforêt
# drops accents and hyphens, Century 21 capitalises every word).
_SPELLINGS = [
    ("Chambéry", "Chambery"),
    ("Saint-Félix", "Saint Felix"),
    ("Alby-sur-Chéran", "Alby Sur Cheran"),
]


def test_the_same_home_on_two_sources_becomes_one_group() -> None:
    # Arrange — a non-exclusive mandate: two agencies, one flat, one rent
    on_seloger = build_listing(source="seloger", price=900.0, surface_m2=58.0, rooms=3)
    on_orpi = build_listing(source="orpi", price=900.0, surface_m2=58.0, rooms=3)

    # Act
    groups = group_duplicates([on_seloger, on_orpi])

    # Assert
    assert len(groups) == 1
    assert groups[0].has_duplicates
    assert set(groups[0].sources) == {"seloger", "orpi"}


def test_no_listing_is_ever_dropped_by_grouping() -> None:
    # Arrange
    listings = [
        build_listing(source="seloger", price=900.0, surface_m2=58.0, rooms=3),
        build_listing(source="orpi", price=900.0, surface_m2=58.0, rooms=3),
        build_listing(source="pap", price=750.0, surface_m2=40.0, rooms=2),
    ]

    # Act
    groups = group_duplicates(listings)

    # Assert — a wrong grouping must cost a glance, never a missed home
    kept = {listing.id for group in groups for listing in group.all_listings}
    assert kept == {listing.id for listing in listings}


def test_two_identical_flats_on_one_source_stay_apart() -> None:
    # Arrange — a residence publishes its identical units side by side
    first = build_listing(source="seloger", price=900.0, surface_m2=58.0, rooms=3)
    second = build_listing(source="seloger", price=900.0, surface_m2=58.0, rooms=3)

    # Act
    groups = group_duplicates([first, second])

    # Assert — re-publication always crosses sources; this is not one
    assert len(groups) == 2


def test_a_rounded_surface_still_matches() -> None:
    # Arrange — "57,6 m²" on one site, "58 m²" on the other
    rounded = build_listing(source="seloger", price=900.0, surface_m2=58.0, rooms=3)
    precise = build_listing(source="laforet", price=900.0, surface_m2=57.6, rooms=3)

    # Act
    groups = group_duplicates([rounded, precise])

    # Assert
    assert len(groups) == 1


def test_a_different_rent_is_a_different_home() -> None:
    # Arrange
    listings = [
        build_listing(source="seloger", price=900.0, surface_m2=58.0, rooms=3),
        build_listing(source="orpi", price=950.0, surface_m2=58.0, rooms=3),
    ]

    # Act
    groups = group_duplicates(listings)

    # Assert
    assert len(groups) == 2


def test_charges_do_not_split_a_group_but_decide_who_leads() -> None:
    # Arrange — same rent, different provisions: the cheaper total leads
    dearer = build_listing(source="seloger", price=900.0, charges=120.0, surface_m2=58.0, rooms=3)
    cheaper = build_listing(source="orpi", price=900.0, charges=60.0, surface_m2=58.0, rooms=3)

    # Act
    groups = group_duplicates([dearer, cheaper])

    # Assert
    assert len(groups) == 1
    assert groups[0].primary.id == cheaper.id


def test_a_listing_without_surface_or_rooms_is_never_grouped() -> None:
    # Arrange — an unknown cannot be a match
    known = build_listing(source="seloger", price=900.0, surface_m2=58.0, rooms=3)
    no_surface = build_listing(source="orpi", price=900.0, rooms=3, surface_m2=None)

    # Act
    groups = group_duplicates([known, no_surface])

    # Assert
    assert len(groups) == 2


def test_a_group_holds_the_place_of_its_first_listing() -> None:
    # Arrange — the caller already sorted; grouping must not reshuffle
    first = build_listing(source="seloger", price=700.0, surface_m2=40.0, rooms=2)
    second = build_listing(source="seloger", price=900.0, surface_m2=58.0, rooms=3)
    second_elsewhere = build_listing(source="orpi", price=900.0, surface_m2=58.0, rooms=3)
    third = build_listing(source="pap", price=1100.0, surface_m2=75.0, rooms=4)

    # Act
    groups = group_duplicates([first, second, second_elsewhere, third])

    # Assert
    assert [group.primary.id for group in groups] == [first.id, second.id, third.id]


def test_a_single_listing_is_a_group_of_one() -> None:
    # Arrange
    alone = build_listing(source="pap", price=880.0, surface_m2=52.0, rooms=2)

    # Act
    groups = group_duplicates([alone])

    # Assert
    assert not groups[0].has_duplicates
    assert groups[0].sources == ("pap",)


@pytest.mark.parametrize(("insee_name", "site_spelling"), _SPELLINGS)
def test_one_commune_spelled_two_ways_still_groups(insee_name: str, site_spelling: str) -> None:
    # Arrange
    on_seloger = build_listing(
        source="seloger", city=insee_name, price=900.0, surface_m2=58.0, rooms=3
    )
    on_laforet = build_listing(
        source="laforet", city=site_spelling, price=900.0, surface_m2=58.0, rooms=3
    )

    # Act
    groups = group_duplicates([on_seloger, on_laforet])

    # Assert
    assert len(groups) == 1


@pytest.mark.parametrize(("insee_name", "site_spelling"), _SPELLINGS)
def test_a_dismissed_home_republished_under_another_spelling_stays_dismissed(
    insee_name: str, site_spelling: str
) -> None:
    # Arrange
    dismissed = build_listing(
        source="seloger", city=insee_name, price=900.0, surface_m2=58.0, rooms=3
    )
    republished = build_listing(
        source="laforet", city=site_spelling, price=900.0, surface_m2=58.0, rooms=3
    )
    dismissals = DismissedHomes(
        [build_dismissal(dismissed, DismissalReason.ASPECT, _fake.date_time_this_year())]
    )

    # Act
    is_hidden = dismissals.is_dismissed(republished)

    # Assert
    assert is_hidden
