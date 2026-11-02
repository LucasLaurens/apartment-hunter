from dataclasses import dataclass

from loguru import logger

from ...domain.entities import Listing, SearchFilter
from ...domain.ports import ListingRepositoryPort
from ...domain.services import ListingMatcher
from .crawl_all_sources import CrawlOutcome


def is_wanted_by_no_filter(
    matcher: ListingMatcher, listing: Listing, saved_filters: list[SearchFilter]
) -> bool:
    """With no filter saved, nothing can be judged irrelevant: an empty keep-set keeps all."""
    return bool(saved_filters) and not any(matcher.matches(listing, f) for f in saved_filters)


@dataclass(frozen=True)
class PurgeOutcome:
    irrelevant: int  # matched no saved filter
    delisted: int  # vanished from the latest crawl of the searched filter

    @property
    def total(self) -> int:
        return self.irrelevant + self.delisted


class PurgeStaleListings:
    """Drop stored listings that are no longer worth showing.

    Two reasons a listing is purged:
      - irrelevant: it matches *no* saved filter anymore (e.g. criteria changed).
      - delisted: it matches the just-crawled filter but no longer appears in that
        crawl, so the source has dropped it (rented / removed).

    The shared listing pool is queried by several filters, so "irrelevant" is
    judged against *all* saved filters — never delete a listing another filter
    still wants. Delisting is scoped to the crawled filter and only trusts a
    source that actually returned listings this run.
    """

    def __init__(
        self,
        repository: ListingRepositoryPort,
        matcher: ListingMatcher,
        keep_filters: list[SearchFilter],
    ):
        self._repository = repository
        self._matcher = matcher
        self._keep_filters = keep_filters

    async def execute(self, crawled_filter: SearchFilter, outcome: CrawlOutcome) -> PurgeOutcome:
        stored = await self._repository.list_all()
        irrelevant_ids: list[str] = []
        delisted_ids: list[str] = []

        for listing in stored:
            if is_wanted_by_no_filter(self._matcher, listing, self._keep_filters):
                irrelevant_ids.append(listing.id)
                continue
            if (
                listing.source in outcome.authoritative_sources
                and listing.url not in outcome.fresh_urls
                and self._matcher.matches(listing, crawled_filter)
            ):
                delisted_ids.append(listing.id)

        await self._repository.delete_many(irrelevant_ids + delisted_ids)
        result = PurgeOutcome(irrelevant=len(irrelevant_ids), delisted=len(delisted_ids))
        if result.total:
            logger.info(
                f"Purged {result.total} listings "
                f"({result.irrelevant} irrelevant, {result.delisted} delisted)"
            )
        return result
