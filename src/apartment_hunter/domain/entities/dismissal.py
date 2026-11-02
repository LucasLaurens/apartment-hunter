from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from ..value_objects import DismissalReason, DpeRating, HomeKey, format_euros


@dataclass(frozen=True)
class Dismissal:
    """The hunter's judgement that a home is not worth seeing again (ADR-0009).

    Kept apart from the listing row, which the purge deletes: the home key and the
    source are what recognise the same home when it comes back, under any URL or on
    another site. The remaining fields are a snapshot of the listing *as it was judged*
    — they feed the criterion suggestions long after the row itself is gone.
    """

    listing_id: str
    source: str
    home_key: HomeKey | None  # None when rooms or surface are unknown: URL-only match
    reason: DismissalReason
    dismissed_at: datetime
    total_price: Decimal
    note: str = ""
    surface_m2: float | None = None
    floor_level: int | None = None
    dpe_rating: DpeRating | None = None
    advertiser: str | None = None
    furnished: bool | None = None
    # Set when the hunter took the dismissal back: it no longer hides nor counts, and
    # stays as the trace « restauré le … ». A new dismissal replaces it whole.
    restored_at: datetime | None = None

    def format_mention(self) -> str:
        """« écarté le 12/10/2026 à 1 210 € (trop cher) »: what the hunter thought, and at
        which total, of a home back with another rent."""
        return (
            f"écarté le {self.dismissed_at:%d/%m/%Y} à {format_euros(self.total_price)} "
            f"({self.reason.label})"
        )

    def __post_init__(self) -> None:
        if self.note and self.reason is not DismissalReason.OTHER:
            raise ValueError(f"Only the 'other' reason carries a note, not {self.reason}")
