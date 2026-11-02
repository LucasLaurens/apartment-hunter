"""Yes / no / indifferent answers, as the CLI wizard and the web form both collect them."""

YES = "yes"
NO = "no"
INDIFFERENT = "both"
CHOICES = [YES, NO, INDIFFERENT]


def parse_tri_state(raw: object) -> bool | None:
    """True for "yes", False for "no", None for anything else (= no preference)."""
    if raw == YES:
        return True
    if raw == NO:
        return False
    return None
