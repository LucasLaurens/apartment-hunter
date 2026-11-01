from apartment_hunter.domain.entities import Listing, SearchFilter
from apartment_hunter.domain.ports import CrawlerPort
from apartment_hunter.domain.value_objects import SiteRules


class InMemoryCrawler(CrawlerPort):
    def __init__(
        self,
        source: str = "fake",
        listings: list[Listing] | None = None,
        forbids_reproduction: bool = False,
    ):
        self._source = source
        self._listings: list[Listing] = listings or []
        self.forbids_reproduction = forbids_reproduction
        self.fetch_calls: list[SearchFilter] = []
        self.applied_rules: list[SiteRules] = []

    @property
    def source_name(self) -> str:
        return self._source

    def apply_site_rules(self, rules: SiteRules) -> None:
        self.applied_rules.append(rules)

    async def fetch(self, search_filter: SearchFilter) -> list[Listing]:
        self.fetch_calls.append(search_filter)
        return list(self._listings)

    def seed(self, listings: list[Listing]) -> None:
        self._listings = listings
