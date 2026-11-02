"""Regenerate the README's screenshots, clip and terminal capture from the demo database.

    uv run python scripts/seed_demo.py demo.db
    DATABASE_URL=demo.db uv run hunt serve --port 8001      # in another terminal
    DATABASE_URL=demo.db uv run python scripts/capture_readme_media.py http://127.0.0.1:8001

Writes `docs/media/`. Only the demo database's fictitious listings are ever captured.
The clip needs ffmpeg (webm → gif).
"""

import asyncio
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Final

from playwright.async_api import Page, async_playwright
from rich.console import Console

_MEDIA: Final = Path(__file__).resolve().parent.parent / "docs" / "media"
_FILTER_ID: Final = "demo"
_VIEWPORT: Final = {"width": 1280, "height": 800}
_THEME_KEY: Final = "ah-theme"  # THEME_STORAGE_KEY in index.html
_TILES_SETTLE_MS: Final = 6000  # OpenFreeMap tiles arrive well after the page
_GIF_FPS: Final = 6
_GIF_WIDTH: Final = 800
_REVIEW_WIDTH: Final = 132
_REVIEW_HEIGHT: Final = 22


async def _open(page: Page, url: str, wait_ms: int = 1500) -> None:
    """Load `url`; a list view waits for its cards (the first load geocodes the area)."""
    await page.goto(url)
    if "vue=carte" not in url:
        await page.wait_for_selector(".card", timeout=60_000)
    await page.wait_for_timeout(wait_ms)


async def capture_pages(base_url: str) -> None:
    listings = f"{base_url}/?filtre={_FILTER_ID}"
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch()
        for theme in ("light", "dark"):
            context = await browser.new_context(viewport=_VIEWPORT, color_scheme=theme)
            await context.add_init_script(f"localStorage.setItem('{_THEME_KEY}', '{theme}')")
            page = await context.new_page()
            await _open(page, listings)
            await page.screenshot(path=_MEDIA / f"liste-{theme}.png")
            if theme == "light":
                await _open(page, f"{listings}&vue=carte", _TILES_SETTLE_MS)
                await page.locator(".map-pin").first.dispatch_event("click")
                await page.wait_for_timeout(600)
                await page.screenshot(path=_MEDIA / "carte.png")
                await _open(page, listings)
                await page.locator("[data-dismiss-id]").first.click()
                await page.wait_for_timeout(400)
                await page.screenshot(path=_MEDIA / "ecarter.png")
                await page.keyboard.press("Escape")
                await page.locator('[aria-label^="Modifier le filtre"]').click()
                await page.wait_for_timeout(_TILES_SETTLE_MS)
                await page.locator("#filterMap").scroll_into_view_if_needed()
                await page.screenshot(path=_MEDIA / "filtre.png")
            await context.close()
        await _record_clip(browser, listings)
        await browser.close()


async def _record_clip(browser: object, listings: str) -> None:
    """A short tour: the list, a sort, the map and a pin, a dismissal, back to the list."""
    with tempfile.TemporaryDirectory() as video_dir:
        context = await browser.new_context(  # type: ignore[attr-defined]
            viewport=_VIEWPORT,
            color_scheme="light",
            record_video_dir=video_dir,
            record_video_size=_VIEWPORT,
        )
        page = await context.new_page()
        await _open(page, listings, 2000)
        await page.mouse.wheel(0, 500)
        await page.wait_for_timeout(1200)
        await page.mouse.wheel(0, -500)
        await page.select_option("#sortSelect", index=1)
        await page.wait_for_selector(".card")
        await page.wait_for_timeout(1500)
        await page.locator('[data-view="map"]').click()
        await page.wait_for_timeout(_TILES_SETTLE_MS)
        await page.locator(".map-pin").first.dispatch_event("click")
        await page.wait_for_timeout(2000)
        await page.keyboard.press("Escape")
        await page.locator('[data-view="list"]').click()
        await page.wait_for_timeout(1200)
        await page.locator("[data-dismiss-id]").first.click()
        await page.wait_for_timeout(1500)
        await page.keyboard.press("1")
        await page.wait_for_timeout(2500)
        await context.close()
        webm = next(Path(video_dir).glob("*.webm"))
        _convert_to_gif(webm, _MEDIA / "visite.gif")


def _convert_to_gif(webm: Path, gif: Path) -> None:
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        print("ffmpeg not found: clip skipped")
        return
    scale = f"fps={_GIF_FPS},scale={_GIF_WIDTH}:-1:flags=lanczos"
    subprocess.run(
        [
            ffmpeg,
            "-y",
            "-loglevel",
            "error",
            "-i",
            str(webm),
            "-vf",
            f"{scale},split[a][b];[a]palettegen=max_colors=64:stats_mode=diff[p];[b][p]paletteuse=dither=bayer:bayer_scale=4:diff_mode=rectangle",
            str(gif),
        ],
        check=True,
    )


async def capture_review() -> None:
    """`hunt review` as the terminal draws it, on the demo filter, saved as SVG."""
    from apartment_hunter.infrastructure.config import get_settings
    from apartment_hunter.infrastructure.container import Container
    from apartment_hunter.presentation.cli.review import ReviewScreen

    container = Container(get_settings())
    await container.repository.connect()
    try:
        search_filter = next(
            f
            for f in await container.make_manage_filters_use_case().list_all()
            if f.id == _FILTER_ID
        )
        screen = ReviewScreen(search_filter, [])
        # The order `hunt review` opens on, which its header names.
        screen.groups = await container.make_get_top_use_case().execute(
            search_filter, search_filter.max_results, sort=screen.sort
        )
    finally:
        await container.close()
    console = Console(record=True, width=_REVIEW_WIDTH, force_terminal=True)
    console.print(screen.render(_REVIEW_HEIGHT))
    console.save_svg(str(_MEDIA / "hunt-review.svg"), title="hunt review")


if __name__ == "__main__":
    if len(sys.argv) != 2 or "DATABASE_URL" not in os.environ:
        sys.exit("usage: DATABASE_URL=demo.db uv run python scripts/capture_readme_media.py <url>")
    _MEDIA.mkdir(parents=True, exist_ok=True)
    asyncio.run(capture_pages(sys.argv[1].rstrip("/")))
    asyncio.run(capture_review())
    print(f"written: {sorted(p.name for p in _MEDIA.iterdir())}")
