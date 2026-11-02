from abc import ABC, abstractmethod
from collections.abc import Sequence

from ..entities import SearchFilter

# Commune name, lowercased → (latitude, longitude). The matcher falls back to this
# table for any listing whose own coordinates the source never printed.
type GeocodedCities = dict[str, tuple[float, float]]


class GeocodingPort(ABC):
    """Turning a filter's radius into commune names and coordinates.

    Two questions, deliberately kept apart because the answers have different sizes:
    *which communes count as being in radius* (uncapped — used for matching) and
    *which communes are worth crawling* (capped — used to build search URLs).
    """

    @abstractmethod
    async def find_cities_in_radius(self, filters: Sequence[SearchFilter]) -> GeocodedCities:
        """Every commune within radius of any of these filters, with its coordinates.

        Takes a sequence, not one filter, because the purge judges a listing against
        *all* saved filters at once: a table built for one filter would let the purge
        delete listings another filter still wants.
        """

    @abstractmethod
    async def list_crawl_cities(self, target: SearchFilter, geocoded: GeocodedCities) -> list[str]:
        """The commune names to actually search, nearest first and capped.

        A source that cannot search by radius is queried commune by commune, so this
        list is what bounds crawl time.
        """
