"""Suggest, apply and refuse a criterion after repeated dismissals (ticket 08)."""

from dataclasses import replace

import pytest
from faker import Faker

from apartment_hunter.application.use_cases import (
    DismissHome,
    GetTopListings,
    RestoreHome,
    SuggestCriteria,
)
from apartment_hunter.domain.entities import FilterBoundError, Listing, SearchFilter
from apartment_hunter.domain.value_objects import DismissalReason
from tests.fakes.builders import build_listing, build_search_filter
from tests.fakes.in_memory_geocoding import InMemoryGeocoding
from tests.fakes.in_memory_listing_repository import InMemoryListingRepository
from tests.fakes.in_memory_rent_references import InMemoryRentReferences

_fake = Faker("fr_FR")
GEOCODED = {"annecy": (45.8992, 6.1294), "poisy": (45.9217, 6.0631)}


def _build_use_case(repository: InMemoryListingRepository) -> SuggestCriteria:
    geocoding = InMemoryGeocoding(GEOCODED)
    get_top = GetTopListings(repository, geocoding, InMemoryRentReferences())
    return SuggestCriteria(repository, get_top, geocoding)


def _build_home(city: str, surface_m2: float) -> Listing:
    return build_listing(city=city, surface_m2=surface_m2, price=float(_fake.random_int(700, 1100)))


async def _save_filter(repository: InMemoryListingRepository) -> SearchFilter:
    search_filter = build_search_filter(
        cities=["Annecy"], radius_km=20, max_price=1500, max_dpe_rating=None
    )
    await repository.save_filter(search_filter)
    return search_filter


async def _dismiss(
    repository: InMemoryListingRepository, homes: list[Listing], reason: DismissalReason
) -> None:
    dismiss = DismissHome(repository)
    for home in homes:
        await dismiss.execute(home, reason)


async def test_the_third_same_commune_proposes_its_exclusion_and_counts_the_cost() -> None:
    # Arrange — three Poisy homes dismissed; two more in Poisy and one in Annecy still shown
    repository = InMemoryListingRepository()
    await _save_filter(repository)
    dismissed = [_build_home("Poisy", 30.0 + n * 7) for n in range(3)]
    still_shown = [_build_home("Poisy", 60.0 + n * 7) for n in range(2)]
    elsewhere = _build_home("Annecy", 52.0)
    await repository.save_many([*dismissed, *still_shown, elsewhere])
    await _dismiss(repository, dismissed, DismissalReason.CITY)

    # Act
    pending = await _build_use_case(repository).find_suggestions(dismissed[-1])

    # Assert
    assert len(pending) == 1
    assert pending[0].suggestion.proposal == "exclure Poisy"
    assert pending[0].hidden_too == len(still_shown)


async def test_a_restored_dismissal_does_not_count() -> None:
    # Arrange
    repository = InMemoryListingRepository()
    await _save_filter(repository)
    dismissed = [_build_home("Poisy", 30.0 + n * 7) for n in range(3)]
    await repository.save_many(dismissed)
    await _dismiss(repository, dismissed, DismissalReason.CITY)
    await RestoreHome(repository).execute(dismissed[0].id)

    # Act
    pending = await _build_use_case(repository).find_suggestions(dismissed[-1])

    # Assert
    assert pending == []


async def test_accepting_rewrites_the_stored_filter() -> None:
    # Arrange
    repository = InMemoryListingRepository()
    search_filter = await _save_filter(repository)
    dismissed = [_build_home("Annecy", s) for s in (24.0, 27.5, 31.0)]
    await repository.save_many(dismissed)
    await _dismiss(repository, dismissed, DismissalReason.TOO_SMALL)
    use_case = _build_use_case(repository)
    pending = await use_case.find_suggestions(dismissed[-1])

    # Act
    await use_case.apply_suggestion(pending[0])

    # Assert
    stored = next(f for f in await repository.load_filters() if f.id == search_filter.id)
    assert stored.min_surface_m2 == 32
    assert stored.cities == search_filter.cities
    with pytest.raises(FilterBoundError):
        replace(stored, min_surface_m2=-float(_fake.random_int(1, 50)))


async def test_a_refusal_is_kept_and_silences_the_question() -> None:
    # Arrange
    repository = InMemoryListingRepository()
    search_filter = await _save_filter(repository)
    dismissed = [_build_home("Annecy", s) for s in (24.0, 27.5, 31.0)]
    await repository.save_many(dismissed)
    await _dismiss(repository, dismissed, DismissalReason.TOO_SMALL)
    use_case = _build_use_case(repository)
    pending = await use_case.find_suggestions(dismissed[-1])

    # Act
    await use_case.save_refusal(pending[0])

    # Assert
    refusals = await repository.list_criterion_refusals()
    assert [(r.filter_id, r.reason, r.dismissal_count) for r in refusals] == [
        (search_filter.id, DismissalReason.TOO_SMALL, 3)
    ]
    assert await use_case.find_suggestions(dismissed[-1]) == []
