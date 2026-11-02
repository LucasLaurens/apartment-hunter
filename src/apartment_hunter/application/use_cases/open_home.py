from collections.abc import Callable
from datetime import datetime

from ...domain.entities import Listing
from ...domain.ports import ListingRepositoryPort
from ...domain.services import build_opening
from .dismiss_home import ListingNotFoundError


class OpenHome:
    """The hunter followed a listing's link: its whole home stops being *Nouvelle*.

    Takes a listing, like `DismissHome`: the hunter points at one publication, and the
    *Doublon* rule (`OpenedHomes`) extends the opening to every other publication of
    that home, and to the same URL once the purge has dropped it and a crawl brings it
    back. The review and the web route both come through here.
    """

    def __init__(
        self,
        repository: ListingRepositoryPort,
        read_now: Callable[[], datetime] = datetime.now,
    ):
        self._repository = repository
        self._read_now = read_now

    async def execute(self, listing: Listing) -> None:
        await self._repository.save_opening(build_opening(listing, self._read_now()))

    async def execute_by_id(self, listing_id: str) -> None:
        """The web page holds ids, not listings. Raises ListingNotFoundError."""
        listing = await self._repository.find_listing(listing_id)
        if listing is None:
            raise ListingNotFoundError(listing_id)
        await self.execute(listing)
