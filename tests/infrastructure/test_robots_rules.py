"""robots.txt decides, read once a day per host (RFC 9309), with a reader the test owns."""

import threading
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest
from faker import Faker

from apartment_hunter.domain.value_objects import SiteRules
from apartment_hunter.infrastructure.crawlers.base_crawler import BaseCrawler
from apartment_hunter.infrastructure.crawlers.robots import (
    ROBOTS_TTL_SECONDS,
    UNREACHABLE_RETRY_SECONDS,
    RobotsRules,
)

_fake = Faker()
_AGENT = "apartment-hunter/0.1 (personal home search)"


class InMemoryRobots:
    """Answers robots.txt requests from a table, and counts them."""

    def __init__(self, answer: tuple[int, str] | None) -> None:
        self.answer = answer
        self.reads: list[str] = []

    async def read(self, url: str) -> tuple[int, str] | None:
        self.reads.append(url)
        return self.answer


class ManualClock:
    def __init__(self) -> None:
        self.now = 0.0

    def read(self) -> float:
        return self.now


def _build_site() -> str:
    return f"https://{_fake.domain_name()}"


async def test_a_disallowed_path_is_refused_and_the_rest_allowed() -> None:
    # Arrange
    site = _build_site()
    robots = InMemoryRobots((200, "User-agent: *\nDisallow: /recherche/\n"))
    rules = RobotsRules(_AGENT, robots.read)

    # Act & Assert
    assert not await rules.is_allowed(f"{site}/recherche/annecy?page=2")
    assert await rules.is_allowed(f"{site}/location/annecy")


async def test_a_rule_naming_this_crawler_wins_over_the_wildcard() -> None:
    # Arrange
    robots = InMemoryRobots(
        (200, "User-agent: apartment-hunter\nDisallow: /\n\nUser-agent: *\nAllow: /\n")
    )
    rules = RobotsRules(_AGENT, robots.read)

    # Act & Assert
    assert not await rules.is_allowed(f"{_build_site()}/location/annecy")


@pytest.mark.parametrize("status", [404, 410, 403])
async def test_a_missing_file_means_no_rules(status: int) -> None:
    # Arrange
    rules = RobotsRules(_AGENT, InMemoryRobots((status, "")).read)

    # Act & Assert
    assert await rules.is_allowed(f"{_build_site()}/location/annecy")


@pytest.mark.parametrize("answer", [None, (503, ""), (500, "User-agent: *\nAllow: /\n")])
async def test_unknown_rules_disallow_everything(answer: tuple[int, str] | None) -> None:
    # Arrange — a server error or no answer: the rules are unknown
    rules = RobotsRules(_AGENT, InMemoryRobots(answer).read)

    # Act & Assert
    assert not await rules.is_allowed(f"{_build_site()}/location/annecy")


async def test_the_file_is_read_once_a_day_per_host() -> None:
    # Arrange
    site = _build_site()
    robots = InMemoryRobots((200, "User-agent: *\nAllow: /\n"))
    clock = ManualClock()
    rules = RobotsRules(_AGENT, robots.read, clock.read)

    # Act
    for page in range(_fake.random_int(3, 9)):
        await rules.is_allowed(f"{site}/location/annecy?page={page}")
    clock.now = ROBOTS_TTL_SECONDS + 1
    await rules.is_allowed(f"{site}/location/annecy")

    # Assert
    assert robots.reads == [f"{site}/robots.txt", f"{site}/robots.txt"]


async def test_an_unreachable_host_is_tried_again_an_hour_later() -> None:
    # Arrange
    site = _build_site()
    robots = InMemoryRobots(None)
    clock = ManualClock()
    rules = RobotsRules(_AGENT, robots.read, clock.read)
    await rules.is_allowed(f"{site}/a")

    # Act — the host answers again after the retry delay
    robots.answer = (200, "User-agent: *\nAllow: /\n")
    clock.now = UNREACHABLE_RETRY_SECONDS + 1
    allowed = await rules.is_allowed(f"{site}/a")

    # Assert
    assert allowed
    assert len(robots.reads) == 2


async def test_the_crawl_delay_is_read_for_this_crawler() -> None:
    # Arrange
    delay = _fake.random_int(5, 30)
    rules = RobotsRules(
        _AGENT, InMemoryRobots((200, f"User-agent: *\nCrawl-delay: {delay}\n")).read
    )

    # Act & Assert
    assert await rules.find_crawl_delay(f"{_build_site()}/location") == delay


class _SiteHandler(BaseHTTPRequestHandler):
    """A site whose robots.txt forbids /prive/, and that records every path asked."""

    paths: list[str] = []

    def do_GET(self) -> None:  # noqa: N802 - http.server's own name
        type(self).paths.append(self.path)
        body = b"User-agent: *\nDisallow: /prive/\n" if self.path == "/robots.txt" else b"<p>ok</p>"
        self.send_response(200)
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args: object) -> None:
        pass


@pytest.fixture
def site() -> Iterator[str]:
    _SiteHandler.paths = []
    server = HTTPServer(("127.0.0.1", 0), _SiteHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_address[1]}"
    server.shutdown()
    server.server_close()


class _SiteCrawler(BaseCrawler):
    source_name = "site"
    RATE_LIMIT_SECONDS = 0.0

    def __init__(self, base_url: str) -> None:
        super().__init__()
        self.BASE_URL = base_url

    async def fetch(self, search_filter: object) -> list[object]:  # pragma: no cover - unused
        return []

    async def read_html(self, url: str) -> str | None:
        return await self._fetch_html(url)


async def test_the_crawler_never_asks_for_a_path_robots_txt_forbids(site: str) -> None:
    # Arrange
    crawler = _SiteCrawler(site)
    allowed = f"/annonces/{_fake.slug()}"

    # Act
    refused_body = await crawler.read_html(f"{site}/prive/{_fake.slug()}")
    allowed_body = await crawler.read_html(f"{site}{allowed}")

    # Assert — robots.txt read once, the forbidden path never requested
    assert refused_body is None
    assert allowed_body == "<p>ok</p>"
    assert _SiteHandler.paths == ["/robots.txt", allowed]


async def test_wildcards_are_read_as_rfc_9309_says() -> None:
    # Arrange — PAP's own rule; Python 3.12's parser read it literally and allowed all
    site = _build_site()
    robots = InMemoryRobots((200, "User-agent: *\nDisallow: /*?*\nDisallow: /fin$\n"))
    rules = RobotsRules(_AGENT, robots.read)

    # Act & Assert
    assert not await rules.is_allowed(f"{site}/annonce/annecy?rayon=20")
    assert not await rules.is_allowed(f"{site}/fin")
    assert await rules.is_allowed(f"{site}/fine")


async def test_ignoring_the_sites_rules_skips_robots_txt_entirely(site: str) -> None:
    # Arrange — the hunter's own choice (ADR-0012); the anti-bot line does not move
    crawler = _SiteCrawler(site)
    crawler.apply_site_rules(SiteRules.IGNORED)
    forbidden = f"/prive/{_fake.slug()}"

    # Act
    body = await crawler.read_html(f"{site}{forbidden}")

    # Assert — robots.txt never asked, the page fetched
    assert body == "<p>ok</p>"
    assert _SiteHandler.paths == [forbidden]
