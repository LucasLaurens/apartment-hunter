import pytest

from apartment_hunter.application.use_cases import CrawlOutcome, PurgeStaleListings
from apartment_hunter.domain.services import ListingMatcher
from tests.fakes.builders import build_listing, build_search_filter
from tests.fakes.in_memory_listing_repository import InMemoryListingRepository

_ANNECY = {"annecy": (45.9, 6.1)}


@pytest.fixture
def repository() -> InMemoryListingRepository:
    return InMemoryListingRepository()


def _build_matcher() -> ListingMatcher:
    return ListingMatcher(geocoded_cities=_ANNECY)


def _crawl(fresh_urls: list[str], sources: list[str]) -> CrawlOutcome:
    return CrawlOutcome(
        new_count=len(fresh_urls),
        fresh_urls=frozenset(fresh_urls),
        authoritative_sources=frozenset(sources),
    )


async def test_deletes_listing_matching_no_filter(repository: InMemoryListingRepository) -> None:
    # Arrange
    off_filter = build_listing(price=5000, source="pap")  # above any filter's max_price
    await repository.save_many([off_filter])
    search_filter = build_search_filter(max_price=1500)
    purge = PurgeStaleListings(repository, _build_matcher(), keep_filters=[search_filter])

    # Act
    result = await purge.execute(search_filter, _crawl([off_filter.url], ["pap"]))

    # Assert
    assert result.irrelevant == 1
    assert repository.count() == 0


async def test_deletes_delisted_listing_absent_from_fresh_crawl(
    repository: InMemoryListingRepository,
) -> None:
    # Arrange
    gone = build_listing(price=900, source="pap")
    await repository.save_many([gone])
    search_filter = build_search_filter(max_price=1500)
    purge = PurgeStaleListings(repository, _build_matcher(), keep_filters=[search_filter])

    # Act — source crawled (authoritative) but this URL no longer returned
    result = await purge.execute(search_filter, _crawl(fresh_urls=[], sources=["pap"]))

    # Assert
    assert result.delisted == 1
    assert repository.count() == 0


async def test_keeps_listing_still_present_in_crawl(
    repository: InMemoryListingRepository,
) -> None:
    # Arrange
    live = build_listing(price=900, source="pap")
    await repository.save_many([live])
    search_filter = build_search_filter(max_price=1500)
    purge = PurgeStaleListings(repository, _build_matcher(), keep_filters=[search_filter])

    # Act
    result = await purge.execute(search_filter, _crawl([live.url], ["pap"]))

    # Assert
    assert result.total == 0
    assert repository.count() == 1


async def test_keeps_listing_when_source_returned_nothing(
    repository: InMemoryListingRepository,
) -> None:
    # Arrange — an empty/failed source is not authoritative, so its listings survive
    kept = build_listing(price=900, source="pap")
    await repository.save_many([kept])
    search_filter = build_search_filter(max_price=1500)
    purge = PurgeStaleListings(repository, _build_matcher(), keep_filters=[search_filter])

    # Act
    result = await purge.execute(search_filter, _crawl(fresh_urls=[], sources=[]))

    # Assert
    assert result.total == 0
    assert repository.count() == 1


async def test_keeps_listing_relevant_to_another_saved_filter(
    repository: InMemoryListingRepository,
) -> None:
    # Arrange — listing is off the crawled filter but matches a second saved filter
    shared = build_listing(price=2000, source="pap")
    await repository.save_many([shared])
    crawled = build_search_filter(max_price=1500)
    other = build_search_filter(max_price=2500)
    purge = PurgeStaleListings(repository, _build_matcher(), keep_filters=[crawled, other])

    # Act
    result = await purge.execute(crawled, _crawl(fresh_urls=[], sources=["pap"]))

    # Assert
    assert result.total == 0
    assert repository.count() == 1
