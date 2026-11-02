"""Guards on the web assets, which have no JS test harness in this project.

Two rules live in `app.js` that a Python test can still watch: the escaper must cover
the attribute context, and a listing URL must never reach an `href` unfiltered. Both
were real holes; these assertions fail if either is undone. The third rule is a
duplicated bound — the form's `min`/`max` attributes and the domain's constants.
"""

import re
import shutil
import subprocess
from pathlib import Path
from typing import Final

import pytest

from apartment_hunter.domain.entities import (
    DEFAULT_MAX_RESULTS,
    DEFAULT_NOTIFICATION_INTERVAL_MINUTES,
    DEFAULT_RADIUS_KM,
    DEFAULT_REFRESH_INTERVAL_MINUTES,
    MAX_MAX_RESULTS,
    MAX_RADIUS_KM,
    MIN_INTERVAL_MINUTES,
    MIN_MAX_RESULTS,
    MIN_RADIUS_KM,
)
from apartment_hunter.domain.services import AdvertiserKind
from apartment_hunter.domain.value_objects import RENT_MAP_CREDIT, ListingSort

_ASSETS: Final = (
    Path(__file__).parent.parent.parent
    / "src"
    / "apartment_hunter"
    / "presentation"
    / "web"
    / "assets"
)
_APP_JS: Final = (_ASSETS / "app.js").read_text(encoding="utf-8")
_INDEX_HTML: Final = (_ASSETS / "index.html").read_text(encoding="utf-8")


def test_escaper_covers_the_attribute_context() -> None:
    # Act & Assert — escHtml output lands in attribute values, quotes included
    assert "&#39;" in _APP_JS
    assert "&#96;" in _APP_JS
    assert "&quot;" in _APP_JS


def test_no_scraped_value_is_interpolated_into_inline_js() -> None:
    # Arrange — every inline handler in the assets
    handlers = re.findall(r'on\w+="([^"]*)"', _APP_JS)

    # Act & Assert — an HTML entity is decoded before the handler body is compiled, so
    # escaping cannot protect that context: a source name travels as data instead.
    assert not [h for h in handlers if "escHtml(" in h], handlers
    assert '${DATA_SOURCE}="${escHtml(' in _APP_JS


def test_no_listing_url_reaches_an_href_unfiltered() -> None:
    # Arrange — every href interpolation in the assets
    hrefs = re.findall(r'href="\$\{([^}]+)\}"', _APP_JS)

    # Act & Assert — a listing URL must go through safeUrl() first
    assert hrefs, "no interpolated href found — has the card markup moved?"
    assert all("a.url" not in expression for expression in hrefs)
    assert "safeUrl(a.url)" in _APP_JS


def _read_numeric_attributes(field_id: str) -> dict[str, str]:
    field = re.search(rf'<input[^>]*id="{field_id}"[^>]*>', _INDEX_HTML)
    assert field, f"field {field_id} not found in index.html"
    return dict(re.findall(r'(min|max)="([^"]+)"', field.group(0)))


def test_form_radius_bounds_match_the_domain() -> None:
    # Act
    bounds = _read_numeric_attributes("fm-radius")

    # Assert
    assert float(bounds["min"]) == MIN_RADIUS_KM
    assert float(bounds["max"]) == MAX_RADIUS_KM


def test_form_result_cap_bounds_match_the_domain() -> None:
    # Act
    bounds = _read_numeric_attributes("fm-max-results")

    # Assert
    assert int(bounds["min"]) == MIN_MAX_RESULTS
    assert int(bounds["max"]) == MAX_MAX_RESULTS


def test_form_interval_minimums_match_the_domain() -> None:
    # Act
    notify = _read_numeric_attributes("fm-interval")
    refresh = _read_numeric_attributes("fm-refresh")

    # Assert
    assert int(notify["min"]) == MIN_INTERVAL_MINUTES
    assert int(refresh["min"]) == MIN_INTERVAL_MINUTES


def test_app_js_parses() -> None:
    """A rename once left two `const advertiser` in one scope — a dead page, green suite.

    Skipped rather than failed when Node is absent: a syntax check that cannot run must
    not be reported as a syntax check that passed, and the project already runs the page
    through Playwright in `make ui-check`.
    """
    # Arrange
    node = shutil.which("node")
    if node is None:
        pytest.skip("node absent — parse guard cannot run here")

    # Act
    check = subprocess.run([node, "--check", str(_ASSETS / "app.js")], capture_output=True)

    # Assert
    assert check.returncode == 0, check.stderr.decode()


def test_every_icon_used_by_the_script_exists_in_the_sprite() -> None:
    # Arrange — an unknown `#i-name` renders an empty box, silently
    block = re.search(r"const ICON = Object\.freeze\(\{(.*?)\}\);", _APP_JS, re.DOTALL)
    assert block is not None, "bloc ICON introuvable dans app.js"
    used = set(re.findall(r"'([a-z-]+)'", block.group(1)))
    defined = set(re.findall(r'<symbol id="i-([a-z-]+)"', _INDEX_HTML))

    # Act
    missing = used - defined

    # Assert
    assert not missing, f"icônes absentes du sprite : {sorted(missing)}"


# Hooks and default states that are meant to carry no rule of their own.
_UNSTYLED_CLASSES: Final = frozenset({"btn-watch-idle", "fm-dpe-cb"})


def test_every_class_in_the_markup_has_a_rule() -> None:
    """A stylesheet edit once deleted the modal, toast, form and pagination rules.

    The page kept working — every behaviour check passed — and simply rendered those
    parts unstyled. A class written in the markup with no rule is that defect.
    """
    # Arrange
    styles = re.sub(
        r"/\*.*?\*/", "", (_ASSETS / "styles.css").read_text(encoding="utf-8"), flags=re.S
    )
    styled = set(re.findall(r"\.([a-zA-Z][\w-]*)", styles))
    used = {
        name
        for source in (_INDEX_HTML, _APP_JS)
        for attribute in re.findall(r'class="([^"$]*)"', source)
        for name in attribute.split()
    }

    # Act
    unstyled = used - styled - _UNSTYLED_CLASSES

    # Assert
    assert not unstyled, f"classes sans règle : {sorted(unstyled)}"


_SRI: Final = re.compile(r"sha384-[A-Za-z0-9+/]{64}")
_PINNED_URL: Final = re.compile(r"@\d+\.\d+\.\d+/")


def test_the_map_library_is_pinned_and_integrity_checked() -> None:
    """The page's only third-party code (ticket 14): an exact version, and its hash.

    A floating version or a missing `integrity` lets a compromised CDN run code in the
    page that holds the hunter's filters and opens their links.
    """
    # Arrange
    block = re.search(r"const MAP_LIBRARY = Object\.freeze\(\{(.*?)\}\);", _APP_JS, re.DOTALL)
    assert block is not None, "MAP_LIBRARY introuvable dans app.js"
    urls = re.findall(r"'(https://[^']+)'", block.group(1))
    hashes = _SRI.findall(block.group(1))

    # Act & Assert
    assert urls and all(_PINNED_URL.search(url) for url in urls), urls
    assert len(hashes) == len(urls)
    assert "integrity: MAP_LIBRARY.JS_SRI" in _APP_JS
    assert "integrity: MAP_LIBRARY.CSS_SRI" in _APP_JS
    assert _APP_JS.count("crossOrigin: 'anonymous'") >= len(urls)


def test_no_external_tag_in_the_page_skips_integrity() -> None:
    # Arrange
    tags = re.findall(r"<(?:script|link)\b[^>]*(?:src|href)=\"https?://[^>]*>", _INDEX_HTML)

    # Act & Assert
    assert all("integrity=" in tag for tag in tags), tags


def test_map_popups_are_built_from_text_never_html() -> None:
    # Act & Assert — a commune name or a scraped title must never be parsed as markup
    assert "setHTML(" not in _APP_JS
    assert ".setDOMContent(content)" in _APP_JS
    # Every popup goes through the one opener, fed by a DOM builder.
    openers = re.findall(r"openMapPopup\(map, \[[^\]]+\], (\w+)\(", _APP_JS)
    assert openers and set(openers) <= {"buildPinDetail", "buildCommuneDetail"}, openers


# Line comments stop at the newline; block comments may span lines.
_JS_COMMENT: Final = re.compile(
    r"(^[ \t]*//[^\n]*)|([ \t]{2}//[^\n]*)|(/\*.*?\*/)", re.MULTILINE | re.DOTALL
)
_HTML_COMMENT: Final = re.compile(r"<!--.*?-->", re.DOTALL)


def test_no_em_dash_reaches_the_page_text() -> None:
    # Arrange — comments may keep theirs: only what the hunter reads is held (W22)
    script = _JS_COMMENT.sub("", _APP_JS)
    markup = _HTML_COMMENT.sub("", _INDEX_HTML)

    # Act
    offending = [line.strip() for line in (script + markup).splitlines() if "—" in line]

    # Assert
    assert offending == []


def test_every_listing_order_the_server_knows_is_offered_by_the_page() -> None:
    # Arrange
    script_sorts = set(re.findall(r"^\s+[A-Z_0-9]+: '([a-z_0-9]+)',$", _read_sort_enum(), re.M))

    # Act & Assert
    assert script_sorts == {sort.value for sort in ListingSort}


def _read_sort_enum() -> str:
    start = _APP_JS.index("const SORT = Object.freeze({")
    return _APP_JS[start : _APP_JS.index("});", start)]


def _read_js_object(name: str) -> dict[str, str]:
    """`const NAME = Object.freeze({KEY: value, ...})` as {KEY: 'value'}, quotes dropped."""
    match = re.search(rf"const {name} = Object\.freeze\(\{{(.*?)\}}\);", _APP_JS, re.S)
    assert match, f"{name} not found in app.js — has it moved?"
    pairs = re.findall(r"(\w+):\s*'?([^,'\n]+)'?", match.group(1))
    return {key: value.strip() for key, value in pairs}


def test_the_form_defaults_are_the_domain_defaults() -> None:
    # Act
    defaults = _read_js_object("DEFAULT")

    # Assert — a new filter must not start from different values on the web
    assert float(defaults["RADIUS_KM"]) == DEFAULT_RADIUS_KM
    assert int(defaults["MAX_RESULTS"]) == DEFAULT_MAX_RESULTS
    assert int(defaults["NOTIFY_INTERVAL_MIN"]) == DEFAULT_NOTIFICATION_INTERVAL_MINUTES
    assert int(defaults["REFRESH_INTERVAL_MIN"]) == DEFAULT_REFRESH_INTERVAL_MINUTES


def test_the_advertiser_kinds_are_the_domain_ones() -> None:
    # Act & Assert — the card compares the API's value against these
    assert set(_read_js_object("ADVERTISER").values()) == {kind.value for kind in AdvertiserKind}


def test_the_rent_map_credit_names_the_source_as_the_domain_does() -> None:
    # Act & Assert — Licence Ouverte: the web line must carry the same credit (ADR-0010)
    assert RENT_MAP_CREDIT[1:] in _APP_JS


def test_the_card_masonry_keeps_the_reading_order() -> None:
    """Cards are packed as a masonry by auto-placement, in DOM order.

    `dense` placement would fill a hole with a later card: the sort order would no
    longer be the reading order, and j/k would jump around the page.
    """
    # Arrange
    styles = (_ASSETS / "styles.css").read_text(encoding="utf-8")

    # Act
    dense = re.findall(r"grid-auto-flow\s*:[^;}]*dense", styles) + re.findall(
        r"gridAutoFlow[^;\n]*dense", _APP_JS
    )

    # Assert
    assert ".cards.is-masonry" in styles
    assert "MASONRY: 'is-masonry'" in _APP_JS
    assert not dense, "un placement `dense` réordonnerait les cartes"
