"""2A Immobilier parsing, on trimmed copies of the site's own pages (2026-11-01).

`list_first_page.html` keeps four cards of page 1 (a cellar, a shop, two apartments) and
its pager; `list_last_page.html` two parking cards and the pager of the last page;
`detail_ref_7942.html` the facts table and energy labels of one apartment.
"""

from decimal import Decimal
from pathlib import Path

from faker import Faker

from apartment_hunter.domain.entities import SearchFilter
from apartment_hunter.domain.services import AdvertiserKind, detect_advertiser_kind
from apartment_hunter.domain.value_objects import DpeRating, Floor
from apartment_hunter.infrastructure.crawlers.twoa_immobilier_crawler import (
    TwoAImmobilierCrawler,
    build_list_page_url,
    has_next_page,
)

_fake = Faker("fr_FR")
_FIXTURES = Path(__file__).parents[1] / "fixtures" / "2a_immobilier"
_ANNECY_FLAT = (
    "https://www.2a-immo.fr/location/appartement/annecy/"
    "location-appartement-annecy-2-pieces-44-m2-ref-7942"
)


def _read_fixture(name: str) -> str:
    return (_FIXTURES / name).read_text()


class _FixtureSite(TwoAImmobilierCrawler):
    """The crawler served by a dict of pages instead of the network."""

    RATE_LIMIT_SECONDS = 0.0

    def __init__(self, pages: dict[str, str]) -> None:
        super().__init__()
        self.pages = pages
        self.requested: list[str] = []

    async def _fetch_html(self, url: str) -> str | None:
        self.requested.append(url)
        return self.pages.get(url)


def test_an_apartment_card_is_read_field_by_field() -> None:
    # Arrange
    html = _read_fixture("list_first_page.html")

    # Act
    listings = TwoAImmobilierCrawler().parse_page(html)

    # Assert
    flat = next(listing for listing in listings if listing.url == _ANNECY_FLAT)
    assert flat.source == "2a-immobilier"
    assert flat.title == "Appartement 2 pièces - 44 m²"
    assert flat.location.city == "Annecy"
    assert flat.location.postal_code is None
    assert flat.price.amount == Decimal(1135)
    assert flat.charges_included is True
    assert flat.surface_m2 == 44.0
    assert flat.rooms == 2
    assert flat.furnished is True
    assert flat.advertiser == "2A Immobilier"
    assert flat.images == (
        "https://www.2a-immo.fr/sites/2a-immo.fr/files/styles/medium/public/realestate/"
        "photos/2026-11/location-appartement-annecy-ref-7942.jpg?itok=W4VQMqS8",
    )


def test_a_card_without_the_furnished_ribbon_says_nothing_about_furnishing() -> None:
    # Arrange
    html = _read_fixture("list_first_page.html")

    # Act
    listings = TwoAImmobilierCrawler().parse_page(html)

    # Assert — Villaz has no ribbon: unknown, never read as unfurnished
    villaz = next(listing for listing in listings if listing.location.city == "Villaz")
    assert villaz.furnished is None
    assert villaz.price.amount == Decimal(930)


def test_cellars_and_shops_are_dropped() -> None:
    # Arrange — the page holds a cellar, a shop and two apartments
    html = _read_fixture("list_first_page.html")

    # Act
    listings = TwoAImmobilierCrawler().parse_page(html)

    # Assert
    assert len(listings) == 2
    assert all("/location/appartement/" in listing.url for listing in listings)


def test_a_page_of_parkings_yields_nothing() -> None:
    # Act & Assert
    assert TwoAImmobilierCrawler().parse_page(_read_fixture("list_last_page.html")) == []


def test_only_the_last_page_has_no_next_link() -> None:
    # Act & Assert
    assert has_next_page(_read_fixture("list_first_page.html"))
    assert not has_next_page(_read_fixture("list_last_page.html"))


async def test_the_walk_stops_on_the_last_page() -> None:
    # Arrange — past its end the site serves its last page again, so a page
    # beyond it must never be asked for
    list_pages = [build_list_page_url(page) for page in range(3)]
    crawler = _FixtureSite(
        {
            list_pages[0]: _read_fixture("list_first_page.html"),
            list_pages[1]: _read_fixture("list_last_page.html"),
            list_pages[2]: _read_fixture("list_first_page.html"),
        }
    )
    search_filter = SearchFilter(id=_fake.uuid4(), name=_fake.word(), cities=[_fake.city()])

    # Act
    listings = await crawler.fetch(search_filter)

    # Assert
    assert [url for url in crawler.requested if url in list_pages] == list_pages[:2]
    assert len(listings) == 2


def test_the_detail_page_adds_the_dpe_and_the_storey() -> None:
    # Arrange
    html = _read_fixture("detail_ref_7942.html")

    # Act
    details = TwoAImmobilierCrawler.parse_details(html)

    # Assert — the GES scale is drawn on A whatever the home: never read
    assert details.dpe_rating == DpeRating.C
    assert details.ges_rating is None
    assert details.floor == Floor.from_int(6)
    assert details.published_at is None


def test_an_unstated_storey_is_not_read_from_the_availability_date() -> None:
    # Arrange — the site's own wording when the storey is unknown
    available = _fake.future_date().strftime("%d/%m/%Y")
    html = (
        '<div class="infos">'
        f'<div class="info">Disponibilité : {available}</div>'
        '<div class="info">Etage : N.C.</div>'
        "</div>"
    )

    # Act
    details = TwoAImmobilierCrawler.parse_details(html)

    # Assert
    assert details.floor is None


def test_a_detail_page_without_labels_keeps_them_unknown() -> None:
    # Arrange
    html = f"<html><body><p>{_fake.sentence()}</p></body></html>"

    # Act
    details = TwoAImmobilierCrawler.parse_details(html)

    # Assert
    assert details.dpe_rating is None
    assert details.ges_rating is None
    assert details.floor is None


def test_the_source_is_an_agency_and_only_runs_with_the_rules_ignored() -> None:
    # Arrange
    crawler = TwoAImmobilierCrawler()

    # Act
    kind = detect_advertiser_kind(crawler.source_name, None)

    # Assert
    assert kind is AdvertiserKind.AGENCY
    assert crawler.forbids_reproduction is True
