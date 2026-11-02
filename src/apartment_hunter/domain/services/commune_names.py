"""One commune, whatever the site calls it.

Every site spells a commune its own way: Laforêt drops accents and hyphens
("Saint Felix"), Century 21 capitalises each word ("Alby Sur Cheran"), the geo API
keeps the INSEE name ("Alby-sur-Chéran"). Wherever two names must be compared — the
matcher against the communes in radius, the home key of a duplicate or a dismissal —
both sides are folded here first, so no reader can disagree on what one commune is.
"""

import re
import unicodedata
from functools import lru_cache

_COMMUNE_SEPARATORS_RE = re.compile(r"[\s'’-]+")


@lru_cache(maxsize=4096)
def fold_commune_name(name: str) -> str:
    """ "Saint Felix", "SAINT-FÉLIX" and "saint-félix" all fold to "saint felix".

    Idempotent: folding a folded name changes nothing, which is what lets the
    `dismissals` migration rewrite stored names on every startup.
    """
    decomposed = unicodedata.normalize("NFKD", name.casefold())
    bare = "".join(c for c in decomposed if not unicodedata.combining(c))
    return _COMMUNE_SEPARATORS_RE.sub(" ", bare).strip()
