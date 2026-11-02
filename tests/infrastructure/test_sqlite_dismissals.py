"""A dismissal outlives the listing row it was made on (ADR-0009).

The purge deletes listing rows; if a dismissal lived on that row, every dismissed home
would come back on the next crawl.
"""

import sqlite3
from pathlib import Path

from faker import Faker

from apartment_hunter.domain.services import CriterionRefusal, DismissedHomes, build_dismissal
from apartment_hunter.domain.value_objects import DismissalReason
from apartment_hunter.infrastructure.storage.sqlite_repository import SqliteRepository
from tests.fakes.builders import build_listing, build_search_filter

_fake = Faker("fr_FR")


async def _open_repository(db_path: str) -> SqliteRepository:
    repository = SqliteRepository(db_path)
    await repository.connect()
    return repository


async def test_a_dismissal_survives_the_purge_of_its_listing(tmp_path: Path) -> None:
    # Arrange
    repository = await _open_repository(str(tmp_path / "hunter.db"))
    listing = build_listing()
    await repository.save_many([listing])
    await repository.save_dismissal(
        build_dismissal(listing, DismissalReason.ASPECT, _fake.date_time_this_year())
    )

    # Act
    await repository.delete_many([listing.id])

    # Assert
    assert [d.listing_id for d in await repository.list_dismissals()] == [listing.id]
    await repository.close()


async def test_a_dismissal_reads_back_identical_after_a_reconnection(tmp_path: Path) -> None:
    # Arrange
    db_path = str(tmp_path / "hunter.db")
    repository = await _open_repository(db_path)
    listing = build_listing(
        charges=_fake.random_int(min=20, max=150),
        advertiser=_fake.company(),
        furnished=True,
        floor_level=_fake.random_int(min=0, max=6),
    )
    dismissal = build_dismissal(
        listing, DismissalReason.OTHER, _fake.date_time_this_year(), _fake.sentence()
    )
    await repository.save_dismissal(dismissal)
    await repository.close()

    # Act
    reopened = await _open_repository(db_path)
    stored = await reopened.list_dismissals()

    # Assert
    assert stored == [dismissal]
    await reopened.close()


async def test_a_listing_without_rooms_reads_back_without_a_home_key(tmp_path: Path) -> None:
    # Arrange
    repository = await _open_repository(str(tmp_path / "hunter.db"))
    listing = build_listing(rooms=None, surface_m2=None, dpe=None)
    dismissal = build_dismissal(listing, DismissalReason.FLOOR, _fake.date_time_this_year())

    # Act
    await repository.save_dismissal(dismissal)

    # Assert
    assert await repository.list_dismissals() == [dismissal]
    await repository.close()


async def test_dismissing_again_replaces_the_earlier_dismissal(tmp_path: Path) -> None:
    # Arrange
    repository = await _open_repository(str(tmp_path / "hunter.db"))
    listing = build_listing()
    await repository.save_dismissal(
        build_dismissal(listing, DismissalReason.ASPECT, _fake.date_time_this_year())
    )
    later = build_dismissal(listing, DismissalReason.TOO_SMALL, _fake.date_time_this_year())

    # Act
    await repository.save_dismissal(later)

    # Assert
    assert await repository.list_dismissals() == [later]
    await repository.close()


async def test_a_dismissal_stored_with_a_site_spelling_still_hides_its_home(
    tmp_path: Path,
) -> None:
    # Arrange — a row written before the home key folded its commune
    db_path = str(tmp_path / "hunter.db")
    repository = await _open_repository(db_path)
    dismissed = build_listing(source="seloger", city="Chambéry", rooms=3, surface_m2=58.0)
    await repository.save_dismissal(
        build_dismissal(dismissed, DismissalReason.ASPECT, _fake.date_time_this_year())
    )
    await repository.close()
    with sqlite3.connect(db_path) as legacy:
        legacy.execute("UPDATE dismissals SET home_city = ?", ("Chambéry",))
    republished = build_listing(source="laforet", city="Chambery", rooms=3, surface_m2=58.0)

    # Act
    reopened = await _open_repository(db_path)
    dismissals = DismissedHomes(await reopened.list_dismissals())
    await reopened.close()

    # Assert
    assert dismissals.is_dismissed(republished)


async def test_a_restored_dismissal_stops_hiding_but_keeps_its_trace(tmp_path: Path) -> None:
    # Arrange
    db_path = str(tmp_path / "hunter.db")
    repository = await _open_repository(db_path)
    listing = build_listing()
    await repository.save_dismissal(
        build_dismissal(listing, DismissalReason.DPE, _fake.date_time_this_month())
    )

    # Act
    await repository.save_restoration(listing.id, _fake.date_time_this_month())

    # Assert
    assert await repository.list_dismissals() == []
    async with repository._conn.execute(
        "SELECT restored_at FROM dismissals WHERE listing_id = ?", (listing.id,)
    ) as cur:
        assert (await cur.fetchone())[0] is not None
    await repository.close()


async def test_dismissing_a_restored_home_again_hides_it_again(tmp_path: Path) -> None:
    # Arrange
    repository = await _open_repository(str(tmp_path / "hunter.db"))
    listing = build_listing()
    await repository.save_dismissal(
        build_dismissal(listing, DismissalReason.DPE, _fake.date_time_this_month())
    )
    await repository.save_restoration(listing.id, _fake.date_time_this_month())

    # Act
    await repository.save_dismissal(
        build_dismissal(listing, DismissalReason.ASPECT, _fake.date_time_this_month())
    )

    # Assert
    assert [d.reason for d in await repository.list_dismissals()] == [DismissalReason.ASPECT]
    await repository.close()


async def test_a_restored_dismissal_is_listed_with_its_date_until_dismissed_again(
    tmp_path: Path,
) -> None:
    # Arrange
    repository = await _open_repository(str(tmp_path / "hunter.db"))
    listing = build_listing()
    await repository.save_dismissal(
        build_dismissal(listing, DismissalReason.DPE, _fake.date_time_this_year())
    )
    restored_at = _fake.date_time_this_month()
    await repository.save_restoration(listing.id, restored_at)
    listed = [d.restored_at for d in await repository.list_restored_dismissals()]

    # Act
    await repository.save_dismissal(
        build_dismissal(listing, DismissalReason.ASPECT, _fake.date_time_this_month())
    )

    # Assert
    assert listed == [restored_at]
    assert await repository.list_restored_dismissals() == []
    await repository.close()


async def test_a_stored_listing_is_found_by_its_id(tmp_path: Path) -> None:
    # Arrange
    repository = await _open_repository(str(tmp_path / "hunter.db"))
    listing = build_listing()
    await repository.save_many([listing])

    # Act
    found = await repository.find_listing(listing.id)

    # Assert
    assert found is not None and found.url == listing.url
    assert await repository.find_listing(_fake.sha256()) is None
    await repository.close()


async def test_a_database_from_before_restoration_gains_the_column(tmp_path: Path) -> None:
    # Arrange — a dismissals table written before `restored_at` existed
    db_path = str(tmp_path / "hunter.db")
    repository = await _open_repository(db_path)
    listing = build_listing()
    await repository.save_dismissal(
        build_dismissal(listing, DismissalReason.CITY, _fake.date_time_this_month())
    )
    await repository.close()
    with sqlite3.connect(db_path) as raw:
        raw.execute("ALTER TABLE dismissals DROP COLUMN restored_at")

    # Act
    reopened = await _open_repository(db_path)

    # Assert
    assert [d.listing_id for d in await reopened.list_dismissals()] == [listing.id]
    await reopened.close()


async def test_refusals_survive_the_purge_and_go_with_their_filter(tmp_path: Path) -> None:
    # Arrange — the dismissed listings are purged, the refusal must stay
    repository = await _open_repository(str(tmp_path / "hunter.db"))
    kept, dropped = build_search_filter(), build_search_filter()
    for search_filter in (kept, dropped):
        await repository.save_filter(search_filter)
    listing = build_listing()
    await repository.save_many([listing])
    refusals = [
        CriterionRefusal(
            filter_id=f.id,
            reason=DismissalReason.CITY,
            value=listing.location.city.lower(),
            refused_at=_fake.date_time_this_month(),
            dismissal_count=_fake.random_int(3, 9),
        )
        for f in (kept, dropped)
    ]
    for refusal in refusals:
        await repository.save_criterion_refusal(refusal)

    # Act
    await repository.delete_many([listing.id])
    await repository.delete_filter(dropped.id)

    # Assert
    assert await repository.list_criterion_refusals() == [refusals[0]]
    await repository.close()
