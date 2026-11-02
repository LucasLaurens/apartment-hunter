"""The local server answers its own page only: no rebound host, no cross-site write."""

import httpx
import pytest
from faker import Faker

from apartment_hunter.presentation.web.app import app
from apartment_hunter.presentation.web.request_guard import is_cross_site_write

_fake = Faker()
_HOST = "127.0.0.1:8001"


def _make_client(host: str) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url=f"http://{host}")


async def test_a_rebound_domain_is_refused() -> None:
    # Arrange — a visited page pointed its own domain at 127.0.0.1
    async with _make_client(_fake.domain_name()) as client:
        # Act
        response = await client.get("/api/filters")

    # Assert
    assert response.status_code == httpx.codes.BAD_REQUEST


async def test_a_form_posted_from_another_site_is_refused() -> None:
    # Arrange
    async with _make_client(_HOST) as client:
        # Act — no JSON body, so nothing else would have stopped it
        response = await client.post(
            f"/api/listings/{_fake.sha256()[:16]}/opened",
            headers={"Origin": f"https://{_fake.domain_name()}"},
        )

    # Assert
    assert response.status_code == httpx.codes.FORBIDDEN


@pytest.mark.parametrize(
    ("origin", "fetch_site", "refused"),
    [
        (f"http://{_HOST}", None, False),
        (None, "same-origin", False),
        (None, "none", False),
        (None, None, False),
        ("https://evil.example", None, True),
        (None, "cross-site", True),
        (None, "same-site", True),
    ],
)
def test_a_write_is_judged_by_where_the_browser_says_it_comes_from(
    origin: str | None, fetch_site: str | None, refused: bool
) -> None:
    # Act & Assert
    assert is_cross_site_write("POST", _HOST, origin, fetch_site) is refused


def test_a_read_is_never_refused() -> None:
    # Act & Assert
    assert not is_cross_site_write("GET", _HOST, "https://evil.example", "cross-site")
