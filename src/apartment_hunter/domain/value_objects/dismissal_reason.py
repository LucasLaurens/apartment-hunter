"""Why the hunter dismissed a home — a closed list, so reasons can be counted."""

from enum import StrEnum
from typing import Final


class DismissalReason(StrEnum):
    """Stored by value in SQLite: renaming a member's value is a data migration.

    Only OTHER carries a free text. ASPECT covers what only the eye can judge
    (photos, light, condition) and maps to no filter criterion.
    """

    TOO_EXPENSIVE = "too_expensive"
    TOO_SMALL = "too_small"
    FLOOR = "floor"
    DPE = "dpe"
    CITY = "city"
    ADVERTISER = "advertiser"
    FURNISHED = "furnished"
    ASPECT = "aspect"
    OTHER = "other"

    @property
    def label(self) -> str:
        """« trop cher »: how the hunter reads the reason, on every screen and in the alert."""
        return _LABELS[self]


_LABELS: Final = {
    DismissalReason.TOO_EXPENSIVE: "trop cher",
    DismissalReason.TOO_SMALL: "trop petit",
    DismissalReason.FLOOR: "étage",
    DismissalReason.DPE: "DPE",
    DismissalReason.CITY: "commune",
    DismissalReason.ADVERTISER: "annonceur",
    DismissalReason.FURNISHED: "meublé",
    DismissalReason.ASPECT: "aspect",
    DismissalReason.OTHER: "autre",
}
