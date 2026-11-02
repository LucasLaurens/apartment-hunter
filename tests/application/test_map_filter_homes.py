"""What the map draws for a filter (ticket 14): one pin per commune, from our geocoding."""

from dataclasses import replace

from faker import Faker

from apartment_hunter.application.use_cases import GetTopListings, MapFilterHomes
from apartment_hunter.domain.value_objects import Location
from tests.fakes.builders import build_listing, build_search_filter
from tests.fakes.in_memory_geocoding import InMemoryGeocoding
from tests.fakes.in_memory_listing_repository import InMemoryListingRepository
from tests.fakes.in_memory_rent_references import InMemoryRentReferences

_fake = Faker("fr_FR")
GEOCODED = {"annecy": (45.8992, 6.1294), "poisy": (45.9214, 6.0636)}


def _build_use_case(repository: InMemoryListingRepository) -> MapFilterHomes:
    geocoding = InMemoryGeocoding(GEOCODED)
    return MapFilterHomes(
        GetTopListings(repository, geocoding, InMemoryRentReferences()), geocoding
    )


def _place_in(city: str) -> Location:
    return Location(city=city)  # no own coordinates: the pin is the commune's


async def test_homes_gather_on_their_commune() -> None:
    # Arrange
    repository = InMemoryListingRepository()
    in_poisy = [replace(build_listing(), location=_place_in("Poisy")) for _ in range(2)]
    in_annecy = replace(build_listing(), location=_place_in("Annecy"))
    await repository.save_many([*in_poisy, in_annecy])
    search_filter = build_search_filter(cities=["Annecy"], max_dpe_rating=None)

    # Act
    filter_map = await _build_use_case(repository).execute(search_filter)

    # Assert
    counts = {pin.name: len(pin.homes) for pin in filter_map.pins}
    assert counts == {"Poisy": 2, "Annecy": 1}
    assert {pin.name: pin.position for pin in filter_map.pins}["Poisy"] == GEOCODED["poisy"]
    assert filter_map.centre == GEOCODED["annecy"]
    assert filter_map.unplaced == 0


async def test_a_home_the_geocoder_cannot_place_is_counted_not_dropped() -> None:
    # Arrange — kept by the matcher on an exact city match, but no coordinates anywhere
    repository = InMemoryListingRepository()
    city = _fake.city()
    await repository.save_many([replace(build_listing(), location=_place_in(city))])
    search_filter = build_search_filter(cities=[city], max_dpe_rating=None)

    # Act
    filter_map = await _build_use_case(repository).execute(search_filter)

    # Assert
    assert filter_map.pins == []
    assert filter_map.unplaced == 1
    assert filter_map.centre is None


async def test_the_area_lists_every_commune_in_radius() -> None:
    # Arrange
    search_filter = build_search_filter(cities=["Annecy"])

    # Act
    area = await _build_use_case(InMemoryListingRepository()).find_area(search_filter)

    # Assert
    assert area.centre == GEOCODED["annecy"]
    assert dict(area.communes) == GEOCODED
    assert area.radius_km == search_filter.radius_km
