from abc import ABC, abstractmethod
from collections.abc import Sequence

from ..entities import SearchFilter
from ..services.rent_reference_book import RentReferenceBook


class RentReferencePort(ABC):
    """The Carte des loyers references of the communes a filter can match (ADR-0010)."""

    @abstractmethod
    async def find_references(self, filters: Sequence[SearchFilter]) -> RentReferenceBook:
        """Every commune these filters can match, with its reference per segment.

        Never raises for an unreadable map: it answers `RentReferenceBook.build_unavailable()`,
        so a missing file costs the positions, never the page.
        """
