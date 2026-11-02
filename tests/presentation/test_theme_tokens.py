"""The light and dark themes are one list of colours, not two (ADR-0011).

Every colour is written as `light-dark(light, dark)`, so a colour added with only its
light value would silently stay light in the dark theme. These guards fail on that, on
a second token block creeping back, and on the storage key drifting between the
<head> script that applies the choice and the audit that reloads with it.
"""

import re
from pathlib import Path
from typing import Final

_ROOT: Final = Path(__file__).parent.parent.parent
_ASSETS: Final = _ROOT / "src" / "apartment_hunter" / "presentation" / "web" / "assets"
_STYLES: Final = (_ASSETS / "styles.css").read_text(encoding="utf-8")
_INDEX_HTML: Final = (_ASSETS / "index.html").read_text(encoding="utf-8")
_VERIFY_UI: Final = (_ROOT / "scripts" / "verify_ui.py").read_text(encoding="utf-8")
_LIGHT_DARK: Final = "light-dark("


def _strip_light_dark_calls(css: str) -> str:
    """The stylesheet with every `light-dark(...)` call removed, nested parens included.

    O(n) time, O(n) space — n the stylesheet length, one pass with a depth counter.
    """
    kept: list[str] = []
    index = 0
    while (start := css.find(_LIGHT_DARK, index)) != -1:
        kept.append(css[index:start])
        depth, cursor = 1, start + len(_LIGHT_DARK)
        while depth:
            depth += {"(": 1, ")": -1}.get(css[cursor], 0)
            cursor += 1
        index = cursor
    kept.append(css[index:])
    return "".join(kept)


def test_every_colour_carries_its_dark_value() -> None:
    # Act
    outside = _strip_light_dark_calls(_STYLES)

    # Assert
    assert "oklch(" not in outside, "a colour is written without its dark value"


def test_there_is_no_second_token_block() -> None:
    # Act & Assert — "Système" is `color-scheme: light dark`, not a media query
    assert "prefers-color-scheme" not in _STYLES


def test_the_head_script_and_the_audit_share_one_storage_key() -> None:
    # Arrange
    head = re.search(r"const THEME_STORAGE_KEY = '([^']+)'", _INDEX_HTML)
    audit = re.search(r'THEME_STORAGE_KEY: Final = "([^"]+)"', _VERIFY_UI)

    # Act & Assert
    assert head is not None and audit is not None
    assert head.group(1) == audit.group(1)
