"""robots.txt, read once a day per host and obeyed by every crawler request (RFC 9309).

The collection rules say a site's robots.txt is never bypassed. Checking it by hand,
source by source, held only until a site changed its file: the gate now reads it.

- 2xx: the file's rules apply, `Crawl-delay` included.
- 4xx: the site publishes no rules, so nothing is disallowed (RFC 9309, 2.3.1.3).
- 5xx or no answer: the rules are unknown, so everything is disallowed until the next
  try (2.3.1.4). Not reading a site beats reading it against its will.
"""

import asyncio
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from http import HTTPStatus
from typing import Final
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser

ROBOTS_TTL_SECONDS: Final = 86_400
UNREACHABLE_RETRY_SECONDS: Final = 3_600
_ROBOTS_PATH: Final = "/robots.txt"

# The status and body of a robots.txt request, or None when the host did not answer.
type RobotsReader = Callable[[str], Awaitable[tuple[int, str] | None]]


class RobotsDisallowedError(Exception):
    """The site's robots.txt does not let this crawler fetch the URL."""


@dataclass(frozen=True)
class _HostRules:
    parser: RobotFileParser | None  # None: rules unknown, everything disallowed
    expires_at: float


class RobotsRules:
    """One crawler's view of the robots.txt of each host it visits.

    O(1) per check once a host is loaded (the parser scans its few rule lines); one
    request per host per day, never two at once.
    """

    def __init__(
        self,
        user_agent: str,
        read_robots: RobotsReader,
        read_clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._user_agent = user_agent
        self._read_robots = read_robots
        self._read_clock = read_clock
        self._by_host: dict[str, _HostRules] = {}
        self._lock = asyncio.Lock()

    async def is_allowed(self, url: str) -> bool:
        rules = await self._load(url)
        return rules.parser is not None and rules.parser.can_fetch(self._user_agent, url)

    async def find_crawl_delay(self, url: str) -> float:
        """Seconds the site asks between two requests; 0 when it asks nothing."""
        rules = await self._load(url)
        delay = rules.parser.crawl_delay(self._user_agent) if rules.parser else None
        return float(delay or 0)

    async def _load(self, url: str) -> _HostRules:
        parts = urlsplit(url)
        host = f"{parts.scheme}://{parts.netloc}"
        async with self._lock:
            cached = self._by_host.get(host)
            now = self._read_clock()
            if cached is not None and cached.expires_at > now:
                return cached
            rules = self._build_rules(await self._read_robots(host + _ROBOTS_PATH), now)
            self._by_host[host] = rules
            return rules

    @staticmethod
    def _build_rules(answer: tuple[int, str] | None, now: float) -> _HostRules:
        if answer is None or answer[0] >= HTTPStatus.INTERNAL_SERVER_ERROR:
            return _HostRules(parser=None, expires_at=now + UNREACHABLE_RETRY_SECONDS)
        status, body = answer
        parser = RobotFileParser()
        is_success = HTTPStatus.OK <= status < HTTPStatus.MULTIPLE_CHOICES
        parser.parse(body.splitlines() if is_success else [])
        return _HostRules(parser=parser, expires_at=now + ROBOTS_TTL_SECONDS)
