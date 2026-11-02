"""Date wordings taken from the real listing pages each crawler reads."""

from datetime import datetime, timedelta

import pytest
from faker import Faker

from apartment_hunter.infrastructure.crawlers.french_dates import parse_french_date

_fake = Faker("fr_FR")


def test_reads_an_iso_timestamp_with_offset() -> None:
    # Arrange — Foncia's SSR state, SeLoger's search payload
    text = 'datePublication":"2026-08-03T10:22:27+02:00"'

    # Act
    parsed = parse_french_date(text)

    # Assert
    assert parsed == datetime(2026, 8, 3, 10, 22, 27)


def test_reads_an_iso_date_without_time() -> None:
    # Act & Assert — Orpi's analytics payload
    assert parse_french_date('dateCreation: "2024-05-06"') == datetime(2024, 5, 6)


def test_reads_a_french_numeric_date() -> None:
    # Act & Assert — ParuVendu's clock-icon paragraph
    assert parse_french_date("03/08/2026") == datetime(2026, 8, 3)


def test_reads_a_spelled_out_date() -> None:
    # Act & Assert — PAP's "p.item-date"
    assert parse_french_date("Réf. : D43/0192 / Publié le 3 août 2026") == datetime(2026, 8, 3)


def test_reads_a_spelled_out_date_with_ordinal_and_accents() -> None:
    # Act & Assert
    assert parse_french_date("Publié le 1er février 2026") == datetime(2026, 2, 1)


@pytest.mark.parametrize(
    ("wording", "expected_delta"),
    [
        ("il y a 30 minutes", timedelta(minutes=30)),
        ("il y a 5 heures", timedelta(hours=5)),
        ("il y a 2 jours", timedelta(days=2)),
        ("il y a 3 semaines", timedelta(weeks=3)),
        ("il y a 2 mois", timedelta(days=60)),
    ],
)
def test_reads_a_relative_wording(wording: str, expected_delta: timedelta) -> None:
    # Arrange
    now = _fake.date_time_between(start_date="-1y", end_date="now")

    # Act
    parsed = parse_french_date(wording, now=now)

    # Assert
    assert parsed == now - expected_delta


def test_reads_today_and_yesterday() -> None:
    # Arrange
    now = _fake.date_time_between(start_date="-1y", end_date="now")

    # Act & Assert
    assert parse_french_date("Aujourd'hui", now=now) == now
    assert parse_french_date("Hier à 14h", now=now) == now - timedelta(days=1)


def test_ignores_hier_hidden_inside_a_word() -> None:
    # Act & Assert — "fichier" must not read as "hier"
    assert parse_french_date("Télécharger le fichier") is None


def test_returns_none_when_no_date_is_present() -> None:
    # Act & Assert — Century 21 cards
    assert parse_french_date("Appartement 3 pcs 60,3 m² charges comprises") is None
    assert parse_french_date("") is None


def test_returns_none_for_an_impossible_date() -> None:
    # Act & Assert — a site typo must not crash the crawl
    assert parse_french_date("31/02/2026") is None
