"""Which listings the hunter's dismissals hide — one rule, shared by every reader.

A listing is dismissed when it *would group* with a dismissed listing under the
*Doublon* rule (`RecognisedHomes`). The review, the web list and the alert all ask
`DismissedHomes`, so a home is never hidden in one and shown in another.

A rent change breaks the recognition, on the same URL too: a lower rent is news, so the
home comes back. It then carries the earlier dismissal, found by its layout (the key
without the rent) — a lookup that only ever adds a mention, never hides (ADR-0009).
"""

from collections import defaultdict
from collections.abc import Iterable
from dataclasses import replace
from datetime import datetime

from ..entities import Dismissal, Listing
from ..value_objects import DismissalReason
from .duplicates import build_home_key
from .recognised_homes import RecognisedHomes


def format_restored_label(restored_at: datetime) -> str:
    """« restauré le 12/10/2026 »: this home has been judged once already."""
    return f"restauré le {restored_at:%d/%m/%Y}"


def build_dismissal(
    listing: Listing, reason: DismissalReason, dismissed_at: datetime, note: str = ""
) -> Dismissal:
    """Freeze what the hunter saw when they dismissed this listing."""
    return Dismissal(
        listing_id=listing.id,
        source=listing.source,
        home_key=build_home_key(listing),
        reason=reason,
        dismissed_at=dismissed_at,
        total_price=listing.price.total,
        note=note,
        surface_m2=listing.surface_m2,
        floor_level=listing.floor.level if listing.floor else None,
        dpe_rating=listing.dpe_rating,
        advertiser=listing.advertiser,
        furnished=listing.furnished,
    )


class DismissedHomes:
    """O(d) to build for d dismissals, O(s) per listing, s = dismissals per key."""

    def __init__(self, dismissals: Iterable[Dismissal]) -> None:
        kept = list(dismissals)
        self._homes = RecognisedHomes(kept)
        self._by_layout: dict[tuple[str, int, int], list[Dismissal]] = defaultdict(list)
        for dismissal in kept:
            if dismissal.home_key is not None:
                self._by_layout[dismissal.home_key.layout].append(dismissal)

    def is_dismissed(self, listing: Listing) -> bool:
        key = build_home_key(listing)
        # A same-URL dismissal stops counting once the rent moved; a key match cannot
        # have moved, its key holds the rent.
        return any(
            key is None or d.home_key is None or d.home_key.rent == key.rent
            for d in self._homes.find_judgements(listing)
        )

    def find_former_dismissal(self, listing: Listing) -> Dismissal | None:
        """The latest dismissal of this home at another rent; None for a home without a
        key, which only its URL recognises."""
        key = build_home_key(listing)
        if key is None:
            return None
        return max(
            (d for d in self._by_layout.get(key.layout, ()) if d.home_key != key),
            key=lambda d: d.dismissed_at,
            default=None,
        )

    def annotate(self, listings: Iterable[Listing]) -> list[Listing]:
        return [
            replace(listing, former_dismissal=self.find_former_dismissal(listing))
            for listing in listings
        ]

    def keep_undismissed(self, listings: Iterable[Listing]) -> list[Listing]:
        return [listing for listing in listings if not self.is_dismissed(listing)]


class RestoredHomes:
    """The dismissals taken back, recognised like the ones in force (`RecognisedHomes`)."""

    def __init__(self, restorations: Iterable[Dismissal]) -> None:
        self._homes = RecognisedHomes(restorations)

    def find_restored_at(self, listing: Listing) -> datetime | None:
        """The latest restoration of this home; None if it was never taken back."""
        return max(
            (d.restored_at for d in self._homes.find_judgements(listing) if d.restored_at),
            default=None,
        )

    def annotate(self, listings: Iterable[Listing]) -> list[Listing]:
        return [
            replace(listing, restored_at=self.find_restored_at(listing)) for listing in listings
        ]
