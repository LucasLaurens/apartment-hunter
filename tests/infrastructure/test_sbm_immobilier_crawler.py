"""SBM Immobilier, read from trimmed copies of its own pages: never the network."""

from decimal import Decimal
from pathlib import Path

from apartment_hunter.domain.value_objects import DpeRating, PublicationSource
from apartment_hunter.infrastructure.crawlers.sbm_immobilier_crawler import (
    SbmImmobilierCrawler,
    build_list_page_url,
    has_next_page,
)

_FIXTURES = Path(__file__).parent.parent / "fixtures" / "sbm"


def _read(name: str) -> str:
    return (_FIXTURES / name).read_text(encoding="utf-8")


def test_an_apartment_card_is_mapped_field_by_field() -> None:
    # Arrange
    crawler = SbmImmobilierCrawler()

    # Act
    listings = {
        listing.title: listing for listing in crawler.parse_page(_read("list_first_page.html"))
    }

    # Assert
    t2 = listings["T2"]
    assert t2.url == "https://www.sbm-immo.com/bien/t2-01010006658-c-74000/"
    assert (t2.location.city, t2.location.postal_code) == ("Annecy", "74000")
    assert t2.location.has_coordinates
    assert t2.price.amount == Decimal(1330)
    assert (t2.surface_m2, t2.rooms) == (57.0, 2)
    assert t2.published_at_source is PublicationSource.SITE
    assert t2.published_at.date().isoformat() == "2026-10-28"
    assert t2.advertiser == "SBM Immobilier"
    assert t2.images and t2.images[0].startswith("https://www.sbm-immo.com/wp-content/")


def test_a_garage_is_left_out_and_an_untyped_apartment_kept() -> None:
    # Act
    titles = [
        listing.title
        for listing in SbmImmobilierCrawler().parse_page(_read("list_first_page.html"))
    ]

    # Assert — « Stationnement » is not a home; « APPARTEMENT » with no T-type still is
    assert sorted(titles) == ["APPARTEMENT", "T2"]


def test_the_walk_stops_on_the_page_without_a_next_link() -> None:
    # Act & Assert
    assert has_next_page(_read("list_first_page.html"))
    assert not has_next_page(_read("list_last_page.html"))
    assert build_list_page_url(1) == "https://www.sbm-immo.com/locations-immobilieres/"
    assert build_list_page_url(3) == "https://www.sbm-immo.com/locations-immobilieres/page/3/"


def test_the_detail_page_adds_energy_storey_furnishing_and_settled_charges() -> None:
    # Act
    details = SbmImmobilierCrawler.parse_details(_read("detail_t2.html"))

    # Assert — the card's 1 330 € is 1 200 € rent plus a 130 € provision
    assert (details.dpe_rating, details.ges_rating) == (DpeRating.D, DpeRating.D)
    assert details.floor is not None and details.floor.level == 4
    assert details.furnished is True
    assert details.charges_included is True


def test_a_detail_page_without_its_json_ld_settles_nothing() -> None:
    # Act
    details = SbmImmobilierCrawler.parse_details("<html><body></body></html>")

    # Assert — unknown stays unknown, never « hors charges » nor « non meublé »
    assert details.charges_included is None
    assert details.furnished is None
    assert details.floor is None
