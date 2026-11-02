from datetime import date, timedelta

from apartment_hunter.domain.services import (
    RENTAL_BAN_DATES,
    THERMAL_SIEVE_LABEL,
    build_rental_ban_warning,
    is_thermal_sieve,
)
from apartment_hunter.domain.value_objects import DpeRating


def test_f_and_g_are_thermal_sieves() -> None:
    # Act & Assert
    assert is_thermal_sieve(DpeRating.F)
    assert is_thermal_sieve(DpeRating.G)


def test_e_carries_a_ban_date_without_being_a_thermal_sieve() -> None:
    # Act & Assert — the law bans E in 2034, but the word designates F and G only.
    assert DpeRating.E in RENTAL_BAN_DATES
    assert not is_thermal_sieve(DpeRating.E)
    assert build_rental_ban_warning(DpeRating.E, date(2030, 1, 1)) == ""


def test_unknown_rating_is_not_a_thermal_sieve() -> None:
    # Act & Assert — absence of a DPE is an unknown, never an accusation.
    assert not is_thermal_sieve(None)
    assert build_rental_ban_warning(None, date(2026, 1, 1)) == ""


def test_good_ratings_carry_no_warning() -> None:
    # Arrange
    today = date(2026, 1, 1)

    # Act & Assert
    for rating in (DpeRating.A, DpeRating.B, DpeRating.C, DpeRating.D):
        assert build_rental_ban_warning(rating, today) == ""


def test_warning_is_past_tense_once_the_ban_took_effect() -> None:
    # Arrange
    ban_day = RENTAL_BAN_DATES[DpeRating.G]

    # Act
    warning = build_rental_ban_warning(DpeRating.G, ban_day)

    # Assert
    assert warning == f"{THERMAL_SIEVE_LABEL} — location interdite depuis le 01/01/2025"


def test_warning_is_future_tense_the_day_before_the_ban() -> None:
    # Arrange
    eve = RENTAL_BAN_DATES[DpeRating.F] - timedelta(days=1)

    # Act
    warning = build_rental_ban_warning(DpeRating.F, eve)

    # Assert
    assert warning == f"{THERMAL_SIEVE_LABEL} — location interdite à partir du 01/01/2028"


def test_every_banned_class_is_worse_than_the_one_banned_later() -> None:
    # Act & Assert — the calendar must follow the rating order, worst banned first.
    by_date = sorted(RENTAL_BAN_DATES.items(), key=lambda pair: pair[1])
    ranks = [rating.compute_rank() for rating, _ in by_date]
    assert ranks == sorted(ranks, reverse=True)
