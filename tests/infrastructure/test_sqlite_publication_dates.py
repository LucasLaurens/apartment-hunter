"""Publication dates survive a round-trip, and first-seen rows get upgraded."""

from dataclasses import replace
from datetime import datetime, timedelta
from pathlib import Path

from apartment_hunter.domain.value_objects import PublicationSource
from apartment_hunter.infrastructure.storage.sqlite_repository import SqliteRepository
from tests.fakes.builders import build_listing


async def _open_repository(tmp_path: Path) -> SqliteRepository:
    repository = SqliteRepository(str(tmp_path / "hunter.db"))
    await repository.connect()
    return repository


async def test_round_trips_the_publication_source(tmp_path: Path) -> None:
    # Arrange
    repository = await _open_repository(tmp_path)
    published_at = (datetime.now() - timedelta(days=4)).replace(microsecond=0)
    site_dated = replace(
        build_listing(),
        published_at=published_at,
        published_at_source=PublicationSource.SITE,
    )
    first_seen = build_listing()

    # Act
    await repository.save_many([site_dated, first_seen])
    stored = {listing.id: listing for listing in await repository.list_all()}

    # Assert
    assert stored[site_dated.id].published_at == published_at
    assert stored[site_dated.id].has_site_publication_date
    assert not stored[first_seen.id].has_site_publication_date
    await repository.close()


async def test_upgrades_a_first_seen_row_once_the_site_publishes_a_date(tmp_path: Path) -> None:
    # Arrange — first crawl read no date, second one does
    repository = await _open_repository(tmp_path)
    listing = build_listing()
    await repository.save_many([listing])
    real_date = (datetime.now() - timedelta(days=12)).replace(microsecond=0)

    # Act
    await repository.save_many(
        [replace(listing, published_at=real_date, published_at_source=PublicationSource.SITE)]
    )
    stored = (await repository.list_all())[0]

    # Assert
    assert stored.published_at == real_date
    assert stored.has_site_publication_date
    await repository.close()


async def test_keeps_an_existing_site_date_untouched(tmp_path: Path) -> None:
    # Arrange
    repository = await _open_repository(tmp_path)
    original = (datetime.now() - timedelta(days=20)).replace(microsecond=0)
    listing = replace(
        build_listing(),
        published_at=original,
        published_at_source=PublicationSource.SITE,
    )
    await repository.save_many([listing])

    # Act — a later crawl re-reads the same listing, one day "fresher"
    await repository.save_many([replace(listing, published_at=original + timedelta(days=1))])
    stored = (await repository.list_all())[0]

    # Assert — the age ranking must not drift on every crawl
    assert stored.published_at == original
    await repository.close()
