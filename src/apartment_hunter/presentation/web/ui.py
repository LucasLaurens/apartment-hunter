"""The single-page web interface, assembled from its HTML, CSS and JS assets.

Markup, styles and behaviour live in `assets/` — editable with tooling that knows
those languages — and are inlined into one document here, so serving the UI stays a
single response with no static-file routes.
"""

from functools import cache
from pathlib import Path

_ASSETS = Path(__file__).parent / "assets"
_STYLES_TOKEN = "<!--styles-->"
_SCRIPT_TOKEN = "<!--script-->"


def _read_asset(name: str) -> str:
    return (_ASSETS / name).read_text(encoding="utf-8")


@cache
def render_html_page() -> str:
    """The full page. Cached: the assets cannot change while the server runs."""
    return (
        _read_asset("index.html")
        .replace(_STYLES_TOKEN, _read_asset("styles.css"))
        .replace(_SCRIPT_TOKEN, _read_asset("app.js"))
    )
