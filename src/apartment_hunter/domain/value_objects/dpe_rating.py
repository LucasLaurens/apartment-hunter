import re
from enum import StrEnum

_RATING_RE = re.compile(r"\b[A-G]\b")


class DpeRating(StrEnum):
    A = "A"
    B = "B"
    C = "C"
    D = "D"
    E = "E"
    F = "F"
    G = "G"

    @staticmethod
    def _build_rating_order() -> list["DpeRating"]:
        return list(DpeRating)

    def compute_rank(self) -> int:
        return self._build_rating_order().index(self)

    @classmethod
    def up_to(cls, max_rating: "DpeRating") -> set["DpeRating"]:
        """All ratings at least as good as (≤) max_rating — e.g. up_to(D) = {A,B,C,D}."""
        order = cls._build_rating_order()
        return set(order[: max_rating.compute_rank() + 1])

    def __le__(self, other: object) -> bool:
        if not isinstance(other, DpeRating):
            return NotImplemented
        return self.compute_rank() <= other.compute_rank()

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, DpeRating):
            return NotImplemented
        return self.compute_rank() < other.compute_rank()

    def __ge__(self, other: object) -> bool:
        if not isinstance(other, DpeRating):
            return NotImplemented
        return self.compute_rank() >= other.compute_rank()

    def __gt__(self, other: object) -> bool:
        if not isinstance(other, DpeRating):
            return NotImplemented
        return self.compute_rank() > other.compute_rank()

    @classmethod
    def from_string(cls, value: str) -> "DpeRating | None":
        # Crawlers hand us messy labels ("F : 380 kWhEP/m².an", "Classe F").
        # Extract the first A–G letter rather than demanding an exact match,
        # else an unparsed F collapses to None and slips past the matcher.
        match = _RATING_RE.search(value.strip().upper())
        return cls(match.group()) if match else None
