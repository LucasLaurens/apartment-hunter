"""The same home, published more than once.

A landlord who signs a non-exclusive mandate has three agencies advertising the flat,
and an agency often republishes its own mandate on a portal. Each publication is a
listing of its own — its URL, its price, its advertiser — and stays stored as one
(see `docs/decisions/0001-annonce-est-l-unite-stockee.md`).

What must not happen is the reader meeting the same home four times in a page of
twenty-five. So the listings are *grouped* for display, never merged and never
dropped: the group keeps every one of its listings, with its own link, so a wrong
grouping costs a glance instead of a missed home.

Grouping is deliberately strict. Two listings are the same home only when the town
(folded: "Chambéry" and "Chambery" are one), the room count, the rounded surface and
the **rent** all agree. Rent, not total: the provision for charges is what differs
between two publications of one flat. A listing missing its rooms or its surface is
never grouped — an unknown cannot be a match.
"""

from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from ..entities import Listing
from ..value_objects import HomeKey
from .commune_names import fold_commune_name


@dataclass(frozen=True)
class ListingGroup:
    """One home, and every listing advertising it. `primary` is the one to show."""

    primary: Listing
    others: tuple[Listing, ...] = ()

    @property
    def city(self) -> str:
        return self.primary.location.city

    @property
    def has_duplicates(self) -> bool:
        return bool(self.others)

    @property
    def all_listings(self) -> tuple[Listing, ...]:
        return (self.primary, *self.others)

    @property
    def sources(self) -> tuple[str, ...]:
        """Every source carrying this home, first-seen order, without repeats."""
        seen: dict[str, None] = {}
        for listing in self.all_listings:
            seen.setdefault(listing.source, None)
        return tuple(seen)


def build_home_key(listing: Listing) -> HomeKey | None:
    """What makes two publications the same home, or None when it cannot be told."""
    if listing.rooms is None or listing.surface_m2 is None:
        return None
    return HomeKey(
        city=fold_commune_name(listing.location.city),
        rooms=listing.rooms,
        # Sites round differently ("57,6 m²" vs "58 m²"): compare whole m².
        surface_m2=round(listing.surface_m2),
        rent=listing.price.amount,
    )


def group_duplicates(listings: Sequence[Listing]) -> list[ListingGroup]:
    """Collapse re-publications of one home into groups, keeping the incoming order.

    The first listing of a group holds its place in the list, so the caller's sort
    survives. Within a group the cheapest **total** leads — two agencies quoting the
    same rent can still charge different provisions.

    **One home is advertised at most once per source.** Two matching listings from the
    same site are therefore kept apart: a residence of identical flats has its units
    published side by side by one agency, and merging those would hide a real home.
    Re-publication — a non-exclusive mandate, or an agency mirroring itself onto a
    portal — always crosses sources, so nothing genuine is lost.

    O(n) time and space in practice: one pass, and the inner scan runs over the open
    groups sharing an exact key — one or two, never the whole list. `n` is the matched
    count, capped by the filter's `max_results`.
    """
    open_groups: dict[HomeKey, list[list[Listing]]] = {}
    members: list[list[Listing]] = []

    for listing in listings:
        key = build_home_key(listing)
        if key is None:
            members.append([listing])
            continue
        candidates = open_groups.setdefault(key, [])
        joined = next(
            (group for group in candidates if all(m.source != listing.source for m in group)),
            None,
        )
        if joined is None:
            joined = [listing]
            candidates.append(joined)
            members.append(joined)
        else:
            joined.append(listing)

    return [_build_group(group) for group in members]


def _build_group(members: Iterable[Listing]) -> ListingGroup:
    """Cheapest total leads; the rest keep their incoming order behind it."""
    ordered = list(members)
    leader = min(ordered, key=lambda listing: listing.price.total)
    return ListingGroup(
        primary=leader,
        others=tuple(listing for listing in ordered if listing is not leader),
    )
