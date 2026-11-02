from collections.abc import Callable
from datetime import datetime

from ...domain.entities import Dismissal, Listing
from ...domain.ports import ListingRepositoryPort
from ...domain.services import build_dismissal
from ...domain.value_objects import DismissalReason


class ListingNotFoundError(LookupError):
    """The page pointed at a listing the purge has since removed."""


class DismissHome:
    """The hunter decides a home is not worth seeing again, and says why.

    Takes a listing rather than a home: the hunter points at one publication, and the
    *Doublon* rule (`DismissedHomes`) extends the judgement to every other publication
    of that home. Global — no filter is involved — and without expiry.
    """

    def __init__(
        self,
        repository: ListingRepositoryPort,
        read_now: Callable[[], datetime] = datetime.now,
    ):
        self._repository = repository
        self._read_now = read_now

    async def execute(self, listing: Listing, reason: DismissalReason, note: str = "") -> None:
        dismissal = build_dismissal(listing, reason, self._read_now(), note.strip())
        await self._repository.save_dismissal(dismissal)

    async def execute_by_id(self, listing_id: str, reason: DismissalReason, note: str = "") -> None:
        """The web page holds ids, not listings. Raises ListingNotFoundError."""
        listing = await self._repository.find_listing(listing_id)
        if listing is None:
            raise ListingNotFoundError(listing_id)
        await self.execute(listing, reason, note)


class ListDismissedHomes:
    """The dismissals in force, newest first: what the restore page offers back."""

    def __init__(self, repository: ListingRepositoryPort):
        self._repository = repository

    async def execute(self) -> list[Dismissal]:
        return sorted(
            await self._repository.list_dismissals(), key=lambda d: d.dismissed_at, reverse=True
        )


class RestoreHome:
    """The hunter takes a dismissal back: the home, and its duplicates, show again."""

    def __init__(
        self,
        repository: ListingRepositoryPort,
        read_now: Callable[[], datetime] = datetime.now,
    ):
        self._repository = repository
        self._read_now = read_now

    async def execute(self, listing_id: str) -> None:
        await self._repository.save_restoration(listing_id, self._read_now())
