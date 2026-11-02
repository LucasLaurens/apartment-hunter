"""When a stored listing can no longer be trusted to be online (ticket 13).

Two cases, told apart by whether the listing's source still answers this filter:

- the source answered for a while without the listing: it is expired, and hidden;
- the source stopped answering: the listing may be gone or not. It stays shown, marked,
  for `SOURCE_DOWN_HIDE_AFTER`, then is hidden and counted — a missed home costs more
  than a wasted click, so doubt keeps the listing until doubt has lasted a week.

Time is measured against the filter's own crawls, never the wall clock: `reference` is
the last time any source answered this filter. A hunter who leaves the laptop shut for
a month comes back to the page as it was, not to a page emptied by age alone.
"""

from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from typing import Final

from ..entities import Listing

STALE_AFTER_MIN: Final = timedelta(hours=48)
# A filter refreshed every 12 h must miss three crawls before its listings expire.
STALE_REFRESH_FACTOR: Final = 3
SOURCE_DOWN_HIDE_AFTER: Final = timedelta(days=7)


def compute_stale_after(refresh_interval_minutes: int) -> timedelta:
    return max(STALE_AFTER_MIN, timedelta(minutes=refresh_interval_minutes * STALE_REFRESH_FACTOR))


def build_source_down_warning(down_days: int) -> str:
    """'' for a healthy source, so every reader can print the result as-is."""
    if not down_days:
        return ""
    return f"source injoignable depuis {down_days} j, annonce peut-être expirée"


@dataclass(frozen=True)
class UnreachableSource:
    source: str
    down_days: int
    hidden_count: int  # listings no longer shown because the source is down too long


@dataclass(frozen=True)
class FreshnessReport:
    shown: list[Listing]
    unreachable: list[UnreachableSource]


class SourceFreshness:
    """Sorts a filter's listings by what its last crawls say about each source."""

    def __init__(self, last_success_by_source: Mapping[str, datetime], stale_after: timedelta):
        self._last_success = dict(last_success_by_source)
        self._stale_after = stale_after
        self._reference = max(self._last_success.values(), default=datetime.min)

    def sort_out(self, listings: list[Listing]) -> FreshnessReport:
        """O(n) time, O(n) space — n the listings; sources are a handful."""
        shown: list[Listing] = []
        hidden: Counter[str] = Counter()
        affected: set[str] = set()
        for listing in listings:
            last_success = self._last_success.get(listing.source)
            if last_success is None:
                shown.append(listing)
                continue
            down_for = self._reference - last_success
            if down_for > self._stale_after:
                affected.add(listing.source)
                if down_for > SOURCE_DOWN_HIDE_AFTER:
                    hidden[listing.source] += 1
                else:
                    shown.append(replace(listing, source_down_days=down_for.days))
            elif last_success - listing.last_seen_at <= self._stale_after:
                shown.append(listing)
        return FreshnessReport(shown=shown, unreachable=self._list_unreachable(affected, hidden))

    def _list_unreachable(
        self, affected: set[str], hidden: Counter[str]
    ) -> list[UnreachableSource]:
        return [
            UnreachableSource(
                source=source,
                down_days=(self._reference - self._last_success[source]).days,
                hidden_count=hidden[source],
            )
            for source in sorted(affected)
        ]
