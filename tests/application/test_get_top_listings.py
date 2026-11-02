"""Display order: newest parution by default, price/surface on demand."""

from dataclasses import replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from faker import Faker

from apartment_hunter.application.use_cases import GetTopListings
from apartment_hunter.domain.entities import Listing
from apartment_hunter.domain.services import (
    SOURCE_DOWN_HIDE_AFTER,
    STALE_AFTER_MIN,
    build_published_key,
)
from apartment_hunter.domain.value_objects import ListingSort, Price, RentReference, RentSegment
from tests.fakes.builders import build_listing, build_search_filter
from tests.fakes.in_memory_geocoding import InMemoryGeocoding
from tests.fakes.in_memory_listing_repository import InMemoryListingRepository
from tests.fakes.in_memory_rent_references import InMemoryRentReferences

_fake = Faker()
GEOCODED = {"annecy": (45.8992, 6.1294)}
_HOURS_FROM_LOCAL = 3  # gap between the local zone and the "foreign" one used below


def _compute_local_offset() -> timedelta:
    return datetime.now().astimezone().utcoffset() or timedelta()


def _build_foreign_zone() -> timezone:
    """A zone the runner is certainly not in — three hours behind its own offset."""
    return timezone(_compute_local_offset() - timedelta(hours=_HOURS_FROM_LOCAL))


@pytest.fixture
def use_case() -> tuple[GetTopListings, InMemoryListingRepository]:
    repository = InMemoryListingRepository()
    return GetTopListings(
        repository, InMemoryGeocoding(GEOCODED), InMemoryRentReferences()
    ), repository


async def test_orders_by_publication_date_descending_by_default(
    use_case: tuple[GetTopListings, InMemoryListingRepository],
) -> None:
    # Arrange
    get_top, repository = use_case
    oldest = build_listing(published_offset_minutes=600)
    newest = build_listing(published_offset_minutes=5)
    middle = build_listing(published_offset_minutes=120)
    await repository.save_many([oldest, newest, middle])

    # Act
    homes = await get_top.execute(build_search_filter(max_dpe_rating=None), limit=3)

    # Assert
    assert [home.primary.id for home in homes] == [newest.id, middle.id, oldest.id]


async def test_orders_by_total_price_ascending(
    use_case: tuple[GetTopListings, InMemoryListingRepository],
) -> None:
    # Arrange — charges count: the cheapest rent is not the cheapest total
    get_top, repository = use_case
    cheap_total = replace(build_listing(), price=Price(amount=Decimal("800")))
    with_charges = replace(
        build_listing(), price=Price(amount=Decimal("750"), charges=Decimal("120"))
    )
    await repository.save_many([with_charges, cheap_total])

    # Act
    homes = await get_top.execute(
        build_search_filter(max_dpe_rating=None), limit=2, sort=ListingSort.PRICE_ASC
    )

    # Assert
    assert [home.primary.id for home in homes] == [cheap_total.id, with_charges.id]


async def test_orders_by_surface_descending_and_sinks_unknown_surface(
    use_case: tuple[GetTopListings, InMemoryListingRepository],
) -> None:
    # Arrange
    get_top, repository = use_case
    biggest = build_listing(surface_m2=90.0)
    smallest = build_listing(surface_m2=30.0)
    unknown = replace(build_listing(), surface_m2=None)
    await repository.save_many([smallest, unknown, biggest])

    # Act
    homes = await get_top.execute(
        build_search_filter(max_dpe_rating=None), limit=3, sort=ListingSort.SURFACE_DESC
    )

    # Assert
    assert [home.primary.id for home in homes] == [biggest.id, smallest.id, unknown.id]


async def test_breaks_a_price_tie_with_the_newest_parution(
    use_case: tuple[GetTopListings, InMemoryListingRepository],
) -> None:
    # Arrange
    get_top, repository = use_case
    same_price = Price(amount=Decimal("900"))
    older = replace(build_listing(published_offset_minutes=300), price=same_price)
    newer = replace(build_listing(published_offset_minutes=10), price=same_price)
    await repository.save_many([older, newer])

    # Act
    homes = await get_top.execute(
        build_search_filter(max_dpe_rating=None), limit=2, sort=ListingSort.PRICE_ASC
    )

    # Assert
    assert [home.primary.id for home in homes] == [newer.id, older.id]


async def test_ranks_a_timezone_aware_parution_by_its_real_instant(
    use_case: tuple[GetTopListings, InMemoryListingRepository],
) -> None:
    # Arrange — the aware listing is one minute newer, but its wall clock reads
    # three hours earlier; dropping the offset instead of converting buries it.
    get_top, repository = use_case
    local_now = datetime.now().replace(microsecond=0)
    naive = replace(build_listing(), published_at=local_now - timedelta(minutes=1))
    aware = replace(
        build_listing(),
        published_at=local_now.astimezone(_build_foreign_zone()),
    )
    await repository.save_many([naive, aware])

    # Act
    homes = await get_top.execute(build_search_filter(max_dpe_rating=None), limit=2)

    # Assert
    assert [home.primary.id for home in homes] == [aware.id, naive.id]
    assert build_published_key(aware) == local_now


async def test_hides_a_listing_its_source_kept_answering_without(
    use_case: tuple[GetTopListings, InMemoryListingRepository],
) -> None:
    # Arrange
    get_top, repository = use_case
    search_filter = build_search_filter(max_dpe_rating=None)
    answered_at = datetime.now()
    fresh = replace(build_listing(source="pap"), last_seen_at=answered_at)
    expired = replace(build_listing(source="pap"), last_seen_at=answered_at - STALE_AFTER_MIN * 2)
    await repository.save_many([fresh, expired])
    await repository.save_source_successes(search_filter.id, frozenset({"pap"}), answered_at)

    # Act
    homes = await get_top.execute(search_filter, limit=10)

    # Assert
    assert [home.primary.id for home in homes] == [fresh.id]


async def test_page_reports_a_source_that_stopped_answering(
    use_case: tuple[GetTopListings, InMemoryListingRepository],
) -> None:
    # Arrange
    get_top, repository = use_case
    search_filter = build_search_filter(max_dpe_rating=None)
    answered_at = datetime.now()
    down_since = answered_at - SOURCE_DOWN_HIDE_AFTER * 2
    await repository.save_many(
        [replace(build_listing(source="paruvendu"), last_seen_at=down_since)]
    )
    await repository.save_source_successes(search_filter.id, frozenset({"pap"}), answered_at)
    await repository.save_source_successes(search_filter.id, frozenset({"paruvendu"}), down_since)

    # Act
    page = await get_top.execute_paginated(search_filter)

    # Assert
    assert page.total == 0
    assert [(u.source, u.hidden_count) for u in page.unreachable] == [("paruvendu", 1)]


async def test_the_page_says_when_the_filter_was_last_searched(
    use_case: tuple[GetTopListings, InMemoryListingRepository],
) -> None:
    # Arrange
    get_top, repository = use_case
    search_filter = build_search_filter(max_dpe_rating=None)
    older = datetime.now() - timedelta(hours=3)
    latest = datetime.now() - timedelta(minutes=12)
    await repository.save_source_successes(search_filter.id, frozenset({"pap"}), older)
    await repository.save_source_successes(search_filter.id, frozenset({"orpi"}), latest)

    # Act
    page = await get_top.execute_paginated(search_filter)
    never = await get_top.execute_paginated(build_search_filter(max_dpe_rating=None))

    # Assert
    assert page.last_searched_at == latest
    assert never.last_searched_at is None


async def _save_homes_from(
    repository: InMemoryListingRepository, source: str, count: int, first_surface: int
) -> None:
    """`count` distinct homes from one source; the surfaces keep them from grouping."""
    await repository.save_many(
        [build_listing(source=source, surface_m2=first_surface + n) for n in range(count)]
    )


async def test_source_counts_cover_the_whole_filter_not_the_page(
    use_case: tuple[GetTopListings, InMemoryListingRepository],
) -> None:
    # Arrange
    get_top, repository = use_case
    pap_homes, orpi_homes = _fake.random_int(3, 6), _fake.random_int(3, 6)
    await _save_homes_from(repository, "pap", pap_homes, first_surface=20)
    await _save_homes_from(repository, "orpi", orpi_homes, first_surface=60)

    # Act
    page = await get_top.execute_paginated(build_search_filter(max_dpe_rating=None), page_size=2)

    # Assert
    assert page.source_counts == {"orpi": orpi_homes, "pap": pap_homes}
    assert len(page.groups) == 2


async def test_picking_a_source_pages_through_that_source_only(
    use_case: tuple[GetTopListings, InMemoryListingRepository],
) -> None:
    # Arrange
    get_top, repository = use_case
    orpi_homes = _fake.random_int(2, 5)
    await _save_homes_from(repository, "pap", _fake.random_int(3, 6), first_surface=20)
    await _save_homes_from(repository, "orpi", orpi_homes, first_surface=60)

    # Act
    page = await get_top.execute_paginated(
        build_search_filter(max_dpe_rating=None), page=2, page_size=1, source="orpi"
    )

    # Assert
    assert page.total == orpi_homes
    assert page.pages == orpi_homes
    assert [home.primary.source for home in page.groups] == ["orpi"]


async def test_a_page_past_the_last_serves_the_last(
    use_case: tuple[GetTopListings, InMemoryListingRepository],
) -> None:
    # Arrange — a page number kept in a URL after the list shrank
    get_top, repository = use_case
    await _save_homes_from(repository, "pap", 3, first_surface=20)

    # Act
    page = await get_top.execute_paginated(
        build_search_filter(max_dpe_rating=None), page=_fake.random_int(3, 99), page_size=2
    )

    # Assert
    assert (page.page, page.pages, len(page.groups)) == (2, 2, 1)


def _build_reference(commune: str, per_m2: str) -> RentReference:
    value = Decimal(per_m2)
    return RentReference(
        commune=commune,
        segment=RentSegment.ONE_TWO_ROOMS,
        per_m2=value,
        lower_per_m2=value * Decimal("0.7"),
        upper_per_m2=value * Decimal("1.4"),
        observed_in_commune=_fake.random_int(100, 5000),
        r2_adjusted=0.8,
        vintage=2025,
    )


def _build_positioned_use_case(
    references: dict[str, str],
) -> tuple[GetTopListings, InMemoryListingRepository]:
    repository = InMemoryListingRepository()
    geocoded = {"annecy": (45.8992, 6.1294), "villaz": (45.9531, 6.1950)}
    book = InMemoryRentReferences(
        {
            commune: {RentSegment.ONE_TWO_ROOMS: _build_reference(commune, per_m2)}
            for commune, per_m2 in references.items()
        }
    )
    return GetTopListings(repository, InMemoryGeocoding(geocoded), book), repository


def _build_home(city: str, price: float, surface_m2: float, minutes_ago: int = 0) -> Listing:
    return build_listing(
        city=city,
        price=price,
        surface_m2=surface_m2,
        rooms=2,
        charges_included=True,
        published_offset_minutes=minutes_ago,
    )


async def test_position_order_ranks_against_each_commune_and_puts_the_unknown_last() -> None:
    # Arrange — Annecy 18 €/m² vs 20 (−10 %), Villaz 15 €/m² vs 12 (+25 %): cheaper per m²
    # is not lower vs its own reference
    get_top, repository = _build_positioned_use_case({"Annecy": "20", "Villaz": "12"})
    annecy = _build_home("Annecy", price=720.0, surface_m2=40.0)
    villaz = _build_home("Villaz", price=600.0, surface_m2=40.0)
    furnished = replace(_build_home("Annecy", price=400.0, surface_m2=40.0), furnished=True)
    await repository.save_many([villaz, furnished, annecy])

    # Act
    homes = await get_top.execute(
        build_search_filter(cities=["Annecy"], radius_km=20, max_dpe_rating=None),
        limit=3,
        sort=ListingSort.MARKET_POSITION,
    )

    # Assert
    assert [home.primary.id for home in homes] == [annecy.id, villaz.id, furnished.id]


async def test_position_order_keeps_the_best_placed_of_the_pool_not_the_newest() -> None:
    # Arrange — the newest homes are the dearest; the cap is smaller than the pool
    get_top, repository = _build_positioned_use_case({"Annecy": "20"})
    dear_and_new = [
        _build_home("Annecy", price=1100.0 + n, surface_m2=40.0, minutes_ago=n) for n in range(3)
    ]
    cheap_and_old = [
        _build_home("Annecy", price=650.0 + n, surface_m2=40.0, minutes_ago=600 + n)
        for n in range(2)
    ]
    await repository.save_many(dear_and_new + cheap_and_old)

    # Act
    homes = await get_top.execute(
        build_search_filter(cities=["Annecy"], radius_km=20, max_dpe_rating=None, max_results=2),
        limit=2,
        sort=ListingSort.MARKET_POSITION,
    )

    # Assert
    assert {home.primary.id for home in homes} == {home.id for home in cheap_and_old}
