"""Translate the web page's dismissal body into a reason and a note."""

from typing import Any

from ...domain.value_objects import DismissalReason


def parse_dismissal(body: dict[str, Any]) -> tuple[DismissalReason, str]:
    """Raises ValueError on an unknown reason, or a note on any reason but « autre »."""
    reason = DismissalReason(str(body.get("reason", "")))
    note = str(body.get("note") or "").strip()
    if note and reason is not DismissalReason.OTHER:
        raise ValueError("Seule la raison « autre » porte un texte libre.")
    return reason, note
