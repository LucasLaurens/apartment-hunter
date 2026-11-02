from enum import StrEnum


class ListingSort(StrEnum):
    """How a page of listings is ordered.

    PUBLISHED_DESC is the default everywhere: the newest parution first, which is
    what matters when hunting a rental. The others are display preferences the web
    UI can pick per request — they never change which listings match a filter.
    """

    PUBLISHED_DESC = "published_desc"
    PRICE_ASC = "price_asc"
    PRICE_DESC = "price_desc"
    SURFACE_DESC = "surface_desc"
    PRICE_PER_M2_ASC = "price_per_m2_asc"  # total charges included per m²; no surface last
    MARKET_POSITION = "market_position"  # lowest vs the Carte des loyers first (ADR-0010)

    @property
    def window_sort(self) -> "ListingSort":
        """The order a store cuts its candidate window on.

        A position needs the Carte des loyers, which the database has not got; €/m² is
        its closest proxy, so the window keeps the homes most likely to rank first and
        the position itself is sorted in Python over that whole window.
        """
        return ListingSort.PRICE_PER_M2_ASC if self is ListingSort.MARKET_POSITION else self

    @classmethod
    def from_value(cls, raw: str | None) -> "ListingSort":
        """Parse a request value, falling back to the default on anything unknown.

        A stale bookmark or a hand-typed URL must still render a page rather than
        fail, so an unrecognised value degrades to the newest-first order.
        """
        if raw is None:
            return DEFAULT_LISTING_SORT
        try:
            return cls(raw)
        except ValueError:
            return DEFAULT_LISTING_SORT


DEFAULT_LISTING_SORT = ListingSort.PUBLISHED_DESC
