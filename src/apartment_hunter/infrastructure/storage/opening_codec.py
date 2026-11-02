"""Row shape of an opening: the `openings` table, one row per opened listing."""

from datetime import datetime

import aiosqlite

from ...domain.entities import Opening
from .home_key_codec import HOME_KEY_COLUMNS, home_key_from_row, home_key_to_row

OPENING_COLUMNS = ("listing_id", "source", *HOME_KEY_COLUMNS, "opened_at")


def opening_to_row(opening: Opening) -> tuple[str | int | None, ...]:
    return (
        opening.listing_id,
        opening.source,
        *home_key_to_row(opening.home_key),
        opening.opened_at.isoformat(),
    )


def opening_from_row(row: aiosqlite.Row) -> Opening:
    r = dict(row)
    return Opening(
        listing_id=r["listing_id"],
        source=r["source"],
        home_key=home_key_from_row(r),
        opened_at=datetime.fromisoformat(r["opened_at"]),
    )
