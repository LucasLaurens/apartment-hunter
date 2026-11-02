"""The throwaway filter behind `hunt search --city …`.

Grouping the flags in one object keeps the command signature readable and gives the
"flags → SearchFilter" rule a single home, mirroring the web form's translator.
"""

from dataclasses import dataclass

from ...domain.entities import DEFAULT_MAX_RESULTS, DEFAULT_RADIUS_KM, SearchFilter
from ...domain.value_objects import DpeRating

ADHOC_FILTER_ID = "adhoc"
ADHOC_FILTER_NAME = "Ad-hoc search"


def _split(raw: str | None) -> list[str]:
    return [item.strip() for item in raw.split(",") if item.strip()] if raw else []


@dataclass(frozen=True)
class AdHocCriteria:
    """The `search` command's ad-hoc flags, as typed on the command line."""

    city: str
    radius_km: float = DEFAULT_RADIUS_KM
    excluded: str | None = None
    min_price: int | None = None
    max_price: int | None = None
    min_surface_m2: float | None = None
    min_rooms: int | None = None
    max_rooms: int | None = None
    furnished: bool | None = None
    exclude_ground_floor: bool = False
    exclude_first_floor: bool = False
    top_floor_only: bool = False
    dpe: str | None = None
    limit: int | None = None

    def to_filter(self) -> SearchFilter:
        """The non-persisted SearchFilter these flags describe."""
        return SearchFilter(
            id=ADHOC_FILTER_ID,
            name=ADHOC_FILTER_NAME,
            cities=_split(self.city),
            radius_km=self.radius_km,
            excluded_cities=_split(self.excluded),
            min_price=self.min_price,
            max_price=self.max_price,
            min_surface_m2=self.min_surface_m2,
            min_rooms=self.min_rooms,
            max_rooms=self.max_rooms,
            furnished=self.furnished,
            exclude_ground_floor=self.exclude_ground_floor,
            exclude_first_floor=self.exclude_first_floor,
            top_floor_only=self.top_floor_only,
            accepted_dpe_ratings=self._parse_accepted_dpe(),
            max_results=self.limit or DEFAULT_MAX_RESULTS,
        )

    def _parse_accepted_dpe(self) -> set[DpeRating]:
        """ "A,C,x" → {A, C}; no --dpe at all means no DPE filtering."""
        return {r for letter in _split(self.dpe) if (r := DpeRating.from_string(letter))}
