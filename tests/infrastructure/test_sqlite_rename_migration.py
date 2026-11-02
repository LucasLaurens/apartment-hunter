"""A database written before the rename must open, read and keep its notifications.

The stored row was an `apartments` row with an `agency` column, referenced by
`notifications.apartment_id`. Renaming those in place is the only way an existing
database survives the glossary — a fresh schema beside the old one would silently
hide every listing already crawled.
"""

import sqlite3
from pathlib import Path

from faker import Faker

from apartment_hunter.infrastructure.storage.sqlite_repository import SqliteRepository

_fake = Faker("fr_FR")

_OLD_SCHEMA = """
CREATE TABLE apartments (
    id TEXT PRIMARY KEY,
    url TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    source TEXT NOT NULL,
    city TEXT NOT NULL,
    postal_code TEXT,
    latitude REAL,
    longitude REAL,
    full_address TEXT,
    price_amount TEXT NOT NULL,
    price_charges TEXT,
    surface_m2 REAL,
    rooms INTEGER,
    floor_level INTEGER,
    floor_is_top INTEGER,
    dpe_rating TEXT,
    ges_rating TEXT,
    furnished INTEGER,
    charges_included INTEGER,
    collective_heating INTEGER,
    published_at TEXT NOT NULL,
    published_at_source TEXT NOT NULL DEFAULT 'first_seen',
    fetched_at TEXT NOT NULL,
    description TEXT,
    images TEXT DEFAULT '[]',
    agency TEXT
);
CREATE INDEX idx_apartments_published ON apartments(published_at DESC);
CREATE INDEX idx_apartments_source ON apartments(source);
CREATE TABLE filters (
    id TEXT PRIMARY KEY, name TEXT NOT NULL, config TEXT NOT NULL,
    enabled INTEGER NOT NULL DEFAULT 1, created_at TEXT NOT NULL
);
CREATE TABLE notifications (
    apartment_id TEXT NOT NULL REFERENCES apartments(id),
    filter_id TEXT NOT NULL REFERENCES filters(id),
    notified_at TEXT NOT NULL,
    PRIMARY KEY (apartment_id, filter_id)
);
CREATE TABLE schema_version (version INTEGER PRIMARY KEY);
INSERT INTO schema_version VALUES (8);
"""


def _build_legacy_database(path: Path, listing_id: str, advertiser: str, filter_id: str) -> None:
    """A pre-rename database with one notified row.

    Deliberately missing `idx_notifications_filter`: a database born before that index
    existed must end up with it too, or it runs the notification lookup as a full scan
    for good. That is what makes the schema comparison below worth asserting.
    """
    db = sqlite3.connect(path)
    db.executescript(_OLD_SCHEMA)
    db.execute(
        "INSERT INTO apartments (id, url, title, source, city, price_amount, "
        "published_at, fetched_at, agency) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            listing_id,
            "https://exemple.test/annonce",
            "T3 lumineux",
            "orpi",
            "Annecy",
            "900",
            "2026-08-01T09:00:00",
            "2026-08-01T09:00:00",
            advertiser,
        ),
    )
    db.execute(
        "INSERT INTO filters (id, name, config, created_at) VALUES (?, ?, ?, ?)",
        (filter_id, "Ancien filtre", '{"cities": ["Annecy"]}', "2026-08-01T09:00:00"),
    )
    db.execute(
        "INSERT INTO notifications (apartment_id, filter_id, notified_at) VALUES (?, ?, ?)",
        (listing_id, filter_id, "2026-08-01T09:05:00"),
    )
    db.commit()
    db.close()


async def test_a_legacy_database_keeps_its_listings_and_advertiser(tmp_path: Path) -> None:
    # Arrange
    db_path = tmp_path / "legacy.db"
    advertiser = _fake.company()
    _build_legacy_database(db_path, "abc123", advertiser, "filter01")

    # Act
    repository = SqliteRepository(str(db_path))
    await repository.connect()
    stored = await repository.list_all()

    # Assert — the row is still there, and `agency` came across as `advertiser`
    assert len(stored) == 1
    assert stored[0].advertiser == advertiser
    await repository.close()


async def test_a_legacy_notification_still_suppresses_a_second_alert(tmp_path: Path) -> None:
    # Arrange — the row was already alerted under the old column name
    db_path = tmp_path / "legacy.db"
    _build_legacy_database(db_path, "abc123", _fake.company(), "filter01")
    repository = SqliteRepository(str(db_path))
    await repository.connect()

    # Act
    unnotified = await repository.find_new_since("filter01")

    # Assert — losing this would re-alert every listing already seen
    assert unnotified == []
    await repository.close()


async def test_the_migrated_schema_matches_a_fresh_one(tmp_path: Path) -> None:
    # Arrange
    legacy_path = tmp_path / "legacy.db"
    _build_legacy_database(legacy_path, "abc123", _fake.company(), "filter01")
    migrated = SqliteRepository(str(legacy_path))
    await migrated.connect()
    fresh = SqliteRepository(str(tmp_path / "fresh.db"))
    await fresh.connect()

    # Act
    def read_names(repository: SqliteRepository) -> set[str]:
        db = sqlite3.connect(repository._db_path)  # noqa: SLF001 — schema check
        rows = db.execute("SELECT name FROM sqlite_master WHERE name NOT LIKE 'sqlite_%'")
        found = {row[0] for row in rows}
        db.close()
        return found

    # Assert — one schema, whichever way the database was born
    assert read_names(migrated) == read_names(fresh)
    await migrated.close()
    await fresh.close()


async def test_the_migration_is_replayable(tmp_path: Path) -> None:
    # Arrange
    db_path = tmp_path / "legacy.db"
    _build_legacy_database(db_path, "abc123", _fake.company(), "filter01")

    # Act — every startup replays the renames; the second must be a no-op
    for _ in range(2):
        repository = SqliteRepository(str(db_path))
        await repository.connect()
        stored = await repository.list_all()
        await repository.close()

    # Assert
    assert len(stored) == 1
