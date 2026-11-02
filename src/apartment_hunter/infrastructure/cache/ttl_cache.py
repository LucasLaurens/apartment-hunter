import time
from dataclasses import dataclass
from typing import TypeVar

from ...domain.ports import CachePort

T = TypeVar("T")


@dataclass
class _Entry:
    value: object
    expires_at: float


class TtlCache(CachePort):
    def __init__(self, ttl_seconds: int = 300):
        self._store: dict[str, _Entry] = {}
        self._ttl = ttl_seconds

    def get(self, key: str) -> object | None:
        entry = self._store.get(key)
        if entry is None:
            return None
        if time.monotonic() > entry.expires_at:
            del self._store[key]
            return None
        return entry.value

    def set(self, key: str, value: object) -> None:
        self._store[key] = _Entry(value=value, expires_at=time.monotonic() + self._ttl)

    def invalidate(self, key: str) -> None:
        self._store.pop(key, None)


GEOCODING_CACHE = TtlCache(ttl_seconds=86_400)  # 24h — Nominatim coords are stable
DETAIL_CACHE = TtlCache(ttl_seconds=86_400)  # 24h — DPE/GES + publication date per listing URL
