"""Where a listing's rent sits against the Carte des loyers (ADR-0010).

A reference is a *prediction for a typical home* (37 m² for a T1-T2, 72 m² for a T3+),
charges included and unfurnished — not a median, and not something a real surface can
be corrected against. Hence the wording: « vs réf. », never « prix du marché ».
"""

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
from typing import Final

# The producer asks for caution below these (guide d'utilisation, p. 2).
WEAK_OBSERVATIONS: Final = 30
WEAK_R2_ADJUSTED: Final = 0.5
# Licence Ouverte 2.0: every surface that shows a position names the source.
RENT_MAP_CREDIT: Final = "Estimations ANIL, à partir des données du Groupe SeLoger et de leboncoin"
_MINUS: Final = "−"
_NARROW_NBSP: Final = " "


class RentSegment(StrEnum):
    """One file of the Carte des loyers, picked by the number of rooms."""

    ALL_APARTMENTS = "app"
    ONE_TWO_ROOMS = "app12"
    THREE_PLUS_ROOMS = "app3"

    @classmethod
    def from_rooms(cls, rooms: int | None) -> "RentSegment":
        if rooms is None:
            return cls.ALL_APARTMENTS
        return cls.ONE_TWO_ROOMS if rooms <= 2 else cls.THREE_PLUS_ROOMS

    @property
    def label(self) -> str:
        return _SEGMENT_LABELS[self]

    @property
    def typical_surface_m2(self) -> int:
        """The home the prediction is made for (guide d'utilisation, p. 1)."""
        return _TYPICAL_SURFACES_M2[self]


_SEGMENT_LABELS: Final = {
    RentSegment.ALL_APARTMENTS: "tous appartements",
    RentSegment.ONE_TWO_ROOMS: "T1-T2",
    RentSegment.THREE_PLUS_ROOMS: "T3+",
}
_TYPICAL_SURFACES_M2: Final = {
    RentSegment.ALL_APARTMENTS: 52,
    RentSegment.ONE_TWO_ROOMS: 37,
    RentSegment.THREE_PLUS_ROOMS: 72,
}


@dataclass(frozen=True)
class RentReference:
    commune: str
    segment: RentSegment
    per_m2: Decimal
    lower_per_m2: Decimal  # bounds of the 95 % prediction interval, wider than a CI
    upper_per_m2: Decimal
    observed_in_commune: int
    r2_adjusted: float
    vintage: int

    @property
    def is_weak(self) -> bool:
        return self.observed_in_commune < WEAK_OBSERVATIONS or self.r2_adjusted < WEAK_R2_ADJUSTED

    def format_detail(self) -> str:
        """« Annecy, T1-T2 (logement type 37 m²) : 20,92 €/m², fourchette 15,69-27,89, … »"""
        typical = f"logement type {self.segment.typical_surface_m2} m²"
        return (
            f"{self.commune}, {self.segment.label} ({typical}) : "
            f"{_format_per_m2(self.per_m2)} €/m², fourchette {_format_per_m2(self.lower_per_m2)}"
            f"-{_format_per_m2(self.upper_per_m2)}, millésime {self.vintage}"
        )


class NoPositionReason(StrEnum):
    """Why a listing gets no position. The first four are checked in this order."""

    FURNISHED = "meublé"
    CHARGES_UNKNOWN = "charges inconnues"
    NO_SURFACE = "sans surface"
    COMMUNE_ABSENT = "commune absente"
    MAP_UNAVAILABLE = "carte des loyers indisponible"
    NOT_ASSESSED = "non évalué"


@dataclass(frozen=True)
class MarketPosition:
    reference: RentReference
    per_m2: Decimal  # the listing's total charges included, per m²

    @property
    def gap_percent(self) -> int:
        return round((self.per_m2 / self.reference.per_m2 - 1) * 100)

    @property
    def is_outside_range(self) -> bool:
        """The only case where « sous le marché » is true; inside, the % only ranks."""
        return not self.reference.lower_per_m2 <= self.per_m2 <= self.reference.upper_per_m2

    @property
    def sort_key(self) -> tuple[int, float]:
        return (0, float(self.per_m2 / self.reference.per_m2))

    def format_gap(self) -> str:
        """« −12 % »: the short form a list column has room for."""
        gap = self.gap_percent
        sign = _MINUS if gap < 0 else "+" if gap > 0 else ""
        return f"{sign}{abs(gap)}{_NARROW_NBSP}%"

    def format_label(self) -> str:
        """« −12 % vs réf. », « · hors fourchette » outside the interval, « (repère faible) »."""
        label = f"{self.format_gap()} vs réf."
        if self.is_outside_range:
            label += " · hors fourchette"
        if self.reference.is_weak:
            label += " (repère faible)"
        return label


@dataclass(frozen=True)
class NoMarketPosition:
    reason: NoPositionReason

    @property
    def sort_key(self) -> tuple[int, float]:
        """Homes without a reference rank after every home that has one."""
        return (1, 0.0)

    def format_gap(self) -> str:
        return "?"

    def format_label(self) -> str:
        return f"pas de repère ({self.reason.value})"


type MarketAssessment = MarketPosition | NoMarketPosition

NOT_ASSESSED: Final = NoMarketPosition(NoPositionReason.NOT_ASSESSED)


def _format_per_m2(value: Decimal) -> str:
    return f"{value:.2f}".replace(".", ",")
