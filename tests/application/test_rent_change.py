"""A dismissed home whose rent changes comes back, and says what the hunter thought.

A lower rent is news (ADR-0009): the change breaks the recognition, so the home shows
again in the review, the web list and the alert. The earlier dismissal is found again
by the layout alone (commune, rooms, surface) — a lookup that adds a mention and never
hides anything.
"""

from dataclasses import replace
from decimal import Decimal

import pytest
from faker import Faker

from apartment_hunter.application.use_cases import (
    DismissHome,
    GetTopListings,
    NotifyNewListings,
    format_alert_line,
)
from apartment_hunter.domain.entities import Listing
from apartment_hunter.domain.value_objects import DismissalReason, Price, format_euros
from tests.fakes.builders import build_listing, build_search_filter
from tests.fakes.in_memory_geocoding import InMemoryGeocoding
from tests.fakes.in_memory_listing_repository import InMemoryListingRepository
from tests.fakes.in_memory_notifier import InMemoryNotifier
from tests.fakes.in_memory_rent_references import InMemoryRentReferences

GEOCODED = {"annecy": (45.8992, 6.1294)}
_fake = Faker("fr_FR")


@pytest.fixture
def repository() -> InMemoryListingRepository:
    return InMemoryListingRepository()


def _build_home(source: str, rent: int, rooms: int = 3, surface: float = 55.0) -> Listing:
    return build_listing(source=source, rooms=rooms, surface_m2=surface, price=rent)


def _pick_rent() -> int:
    return _fake.random_int(min=700, max=1400)


def _move_rent(listing: Listing, delta: int) -> Listing:
    return replace(listing, price=Price(amount=listing.price.amount + delta))


async def _find_shown(repository: InMemoryListingRepository) -> dict[str, Listing]:
    top = GetTopListings(repository, InMemoryGeocoding(GEOCODED), InMemoryRentReferences())
    groups = await top.execute(build_search_filter(max_dpe_rating=None, max_price=2000), 50)
    return {listing.id: listing for group in groups for listing in group.all_listings}


async def test_a_home_back_on_another_site_at_a_lower_rent_shows_with_the_mention(
    repository: InMemoryListingRepository,
) -> None:
    # Arrange
    dismissed = _build_home("pap", _pick_rent())
    await repository.save_many([dismissed])
    await DismissHome(repository).execute(dismissed, DismissalReason.TOO_EXPENSIVE)
    back = _move_rent(_build_home("orpi", int(dismissed.price.amount)), -50)

    # Act
    await repository.save_many([back])
    shown = await _find_shown(repository)

    # Assert — date, former total and reason, as the hunter wrote them off
    former = shown[back.id].former_dismissal
    assert former is not None
    assert former.listing_id == dismissed.id
    assert former.format_mention() == (
        f"écarté le {former.dismissed_at:%d/%m/%Y} à "
        f"{format_euros(dismissed.price.total)} (trop cher)"
    )


async def test_the_same_ad_with_a_new_rent_comes_back(
    repository: InMemoryListingRepository,
) -> None:
    # Arrange
    listing = _build_home("pap", _pick_rent())
    await repository.save_many([listing])
    await DismissHome(repository).execute(listing, DismissalReason.TOO_EXPENSIVE)

    # Act — the site lowers the rent on the very same URL
    await repository.save_many([_move_rent(listing, -_fake.random_int(min=10, max=100))])
    shown = await _find_shown(repository)

    # Assert
    assert shown[listing.id].former_dismissal is not None


async def test_the_layout_lookup_never_hides_a_home(
    repository: InMemoryListingRepository,
) -> None:
    # Arrange — homes of the dismissed layout, at every other rent, on every source
    dismissed = _build_home("pap", _pick_rent())
    await repository.save_many([dismissed])
    await DismissHome(repository).execute(dismissed, DismissalReason.ASPECT)
    rents = {int(dismissed.price.amount) + d for d in (-200, -1, 1, 300)}
    others = [_build_home(source, rent) for rent in rents for source in ("pap", "orpi")]

    # Act
    await repository.save_many(others)
    shown = await _find_shown(repository)

    # Assert
    assert {o.id for o in others} <= shown.keys()
    assert dismissed.id not in shown


async def test_an_identical_lot_of_the_same_site_gets_no_mention(
    repository: InMemoryListingRepository,
) -> None:
    # Arrange — a residence's next lot: same layout, same rent, one source
    rent = _pick_rent()
    dismissed = _build_home("pap", rent)
    next_lot = _build_home("pap", rent)
    await repository.save_many([dismissed, next_lot])
    await DismissHome(repository).execute(dismissed, DismissalReason.FLOOR)

    # Act
    shown = await _find_shown(repository)

    # Assert
    assert shown[next_lot.id].former_dismissal is None


async def test_a_home_without_rooms_nor_surface_never_gets_the_mention(
    repository: InMemoryListingRepository,
) -> None:
    # Arrange — recognised by its URL only, so no layout to find it again by
    rent = _pick_rent()
    dismissed = build_listing(source="pap", rooms=None, surface_m2=None, price=rent)
    await repository.save_many([dismissed])
    await DismissHome(repository).execute(dismissed, DismissalReason.ASPECT)
    lookalike = build_listing(source="orpi", rooms=None, surface_m2=None, price=rent - 50)

    # Act
    await repository.save_many([lookalike])
    shown = await _find_shown(repository)

    # Assert
    assert shown[lookalike.id].former_dismissal is None


async def test_the_alert_carries_the_mention(repository: InMemoryListingRepository) -> None:
    # Arrange
    dismissed = _build_home("pap", _pick_rent())
    await repository.save_many([dismissed])
    await DismissHome(repository).execute(dismissed, DismissalReason.TOO_EXPENSIVE)
    back = _move_rent(_build_home("orpi", int(dismissed.price.amount)), -50)
    await repository.save_many([back])
    notifier = InMemoryNotifier()
    notify = NotifyNewListings(
        repository, [notifier], InMemoryGeocoding(GEOCODED), InMemoryRentReferences()
    )

    # Act
    await notify.execute(build_search_filter(max_dpe_rating=None, max_price=2000))

    # Assert
    alerted = notifier.calls[0][0]
    assert [listing.id for listing in alerted] == [back.id]
    assert "écarté le " in format_alert_line(alerted[0])
    assert format_euros(Decimal(dismissed.price.total)) in format_alert_line(alerted[0])
