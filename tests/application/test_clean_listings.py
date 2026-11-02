from dataclasses import replace
from datetime import datetime, timedelta

from faker import Faker

from apartment_hunter.application.use_cases import CleanListings
from tests.fakes.builders import build_listing, build_search_filter
from tests.fakes.in_memory_geocoding import InMemoryGeocoding
from tests.fakes.in_memory_listing_repository import InMemoryListingRepository

_fake = Faker()
_ANNECY = {"annecy": (45.9, 6.1)}


def _build_cleaner(repository: InMemoryListingRepository) -> CleanListings:
    return CleanListings(repository, InMemoryGeocoding(known=_ANNECY))


async def test_drops_a_listing_no_saved_filter_wants() -> None:
    # Arrange
    repository = InMemoryListingRepository()
    await repository.save_filter(build_search_filter(max_price=1500))
    off_filter = build_listing(price=5000)
    await repository.save_many([off_filter])
    cleaner = _build_cleaner(repository)

    # Act
    stale = await cleaner.find_stale(datetime.now() - timedelta(days=7))
    deleted = await cleaner.delete(stale)

    # Assert
    assert stale.irrelevant == [off_filter.id]
    assert deleted == 1
    assert repository.count() == 0


async def test_drops_a_wanted_listing_no_crawl_has_seen_since_the_cutoff() -> None:
    # Arrange — the Veyrier-du-Lac case: matches the filter, never returned again
    repository = InMemoryListingRepository()
    await repository.save_filter(build_search_filter(max_price=1500))
    cutoff = datetime.now() - timedelta(days=_fake.random_int(1, 30))
    forgotten = replace(build_listing(price=900), last_seen_at=cutoff - timedelta(hours=1))
    recent = replace(build_listing(price=900), last_seen_at=cutoff + timedelta(hours=1))
    await repository.save_many([forgotten, recent])
    cleaner = _build_cleaner(repository)

    # Act
    stale = await cleaner.find_stale(cutoff)
    await cleaner.delete(stale)

    # Assert
    assert stale.unseen == [forgotten.id]
    assert stale.irrelevant == []
    assert [listing.id for listing in await repository.list_all()] == [recent.id]


async def test_finding_stale_listings_deletes_nothing() -> None:
    # Arrange
    repository = InMemoryListingRepository()
    await repository.save_many([build_listing(price=5000)])
    await repository.save_filter(build_search_filter(max_price=1500))
    cleaner = _build_cleaner(repository)

    # Act
    stale = await cleaner.find_stale(datetime.now())

    # Assert
    assert stale.total == 1
    assert repository.count() == 1


async def test_with_no_saved_filter_only_the_unseen_go() -> None:
    # Arrange — an empty keep-set judges nothing irrelevant, as in the crawl's purge
    repository = InMemoryListingRepository()
    await repository.save_many([build_listing(price=5000)])
    cleaner = _build_cleaner(repository)

    # Act
    stale = await cleaner.find_stale(datetime.now() - timedelta(days=7))

    # Assert
    assert stale.total == 0
