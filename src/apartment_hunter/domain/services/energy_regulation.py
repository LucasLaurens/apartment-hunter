"""Passoire thermique — the legal weight an F or G rating carries.

A DPE letter is not just a comfort score: the loi Climat et Résilience bars the worst
classes from being rented out, class by class, on fixed dates. The listing stays
published and the decision stays the operator's, so this module only ever produces a
*warning* — never a filter. Excluding a listing is `SearchFilter.accepted_dpe_ratings`,
and nothing else.

The calendar is the single home of those dates: `is_thermal_sieve` and
`build_rental_ban_warning` both read it, and every reader (web card, CLI table, alert) takes
its wording from `build_rental_ban_warning` rather than re-deriving one.
"""

from datetime import date
from typing import Final

from ..value_objects import DpeRating

# Date from which a home of this class may no longer be newly let (habitation,
# France métropolitaine). Class E is in the table because the law says so, but it is
# not a passoire thermique and carries no warning — see `build_rental_ban_warning`.
RENTAL_BAN_DATES: Final[dict[DpeRating, date]] = {
    DpeRating.G: date(2025, 1, 1),
    DpeRating.F: date(2028, 1, 1),
    DpeRating.E: date(2034, 1, 1),
}

# The two classes the term designates. Kept apart from the calendar above: the word
# and the ban are different facts, and E has a ban date without being a passoire.
THERMAL_SIEVE_RATINGS: Final[frozenset[DpeRating]] = frozenset({DpeRating.F, DpeRating.G})

THERMAL_SIEVE_LABEL: Final = "Passoire thermique"


def is_thermal_sieve(rating: DpeRating | None) -> bool:
    """True for F and G. An unknown rating is not a passoire — it is an unknown."""
    return rating in THERMAL_SIEVE_RATINGS


def build_rental_ban_warning(rating: DpeRating | None, today: date) -> str:
    """The sentence to show beside a passoire, or `''` when there is nothing to say.

    Empty rather than `None` so every caller can concatenate it without a null check.
    `today` is a parameter, not a clock read: the wording flips from future to past on
    a fixed date, and a test must be able to stand on either side of it.

    O(1) — one set membership and one dict lookup.
    """
    if not is_thermal_sieve(rating):
        return ""
    assert rating is not None  # narrowed by is_thermal_sieve
    effective_on = RENTAL_BAN_DATES[rating]
    when = effective_on.strftime("%d/%m/%Y")
    if today >= effective_on:
        return f"{THERMAL_SIEVE_LABEL} — location interdite depuis le {when}"
    return f"{THERMAL_SIEVE_LABEL} — location interdite à partir du {when}"
