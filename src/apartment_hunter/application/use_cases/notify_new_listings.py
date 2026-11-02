from loguru import logger

from ...domain.entities import Listing, SearchFilter
from ...domain.ports import (
    GeocodingPort,
    ListingRepositoryPort,
    NotifierPort,
    RentReferencePort,
)
from ...domain.services import (
    DismissedHomes,
    ListingMatcher,
    RestoredHomes,
    format_restored_label,
)


def format_alert_line(listing: Listing) -> str:
    """The domain's summary, then the position: the summary cannot know it, the position
    depends on the Carte des loyers, which only the application has (ADR-0010). A home
    back with another rent says what the hunter thought of it (ADR-0009)."""
    line = f"{listing.build_summary_line()} · {listing.market_position.format_label()}"
    if listing.former_dismissal:
        line += f" · {listing.former_dismissal.format_mention()}"
    if listing.restored_at:
        line += f" · {format_restored_label(listing.restored_at)}"
    return line


class NotifyNewListings:
    """Alert on listings this filter has not alerted on yet.

    Takes the geocoding port rather than a ready-made coordinate table: the table's
    contents used to be decided at each call site, so the same listing could be alerted
    by the CLI and skipped by the web — one built a per-filter table, the other a table
    merged across every saved filter.
    """

    def __init__(
        self,
        repository: ListingRepositoryPort,
        notifiers: list[NotifierPort],
        geocoding: GeocodingPort,
        rent_references: RentReferencePort,
    ):
        self._repository = repository
        self._notifiers = notifiers
        self._geocoding = geocoding
        self._rent_references = rent_references

    async def execute(self, search_filter: SearchFilter) -> int:
        """Notify about new unseen listings. Returns count notified."""
        candidates = await self._repository.find_new_since(search_filter.id)
        matcher = ListingMatcher(
            geocoded_cities=await self._geocoding.find_cities_in_radius([search_filter])
        )

        dismissed = DismissedHomes(await self._repository.list_dismissals())
        matched = dismissed.annotate(
            dismissed.keep_undismissed(
                listing for listing in candidates if matcher.matches(listing, search_filter)
            )
        )
        if not matched:
            return 0
        book = await self._rent_references.find_references([search_filter])
        restored = RestoredHomes(await self._repository.list_restored_dismissals())
        matched = restored.annotate(book.annotate(matched))

        for notifier in self._notifiers:
            try:
                await notifier.notify(matched, search_filter)
            except Exception as exc:
                logger.error(f"Notifier {notifier.name} failed: {exc}")

        ids = [listing.id for listing in matched]
        await self._repository.mark_notified(ids, search_filter.id)
        logger.info(f"Notified {len(matched)} new listings for filter '{search_filter.name}'")
        return len(matched)
