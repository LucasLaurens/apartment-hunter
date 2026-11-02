"""What the expiry rule reads from storage: when a listing was last returned by a
crawl, and when each source last answered a filter (ticket 13)."""

import sqlite3
from dataclasses import replace
from datetime import timedelta
from pathlib import Path

from faker import Faker

from apartment_hunter.infrastructure.storage.sqlite_repository import SqliteRepository
from tests.fakes.builders import build_listing, build_search_filter

_fake = Faker()


async def _open_repository(tmp_path: Path) -> SqliteRepository:
    repository = SqliteRepository(str(tmp_path / "hunter.db"))
    await repository.connect()
    return repository


async def test_a_new_crawl_moves_last_seen_forward_and_keeps_first_sighting(
    tmp_path: Path,
) -> None:
    # Arrange
    repository = await _open_repository(tmp_path)
    first = build_listing()
    await repository.save_many([first])
    later = first.last_seen_at + timedelta(hours=_fake.random_int(1, 72))

    # Act
    await repository.save_many([replace(first, last_seen_at=later, fetched_at=later)])

    # Assert
    stored = (await repository.list_all())[0]
    assert stored.last_seen_at == later
    assert stored.fetched_at == first.fetched_at
    await repository.close()


async def test_an_older_sighting_never_moves_last_seen_back(tmp_path: Path) -> None:
    # Arrange
    repository = await _open_repository(tmp_path)
    listing = build_listing()
    await repository.save_many([listing])
    earlier = listing.last_seen_at - timedelta(hours=_fake.random_int(1, 72))

    # Act
    await repository.save_many([replace(listing, last_seen_at=earlier)])

    # Assert
    assert (await repository.list_all())[0].last_seen_at == listing.last_seen_at
    await repository.close()


async def test_source_successes_are_kept_per_filter_and_overwritten(tmp_path: Path) -> None:
    # Arrange
    repository = await _open_repository(tmp_path)
    watched, other = build_search_filter(), build_search_filter()
    first = _fake.date_time_between(start_date="-30d", end_date="-2d")
    second = first + timedelta(days=1)
    await repository.save_source_successes(watched.id, frozenset({"pap", "orpi"}), first)

    # Act
    await repository.save_source_successes(watched.id, frozenset({"pap"}), second)

    # Assert
    assert await repository.find_source_successes(watched.id) == {"pap": second, "orpi": first}
    assert await repository.find_source_successes(other.id) == {}
    await repository.close()


async def test_deleting_a_filter_drops_its_source_successes(tmp_path: Path) -> None:
    # Arrange
    repository = await _open_repository(tmp_path)
    search_filter = build_search_filter()
    await repository.save_filter(search_filter)
    await repository.save_source_successes(
        search_filter.id, frozenset({"pap"}), _fake.date_time_this_month()
    )

    # Act
    await repository.delete_filter(search_filter.id)

    # Assert
    assert await repository.find_source_successes(search_filter.id) == {}
    await repository.close()


async def test_rows_stored_before_the_column_read_their_first_sighting(tmp_path: Path) -> None:
    # Arrange — a database from before `last_seen_at` existed
    db_path = tmp_path / "hunter.db"
    repository = SqliteRepository(str(db_path))
    await repository.connect()
    listing = build_listing()
    await repository.save_many([listing])
    await repository.close()
    with sqlite3.connect(db_path) as raw:
        raw.execute("UPDATE listings SET last_seen_at = NULL")

    # Act
    reopened = SqliteRepository(str(db_path))
    await reopened.connect()

    # Assert
    assert (await reopened.list_all())[0].last_seen_at == listing.fetched_at
    await reopened.close()
