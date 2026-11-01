"""Whether the crawlers follow what each site asks of robots (ADR-0012).

HONOURED is the default: robots.txt is obeyed, and a source whose terms forbid
extracting its listings is not crawled. IGNORED is the hunter's own choice, at their
own risk: both are set aside. Neither ever touches the anti-bot line: no browser
imitation, no challenge solving, no account, whatever this says.
"""

from enum import StrEnum


class SiteRules(StrEnum):
    """Stored by value in SQLite: renaming a member's value is a data migration."""

    HONOURED = "honoured"
    IGNORED = "ignored"
