"""Dependency injection — wires concrete implementations to ports."""

from pathlib import Path

from ..application.use_cases import (
    CleanListings,
    CrawlAllSources,
    DismissHome,
    GetTopListings,
    ListDismissedHomes,
    ManageFilters,
    ManageSiteRules,
    MapFilterHomes,
    NotifyNewListings,
    OpenHome,
    RefreshFilter,
    RestoreHome,
    SuggestCriteria,
    WatchFilters,
)
from ..domain.ports import CrawlerPort, NotifierPort
from .clock import AsyncioClock
from .config import Settings
from .crawlers import (
    AgenceBfmCrawler,
    BienIciCrawler,
    Century21Crawler,
    CityaCrawler,
    FnaimCrawler,
    FonciaCrawler,
    LaforetCrawler,
    LocserviceCrawler,
    OrpiCrawler,
    PapCrawler,
    ParuVenduCrawler,
    SbmImmobilierCrawler,
    SquareHabitatCrawler,
    TwoAImmobilierCrawler,
)
from .geocoding import NominatimGeocoding
from .notifications.composite_notifier import CompositeNotifier
from .notifications.terminal_notifier import TerminalNotifier
from .rent_map import CarteDesLoyers
from .storage.sqlite_repository import SqliteRepository


def build_crawlers(settings: Settings) -> list[CrawlerPort]:
    timeout = settings.request_timeout_seconds
    return [
        PapCrawler(timeout=timeout),
        OrpiCrawler(timeout=timeout),
        FonciaCrawler(timeout=timeout),
        ParuVenduCrawler(timeout=timeout),
        Century21Crawler(timeout=timeout),
        LaforetCrawler(timeout=timeout),
        CityaCrawler(timeout=timeout),
        SquareHabitatCrawler(timeout=timeout),
        TwoAImmobilierCrawler(timeout=timeout),
        SbmImmobilierCrawler(timeout=timeout),
        AgenceBfmCrawler(timeout=timeout),
    ]


def build_notifiers() -> list[NotifierPort]:
    # No email, no OS push: new listings surface in the terminal and via the
    # web UI's "Nouveau" badge (in-app bell).
    return [TerminalNotifier()]


class Container:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.repository = SqliteRepository(settings.database_url)
        self.crawlers = build_crawlers(settings)
        self.notifiers = build_notifiers()
        # Both stateless, and both wanted by nearly every use case: held once. The
        # coordinate table used to be a parameter of three factories, computed by
        # whichever entry point happened to call them.
        self.geocoding = NominatimGeocoding()
        self.clock = AsyncioClock()
        # Held once: it keeps the parsed files and the lock that stops two requests
        # from downloading the same file at once.
        self.rent_references = CarteDesLoyers(Path(settings.rent_map_cache_dir))

    def make_crawl_use_case(self) -> CrawlAllSources:
        return CrawlAllSources(
            crawlers=self.crawlers,
            repository=self.repository,
            max_concurrent=self.settings.max_concurrent_crawlers,
        )

    def make_get_top_use_case(self) -> GetTopListings:
        return GetTopListings(
            repository=self.repository,
            geocoding=self.geocoding,
            rent_references=self.rent_references,
        )

    def make_notify_use_case(self) -> NotifyNewListings:
        return NotifyNewListings(
            repository=self.repository,
            notifiers=[CompositeNotifier(self.notifiers)],
            geocoding=self.geocoding,
            rent_references=self.rent_references,
        )

    def make_refresh_use_case(self) -> RefreshFilter:
        return RefreshFilter(
            crawl=self.make_crawl_use_case(),
            repository=self.repository,
            geocoding=self.geocoding,
        )

    def make_watch_use_case(
        self,
        crawl_interval_minutes: int | None = None,
        alert_interval_minutes: int | None = None,
    ) -> WatchFilters:
        return WatchFilters(
            refresh=self.make_refresh_use_case(),
            notify=self.make_notify_use_case(),
            manage=self.make_manage_filters_use_case(),
            clock=self.clock,
            crawl_interval_minutes=crawl_interval_minutes,
            alert_interval_minutes=alert_interval_minutes,
        )

    def make_dismiss_use_case(self) -> DismissHome:
        return DismissHome(repository=self.repository)

    def make_map_use_case(self) -> MapFilterHomes:
        return MapFilterHomes(get_top=self.make_get_top_use_case(), geocoding=self.geocoding)

    def make_suggest_criteria_use_case(self) -> SuggestCriteria:
        return SuggestCriteria(
            repository=self.repository,
            get_top=self.make_get_top_use_case(),
            geocoding=self.geocoding,
        )

    def make_list_dismissed_use_case(self) -> ListDismissedHomes:
        return ListDismissedHomes(repository=self.repository)

    def make_restore_use_case(self) -> RestoreHome:
        return RestoreHome(repository=self.repository)

    def make_open_home_use_case(self) -> OpenHome:
        return OpenHome(repository=self.repository)

    def make_clean_use_case(self) -> CleanListings:
        return CleanListings(repository=self.repository, geocoding=self.geocoding)

    def make_site_rules_use_case(self) -> ManageSiteRules:
        return ManageSiteRules(repository=self.repository)

    def make_clean_use_case(self) -> CleanListings:
        return CleanListings(repository=self.repository, geocoding=self.geocoding)

    def make_manage_filters_use_case(self) -> ManageFilters:
        return ManageFilters(repository=self.repository)

    async def close(self) -> None:
        await self.repository.close()
        for crawler in self.crawlers:
            await crawler.close()
