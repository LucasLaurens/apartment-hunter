"""Who publishes a listing, and under which brand.

Displayed, never filtering: it changes what the home *costs* (an agency charges
letting fees, a private landlord charges none) without changing whether the listing
is worth seeing.

Three notions must not be confused (see `docs/functional/glossaire.md`):

* **source** — the site the listing was crawled from (`pap`, `orpi`…);
* **advertiser** — who publishes it (`Listing.advertiser`), an agency branch by name
  or nobody at all for a private ad;
* **network** — the brand behind that branch ("Laforêt" in "Laforêt Annecy").

Some sources settle the first question on their own: PAP carries private ads only, an
agency network carries its own mandates only. Portals carry both, so there the answer
comes from whether the listing names an advertiser at all.
"""

import unicodedata
from enum import StrEnum
from typing import Final


class AdvertiserKind(StrEnum):
    PRIVATE = "particulier"
    AGENCY = "agence"
    UNKNOWN = "inconnu"


# Network brand per agency source, keyed by the crawler's own `source_name`. One home:
# the source list below is derived from it, so a network can never be classified
# without a name, nor named without being classified.
NETWORK_NAMES: Final[dict[str, str]] = {
    "orpi": "Orpi",
    "foncia": "Foncia",
    "laforet": "Laforêt",
    "century21": "Century 21",
    "citya": "Citya",
    "squarehabitat": "Square Habitat",
}

# Sources whose whole catalogue is one kind. `tests/infrastructure/
# test_advertiser_source_parity.py` fails when a crawler is added without being
# classified here, so a new source can never default to "unknown" by omission.
# Locservice carries partner agency ads too; its crawler leaves them out.
PRIVATE_ONLY_SOURCES: Final[frozenset[str]] = frozenset({"pap", "locservice"})
AGENCY_ONLY_SOURCES: Final[frozenset[str]] = frozenset(NETWORK_NAMES)
MIXED_SOURCES: Final[frozenset[str]] = frozenset({"paruvendu", "bienici"})


def _fold(text: str) -> str:
    """Lowercased, unaccented, space-free — "Century 21" and "century21" as one key."""
    stripped = unicodedata.normalize("NFKD", text.lower())
    return "".join(c for c in stripped if not unicodedata.combining(c) and not c.isspace())


# Folded network key → display name, built once. Matching a branch name means scanning
# these, so precompute rather than folding the same five brands on every listing.
_FOLDED_NETWORKS: Final[dict[str, str]] = {_fold(name): name for name in NETWORK_NAMES.values()}


def detect_advertiser_kind(source: str, advertiser: str | None) -> AdvertiserKind:
    """Who publishes this listing, read from its source and its advertiser name.

    O(1) — two set lookups on a normalised source name.
    """
    normalised = source.strip().lower()
    if normalised in PRIVATE_ONLY_SOURCES:
        return AdvertiserKind.PRIVATE
    if normalised in AGENCY_ONLY_SOURCES:
        return AdvertiserKind.AGENCY
    # A portal that names a publisher names an agency: a private landlord has no trade
    # name to print. Saying nothing stays "unknown" — never guessed as private.
    if advertiser and advertiser.strip():
        return AdvertiserKind.AGENCY
    return AdvertiserKind.UNKNOWN


def find_network(advertiser: str | None) -> str:
    """The brand behind a branch name, or `''` when it belongs to none we know.

    Substring, because a branch prints the brand with its town appended
    ("Laforêt Annecy", "Century 21 Lac Bleu") and the folding makes the spacing
    irrelevant. Empty rather than `None` so callers can print it unguarded.

    O(len(advertiser) × networks) — five brands, a name of a few words.
    """
    if not advertiser:
        return ""
    folded = _fold(advertiser)
    for key, display in _FOLDED_NETWORKS.items():
        if key in folded:
            return display
    return ""
