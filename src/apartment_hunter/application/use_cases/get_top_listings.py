from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from typing import Final

from ...domain.entities import Listing, SearchFilter
from ...domain.ports import GeocodingPort, ListingRepositoryPort, RentReferencePort
from ...domain.services import (
    DismissedHomes,
    FreshnessReport,
    ListingGroup,
    ListingMatcher,
    OpenedHomes,
    RestoredHomes,
    SourceFreshness,
    UnreachableSource,
    compute_stale_after,
    group_duplicates,
    sort_listings,
)
from ...domain.value_objects import DEFAULT_LISTING_SORT, ListingSort

PAGE_SIZE = 25
# No source picked: the page lists every home of the filter.
EVERY_SOURCE: Final = ""


@dataclass(frozen=True)
class ListingPage:
    groups: list[ListingGroup]
    total: int  # homes the list opens: the picked source's, or all of them
    page: int  # the page served, clamped to the last one
    pages: int
    source_counts: dict[str, int]  # homes per source over the whole filter, never one page
    # Sources that stopped answering this filter, with what that hides from the page.
    unreachable: list[UnreachableSource]
    # When a source last answered this filter: the page's honest freshness (W2).
    # None until the filter has been searched once.
    last_searched_at: datetime | None


@dataclass(frozen=True)
class _Selection:
    groups: list[ListingGroup]
    unreachable: list[UnreachableSource]


class GetTopListings:
    """What to surface for a filter, one entry per *home* rather than per publication.

    Grouping happens before the cap and before the page is cut, so the counts stay
    honest: a page of 25 is 25 homes, and the total the badge shows is the total the
    list opens. Doing it after pagination would group only what a page happens to hold.
    """

    def __init__(
        self,
        repository: ListingRepositoryPort,
        geocoding: GeocodingPort,
        rent_references: RentReferencePort,
    ):
        self._repository = repository
        self._geocoding = geocoding
        self._rent_references = rent_references

    async def execute(
        self,
        search_filter: SearchFilter,
        limit: int = 10,
        sort: ListingSort = DEFAULT_LISTING_SORT,
    ) -> list[ListingGroup]:
        """Return the top N homes matching the filter, ordered by `sort`."""
        cap = max(limit, search_filter.max_results)
        return (await self._select_matched(search_filter, cap, sort)).groups[:limit]

    async def execute_paginated(
        self,
        search_filter: SearchFilter,
        page: int = 1,
        page_size: int = PAGE_SIZE,
        sort: ListingSort = DEFAULT_LISTING_SORT,
        source: str = EVERY_SOURCE,
    ) -> ListingPage:
        """Return one page of matched homes, with the counts the page's controls show.

        Total is capped at the filter's `max_results`, so the page count never
        exceeds what the user asked to surface. The source is picked here, before the
        page is cut, so a source's homes are never split across pages that hold none of
        them, and its count is the number of homes the list then opens (W8).
        """
        selection = await self._select_matched(search_filter, search_filter.max_results, sort)
        successes = await self._repository.find_source_successes(search_filter.id)
        # O(n) time, O(s) space: n homes, s sources (a handful); a group counts once
        # per source carrying it, as the pill filters it.
        source_counts = Counter(src for group in selection.groups for src in group.sources)
        picked = [g for g in selection.groups if not source or source in g.sources]
        pages = max(1, -(-len(picked) // page_size))
        served = min(max(1, page), pages)
        start = (served - 1) * page_size
        return ListingPage(
            groups=picked[start : start + page_size],
            total=len(picked),
            page=served,
            pages=pages,
            source_counts=dict(sorted(source_counts.items())),
            unreachable=selection.unreachable,
            last_searched_at=max(successes.values(), default=None),
        )

    async def _select_matched(
        self, search_filter: SearchFilter, cap: int, sort: ListingSort
    ) -> _Selection:
        candidates = await self._repository.find_top(search_filter, limit=cap, sort=sort)
        matcher = ListingMatcher(
            geocoded_cities=await self._geocoding.find_cities_in_radius([search_filter])
        )
        matched = [listing for listing in candidates if matcher.matches(listing, search_filter)]
        freshness = await self._sort_out_expired(search_filter, matched)
        dismissed = DismissedHomes(await self._repository.list_dismissals())
        undismissed = dismissed.annotate(dismissed.keep_undismissed(freshness.shown))
        book = await self._rent_references.find_references([search_filter])
        opened = OpenedHomes(await self._repository.list_openings())
        restored = RestoredHomes(await self._repository.list_restored_dismissals())
        shown = restored.annotate(opened.annotate(book.annotate(undismissed)))
        # Group after sorting so a group takes the place of its first listing, and cap
        # after grouping so `max_results` counts homes rather than publications.
        return _Selection(
            groups=group_duplicates(sort_listings(shown, sort))[:cap],
            unreachable=freshness.unreachable,
        )

    async def _sort_out_expired(
        self, search_filter: SearchFilter, listings: list[Listing]
    ) -> FreshnessReport:
        successes = await self._repository.find_source_successes(search_filter.id)
        stale_after = compute_stale_after(search_filter.refresh_interval_minutes)
        return SourceFreshness(successes, stale_after).sort_out(listings)
