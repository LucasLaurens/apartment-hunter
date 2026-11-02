"""After a dismissal, what filter change to propose, and what it would cost.

The rule lives in `domain/services/criterion_suggestions.py`; this use case feeds it the
dismissals in force, every saved filter and the refusals kept, then measures the impact:
how many homes the filter shows today, not dismissed, the change would hide as well. A
suggestion is only applied when the hunter says yes, through the same save path as any
filter edit — `SearchFilter` refuses a value out of bounds.
"""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from ...domain.entities import Listing, SearchFilter
from ...domain.ports import GeocodingPort, ListingRepositoryPort
from ...domain.services import (
    CriterionRefusal,
    CriterionSuggestion,
    ListingMatcher,
    build_criterion_suggestion,
)
from .get_top_listings import GetTopListings


@dataclass(frozen=True)
class PendingSuggestion:
    search_filter: SearchFilter
    suggestion: CriterionSuggestion
    hidden_too: int  # homes shown today, not dismissed, that the change would also hide


class SuggestCriteria:
    def __init__(
        self,
        repository: ListingRepositoryPort,
        get_top: GetTopListings,
        geocoding: GeocodingPort,
        read_now: Callable[[], datetime] = datetime.now,
    ):
        self._repository = repository
        self._get_top = get_top
        self._geocoding = geocoding
        self._read_now = read_now

    async def find_suggestions(self, dismissed: Listing) -> list[PendingSuggestion]:
        """One per filter that would still let these homes through. Call it right after
        the dismissal of `dismissed` was saved."""
        dismissals = await self._repository.list_dismissals()
        trigger = next((d for d in dismissals if d.listing_id == dismissed.id), None)
        if trigger is None:
            return []
        refusals = await self._repository.list_criterion_refusals()
        pending: list[PendingSuggestion] = []
        for search_filter in await self._repository.load_filters():
            suggestion = build_criterion_suggestion(
                trigger, dismissals, search_filter, refusals, dismissed.location.city
            )
            if suggestion is not None:
                hidden = await self._count_hidden_too(search_filter, suggestion.revised_filter)
                pending.append(PendingSuggestion(search_filter, suggestion, hidden))
        return pending

    async def apply_suggestion(self, pending: PendingSuggestion) -> None:
        await self._repository.save_filter(pending.suggestion.revised_filter)

    async def save_refusal(self, pending: PendingSuggestion) -> None:
        suggestion = pending.suggestion
        await self._repository.save_criterion_refusal(
            CriterionRefusal(
                filter_id=pending.search_filter.id,
                reason=suggestion.reason,
                value=suggestion.value,
                refused_at=self._read_now(),
                dismissal_count=suggestion.dismissal_count,
            )
        )

    async def _count_hidden_too(self, current: SearchFilter, revised: SearchFilter) -> int:
        """O(h) for h homes the filter shows; the dismissed ones are already out of them."""
        homes = await self._get_top.execute(current, current.max_results)
        matcher = ListingMatcher(
            geocoded_cities=await self._geocoding.find_cities_in_radius([revised])
        )
        return sum(1 for home in homes if not matcher.matches(home.primary, revised))
