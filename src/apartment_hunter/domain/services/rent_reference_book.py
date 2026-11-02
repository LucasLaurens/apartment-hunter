"""The rent references of a filter's communes, and the position each listing gets.

Pure: the references arrive already read (from the Carte des loyers, by an adapter),
keyed by commune name. Nothing here ever falls back to a wider area or to a median of
our own listings — no reference means no position (ADR-0010).
"""

from collections.abc import Mapping
from dataclasses import replace
from decimal import Decimal

from ..entities import Listing
from ..value_objects.market_position import (
    MarketAssessment,
    MarketPosition,
    NoMarketPosition,
    NoPositionReason,
    RentReference,
    RentSegment,
)
from .commune_names import fold_commune_name


class RentReferenceBook:
    def __init__(
        self,
        references: Mapping[str, Mapping[RentSegment, RentReference]],
        is_available: bool = True,
    ):
        self._references = {
            fold_commune_name(commune): dict(segments) for commune, segments in references.items()
        }
        # False when the map could not be read at all: then no commune is "absent",
        # the whole reference is, and the label must say so rather than blame the commune.
        self._is_available = is_available

    @classmethod
    def build_unavailable(cls) -> "RentReferenceBook":
        return cls({}, is_available=False)

    def assess(self, listing: Listing) -> MarketAssessment:
        """Checked in a fixed order so a furnished home is never called « sans surface »."""
        if listing.furnished is True:
            return NoMarketPosition(NoPositionReason.FURNISHED)
        if listing.charges_unknown:
            return NoMarketPosition(NoPositionReason.CHARGES_UNKNOWN)
        if not listing.surface_m2:
            return NoMarketPosition(NoPositionReason.NO_SURFACE)
        if not self._is_available:
            return NoMarketPosition(NoPositionReason.MAP_UNAVAILABLE)
        segment = RentSegment.from_rooms(listing.rooms)
        reference = self._references.get(fold_commune_name(listing.location.city), {}).get(segment)
        if reference is None:
            return NoMarketPosition(NoPositionReason.COMMUNE_ABSENT)
        per_m2 = listing.price.total / Decimal(str(listing.surface_m2))
        return MarketPosition(reference=reference, per_m2=per_m2)

    def annotate(self, listings: list[Listing]) -> list[Listing]:
        """O(n) time — n the listings; each lookup is a dict access."""
        return [replace(listing, market_position=self.assess(listing)) for listing in listings]
