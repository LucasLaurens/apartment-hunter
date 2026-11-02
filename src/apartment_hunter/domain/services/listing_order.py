"""The one place that knows how listings are ordered for display.

`sqlite_repository` mirrors these orders in SQL to cut its candidate window; the
parity test in `tests/infrastructure/test_sqlite_sort_parity.py` fails if the two
representations drift apart.
"""

from datetime import datetime
from typing import assert_never

from ..entities import Listing
from ..value_objects import ListingSort

_NO_SURFACE = 0.0  # unknown surface sinks to the bottom of a surface ranking


def _build_per_m2_key(listing: Listing) -> tuple[bool, float]:
    """Unknown (or zero) surface after every known one. Float, like SQLite's REAL, so a
    tie in one order is a tie in the other."""
    if not listing.surface_m2:
        return (True, 0.0)
    return (False, float(listing.price.total) / listing.surface_m2)


def build_published_key(listing: Listing) -> datetime:
    """Comparable publication instant, as local wall-clock time.

    Sites disagree: a source may send a tz-aware ISO date, the others naive local ones.
    Converting (rather than dropping the offset) is what keeps an aware 16:30+02:00
    listing ranked above a naive 15:00 one.
    """
    dt = listing.published_at
    return dt.astimezone().replace(tzinfo=None) if dt.tzinfo else dt


def sort_listings(listings: list[Listing], sort: ListingSort) -> list[Listing]:
    """Listings ordered for display, newest parution breaking every tie.

    O(n log n) time, O(n) space — n = matched listings. The newest-first pass runs
    first and Python's sort is stable, so listings sharing a price or a surface stay
    ordered by parution date.
    """
    newest_first = sorted(listings, key=build_published_key, reverse=True)
    match sort:
        case ListingSort.PUBLISHED_DESC:
            return newest_first
        case ListingSort.PRICE_ASC:
            return sorted(newest_first, key=lambda listing: listing.price.total)
        case ListingSort.PRICE_DESC:
            return sorted(newest_first, key=lambda listing: listing.price.total, reverse=True)
        case ListingSort.SURFACE_DESC:
            return sorted(
                newest_first, key=lambda listing: listing.surface_m2 or _NO_SURFACE, reverse=True
            )
        case ListingSort.PRICE_PER_M2_ASC:
            return sorted(newest_first, key=_build_per_m2_key)
        case ListingSort.MARKET_POSITION:
            return sorted(newest_first, key=lambda listing: listing.market_position.sort_key)
        case _:
            assert_never(sort)
