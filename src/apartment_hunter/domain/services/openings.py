"""Which listings the hunter has already opened — through any publication of the home.

Opening a listing opens its home: its duplicates on other sources, and the listing
itself when the purge drops it and a crawl brings the same URL back. *Nouvelle* still
means « not opened yet » (ADR-0002); only the unit it remembers changed (ADR-0009).
"""

from collections.abc import Iterable
from dataclasses import replace
from datetime import datetime

from ..entities import Listing, Opening
from .duplicates import build_home_key
from .recognised_homes import RecognisedHomes


def build_opening(listing: Listing, opened_at: datetime) -> Opening:
    return Opening(
        listing_id=listing.id,
        source=listing.source,
        home_key=build_home_key(listing),
        opened_at=opened_at,
    )


class OpenedHomes:
    def __init__(self, openings: Iterable[Opening]) -> None:
        self._homes = RecognisedHomes(openings)

    def find_opened_at(self, listing: Listing) -> datetime | None:
        """The first time any publication of this home was opened; None if never."""
        return min((o.opened_at for o in self._homes.find_judgements(listing)), default=None)

    def annotate(self, listings: Iterable[Listing]) -> list[Listing]:
        """O(n·s) for n listings, s openings per home key (a handful)."""
        return [replace(listing, opened_at=self.find_opened_at(listing)) for listing in listings]
