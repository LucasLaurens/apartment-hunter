"""A saved filter's crawl records which sources answered it — the expiry rule's input."""

from faker import Faker

from apartment_hunter.application.use_cases import CrawlAllSources, RefreshFilter
from apartment_hunter.domain.entities import MAX_CITIES
from tests.fakes.builders import build_listing, build_search_filter
from tests.fakes.in_memory_crawler import InMemoryCrawler
from tests.fakes.in_memory_geocoding import InMemoryGeocoding
from tests.fakes.in_memory_listing_repository import InMemoryListingRepository

GEOCODED = {"annecy": (45.8992, 6.1294)}

fake = Faker("fr_FR")


def _build_refresh(
    repository: InMemoryListingRepository, crawlers: list[InMemoryCrawler]
) -> RefreshFilter:
    return RefreshFilter(
        crawl=CrawlAllSources(crawlers=list(crawlers), repository=repository),
        repository=repository,
        geocoding=InMemoryGeocoding(GEOCODED),
    )


async def test_records_only_the_sources_that_answered() -> None:
    # Arrange
    repository = InMemoryListingRepository()
    answering = InMemoryCrawler("pap", [build_listing(source="pap")])
    silent = InMemoryCrawler("paruvendu", [])
    search_filter = build_search_filter(cities=["Annecy"])

    # Act
    await _build_refresh(repository, [answering, silent]).execute(search_filter, [search_filter])

    # Assert
    assert set(await repository.find_source_successes(search_filter.id)) == {"pap"}


async def test_an_unsaved_filter_records_nothing() -> None:
    # Arrange
    repository = InMemoryListingRepository()
    crawler = InMemoryCrawler("pap", [build_listing(source="pap")])
    adhoc = build_search_filter(cities=["Annecy"])

    # Act
    await _build_refresh(repository, [crawler]).execute(adhoc, [], purge=False)

    # Assert
    assert await repository.find_source_successes(adhoc.id) == {}


async def test_crawls_more_communes_than_a_filter_may_name() -> None:
    # Arrange
    repository = InMemoryListingRepository()
    crawler = InMemoryCrawler("pap", [build_listing(source="pap")])
    search_filter = build_search_filter(cities=["Annecy"])
    communes = [fake.unique.city() for _ in range(MAX_CITIES * 3)]
    refresh = RefreshFilter(
        crawl=CrawlAllSources(crawlers=[crawler], repository=repository),
        repository=repository,
        geocoding=InMemoryGeocoding(GEOCODED, {search_filter.id: communes}),
    )

    # Act
    await refresh.execute(search_filter, [search_filter])

    # Assert
    assert crawler.fetch_calls[0].cities == communes
