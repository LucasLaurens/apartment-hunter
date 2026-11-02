from collections.abc import Mapping, Sequence

from apartment_hunter.domain.entities import SearchFilter
from apartment_hunter.domain.ports import RentReferencePort
from apartment_hunter.domain.services import RentReferenceBook
from apartment_hunter.domain.value_objects import RentReference, RentSegment


class InMemoryRentReferences(RentReferencePort):
    """References seeded by the test, keyed by commune name; empty means no commune known."""

    def __init__(self, references: Mapping[str, Mapping[RentSegment, RentReference]] = {}):
        self._book = RentReferenceBook(references)

    async def find_references(self, filters: Sequence[SearchFilter]) -> RentReferenceBook:
        return self._book
