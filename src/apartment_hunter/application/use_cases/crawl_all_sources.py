import asyncio
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum

from loguru import logger

from ...domain.entities import Listing, SearchFilter
from ...domain.ports import CrawlerPort, ListingRepositoryPort
from ...domain.value_objects import SiteRules

# Cap any single source so one slow/hung crawler never stalls the whole crawl.
SOURCE_TIMEOUT_SECONDS = 180.0


class SourceState(StrEnum):
    RUNNING = "running"
    FOUND = "found"
    EMPTY = "empty"
    FAILED = "failed"  # raised, or ran past SOURCE_TIMEOUT_SECONDS


@dataclass(frozen=True)
class SourceProgress:
    """How one source's crawl is going: what the page shows while a search runs."""

    source: str
    state: SourceState
    count: int = 0


type ProgressReport = Callable[[SourceProgress], None]


def ignore_progress(progress: SourceProgress) -> None:
    """The caller that shows nothing — the CLI and the watch loop."""


@dataclass(frozen=True)
class CrawlOutcome:
    new_count: int
    fresh_urls: frozenset[str]  # every URL seen in this crawl
    authoritative_sources: frozenset[str]  # sources that returned >=1 listing this run


class CrawlAllSources:
    def __init__(
        self,
        crawlers: list[CrawlerPort],
        repository: ListingRepositoryPort,
        max_concurrent: int = 5,
    ):
        self._crawlers = crawlers
        self._repository = repository
        self._semaphore = asyncio.Semaphore(max_concurrent)

    async def execute(
        self, search_filter: SearchFilter, expanded_filter: SearchFilter | None = None
    ) -> int:
        """Crawl all sources concurrently. Returns count of new listings saved."""
        return (await self.execute_detailed(search_filter, expanded_filter)).new_count

    async def execute_detailed(
        self,
        search_filter: SearchFilter,
        expanded_filter: SearchFilter | None = None,
        report: ProgressReport = ignore_progress,
    ) -> CrawlOutcome:
        """Crawl all sources concurrently and report what was seen this run.

        Radius-capable sources (`covers_radius`) search the whole area from the base
        city in one query; per-city sources get `expanded_filter` (cities expanded to
        the communes in radius) so they still reach surrounding towns.
        """
        expanded = expanded_filter or search_filter
        crawlers = await self._select_crawlers()
        tasks = [
            self._crawl_one(
                crawler,
                search_filter if getattr(crawler, "covers_radius", False) else expanded,
                report,
            )
            for crawler in crawlers
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        all_apartments: list[Listing] = []
        fresh_urls: set[str] = set()
        authoritative: set[str] = set()
        for crawler, result in zip(crawlers, results, strict=True):
            if isinstance(result, BaseException):
                logger.error(f"Crawler {crawler.source_name} failed: {result}")
            else:
                all_apartments.extend(result)
                fresh_urls.update(listing.url for listing in result)
                # A source counts as authoritative only if it returned something —
                # an empty result may be a silent parse failure, not a sold-out market.
                if result:
                    authoritative.add(crawler.source_name)
                logger.info(f"{crawler.source_name}: {len(result)} listings fetched")

        new_count = await self._repository.save_many(all_apartments) if all_apartments else 0
        if all_apartments:
            logger.info(f"Saved {new_count} new listings (total fetched: {len(all_apartments)})")
        return CrawlOutcome(
            new_count=new_count,
            fresh_urls=frozenset(fresh_urls),
            authoritative_sources=frozenset(authoritative),
        )

    async def _select_crawlers(self) -> list[CrawlerPort]:
        """The sources this crawl may ask, each told the hunter's choice (ADR-0012).

        Read at every crawl, so a change made in the web page or the CLI applies to the
        next tick of a running watch without restarting it.
        """
        rules = await self._repository.load_site_rules()
        selected = [
            crawler
            for crawler in self._crawlers
            if rules is SiteRules.IGNORED or not crawler.forbids_reproduction
        ]
        for crawler in selected:
            crawler.apply_site_rules(rules)
        return selected

    async def _crawl_one(
        self, crawler: CrawlerPort, search_filter: SearchFilter, report: ProgressReport
    ) -> list[Listing]:
        source = crawler.source_name
        report(SourceProgress(source, SourceState.RUNNING))
        async with self._semaphore:
            try:
                result = await asyncio.wait_for(
                    crawler.fetch(search_filter), timeout=SOURCE_TIMEOUT_SECONDS
                )
            except TimeoutError:
                logger.warning(
                    f"{source}: timed out after {SOURCE_TIMEOUT_SECONDS:.0f}s — skipped this run"
                )
                report(SourceProgress(source, SourceState.FAILED))
                return []
            except Exception:
                report(SourceProgress(source, SourceState.FAILED))
                raise
        state = SourceState.FOUND if result else SourceState.EMPTY
        report(SourceProgress(source, state, len(result)))
        return result
