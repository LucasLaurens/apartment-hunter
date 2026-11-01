"""FNAIM parsing, on trimmed copies of the site's own pages (Annecy, 2026-11-01)."""

from decimal import Decimal
from pathlib import Path

from faker import Faker

from apartment_hunter.domain.services import AdvertiserKind, detect_advertiser_kind
from apartment_hunter.domain.value_objects import DpeRating
from apartment_hunter.infrastructure.crawlers.fnaim_crawler import (
    FnaimCrawler,
    build_search_url,
)

_fake = Faker("fr_FR")
_FIXTURES = Path(__file__).parents[1] / "fixtures" / "fnaim"
_DEPARTMENT = "74"
_FIRST_CARD_URL = (
    "https://www.fnaim.fr/annonce-immobiliere/52208933/18-location-appartement-annecy-74000.htm"
)


def _read_fixture(name: str) -> str:
    return (_FIXTURES / name).read_text(encoding="utf-8")


def test_a_card_is_read_field_by_field() -> None:
    # Arrange
    html = _read_fixture("list_annecy.html")

    # Act
    listings = FnaimCrawler().parse_page(html, _DEPARTMENT)

    # Assert
    listing = next(item for item in listings if item.url == _FIRST_CARD_URL)
    assert listing.source == "fnaim"
    assert (listing.location.city, listing.location.postal_code) == ("Annecy", "74000")
    assert listing.price.amount == Decimal(807)
    assert listing.charges_unknown  # the card says "par mois", never CC or HC
    assert (listing.surface_m2, listing.rooms) == (27.0, 1)
    assert listing.floor is not None and listing.floor.level == 2
    assert listing.furnished is None  # no "Meublé" chip: unknown, not unfurnished
    assert len(listing.images) == 3


def test_the_agency_printed_on_the_card_is_the_advertiser() -> None:
    # Arrange
    html = _read_fixture("list_annecy.html")

    # Act
    [listing] = [
        item for item in FnaimCrawler().parse_page(html, _DEPARTMENT) if item.url == _FIRST_CARD_URL
    ]

    # Assert
    assert listing.advertiser == "ENTRE 2 LACS IMMOBILIER"
    assert detect_advertiser_kind(listing.source, listing.advertiser) is AdvertiserKind.AGENCY


def test_a_furnished_chip_marks_the_listing_furnished_and_teasers_are_skipped() -> None:
    # Arrange
    html = _read_fixture("list_annecy.html")

    # Act
    listings = FnaimCrawler().parse_page(html, _DEPARTMENT)

    # Assert — three listing cards; the advice-article teaser carries no listing link.
    assert len(listings) == 3
    assert [item.furnished for item in listings].count(True) == 2


def test_a_card_from_another_department_is_dropped() -> None:
    # Arrange
    postal = next(code for code in iter(_fake.postcode, None) if not code.startswith(_DEPARTMENT))
    city = _fake.city().upper()
    html = _read_fixture("list_annecy.html").replace("74000", postal).replace("ANNECY", city)

    # Act
    listings = FnaimCrawler().parse_page(html, _DEPARTMENT)

    # Assert
    assert listings == []


def test_pages_are_addressed_as_the_site_paginates() -> None:
    # Arrange
    page = _fake.random_int(2, 9)
    base = "https://www.fnaim.fr/liste-annonces-immobilieres/18-location-appartement"

    # Act & Assert
    assert build_search_url("Annecy", "74000", 1) == f"{base}-annecy-74000.htm"
    assert build_search_url("Saint-Jorioz", "74410", page) == (
        f"{base}-saint-jorioz-74410-page-{page}.htm"
    )


def test_the_detail_page_adds_energy_and_storey() -> None:
    # Arrange
    html = _read_fixture("detail.html")

    # Act
    details = FnaimCrawler.parse_details(html)

    # Assert
    assert (details.dpe_rating, details.ges_rating) == (DpeRating.D, DpeRating.B)
    assert details.floor is not None and details.floor.level == 2
    assert details.published_at is None
