"""What scraped text and scraped links must survive before the app trusts them.

Sites are third parties: a title can carry null bytes or a novel, and a listing's
`href` can carry any scheme at all. Cleaning happens once, at the storage boundary
(`SqliteRepository`), so every crawler — present and future — is covered without
each parser remembering the rule.
"""

from typing import Final
from urllib.parse import urlsplit

# A listing link is only ever followed by a browser or an e-mail client. Anything
# else (javascript:, data:, file:) is a script waiting for a click, not a listing.
WEB_SCHEMES: Final = frozenset({"http", "https"})

_NULL_BYTE: Final = "\x00"
MAX_TEXT_CHARS: Final = 500  # titles, cities, addresses, advertiser names
MAX_DESCRIPTION_CHARS: Final = 5_000  # a description, not a novel


def is_web_url(url: str) -> bool:
    """True for an http(s) URL with a host — the only kind we store or render."""
    parts = urlsplit(url)
    return parts.scheme.lower() in WEB_SCHEMES and bool(parts.netloc)


def clean_text(value: str | None, max_chars: int = MAX_TEXT_CHARS) -> str | None:
    """Trimmed, null-byte-free, length-capped text. None stays None.

    O(n) time, O(n) space — n = length of `value`.
    """
    if value is None:
        return None
    return value.replace(_NULL_BYTE, "").strip()[:max_chars]
