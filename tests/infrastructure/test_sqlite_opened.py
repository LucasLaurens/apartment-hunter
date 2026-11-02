"""Openings live in their own table: they outlive the purge, and a reconnection.

A database written before that table held its openings in `listings.opened_at`; the
migration turns each one into an opening once, then clears the column.
"""

import sqlite3
from contextlib import closing
from pathlib import Path

from faker import Faker

from apartment_hunter.domain.entities import SearchFilter
from apartment_hunter.domain.services import OpenedHomes, build_home_key, build_opening
from apartment_hunter.infrastructure.storage.sqlite_repository import SqliteRepository
from tests.fakes.builders import build_listing

_fake = Faker("fr_FR")


async def _open_repository(tmp_path: Path) -> SqliteRepository:
    repository = SqliteRepository(str(tmp_path / "hunter.db"))
    await repository.connect()
    return repository


async def test_an_opening_survives_a_reconnection(tmp_path: Path) -> None:
    # Arrange
    repository = await _open_repository(tmp_path)
    opening = build_opening(build_listing(), _fake.date_time_this_year())

    # Act
    await repository.save_opening(opening)
    await repository.close()
    reopened = await _open_repository(tmp_path)
    stored = await reopened.list_openings()

    # Assert
    assert stored == [opening]
    await reopened.close()


async def test_the_first_opening_of_a_listing_is_kept(tmp_path: Path) -> None:
    # Arrange
    repository = await _open_repository(tmp_path)
    listing = build_listing()
    first = build_opening(listing, _fake.date_time_this_year())
    await repository.save_opening(first)

    # Act
    await repository.save_opening(build_opening(listing, _fake.date_time_this_month()))

    # Assert
    assert await repository.list_openings() == [first]
    await repository.close()


async def test_the_purge_does_not_erase_an_opening(tmp_path: Path) -> None:
    # Arrange
    repository = await _open_repository(tmp_path)
    listing = build_listing()
    await repository.save_many([listing])
    await repository.save_opening(build_opening(listing, _fake.date_time_this_year()))

    # Act
    await repository.delete_many([listing.id])

    # Assert
    assert [o.listing_id for o in await repository.list_openings()] == [listing.id]
    await repository.close()


async def test_an_opening_without_home_key_round_trips(tmp_path: Path) -> None:
    # Arrange — no rooms nor surface: recognised by its URL only
    repository = await _open_repository(tmp_path)
    opening = build_opening(build_listing(rooms=None, surface_m2=None), _fake.date_time())

    # Act
    await repository.save_opening(opening)

    # Assert
    assert await repository.list_openings() == [opening]
    await repository.close()


async def _store_legacy_opening(tmp_path: Path) -> tuple[str, str]:
    """A listing opened the old way: a timestamp on its own row."""
    repository = await _open_repository(tmp_path)
    listing = build_listing()
    await repository.save_many([listing])
    await repository.close()
    opened_at = _fake.date_time_this_year().isoformat()
    with closing(sqlite3.connect(tmp_path / "hunter.db")) as db, db:
        db.execute("UPDATE listings SET opened_at = ? WHERE id = ?", (opened_at, listing.id))
    return listing.id, opened_at


async def test_the_migration_turns_a_row_timestamp_into_an_opening(tmp_path: Path) -> None:
    # Arrange
    listing_id, opened_at = await _store_legacy_opening(tmp_path)

    # Act
    repository = await _open_repository(tmp_path)
    listing = await repository.find_listing(listing_id)
    openings = await repository.list_openings()

    # Assert — the opening carries the home key, so it reaches the duplicates too
    assert listing is not None
    assert [(o.listing_id, o.opened_at.isoformat(), o.home_key) for o in openings] == [
        (listing_id, opened_at, build_home_key(listing))
    ]
    assert OpenedHomes(openings).find_opened_at(listing) is not None
    await repository.close()


async def test_the_migration_runs_once(tmp_path: Path) -> None:
    # Arrange
    await _store_legacy_opening(tmp_path)
    repository = await _open_repository(tmp_path)
    await repository.close()

    # Act — every later start replays the migrations
    repository = await _open_repository(tmp_path)
    openings = await repository.list_openings()

    # Assert — moved once, and the row no longer holds a second truth
    assert len(openings) == 1
    with sqlite3.connect(tmp_path / "hunter.db") as db:
        assert db.execute(
            "SELECT COUNT(*) FROM listings WHERE opened_at IS NOT NULL"
        ).fetchone() == (0,)
    await repository.close()


async def test_deleting_a_filter_that_already_alerted_does_not_raise(tmp_path: Path) -> None:
    """Foreign keys are enforced, so the alert rows must go before the filter.

    `delete_many` already did this for listings; `delete_filter` did not, and the web
    route answered 500 on any filter that had ever alerted.
    """
    # Arrange
    repository = await _open_repository(tmp_path)
    await repository.save_filter(SearchFilter(id="f1", name="Veille", cities=["Annecy"]))
    listing = build_listing()
    await repository.save_many([listing])
    await repository.mark_notified([listing.id], "f1")

    # Act
    await repository.delete_filter("f1")

    # Assert — the filter is gone and the listing it alerted survives
    assert await repository.load_filters() == []
    assert len(await repository.list_all()) == 1
    await repository.close()


async def test_deleting_a_filter_leaves_other_filters_alerts_alone(tmp_path: Path) -> None:
    # Arrange
    repository = await _open_repository(tmp_path)
    for filter_id in ("f1", "f2"):
        await repository.save_filter(
            SearchFilter(id=filter_id, name=f"Veille {filter_id}", cities=["Annecy"])
        )
    listing = build_listing()
    await repository.save_many([listing])
    await repository.mark_notified([listing.id], "f1")
    await repository.mark_notified([listing.id], "f2")

    # Act
    await repository.delete_filter("f1")

    # Assert — f2 must still consider the listing alerted
    assert await repository.find_new_since("f2") == []
    await repository.close()
