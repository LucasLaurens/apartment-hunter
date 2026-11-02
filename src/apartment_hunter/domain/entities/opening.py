from dataclasses import dataclass
from datetime import datetime

from ..value_objects import HomeKey


@dataclass(frozen=True)
class Opening:
    """The hunter followed a listing's link to its source (ADR-0002, ADR-0009).

    Kept apart from the listing row, like a dismissal: the purge deletes the row, and
    the home key and the source are what recognise the same home when it comes back,
    under the same URL or on another site. Only the first opening of a listing is kept.
    """

    listing_id: str
    source: str
    home_key: HomeKey | None  # None when rooms or surface are unknown: URL-only match
    opened_at: datetime
