"""PAP's commune lookup survives a refused request.

The crawler outlives one tick of `hunt watch` (the container builds it once), so a
failure written into its cache used to switch PAP off for the whole watch run: on
2026-09-25 one refused lookup left « No geo ID found for 'Annecy' » on every tick.
"""

import httpx
from faker import Faker

from apartment_hunter.infrastructure.crawlers.base_crawler import CRAWLER_USER_AGENT
from apartment_hunter.infrastructure.crawlers.pap_crawler import PapCrawler
from apartment_hunter.infrastructure.crawlers.robots import RobotsRules

fake = Faker("fr_FR")


class ScriptedPapGeo:
    """A concrete stand-in for /json/ac-geo: answers from a script, then records calls."""

    def __init__(self, *responses: httpx.Response) -> None:
        self._responses = list(responses)
        self.calls = 0

    def handle(self, request: httpx.Request) -> httpx.Response:
        self.calls += 1
        return self._responses.pop(0)


async def _answer_without_robots(_url: str) -> tuple[int, str]:
    """PAP serving no robots.txt (404): nothing is disallowed, and no network is used."""
    return (404, "")


def _build_crawler(geo: ScriptedPapGeo) -> PapCrawler:
    crawler = PapCrawler()
    crawler._client = httpx.AsyncClient(transport=httpx.MockTransport(geo.handle))
    crawler._robots = RobotsRules(CRAWLER_USER_AGENT, _answer_without_robots)
    return crawler


async def test_a_refused_lookup_is_retried_on_the_next_call() -> None:
    # Arrange
    city = fake.city()
    geo_id = fake.random_int(min=1, max=99999)
    geo = ScriptedPapGeo(
        httpx.Response(403, text="<html>blocked</html>"),
        httpx.Response(200, json=[{"id": geo_id, "name": f"{city} (74000)"}]),
    )
    crawler = _build_crawler(geo)
    await crawler._resolve_geo_id(city)

    # Act
    resolved = await crawler._resolve_geo_id(city)

    # Assert
    assert resolved == geo_id


async def test_a_commune_pap_does_not_know_is_not_asked_twice() -> None:
    # Arrange — an empty answer is a real answer, not a failure
    city = fake.city()
    geo = ScriptedPapGeo(httpx.Response(200, json=[]))
    crawler = _build_crawler(geo)
    await crawler._resolve_geo_id(city)

    # Act
    resolved = await crawler._resolve_geo_id(city)

    # Assert
    assert resolved is None
    assert geo.calls == 1
