import pytest

from apartment_hunter.application.use_cases import CrawlAllSources, SourceProgress, SourceState
from apartment_hunter.domain.value_objects import SiteRules
from tests.fakes.builders import build_listing, build_search_filter
from tests.fakes.in_memory_crawler import InMemoryCrawler
from tests.fakes.in_memory_listing_repository import InMemoryListingRepository


@pytest.fixture
def repository() -> InMemoryListingRepository:
    return InMemoryListingRepository()


async def test_saves_all_results_from_all_crawlers(
    repository: InMemoryListingRepository,
) -> None:
    # Arrange
    crawler_a = InMemoryCrawler("source_a", [build_listing(price=800), build_listing(price=850)])
    crawler_b = InMemoryCrawler("source_b", [build_listing(price=900)])
    use_case = CrawlAllSources(crawlers=[crawler_a, crawler_b], repository=repository)
    search_filter = build_search_filter()

    # Act
    new_count = await use_case.execute(search_filter)

    # Assert
    assert new_count == 3
    assert repository.count() == 3


async def test_deduplicates_same_url(repository: InMemoryListingRepository) -> None:
    # Arrange
    duplicate = build_listing(price=800)
    crawler = InMemoryCrawler("source", [duplicate, duplicate])
    use_case = CrawlAllSources(crawlers=[crawler], repository=repository)
    search_filter = build_search_filter()

    # Act
    await use_case.execute(search_filter)
    new_on_second_run = await use_case.execute(search_filter)

    # Assert
    assert repository.count() == 1
    assert new_on_second_run == 0


async def test_execute_detailed_reports_fresh_urls_and_authoritative_sources(
    repository: InMemoryListingRepository,
) -> None:
    # Arrange
    apt_a = build_listing(price=800)
    apt_b = build_listing(price=850)
    crawler_a = InMemoryCrawler("source_a", [apt_a, apt_b])
    crawler_b = InMemoryCrawler("source_b", [])  # returned nothing → not authoritative
    use_case = CrawlAllSources(crawlers=[crawler_a, crawler_b], repository=repository)

    # Act
    outcome = await use_case.execute_detailed(build_search_filter())

    # Assert
    assert outcome.new_count == 2
    assert outcome.fresh_urls == frozenset({apt_a.url, apt_b.url})
    assert outcome.authoritative_sources == frozenset({"source_a"})


async def test_crawler_failure_does_not_abort_others(
    repository: InMemoryListingRepository,
) -> None:
    # Arrange
    class FailingCrawler(InMemoryCrawler):
        async def fetch(self, search_filter):
            raise RuntimeError("network error")

    good_apt = build_listing(price=700)
    good_crawler = InMemoryCrawler("good", [good_apt])
    bad_crawler = FailingCrawler("bad")
    use_case = CrawlAllSources(crawlers=[bad_crawler, good_crawler], repository=repository)

    # Act
    new_count = await use_case.execute(build_search_filter())

    # Assert
    assert new_count == 1
    assert repository.count() == 1


async def test_each_source_reports_how_its_crawl_went(
    repository: InMemoryListingRepository,
) -> None:
    # Arrange
    class FailingCrawler(InMemoryCrawler):
        async def fetch(self, search_filter):  # type: ignore[no-untyped-def]
            raise RuntimeError("network error")

    found = InMemoryCrawler("found", [build_listing(), build_listing()])
    empty = InMemoryCrawler("empty", [])
    failing = FailingCrawler("failing")
    reports: list[SourceProgress] = []
    use_case = CrawlAllSources(crawlers=[found, empty, failing], repository=repository)

    # Act
    await use_case.execute_detailed(build_search_filter(), report=reports.append)

    # Assert
    final = {r.source: (r.state, r.count) for r in reports if r.state is not SourceState.RUNNING}
    assert final == {
        "found": (SourceState.FOUND, 2),
        "empty": (SourceState.EMPTY, 0),
        "failing": (SourceState.FAILED, 0),
    }
    assert {r.source for r in reports if r.state is SourceState.RUNNING} == set(final)


async def test_a_source_whose_terms_forbid_extraction_is_left_alone_by_default(
    repository: InMemoryListingRepository,
) -> None:
    # Arrange
    allowed = InMemoryCrawler("allowed", [build_listing()])
    forbidding = InMemoryCrawler("forbidding", [build_listing()], forbids_reproduction=True)
    use_case = CrawlAllSources(crawlers=[allowed, forbidding], repository=repository)

    # Act
    outcome = await use_case.execute_detailed(build_search_filter())

    # Assert — never asked, not even once
    assert forbidding.fetch_calls == []
    assert outcome.authoritative_sources == {"allowed"}
    assert allowed.applied_rules == [SiteRules.HONOURED]


async def test_ignoring_the_sites_rules_crawls_every_source_and_says_so_to_each(
    repository: InMemoryListingRepository,
) -> None:
    # Arrange — the hunter's own choice, at their own risk (ADR-0012)
    await repository.save_site_rules(SiteRules.IGNORED)
    allowed = InMemoryCrawler("allowed", [build_listing()])
    forbidding = InMemoryCrawler("forbidding", [build_listing()], forbids_reproduction=True)
    use_case = CrawlAllSources(crawlers=[allowed, forbidding], repository=repository)

    # Act
    outcome = await use_case.execute_detailed(build_search_filter())

    # Assert
    assert outcome.authoritative_sources == {"allowed", "forbidding"}
    assert allowed.applied_rules == forbidding.applied_rules == [SiteRules.IGNORED]
