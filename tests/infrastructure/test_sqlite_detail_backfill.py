"""A stored listing picks up what its detail page holds — DPE, GES, storey — once the
crawler can finally read it."""

from dataclasses import replace
from pathlib import Path

from apartment_hunter.domain.value_objects import DpeRating, Floor
from apartment_hunter.infrastructure.storage.sqlite_repository import SqliteRepository
from tests.fakes.builders import build_listing


async def _open_repository(tmp_path: Path) -> SqliteRepository:
    repository = SqliteRepository(str(tmp_path / "hunter.db"))
    await repository.connect()
    return repository


async def test_fills_the_energy_scales_of_an_already_stored_row(tmp_path: Path) -> None:
    # Arrange — first crawl read no scale (detail page blocked)
    repository = await _open_repository(tmp_path)
    listing = replace(build_listing(dpe=None), ges_rating=None)
    await repository.save_many([listing])

    # Act — a later crawl reads both letters
    await repository.save_many([replace(listing, dpe_rating=DpeRating.E, ges_rating=DpeRating.D)])
    stored = (await repository.list_all())[0]

    # Assert — without this the DPE filter would keep letting the row through
    assert stored.dpe_rating is DpeRating.E
    assert stored.ges_rating is DpeRating.D
    await repository.close()


async def test_overwrites_a_letter_a_broken_parser_had_stored(tmp_path: Path) -> None:
    # Arrange
    repository = await _open_repository(tmp_path)
    listing = replace(build_listing(dpe="A"), ges_rating=DpeRating.A)
    await repository.save_many([listing])

    # Act
    await repository.save_many([replace(listing, dpe_rating=DpeRating.F, ges_rating=DpeRating.E)])
    stored = (await repository.list_all())[0]

    # Assert
    assert stored.dpe_rating is DpeRating.F
    assert stored.ges_rating is DpeRating.E
    await repository.close()


async def test_keeps_the_stored_letter_when_a_crawl_reads_nothing(tmp_path: Path) -> None:
    # Arrange
    repository = await _open_repository(tmp_path)
    listing = replace(build_listing(dpe="C"), ges_rating=DpeRating.B)
    await repository.save_many([listing])

    # Act — the detail page is unreadable this time, only the GES survives
    await repository.save_many([replace(listing, dpe_rating=None)])
    stored = (await repository.list_all())[0]

    # Assert
    assert stored.dpe_rating is DpeRating.C
    assert stored.ges_rating is DpeRating.B
    await repository.close()


async def test_fills_the_storey_of_an_already_stored_row(tmp_path: Path) -> None:
    # Arrange — Laforêt cards carry no storey; only the detail page states it
    repository = await _open_repository(tmp_path)
    listing = replace(build_listing(), floor=None)
    await repository.save_many([listing])

    # Act
    await repository.save_many([replace(listing, floor=Floor.from_int(4))])
    stored = (await repository.list_all())[0]

    # Assert — without this, `exclude_first_floor` would stay a no-op on that source
    assert stored.floor == Floor.from_int(4)
    await repository.close()


async def test_fills_the_furnishing_answer_of_an_already_stored_row(tmp_path: Path) -> None:
    # Arrange — cards rarely state it; the detail page's criteria table does
    repository = await _open_repository(tmp_path)
    listing = replace(build_listing(), furnished=None)
    await repository.save_many([listing])

    # Act
    await repository.save_many([replace(listing, furnished=True)])
    stored = (await repository.list_all())[0]

    # Assert — without this, an "unfurnished" filter stays a no-op on stored rows
    assert stored.furnished is True
    await repository.close()


async def test_overwrites_a_furnishing_answer_a_card_had_got_wrong(tmp_path: Path) -> None:
    # Arrange — the headline read "meublé", so the first crawl stored True
    repository = await _open_repository(tmp_path)
    listing = replace(build_listing(), furnished=True)
    await repository.save_many([listing])

    # Act — the detail page answers "Meublé : non"
    await repository.save_many([replace(listing, furnished=False)])
    stored = (await repository.list_all())[0]

    # Assert
    assert stored.furnished is False
    await repository.close()


async def test_keeps_the_stored_furnishing_when_a_crawl_reads_none(tmp_path: Path) -> None:
    # Arrange
    repository = await _open_repository(tmp_path)
    listing = replace(build_listing(), furnished=False)
    await repository.save_many([listing])

    # Act — this crawl couldn't read the criteria table
    await repository.save_many([replace(listing, furnished=None)])
    stored = (await repository.list_all())[0]

    # Assert
    assert stored.furnished is False
    await repository.close()


async def test_keeps_the_stored_storey_when_a_crawl_reads_none(tmp_path: Path) -> None:
    # Arrange
    repository = await _open_repository(tmp_path)
    listing = replace(build_listing(floor_level=3), dpe_rating=None)
    await repository.save_many([listing])

    # Act — the detail page is unreadable this time
    await repository.save_many([replace(listing, floor=Floor.unknown())])
    stored = (await repository.list_all())[0]

    # Assert
    assert stored.floor == Floor.from_int(3)
    await repository.close()
