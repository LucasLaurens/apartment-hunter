"""The identity two publications of one home share."""

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class HomeKey:
    """What two publications of one home share. The only definition of "same home".

    Built by `build_home_key` (domain/services/duplicates.py). Grouping for display and
    recognising a dismissed home both ask this key, so the two can never disagree on
    what a duplicate is (ADR-0009).
    """

    city: str
    rooms: int
    surface_m2: int
    rent: Decimal

    @property
    def layout(self) -> tuple[str, int, int]:
        """The key without the rent: finds a dismissal again after a rent change, to say
        so — never to hide anything (ADR-0009)."""
        return (self.city, self.rooms, self.surface_m2)
