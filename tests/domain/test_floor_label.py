"""The storey as printed on the card and in the terminal: French ordinals (W23)."""

import pytest
from faker import Faker

from apartment_hunter.domain.value_objects import Floor

_fake = Faker()


def test_first_floor_reads_premier() -> None:
    # Act & Assert
    assert Floor.from_int(1).format_label() == "1er étage"


@pytest.mark.parametrize("level", [_fake.random_int(2, 30) for _ in range(3)])
def test_higher_floors_read_the_short_ordinal(level: int) -> None:
    # Act
    label = Floor.from_int(level).format_label()

    # Assert
    assert label == f"{level}e étage"


def test_top_floor_says_so() -> None:
    # Act & Assert
    assert Floor.from_int(4, is_top=True).format_label() == "4e étage (dernier)"
