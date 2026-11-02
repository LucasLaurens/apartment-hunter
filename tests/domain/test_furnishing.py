"""`detect_furnished` / `detect_furnished_label` / `detect_furnished_chip` — the
furnishing answer, in the wordings the sources actually print.

The filter is only as good as this reading: a listing whose furnishing stays unknown
is kept by `ListingMatcher`, so a missed "Meublé : oui" is a meublé on screen for
someone who asked for unfurnished.
"""

import pytest

from apartment_hunter.domain.services import (
    detect_furnished,
    detect_furnished_chip,
    detect_furnished_label,
)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Appartement T2 meublé avec balcon", True),
        ("Studio meublée proche gare", True),
        ("Location non meublée, 3 pièces", False),
        ("Appartement vide, refait à neuf", False),
        # Criteria tables answer next to the label — the bare "Meublé" must not win.
        ("Meublé : Non", False),
        ("Meublé Non", False),
        ("Meublé ? oui", True),
        ("Meublé : oui", True),
        ("Charges : 45 € Étage : 2 Meublé : non Ascenseur : oui", False),
        ("Appartement 3 pièces 60 m² avec balcon", None),
    ],
)
def test_reads_the_furnishing_answer(text: str, expected: bool | None) -> None:
    # Act & Assert
    assert detect_furnished(text) is expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Meublé : non", False),
        ("Meublé Oui", True),
        # A whole detail page carries the site's own nav: bare wording proves nothing.
        ("Location meublée Annecy Location meublée Lyon Nos agences", None),
        ("Appartement lumineux, cuisine équipée", None),
    ],
)
def test_page_level_reading_trusts_the_label_only(text: str, expected: bool | None) -> None:
    # Act & Assert
    assert detect_furnished_label(text) is expected


@pytest.mark.parametrize(
    ("chips", "expected"),
    [
        # Laforêt's own table: a bare chip, which the labelled reading can't see.
        (["Chauffage Gaz de ville", "Ascenseur", "Terrasse", "Meublé"], True),
        (["Ascenseur", "Non meublé"], False),
        (["Ascenseur", "Meublé : non"], False),
        # A chip is the whole answer: a longer wording is a link, not this listing's.
        (["Location meublée Annecy", "Nos agences"], None),
        (["Ascenseur", "Terrasse"], None),
        ([], None),
        # Both printed: the negation is the explicit answer.
        (["Meublé", "Non meublé"], False),
    ],
)
def test_chip_reading_trusts_a_chip_that_is_the_word(
    chips: list[str], expected: bool | None
) -> None:
    # Act & Assert
    assert detect_furnished_chip(chips) is expected
