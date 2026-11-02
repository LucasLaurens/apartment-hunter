"""A filter refuses values that would make the watch loop or the crawl misbehave."""

import pytest
from faker import Faker

from apartment_hunter.domain.entities import (
    MAX_AGE_DAYS,
    MAX_CITIES,
    MAX_MAX_RESULTS,
    MAX_RADIUS_KM,
    MIN_INTERVAL_MINUTES,
    MIN_RADIUS_KM,
    SearchFilter,
)
from tests.fakes.builders import build_search_filter

_fake = Faker("fr_FR")


def _build_filter(**criteria: float | int) -> SearchFilter:
    """The builder pins these criteria; the bound tests need them free."""
    return SearchFilter(id=_fake.uuid4(), name=_fake.word(), cities=[_fake.city()], **criteria)  # type: ignore[arg-type]


def test_accepts_the_default_filter() -> None:
    # Act & Assert — the builder's values must stay inside the bounds
    assert build_search_filter().radius_km <= MAX_RADIUS_KM


@pytest.mark.parametrize("minutes", [0, -5])
def test_rejects_an_interval_below_the_minimum(minutes: int) -> None:
    # Act & Assert — a past deadline makes the loop re-crawl every tick
    with pytest.raises(ValueError, match="at least"):
        build_search_filter(refresh_interval_minutes=minutes)
    with pytest.raises(ValueError, match="at least"):
        build_search_filter(notification_interval_minutes=minutes)


def test_accepts_the_minimum_interval() -> None:
    # Act & Assert
    assert build_search_filter(refresh_interval_minutes=MIN_INTERVAL_MINUTES).enabled


@pytest.mark.parametrize("radius", [0.0, MAX_RADIUS_KM + 1])
def test_rejects_a_radius_outside_the_bounds(radius: float) -> None:
    # Act & Assert — a huge radius expands the crawl to thousands of communes
    with pytest.raises(ValueError, match="radius_km"):
        build_search_filter(radius_km=radius)


@pytest.mark.parametrize("radius", [MIN_RADIUS_KM, MAX_RADIUS_KM])
def test_accepts_the_radius_bounds(radius: float) -> None:
    # Act & Assert
    assert build_search_filter(radius_km=radius).radius_km == radius


@pytest.mark.parametrize("results", [0, MAX_MAX_RESULTS + 1])
def test_rejects_an_absurd_result_cap(results: int) -> None:
    # Act & Assert
    with pytest.raises(ValueError, match="max_results"):
        build_search_filter(max_results=results)


def test_rejects_a_negative_price_bound() -> None:
    # Act & Assert
    with pytest.raises(ValueError, match="cannot be negative"):
        build_search_filter(max_price=-1)


@pytest.mark.parametrize("value", [float("nan"), float("inf")])
def test_rejects_a_criterion_that_is_not_a_number(value: float) -> None:
    # Act & Assert — « nan » passed every comparison and saved a filter matching nothing
    with pytest.raises(ValueError, match="min_surface_m2"):
        SearchFilter(
            id=_fake.uuid4(), name=_fake.word(), cities=[_fake.city()], min_surface_m2=value
        )


def test_rejects_a_freshness_window_the_clock_cannot_subtract() -> None:
    # Act & Assert — 10**30 days was saved, then every page of that filter answered 500
    with pytest.raises(ValueError, match="max_age_days"):
        SearchFilter(
            id=_fake.uuid4(),
            name=_fake.word(),
            cities=[_fake.city()],
            max_age_days=MAX_AGE_DAYS + 1,
        )


def test_accepts_the_longest_freshness_window() -> None:
    # Act & Assert
    longest = SearchFilter(
        id=_fake.uuid4(), name=_fake.word(), cities=[_fake.city()], max_age_days=MAX_AGE_DAYS
    )
    assert longest.max_age_days == MAX_AGE_DAYS


def test_rejects_more_cities_than_a_crawl_should_geocode() -> None:
    # Act & Assert — each city is one Nominatim call, which allows one a second
    with pytest.raises(ValueError, match="cities"):
        build_search_filter(cities=[_fake.city() for _ in range(MAX_CITIES + 1)])
