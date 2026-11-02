from abc import ABC, abstractmethod

from ..entities import Listing, SearchFilter


class NotifierPort(ABC):
    @abstractmethod
    async def notify(self, listings: list[Listing], search_filter: SearchFilter) -> None: ...

    @property
    @abstractmethod
    def name(self) -> str: ...
