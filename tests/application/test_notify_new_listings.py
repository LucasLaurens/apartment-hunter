from decimal import Decimal

import pytest
from faker import Faker

from apartment_hunter.application.use_cases import NotifyNewListings, format_alert_line
from apartment_hunter.domain.value_objects import RentReference, RentSegment
from tests.fakes.builders import build_listing, build_search_filter
from tests.fakes.in_memory_geocoding import InMemoryGeocoding
from tests.fakes.in_memory_listing_repository import InMemoryListingRepository
from tests.fakes.in_memory_notifier import InMemoryNotifier
from tests.fakes.in_memory_rent_references import InMemoryRentReferences

GEOCODED = {"annecy": (45.8992, 6.1294)}


@pytest.fixture
def repository() -> InMemoryListingRepository:
    return InMemoryListingRepository()


@pytest.fixture
def notifier() -> InMemoryNotifier:
    return InMemoryNotifier()


async def test_notifies_new_matching_apartments(
    repository: InMemoryListingRepository, notifier: InMemoryNotifier
) -> None:
    # Arrange
    search_filter = build_search_filter(max_price=1200)
    listing = build_listing(price=900)
    await repository.save_many([listing])
    use_case = NotifyNewListings(
        repository=repository,
        notifiers=[notifier],
        geocoding=InMemoryGeocoding(GEOCODED),
        rent_references=InMemoryRentReferences(),
    )

    # Act
    notified = await use_case.execute(search_filter)

    # Assert
    assert notified == 1
    assert notifier.count_notified() == 1


async def test_does_not_notify_already_notified(
    repository: InMemoryListingRepository, notifier: InMemoryNotifier
) -> None:
    # Arrange
    search_filter = build_search_filter(max_price=1200)
    listing = build_listing(price=900)
    await repository.save_many([listing])
    use_case = NotifyNewListings(
        repository=repository,
        notifiers=[notifier],
        geocoding=InMemoryGeocoding(GEOCODED),
        rent_references=InMemoryRentReferences(),
    )

    # Act — run twice
    await use_case.execute(search_filter)
    notified_second = await use_case.execute(search_filter)

    # Assert
    assert notified_second == 0
    assert len(notifier.calls) == 1


async def test_does_not_notify_non_matching_apartments(
    repository: InMemoryListingRepository, notifier: InMemoryNotifier
) -> None:
    # Arrange
    search_filter = build_search_filter(max_price=800)
    expensive_apt = build_listing(price=1500)  # exceeds max_price
    await repository.save_many([expensive_apt])
    use_case = NotifyNewListings(
        repository=repository,
        notifiers=[notifier],
        geocoding=InMemoryGeocoding(GEOCODED),
        rent_references=InMemoryRentReferences(),
    )

    # Act
    notified = await use_case.execute(search_filter)

    # Assert
    assert notified == 0
    assert notifier.calls == []


async def test_the_alert_line_carries_the_position_or_says_why_there_is_none(
    repository: InMemoryListingRepository, notifier: InMemoryNotifier
) -> None:
    # Arrange — 880 € for 50 m² in Annecy against a 20 €/m² T1-T2 reference
    reference = RentReference(
        commune="Annecy",
        segment=RentSegment.ONE_TWO_ROOMS,
        per_m2=Decimal("20"),
        lower_per_m2=Decimal("15"),
        upper_per_m2=Decimal("28"),
        observed_in_commune=Faker().random_int(100, 5000),
        r2_adjusted=0.8,
        vintage=2025,
    )
    comparable = build_listing(price=880, surface_m2=50.0, rooms=2, charges_included=True)
    furnished = build_listing(price=900, furnished=True)
    await repository.save_many([comparable, furnished])
    use_case = NotifyNewListings(
        repository=repository,
        notifiers=[notifier],
        geocoding=InMemoryGeocoding(GEOCODED),
        rent_references=InMemoryRentReferences({"Annecy": {RentSegment.ONE_TWO_ROOMS: reference}}),
    )

    # Act
    await use_case.execute(build_search_filter(max_price=1200))

    # Assert
    lines = {listing.id: format_alert_line(listing) for listing in notifier.calls[0][0]}
    assert lines[comparable.id].endswith(" · −12 % vs réf.")
    assert lines[furnished.id].endswith(" · pas de repère (meublé)")
