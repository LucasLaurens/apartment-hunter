from abc import ABC, abstractmethod

from ..entities import Listing, SearchFilter
from ..value_objects import SiteRules


class CrawlerPort(ABC):
    # True for a source whose terms forbid extracting its listings: crawled only when
    # the hunter chose to ignore the sites' rules (ADR-0012).
    forbids_reproduction: bool = False

    @property
    @abstractmethod
    def source_name(self) -> str: ...

    @abstractmethod
    async def fetch(self, search_filter: SearchFilter) -> list[Listing]: ...

    def apply_site_rules(self, rules: SiteRules) -> None:  # noqa: B027 — optional hook
        """Follow or set aside robots.txt from the next request on. No-op by default."""

    async def close(self) -> None:  # noqa: B027 — optional no-op hook, not every crawler holds resources
        """Release resources (browser, connections). Override if needed."""
