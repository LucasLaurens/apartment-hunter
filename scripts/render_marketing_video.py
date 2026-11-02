"""Render `marketing/video/stage.html` frame by frame, then encode the MP4 with ffmpeg.

    uv run python scripts/capture_marketing_media.py http://127.0.0.1:8001   # the stills first
    uv run python scripts/render_marketing_video.py square                   # 1080x1080
    uv run python scripts/render_marketing_video.py vertical                 # 1080x1920
    uv run python scripts/render_marketing_video.py vertical 3 12 25   # stills at those seconds

Every frame is a pure function of its time (`seek(t)` in the stage), so the clip is the same
whatever the speed of the machine.
"""

import asyncio
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Final

from playwright.async_api import async_playwright

_VIDEO: Final = Path(__file__).resolve().parent.parent / "marketing" / "video"
_FPS: Final = 30
_SIZES: Final = {"square": (1080, 1080), "vertical": (1080, 1920)}
_JPEG_QUALITY: Final = 95


async def render(format_name: str, stills: list[float]) -> None:
    width, height = _SIZES[format_name]
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch()
        page = await browser.new_page(viewport={"width": width, "height": height})
        await page.goto(f"{(_VIDEO / 'stage.html').as_uri()}?format={format_name}")
        await page.evaluate("window.ready")
        if stills:
            for second in stills:
                await page.evaluate("(t) => window.seek(t)", second)
                await page.screenshot(path=_VIDEO / f"still-{format_name}-{second:g}.png")
        else:
            duration = await page.evaluate("window.DURATION")
            with tempfile.TemporaryDirectory() as frames:
                # O(frames) screenshots, ~1 400 for a 46 s clip.
                for index in range(round(duration * _FPS)):
                    await page.evaluate("(t) => window.seek(t)", index / _FPS)
                    await page.screenshot(
                        path=Path(frames) / f"{index:05d}.jpg", type="jpeg", quality=_JPEG_QUALITY
                    )
                _encode(Path(frames), _VIDEO / f"apartment-hunter-{format_name}.mp4")
        await browser.close()


def _encode(frames: Path, output: Path) -> None:
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        sys.exit("ffmpeg not found")
    subprocess.run(
        [
            ffmpeg, "-y", "-loglevel", "error",
            "-framerate", str(_FPS), "-i", str(frames / "%05d.jpg"),
            "-c:v", "libx264", "-preset", "slow", "-crf", "18", "-pix_fmt", "yuv420p",
            "-movflags", "+faststart", str(output),
        ],
        check=True,
    )  # fmt: skip


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in _SIZES:
        formats = "|".join(_SIZES)
        sys.exit(f"usage: uv run python scripts/render_marketing_video.py {formats} [seconds…]")
    asyncio.run(render(sys.argv[1], [float(arg) for arg in sys.argv[2:]]))
