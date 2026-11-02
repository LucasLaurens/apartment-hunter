"""The storage boundary is where third-party data stops being dangerous."""

import json
from dataclasses import replace
from datetime import datetime
from pathlib import Path

from faker import Faker

from apartment_hunter.domain.entities import (
    MAX_MAX_RESULTS,
    MIN_INTERVAL_MINUTES,
    MIN_RADIUS_KM,
)
from apartment_hunter.domain.services import MAX_DESCRIPTION_CHARS
from apartment_hunter.infrastructure.crawlers.base_crawler import build_listing_id
from apartment_hunter.infrastructure.storage.sqlite_repository import SqliteRepository
from tests.fakes.builders import build_listing

_fake = Faker("fr_FR")


async def _open_repository(tmp_path: Path) -> SqliteRepository:
    repository = SqliteRepository(str(tmp_path / "hunter.db"))
    await repository.connect()
    return repository


async def test_drops_a_listing_whose_link_is_not_http(tmp_path: Path) -> None:
    # Arrange — a site is free to print href="javascript:…"
    repository = await _open_repository(tmp_path)
    hostile_url = "javascript:alert(document.domain)"
    hostile = replace(build_listing(), id=build_listing_id(hostile_url), url=hostile_url)
    legit = build_listing()

    # Act
    saved = await repository.save_many([hostile, legit])

    # Assert
    assert saved == 1
    assert [listing.id for listing in await repository.list_all()] == [legit.id]
    await repository.close()


async def test_strips_null_bytes_from_scraped_text(tmp_path: Path) -> None:
    # Arrange
    repository = await _open_repository(tmp_path)
    title = _fake.sentence()
    listing = replace(build_listing(), title=f"{title}\x00\x00")

    # Act
    await repository.save_many([listing])
    stored = (await repository.list_all())[0]

    # Assert
    assert stored.title == title
    await repository.close()


async def test_caps_a_giant_description(tmp_path: Path) -> None:
    # Arrange
    repository = await _open_repository(tmp_path)
    listing = replace(build_listing(), description="x" * (MAX_DESCRIPTION_CHARS + 500))

    # Act
    await repository.save_many([listing])
    stored = (await repository.list_all())[0]

    # Assert
    assert stored.description is not None
    assert len(stored.description) == MAX_DESCRIPTION_CHARS
    await repository.close()


async def test_drops_a_non_http_image_url(tmp_path: Path) -> None:
    # Arrange
    repository = await _open_repository(tmp_path)
    good_image = "https://cdn.example.fr/photo.jpg"
    listing = replace(build_listing(), images=(good_image, "javascript:alert(1)"))

    # Act
    await repository.save_many([listing])
    stored = (await repository.list_all())[0]

    # Assert
    assert stored.images == (good_image,)
    await repository.close()


async def test_clamps_a_stored_filter_written_before_the_bounds_existed(tmp_path: Path) -> None:
    # Arrange — a row that today's SearchFilter would refuse outright
    repository = await _open_repository(tmp_path)
    legacy_config = {
        "cities": ["Annecy"],
        "radius_km": 9_999.0,
        "refresh_interval_minutes": -5,
        "notification_interval_minutes": 0,
        "max_results": 10_000,
        "max_price": -100,
    }
    await repository._conn.execute(  # noqa: SLF001 — writing what an older version wrote
        "INSERT INTO filters (id, name, config, enabled, created_at) VALUES (?, ?, ?, 1, ?)",
        ("legacy01", "Legacy", json.dumps(legacy_config), datetime.now().isoformat()),
    )
    await repository._conn.commit()  # noqa: SLF001

    # Act — loading must not raise, and must not hand the loop a 1-second interval
    loaded = (await repository.load_filters())[0]

    # Assert
    assert loaded.refresh_interval_minutes == MIN_INTERVAL_MINUTES
    assert loaded.notification_interval_minutes == MIN_INTERVAL_MINUTES
    assert loaded.max_results == MAX_MAX_RESULTS
    assert loaded.radius_km <= 150.0
    assert loaded.radius_km >= MIN_RADIUS_KM
    assert loaded.max_price is None
    await repository.close()


async def test_drops_a_listing_whose_rent_could_not_be_read(tmp_path: Path) -> None:
    # Arrange — a failed price parse reads 0 €, which passed every budget (W5)
    repository = await _open_repository(tmp_path)
    priced = build_listing(price=float(_fake.random_int(500, 2000)))
    unpriced = build_listing(price=0.0)

    # Act
    saved = await repository.save_many([priced, unpriced])

    # Assert
    assert saved == 1
    assert [listing.id for listing in await repository.list_all()] == [priced.id]
    await repository.close()
