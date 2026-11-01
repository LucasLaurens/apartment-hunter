"""Bien'ici parsing, on trimmed answers of the site's own JSON API (2026-11-01)."""

import json
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from faker import Faker

from apartment_hunter.domain.value_objects import DpeRating, Floor, PublicationSource
from apartment_hunter.infrastructure.crawlers.bienici_crawler import (
    BienIciCrawler,
    build_search_square,
    find_city_centre,
    format_polyline,
)

_fake = Faker("fr_FR")
_FIXTURES = Path(__file__).parents[1] / "fixtures" / "bienici"


def _load_ads() -> list[dict[str, Any]]:
    ads: list[dict[str, Any]] = json.loads((_FIXTURES / "realEstateAds.json").read_text())[
        "realEstateAds"
    ]
    return ads


def _build_page(ads: list[dict[str, Any]]) -> str:
    return json.dumps({"total": len(ads), "from": 0, "perPage": 100, "realEstateAds": ads})


def test_a_rented_flat_is_read_field_by_field() -> None:
    # Arrange
    page = _build_page(_load_ads()[1:2])

    # Act
    [listing] = BienIciCrawler().parse_page(page)

    # Assert
    assert listing.url == "https://www.bienici.com/annonce/century-21-202_3154_9825"
    assert listing.source == "bienici"
    assert listing.title == "Appartement 2 pièces Annecy"
    assert listing.location.city == "Annecy"
    assert listing.location.postal_code == "74000"
    assert listing.location.coordinates == (45.90042432977136, 6.122532949504377)
    assert listing.price.total == Decimal(1145)
    assert listing.surface_m2 == 56.82
    assert listing.rooms == 2
    assert listing.floor == Floor.from_int(6)
    assert listing.dpe_rating is DpeRating.C
    assert listing.ges_rating is DpeRating.C
    assert listing.furnished is False
    assert listing.advertiser == "CENTURY 21 CD Immo"
    assert len(listing.images) == 2
    assert listing.published_at == datetime(2026, 10, 23, 0, 14, 28, 630000, tzinfo=UTC)
    assert listing.published_at_source is PublicationSource.SITE


def test_the_price_is_charges_included_and_split_when_the_ad_states_its_charges() -> None:
    # Arrange
    page = _build_page(_load_ads()[:1])

    # Act
    [listing] = BienIciCrawler().parse_page(page)

    # Assert — 2 060 € rent + 200 € charges, published as `price` 2 260
    assert listing.price.amount == Decimal(2060)
    assert listing.price.charges == Decimal(200)
    assert listing.charges_included is True
    assert not listing.charges_unknown


def test_an_ad_stating_no_charges_is_marked_unsettled() -> None:
    # Arrange
    page = _build_page(_load_ads()[2:3])

    # Act
    [listing] = BienIciCrawler().parse_page(page)

    # Assert
    assert listing.price.amount == Decimal(2950)
    assert listing.charges_unknown


def test_a_sale_or_a_house_is_ignored() -> None:
    # Arrange
    flat = _load_ads()[0]
    sale = {**flat, "id": _fake.uuid4(), "adType": "buy"}
    house = {**flat, "id": _fake.uuid4(), "propertyType": "house"}

    # Act
    listings = BienIciCrawler().parse_page(_build_page([sale, house, flat]))

    # Assert
    assert [listing.url for listing in listings] == [
        f"https://www.bienici.com/annonce/{flat['id']}"
    ]


def test_a_city_wide_blur_gives_no_coordinates_of_its_own() -> None:
    # Arrange
    position = {"lat": float(_fake.latitude()), "lon": float(_fake.longitude())}
    ad = {**_load_ads()[0], "blurInfo": {"type": "cityOrArrondissement", "position": position}}

    # Act
    [listing] = BienIciCrawler().parse_page(_build_page([ad]))

    # Assert
    assert listing.location.coordinates is None


def test_the_commune_centre_comes_from_the_suggester_city_entry() -> None:
    # Arrange
    places = json.loads((_FIXTURES / "suggest.json").read_text())

    # Act
    centre = find_city_centre(places, "annecy", "74000")
    elsewhere = find_city_centre(places, "Annecy", "73000")

    # Assert — the commune, not its delegated city of the same name
    assert centre == (
        (45.828002368597154 + 45.97669279087877) / 2,
        (6.048412054366711 + 6.204393184681487) / 2,
    )
    assert elsewhere is None


def test_the_polyline_matches_google_s_reference_encoding() -> None:
    # Act & Assert
    assert (
        format_polyline([(38.5, -120.2), (40.7, -120.95), (43.252, -126.453)])
        == "_p~iF~ps|U_ulLnnqC_mqNvxq`@"
    )


def test_the_search_square_is_a_closed_ring_around_the_centre() -> None:
    # Arrange
    lat, lon = float(_fake.latitude()) / 2, float(_fake.longitude())
    radius_km = _fake.random_int(1, 150)

    # Act
    ring = build_search_square(lat, lon, radius_km)

    # Assert
    assert ring[0] == ring[-1]
    assert len(ring) == 5
    assert min(p[0] for p in ring) < lat < max(p[0] for p in ring)
    assert min(p[1] for p in ring) < lon < max(p[1] for p in ring)
