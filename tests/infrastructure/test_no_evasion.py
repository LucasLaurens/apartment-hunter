"""Crawlers ask honestly and take no for an answer (collection rules, CLAUDE.md).

No TLS-fingerprint imitation, no spoofed browser hints, no user-agent rotation, no
stealth: a source that only answers a disguised client is removed. The guard reads the
source tree, so a hurried edit cannot bring a trick back unnoticed; the server below
checks what a request actually carries.
"""

import threading
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest
from faker import Faker

from apartment_hunter.infrastructure.crawlers.base_crawler import (
    CRAWLER_USER_AGENT,
    BaseCrawler,
    build_page_headers,
)

_fake = Faker()
_SRC = Path(__file__).parents[2] / "src" / "apartment_hunter"
# Each one is how a client pretends to be someone else.
_EVASION_MARKERS = ("impersonat", "fake_useragent", "sec-ch-ua", "stealth", "webdriver")


def test_no_source_file_disguises_the_client() -> None:
    # Arrange
    sources = sorted(_SRC.rglob("*.py"))

    # Act
    offenders = [
        f"{path.relative_to(_SRC)}: {marker}"
        for path in sources
        for marker in _EVASION_MARKERS
        if marker in path.read_text().lower()
    ]

    # Assert
    assert sources
    assert not offenders, offenders


class _RefusingHandler(BaseHTTPRequestHandler):
    hits: list[str] = []

    def do_GET(self) -> None:  # noqa: N802 - http.server's own name
        type(self).hits.append(self.headers.get("User-Agent", ""))
        self.send_response(403)
        self.end_headers()

    def log_message(self, *args: object) -> None:
        pass


@pytest.fixture
def refusing_server() -> Iterator[str]:
    _RefusingHandler.hits = []
    server = HTTPServer(("127.0.0.1", 0), _RefusingHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_address[1]}"
    server.shutdown()
    server.server_close()


class _PlainCrawler(BaseCrawler):
    source_name = "plain"
    BASE_URL = "https://exemple.test"

    async def fetch(self, search_filter: object) -> list[object]:  # pragma: no cover - unused
        return []

    async def read_page(self, url: str) -> str | None:
        return await self._fetch_page(url, build_page_headers(self.BASE_URL))


async def test_a_refusal_is_taken_at_once_and_the_client_says_who_it_is(
    refusing_server: str,
) -> None:
    # Arrange
    crawler = _PlainCrawler()

    # Act
    body = await crawler.read_page(f"{refusing_server}/{_fake.slug()}")

    # Assert — one request, under the crawler's own name, then it gives up
    assert body is None
    assert _RefusingHandler.hits == [CRAWLER_USER_AGENT]
