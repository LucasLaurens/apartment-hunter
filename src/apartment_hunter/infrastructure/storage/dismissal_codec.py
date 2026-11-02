"""Row shape of a dismissal: the `dismissals` table, one row per dismissed listing."""

from datetime import datetime
from decimal import Decimal

import aiosqlite

from ...domain.entities import Dismissal
from ...domain.services import clean_text
from ...domain.value_objects import DismissalReason, DpeRating
from .home_key_codec import HOME_KEY_COLUMNS, home_key_from_row, home_key_to_row

DISMISSAL_COLUMNS = (
    "listing_id",
    "source",
    *HOME_KEY_COLUMNS,
    "reason",
    "note",
    "dismissed_at",
    "total_price",
    "surface_m2",
    "floor_level",
    "dpe_rating",
    "advertiser",
    "furnished",
)


def dismissal_to_row(dismissal: Dismissal) -> tuple[str | int | float | None, ...]:
    return (
        dismissal.listing_id,
        dismissal.source,
        *home_key_to_row(dismissal.home_key),
        dismissal.reason.value,
        clean_text(dismissal.note),
        dismissal.dismissed_at.isoformat(),
        str(dismissal.total_price),
        dismissal.surface_m2,
        dismissal.floor_level,
        dismissal.dpe_rating.value if dismissal.dpe_rating else None,
        dismissal.advertiser,
        int(dismissal.furnished) if dismissal.furnished is not None else None,
    )


def dismissal_from_row(row: aiosqlite.Row) -> Dismissal:
    r = dict(row)
    return Dismissal(
        listing_id=r["listing_id"],
        source=r["source"],
        home_key=home_key_from_row(r),
        reason=DismissalReason(r["reason"]),
        dismissed_at=datetime.fromisoformat(r["dismissed_at"]),
        total_price=Decimal(r["total_price"]),
        note=r["note"] or "",
        surface_m2=r["surface_m2"],
        floor_level=r["floor_level"],
        dpe_rating=DpeRating.from_string(r["dpe_rating"]) if r["dpe_rating"] else None,
        advertiser=r["advertiser"],
        furnished=bool(r["furnished"]) if r["furnished"] is not None else None,
        restored_at=datetime.fromisoformat(r["restored_at"]) if r["restored_at"] else None,
    )
