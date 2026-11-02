"""The Carte des loyers adapter, read from a filled cache: never the network (ticket 05)."""

import shutil
from decimal import Decimal
from pathlib import Path

from faker import Faker

from apartment_hunter.domain.value_objects import (
    MarketPosition,
    NoMarketPosition,
    NoPositionReason,
    RentSegment,
)
from apartment_hunter.infrastructure.rent_map import RENT_MAP_VINTAGE, CarteDesLoyers
from tests.fakes.builders import build_listing, build_search_filter

_fake = Faker()
_FIXTURES = Path(__file__).parent.parent / "fixtures" / "rent_map"
# What geo.api.gouv.fr answers for the filter's department: Seynod is a delegated
# commune of Annecy, so it carries Annecy's code; the 05 code keeps its leading zero.
_COMMUNE_CODES = {"Annecy": "74010", "Seynod": "74010", "Lœuilley-sur-Buëch": "05066"}


async def _find_codes(_base_cities: list[str]) -> dict[str, str]:
    return dict(_COMMUNE_CODES)


def _fill_cache(cache_dir: Path) -> None:
    shutil.copytree(_FIXTURES, cache_dir / str(RENT_MAP_VINTAGE))


async def test_a_listing_reads_its_reference_from_the_cached_files(tmp_path: Path) -> None:
    # Arrange
    _fill_cache(tmp_path)
    rent_map = CarteDesLoyers(tmp_path, find_codes=_find_codes)
    listing = build_listing(
        city="Annecy", price=900.0, surface_m2=45.0, rooms=2, charges_included=True
    )

    # Act
    book = await rent_map.find_references([build_search_filter()])

    # Assert
    position = book.assess(listing)
    assert isinstance(position, MarketPosition)
    assert position.reference.segment is RentSegment.ONE_TWO_ROOMS
    assert position.reference.per_m2 == Decimal("20.92")
    assert (position.reference.lower_per_m2, position.reference.upper_per_m2) == (
        Decimal("15.69"),
        Decimal("27.89"),
    )
    assert position.reference.vintage == RENT_MAP_VINTAGE


async def test_a_former_commune_gets_the_reference_of_the_one_it_merged_into(
    tmp_path: Path,
) -> None:
    # Arrange
    _fill_cache(tmp_path)
    rent_map = CarteDesLoyers(tmp_path, find_codes=_find_codes)
    listing = build_listing(
        city="Seynod", price=1300.0, surface_m2=70.0, rooms=3, charges_included=True
    )

    # Act
    position = (await rent_map.find_references([build_search_filter()])).assess(listing)

    # Assert
    assert isinstance(position, MarketPosition)
    assert position.reference.commune == "Annecy"
    assert position.reference.per_m2 == Decimal("17.97")


async def test_the_files_are_read_as_windows_1252_with_leading_zero_codes(tmp_path: Path) -> None:
    # Arrange — « Œ » and « ë » are single cp1252 bytes, the code keeps its zero
    _fill_cache(tmp_path)
    rent_map = CarteDesLoyers(tmp_path, find_codes=_find_codes)
    listing = build_listing(
        city="Lœuilley-sur-Buëch",
        price=500.0,
        surface_m2=float(_fake.random_int(35, 45)),
        rooms=2,
        charges_included=True,
    )

    # Act
    position = (await rent_map.find_references([build_search_filter()])).assess(listing)

    # Assert
    assert isinstance(position, MarketPosition)
    assert position.reference.commune == "Lœuilley-sur-Buëch"
    assert position.reference.is_weak


async def test_an_unreadable_file_answers_no_position_instead_of_failing(tmp_path: Path) -> None:
    # Arrange — a file that is not the Carte des loyers sits in the cache
    vintage_dir = tmp_path / str(RENT_MAP_VINTAGE)
    vintage_dir.mkdir()
    for segment in RentSegment:
        (vintage_dir / f"pred-{segment.value}-mef-dhup.csv").write_text(_fake.text())
    rent_map = CarteDesLoyers(tmp_path, find_codes=_find_codes)
    listing = build_listing(
        city="Annecy", price=900.0, surface_m2=45.0, rooms=2, charges_included=True
    )

    # Act
    position = (await rent_map.find_references([build_search_filter()])).assess(listing)

    # Assert
    assert position == NoMarketPosition(NoPositionReason.MAP_UNAVAILABLE)


async def test_deleting_the_downloads_empties_the_cache(tmp_path: Path) -> None:
    # Arrange
    _fill_cache(tmp_path)
    rent_map = CarteDesLoyers(tmp_path, find_codes=_find_codes)

    # Act
    rent_map.delete_downloads()

    # Assert
    assert not (tmp_path / str(RENT_MAP_VINTAGE)).exists()
