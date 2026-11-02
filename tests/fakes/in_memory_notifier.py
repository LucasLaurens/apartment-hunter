from apartment_hunter.domain.entities import Listing, SearchFilter
from apartment_hunter.domain.ports import NotifierPort


class InMemoryNotifier(NotifierPort):
    name = "in_memory"

    def __init__(self) -> None:
        self.calls: list[tuple[list[Listing], SearchFilter]] = []

    async def notify(self, listings: list[Listing], search_filter: SearchFilter) -> None:
        self.calls.append((list(listings), search_filter))

    def count_notified(self) -> int:
        return sum(len(apts) for apts, _ in self.calls)
