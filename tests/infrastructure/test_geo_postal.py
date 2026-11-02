"""Seeded postal codes win over the ambiguous name-only lookup."""

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest
from faker import Faker

from apartment_hunter.infrastructure.crawlers import geo_postal
from apartment_hunter.infrastructure.crawlers.geo_postal import (
    resolve_postal_code,
    seed_postal_code,
)

_fake = Faker("fr_FR")


async def test_a_seeded_code_is_returned_without_a_network_lookup() -> None:
    # Arrange — a commune name shared by several departments
    city = f"Saint-{_fake.unique.first_name()}"
    seed_postal_code(city, "74540")

    # Act
    postal = await resolve_postal_code(city)

    # Assert
    assert postal == "74540"


async def test_a_later_seed_replaces_an_earlier_one() -> None:
    # Arrange — the radius expansion knows better than an earlier guess
    city = f"Saint-{_fake.unique.first_name()}"
    seed_postal_code(city, "07300")

    # Act
    seed_postal_code(city, "74540")

    # Assert
    assert await resolve_postal_code(city) == "74540"


async def test_an_empty_code_is_ignored() -> None:
    # Arrange — a commune the API returned without any postal code
    city = f"Saint-{_fake.unique.first_name()}"
    seed_postal_code(city, "74540")

    # Act
    seed_postal_code(city, "")

    # Assert — the known code must survive a blank seed
    assert await resolve_postal_code(city) == "74540"


class ScriptedGeoApi:
    """A local stand-in for geo.api.gouv.fr: serves scripted statuses, counts requests."""

    def __init__(self, *answers: tuple[int, str]) -> None:
        self._answers = list(answers)
        self.requests = 0
        handler = self._build_handler()
        self._server = HTTPServer(("127.0.0.1", 0), handler)
        threading.Thread(target=self._server.serve_forever, daemon=True).start()
        self.url = f"http://127.0.0.1:{self._server.server_port}/communes"

    def _build_handler(self) -> type[BaseHTTPRequestHandler]:
        api = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:
                api.requests += 1
                status, body = api._answers.pop(0)
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(body.encode())

            def log_message(self, *args: object) -> None:
                pass

        return Handler

    def close(self) -> None:
        self._server.shutdown()


async def test_a_failed_lookup_is_retried_on_the_next_call(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Arrange — a transient 500 used to be remembered as "no postal code" for good
    city = f"Saint-{_fake.unique.first_name()}"
    postal = f"74{_fake.random_int(100, 999)}"
    api = ScriptedGeoApi((500, "{}"), (200, json.dumps([{"codesPostaux": [postal]}])))
    monkeypatch.setattr(geo_postal, "_GEO_API", api.url)
    await resolve_postal_code(city)

    # Act
    resolved = await resolve_postal_code(city)

    # Assert
    api.close()
    assert resolved == postal


async def test_a_commune_the_api_does_not_know_is_not_asked_twice(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Arrange — an empty answer is a real answer, not a failure
    city = f"Saint-{_fake.unique.first_name()}"
    api = ScriptedGeoApi((200, "[]"))
    monkeypatch.setattr(geo_postal, "_GEO_API", api.url)
    await resolve_postal_code(city)

    # Act
    resolved = await resolve_postal_code(city)

    # Assert
    api.close()
    assert resolved is None
    assert api.requests == 1
