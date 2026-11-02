"""The SQL orders must stay identical to the domain's own.

`sqlite_repository` re-expresses `sort_listings` in SQL to cut its candidate window
on the requested key. Two representations of one rule drift silently — these tests
fail the moment they disagree.
"""

from dataclasses import replace
from datetime import UTC as _UTC_ZONE
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

from apartment_hunter.domain.entities import Listing
from apartment_hunter.domain.services import sort_listings
from apartment_hunter.domain.value_objects import ListingSort, Price
from apartment_hunter.infrastructure.storage.sqlite_repository import SqliteRepository
from tests.fakes.builders import build_listing, build_search_filter

_LISTINGS = 12  # enough for ties on price and surface to show up
_CANDIDATE_LIMIT = 100  # above _LISTINGS, so the window never truncates the comparison


async def _open_repository(tmp_path: Path) -> SqliteRepository:
    repository = SqliteRepository(str(tmp_path / "hunter.db"))
    await repository.connect()
    return repository


def _build_varied_listings() -> list[Listing]:
    """Listings with repeated prices and surfaces, one of them without a surface.

    Values are stepped rather than faked on purpose: the parity being tested is about
    ties, and a random draw would only hit them by luck.
    """
    listings: list[Listing] = []
    for index in range(_LISTINGS):
        amount = Decimal(str(700 + (index % 4) * 50))  # repeats → ties to break
        charges = Decimal(str(30 * (index % 3))) if index % 2 else None
        listings.append(
            replace(
                build_listing(
                    surface_m2=float(35 + (index % 5) * 10),
                    published_offset_minutes=index * 37,
                ),
                price=Price(amount=amount, charges=charges),
            )
        )
    listings[-1] = replace(listings[-1], surface_m2=None)
    return listings


# The position has no SQL form (it needs the Carte des loyers): the store cuts its window
# on €/m² instead, which this test does hold.
@pytest.mark.parametrize("sort", [s for s in ListingSort if s.window_sort is s])
async def test_sql_order_matches_the_domain_order(tmp_path: Path, sort: ListingSort) -> None:
    # Arrange
    repository = await _open_repository(tmp_path)
    listings = _build_varied_listings()
    await repository.save_many(listings)
    stored = await repository.list_all()

    # Act
    from_sql = await repository.find_top(
        build_search_filter(max_price=100_000, max_dpe_rating=None),
        limit=_CANDIDATE_LIMIT,
        sort=sort,
    )

    # Assert
    assert [listing.id for listing in from_sql] == [
        listing.id for listing in sort_listings(stored, sort)
    ]
    await repository.close()


async def test_stores_a_timezone_aware_parution_as_naive_local_time(tmp_path: Path) -> None:
    # Arrange — SeLoger-style aware ISO date
    repository = await _open_repository(tmp_path)
    local_now = datetime.now().replace(microsecond=0)
    aware = replace(build_listing(), published_at=local_now.astimezone())

    # Act
    await repository.save_many([aware])
    stored = (await repository.list_all())[0]

    # Assert — one comparable storage format, and the same instant read back
    assert stored.published_at.tzinfo is None
    assert stored.published_at == local_now
    await repository.close()


async def test_normalises_a_legacy_offset_row_on_connect(tmp_path: Path) -> None:
    # Arrange — a row written before parution dates were stored as naive local time
    db_path = tmp_path / "hunter.db"
    repository = SqliteRepository(str(db_path))
    await repository.connect()
    listing = build_listing()
    await repository.save_many([listing])
    local_now = datetime.now().replace(microsecond=0)
    legacy = local_now.astimezone(_UTC_ZONE).isoformat()
    await repository._conn.execute(  # noqa: SLF001 — simulating an older schema's write
        "UPDATE listings SET published_at = ? WHERE id = ?", (legacy, listing.id)
    )
    await repository._conn.commit()  # noqa: SLF001
    await repository.close()

    # Act — reopening runs the data migrations
    reopened = SqliteRepository(str(db_path))
    await reopened.connect()
    stored = (await reopened.list_all())[0]

    # Assert
    assert stored.published_at.tzinfo is None
    assert stored.published_at == local_now
    await reopened.close()


async def test_excludes_a_listing_older_than_the_max_age_window(tmp_path: Path) -> None:
    # Arrange
    repository = await _open_repository(tmp_path)
    fresh = build_listing(published_offset_minutes=60)
    stale = replace(build_listing(), published_at=datetime.now() - timedelta(hours=25))
    await repository.save_many([fresh, stale])
    search_filter = build_search_filter(max_price=100_000, max_dpe_rating=None)
    search_filter.max_age_days = 1

    # Act
    candidates = await repository.find_top(search_filter, limit=_CANDIDATE_LIMIT)

    # Assert
    assert [listing.id for listing in candidates] == [fresh.id]
    await repository.close()
