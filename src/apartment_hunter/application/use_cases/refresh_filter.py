"""One crawl of one filter, followed by the purge it makes possible.

This sequence used to exist three times, spelled differently — `_run_search` and
`_purge_after_crawl` in the web layer, `_run_search_cycle` and `_refresh_filter` in the
CLI — and the copies had drifted. Two of them passed the base filter *and* its expanded
commune list to the crawl; the web watch loop passed only the expanded one, so sources
able to search by radius received a commune list instead of the radius.

Orchestration belongs here rather than in an entry point: what the web route and the
Typer command genuinely differ in is how they *report*, not what they do.
"""

from dataclasses import dataclass
from datetime import datetime

from loguru import logger

from ...domain.entities import SearchFilter
from ...domain.ports import GeocodedCities, GeocodingPort, ListingRepositoryPort
from ...domain.services import ListingMatcher
from .crawl_all_sources import CrawlAllSources, ProgressReport, ignore_progress
from .purge_stale_listings import PurgeStaleListings


@dataclass(frozen=True)
class RefreshOutcome:
    new_count: int
    purged_count: int

    @property
    def changed(self) -> bool:
        return bool(self.new_count or self.purged_count)


class RefreshFilter:
    def __init__(
        self,
        crawl: CrawlAllSources,
        repository: ListingRepositoryPort,
        geocoding: GeocodingPort,
    ):
        self._crawl = crawl
        self._repository = repository
        self._geocoding = geocoding

    async def execute(
        self,
        target: SearchFilter,
        keep_filters: list[SearchFilter],
        *,
        purge: bool = True,
        report: ProgressReport = ignore_progress,
    ) -> RefreshOutcome:
        """Crawl `target`, then drop stored listings no saved filter wants any more.

        `keep_filters` is the whole saved set, not just `target`: a listing another
        filter still wants must survive this filter's purge. An ad-hoc filter that was
        never saved passes `purge=False` — it is not in the keep-set, so purging
        against it would delete almost everything.
        """
        geocoded = await self._geocoding.find_cities_in_radius([target])
        crawl_cities = await self._geocoding.list_crawl_cities(target, geocoded)
        logger.debug(f"Crawl cities expanded: {target.cities} → {len(crawl_cities)} communes")

        # Radius-capable sources search the whole area from the base city in one query;
        # per-city sources get the expanded commune list. Both are passed, always.
        outcome = await self._crawl.execute_detailed(
            target, target.with_crawl_cities(crawl_cities), report
        )
        if not purge:
            return RefreshOutcome(new_count=outcome.new_count, purged_count=0)

        # Same gate as the purge: only a saved filter has a page whose freshness matters.
        await self._repository.save_source_successes(
            target.id, outcome.authoritative_sources, datetime.now()
        )

        keep_geocoded = await self._geocoding.find_cities_in_radius(keep_filters)
        purged = await self._purge_for(keep_filters, keep_geocoded).execute(target, outcome)
        return RefreshOutcome(new_count=outcome.new_count, purged_count=purged.total)

    def _purge_for(
        self, keep_filters: list[SearchFilter], geocoded: GeocodedCities
    ) -> PurgeStaleListings:
        return PurgeStaleListings(
            repository=self._repository,
            matcher=ListingMatcher(geocoded_cities=geocoded),
            keep_filters=keep_filters,
        )
