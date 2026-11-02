"""Every use case the entry points ask for must actually build.

`app.py` and `main.py` have no test of their own, so a factory renamed or a dependency
added is only caught here — and both entry points reach the container on their first
request, not at import time.
"""

from pathlib import Path

from apartment_hunter.application.use_cases import (
    CrawlAllSources,
    GetTopListings,
    ManageFilters,
    NotifyNewListings,
    OpenHome,
    RefreshFilter,
    WatchFilters,
)
from apartment_hunter.infrastructure.config import Settings
from apartment_hunter.infrastructure.container import Container


def _build_container(tmp_path: Path) -> Container:
    return Container(Settings(database_url=str(tmp_path / "hunter.db")))


def test_every_factory_builds(tmp_path: Path) -> None:
    # Arrange
    container = _build_container(tmp_path)

    # Act & Assert — no factory takes a coordinate table any more
    assert isinstance(container.make_crawl_use_case(), CrawlAllSources)
    assert isinstance(container.make_get_top_use_case(), GetTopListings)
    assert isinstance(container.make_notify_use_case(), NotifyNewListings)
    assert isinstance(container.make_refresh_use_case(), RefreshFilter)
    assert isinstance(container.make_watch_use_case(), WatchFilters)
    assert isinstance(container.make_manage_filters_use_case(), ManageFilters)
    assert isinstance(container.make_open_home_use_case(), OpenHome)


def test_the_watch_use_case_accepts_the_cli_overrides(tmp_path: Path) -> None:
    # Arrange — `hunt watch --refresh 10 --interval 5`
    container = _build_container(tmp_path)

    # Act
    watch = container.make_watch_use_case(crawl_interval_minutes=10, alert_interval_minutes=5)

    # Assert
    assert isinstance(watch, WatchFilters)


def test_geocoding_and_clock_are_held_once(tmp_path: Path) -> None:
    # Arrange — both are stateless and wanted by nearly every use case
    container = _build_container(tmp_path)

    # Act & Assert
    assert container.geocoding is container.geocoding
    assert container.clock is container.clock
