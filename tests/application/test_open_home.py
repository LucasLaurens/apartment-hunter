"""Opening a listing opens its home, and the purge does not make it new again.

What is opened is a *home* (ADR-0009): any listing that would group with an opened one
under the *Doublon* rule stops being *Nouvelle* too, whichever source publishes it and
however many times its row is purged and crawled again.
"""

from dataclasses import replace
from datetime import datetime

import pytest
from faker import Faker

from apartment_hunter.application.use_cases import (
    GetTopListings,
    ListingNotFoundError,
    OpenHome,
)
from apartment_hunter.domain.entities import Listing
from tests.fakes.builders import build_listing, build_search_filter
from tests.fakes.in_memory_geocoding import InMemoryGeocoding
from tests.fakes.in_memory_listing_repository import InMemoryListingRepository
from tests.fakes.in_memory_rent_references import InMemoryRentReferences

GEOCODED = {"annecy": (45.8992, 6.1294)}
_fake = Faker("fr_FR")


@pytest.fixture
def repository() -> InMemoryListingRepository:
    return InMemoryListingRepository()


def _build_home_on(source: str, rooms: int, surface: float, rent: int) -> Listing:
    return build_listing(source=source, rooms=rooms, surface_m2=surface, price=rent)


def _pick_home_figures() -> tuple[int, float, int]:
    return (
        _fake.random_int(min=1, max=5),
        float(_fake.random_int(min=20, max=110)),
        _fake.random_int(min=500, max=1400),
    )


async def _find_shown(repository: InMemoryListingRepository) -> dict[str, Listing]:
    top = GetTopListings(repository, InMemoryGeocoding(GEOCODED), InMemoryRentReferences())
    groups = await top.execute(build_search_filter(max_dpe_rating=None), limit=50)
    return {listing.id: listing for group in groups for listing in group.all_listings}


async def test_opening_a_listing_opens_its_duplicate_on_another_source(
    repository: InMemoryListingRepository,
) -> None:
    # Arrange
    figures = _pick_home_figures()
    opened = _build_home_on("pap", *figures)
    duplicate = _build_home_on("orpi", *figures)
    await repository.save_many([opened, duplicate])

    # Act
    await OpenHome(repository).execute(opened)

    # Assert — the badge does not light up again on the other site
    assert (await _find_shown(repository))[duplicate.id].opened


async def test_two_lots_of_one_source_are_opened_one_by_one(
    repository: InMemoryListingRepository,
) -> None:
    # Arrange — a residence publishes its identical lots side by side
    figures = _pick_home_figures()
    opened = _build_home_on("pap", *figures)
    next_lot = _build_home_on("pap", *figures)
    await repository.save_many([opened, next_lot])

    # Act
    await OpenHome(repository).execute(opened)

    # Assert
    assert not (await _find_shown(repository))[next_lot.id].opened


async def test_an_opened_listing_stays_opened_after_a_purge_and_a_recrawl(
    repository: InMemoryListingRepository,
) -> None:
    # Arrange
    listing = build_listing()
    await repository.save_many([listing])
    await OpenHome(repository).execute(listing)

    # Act — the purge drops the row, a later crawl brings the same URL back
    await repository.delete_many([listing.id])
    await repository.save_many([replace(listing, fetched_at=datetime.now())])

    # Assert
    assert (await _find_shown(repository))[listing.id].opened


async def test_the_first_opening_is_the_one_remembered(
    repository: InMemoryListingRepository,
) -> None:
    # Arrange
    first = _fake.date_time_this_year()
    later = _fake.date_time_between(start_date=first)
    listing = build_listing()
    await repository.save_many([listing])
    await OpenHome(repository, read_now=lambda: first).execute(listing)

    # Act
    await OpenHome(repository, read_now=lambda: later).execute(listing)

    # Assert
    assert (await _find_shown(repository))[listing.id].opened_at == first


async def test_a_home_never_opened_is_still_new(repository: InMemoryListingRepository) -> None:
    # Arrange
    await repository.save_many([build_listing()])

    # Act
    shown = await _find_shown(repository)

    # Assert
    assert not any(listing.opened for listing in shown.values())


async def test_opening_a_purged_listing_by_id_says_so(
    repository: InMemoryListingRepository,
) -> None:
    # Act & Assert — a stale card in an open tab may point at a purged listing
    with pytest.raises(ListingNotFoundError):
        await OpenHome(repository).execute_by_id(_fake.sha256())
