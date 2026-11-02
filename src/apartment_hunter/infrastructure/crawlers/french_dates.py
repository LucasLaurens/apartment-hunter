"""Parse the publication dates French rental sites print on their listings.

Each site words it differently — an ISO timestamp in an embedded JSON payload
("2026-08-03T10:22:27+02:00"), a French numeric date ("03/08/2026"), a spelled-out
one ("Publié le 3 août 2026"), or a relative one ("il y a 2 jours", "hier").
`parse_french_date` accepts any of them so crawlers never repeat date plumbing.
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta

# Accents are stripped before matching, so only the unaccented spelling is needed.
_MONTHS: dict[str, int] = {
    "janvier": 1,
    "fevrier": 2,
    "mars": 3,
    "avril": 4,
    "mai": 5,
    "juin": 6,
    "juillet": 7,
    "aout": 8,
    "septembre": 9,
    "octobre": 10,
    "novembre": 11,
    "decembre": 12,
}
# "il y a 3 semaines" → 21 days. Months are counted as 30 days: sites use them as a
# coarse "older than a month" marker, never as a precise calendar offset.
_UNIT_DELTAS: dict[str, timedelta] = {
    "minute": timedelta(minutes=1),
    "heure": timedelta(hours=1),
    "jour": timedelta(days=1),
    "semaine": timedelta(weeks=1),
    "mois": timedelta(days=30),
}

_ISO_RE = re.compile(r"(20\d{2})-(\d{2})-(\d{2})(?:[T ](\d{2}):(\d{2})(?::(\d{2}))?)?")
_NUMERIC_RE = re.compile(r"\b(\d{1,2})/(\d{1,2})/(20\d{2})\b")
_SPELLED_RE = re.compile(
    r"\b(\d{1,2})(?:er)?\s+(" + "|".join(_MONTHS) + r")\.?\s+(20\d{2})\b", re.I
)
_AGO_RE = re.compile(r"il y a\s+(\d+)\s*(" + "|".join(_UNIT_DELTAS) + r")", re.I)
_TODAY_RE = re.compile(r"aujourd'hui", re.I)
_YESTERDAY_RE = re.compile(r"\bhier\b", re.I)

_ACCENTS = str.maketrans("àâäéèêëîïôöùûüç", "aaaeeeeiioouuuc")


def parse_french_date(text: str, *, now: datetime | None = None) -> datetime | None:
    """First publication date found in `text`, or None when it holds none.

    O(len(text)) time, O(1) space — a bounded set of regex scans over the snippet.
    Returned datetimes are naive local time: the rest of the app compares them to
    `datetime.now()`, and a tz-aware value would raise on subtraction.
    """
    if not text:
        return None
    reference = now or datetime.now()
    plain = text.translate(_ACCENTS)

    if m := _ISO_RE.search(plain):
        year, month, day = (int(m.group(i)) for i in (1, 2, 3))
        hour, minute, second = (int(m.group(i) or 0) for i in (4, 5, 6))
        return _build_safe_datetime(year, month, day, hour, minute, second)

    if m := _NUMERIC_RE.search(plain):
        return _build_safe_datetime(int(m.group(3)), int(m.group(2)), int(m.group(1)))

    if m := _SPELLED_RE.search(plain):
        return _build_safe_datetime(int(m.group(3)), _MONTHS[m.group(2).lower()], int(m.group(1)))

    if m := _AGO_RE.search(plain):
        return reference - int(m.group(1)) * _UNIT_DELTAS[m.group(2).lower()]

    if _TODAY_RE.search(plain):
        return reference
    if _YESTERDAY_RE.search(plain):
        return reference - timedelta(days=1)

    return None


def _build_safe_datetime(
    year: int, month: int, day: int, hour: int = 0, minute: int = 0, second: int = 0
) -> datetime | None:
    """A datetime, or None when the site printed an impossible date (e.g. 31/02)."""
    try:
        return datetime(year, month, day, hour, minute, second)
    except ValueError:
        return None
