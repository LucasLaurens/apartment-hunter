"""Dismissing a home hides it everywhere, and the purge does not bring it back.

What is dismissed is a *home* (ADR-0009): any listing that would group with a
dismissed one under the *Doublon* rule is hidden too, whichever source publishes it
and however many times the listing row is purged and crawled again.
"""

from dataclasses import replace
from datetime import datetime

import pytest
from faker import Faker

from apartment_hunter.application.use_cases import (
    DismissHome,
    GetTopListings,
    ListingNotFoundError,
    NotifyNewListings,
    RestoreHome,
    format_alert_line,
)
from apartment_hunter.domain.entities import Listing
from apartment_hunter.domain.value_objects import DismissalReason
from tests.fakes.builders import build_listing, build_search_filter
from tests.fakes.in_memory_geocoding import InMemoryGeocoding
from tests.fakes.in_memory_listing_repository import InMemoryListingRepository
from tests.fakes.in_memory_notifier import InMemoryNotifier
from tests.fakes.in_memory_rent_references import InMemoryRentReferences

GEOCODED = {"annecy": (45.8992, 6.1294)}
_fake = Faker("fr_FR")


def _build_home(source: str, rooms: int, surface: float, rent: int) -> Listing:
    return build_listing(source=source, rooms=rooms, surface_m2=surface, price=rent)


def _pick_home_figures() -> tuple[int, float, int]:
    return (
        _fake.random_int(min=1, max=5),
        float(_fake.random_int(min=20, max=110)),
        _fake.random_int(min=500, max=1400),
    )


@pytest.fixture
def repository() -> InMemoryListingRepository:
    return InMemoryListingRepository()


def _make_top(repository: InMemoryListingRepository) -> GetTopListings:
    return GetTopListings(repository, InMemoryGeocoding(GEOCODED), InMemoryRentReferences())


async def _list_shown_ids(repository: InMemoryListingRepository) -> set[str]:
    groups = await _make_top(repository).execute(build_search_filter(max_dpe_rating=None), limit=50)
    return {listing.id for group in groups for listing in group.all_listings}


async def test_a_dismissed_home_disappears_from_the_list(
    repository: InMemoryListingRepository,
) -> None:
    # Arrange
    dismissed = build_listing()
    kept = build_listing()
    await repository.save_many([dismissed, kept])

    # Act
    await DismissHome(repository).execute(dismissed, DismissalReason.TOO_EXPENSIVE)

    # Assert
    assert await _list_shown_ids(repository) == {kept.id}


async def test_a_dismissed_listing_stays_hidden_after_a_purge_and_a_recrawl(
    repository: InMemoryListingRepository,
) -> None:
    # Arrange
    listing = build_listing()
    await repository.save_many([listing])
    await DismissHome(repository).execute(listing, DismissalReason.ASPECT)
    await repository.delete_many([listing.id])

    # Act
    await repository.save_many([replace(listing)])

    # Assert
    assert await _list_shown_ids(repository) == set()


async def test_the_same_home_republished_by_another_source_stays_hidden(
    repository: InMemoryListingRepository,
) -> None:
    # Arrange
    rooms, surface, rent = _pick_home_figures()
    first = _build_home("pap", rooms, surface, rent)
    await repository.save_many([first])
    await DismissHome(repository).execute(first, DismissalReason.FLOOR)
    await repository.delete_many([first.id])

    # Act
    await repository.save_many([_build_home("foncia", rooms, surface, rent)])

    # Assert
    assert await _list_shown_ids(repository) == set()


async def test_a_duplicate_already_stored_on_another_source_is_hidden_with_it(
    repository: InMemoryListingRepository,
) -> None:
    # Arrange
    rooms, surface, rent = _pick_home_figures()
    first = _build_home("pap", rooms, surface, rent)
    mirror = _build_home("orpi", rooms, surface, rent)
    await repository.save_many([first, mirror])

    # Act
    await DismissHome(repository).execute(first, DismissalReason.CITY)

    # Assert
    assert await _list_shown_ids(repository) == set()


async def test_an_identical_lot_from_the_same_source_stays_visible(
    repository: InMemoryListingRepository,
) -> None:
    # Arrange — a residence publishes its identical units side by side
    rooms, surface, rent = _pick_home_figures()
    dismissed_lot = _build_home("foncia", rooms, surface, rent)
    other_lot = _build_home("foncia", rooms, surface, rent)
    await repository.save_many([dismissed_lot, other_lot])

    # Act
    await DismissHome(repository).execute(dismissed_lot, DismissalReason.FLOOR)

    # Assert
    assert await _list_shown_ids(repository) == {other_lot.id}


async def test_a_listing_without_rooms_or_surface_is_only_recognised_by_its_url(
    repository: InMemoryListingRepository,
) -> None:
    # Arrange
    rent = _fake.random_int(min=500, max=1400)
    dismissed = build_listing(source="pap", rooms=None, surface_m2=None, price=rent)
    lookalike = build_listing(source="orpi", rooms=None, surface_m2=None, price=rent)
    await repository.save_many([dismissed, lookalike])

    # Act
    await DismissHome(repository).execute(dismissed, DismissalReason.OTHER)

    # Assert
    assert await _list_shown_ids(repository) == {lookalike.id}


async def test_the_alert_skips_a_dismissed_home(repository: InMemoryListingRepository) -> None:
    # Arrange
    dismissed = build_listing()
    kept = build_listing()
    await repository.save_many([dismissed, kept])
    await DismissHome(repository).execute(dismissed, DismissalReason.DPE)
    notifier = InMemoryNotifier()
    notify = NotifyNewListings(
        repository, [notifier], InMemoryGeocoding(GEOCODED), InMemoryRentReferences()
    )

    # Act
    await notify.execute(build_search_filter(max_dpe_rating=None))

    # Assert
    assert [listing.id for listing in notifier.calls[0][0]] == [kept.id]


async def test_the_dismissal_keeps_a_frozen_snapshot_of_the_home(
    repository: InMemoryListingRepository,
) -> None:
    # Arrange
    charges = _fake.random_int(min=20, max=150)
    listing = build_listing(charges=charges, advertiser=_fake.company(), furnished=False)
    await repository.save_many([listing])
    moment = _fake.date_time_this_year()
    note = _fake.sentence()

    # Act
    await DismissHome(repository, read_now=lambda: moment).execute(
        listing, DismissalReason.OTHER, note
    )

    # Assert
    [dismissal] = await repository.list_dismissals()
    assert dismissal.listing_id == listing.id
    assert dismissal.reason is DismissalReason.OTHER
    assert dismissal.note == note
    assert dismissal.dismissed_at == moment
    assert dismissal.total_price == listing.price.total
    assert dismissal.surface_m2 == listing.surface_m2
    assert dismissal.floor_level == (listing.floor.level if listing.floor else None)
    assert dismissal.dpe_rating == listing.dpe_rating
    assert dismissal.advertiser == listing.advertiser
    assert dismissal.furnished is False


async def test_only_the_other_reason_carries_a_note(repository: InMemoryListingRepository) -> None:
    # Arrange
    listing = build_listing()

    # Act & Assert
    with pytest.raises(ValueError):
        await DismissHome(repository).execute(listing, DismissalReason.ASPECT, _fake.word())


async def test_dismissing_again_replaces_the_reason(repository: InMemoryListingRepository) -> None:
    # Arrange
    listing = build_listing()
    await repository.save_many([listing])
    dismiss = DismissHome(repository, read_now=datetime.now)
    await dismiss.execute(listing, DismissalReason.ASPECT)

    # Act
    await dismiss.execute(listing, DismissalReason.TOO_SMALL)

    # Assert
    assert [d.reason for d in await repository.list_dismissals()] == [DismissalReason.TOO_SMALL]


async def test_a_home_can_be_dismissed_by_the_id_the_page_holds(
    repository: InMemoryListingRepository,
) -> None:
    # Arrange
    dismissed = build_listing()
    await repository.save_many([dismissed])

    # Act
    await DismissHome(repository).execute_by_id(dismissed.id, DismissalReason.FLOOR)

    # Assert
    assert await _list_shown_ids(repository) == set()


async def test_an_unknown_id_is_refused(repository: InMemoryListingRepository) -> None:
    # Act & Assert
    with pytest.raises(ListingNotFoundError):
        await DismissHome(repository).execute_by_id(_fake.sha256(), DismissalReason.CITY)


async def test_restoring_brings_the_home_and_its_duplicates_back(
    repository: InMemoryListingRepository,
) -> None:
    # Arrange
    rooms, surface, rent = _pick_home_figures()
    pointed = _build_home("pap", rooms, surface, rent)
    duplicate = _build_home("orpi", rooms, surface, rent)
    await repository.save_many([pointed, duplicate])
    await DismissHome(repository).execute(pointed, DismissalReason.TOO_SMALL)

    # Act
    await RestoreHome(repository).execute(pointed.id)

    # Assert
    assert await _list_shown_ids(repository) == {pointed.id, duplicate.id}
    assert await repository.list_dismissals() == []


async def test_a_restored_home_says_so_in_the_list_and_the_alert(
    repository: InMemoryListingRepository,
) -> None:
    # Arrange
    rooms, surface, rent = _pick_home_figures()
    pointed = _build_home("pap", rooms, surface, rent)
    duplicate = _build_home("orpi", rooms, surface, rent)
    await repository.save_many([pointed, duplicate])
    await DismissHome(repository).execute(pointed, DismissalReason.ASPECT)
    restored_at = _fake.date_time_this_month()

    # Act
    await RestoreHome(repository, read_now=lambda: restored_at).execute(pointed.id)

    # Assert — the duplicate carries it too: it is the home that was judged once
    groups = await _make_top(repository).execute(build_search_filter(max_dpe_rating=None), 50)
    shown = [listing for group in groups for listing in group.all_listings]
    assert {listing.restored_at for listing in shown} == {restored_at}
    notifier = InMemoryNotifier()
    await NotifyNewListings(
        repository, [notifier], InMemoryGeocoding(GEOCODED), InMemoryRentReferences()
    ).execute(build_search_filter(max_dpe_rating=None, max_price=2000))
    alerted = notifier.calls[0][0]
    assert all(f"restauré le {restored_at:%d/%m/%Y}" in format_alert_line(a) for a in alerted)


async def test_dismissing_a_restored_home_again_replaces_the_reason_and_drops_the_mention(
    repository: InMemoryListingRepository,
) -> None:
    # Arrange
    listing = build_listing()
    await repository.save_many([listing])
    await DismissHome(repository).execute(listing, DismissalReason.TOO_SMALL)
    await RestoreHome(repository).execute(listing.id)

    # Act
    await DismissHome(repository).execute(listing, DismissalReason.DPE)

    # Assert
    assert [d.reason for d in await repository.list_dismissals()] == [DismissalReason.DPE]
    assert await repository.list_restored_dismissals() == []
