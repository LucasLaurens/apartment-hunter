"""Scraped text and scraped links, as the app is willing to accept them."""

import pytest
from faker import Faker

from apartment_hunter.domain.services import MAX_DESCRIPTION_CHARS, MAX_TEXT_CHARS, clean_text
from apartment_hunter.domain.services.sanitising import is_web_url

_fake = Faker("fr_FR")


def test_strips_null_bytes() -> None:
    # Arrange
    title = _fake.sentence()

    # Act
    cleaned = clean_text(f"{title}\x00")

    # Assert
    assert cleaned == title


def test_trims_surrounding_whitespace() -> None:
    # Arrange
    city = _fake.city()

    # Act & Assert
    assert clean_text(f"  {city}\n") == city


def test_caps_text_length() -> None:
    # Act
    cleaned = clean_text("a" * (MAX_TEXT_CHARS * 2))

    # Assert
    assert cleaned is not None
    assert len(cleaned) == MAX_TEXT_CHARS


def test_caps_a_description_at_its_own_limit() -> None:
    # Act
    cleaned = clean_text("b" * (MAX_DESCRIPTION_CHARS + 10), MAX_DESCRIPTION_CHARS)

    # Assert
    assert cleaned is not None
    assert len(cleaned) == MAX_DESCRIPTION_CHARS


def test_keeps_none_as_none() -> None:
    # Act & Assert
    assert clean_text(None) is None


@pytest.mark.parametrize(
    "url",
    [
        "javascript:alert(1)",
        "data:text/html,<script>alert(1)</script>",
        "file:///etc/passwd",
        "https://",
        "",
    ],
)
def test_rejects_a_non_web_url(url: str) -> None:
    # Act & Assert
    assert is_web_url(url) is False


@pytest.mark.parametrize("scheme", ["http", "https", "HTTPS"])
def test_accepts_an_http_url(scheme: str) -> None:
    # Act & Assert
    assert is_web_url(f"{scheme}://www.pap.fr/annonces/12345") is True
