# SQL name of `fold_commune_name`, registered on the connection before the data
# migrations run: SQLite cannot strip an accent on its own.
FOLD_COMMUNE_SQL_FUNCTION = "fold_commune_name"

MIGRATIONS: list[str] = [
    # v1 — initial schema
    """
    CREATE TABLE IF NOT EXISTS listings (
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
        advertiser TEXT,
        opened_at TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS filters (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        config TEXT NOT NULL,
        enabled INTEGER NOT NULL DEFAULT 1,
        created_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS notifications (
        listing_id TEXT NOT NULL REFERENCES listings(id),
        filter_id TEXT NOT NULL REFERENCES filters(id),
        notified_at TEXT NOT NULL,
        PRIMARY KEY (listing_id, filter_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS schema_version (version INTEGER PRIMARY KEY)
    """,
]

# Tables added after the first release, replayed on every startup like the index set:
# the MIGRATIONS block above only runs on a fresh install.
#
# `dismissals` has no foreign key to `listings` on purpose: the purge deletes listing
# rows, and a dismissal must outlive them (ADR-0009).
TABLE_MIGRATIONS: list[str] = [
    """
    CREATE TABLE IF NOT EXISTS dismissals (
        listing_id TEXT PRIMARY KEY,
        source TEXT NOT NULL,
        home_city TEXT,
        home_rooms INTEGER,
        home_surface_m2 INTEGER,
        home_rent TEXT,
        reason TEXT NOT NULL,
        note TEXT NOT NULL DEFAULT '',
        dismissed_at TEXT NOT NULL,
        total_price TEXT NOT NULL,
        surface_m2 REAL,
        floor_level INTEGER,
        dpe_rating TEXT,
        advertiser TEXT,
        furnished INTEGER,
        restored_at TEXT
    )
    """,
    # When each source last answered each filter's crawl: what tells an expired listing
    # from one whose source is down (ticket 13). Dropped with its filter.
    """
    CREATE TABLE IF NOT EXISTS filter_source_successes (
        filter_id TEXT NOT NULL,
        source TEXT NOT NULL,
        answered_at TEXT NOT NULL,
        PRIMARY KEY (filter_id, source)
    )
    """,
    # Settings the hunter chooses for every crawl, one row per key (ADR-0012).
    """
    CREATE TABLE IF NOT EXISTS app_settings (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL
    )
    """,
    # The first time the hunter opened each listing, with what recognises its home. No
    # link to `listings`: an opening must outlive the purge (ADR-0009).
    """
    CREATE TABLE IF NOT EXISTS openings (
        listing_id TEXT PRIMARY KEY,
        source TEXT NOT NULL,
        home_city TEXT,
        home_rooms INTEGER,
        home_surface_m2 INTEGER,
        home_rent TEXT,
        opened_at TEXT NOT NULL
    )
    """,
    # A refused criterion suggestion, so it is not asked again before three more
    # dismissals of that reason and value. No link to `listings`: the purge never
    # erases a refusal. Dropped with its filter.
    """
    CREATE TABLE IF NOT EXISTS criterion_refusals (
        filter_id TEXT NOT NULL,
        reason TEXT NOT NULL,
        value TEXT NOT NULL,
        refused_at TEXT NOT NULL,
        dismissal_count INTEGER NOT NULL,
        PRIMARY KEY (filter_id, reason, value)
    )
    """,
]

# Renames, run before the column adds so those see the new names. Idempotent by
# failure: replaying one on an already-renamed database raises, and the raise is
# ignored — SQLite has no `ALTER TABLE ... RENAME IF EXISTS`.
#
# The stored row was called an "apartment" and its publisher an "agency"; the glossary
# calls them a listing and an advertiser, and a private landlord is no agency. SQLite
# rewrites the foreign keys pointing at the renamed table on its own.
RENAME_MIGRATIONS: list[str] = [
    "ALTER TABLE apartments RENAME TO listings",
    "ALTER TABLE listings RENAME COLUMN agency TO advertiser",
    "ALTER TABLE notifications RENAME COLUMN apartment_id TO listing_id",
    # An index keeps its own name through a table rename; drop the stale ones and let
    # INDEX_MIGRATIONS recreate them under the new names.
    "DROP INDEX IF EXISTS idx_apartments_published",
    "DROP INDEX IF EXISTS idx_apartments_source",
]

# The only home of the index set, replayed on every startup rather than only on a
# fresh install: a database born before an index existed would otherwise never get
# it, and would run the notification lookup as a full scan for good.
INDEX_MIGRATIONS: list[str] = [
    "CREATE INDEX IF NOT EXISTS idx_listings_published ON listings(published_at DESC)",
    "CREATE INDEX IF NOT EXISTS idx_listings_source ON listings(source)",
    "CREATE INDEX IF NOT EXISTS idx_notifications_filter ON notifications(filter_id)",
]

# Idempotent column additions, run on every startup so pre-existing databases
# pick up new columns (the migration block above only runs on first install).
# Each is wrapped to ignore the "duplicate column name" error.
COLUMN_MIGRATIONS: list[str] = [
    "ALTER TABLE listings ADD COLUMN ges_rating TEXT",
    # Rows written before this column existed hold a first-crawl timestamp, which is
    # exactly what 'first_seen' means — so the default backfills them correctly.
    "ALTER TABLE listings ADD COLUMN published_at_source TEXT NOT NULL DEFAULT 'first_seen'",
    # Read by nothing since the `openings` table: kept so the migration that empties it
    # into openings finds it on a database born before it existed.
    "ALTER TABLE listings ADD COLUMN opened_at TEXT",
    # Filled from `fetched_at` by DATA_MIGRATIONS for rows stored before it existed.
    "ALTER TABLE listings ADD COLUMN last_seen_at TEXT",
    # NULL = in force. A restored dismissal stays as the trace ADR-0009 asks for. On a
    # fresh install the table does not exist yet here: TABLE_MIGRATIONS creates it whole.
    "ALTER TABLE dismissals ADD COLUMN restored_at TEXT",
]

# Idempotent data normalisations, run on every startup.
# `published_at` is stored as naive local ISO so `ORDER BY published_at` and the
# `max_age_days` window compare like with like. Rows written before that rule (SeLoger
# and Logic-Immo sent tz-aware ISO) carry an offset and would sort against local ones
# shifted by that offset — convert them once. The WHERE clause looks at the time part
# only, so the date's own dashes never match the offset sign.
DATA_MIGRATIONS: list[str] = [
    """
    UPDATE listings
    SET published_at = strftime('%Y-%m-%dT%H:%M:%S', published_at, 'localtime')
    WHERE published_at LIKE '%Z'
       OR instr(substr(published_at, 12), '+') > 0
       OR instr(substr(published_at, 12), '-') > 0
    """,
    # A dismissal written before the home key folded its commune holds the site's own
    # spelling ("Chambéry"), and would never meet the folded key of the same home
    # re-published as "Chambery". The fold is idempotent, so replaying is a no-op.
    f"""
    UPDATE dismissals
    SET home_city = {FOLD_COMMUNE_SQL_FUNCTION}(home_city)
    WHERE home_city IS NOT NULL
      AND home_city != {FOLD_COMMUNE_SQL_FUNCTION}(home_city)
    """,
    # A row stored before `last_seen_at` was last seen, as far as we know, when first seen.
    "UPDATE listings SET last_seen_at = fetched_at WHERE last_seen_at IS NULL",
]
