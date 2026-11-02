"""Position au marché against the Carte des loyers (ADR-0010, ticket 05)."""

from dataclasses import replace
from decimal import Decimal

import pytest
from faker import Faker

from apartment_hunter.domain.entities import Listing
from apartment_hunter.domain.services import RentReferenceBook
from apartment_hunter.domain.value_objects import (
    MarketPosition,
    NoMarketPosition,
    NoPositionReason,
    Price,
    RentReference,
    RentSegment,
)
from apartment_hunter.domain.value_objects.market_position import (
    WEAK_OBSERVATIONS,
    WEAK_R2_ADJUSTED,
)
from tests.fakes.builders import build_listing

_fake = Faker()


def _build_reference(
    segment: RentSegment = RentSegment.ONE_TWO_ROOMS,
    per_m2: str = "20.00",
    observed: int = 1000,
    r2_adjusted: float = 0.8,
) -> RentReference:
    return RentReference(
        commune="Annecy",
        segment=segment,
        per_m2=Decimal(per_m2),
        lower_per_m2=Decimal("15.00"),
        upper_per_m2=Decimal("28.00"),
        observed_in_commune=observed,
        r2_adjusted=r2_adjusted,
        vintage=2025,
    )


def _build_book(*references: RentReference) -> RentReferenceBook:
    return RentReferenceBook({"Annecy": {ref.segment: ref for ref in references}})


def _build_comparable(price: float, surface_m2: float, rooms: int = 2) -> Listing:
    return build_listing(
        city="Annecy", price=price, surface_m2=surface_m2, rooms=rooms, charges_included=True
    )


def test_a_rent_under_the_reference_reads_as_a_negative_gap() -> None:
    # Arrange — 880 € for 50 m² is 17.60 €/m² against 20.00
    listing = _build_comparable(price=880.0, surface_m2=50.0)

    # Act
    position = _build_book(_build_reference()).assess(listing)

    # Assert
    assert isinstance(position, MarketPosition)
    assert position.gap_percent == -12
    assert position.format_label() == "−12 % vs réf."


def test_a_rent_outside_the_prediction_interval_says_so() -> None:
    # Arrange — 600 € for 50 m² is 12 €/m², under the 15 €/m² lower bound
    listing = _build_comparable(price=600.0, surface_m2=50.0)

    # Act
    position = _build_book(_build_reference()).assess(listing)

    # Assert
    assert isinstance(position, MarketPosition)
    assert position.is_outside_range
    assert position.format_label().endswith("vs réf. · hors fourchette")


@pytest.mark.parametrize(
    ("observed", "r2_adjusted"),
    [(WEAK_OBSERVATIONS - 1, 0.8), (1000, WEAK_R2_ADJUSTED - 0.01)],
)
def test_a_reference_the_producer_calls_fragile_is_marked_weak(
    observed: int, r2_adjusted: float
) -> None:
    # Arrange
    listing = _build_comparable(price=1000.0, surface_m2=50.0)
    book = _build_book(_build_reference(observed=observed, r2_adjusted=r2_adjusted))

    # Act
    label = book.assess(listing).format_label()

    # Assert
    assert label.endswith("(repère faible)")


@pytest.mark.parametrize(
    ("rooms", "segment"),
    [
        (1, RentSegment.ONE_TWO_ROOMS),
        (2, RentSegment.ONE_TWO_ROOMS),
        (3, RentSegment.THREE_PLUS_ROOMS),
        (5, RentSegment.THREE_PLUS_ROOMS),
        (None, RentSegment.ALL_APARTMENTS),
    ],
)
def test_the_segment_follows_the_number_of_rooms(rooms: int | None, segment: RentSegment) -> None:
    # Arrange
    listing = replace(_build_comparable(price=1000.0, surface_m2=50.0), rooms=rooms)
    book = _build_book(*(_build_reference(segment=s) for s in RentSegment))

    # Act
    position = book.assess(listing)

    # Assert
    assert isinstance(position, MarketPosition)
    assert position.reference.segment is segment


def test_reasons_are_checked_in_order_furnished_charges_surface_commune() -> None:
    # Arrange — each listing also fails every later check
    book = _build_book(_build_reference())
    nothing_known = build_listing(city=_fake.city(), surface_m2=None, rooms=2)
    furnished = replace(nothing_known, furnished=True)
    charges_unknown = nothing_known
    no_surface = replace(nothing_known, charges_included=True)
    absent = replace(no_surface, surface_m2=float(_fake.random_int(20, 90)))

    # Act
    reasons = [book.assess(x) for x in (furnished, charges_unknown, no_surface, absent)]

    # Assert
    assert reasons == [
        NoMarketPosition(NoPositionReason.FURNISHED),
        NoMarketPosition(NoPositionReason.CHARGES_UNKNOWN),
        NoMarketPosition(NoPositionReason.NO_SURFACE),
        NoMarketPosition(NoPositionReason.COMMUNE_ABSENT),
    ]
    assert reasons[0].format_label() == "pas de repère (meublé)"


def test_a_missing_segment_is_no_position_never_a_wider_one() -> None:
    # Arrange — the commune has a T3+ reference only
    listing = _build_comparable(price=900.0, surface_m2=40.0, rooms=2)
    book = _build_book(_build_reference(segment=RentSegment.THREE_PLUS_ROOMS))

    # Act
    position = book.assess(listing)

    # Assert
    assert position == NoMarketPosition(NoPositionReason.COMMUNE_ABSENT)


def test_an_unreadable_map_blames_the_map_not_the_commune() -> None:
    # Arrange
    listing = _build_comparable(price=900.0, surface_m2=40.0)

    # Act
    position = RentReferenceBook.build_unavailable().assess(listing)

    # Assert
    assert position == NoMarketPosition(NoPositionReason.MAP_UNAVAILABLE)


def test_the_commune_is_found_whatever_the_site_spelling() -> None:
    # Arrange
    listing = replace(
        _build_comparable(price=900.0, surface_m2=40.0),
        location=replace(build_listing().location, city="ANNECY"),
    )

    # Act
    position = _build_book(_build_reference()).assess(listing)

    # Assert
    assert isinstance(position, MarketPosition)


def test_charges_included_through_a_provision_are_comparable() -> None:
    # Arrange — a provision makes the total settled, so the listing is comparable
    listing = replace(
        build_listing(city="Annecy", price=800.0, surface_m2=45.0, rooms=2),
        price=Price(amount=Decimal("800"), charges=Decimal(_fake.random_int(30, 90))),
    )

    # Act
    position = _build_book(_build_reference()).assess(listing)

    # Assert
    assert isinstance(position, MarketPosition)


def test_homes_without_a_reference_sort_after_every_positioned_home() -> None:
    # Arrange
    book = _build_book(_build_reference())
    expensive = book.assess(_build_comparable(price=1400.0, surface_m2=50.0))
    unknown = book.assess(build_listing(city="Annecy", surface_m2=None))

    # Act
    ordered = sorted([unknown, expensive], key=lambda p: p.sort_key)

    # Assert
    assert ordered == [expensive, unknown]
