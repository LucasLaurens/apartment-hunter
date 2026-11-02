import pytest

from apartment_hunter.domain.services import ListingMatcher, is_out_of_scope_tenancy

from ..fakes.builders import build_listing, build_search_filter


@pytest.mark.parametrize(
    "title",
    [
        "Chambre meublée dans grand T4",
        "Belle chambre en colocation — centre-ville",
        "Chambre chez l'habitant, proche gare",
        "Colocation meublée 4 chambres",
        "Colocation à louer",
        "Colocation à louer - Annecy",
        "Coliving Annecy — tout inclus",
    ],
)
def test_a_room_is_not_a_home(title: str) -> None:
    # Act & Assert
    assert is_out_of_scope_tenancy(title)


@pytest.mark.parametrize(
    "title",
    [
        "T2 en bail mobilité — 6 mois",
        "Location saisonnière au bord du lac",
        "Meublé de tourisme classé 3 étoiles",
        "Studio en location courte durée",
    ],
)
def test_a_short_term_let_is_not_a_home(title: str) -> None:
    # Act & Assert
    assert is_out_of_scope_tenancy(title)


@pytest.mark.parametrize(
    "title",
    [
        "T4 idéal colocation, 3 chambres",
        "Appartement T3 à louer, colocation possible",
        "Grand T5 pour colocation à louer",
        "Appartement 3 pièces avec chambre parentale",
        "T3 lumineux — deux chambres sur cour",
        "Studio meublé proche université",
    ],
)
def test_a_whole_home_goes_through_even_when_it_mentions_rooms(title: str) -> None:
    # Act & Assert — a missed listing costs far more than a room skipped by eye.
    assert not is_out_of_scope_tenancy(title)


def test_a_description_mentioning_a_nearby_colocation_does_not_exclude() -> None:
    # Arrange — the description names neighbouring facts, not the offer itself.
    description = "Quartier étudiant, nombreuses colocations à proximité."

    # Act & Assert
    assert not is_out_of_scope_tenancy("Appartement T2 rénové", description)


def test_a_description_naming_a_mobility_lease_excludes() -> None:
    # Arrange — a legal regime cannot be named in passing.
    description = "Proposé en bail mobilité de 1 à 10 mois."

    # Act & Assert
    assert is_out_of_scope_tenancy("Appartement T2 rénové", description)


def test_the_matcher_drops_a_room_whatever_the_filter_asks() -> None:
    # Arrange — the filter has no option for this: it is what the tool is about.
    matcher = ListingMatcher(geocoded_cities={"annecy": (45.9, 6.13)})
    search_filter = build_search_filter(cities=["Annecy"])
    room = build_listing(city="Annecy", title="Chambre en colocation — 450€", price=450.0)
    home = build_listing(city="Annecy", title="T3 lumineux 65m²", price=950.0)

    # Act
    room_matches = matcher.matches(room, search_filter)
    home_matches = matcher.matches(home, search_filter)

    # Assert
    assert not room_matches
    assert home_matches
