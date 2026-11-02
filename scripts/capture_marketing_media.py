"""Capture the stills the launch video is cut from, at twice the README's pixel density.

    uv run python scripts/seed_demo.py demo.db
    DATABASE_URL=demo.db uv run hunt serve --port 8001      # in another terminal
    uv run python scripts/capture_marketing_media.py http://127.0.0.1:8001

Writes `marketing/video/shots/`. Only the demo database's fictitious listings are captured.
"""

import asyncio
import sys
from pathlib import Path
from typing import Final

from capture_readme_media import _FILTER_ID, _THEME_KEY, _TILES_SETTLE_MS, _VIEWPORT, _open
from playwright.async_api import async_playwright

_SHOTS: Final = Path(__file__).resolve().parent.parent / "marketing" / "video" / "shots"
_SCALE: Final = 2
_CARD_SCALE: Final = 4
# The demo card that sits furthest under its commune's reference rent (« −17 % vs réf. »).
_BARGAIN_CARD: Final = 7


async def capture_shots(base_url: str) -> None:
    listings = f"{base_url}/?filtre={_FILTER_ID}"
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch()
        for theme in ("light", "dark"):
            context = await browser.new_context(
                viewport=_VIEWPORT, device_scale_factor=_SCALE, color_scheme=theme
            )
            await context.add_init_script(f"localStorage.setItem('{_THEME_KEY}', '{theme}')")
            page = await context.new_page()
            await _open(page, listings)
            await page.screenshot(path=_SHOTS / f"liste-{theme}.png")
            if theme == "dark":
                await context.close()
                continue
            await _open(page, f"{listings}&vue=carte", _TILES_SETTLE_MS)
            await page.locator(".map-pin").first.dispatch_event("click")
            await page.wait_for_timeout(600)
            await page.screenshot(path=_SHOTS / "carte.png")
            await _open(page, listings)
            await page.locator("[data-dismiss-id]").first.click()
            await page.wait_for_timeout(400)
            await page.screenshot(path=_SHOTS / "ecarter.png")
            await page.keyboard.press("Escape")
            await page.locator('[aria-label^="Modifier le filtre"]').click()
            await page.wait_for_timeout(_TILES_SETTLE_MS)
            await page.locator("#filterMap").scroll_into_view_if_needed()
            await page.screenshot(path=_SHOTS / "filtre.png")
            await context.close()
        # One card fills the frame on its own, so it needs twice the density of a page.
        context = await browser.new_context(
            viewport=_VIEWPORT, device_scale_factor=_CARD_SCALE, color_scheme="light"
        )
        await context.add_init_script(f"localStorage.setItem('{_THEME_KEY}', 'light')")
        page = await context.new_page()
        await _open(page, listings)
        await page.locator(".card").nth(_BARGAIN_CARD).screenshot(path=_SHOTS / "carte-annonce.png")
        await context.close()
        await browser.close()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("usage: uv run python scripts/capture_marketing_media.py <url>")
    _SHOTS.mkdir(parents=True, exist_ok=True)
    asyncio.run(capture_shots(sys.argv[1].rstrip("/")))
    print(f"written: {sorted(p.name for p in _SHOTS.iterdir())}")
