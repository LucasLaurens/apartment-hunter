"""
Check the web interface against the rules it claims to follow: WCAG AA contrast in
every theme, the saved theme applied before first paint, keyboard reachability, named
icon controls, no layout overflow.

The interface must be running first (`make dev`), then:
    make ui-check                 # http://127.0.0.1:8001
    make ui-check PORT=8123       # another port

Screenshots land next to the checks so the visual result is looked at, not assumed:
a green run is not evidence for anything visual.
"""

import asyncio
import sys
import unicodedata
from pathlib import Path
from typing import Final

from playwright.async_api import Page, async_playwright

BASE_URL: Final = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8001/"
OUT_DIR: Final = Path(__file__).parent.parent / ".ui-screenshots"

# WCAG 2.1 AA
MIN_TEXT_CONTRAST: Final = 4.5
MIN_UI_CONTRAST: Final = 3.0

DESKTOP: Final = (1440, 900)
TABLET: Final = (768, 1000)
MOBILE: Final = (390, 844)
VIEWPORTS: Final[dict[str, tuple[int, int]]] = {
    "desktop": DESKTOP,
    "tablet": TABLET,
    "mobile": MOBILE,
}
LOAD_TIMEOUT_MS: Final = 20_000
MODAL_CLOSE_WAIT_MS: Final = 200
VIEWPORT_SETTLE_MS: Final = 300

# Selectors and ids, mirrored from index.html — one spelling each.
SKIP_LINK_CLASS: Final = "skip-link"
NAME_FIELD: Final = "fm-name"
NAME_ERROR: Final = f"#{NAME_FIELD}-error"
MODAL_VISIBLE_SELECTOR: Final = "#filterModal[style*='flex']"
CONTENT_READY_SELECTOR: Final = ".card, .empty"
OPEN_MODAL_BUTTON: Final = "button:has-text('Nouveau filtre')"
SAVE_BUTTON: Final = "button:has-text('Enregistrer')"
MODAL_DISPLAY_JS: Final = "document.getElementById('filterModal').style.display"
HIDDEN_DISPLAY: Final = "none"

# Mirrored from the <head> script of index.html (ADR-0011).
THEME_STORAGE_KEY: Final = "ah-theme"
THEMES: Final = ("light", "dark")
SET_THEME_JS: Final = "([key, theme]) => localStorage.setItem(key, theme)"
READ_THEME_JS: Final = "document.documentElement.dataset.theme"

# (label, element owning the background, element owning the text)
PROBES: Final[list[tuple[str, str, str]]] = [
    ("titre de carte", ".card", ".card-title"),
    ("ligne argent (muted)", ".card", ".card-money"),
    ("prix", ".card", ".card-price"),
    ("bouton primaire", "#searchBtn", "#searchBtn"),
    ("pastille source", ".source-pill", ".source-pill"),
    ("badge DPE", ".dpe-badge", ".dpe-badge"),
    ("ligne de décision", ".card", ".card-facts"),
    # Regulatory notices carry a legal consequence: they must be as readable as body
    # text, not a decorative tint.
    ("avertissement DPE", ".card-warning", ".card-warning"),
    ("charges inconnues", ".card", ".card .is-uncertain"),
    ("meta de filtre", "aside", ".filter-meta"),
]

# Computed styles come back in OKLCH; let the browser rasterise them to sRGB
# rather than reimplementing the conversion here.
_TO_RGB_JS: Final = """
color => {
  const c = document.createElement('canvas');
  c.width = c.height = 1;
  const ctx = c.getContext('2d');
  ctx.fillStyle = color;
  ctx.fillRect(0, 0, 1, 1);
  return [...ctx.getImageData(0, 0, 1, 1).data].slice(0, 3);
}
"""

_UNNAMED_BUTTONS_JS: Final = """
[...document.querySelectorAll('button')]
  .filter(b => !b.innerText.trim() && !b.getAttribute('aria-label'))
  .map(b => b.outerHTML.slice(0, 80))
"""


Rgb = tuple[float, float, float]


def _compute_relative_luminance(rgb: Rgb) -> float:
    """WCAG relative luminance. O(1)."""

    def convert_channel(value: float) -> float:
        srgb = value / 255
        return srgb / 12.92 if srgb <= 0.03928 else ((srgb + 0.055) / 1.055) ** 2.4

    red, green, blue = (convert_channel(c) for c in rgb)
    return 0.2126 * red + 0.7152 * green + 0.0722 * blue


def compute_contrast_ratio(foreground: Rgb, background: Rgb) -> float:
    lighter = max(_compute_relative_luminance(foreground), _compute_relative_luminance(background))
    darker = min(_compute_relative_luminance(foreground), _compute_relative_luminance(background))
    return (lighter + 0.05) / (darker + 0.05)


async def _to_rgb(page: Page, css_color: str) -> Rgb:
    red, green, blue = await page.evaluate(_TO_RGB_JS, css_color)
    return float(red), float(green), float(blue)


async def check_contrast(page: Page) -> list[str]:
    print(f"== Contraste (AA : {MIN_TEXT_CONTRAST}:1 texte, {MIN_UI_CONTRAST}:1 UI) ==")
    failures: list[str] = []
    body_bg = await page.evaluate("getComputedStyle(document.body).backgroundColor")
    for label, bg_selector, fg_selector in PROBES:
        bg_el = await page.query_selector(bg_selector)
        fg_el = await page.query_selector(fg_selector)
        if bg_el is None or fg_el is None:
            print(f"  {label:18} absent de la page — non vérifié")
            continue
        background = await bg_el.evaluate("e => getComputedStyle(e).backgroundColor")
        foreground = await fg_el.evaluate("e => getComputedStyle(e).color")
        if "rgba(0, 0, 0, 0)" in background or "transparent" in background:
            background = body_bg
        foreground_rgb = await _to_rgb(page, foreground)
        ratio = compute_contrast_ratio(foreground_rgb, await _to_rgb(page, background))
        if ratio >= MIN_TEXT_CONTRAST:
            verdict = "OK"
        else:
            verdict = "UI" if ratio >= MIN_UI_CONTRAST else "BAS"
        print(f"  {label:18} {ratio:5.2f}:1  [{verdict}]")
        if ratio < MIN_TEXT_CONTRAST:
            failures.append(f"contraste {label} à {ratio:.2f}:1")
    return failures


async def check_every_theme(page: Page) -> list[str]:
    """AA contrast in each theme, and the saved choice applied by the time the page loads.

    The choice is set in storage and the page reloaded, as a returning visitor would see
    it — not toggled live, which would skip the <head> script that prevents the flash.
    """
    failures: list[str] = []
    for theme in THEMES:
        await page.evaluate(SET_THEME_JS, [THEME_STORAGE_KEY, theme])
        await page.reload(wait_until="networkidle")
        await page.wait_for_selector(CONTENT_READY_SELECTOR, timeout=LOAD_TIMEOUT_MS)
        applied = await page.evaluate(READ_THEME_JS)
        print(f"== Thème {theme} : appliqué au chargement = {applied} ==")
        if applied != theme:
            failures.append(f"thème {theme} enregistré mais {applied} appliqué au chargement")
        failures += [f"[{theme}] {failure}" for failure in await check_contrast(page)]
        await page.screenshot(path=str(OUT_DIR / f"ui-theme-{theme}.png"))
    await page.evaluate(SET_THEME_JS, [THEME_STORAGE_KEY, THEMES[0]])
    await page.reload(wait_until="networkidle")
    await page.wait_for_selector(CONTENT_READY_SELECTOR, timeout=LOAD_TIMEOUT_MS)
    return failures


_PICTOGRAPH_CATEGORY: Final = "So"

async def check_no_emoji_icons(page: Page) -> list[str]:
    text = await page.evaluate("document.body.innerText")
    # A pictograph is a "Symbol, other" (🔔, ✓, ★). A code-point bound flagged typography
    # too: the minus sign of « −12 % » (U+2212) is a maths symbol, not an icon.
    emoji = sorted({char for char in text if unicodedata.category(char) == _PICTOGRAPH_CATEGORY})
    print(f"== Emoji rendus comme icônes : {emoji or 'aucun'} ==")
    return [f"emoji utilisé comme icône : {emoji}"] if emoji else []


async def check_keyboard(page: Page) -> list[str]:
    await page.keyboard.press("Tab")
    first = await page.evaluate("document.activeElement.className")
    print(f"== Premier arrêt de tabulation : {first!r} ==")
    if SKIP_LINK_CLASS in str(first):
        return []
    return [f"premier arrêt de tabulation inattendu : {first!r}"]


async def check_modal(page: Page) -> list[str]:
    failures: list[str] = []
    await page.click(OPEN_MODAL_BUTTON)
    await page.wait_for_selector(MODAL_VISIBLE_SELECTOR)

    focused = await page.evaluate("document.activeElement.id")
    print(f"== Modale ouverte, focus sur : {focused!r} ==")
    if focused != NAME_FIELD:
        failures.append(f"focus de la modale sur {focused!r} au lieu de {NAME_FIELD}")
    await page.screenshot(path=str(OUT_DIR / "ui-modal.png"))

    # An empty required field must surface an inline error, not a silent focus jump.
    await page.click(SAVE_BUTTON)
    error_shown = await page.is_visible(NAME_ERROR)
    invalid = await page.get_attribute(f"#{NAME_FIELD}", "aria-invalid")
    print(f"== Erreur inline affichée : {error_shown}, aria-invalid={invalid!r} ==")
    if not error_shown or invalid != "true":
        failures.append("validation inline non affichée sur champ requis vide")
    await page.screenshot(path=str(OUT_DIR / "ui-modal-error.png"))

    await page.keyboard.press("Escape")
    await page.wait_for_timeout(MODAL_CLOSE_WAIT_MS)
    display = await page.evaluate(MODAL_DISPLAY_JS)
    print(f"== Échap ferme la modale : display={display!r} ==")
    if display != HIDDEN_DISPLAY:
        failures.append("Échap ne ferme pas la modale")
    return failures


async def check_named_controls(page: Page) -> list[str]:
    unnamed = await page.evaluate(_UNNAMED_BUTTONS_JS)
    print(f"== Boutons sans nom accessible : {unnamed or 'aucun'} ==")
    return [f"boutons icône sans nom accessible : {unnamed}"] if unnamed else []


async def check_no_overflow(page: Page) -> list[str]:
    narrow_width, narrow_height = MOBILE
    await page.set_viewport_size({"width": narrow_width, "height": narrow_height})
    await page.wait_for_timeout(MODAL_CLOSE_WAIT_MS)
    overflow = await page.evaluate(
        "document.documentElement.scrollWidth - document.documentElement.clientWidth"
    )
    print(f"== Débordement horizontal à {narrow_width}px : {overflow}px ==")
    if overflow <= 0:
        return []
    return [f"débordement horizontal de {overflow}px à {narrow_width}px"]


async def main() -> int:
    OUT_DIR.mkdir(exist_ok=True)
    failures: list[str] = []
    console_errors: list[str] = []

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch()
        desktop_width, desktop_height = DESKTOP
        page = await browser.new_page(viewport={"width": desktop_width, "height": desktop_height})
        page.on("console", lambda m: console_errors.append(m.text) if m.type == "error" else None)
        page.on("pageerror", lambda e: console_errors.append(str(e)))

        await page.goto(BASE_URL, wait_until="networkidle")
        await page.wait_for_selector(CONTENT_READY_SELECTOR, timeout=LOAD_TIMEOUT_MS)

        for name, (width, height) in VIEWPORTS.items():
            await page.set_viewport_size({"width": width, "height": height})
            await page.wait_for_timeout(VIEWPORT_SETTLE_MS)
            await page.screenshot(path=str(OUT_DIR / f"ui-{name}.png"))
        await page.set_viewport_size({"width": desktop_width, "height": desktop_height})

        failures += await check_every_theme(page)
        failures += await check_no_emoji_icons(page)
        failures += await check_keyboard(page)
        failures += await check_modal(page)
        failures += await check_named_controls(page)
        failures += await check_no_overflow(page)

        print(f"== Erreurs console : {console_errors or 'aucune'} ==")
        if console_errors:
            failures.append(f"erreurs console : {console_errors}")

        await browser.close()

    print(f"\nCaptures écrites dans {OUT_DIR} — à regarder, pas à supposer.")
    if failures:
        print("ÉCHECS :\n  " + "\n  ".join(failures))
        return 1
    print("TOUTES LES VÉRIFICATIONS PASSENT")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
