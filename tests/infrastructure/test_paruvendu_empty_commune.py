"""An empty commune costs ParuVendu one redirect, never a department page.

A commune without listings 301s to the whole department page. Following it downloaded that
same page once per empty commune — 20 of the 30 communes within 20 km of Annecy
(2026-11-01) — and sent its out-of-radius cards to detail enrichment.
"""

import threading
from collections.abc import Iterator
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest
from faker import Faker

from apartment_hunter.domain.entities import SearchFilter
from apartment_hunter.infrastructure.crawlers.base_crawler import build_city_slug
from apartment_hunter.infrastructure.crawlers.geo_postal import seed_postal_code
from apartment_hunter.infrastructure.crawlers.paruvendu_crawler import ParuVenduCrawler

fake = Faker("fr_FR")
_SEARCH_PATH = "/immobilier/recherche/location/appartement"
_DEPARTMENT_PATH = f"{_SEARCH_PATH}/haute-savoie-74/"


def _build_card(commune: str) -> str:
    listing_id = fake.unique.random_int(1_000_000_000, 1_999_999_999)
    return f"""
    <div class="blocAnnonce" data-id="{listing_id}">
      <h3><a href="/immobilier/location/appartement/{listing_id}A1KILHAP000">
        <span>Appartement
          {commune} (74)
        </span>
      </a></h3>
      <div>{fake.random_int(500, 1500)} € CC*</div>
    </div>
    """


class _ParuVenduSite:
    """paruvendu.fr's commune routing on localhost: a page per commune with listings,
    a 301 to the department page for the others. Records every path asked."""

    def __init__(self, pages: dict[str, str]) -> None:
        self.pages = pages
        self.paths: list[str] = []
        self._server = HTTPServer(("127.0.0.1", 0), self._build_handler())
        threading.Thread(target=self._server.serve_forever, daemon=True).start()
        self.url = f"http://127.0.0.1:{self._server.server_address[1]}"

    def _build_handler(self) -> type[BaseHTTPRequestHandler]:
        site = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:
                site.paths.append(self.path)
                if self.path in site.pages:
                    self._answer(HTTPStatus.OK, site.pages[self.path])
                elif self.path.startswith(_SEARCH_PATH):
                    self.send_response(HTTPStatus.MOVED_PERMANENTLY)
                    self.send_header("Location", _DEPARTMENT_PATH)
                    self.end_headers()
                else:
                    self._answer(HTTPStatus.NOT_FOUND, "")

            def _answer(self, status: HTTPStatus, body: str) -> None:
                self.send_response(status)
                self.end_headers()
                self.wfile.write(body.encode())

            def log_message(self, *args: object) -> None:
                pass

        return Handler

    def close(self) -> None:
        self._server.shutdown()
        self._server.server_close()


class _LocalParuVenduCrawler(ParuVenduCrawler):
    """ParuVendu itself, routed to the local site instead of paruvendu.fr."""

    RATE_LIMIT_SECONDS = 0.0

    def __init__(self, site_url: str) -> None:
        super().__init__()
        self._site_url = site_url

    async def _fetch_html(self, url: str) -> str | None:
        return await super()._fetch_html(url.replace(self.BASE_URL, self._site_url))


def _seed_commune() -> tuple[str, str]:
    commune = fake.unique.city()
    postal = f"74{fake.random_int(100, 999)}"
    seed_postal_code(commune, postal)
    return commune, f"{_SEARCH_PATH}/{build_city_slug(commune)}-{postal}/"


@pytest.fixture
def stocked_and_empty() -> Iterator[tuple[_ParuVenduSite, str, str]]:
    stocked, stocked_path = _seed_commune()
    empty, _ = _seed_commune()
    elsewhere = "".join(_build_card(fake.unique.city()) for _ in range(3))
    site = _ParuVenduSite(
        {
            "/robots.txt": "User-agent: *\nDisallow: /immobilier/geo/*\n",
            stocked_path: f"<main>{_build_card(stocked)}</main>",
            _DEPARTMENT_PATH: f"<main>{elsewhere}</main>",
        }
    )
    yield site, stocked, empty
    site.close()


async def test_an_empty_commune_never_downloads_the_department_page(
    stocked_and_empty: tuple[_ParuVenduSite, str, str],
) -> None:
    # Arrange
    site, stocked, empty = stocked_and_empty
    crawler = _LocalParuVenduCrawler(site.url)
    search_filter = SearchFilter(id=fake.uuid4(), name=fake.word(), cities=[stocked, empty])

    # Act
    listings = await crawler.fetch(search_filter)

    # Assert — the empty commune's redirect is read, not followed
    assert _DEPARTMENT_PATH not in site.paths
    assert [listing.location.city for listing in listings] == [stocked]
