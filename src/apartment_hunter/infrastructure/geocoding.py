"""The geocoding port, answered by Nominatim and the commune index.

Thin on purpose: the lookups themselves live in `geocoder.py`. What this adapter adds
is the *merge* across filters, which used to be written out at four call sites — twice
in the web layer, twice in the CLI — with two different meanings for the same table.
"""

from collections.abc import Sequence

from ..domain.entities import SearchFilter
from ..domain.ports import GeocodedCities, GeocodingPort
from .geocoder import expand_crawl_cities, geocode_radius_cities


class NominatimGeocoding(GeocodingPort):
    async def find_cities_in_radius(self, filters: Sequence[SearchFilter]) -> GeocodedCities:
        """One table covering every filter passed in.

        Cheap to call repeatedly: `geocode_radius_cities` sits behind a 24 h TTL cache,
        which is the only reason the web layer could afford one call per filter per
        request.
        """
        merged: GeocodedCities = {}
        for search_filter in filters:
            merged.update(
                await geocode_radius_cities(
                    search_filter.cities,
                    search_filter.radius_km,
                    search_filter.excluded_cities,
                )
            )
        return merged

    async def list_crawl_cities(self, target: SearchFilter, geocoded: GeocodedCities) -> list[str]:
        return await expand_crawl_cities(
            target.cities,
            target.radius_km,
            target.excluded_cities,
            geocoded,
        )
