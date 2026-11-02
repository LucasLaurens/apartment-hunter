"""What `hunt review` shows (ticket 08): rendered to text, no terminal needed."""

from dataclasses import replace
from datetime import date, datetime
from decimal import Decimal

from faker import Faker
from rich.console import Console

from apartment_hunter.application.use_cases import PendingSuggestion
from apartment_hunter.domain.services import (
    CriterionSuggestion,
    RentReferenceBook,
    build_dismissal,
    group_duplicates,
)
from apartment_hunter.domain.value_objects import (
    RENT_MAP_CREDIT,
    DismissalReason,
    ListingSort,
    RentReference,
    RentSegment,
)
from apartment_hunter.presentation.cli.review import (
    DismissedScreen,
    ReviewScreen,
    compute_next_sort,
    format_home_label,
    format_per_m2,
    format_suggestion_question,
)
from tests.fakes.builders import build_listing, build_search_filter

_fake = Faker("fr_FR")
_WIDTH = 160
_HEIGHT = 20


def _render(screen: ReviewScreen | DismissedScreen) -> str:
    console = Console(record=True, width=_WIDTH, color_system=None)
    console.print(screen.render(_HEIGHT))
    return console.export_text()


def test_a_listing_never_opened_carries_the_new_mark() -> None:
    # Arrange
    fresh = build_listing()
    opened = replace(build_listing(), opened_at=datetime.now())
    screen = ReviewScreen(build_search_filter(), group_duplicates([fresh, opened]))

    # Act
    lines = [line for line in _render(screen).splitlines() if "●" in line]

    # Assert
    assert len(lines) == 1


def test_an_opened_home_says_when_it_was_opened() -> None:
    # Arrange
    opened_at = _fake.date_time_this_year()
    listing = replace(build_listing(), opened_at=opened_at)
    screen = ReviewScreen(build_search_filter(), group_duplicates([listing]))

    # Act & Assert
    assert f"ouverte le {opened_at:%d/%m/%Y}" in _render(screen)


def test_a_home_never_opened_says_nothing_of_it() -> None:
    # Arrange
    screen = ReviewScreen(build_search_filter(), group_duplicates([build_listing()]))

    # Act & Assert
    assert "ouverte le" not in _render(screen)


def test_a_home_back_at_another_rent_says_how_it_was_dismissed() -> None:
    # Arrange
    dismissal = build_dismissal(build_listing(), DismissalReason.TOO_EXPENSIVE, datetime.now())
    listing = replace(build_listing(), former_dismissal=dismissal)
    screen = ReviewScreen(build_search_filter(), group_duplicates([listing]))

    # Act & Assert
    assert dismissal.format_mention() in _render(screen)


def test_a_restored_home_says_when_it_was_taken_back() -> None:
    # Arrange
    restored_at = _fake.date_time_this_year()
    listing = replace(build_listing(), restored_at=restored_at)
    screen = ReviewScreen(build_search_filter(), group_duplicates([listing]))

    # Act & Assert
    assert f"restauré le {restored_at:%d/%m/%Y}" in _render(screen)
    assert "d écartés" in _render(screen)


def test_a_rent_alone_is_marked_in_the_list() -> None:
    # Arrange
    listing = build_listing(price=float(_fake.random_int(600, 999)))
    screen = ReviewScreen(build_search_filter(), group_duplicates([listing]))

    # Act & Assert
    assert "charges ?" in _render(screen)


def test_the_detail_reads_like_the_web_card() -> None:
    # Arrange — a passoire thermique, with GES and charges
    listing = build_listing(dpe="G", charges=float(_fake.random_int(30, 120)))
    screen = ReviewScreen(
        build_search_filter(), group_duplicates([listing]), today=date(2026, 10, 29)
    )

    # Act
    text = _render(screen)

    # Assert
    assert "GES" in text
    assert "de charges" in text
    assert "location interdite" in text


def test_a_home_on_several_sources_says_how_many() -> None:
    # Arrange
    rooms, surface, rent = 3, 61.0, float(_fake.random_int(700, 1200))
    group = group_duplicates(
        [
            build_listing(source=source, rooms=rooms, surface_m2=surface, price=rent)
            for source in ("pap", "orpi", "laforet")
        ]
    )

    # Act & Assert
    assert "×3" in _render(ReviewScreen(build_search_filter(), group))


def test_the_header_agrees_with_one_home() -> None:
    # Act & Assert
    screen = ReviewScreen(build_search_filter(), group_duplicates([build_listing()]))
    assert "1 logement à revoir" in _render(screen)


def test_asking_for_a_reason_shows_the_closed_list_in_the_panel() -> None:
    # Arrange
    screen = ReviewScreen(
        build_search_filter(), group_duplicates([build_listing()]), asking_reason=True
    )

    # Act
    text = _render(screen)

    # Assert
    assert "pour quelle raison" in text
    assert "trop cher" in text and "autre" in text


def test_a_message_names_the_home() -> None:
    # Arrange
    listing = build_listing(rooms=3, charges=float(_fake.random_int(30, 120)))

    # Act & Assert
    assert format_home_label(listing).endswith(f"· {listing.location.city} · T3")


def test_price_per_square_metre_uses_a_decimal_comma() -> None:
    # Arrange
    listing = build_listing(price=1000.0, surface_m2=64.0)

    # Act & Assert
    assert format_per_m2(listing).startswith("15,6")


def test_the_dismissed_screen_shows_the_reason_and_restores_by_key() -> None:
    # Arrange
    listing = build_listing()
    dismissal = build_dismissal(listing, DismissalReason.FLOOR, _fake.date_time_this_month())

    # Act
    text = _render(DismissedScreen([dismissal]))

    # Assert
    assert "étage" in text
    assert "u restaurer" in text
    assert "d à revoir" in text
    assert "1 logement écarté" in text


def test_the_review_shows_the_position_its_reference_and_the_source() -> None:
    # Arrange — 880 € for 50 m² against a 20 €/m² T1-T2 reference in Annecy
    reference = RentReference(
        commune="Annecy",
        segment=RentSegment.ONE_TWO_ROOMS,
        per_m2=Decimal("20.00"),
        lower_per_m2=Decimal("15.00"),
        upper_per_m2=Decimal("28.00"),
        observed_in_commune=_fake.random_int(100, 9000),
        r2_adjusted=0.8,
        vintage=2025,
    )
    listing = build_listing(
        city="Annecy", price=880.0, surface_m2=50.0, rooms=2, charges_included=True
    )
    book = RentReferenceBook({"Annecy": {RentSegment.ONE_TWO_ROOMS: reference}})
    screen = ReviewScreen(build_search_filter(), group_duplicates(book.annotate([listing])))

    # Act
    text = _render(screen)

    # Assert
    assert "Position : −12 % vs réf." in text
    assert "T1-T2 (logement type 37 m²) : 20,00 €/m², fourchette 15,00-28,00" in text
    assert RENT_MAP_CREDIT in text


def test_a_home_without_a_reference_says_why() -> None:
    # Arrange
    listing = build_listing(furnished=True)
    screen = ReviewScreen(
        build_search_filter(),
        group_duplicates(RentReferenceBook({}).annotate([listing])),
    )

    # Act & Assert
    assert "Position : pas de repère (meublé)" in _render(screen)


def test_the_sort_key_cycles_position_then_per_m2_then_parution() -> None:
    # Arrange
    start = ListingSort.MARKET_POSITION

    # Act
    seen = [start]
    for _ in range(3):
        seen.append(compute_next_sort(seen[-1]))

    # Assert
    assert seen == [
        ListingSort.MARKET_POSITION,
        ListingSort.PRICE_PER_M2_ASC,
        ListingSort.PUBLISHED_DESC,
        ListingSort.MARKET_POSITION,
    ]


def test_the_review_opens_on_position_order_and_says_so() -> None:
    # Arrange
    screen = ReviewScreen(build_search_filter(), group_duplicates([build_listing()]))

    # Act & Assert
    assert "trié par position au marché" in _render(screen)


def test_the_suggestion_question_names_the_change_its_cause_and_its_cost() -> None:
    # Arrange
    search_filter = build_search_filter()
    pending = PendingSuggestion(
        search_filter=search_filter,
        suggestion=CriterionSuggestion(
            reason=DismissalReason.CITY,
            value="poisy",
            dismissal_count=3,
            proposal="exclure Poisy",
            revised_filter=replace(search_filter, excluded_cities=["Poisy"]),
        ),
        hidden_too=2,
    )

    # Act
    question = format_suggestion_question(pending)

    # Assert
    assert question == (
        f"Suggestion pour « {search_filter.name} » : exclure Poisy ? 3 écarts « commune » ; "
        "masquerait aussi 2 logements non écartés. [o/N]"
    )
