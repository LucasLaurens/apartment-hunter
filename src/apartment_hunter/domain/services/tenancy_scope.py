"""Listings that are not a home to rent, and must never reach the list.

Portals answer a "location" query with more than whole flats: rooms in a shared flat,
rooms at the owner's, mobility leases and holiday lets. None of them is what is being
hunted, and their low rent skews every price comparison — a 450 € room sitting next to
a 900 € two-room makes the second look expensive.

The exclusion is unconditional, not a filter option: it is a definition of what the
tool is about, so it lives here rather than on `SearchFilter`.

**Conservative on purpose.** Only wordings that describe the *offer itself* count.
A whole flat advertised as "idéal colocation" or "idéal étudiant" is a whole flat,
and must go through: a missed listing costs far more than a room to skip by eye.
"""

import re
from typing import Final

# A room, not a home. "Chambre" must sit at the start of the wording or be tied to a
# shared-flat phrase — an ad body mentioning "chambre avec placard" describes a room
# *of* the flat it is selling.
_ROOM_ONLY_PATTERNS: Final[tuple[re.Pattern[str], ...]] = (
    re.compile(r"^\s*(?:belle\s+|grande\s+|jolie\s+)?chambre\b", re.I),
    re.compile(r"\bchambre\s+(?:en\s+)?coloc(?:ation)?\b", re.I),
    re.compile(r"\bchambre\s+chez\s+(?:l['’]\s*habitant|un\s+particulier)\b", re.I),
    re.compile(r"\bcolocation\s+(?:meubl|de|dans)\w*", re.I),
    # A title that *opens* on the word offers the shared flat itself (« Colocation à
    # louer », a portal's room ad); « T5 pour colocation » rents the whole flat (H2).
    re.compile(r"^\s*colocation\b", re.I),
    re.compile(r"\bcoliving\b", re.I),
)

# A lease that is not a durable home: 1-to-10-month mobility lease, holiday rental.
_SHORT_TERM_PATTERNS: Final[tuple[re.Pattern[str], ...]] = (
    re.compile(r"\bbail\s+mobilit", re.I),
    re.compile(r"\blocation\s+saisonni", re.I),
    re.compile(r"\bmeubl\w*\s+de\s+tourisme\b", re.I),
    re.compile(r"\blocation\s+(?:de\s+)?courte\s+dur", re.I),
)

_OUT_OF_SCOPE_PATTERNS: Final[tuple[re.Pattern[str], ...]] = (
    _ROOM_ONLY_PATTERNS + _SHORT_TERM_PATTERNS
)


def is_out_of_scope_tenancy(title: str, description: str | None = None) -> bool:
    """True when the listing offers a room or a short-term let rather than a home.

    The title is read first and on its own: it states what is being offered, while a
    description mentions neighbouring facts ("proche colocation étudiante").
    The description is only searched for the short-term-lease wordings, which name a
    legal regime and cannot be said in passing.

    O(n) in the text length — a bounded number of anchored patterns, one pass each.
    """
    if any(pattern.search(title) for pattern in _OUT_OF_SCOPE_PATTERNS):
        return True
    if not description:
        return False
    return any(pattern.search(description) for pattern in _SHORT_TERM_PATTERNS)
