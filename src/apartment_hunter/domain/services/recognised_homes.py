"""How a judgement on one listing reaches every publication of its home (ADR-0009).

A listing carries a judgement when it *would group* with the judged listing under the
*Doublon* rule: the same URL, or the same home key on another source. Two identical
listings of one source stay apart — a residence publishes its identical lots side by
side, and judging one lot is not judging the next. Dismissals and openings both ask
this index, so « the same home » has one meaning for both.
"""

from collections import defaultdict
from collections.abc import Iterable
from typing import Protocol

from ..entities import Listing
from ..value_objects import HomeKey
from .duplicates import build_home_key


class HomeJudgement(Protocol):
    @property
    def listing_id(self) -> str: ...

    @property
    def source(self) -> str: ...

    @property
    def home_key(self) -> HomeKey | None: ...


class RecognisedHomes[J: HomeJudgement]:
    """O(j) to build for j judgements, O(s) per listing, s = judgements sharing its key."""

    def __init__(self, judgements: Iterable[J]) -> None:
        self._by_listing_id: dict[str, list[J]] = defaultdict(list)
        self._by_key: dict[HomeKey, list[J]] = defaultdict(list)
        for judgement in judgements:
            self._by_listing_id[judgement.listing_id].append(judgement)
            if judgement.home_key is not None:
                self._by_key[judgement.home_key].append(judgement)

    def find_judgements(self, listing: Listing) -> list[J]:
        found = list(self._by_listing_id.get(listing.id, ()))
        key = build_home_key(listing)
        if key is not None:
            found += [j for j in self._by_key.get(key, ()) if j.source != listing.source]
        return found
