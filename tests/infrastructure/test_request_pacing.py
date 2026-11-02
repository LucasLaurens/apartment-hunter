"""A source is never hit faster than its courtesy budget allows.

`RATE_LIMIT_SECONDS` used to be read by `_get_throttled` alone — the path a single
crawler takes — while the eight others went through `_fetch_html` and paced nothing.
The arithmetic was also unprotected, so four concurrent commune searches read the same
deadline and fired together.
"""

import asyncio

from apartment_hunter.infrastructure.crawlers.base_crawler import BaseCrawler
from apartment_hunter.infrastructure.crawlers.century21_crawler import Century21Crawler
from apartment_hunter.infrastructure.crawlers.laforet_crawler import LaforetCrawler
from apartment_hunter.infrastructure.crawlers.pap_crawler import PapCrawler


class PacedCrawler(BaseCrawler):
    """A crawler that only records when the gate let it through — no network at all."""

    source_name = "paced"
    BASE_URL = "https://exemple.test"
    RATE_LIMIT_SECONDS = 0.12
    CITY_CONCURRENCY = 2

    def __init__(self) -> None:
        super().__init__()
        self.starts: list[float] = []

    async def fetch(self, search_filter: object) -> list[object]:  # pragma: no cover - unused
        return []

    async def take_turn(self) -> None:
        await self._await_turn()
        self.starts.append(asyncio.get_running_loop().time())


async def test_two_sequential_requests_are_spaced() -> None:
    # Arrange
    crawler = PacedCrawler()

    # Act
    await crawler.take_turn()
    await crawler.take_turn()

    # Assert
    gap = crawler.starts[1] - crawler.starts[0]
    assert gap >= crawler.compute_request_spacing_seconds()


async def test_concurrent_requests_do_not_fire_together() -> None:
    # Arrange — this is what the old unprotected arithmetic got wrong
    crawler = PacedCrawler()

    # Act
    await asyncio.gather(*(crawler.take_turn() for _ in range(4)))

    # Assert — every consecutive pair keeps its distance
    spacing = crawler.compute_request_spacing_seconds()
    starts = crawler.starts
    gaps = [starts[i + 1] - starts[i] for i in range(len(starts) - 1)]
    assert all(gap >= spacing * 0.9 for gap in gaps), gaps


def test_the_spacing_shares_the_budget_across_concurrent_communes() -> None:
    # Arrange — pacing serially at RATE_LIMIT_SECONDS would put 30 communes × 4 pages
    # past the 180 s per-source cap, so the budget is a window, not a serial delay.
    crawler = PacedCrawler()

    # Act
    spacing = crawler.compute_request_spacing_seconds()

    # Assert
    assert spacing == crawler.RATE_LIMIT_SECONDS / crawler.CITY_CONCURRENCY


def test_every_crawler_declares_a_positive_budget() -> None:
    # Arrange — a zero or negative budget would remove the gate entirely
    crawlers = [PapCrawler(), Century21Crawler(), LaforetCrawler()]

    # Act & Assert
    for crawler in crawlers:
        assert crawler.RATE_LIMIT_SECONDS > 0
        assert crawler.compute_request_spacing_seconds() > 0
