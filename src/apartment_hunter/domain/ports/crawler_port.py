from abc import ABC, abstractmethod

from ..entities import Listing, SearchFilter


class CrawlerPort(ABC):
    @property
    @abstractmethod
    def source_name(self) -> str: ...

    @abstractmethod
    async def fetch(self, search_filter: SearchFilter) -> list[Listing]: ...

    async def close(self) -> None:  # noqa: B027 — optional no-op hook, not every crawler holds resources
        """Release resources (browser, connections). Override if needed."""
