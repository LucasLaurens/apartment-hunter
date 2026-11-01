"""Locservice parsing, on trimmed pages saved from the site on 2026-11-01.

`annecy-p1.html` holds three cards of the Annecy page — an Annecy owner's T2, a partner
agency's T4, a Poisy neighbour — and the Arith card of page 2 (Savoie, 19 km away).
`annecy-p3.html` is the last page, which the site also serves for any page past it.
"""

from decimal import Decimal
from pathlib import Path

from faker import Faker

from apartment_hunter.domain.value_objects import DpeRating
from apartment_hunter.infrastructure.crawlers.base_crawler import merge_details
from apartment_hunter.infrastructure.crawlers.locservice_crawler import (
    LocserviceCrawler,
    build_page_url,
    build_search_url,
)

_fake = Faker("fr_FR")
_FIXTURES = Path(__file__).parents[1] / "fixtures" / "locservice"
_FIRST_PAGE = "https://www.locservice.fr/haute-savoie-74/location-appartement-annecy.html"


def _read_fixture(name: str) -> str:
    return (_FIXTURES / name).read_text(encoding="utf-8")


class ScriptedLocserviceCrawler(LocserviceCrawler):
    """Locservice without the network: page 1, then the last page for any page after it."""

    def __init__(self) -> None:
        super().__init__()
        self.requested: list[str] = []

    async def _fetch_html(self, url: str) -> str | None:
        self.requested.append(url)
        return _read_fixture("annecy-p1.html" if url == _FIRST_PAGE else "annecy-p3.html")


def test_an_owner_card_is_read_field_by_field() -> None:
    # Arrange
    html = _read_fixture("annecy-p1.html")

    # Act
    listing = LocserviceCrawler().parse_page(html)[0]

    # Assert
    assert (
        listing.url
        == "https://www.locservice.fr/haute-savoie-74/location-appartement-annecy/2497833"
    )
    assert listing.source == "locservice"
    assert listing.title == "Appartement T2 meublé à louer"
    assert listing.location.city == "Annecy"
    assert listing.location.postal_code == "74000"
    assert listing.price.amount == Decimal(1350)
    assert listing.surface_m2 == 53.0
    assert listing.rooms == 2
    assert listing.furnished is True
    assert listing.charges_unknown  # the card prints a bare rent
    assert listing.description and listing.description.endswith("…")
    assert listing.images and listing.images[0].startswith("https://img.locservice.fr/")
    assert listing.advertiser is None


def test_a_partner_agency_card_is_left_out() -> None:
    # Arrange
    html = _read_fixture("annecy-p1.html")

    # Act
    listings = LocserviceCrawler().parse_page(html)

    # Assert — three owners' cards remain of four
    assert len(listings) == 3
    assert not [listing for listing in listings if "/p-cf-" in listing.url]


def test_a_neighbour_across_the_department_border_is_kept() -> None:
    # Arrange — the page lists neighbours within ~20 km, not national filler: the radius
    # is the matcher's call, and Arith (Savoie) is 19 km from Annecy
    html = _read_fixture("annecy-p1.html")

    # Act
    postal_codes = [
        listing.location.postal_code for listing in LocserviceCrawler().parse_page(html)
    ]

    # Assert
    assert postal_codes == ["74000", "74330", "73340"]


async def test_pagination_stops_when_the_last_page_comes_back() -> None:
    # Arrange
    crawler = ScriptedLocserviceCrawler()

    # Act
    listings = await crawler.fetch_listing_pages(_FIRST_PAGE, label=_fake.city())

    # Assert — page 3 is the redirect target of page 2's successor: nothing new, stop
    assert crawler.requested == [
        _FIRST_PAGE,
        build_page_url(_FIRST_PAGE, 2),
        build_page_url(_FIRST_PAGE, 3),
    ]
    assert len(listings) == 5


def test_the_search_url_spells_department_and_saint_as_the_site_does() -> None:
    # Act
    url = build_search_url("Saint-Jorioz", "74", "Haute-Savoie")

    # Assert
    assert url == "https://www.locservice.fr/haute-savoie-74/location-appartement-st-jorioz.html"
    assert build_page_url(url, 2).endswith("/location-appartement-st-jorioz-p2.html")


def test_the_detail_page_adds_energy_furnishing_and_settles_the_charges() -> None:
    # Arrange
    card = LocserviceCrawler().parse_page(_read_fixture("annecy-p1.html"))[1]

    # Act
    details = LocserviceCrawler.parse_details(_read_fixture("detail-2605307.html"))
    listing = merge_details(card, details)

    # Assert
    assert details.dpe_rating == DpeRating.from_string("C")
    assert details.ges_rating == DpeRating.from_string("C")
    assert details.furnished is True
    assert details.floor is None  # "rez de jardin" names no storey
    assert listing.charges_included is True
    assert not listing.charges_unknown
