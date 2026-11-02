"""Whether a listing advertises itself as furnished, read from its wording.

Most sources expose no furnished flag, so the rule lives in one place: crawlers apply
it while parsing a card, again on the detail page they fetch, and ListingMatcher
applies it a last time to listings that reached the database without one.

Three entry points, because the three texts differ in how much noise they carry:

* `detect_furnished` — a card's own text, or a title/description pair. Bare wording
  counts there ("Appartement meublé T2").
* `detect_furnished_label` — a whole detail page. Only the criteria-table form counts
  ("Meublé : Non"), because a page's nav and footer link to "location meublée <ville>"
  and the bare wording would read almost every page as furnished.
* `detect_furnished_chip` — the criteria chips of a detail page, each already scoped by
  the crawler to the listing's own table. A chip is a bare word ("Meublé", Laforêt), so
  the labelled reading finds nothing; only a chip that *is* the word counts.
"""

import re
from collections.abc import Iterable

# Criteria tables print the answer next to the label: "Meublé : Non", "Meublé Oui",
# "Meublé ? oui". Read *before* the bare-word rules below, which would otherwise see
# the "Meublé" of "Meublé : Non" and call the listing furnished.
_LABEL_RE = re.compile(r"meubl\w*\s*[:?\-–]?\s*(oui|non)\b", re.I)
# "meublé/meublée", but the negation forms ("non meublé", "vide") must win.
_NON_MEUBLE_RE = re.compile(r"non[\s-]*meubl|\bvide\b|non[\s-]*équipé", re.I)
_MEUBLE_RE = re.compile(r"\bmeubl(?:é|ée|e|és|ées)\b", re.I)
# A criteria chip states the whole answer in its own text: "Meublé", "Non meublé".
# Anchored on both ends so a longer wording ("Location meublée Annecy") can't match.
_MEUBLE_CHIP_RE = re.compile(r"meubl(?:é|ée|e)", re.I)
_NON_MEUBLE_CHIP_RE = re.compile(r"non[\s-]*meubl(?:é|ée|e)", re.I)


def detect_furnished(text: str) -> bool | None:
    """True/False from the listing's wording, None when it says nothing either way."""
    labelled = detect_furnished_label(text)
    if labelled is not None:
        return labelled
    if _NON_MEUBLE_RE.search(text):
        return False
    if _MEUBLE_RE.search(text):
        return True
    return None


def detect_furnished_label(text: str) -> bool | None:
    """The criteria-table answer only ("Meublé : Non"), None when the text has none.

    Safe to run over an entire detail page: the label form states the listing's own
    answer, whereas the bare word appears in every site's own navigation.
    """
    m = _LABEL_RE.search(text)
    if m is None:
        return None
    return m.group(1).lower() == "oui"


def detect_furnished_chip(chips: Iterable[str]) -> bool | None:
    """The criteria chips' answer, None when none of them mentions furnishing.

    Some sites print furnishing as a bare chip beside "Ascenseur" and "Terrasse", with
    no "Oui"/"Non" to label it, so `detect_furnished_label` reads such a page as silent
    and the *non meublé* filter lets a meublé through. A chip counts only when its whole
    text is the word: the crawler scopes the chips to the listing's own criteria table,
    and the full-string match keeps a stray "Location meublée Annecy" out even so.

    A "Non meublé" chip wins over a "Meublé" one — the negation is the explicit answer.

    O(total chip length): one anchored match per chip, no scan over the page.
    """
    verdict: bool | None = None
    for chip in chips:
        text = chip.strip()
        labelled = detect_furnished_label(text)
        if labelled is not None:
            return labelled
        if _NON_MEUBLE_CHIP_RE.fullmatch(text):
            return False
        if _MEUBLE_CHIP_RE.fullmatch(text):
            verdict = True
    return verdict
