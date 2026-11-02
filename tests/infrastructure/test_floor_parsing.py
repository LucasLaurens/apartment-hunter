"""`parse_floor` — the storey, in every wording the sources actually print."""

import pytest
from bs4 import BeautifulSoup

from apartment_hunter.domain.value_objects import Floor
from apartment_hunter.infrastructure.crawlers.base_crawler import parse_floor
from apartment_hunter.infrastructure.crawlers.laforet_crawler import LaforetCrawler
from apartment_hunter.infrastructure.crawlers.paruvendu_crawler import ParuVenduCrawler


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Étage 3", Floor.from_int(3)),  # Orpi's info line
        ("Etage : 2", Floor.from_int(2)),  # ParuVendu's characteristics table
        ("Étage 3/5", Floor.from_int(3)),  # SeLoger's tag list
        ("Étage 5/5", Floor.from_int(5, is_top=True)),
        ("Situé au 2ème étage d'une copropriété sans ascenseur", Floor.from_int(2)),
        ("se trouve au 4e étage sur 5 d'une copropriété récente", Floor.from_int(4)),
        ("se trouve au 5e étage sur 5, avec ascenseur", Floor.from_int(5, is_top=True)),
        ("Charmant T2 au 3ème étage, dernier étage de l'immeuble", Floor.from_int(3, is_top=True)),
        ("Appartement en rez-de-chaussée avec jardin", Floor.ground()),
        ("Studio RDC sur cour", Floor.ground()),
    ],
)
def test_reads_the_storey(text: str, expected: Floor) -> None:
    # Act & Assert
    assert parse_floor(text) == expected


@pytest.mark.parametrize(
    "text",
    [
        "Appartement 3 pièces 60 m² avec balcon",
        "Immeuble récent de 5 étages avec ascenseur",  # a building's height, not a storey
    ],
)
def test_leaves_the_storey_unknown_when_the_text_says_nothing(text: str) -> None:
    # Act & Assert — an invented storey would silently drop listings from the results
    assert parse_floor(text) is None


def test_laforet_reads_the_storey_from_its_broken_ordinal() -> None:
    # Arrange — the advertiser's own copy ships a mojibake ordinal: "4? étage"
    soup = BeautifulSoup(
        "<p>ce T2 meublé de 43,12 m² se trouve au 4? étage sur 5 d'une copropriété</p>",
        "lxml",
    )

    # Act
    details = LaforetCrawler.parse_details(soup)

    # Assert
    assert details.floor == Floor.from_int(4)


def test_paruvendu_reads_the_storey_alongside_the_energy_scales() -> None:
    # Arrange
    soup = BeautifulSoup(
        '<div class="DPE_consEnerNote NoteEnerg_D">D</div>'
        "<ul><li>Etage : 2</li><li>Meublé : non</li></ul>",
        "lxml",
    )

    # Act
    details = ParuVenduCrawler.parse_details(soup)

    # Assert
    assert details.floor == Floor.from_int(2)
    assert details.dpe_rating is not None
    assert details.furnished is False


def test_laforet_reads_the_furnishing_answer_from_its_criteria_list() -> None:
    # Arrange — the page's own nav links to "Location meublée" pages of other towns
    soup = BeautifulSoup(
        "<nav><a>Location meublée Annecy</a></nav><ul><li>Meublé : oui</li></ul>",
        "lxml",
    )

    # Act
    details = LaforetCrawler.parse_details(soup)

    # Assert — the nav must not decide it; the criteria list must
    assert details.furnished is True
