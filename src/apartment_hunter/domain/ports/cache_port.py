from abc import ABC, abstractmethod
from typing import TypeVar

T = TypeVar("T")


class CachePort(ABC):
    @abstractmethod
    def get(self, key: str) -> object | None: ...

    @abstractmethod
    def set(self, key: str, value: object) -> None: ...

    @abstractmethod
    def invalidate(self, key: str) -> None: ...
