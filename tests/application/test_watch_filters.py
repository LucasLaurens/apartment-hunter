"""The watch policy, on a clock the test drives.

None of this was testable before: the schedule lived twice in the presentation layer,
read the event loop directly, and never returned. These are the behaviours the two
copies disagreed on.
"""

from dataclasses import dataclass, field

from apartment_hunter.application.use_cases import (
    CrawlAllSources,
    ManageFilters,
    NotifyNewListings,
    RefreshFilter,
    WatchFilters,
)
from apartment_hunter.application.use_cases.watch_filters import SECONDS_PER_MINUTE
from apartment_hunter.domain.entities import Listing, SearchFilter
from apartment_hunter.domain.ports import CrawlerPort

from ..fakes.builders import build_listing, build_search_filter
from ..fakes.in_memory_crawler import InMemoryCrawler
from ..fakes.in_memory_geocoding import InMemoryGeocoding
from ..fakes.in_memory_listing_repository import InMemoryListingRepository
from ..fakes.in_memory_notifier import InMemoryNotifier
from ..fakes.in_memory_rent_references import InMemoryRentReferences
from ..fakes.manual_clock import ManualClock

GEOCODED = {"annecy": (45.8992, 6.1294)}


class BrokenCrawler(CrawlerPort):
    """A source that blows up — one crawler must never stop the whole watch."""

    @property
    def source_name(self) -> str:
        return "broken"

    async def fetch(self, search_filter: SearchFilter) -> list[Listing]:
        raise RuntimeError("source down")


@dataclass
class WatchHarness:
    """Everything one watch needs, wired to fakes."""

    repository: InMemoryListingRepository = field(default_factory=InMemoryListingRepository)
    notifier: InMemoryNotifier = field(default_factory=InMemoryNotifier)
    clock: ManualClock = field(default_factory=ManualClock)

    def build(
        self,
        crawlers: list[CrawlerPort],
        **overrides: int | None,
    ) -> WatchFilters:
        geocoding = InMemoryGeocoding(GEOCODED)
        return WatchFilters(
            refresh=RefreshFilter(
                crawl=CrawlAllSources(crawlers=crawlers, repository=self.repository),
                repository=self.repository,
                geocoding=geocoding,
            ),
            notify=NotifyNewListings(
                repository=self.repository,
                notifiers=[self.notifier],
                geocoding=geocoding,
                rent_references=InMemoryRentReferences(),
            ),
            manage=ManageFilters(repository=self.repository),
            clock=self.clock,
            crawl_interval_minutes=overrides.get("crawl_interval_minutes"),
            alert_interval_minutes=overrides.get("alert_interval_minutes"),
        )

    async def save_filter(self, **kwargs: object) -> SearchFilter:
        search_filter = build_search_filter(cities=["Annecy"], max_dpe_rating=None, **kwargs)  # type: ignore[arg-type]
        await self.repository.save_filter(search_filter)
        return search_filter


def _build_one_listing() -> InMemoryCrawler:
    return InMemoryCrawler(listings=[build_listing(city="Annecy", price=900.0)])


async def test_a_first_pass_crawls_and_alerts() -> None:
    # Arrange
    harness = WatchHarness()
    target = await harness.save_filter()
    watch = harness.build([_build_one_listing()])

    # Act
    reports = await watch.run_pass([target.id])

    # Assert
    assert [r.crawled for r in reports] == [True]
    assert reports[0].new_count == 1
    assert reports[0].notified == 1


async def test_a_pass_before_the_deadline_does_nothing() -> None:
    # Arrange
    harness = WatchHarness()
    target = await harness.save_filter()
    crawler = _build_one_listing()
    watch = harness.build([crawler])
    await watch.run_pass([target.id])

    # Act — one minute later, both deadlines are still in the future
    harness.clock.advance(SECONDS_PER_MINUTE)
    reports = await watch.run_pass([target.id])

    # Assert
    assert reports[0].crawled is False
    assert len(crawler.fetch_calls) == 1


async def test_the_crawl_deadline_is_the_filters_own_cadence() -> None:
    # Arrange
    harness = WatchHarness()
    target = await harness.save_filter(refresh_interval_minutes=30)
    crawler = _build_one_listing()
    watch = harness.build([crawler])
    await watch.run_pass([target.id])

    # Act
    harness.clock.advance(30 * SECONDS_PER_MINUTE)
    reports = await watch.run_pass([target.id])

    # Assert
    assert reports[0].crawled is True
    assert len(crawler.fetch_calls) == 2


async def test_an_override_wins_over_the_filters_own_cadence() -> None:
    # Arrange — the CLI's --refresh flag
    harness = WatchHarness()
    target = await harness.save_filter(refresh_interval_minutes=30)
    watch = harness.build([_build_one_listing()], crawl_interval_minutes=5)
    await watch.run_pass([target.id])

    # Act
    harness.clock.advance(5 * SECONDS_PER_MINUTE)
    reports = await watch.run_pass([target.id])

    # Assert
    assert reports[0].crawled is True


async def test_an_edited_cadence_applies_from_the_next_deadline() -> None:
    # Arrange — the CLI loop captured its filters once and ignored later edits
    harness = WatchHarness()
    target = await harness.save_filter(refresh_interval_minutes=60)
    crawler = _build_one_listing()
    watch = harness.build([crawler])
    await watch.run_pass([target.id])

    # Act — the operator shortens the cadence, then the standing deadline comes due
    target.refresh_interval_minutes = 10
    await harness.repository.save_filter(target)
    harness.clock.advance(60 * SECONDS_PER_MINUTE)
    await watch.run_pass([target.id])
    harness.clock.advance(10 * SECONDS_PER_MINUTE)
    reports = await watch.run_pass([target.id])

    # Assert — the third crawl came 10 minutes after the second, not 60
    assert reports[0].crawled is True
    assert len(crawler.fetch_calls) == 3


async def test_a_failing_source_does_not_stop_the_watch() -> None:
    # Arrange — the CLI loop had no error branch, so this killed the whole watch
    harness = WatchHarness()
    first = await harness.save_filter()
    second = await harness.save_filter()
    watch = harness.build([BrokenCrawler(), _build_one_listing()])

    # Act
    reports = await watch.run_pass([first.id, second.id])

    # Assert
    assert len(reports) == 2
    assert all(r.crawled for r in reports)
    assert reports[0].new_count == 1


async def test_the_loop_sleeps_until_the_soonest_deadline() -> None:
    # Arrange
    harness = WatchHarness()
    target = await harness.save_filter(
        refresh_interval_minutes=30, notification_interval_minutes=15
    )
    watch = harness.build([_build_one_listing()])
    await watch.run_pass([target.id])

    # Act
    sleep_for = watch.compute_seconds_until_next_deadline()

    # Assert — the alert cadence is the shorter of the two
    assert sleep_for == 15 * SECONDS_PER_MINUTE


async def test_nothing_watched_yet_still_yields_a_bounded_sleep() -> None:
    # Arrange — a spinning loop would hammer every source
    harness = WatchHarness()
    watch = harness.build([_build_one_listing()])

    # Act & Assert
    assert watch.compute_seconds_until_next_deadline() >= 1.0


async def test_an_unwatched_filter_is_left_alone() -> None:
    # Arrange
    harness = WatchHarness()
    watched = await harness.save_filter()
    await harness.save_filter()
    watch = harness.build([_build_one_listing()])

    # Act
    reports = await watch.run_pass([watched.id])

    # Assert
    assert len(reports) == 1
    assert reports[0].filter_name == watched.name
