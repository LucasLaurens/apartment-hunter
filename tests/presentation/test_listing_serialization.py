"""The web payload must carry every mark the glossary says a card owes its reader."""

from dataclasses import replace
from datetime import date, datetime
from decimal import Decimal

from faker import Faker

from apartment_hunter.domain.services import (
    AdvertiserKind,
    RentReferenceBook,
    build_dismissal,
    group_duplicates,
)
from apartment_hunter.domain.value_objects import (
    DismissalReason,
    DpeRating,
    RentReference,
    RentSegment,
)
from apartment_hunter.presentation.web.serializers import group_to_dict, listing_to_dict

from ..fakes.builders import build_listing


def test_an_unsettled_total_is_flagged() -> None:
    # Arrange
    listing = build_listing(price=800.0)

    # Act
    payload = listing_to_dict(listing)

    # Assert
    assert payload["charges_unknown"] is True


def test_a_settled_total_is_not_flagged() -> None:
    # Arrange
    listing = build_listing(price=800.0, charges=95.0)

    # Act
    payload = listing_to_dict(listing)

    # Assert
    assert payload["charges_unknown"] is False


def test_a_thermal_sieve_carries_its_dated_warning() -> None:
    # Arrange
    listing = build_listing(dpe="G")

    # Act
    payload = listing_to_dict(listing, today=date(2026, 3, 1))

    # Assert
    assert payload["rental_ban_warning"] == (
        "Passoire thermique — location interdite depuis le 01/01/2025"
    )


def test_a_decent_rating_carries_no_warning() -> None:
    # Arrange
    listing = build_listing(dpe="C")

    # Act
    payload = listing_to_dict(listing, today=date(2026, 3, 1))

    # Assert — empty string, so the card can print it without a null check
    assert payload["rental_ban_warning"] == ""


def test_the_advertiser_kind_travels_with_the_listing() -> None:
    # Arrange
    listing = build_listing(source="pap")

    # Act
    payload = listing_to_dict(listing)

    # Assert
    assert payload["advertiser_kind"] == AdvertiserKind.PRIVATE.value


def test_the_opened_state_travels_with_the_listing() -> None:
    # Arrange
    listing = build_listing()

    # Act
    fresh = listing_to_dict(listing)
    read = listing_to_dict(replace(listing, opened_at=listing.fetched_at))

    # Assert — this is what the "Nouveau" badge reads, not the arrival order
    assert fresh["opened"] is False
    assert read["opened"] is True


def test_an_unknown_rating_serialises_as_no_rating_and_no_warning() -> None:
    # Arrange
    listing = build_listing(dpe=None)

    # Act
    payload = listing_to_dict(listing, today=date(2026, 3, 1))

    # Assert
    assert payload["dpe_rating"] is None
    assert payload["rental_ban_warning"] == ""
    assert DpeRating.G.value not in str(payload["rental_ban_warning"])


def test_a_group_carries_its_duplicates_whole() -> None:
    # Arrange — one home, two sources
    on_seloger = build_listing(source="seloger", price=900.0, surface_m2=58.0, rooms=3)
    on_orpi = build_listing(source="orpi", price=900.0, surface_m2=58.0, rooms=3)

    # Act
    payload = group_to_dict(group_duplicates([on_seloger, on_orpi])[0])

    # Assert — every duplicate keeps its own link, so a wrong grouping is reversible
    assert payload["sources"] == ["seloger", "orpi"]
    assert [other["url"] for other in payload["also_on"]] == [on_orpi.url]


def test_a_lone_listing_serialises_with_no_duplicates() -> None:
    # Arrange
    alone = build_listing(source="pap", price=880.0, surface_m2=52.0, rooms=2)

    # Act
    payload = group_to_dict(group_duplicates([alone])[0])

    # Assert
    assert payload["also_on"] == []
    assert payload["sources"] == ["pap"]


def test_the_network_travels_with_the_listing() -> None:
    # Arrange
    listing = build_listing(source="seloger", advertiser="Laforêt Annecy")

    # Act
    payload = listing_to_dict(listing)

    # Assert
    assert payload["network"] == "Laforêt"


def test_a_listing_of_a_down_source_carries_its_doubt() -> None:
    # Arrange
    listing = replace(build_listing(), source_down_days=3)

    # Act
    payload = listing_to_dict(listing)

    # Assert
    assert "3 j" in payload["source_down_warning"]


def test_a_listing_of_an_answering_source_carries_no_doubt() -> None:
    # Act & Assert
    assert listing_to_dict(build_listing())["source_down_warning"] == ""


def test_a_card_carries_the_position_and_the_reference_it_was_measured_against() -> None:
    # Arrange — 600 € for 50 m² against a 20 €/m² reference whose interval starts at 15
    reference = RentReference(
        commune="Annecy",
        segment=RentSegment.ONE_TWO_ROOMS,
        per_m2=Decimal("20"),
        lower_per_m2=Decimal("15"),
        upper_per_m2=Decimal("28"),
        observed_in_commune=Faker().random_int(100, 5000),
        r2_adjusted=0.8,
        vintage=2025,
    )
    listing = build_listing(price=600.0, surface_m2=50.0, rooms=2, charges_included=True)
    book = RentReferenceBook({"Annecy": {RentSegment.ONE_TWO_ROOMS: reference}})

    # Act
    payload = listing_to_dict(book.annotate([listing])[0])

    # Assert
    assert payload["market_position"]["label"].endswith("vs réf. · hors fourchette")
    assert payload["market_position"]["outside_range"] is True
    assert payload["market_position"]["reference"].startswith("Annecy, T1-T2")


def test_a_card_without_a_reference_says_why() -> None:
    # Arrange
    listing = build_listing(surface_m2=None, charges_included=True)

    # Act
    payload = listing_to_dict(RentReferenceBook({}).annotate([listing])[0])

    # Assert
    assert payload["market_position"] == {
        "label": "pas de repère (sans surface)",
        "outside_range": False,
        "reference": "",
    }


def test_a_home_back_at_another_rent_carries_its_former_dismissal() -> None:
    # Arrange
    dismissal = build_dismissal(build_listing(), DismissalReason.TOO_EXPENSIVE, datetime.now())
    listing = build_listing()

    # Act
    fresh = listing_to_dict(listing)
    back = listing_to_dict(replace(listing, former_dismissal=dismissal))

    # Assert
    assert fresh["former_dismissal"] == ""
    assert back["former_dismissal"] == dismissal.format_mention()
