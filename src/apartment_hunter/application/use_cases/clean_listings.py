"""Cleaning the listing store by hand, between two crawls (`hunt clean`).

The purge after a crawl only drops what that crawl can vouch for. A listing no crawl
reaches any more (its commune left every radius, or an older crawler stored it under
the wrong commune) is never seen again, so nothing ever corrects or removes it.

Dismissals and openings live in their own tables, keyed by home rather than by row
(ADR-0009): a cleaned listing that comes back keeps the hunter's judgement of it.
"""

from dataclasses import dataclass
from datetime import datetime

from ...domain.ports import GeocodingPort, ListingRepositoryPort
from ...domain.services import ListingMatcher
from .purge_stale_listings import is_wanted_by_no_filter


@dataclass(frozen=True)
class StaleListings:
    irrelevant: list[str]  # match no saved filter
    unseen: list[str]  # returned by no crawl since the cutoff

    @property
    def total(self) -> int:
        return len(self.irrelevant) + len(self.unseen)


class CleanListings:
    def __init__(self, repository: ListingRepositoryPort, geocoding: GeocodingPort):
        self._repository = repository
        self._geocoding = geocoding

    async def find_stale(self, unseen_since: datetime) -> StaleListings:
        """O(n·f) time, O(n) space — n stored listings, f saved filters (a handful)."""
        saved = await self._repository.load_filters()
        matcher = ListingMatcher(geocoded_cities=await self._geocoding.find_cities_in_radius(saved))
        irrelevant: list[str] = []
        unseen: list[str] = []
        for listing in await self._repository.list_all():
            if is_wanted_by_no_filter(matcher, listing, saved):
                irrelevant.append(listing.id)
            elif listing.last_seen_at < unseen_since:
                unseen.append(listing.id)
        return StaleListings(irrelevant=irrelevant, unseen=unseen)

    async def delete(self, stale: StaleListings) -> int:
        return await self._repository.delete_many(stale.irrelevant + stale.unseen)
