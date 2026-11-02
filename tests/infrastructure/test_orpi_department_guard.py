"""Orpi's commune page keeps only listings from the searched department.

A commune Orpi has no stock for is served padded with listings from elsewhere — on the
« Autour d'Annecy » filter, 38 of 45 listings, Limoges among them, each one costing a
detail-page request before the matcher threw it away (measured 2026-10-28).
"""

from faker import Faker

from apartment_hunter.domain.entities import Listing, SearchFilter
from apartment_hunter.infrastructure.crawlers.geo_postal import seed_postal_code
from apartment_hunter.infrastructure.crawlers.orpi_crawler import OrpiCrawler

fake = Faker("fr_FR")


def _build_card(town_slug: str, postal: str) -> str:
    href = f"/annonce-location-appartement-t2-{town_slug}-{postal}-{fake.uuid4()}/"
    rent = fake.random_int(500, 1500)
    return f"""
    <article class="c-estate-thumb">
      <a class="c-overlay__link" href="{href}"><b>Appartement 2 pièces 45 m²</b></a>
      <div class="c-estate-thumb__price-tag"><span class="u-h4">{rent} €</span></div>
      <p class="c-estate-thumb__infos__location">{town_slug}</p>
    </article>
    """


class ScriptedOrpiCrawler(OrpiCrawler):
    """Orpi without the network: every page answers with the same scripted HTML."""

    def __init__(self, html: str) -> None:
        super().__init__()
        self._html = html

    async def _fetch_html(self, url: str) -> str | None:
        return self._html


async def _fetch_commune(postal_in_zone: str, *postals: str) -> list[Listing]:
    city = fake.unique.city()
    seed_postal_code(city, postal_in_zone)
    cards = "".join(_build_card("ville", postal) for postal in postals)
    crawler = ScriptedOrpiCrawler(f"<main>{cards}</main>")
    search_filter = SearchFilter(id=fake.uuid4(), name=fake.word(), cities=[city])
    return await crawler._fetch_city(city, search_filter)


async def test_listings_from_another_department_are_dropped() -> None:
    # Arrange
    in_zone = f"74{fake.random_int(100, 999)}"
    elsewhere = f"87{fake.random_int(100, 999)}"

    # Act
    listings = await _fetch_commune(in_zone, in_zone, elsewhere)

    # Assert
    assert [listing.location.postal_code for listing in listings] == [in_zone]


async def test_neighbouring_communes_of_the_department_are_kept() -> None:
    # Arrange — the radius is the matcher's call, not the crawler's
    in_zone = f"74{fake.random_int(100, 999)}"
    neighbour = f"74{fake.random_int(100, 999)}"

    # Act
    listings = await _fetch_commune(in_zone, in_zone, neighbour)

    # Assert
    assert len(listings) == 2
