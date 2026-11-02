"""A geocoding port answered from a dict — no Nominatim, no network."""

from collections.abc import Sequence

from apartment_hunter.domain.entities import SearchFilter
from apartment_hunter.domain.ports import GeocodedCities, GeocodingPort


class InMemoryGeocoding(GeocodingPort):
    """Every commune it knows sits in the table it was built with.

    `list_crawl_cities` answers with the filter's own cities: expanding to neighbouring
    communes is a network job, and a test that wants the expansion says so by seeding
    `crawl_cities_by_filter`.
    """

    def __init__(
        self,
        known: GeocodedCities | None = None,
        crawl_cities_by_filter: dict[str, list[str]] | None = None,
    ) -> None:
        self.known: GeocodedCities = dict(known or {})
        self.crawl_cities_by_filter = crawl_cities_by_filter or {}
        self.radius_calls: list[tuple[str, ...]] = []

    async def find_cities_in_radius(self, filters: Sequence[SearchFilter]) -> GeocodedCities:
        self.radius_calls.append(tuple(f.id for f in filters))
        return dict(self.known)

    async def list_crawl_cities(self, target: SearchFilter, geocoded: GeocodedCities) -> list[str]:
        return self.crawl_cities_by_filter.get(target.id, list(target.cities))
