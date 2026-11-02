import asyncio

from loguru import logger

from ...domain.entities import Listing, SearchFilter
from ...domain.ports import NotifierPort


class CompositeNotifier(NotifierPort):
    """Fan-out to multiple notifiers; failures are logged, not re-raised."""

    name = "composite"

    def __init__(self, notifiers: list[NotifierPort]):
        self._notifiers = notifiers

    async def notify(self, listings: list[Listing], search_filter: SearchFilter) -> None:
        tasks = [n.notify(listings, search_filter) for n in self._notifiers]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for notifier, result in zip(self._notifiers, results, strict=True):
            if isinstance(result, Exception):
                logger.error(f"[{notifier.name}] notification failed: {result}")
