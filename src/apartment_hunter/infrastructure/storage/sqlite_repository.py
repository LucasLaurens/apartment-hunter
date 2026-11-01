import json
from datetime import datetime
from decimal import Decimal

import aiosqlite
from loguru import logger

from ...domain.entities import (
    Dismissal,
    Listing,
    Opening,
    SearchFilter,
)
from ...domain.ports import ListingRepositoryPort
from ...domain.services import (
    MAX_DESCRIPTION_CHARS,
    CriterionRefusal,
    build_opening,
    build_published_key,
    clean_text,
    fold_commune_name,
    is_web_url,
)
from ...domain.value_objects import (
    DEFAULT_LISTING_SORT,
    DismissalReason,
    DpeRating,
    Floor,
    ListingSort,
    Location,
    Price,
    PublicationSource,
    SiteRules,
)
from .dismissal_codec import DISMISSAL_COLUMNS, dismissal_from_row, dismissal_to_row
from .filter_codec import filter_from_json, filter_to_json
from .migrations import (
    COLUMN_MIGRATIONS,
    DATA_MIGRATIONS,
    FOLD_COMMUNE_SQL_FUNCTION,
    INDEX_MIGRATIONS,
    MIGRATIONS,
    RENAME_MIGRATIONS,
    TABLE_MIGRATIONS,
)
from .opening_codec import OPENING_COLUMNS, opening_from_row, opening_to_row

# The SQL pass is a coarse pre-filter: ListingMatcher does the real work in the
# domain, so the query keeps a margin rather than cutting exactly at the bounds.
_PRICE_SLACK_RATIO = 0.2  # ±20% — nearby towns priced just outside stay candidates
_CANDIDATES_PER_RESULT = 50  # rows read per wanted result (most get filtered out)
_MAX_CANDIDATES = 500  # hard cap on one query, whatever the requested limit
_UNNOTIFIED_LIMIT = 200  # newest unnotified rows considered per notification run
_SITE_RULES_KEY = "site_rules"
# OR IGNORE: the first opening of a listing is the one kept.
_INSERT_OPENING_SQL = (
    f"INSERT OR IGNORE INTO openings ({', '.join(OPENING_COLUMNS)}) "
    f"VALUES ({', '.join('?' * len(OPENING_COLUMNS))})"
)

# Prices are stored as text (Decimal round-trip), surface may be NULL — mirror the
# domain's own keys: total = rent + charges, unknown surface sinks to the bottom.
_PRICE_TOTAL_SQL = "CAST(price_amount AS REAL) + COALESCE(CAST(price_charges AS REAL), 0)"
_SURFACE_SQL = "COALESCE(surface_m2, 0)"
_NEWEST_FIRST_SQL = "published_at DESC"  # canonical naive-local ISO sorts lexicographically
_NO_SURFACE_LAST_SQL = "(surface_m2 IS NULL OR surface_m2 = 0)"

# Same orders as `domain.services.listing_order.sort_listings`, expressed in SQL so the
# candidate window is cut on the requested key. `tests/infrastructure/
# test_sqlite_sort_parity.py` fails if the two ever disagree.
_ORDER_BY: dict[ListingSort, str] = {
    ListingSort.PUBLISHED_DESC: _NEWEST_FIRST_SQL,
    ListingSort.PRICE_ASC: f"{_PRICE_TOTAL_SQL} ASC, {_NEWEST_FIRST_SQL}",
    ListingSort.PRICE_DESC: f"{_PRICE_TOTAL_SQL} DESC, {_NEWEST_FIRST_SQL}",
    ListingSort.SURFACE_DESC: f"{_SURFACE_SQL} DESC, {_NEWEST_FIRST_SQL}",
    ListingSort.PRICE_PER_M2_ASC: (
        f"{_NO_SURFACE_LAST_SQL}, ({_PRICE_TOTAL_SQL}) / NULLIF(surface_m2, 0) ASC,"
        f" {_NEWEST_FIRST_SQL}"
    ),
}


def _has_known_floor(listing: Listing) -> bool:
    """True when the crawler actually read a storey — `Floor.unknown()` is not one."""
    return listing.floor is not None and listing.floor.is_known


def _has_detail_values(listing: Listing) -> bool:
    """True when this crawl read at least one field the backfill can write."""
    return bool(
        listing.dpe_rating
        or listing.ges_rating
        or _has_known_floor(listing)
        or listing.furnished is not None
    )


def _build_floor_columns(listing: Listing) -> dict[str, str | int | None]:
    if not _has_known_floor(listing):
        return {"floor_level": None, "floor_is_top": None}
    assert listing.floor is not None
    return {"floor_level": listing.floor.level, "floor_is_top": int(listing.floor.is_top)}


class SqliteRepository(ListingRepositoryPort):
    def __init__(self, db_path: str):
        self._db_path = db_path
        self._db: aiosqlite.Connection | None = None

    async def connect(self) -> None:
        self._db = await aiosqlite.connect(self._db_path)
        self._db.row_factory = aiosqlite.Row
        await self._db.execute("PRAGMA journal_mode=WAL")
        await self._db.execute("PRAGMA foreign_keys=ON")
        await self._run_migrations()

    async def close(self) -> None:
        if self._db:
            await self._db.close()

    async def _run_migrations(self) -> None:
        assert self._db is not None
        async with self._db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='schema_version'"
        ) as cur:
            exists = await cur.fetchone()

        if not exists:
            for statement in MIGRATIONS:
                await self._db.execute(statement)
            await self._db.execute(
                "INSERT OR IGNORE INTO schema_version VALUES (?)", (len(MIGRATIONS),)
            )
            await self._db.commit()
            logger.info("DB migrations applied")

        # Renames first: the column adds below address the new names.
        for statement in RENAME_MIGRATIONS:
            try:
                await self._db.execute(statement)
            except Exception:
                pass  # already renamed, or the old name never existed
        # Idempotent column adds for databases created before these columns existed.
        for statement in COLUMN_MIGRATIONS:
            try:
                await self._db.execute(statement)
            except Exception:
                pass  # column already present
        for statement in TABLE_MIGRATIONS:
            await self._db.execute(statement)
        for statement in INDEX_MIGRATIONS:
            await self._db.execute(statement)
        await self._db.create_function(
            FOLD_COMMUNE_SQL_FUNCTION, 1, fold_commune_name, deterministic=True
        )
        for statement in DATA_MIGRATIONS:
            await self._db.execute(statement)
        await self._migrate_row_openings()
        await self._db.commit()

    async def _migrate_row_openings(self) -> None:
        """Turn each `listings.opened_at` into an opening, then clear it: once only.

        In Python, not SQL: the home key folds the commune and rounds the surface the
        way `build_home_key` does, and a second copy of that rule in SQL would drift.
        """
        async with self._conn.execute("SELECT * FROM listings WHERE opened_at IS NOT NULL") as cur:
            rows = await cur.fetchall()
        if not rows:
            return
        openings = [
            build_opening(self._from_row(row), datetime.fromisoformat(row["opened_at"]))
            for row in rows
        ]
        await self._conn.executemany(_INSERT_OPENING_SQL, [opening_to_row(o) for o in openings])
        await self._conn.execute("UPDATE listings SET opened_at = NULL")
        logger.info(f"{len(openings)} listing openings moved to the openings table")

    @property
    def _conn(self) -> aiosqlite.Connection:
        assert self._db is not None, "Call connect() before using repository"
        return self._db

    async def save_many(self, listings: list[Listing]) -> int:
        storable = self._keep_storable(listings)
        rows = [self._to_row(listing) for listing in storable]
        async with self._conn.executemany(
            """
            INSERT OR IGNORE INTO listings (
                id, url, title, source, city, postal_code, latitude, longitude,
                full_address, price_amount, price_charges, surface_m2, rooms,
                floor_level, floor_is_top, dpe_rating, ges_rating, furnished, charges_included,
                collective_heating, published_at, published_at_source, fetched_at,
                last_seen_at, description, images, advertiser
            ) VALUES (
                :id, :url, :title, :source, :city, :postal_code, :latitude, :longitude,
                :full_address, :price_amount, :price_charges, :surface_m2, :rooms,
                :floor_level, :floor_is_top, :dpe_rating, :ges_rating, :furnished,
                :charges_included,
                :collective_heating, :published_at, :published_at_source, :fetched_at,
                :last_seen_at, :description, :images, :advertiser
            )
            """,
            rows,
        ) as cur:
            new_count = cur.rowcount
        await self._backfill_site_dates(storable)
        await self._backfill_detail_fields(storable)
        await self._update_price_and_place(storable)
        await self._update_last_seen(storable)
        await self._conn.commit()
        return max(new_count, 0)

    @staticmethod
    def _keep_storable(listings: list[Listing]) -> list[Listing]:
        """Only the listings a browser may safely open and a hunter can compare.

        A site is free to print `href="javascript:…"`; stored, that link would later be
        rendered as the card's title anchor. A rent read as 0 € is a parse that failed,
        not a free flat: it passed every budget and sorted first by price (W5). Dropping
        both here keeps every reader — web UI, e-mail, terminal — clear of them.
        """
        linked = [listing for listing in listings if is_web_url(listing.url)]
        if (dropped := len(listings) - len(linked)) > 0:
            logger.warning(f"Dropped {dropped} listing(s) with a non-http(s) URL")
        priced = [listing for listing in linked if listing.price.total > 0]
        if (unpriced := len(linked) - len(priced)) > 0:
            logger.warning(f"Dropped {unpriced} listing(s) whose rent could not be read")
        return priced

    async def _backfill_site_dates(self, listings: list[Listing]) -> None:
        """Upgrade already-stored rows once their source starts publishing a date.

        Inserts are INSERT OR IGNORE, so a listing first seen before its site date was
        readable would keep the first-crawl fallback forever. Rows that already hold a
        site date are left alone — re-reading it must not shuffle the age ranking.
        """
        dated = [
            {"id": listing.id, "published_at": build_published_key(listing).isoformat()}
            for listing in listings
            if listing.has_site_publication_date
        ]
        if not dated:
            return
        await self._conn.executemany(
            f"""
            UPDATE listings
            SET published_at = :published_at,
                published_at_source = '{PublicationSource.SITE.value}'
            WHERE id = :id AND published_at_source != '{PublicationSource.SITE.value}'
            """,
            dated,
        )

    async def _backfill_detail_fields(self, listings: list[Listing]) -> None:
        """Write what the detail page adds — DPE, GES, storey, furnishing — onto stored rows.

        Inserts are INSERT OR IGNORE, so a listing first seen while its detail page was
        unreadable — or read by a parser that got the value wrong — would keep that
        blank forever, and the DPE, floor and furnished filters would keep letting it
        through. A crawl that reads a value therefore overwrites; one that reads nothing
        (COALESCE) leaves the stored value alone.
        """
        enriched: list[dict[str, str | int | None]] = [
            {
                "id": listing.id,
                "dpe_rating": listing.dpe_rating.value if listing.dpe_rating else None,
                "ges_rating": listing.ges_rating.value if listing.ges_rating else None,
                "furnished": int(listing.furnished) if listing.furnished is not None else None,
                **_build_floor_columns(listing),
            }
            for listing in listings
            if _has_detail_values(listing)
        ]
        if not enriched:
            return
        await self._conn.executemany(
            """
            UPDATE listings
            SET dpe_rating = COALESCE(:dpe_rating, dpe_rating),
                ges_rating = COALESCE(:ges_rating, ges_rating),
                floor_level = COALESCE(:floor_level, floor_level),
                floor_is_top = COALESCE(:floor_is_top, floor_is_top),
                furnished = COALESCE(:furnished, furnished)
            WHERE id = :id
            """,
            enriched,
        )

    async def _update_price_and_place(self, listings: list[Listing]) -> None:
        """Follow the source's rent, commune and title on rows this crawl returned again.

        Inserts are INSERT OR IGNORE, so a rent lowered on the same ad stayed at its first
        reading: every reader showed a stale total, and a home dismissed as too expensive
        never came back (ADR-0009). `_keep_storable` already dropped the 0 € misreads;
        charges read as nothing leave the stored ones alone, as detail fields do. The
        commune and the title built from it follow for the same reason: rows stored under
        the *searched* commune (ParuVendu, Foncia) are corrected on the next crawl.
        """
        await self._conn.executemany(
            """
            UPDATE listings
            SET price_amount = :price_amount,
                price_charges = COALESCE(:price_charges, price_charges),
                title = :title,
                city = :city,
                postal_code = COALESCE(:postal_code, postal_code)
            WHERE id = :id
            """,
            [
                {
                    "id": listing.id,
                    "price_amount": str(listing.price.amount),
                    "title": clean_text(listing.title),
                    "city": clean_text(listing.location.city),
                    "postal_code": clean_text(listing.location.postal_code),
                    "price_charges": (
                        str(listing.price.charges) if listing.price.charges is not None else None
                    ),
                }
                for listing in listings
            ],
        )

    async def _update_last_seen(self, listings: list[Listing]) -> None:
        """Move `last_seen_at` forward on rows this crawl returned again.

        Never backwards: two filters crawled concurrently may save the same URL out of
        order. Naive-local ISO strings compare like the datetimes they encode.
        """
        await self._conn.executemany(
            """
            UPDATE listings SET last_seen_at = :last_seen_at
            WHERE id = :id AND last_seen_at < :last_seen_at
            """,
            [
                {"id": listing.id, "last_seen_at": listing.last_seen_at.isoformat()}
                for listing in listings
            ],
        )

    async def find_new_since(self, filter_id: str) -> list[Listing]:
        async with self._conn.execute(
            """
            SELECT a.* FROM listings a
            WHERE NOT EXISTS (
                SELECT 1 FROM notifications n
                WHERE n.listing_id = a.id AND n.filter_id = ?
            )
            ORDER BY a.published_at DESC
            LIMIT ?
            """,
            (filter_id, _UNNOTIFIED_LIMIT),
        ) as cur:
            rows = await cur.fetchall()
        return [self._from_row(row) for row in rows]

    async def mark_notified(self, listing_ids: list[str], filter_id: str) -> None:
        now = datetime.now().isoformat()
        await self._conn.executemany(
            "INSERT OR IGNORE INTO notifications (listing_id, filter_id, notified_at) "
            "VALUES (?, ?, ?)",
            [(apt_id, filter_id, now) for apt_id in listing_ids],
        )
        await self._conn.commit()

    async def save_opening(self, opening: Opening) -> None:
        await self._conn.execute(_INSERT_OPENING_SQL, opening_to_row(opening))
        await self._conn.commit()

    async def list_openings(self) -> list[Opening]:
        async with self._conn.execute("SELECT * FROM openings") as cur:
            rows = await cur.fetchall()
        return [opening_from_row(row) for row in rows]

    async def find_top(
        self,
        search_filter: SearchFilter,
        limit: int = 10,
        sort: ListingSort = DEFAULT_LISTING_SORT,
    ) -> list[Listing]:
        # Coarse SQL pre-filter; geo-radius and full matching done by ListingMatcher in domain
        params: list[str | int | float] = []
        conditions: list[str] = []

        if search_filter.max_price:
            conditions.append("CAST(price_amount AS REAL) <= ?")
            params.append(search_filter.max_price * (1 + _PRICE_SLACK_RATIO))
        if search_filter.min_price:
            conditions.append("CAST(price_amount AS REAL) >= ?")
            params.append(search_filter.min_price * (1 - _PRICE_SLACK_RATIO))
        if search_filter.max_age_days is not None:
            # datetime() on both sides: the stored value keeps the ISO 'T' separator,
            # which would compare greater than SQLite's space-separated own format.
            conditions.append(
                "datetime(published_at) >= datetime('now', 'localtime', '-' || ? || ' days')"
            )
            params.append(search_filter.max_age_days)
        if search_filter.accepted_dpe_ratings:
            allowed = [r.value for r in search_filter.accepted_dpe_ratings]
            dpe_placeholders = ",".join("?" * len(allowed))
            conditions.append(f"(dpe_rating IS NULL OR dpe_rating IN ({dpe_placeholders}))")
            params.extend(allowed)

        where_clause = ("WHERE " + " AND ".join(conditions)) if conditions else ""
        params.append(min(limit * _CANDIDATES_PER_RESULT, _MAX_CANDIDATES))

        query = f"""
            SELECT * FROM listings
            {where_clause}
            ORDER BY {_ORDER_BY[sort.window_sort]}
            LIMIT ?
        """

        async with self._conn.execute(query, params) as cur:
            rows = await cur.fetchall()
        return [self._from_row(row) for row in rows]

    async def find_listing(self, listing_id: str) -> Listing | None:
        async with self._conn.execute("SELECT * FROM listings WHERE id = ?", (listing_id,)) as cur:
            row = await cur.fetchone()
        return self._from_row(row) if row is not None else None

    async def list_all(self) -> list[Listing]:
        async with self._conn.execute("SELECT * FROM listings") as cur:
            rows = await cur.fetchall()
        return [self._from_row(row) for row in rows]

    async def delete_many(self, listing_ids: list[str]) -> int:
        if not listing_ids:
            return 0
        params = [(apt_id,) for apt_id in listing_ids]
        # Drop notification rows first — FK has no ON DELETE CASCADE, and a stale
        # notification would silently suppress re-notifying a re-listed listing.
        await self._conn.executemany("DELETE FROM notifications WHERE listing_id = ?", params)
        async with self._conn.executemany("DELETE FROM listings WHERE id = ?", params) as cur:
            deleted = cur.rowcount
        await self._conn.commit()
        return max(deleted, 0)

    async def save_dismissal(self, dismissal: Dismissal) -> None:
        placeholders = ", ".join("?" * len(DISMISSAL_COLUMNS))
        await self._conn.execute(
            f"INSERT OR REPLACE INTO dismissals ({', '.join(DISMISSAL_COLUMNS)}) "
            f"VALUES ({placeholders})",
            dismissal_to_row(dismissal),
        )
        await self._conn.commit()

    async def list_dismissals(self) -> list[Dismissal]:
        async with self._conn.execute(
            "SELECT * FROM dismissals WHERE restored_at IS NULL ORDER BY dismissed_at"
        ) as cur:
            rows = await cur.fetchall()
        return [dismissal_from_row(row) for row in rows]

    async def list_restored_dismissals(self) -> list[Dismissal]:
        async with self._conn.execute(
            "SELECT * FROM dismissals WHERE restored_at IS NOT NULL"
        ) as cur:
            rows = await cur.fetchall()
        return [dismissal_from_row(row) for row in rows]

    async def save_source_successes(
        self, filter_id: str, sources: frozenset[str], answered_at: datetime
    ) -> None:
        await self._conn.executemany(
            "INSERT OR REPLACE INTO filter_source_successes (filter_id, source, answered_at) "
            "VALUES (?, ?, ?)",
            [(filter_id, source, answered_at.isoformat()) for source in sources],
        )
        await self._conn.commit()

    async def find_source_successes(self, filter_id: str) -> dict[str, datetime]:
        async with self._conn.execute(
            "SELECT source, answered_at FROM filter_source_successes WHERE filter_id = ?",
            (filter_id,),
        ) as cur:
            rows = await cur.fetchall()
        return {row["source"]: datetime.fromisoformat(row["answered_at"]) for row in rows}

    async def save_criterion_refusal(self, refusal: CriterionRefusal) -> None:
        await self._conn.execute(
            "INSERT OR REPLACE INTO criterion_refusals"
            " (filter_id, reason, value, refused_at, dismissal_count) VALUES (?, ?, ?, ?, ?)",
            (
                refusal.filter_id,
                refusal.reason.value,
                refusal.value,
                refusal.refused_at.isoformat(),
                refusal.dismissal_count,
            ),
        )
        await self._conn.commit()

    async def list_criterion_refusals(self) -> list[CriterionRefusal]:
        async with self._conn.execute("SELECT * FROM criterion_refusals") as cur:
            rows = await cur.fetchall()
        return [
            CriterionRefusal(
                filter_id=row["filter_id"],
                reason=DismissalReason(row["reason"]),
                value=row["value"],
                refused_at=datetime.fromisoformat(row["refused_at"]),
                dismissal_count=row["dismissal_count"],
            )
            for row in rows
        ]

    async def save_restoration(self, listing_id: str, restored_at: datetime) -> None:
        await self._conn.execute(
            "UPDATE dismissals SET restored_at = ? WHERE listing_id = ? AND restored_at IS NULL",
            (restored_at.isoformat(), listing_id),
        )
        await self._conn.commit()

    async def load_site_rules(self) -> SiteRules:
        async with self._conn.execute(
            "SELECT value FROM app_settings WHERE key = ?", (_SITE_RULES_KEY,)
        ) as cur:
            row = await cur.fetchone()
        return SiteRules(row["value"]) if row else SiteRules.HONOURED

    async def save_site_rules(self, rules: SiteRules) -> None:
        await self._conn.execute(
            "INSERT OR REPLACE INTO app_settings (key, value) VALUES (?, ?)",
            (_SITE_RULES_KEY, rules.value),
        )
        await self._conn.commit()

    async def save_filter(self, search_filter: SearchFilter) -> None:
        config = filter_to_json(search_filter)
        await self._conn.execute(
            """
            INSERT OR REPLACE INTO filters (id, name, config, enabled, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                search_filter.id,
                search_filter.name,
                config,
                int(search_filter.enabled),
                search_filter.created_at.isoformat(),
            ),
        )
        await self._conn.commit()

    async def load_filters(self) -> list[SearchFilter]:
        async with self._conn.execute("SELECT * FROM filters ORDER BY created_at DESC") as cur:
            rows = await cur.fetchall()
        return [filter_from_json(dict(row)) for row in rows]

    async def delete_filter(self, filter_id: str) -> None:
        """Drop the filter and the alerts it sent.

        `notifications` references `filters(id)` with no ON DELETE clause and
        `connect()` turns FK enforcement on, so deleting a filter that has ever
        alerted raised `IntegrityError` and the caller saw a 500. Same order as
        `delete_many`: the referencing rows go first.
        """
        await self._conn.execute("DELETE FROM notifications WHERE filter_id = ?", (filter_id,))
        await self._conn.execute("DELETE FROM criterion_refusals WHERE filter_id = ?", (filter_id,))
        await self._conn.execute(
            "DELETE FROM filter_source_successes WHERE filter_id = ?", (filter_id,)
        )
        await self._conn.execute("DELETE FROM filters WHERE id = ?", (filter_id,))
        await self._conn.commit()

    @staticmethod
    def _to_row(listing: Listing) -> dict[str, str | int | float | None]:
        return {
            "id": listing.id,
            "url": listing.url,
            # Scraped text is third-party input: null bytes out, length capped.
            "title": clean_text(listing.title),
            "source": listing.source,
            "city": clean_text(listing.location.city),
            "postal_code": clean_text(listing.location.postal_code),
            "latitude": listing.location.latitude,
            "longitude": listing.location.longitude,
            "full_address": clean_text(listing.location.full_address),
            "price_amount": str(listing.price.amount),
            "price_charges": str(listing.price.charges) if listing.price.charges else None,
            "surface_m2": listing.surface_m2,
            "rooms": listing.rooms,
            "floor_level": listing.floor.level if listing.floor else None,
            "floor_is_top": int(listing.floor.is_top) if listing.floor else None,
            "dpe_rating": listing.dpe_rating.value if listing.dpe_rating else None,
            "ges_rating": listing.ges_rating.value if listing.ges_rating else None,
            "furnished": int(listing.furnished) if listing.furnished is not None else None,
            "charges_included": (
                int(listing.charges_included) if listing.charges_included is not None else None
            ),
            "collective_heating": (
                int(listing.collective_heating) if listing.collective_heating is not None else None
            ),
            # Canonical naive-local ISO: one comparable format for ORDER BY and the
            # `max_age_days` window, whatever timezone the source advertised.
            "published_at": build_published_key(listing).isoformat(),
            "published_at_source": listing.published_at_source.value,
            "fetched_at": listing.fetched_at.isoformat(),
            "last_seen_at": listing.last_seen_at.isoformat(),
            "description": clean_text(listing.description, MAX_DESCRIPTION_CHARS),
            "images": json.dumps([url for url in listing.images if is_web_url(url)]),
            "advertiser": clean_text(listing.advertiser),
        }

    @staticmethod
    def _from_row(row: aiosqlite.Row) -> Listing:
        r = dict(row)

        floor: Floor | None = None
        if r.get("floor_level") is not None:
            floor = Floor(level=r["floor_level"], is_top=bool(r.get("floor_is_top")))

        images_raw = r.get("images", "[]")
        try:
            images = tuple(json.loads(images_raw))
        except (json.JSONDecodeError, TypeError):
            images = ()

        return Listing(
            id=r["id"],
            url=r["url"],
            title=r["title"],
            source=r["source"],
            location=Location(
                city=r["city"],
                postal_code=r.get("postal_code"),
                latitude=r.get("latitude"),
                longitude=r.get("longitude"),
                full_address=r.get("full_address"),
            ),
            price=Price(
                amount=Decimal(str(r["price_amount"])),
                charges=Decimal(str(r["price_charges"])) if r.get("price_charges") else None,
            ),
            surface_m2=r.get("surface_m2"),
            rooms=r.get("rooms"),
            floor=floor,
            dpe_rating=DpeRating.from_string(r["dpe_rating"]) if r.get("dpe_rating") else None,
            ges_rating=DpeRating.from_string(r["ges_rating"]) if r.get("ges_rating") else None,
            furnished=bool(r["furnished"]) if r.get("furnished") is not None else None,
            charges_included=(
                bool(r["charges_included"]) if r.get("charges_included") is not None else None
            ),
            collective_heating=(
                bool(r["collective_heating"]) if r.get("collective_heating") is not None else None
            ),
            published_at=datetime.fromisoformat(r["published_at"]),
            published_at_source=PublicationSource(
                r.get("published_at_source") or PublicationSource.FIRST_SEEN.value
            ),
            fetched_at=datetime.fromisoformat(r["fetched_at"]),
            last_seen_at=datetime.fromisoformat(r["last_seen_at"]),
            description=r.get("description"),
            images=images,
            advertiser=r.get("advertiser"),
        )
