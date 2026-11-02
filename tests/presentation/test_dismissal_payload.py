"""What the web page may send when it dismisses a home, and the list it reads keys from."""

import pytest
from faker import Faker

from apartment_hunter.domain.value_objects import DismissalReason
from apartment_hunter.presentation.dismissal_reasons import REASON_KEYS, REASON_LABELS
from apartment_hunter.presentation.web.dismissal_payload import parse_dismissal

_fake = Faker("fr_FR")


def test_a_known_reason_is_read() -> None:
    # Act
    reason, note = parse_dismissal({"reason": DismissalReason.FLOOR.value})

    # Assert
    assert (reason, note) == (DismissalReason.FLOOR, "")


def test_the_other_reason_keeps_its_text() -> None:
    # Arrange
    text = _fake.sentence()

    # Act
    reason, note = parse_dismissal({"reason": DismissalReason.OTHER.value, "note": f"  {text} "})

    # Assert
    assert (reason, note) == (DismissalReason.OTHER, text)


def test_an_unknown_reason_is_refused() -> None:
    # Act & Assert
    with pytest.raises(ValueError):
        parse_dismissal({"reason": _fake.word()})


def test_a_note_on_a_listed_reason_is_refused() -> None:
    # Act & Assert
    with pytest.raises(ValueError):
        parse_dismissal({"reason": DismissalReason.DPE.value, "note": _fake.sentence()})


def test_every_reason_has_one_key_and_one_label() -> None:
    # Arrange
    reasons = [reason for reason, _ in REASON_KEYS.values()]

    # Act & Assert — a reason added to the enum must be typeable on both screens
    assert sorted(reasons) == sorted(DismissalReason)
    assert set(REASON_LABELS) == set(DismissalReason)
