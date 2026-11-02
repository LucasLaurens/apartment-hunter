"""What the map draws for a filter (ticket 14): the radius, and the homes by commune.

No source publishes a listing's coordinates, so a pin stands for a commune, placed by
the geocoding the matcher already uses (`ListingMatcher.find_position`): a pin always
sits where the radius check measured from.
"""

from collections import defaultdict
from dataclasses import dataclass

from ...domain.entities import SearchFilter
from ...domain.ports import GeocodingPort
from ...domain.services import ListingGroup, ListingMatcher
from .get_top_listings import GetTopListings

Position = tuple[float, float]


@dataclass(frozen=True)
class CommunePin:
    name: str  # as the listings spell it
    position: Position
    homes: list[ListingGroup]


@dataclass(frozen=True)
class FilterMap:
    radius_km: float
    centre: Position | None  # None when the base commune is not geocoded: no circle to draw
    pins: list[CommunePin]
    unplaced: int  # homes shown in the list that the map cannot place


@dataclass(frozen=True)
class FilterArea:
    radius_km: float
    centre: Position | None
    communes: list[tuple[str, Position]]


class MapFilterHomes:
    def __init__(self, get_top: GetTopListings, geocoding: GeocodingPort):
        self._get_top = get_top
        self._geocoding = geocoding

    async def execute(self, search_filter: SearchFilter) -> FilterMap:
        """The homes the list would show, gathered on their commune. O(h), h = homes."""
        homes = await self._get_top.execute(search_filter, limit=search_filter.max_results)
        matcher = ListingMatcher(await self._geocoding.find_cities_in_radius([search_filter]))
        by_commune: dict[Position, list[ListingGroup]] = defaultdict(list)
        names: dict[Position, str] = {}
        unplaced = 0
        for group in homes:
            position = matcher.find_position(group.primary)
            if position is None:
                unplaced += 1
                continue
            by_commune[position].append(group)
            names.setdefault(position, group.city)
        return FilterMap(
            radius_km=search_filter.radius_km,
            centre=self._find_centre(matcher, search_filter),
            pins=[CommunePin(names[p], p, groups) for p, groups in by_commune.items()],
            unplaced=unplaced,
        )

    async def find_area(self, search_filter: SearchFilter) -> FilterArea:
        """Every commune in radius: what the filter modal lets the hunter exclude."""
        geocoded = await self._geocoding.find_cities_in_radius([search_filter])
        return FilterArea(
            radius_km=search_filter.radius_km,
            centre=self._find_centre(ListingMatcher(geocoded), search_filter),
            communes=list(geocoded.items()),
        )

    @staticmethod
    def _find_centre(matcher: ListingMatcher, search_filter: SearchFilter) -> Position | None:
        for city in search_filter.cities:
            if (position := matcher.find_commune_position(city)) is not None:
                return position
        return None
