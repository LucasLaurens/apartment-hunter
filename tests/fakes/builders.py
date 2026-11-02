"""Test data builders — use faker, never hardcode."""

from datetime import datetime, timedelta
from decimal import Decimal

from faker import Faker

from apartment_hunter.domain.entities import (
    DEFAULT_MAX_RESULTS,
    DEFAULT_NOTIFICATION_INTERVAL_MINUTES,
    DEFAULT_REFRESH_INTERVAL_MINUTES,
    Listing,
    SearchFilter,
)
from apartment_hunter.domain.value_objects import DpeRating, Floor, Location, Price
from apartment_hunter.infrastructure.crawlers.base_crawler import build_listing_id

_fake = Faker("fr_FR")


def build_listing(
    *,
    city: str = "Annecy",
    postal_code: str | None = None,
    price: float = 900.0,
    surface_m2: float | None = 55.0,
    rooms: int | None = 3,
    floor_level: int = 2,
    is_top: bool = False,
    dpe: str | None = "C",
    furnished: bool | None = None,
    published_offset_minutes: int = 0,
    source: str = "fake",
    advertiser: str | None = None,
    title: str | None = None,
    description: str | None = None,
    charges: float | None = None,
    charges_included: bool | None = None,
) -> Listing:
    url = f"https://fake.fr/{_fake.uuid4()}"
    return Listing(
        id=build_listing_id(url),
        url=url,
        title=title if title is not None else f"Appartement {rooms}p {surface_m2}m²",
        description=description,
        source=source,
        location=Location(
            city=city,
            postal_code=postal_code,
            latitude=45.9 + _fake.pyfloat(min_value=-0.1, max_value=0.1),
            longitude=6.1,
        ),
        price=Price(
            amount=Decimal(str(price)),
            charges=Decimal(str(charges)) if charges is not None else None,
        ),
        charges_included=charges_included,
        surface_m2=surface_m2,
        rooms=rooms,
        floor=Floor.from_int(floor_level, is_top),
        dpe_rating=DpeRating.from_string(dpe) if dpe else None,
        furnished=furnished,
        advertiser=advertiser,
        published_at=datetime.now() - timedelta(minutes=published_offset_minutes),
    )


def build_search_filter(
    *,
    cities: list[str] | None = None,
    radius_km: float = 30.0,
    excluded_cities: list[str] | None = None,
    max_price: int = 1500,
    max_dpe_rating: str | None = "D",
    max_results: int = DEFAULT_MAX_RESULTS,
    notification_interval_minutes: int = DEFAULT_NOTIFICATION_INTERVAL_MINUTES,
    refresh_interval_minutes: int = DEFAULT_REFRESH_INTERVAL_MINUTES,
) -> SearchFilter:
    max_rating = DpeRating.from_string(max_dpe_rating) if max_dpe_rating else None
    return SearchFilter(
        id=_fake.uuid4()[:8],
        name=f"Test filter {_fake.word()}",
        cities=cities or ["Annecy"],
        radius_km=radius_km,
        excluded_cities=excluded_cities or [],
        max_price=max_price,
        accepted_dpe_ratings=DpeRating.up_to(max_rating) if max_rating else set(),
        max_results=max_results,
        notification_interval_minutes=notification_interval_minutes,
        refresh_interval_minutes=refresh_interval_minutes,
    )
