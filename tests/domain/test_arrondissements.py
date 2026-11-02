"""Paris, Lyon and Marseille are read by arrondissement: the rent map has no city row."""

import pytest

from apartment_hunter.domain.services import build_arrondissement_name, is_arrondissement_code


@pytest.mark.parametrize(
    ("city", "postal_code", "expected"),
    [
        ("Paris", "75011", "Paris 11e Arrondissement"),
        ("Paris", "75001", "Paris 1er Arrondissement"),
        ("PARIS", "75116", "Paris 16e Arrondissement"),
        ("Lyon", "69003", "Lyon 3e Arrondissement"),
        ("Marseille", "13008", "Marseille 8e Arrondissement"),
    ],
)
def test_the_postal_code_names_the_arrondissement(
    city: str, postal_code: str, expected: str
) -> None:
    # Act & Assert
    assert build_arrondissement_name(city, postal_code) == expected


@pytest.mark.parametrize(
    ("label", "expected"),
    [
        ("Paris 11e", "Paris 11e Arrondissement"),
        ("Paris 1er Arrondissement", "Paris 1er Arrondissement"),
        ("Lyon 3ème", "Lyon 3e Arrondissement"),
        ("marseille 13", "Marseille 13e Arrondissement"),
    ],
)
def test_a_city_label_names_the_arrondissement_without_a_postal_code(
    label: str, expected: str
) -> None:
    # Act & Assert
    assert build_arrondissement_name(label, None) == expected


@pytest.mark.parametrize(
    ("city", "postal_code"),
    [
        ("Paris", None),  # no clue which arrondissement
        ("Paris", "92100"),  # a postal code outside the city
        ("Paris 21e", None),  # Paris stops at 20
        ("Lyon", "69010"),  # Lyon stops at 9
        ("Marseille-en-Beauvaisis", "60690"),  # a commune of the Oise, no arrondissement
        ("Annecy", "74000"),
    ],
)
def test_no_arrondissement_is_invented(city: str, postal_code: str | None) -> None:
    # Act & Assert
    assert build_arrondissement_name(city, postal_code) == ""


def test_only_the_arrondissement_codes_are_recognised() -> None:
    # Act & Assert — 75056 is Paris as a whole, which the map does not carry
    assert all(is_arrondissement_code(code) for code in ("75111", "69381", "13216"))
    assert not any(is_arrondissement_code(code) for code in ("75056", "69123", "13055", "74010"))
