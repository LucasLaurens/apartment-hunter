from abc import ABC, abstractmethod
from datetime import datetime

from ..entities import Dismissal, Listing, Opening, SearchFilter
from ..services.criterion_suggestions import CriterionRefusal
from ..value_objects import DEFAULT_LISTING_SORT, ListingSort


class ListingRepositoryPort(ABC):
    @abstractmethod
    async def save_many(self, listings: list[Listing]) -> int:
        """Upsert listings. Returns count of newly inserted rows."""

    @abstractmethod
    async def find_new_since(self, filter_id: str) -> list[Listing]:
        """Return listings not yet notified for this filter."""

    @abstractmethod
    async def mark_notified(self, listing_ids: list[str], filter_id: str) -> None: ...

    @abstractmethod
    async def save_opening(self, opening: Opening) -> None:
        """Record that the hunter followed this listing's link; the first one is kept.

        Not scoped to a filter, and stored apart from the listing row: the purge must
        never make an opened home *Nouvelle* again (ADR-0009).
        """

    @abstractmethod
    async def list_openings(self) -> list[Opening]:
        """Every opening, whether or not its listing is still stored."""

    @abstractmethod
    async def find_top(
        self,
        search_filter: SearchFilter,
        limit: int = 10,
        sort: ListingSort = DEFAULT_LISTING_SORT,
    ) -> list[Listing]:
        """Return top N listings matching filter, ordered by `sort`.

        The order decides which candidates survive the limit, so asking for the
        cheapest returns the cheapest matches — not the cheapest of the newest.
        """

    @abstractmethod
    async def find_listing(self, listing_id: str) -> Listing | None:
        """The stored listing with this id; None once the purge has removed it."""

    @abstractmethod
    async def list_all(self) -> list[Listing]:
        """Return every stored listing."""

    @abstractmethod
    async def delete_many(self, listing_ids: list[str]) -> int:
        """Delete listings (and their notification rows) by id. Returns count deleted."""

    @abstractmethod
    async def save_dismissal(self, dismissal: Dismissal) -> None:
        """Record a dismissal, replacing any earlier one of the same listing.

        Stored apart from the listing row: `delete_many` must never erase it, or the
        purge would bring every dismissed home back (ADR-0009).
        """

    @abstractmethod
    async def list_dismissals(self) -> list[Dismissal]:
        """Every dismissal still in force, whether or not its listing is still stored."""

    @abstractmethod
    async def list_restored_dismissals(self) -> list[Dismissal]:
        """The dismissals taken back and not dismissed again: the « restauré le … » trace."""

    @abstractmethod
    async def save_restoration(self, listing_id: str, restored_at: datetime) -> None:
        """Lift a dismissal, keeping it as a trace (ADR-0009): it no longer hides,
        and it no longer counts. Dismissing the home again puts it back in force."""

    @abstractmethod
    async def save_source_successes(
        self, filter_id: str, sources: frozenset[str], answered_at: datetime
    ) -> None:
        """Record that these sources answered this filter's crawl at `answered_at`."""

    @abstractmethod
    async def find_source_successes(self, filter_id: str) -> dict[str, datetime]:
        """Last time each source answered this filter; {} when none ever did."""

    @abstractmethod
    async def save_criterion_refusal(self, refusal: CriterionRefusal) -> None:
        """Keep a refused suggestion; a new refusal of the same one replaces it."""

    @abstractmethod
    async def list_criterion_refusals(self) -> list[CriterionRefusal]:
        """Every refusal kept, all filters together. Survives the purge."""

    @abstractmethod
    async def save_filter(self, search_filter: SearchFilter) -> None: ...

    @abstractmethod
    async def load_filters(self) -> list[SearchFilter]: ...

    @abstractmethod
    async def delete_filter(self, filter_id: str) -> None: ...
