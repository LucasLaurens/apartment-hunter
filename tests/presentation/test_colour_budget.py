"""The colour budget (ticket 04): hue is spent on state, never on decoration.

"New" owns the accent; danger and warn mark a destructive action, an unsettled total
and a letting ban; the DPE/GES scale is regulatory. Anything else is a tinted neutral.
A portal hue, a pulsing card or a decorative tint creeping back fails here.
"""

import re
from pathlib import Path
from typing import Final

_STYLES: Final = (
    Path(__file__).parent.parent.parent
    / "src"
    / "apartment_hunter"
    / "presentation"
    / "web"
    / "assets"
    / "styles.css"
).read_text(encoding="utf-8")

ACCENT_HUE: Final = "157"
DANGER_HUE: Final = "27"
WARN_HUES: Final = frozenset({"70", "75"})
STATE_HUES: Final = frozenset({ACCENT_HUE, DANGER_HUE, *WARN_HUES, "var(--dpe-h)"})
# Neutrals are tinted toward the accent at chroma 0.004–0.020: up to this, a hue is a tint.
MAX_NEUTRAL_CHROMA: Final = 0.02
_OKLCH: Final = re.compile(r"oklch\(\s*[\d.]+%\s+([\d.]+)\s+([\d.]+|var\(--[a-z-]+\))")
_RULE: Final = re.compile(r"([^{}]+)\{([^{}]*)\}")


def test_every_coloured_value_is_a_state_hue() -> None:
    # Arrange
    colours = _OKLCH.findall(_STYLES)

    # Act — O(n) over the stylesheet
    decorative = sorted(
        {(chroma, hue) for chroma, hue in colours if float(chroma) > MAX_NEUTRAL_CHROMA}
        - {(chroma, hue) for chroma, hue in colours if hue in STATE_HUES}
    )

    # Assert
    assert colours, "no oklch() found — has the stylesheet moved?"
    assert not decorative, f"hue spent outside state: {decorative}"


def test_no_source_carries_a_hue() -> None:
    # Act & Assert
    assert "--src-h" not in _STYLES


def test_no_card_moves() -> None:
    # Arrange
    card_rules = [body for selector, body in _RULE.findall(_STYLES) if ".card" in selector]

    # Act
    animated = [body.strip() for body in card_rules if "animation" in body]

    # Assert
    assert card_rules, "no .card rule found — has the card markup moved?"
    assert not animated, f"a card animates: {animated}"
