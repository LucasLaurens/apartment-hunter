"""A re-crawl of the same ad brings its current rent and commune: the stored ones used to
be frozen at the first reading, so a lowered rent reached no reader (ADR-0009), and a
listing filed under the searched commune kept it after its card's own was read."""

from dataclasses import replace
from decimal import Decimal
from pathlib import Path

from faker import Faker

from apartment_hunter.domain.value_objects import Location, Price
from apartment_hunter.infrastructure.storage.sqlite_repository import SqliteRepository
from tests.fakes.builders import build_listing

_fake = Faker("fr_FR")


async def _open_repository(tmp_path: Path) -> SqliteRepository:
    repository = SqliteRepository(str(tmp_path / "hunter.db"))
    await repository.connect()
    return repository


async def test_a_lowered_rent_reaches_the_stored_row(tmp_path: Path) -> None:
    # Arrange
    repository = await _open_repository(tmp_path)
    listing = build_listing(price=float(_fake.random_int(800, 1400)))
    await repository.save_many([listing])
    lowered = Decimal(_fake.random_int(500, 790))

    # Act
    await repository.save_many([replace(listing, price=Price(lowered, listing.price.charges))])
    stored = await repository.find_listing(listing.id)

    # Assert
    assert stored is not None
    assert stored.price.amount == lowered
    await repository.close()


async def test_charges_read_as_nothing_keep_the_stored_ones(tmp_path: Path) -> None:
    # Arrange — the card printed charges once, a later crawl could not read them
    repository = await _open_repository(tmp_path)
    charges = float(_fake.random_int(30, 150))
    listing = build_listing(charges=charges)
    await repository.save_many([listing])

    # Act
    await repository.save_many([replace(listing, price=Price(listing.price.amount))])
    stored = await repository.find_listing(listing.id)

    # Assert
    assert stored is not None
    assert stored.price.charges == Decimal(str(charges))
    await repository.close()


async def test_a_corrected_commune_reaches_the_stored_row(tmp_path: Path) -> None:
    # Arrange — stored under the commune that was searched, before the card's own was read
    repository = await _open_repository(tmp_path)
    searched, named = _fake.unique.city(), _fake.unique.city()
    listing = build_listing(city=searched)
    await repository.save_many([listing])

    # Act
    await repository.save_many(
        [replace(listing, title=f"Appartement {named}", location=Location(city=named))]
    )
    stored = await repository.find_listing(listing.id)
    await repository.close()

    # Assert
    assert stored is not None
    assert stored.location.city == named
    assert stored.title == f"Appartement {named}"
