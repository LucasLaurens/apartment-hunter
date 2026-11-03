"""Agence BFM, read from trimmed copies of its own pages: never the network."""

import base64
import json
from decimal import Decimal
from pathlib import Path

from faker import Faker

from apartment_hunter.domain.value_objects import DpeRating, PublicationSource
from apartment_hunter.infrastructure.crawlers.agence_bfm_crawler import (
    AgenceBfmCrawler,
    read_reference,
)

_FIXTURES = Path(__file__).parent.parent / "fixtures" / "bfm"
fake = Faker("fr_FR")


def _read(name: str) -> str:
    return (_FIXTURES / name).read_text(encoding="utf-8")


def _encode_page(record: dict[str, object]) -> str:
    """A page carrying one record, encoded the way Netty ships its state."""
    state = base64.b64encode(json.dumps({"prodId": {"LA1": record}}).encode()).decode()
    return f'<script>window._TEMPLATE_DATA = JSON.parse(b64_to_utf8("{state}"));</script>'


def test_an_apartment_record_is_mapped_field_by_field() -> None:
    # Act
    listings = {
        listing.location.city: listing
        for listing in AgenceBfmCrawler().parse_page(_read("list.html"))
    }

    # Assert — 996 € rent plus a 110 € provision: the total is settled
    t2 = listings["Annecy"]
    assert t2.url == (
        "https://www.agencebfm-immo.com/location/appartement-t2-2-pieces-annecy-74000,LA4396"
    )
    assert (t2.location.postal_code, t2.location.has_coordinates) == ("74000", True)
    assert (t2.price.amount, t2.price.charges, t2.price.total) == (
        Decimal(996),
        Decimal(110),
        Decimal(1106),
    )
    assert not t2.charges_unknown
    assert (t2.surface_m2, t2.rooms) == (55.09, 2)
    assert t2.floor is not None and t2.floor.level == 2
    assert t2.published_at_source is PublicationSource.SITE
    assert t2.published_at.date().isoformat() == "2026-10-12"
    assert t2.advertiser == "Agence BFM"
    assert t2.images and t2.images[0].startswith("https://img.netty.immo/")


def test_a_rent_printed_without_provision_keeps_its_charges_unknown() -> None:
    # Act
    listings = {
        listing.location.city: listing
        for listing in AgenceBfmCrawler().parse_page(_read("list.html"))
    }

    # Assert — « 847.17 € /mois HC », no provision: never shown as charges comprises
    rumilly = listings["Rumilly"]
    assert rumilly.price.amount == Decimal("847.17")
    assert rumilly.charges_unknown


def test_parkings_and_houses_are_left_out() -> None:
    # Act
    cities = sorted(
        listing.location.city for listing in AgenceBfmCrawler().parse_page(_read("list.html"))
    )

    # Assert — the fixture also holds a garage in Annecy and a house in Epagny Metz-Tessy
    assert cities == ["Annecy", "Rumilly"]


def test_a_storey_of_zero_is_unknown_not_ground_floor() -> None:
    # Arrange — Netty writes 0 in every field nobody filled
    page = _encode_page(
        {
            "prod_ref": "LA1",
            "prod_type": "appt",
            "type_offer": 2,
            "city": fake.city(),
            "rent_total": fake.random_int(500, 2000),
            "floor": 0,
            "floors": fake.random_int(1, 8),
        }
    )

    # Act
    (listing,) = AgenceBfmCrawler().parse_page(page)

    # Assert
    assert listing.floor is None


def test_a_record_naming_no_commune_is_dropped() -> None:
    # Arrange
    page = _encode_page(
        {"prod_ref": "LA1", "prod_type": "appt", "type_offer": 2, "rent_total": 900}
    )

    # Act & Assert
    assert AgenceBfmCrawler().parse_page(page) == []


def test_the_detail_page_adds_energy_classes_from_its_legal_mention() -> None:
    # Act
    details = AgenceBfmCrawler.parse_details(_read("detail_t2.html"), "LA4396")

    # Assert — « Classe énergie D, Classe climat D »
    assert (details.dpe_rating, details.ges_rating) == (DpeRating.D, DpeRating.D)


def test_a_page_without_state_settles_nothing() -> None:
    # Act
    details = AgenceBfmCrawler.parse_details("<html><body></body></html>", "LA4396")

    # Assert
    assert (details.dpe_rating, details.ges_rating) == (None, None)
    assert AgenceBfmCrawler().parse_page("<html><body></body></html>") == []


def test_the_reference_is_read_from_the_end_of_the_url() -> None:
    # Act & Assert
    assert (
        read_reference(
            "https://www.agencebfm-immo.com/location/appartement-t2-2-pieces-annecy-74000,LA4396"
        )
        == "LA4396"
    )
