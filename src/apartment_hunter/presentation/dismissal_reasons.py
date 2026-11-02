"""The closed list of dismissal reasons as the hunter types and reads them (ADR-0009).

One spelling for both screens: `hunt review` reads a key, the web page puts the same
keys on its reason bar, so the gesture learnt in one works in the other.
"""

from typing import Final

from ..domain.value_objects import DismissalReason

_KEYED_REASONS: Final = {
    "1": DismissalReason.TOO_EXPENSIVE,
    "2": DismissalReason.TOO_SMALL,
    "3": DismissalReason.FLOOR,
    "4": DismissalReason.DPE,
    "5": DismissalReason.CITY,
    "6": DismissalReason.ADVERTISER,
    "7": DismissalReason.FURNISHED,
    "8": DismissalReason.ASPECT,
    "0": DismissalReason.OTHER,
}
# The label is the domain's (`DismissalReason.label`): the alert speaks it too.
REASON_KEYS: Final[dict[str, tuple[DismissalReason, str]]] = {
    key: (reason, reason.label) for key, reason in _KEYED_REASONS.items()
}
REASON_LABELS: Final[dict[DismissalReason, str]] = dict(REASON_KEYS.values())
