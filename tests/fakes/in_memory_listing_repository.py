from collections import defaultdict
from dataclasses import replace
from datetime import datetime

from apartment_hunter.domain.entities import Dismissal, Listing, Opening, SearchFilter
from apartment_hunter.domain.ports import ListingRepositoryPort
from apartment_hunter.domain.services import CriterionRefusal, sort_listings
from apartment_hunter.domain.value_objects import (
    DEFAULT_LISTING_SORT,
    DismissalReason,
    ListingSort,
    Price,
)


class InMemoryListingRepository(ListingRepositoryPort):
    def __init__(self) -> None:
        self._apartments: dict[str, Listing] = {}
        self._notified: dict[str, set[str]] = defaultdict(set)  # filter_id → set of apt_ids
        self._filters: dict[str, SearchFilter] = {}
        self._dismissals: dict[str, Dismissal] = {}  # listing_id → dismissal
        self._openings: dict[str, Opening] = {}  # listing_id → first opening
        self._source_successes: dict[str, dict[str, datetime]] = defaultdict(dict)
        self._refusals: dict[tuple[str, DismissalReason, str], CriterionRefusal] = {}

    async def save_many(self, listings: list[Listing]) -> int:
        new = 0
        for listing in listings:
            stored = self._apartments.get(listing.id)
            if stored is None:
                self._apartments[listing.id] = listing
                new += 1
            else:
                # As SQLite does: rent, commune and title follow the source, charges and
                # postal code read as nothing keep the stored ones, last seen never moves
                # backwards.
                price = Price(listing.price.amount, listing.price.charges or stored.price.charges)
                location = replace(
                    listing.location,
                    postal_code=listing.location.postal_code or stored.location.postal_code,
                )
                last_seen_at = max(stored.last_seen_at, listing.last_seen_at)
                self._apartments[listing.id] = replace(
                    stored,
                    title=listing.title,
                    price=price,
                    location=location,
                    last_seen_at=last_seen_at,
                )
        return new

    async def find_new_since(self, filter_id: str) -> list[Listing]:
        notified_ids = self._notified[filter_id]
        return [listing for listing in self._apartments.values() if listing.id not in notified_ids]

    async def mark_notified(self, listing_ids: list[str], filter_id: str) -> None:
        self._notified[filter_id].update(listing_ids)

    async def save_opening(self, opening: Opening) -> None:
        self._openings.setdefault(opening.listing_id, opening)

    async def list_openings(self) -> list[Opening]:
        return list(self._openings.values())

    async def find_top(
        self,
        search_filter: SearchFilter,
        limit: int = 10,
        sort: ListingSort = DEFAULT_LISTING_SORT,
    ) -> list[Listing]:
        return sort_listings(list(self._apartments.values()), sort.window_sort)[:limit]

    async def find_listing(self, listing_id: str) -> Listing | None:
        return self._apartments.get(listing_id)

    async def list_all(self) -> list[Listing]:
        return list(self._apartments.values())

    async def delete_many(self, listing_ids: list[str]) -> int:
        deleted = 0
        for apt_id in listing_ids:
            if self._apartments.pop(apt_id, None) is not None:
                deleted += 1
            for notified_ids in self._notified.values():
                notified_ids.discard(apt_id)
        return deleted

    async def save_dismissal(self, dismissal: Dismissal) -> None:
        self._dismissals[dismissal.listing_id] = dismissal

    async def list_dismissals(self) -> list[Dismissal]:
        return [d for d in self._dismissals.values() if d.restored_at is None]

    async def list_restored_dismissals(self) -> list[Dismissal]:
        return [d for d in self._dismissals.values() if d.restored_at is not None]

    async def save_restoration(self, listing_id: str, restored_at: datetime) -> None:
        dismissal = self._dismissals.get(listing_id)
        if dismissal is not None and dismissal.restored_at is None:
            self._dismissals[listing_id] = replace(dismissal, restored_at=restored_at)

    async def save_source_successes(
        self, filter_id: str, sources: frozenset[str], answered_at: datetime
    ) -> None:
        self._source_successes[filter_id].update(dict.fromkeys(sources, answered_at))

    async def find_source_successes(self, filter_id: str) -> dict[str, datetime]:
        return dict(self._source_successes.get(filter_id, {}))

    async def save_criterion_refusal(self, refusal: CriterionRefusal) -> None:
        self._refusals[(refusal.filter_id, refusal.reason, refusal.value)] = refusal

    async def list_criterion_refusals(self) -> list[CriterionRefusal]:
        return list(self._refusals.values())

    async def save_filter(self, search_filter: SearchFilter) -> None:
        self._filters[search_filter.id] = search_filter

    async def load_filters(self) -> list[SearchFilter]:
        return list(self._filters.values())

    async def delete_filter(self, filter_id: str) -> None:
        self._filters.pop(filter_id, None)
        self._source_successes.pop(filter_id, None)
        self._refusals = {k: r for k, r in self._refusals.items() if r.filter_id != filter_id}

    def count(self) -> int:
        return len(self._apartments)
