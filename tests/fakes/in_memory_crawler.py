from apartment_hunter.domain.entities import Listing, SearchFilter
from apartment_hunter.domain.ports import CrawlerPort


class InMemoryCrawler(CrawlerPort):
    def __init__(self, source: str = "fake", listings: list[Listing] | None = None):
        self._source = source
        self._listings: list[Listing] = listings or []
        self.fetch_calls: list[SearchFilter] = []

    @property
    def source_name(self) -> str:
        return self._source

    async def fetch(self, search_filter: SearchFilter) -> list[Listing]:
        self.fetch_calls.append(search_filter)
        return list(self._listings)

    def seed(self, listings: list[Listing]) -> None:
        self._listings = listings
