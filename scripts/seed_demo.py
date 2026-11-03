"""Fill a demo database with fictitious homes in and around Paris, to try the app without crawling.

    uv run python scripts/seed_demo.py demo.db
    DATABASE_URL=demo.db uv run hunt serve

Every listing is invented (Faker, a fixed seed): no listing site is contacted and no
third-party content is stored, which is also what the README's screenshots are taken
from. Links point to example.org. Communes and source names are real, so the map, the
market position and the source pills behave as they do with a crawl (the map and the
position still ask the public geocoding API and the Carte des loyers).
"""

import asyncio
import sys
from collections import OrderedDict
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Final

from faker import Faker

from apartment_hunter.domain.entities import Listing, SearchFilter
from apartment_hunter.domain.services import build_dismissal, build_opening
from apartment_hunter.domain.value_objects import (
    DismissalReason,
    DpeRating,
    Floor,
    Location,
    Price,
    PublicationSource,
)
from apartment_hunter.infrastructure.crawlers.base_crawler import build_listing_id
from apartment_hunter.infrastructure.storage.sqlite_repository import SqliteRepository

_SEED: Final = 75000
_LISTING_COUNT: Final = 36
_FILTER_ID: Final = "demo"
# Paris and the inner suburbs, Paris most often. Like most sources, a demo listing names
# its commune only: the map pins it at the commune, one pin per commune. Rent references
# load for the filter cities' departments only, hence one filter city per department.
_FILTER_CITIES: Final = ["Paris", "Boulogne-Billancourt", "Pantin", "Vincennes"]
_SUBURBS: Final = (
    "Boulogne-Billancourt",
    "Issy-les-Moulineaux",
    "Levallois-Perret",
    "Montreuil",
    "Vincennes",
    "Saint-Mandé",
    "Ivry-sur-Seine",
)
_PARIS_SHARE: Final = 0.6
# A Paris home carries its arrondissement's postal code: the rent map has no row for
# Paris as a whole, only one per arrondissement.
_PARIS_ARRONDISSEMENTS: Final = (3, 5, 9, 10, 11, 11, 12, 13, 14, 15, 15, 17, 18, 19, 20)
# €/m² per month, drawn per listing: Paris above its suburbs, as on the Carte des loyers.
_PARIS_RENT_PER_M2: Final = (27, 38)
_SUBURB_RENT_PER_M2: Final = (20, 29)
_SOURCES: Final = ("orpi", "foncia", "century21", "laforet", "paruvendu", "squarehabitat")
# Each network's ads carry one of its own branches; ParuVendu is mostly private owners.
_AGENCIES: Final = {
    "orpi": "Orpi Paris Bastille",
    "foncia": "Foncia Paris Nation",
    "century21": "Century 21 Saint-Ambroise",
    "laforet": "Laforêt Paris 15",
    "squarehabitat": "Square Habitat Paris Est",
}
# Faker draws a dict's keys weighted by their values: mostly C and D, as in the area.
_DPE_WEIGHTS: Final = OrderedDict(
    [("B", 0.1), ("C", 0.3), ("D", 0.3), ("E", 0.2), ("F", 0.05), ("G", 0.05)]
)


def build_demo_listings(fake: Faker, now: datetime) -> list[Listing]:
    """Fictitious but plausible homes: rents by size and place, scattered over the radius."""
    listings: list[Listing] = []
    for index in range(_LISTING_COUNT):
        in_paris = fake.random.random() < _PARIS_SHARE
        city = "Paris" if in_paris else fake.random_element(_SUBURBS)
        postal_code = f"750{fake.random_element(_PARIS_ARRONDISSEMENTS):02d}" if in_paris else None
        rent_low, rent_high = _PARIS_RENT_PER_M2 if in_paris else _SUBURB_RENT_PER_M2
        rooms = fake.random_element((1, 1, 2, 2, 2, 3, 3, 4))
        surface = fake.random_int(14, 26) + (rooms - 1) * fake.random_int(12, 19)
        rent = Decimal(round(surface * fake.random_int(rent_low, rent_high) / 10) * 10)
        charges = Decimal(fake.random_element((0, 40, 60, 80, 110, 140)))
        source = fake.random_element(_SOURCES)
        url = f"https://example.org/annonce/{source}/{fake.uuid4()}"
        published = now - timedelta(hours=fake.random_int(1, 24 * 12))
        listings.append(
            Listing(
                id=build_listing_id(url),
                url=url,
                title=f"Appartement {rooms} pièce{'s' if rooms > 1 else ''} {surface} m²",
                source=source,
                location=Location(city=city, postal_code=postal_code),
                price=Price(amount=rent, charges=charges or None),
                published_at=published,
                published_at_source=(
                    PublicationSource.SITE if index % 3 else PublicationSource.FIRST_SEEN
                ),
                surface_m2=float(surface),
                rooms=rooms,
                floor=Floor(level=fake.random_int(0, 5), is_top=index % 7 == 0),
                dpe_rating=DpeRating.from_string(fake.random_element(_DPE_WEIGHTS)),
                ges_rating=DpeRating.from_string(fake.random_element(_DPE_WEIGHTS)),
                furnished=index % 4 == 0,
                charges_included=True if charges else None,
                advertiser=_AGENCIES.get(source),
                description=fake.paragraph(nb_sentences=3),
                images=tuple(f"https://example.org/photo/{n}.jpg" for n in range(index % 6)),
                fetched_at=published,
                last_seen_at=now,
            )
        )
    return listings


async def seed(path: str) -> None:
    fake = Faker("fr_FR")
    Faker.seed(_SEED)
    now = datetime.now()
    repository = SqliteRepository(path)
    await repository.connect()
    try:
        await _fill(repository, fake, now)
    finally:
        # An open connection keeps its thread alive: an error would hang instead of exit.
        await repository.close()
    print(f"{_LISTING_COUNT} fictitious listings in {path}, filter « Paris et proche banlieue ».")


async def _fill(repository: SqliteRepository, fake: Faker, now: datetime) -> None:
    await repository.save_filter(
        SearchFilter(
            id=_FILTER_ID,
            name="Paris et proche banlieue",
            cities=_FILTER_CITIES,
            radius_km=10,
            max_price=2000,
            min_surface_m2=20,
        )
    )
    listings = build_demo_listings(fake, now)
    await repository.save_many(listings)
    await repository.save_source_successes(_FILTER_ID, frozenset(_SOURCES), now)
    # A few homes already opened, one dismissed: the « Nouveau » badge and the dismissed
    # page then show their real states.
    for listing in listings[:8]:
        await repository.save_opening(build_opening(listing, now - timedelta(days=1)))
    await repository.save_dismissal(
        build_dismissal(listings[-1], DismissalReason.TOO_EXPENSIVE, now - timedelta(days=2))
    )


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("usage: uv run python scripts/seed_demo.py <demo.db>")
    asyncio.run(seed(sys.argv[1]))
