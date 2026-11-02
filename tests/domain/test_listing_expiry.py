"""Expired listings: hidden when their source answered without them, flagged when the
source itself stopped answering (ticket 13)."""

from dataclasses import replace
from datetime import datetime, timedelta

from faker import Faker

from apartment_hunter.domain.services import (
    SOURCE_DOWN_HIDE_AFTER,
    STALE_AFTER_MIN,
    STALE_REFRESH_FACTOR,
    SourceFreshness,
    build_source_down_warning,
    compute_stale_after,
)
from tests.fakes.builders import build_listing

_fake = Faker()


def _pick_moment() -> datetime:
    return _fake.date_time_between(start_date="-30d", end_date="now")


def test_listing_seen_by_the_latest_answer_of_its_source_stays_shown() -> None:
    # Arrange
    answered_at = _pick_moment()
    listing = replace(build_listing(source="pap"), last_seen_at=answered_at)
    freshness = SourceFreshness({"pap": answered_at}, STALE_AFTER_MIN)

    # Act
    report = freshness.sort_out([listing])

    # Assert
    assert report.shown == [listing]
    assert report.unreachable == []


def test_listing_unseen_while_its_source_kept_answering_is_hidden() -> None:
    # Arrange
    answered_at = _pick_moment()
    expired = replace(
        build_listing(source="pap"),
        last_seen_at=answered_at - STALE_AFTER_MIN - timedelta(minutes=1),
    )
    freshness = SourceFreshness({"pap": answered_at}, STALE_AFTER_MIN)

    # Act
    report = freshness.sort_out([expired])

    # Assert
    assert report.shown == []


def test_listing_of_a_source_down_less_than_a_week_is_shown_with_its_down_days() -> None:
    # Arrange
    reference = _pick_moment()
    down_days = _fake.random_int(3, 6)
    down_since = reference - timedelta(days=down_days)
    listing = replace(build_listing(source="paruvendu"), last_seen_at=down_since)
    freshness = SourceFreshness({"pap": reference, "paruvendu": down_since}, STALE_AFTER_MIN)

    # Act
    report = freshness.sort_out([listing])

    # Assert
    assert [shown.source_down_days for shown in report.shown] == [down_days]
    assert [(u.source, u.down_days, u.hidden_count) for u in report.unreachable] == [
        ("paruvendu", down_days, 0)
    ]


def test_listing_of_a_source_down_more_than_a_week_is_hidden_and_counted() -> None:
    # Arrange
    reference = _pick_moment()
    down_since = reference - SOURCE_DOWN_HIDE_AFTER - timedelta(days=1)
    listings = [
        replace(build_listing(source="paruvendu"), last_seen_at=down_since) for _ in range(2)
    ]
    freshness = SourceFreshness({"pap": reference, "paruvendu": down_since}, STALE_AFTER_MIN)

    # Act
    report = freshness.sort_out(listings)

    # Assert
    assert report.shown == []
    assert [(u.source, u.hidden_count) for u in report.unreachable] == [("paruvendu", 2)]


def test_time_is_measured_against_the_filter_crawls_not_the_wall_clock() -> None:
    # Arrange — laptop shut for a month: nothing answered since, so nothing ages
    month_ago = datetime.now() - timedelta(days=30)
    listing = replace(build_listing(source="pap"), last_seen_at=month_ago)
    freshness = SourceFreshness({"pap": month_ago}, STALE_AFTER_MIN)

    # Act
    report = freshness.sort_out([listing])

    # Assert
    assert report.shown == [listing]


def test_listing_of_a_source_that_never_answered_this_filter_is_kept() -> None:
    # Arrange — in doubt, keep: a missed listing costs more than a wasted click
    long_ago = _pick_moment() - timedelta(days=60)
    listing = replace(build_listing(source="orpi"), last_seen_at=long_ago)
    freshness = SourceFreshness({"pap": _pick_moment()}, STALE_AFTER_MIN)

    # Act
    report = freshness.sort_out([listing])

    # Assert
    assert report.shown == [listing]


def test_source_unaffecting_any_listing_is_not_reported() -> None:
    # Arrange
    reference = _pick_moment()
    freshness = SourceFreshness(
        {"pap": reference, "paruvendu": reference - timedelta(days=3)}, STALE_AFTER_MIN
    )

    # Act
    report = freshness.sort_out([])

    # Assert
    assert report.unreachable == []


def test_stale_after_grows_with_a_slow_refresh_interval() -> None:
    # Arrange
    slow_minutes = int(STALE_AFTER_MIN.total_seconds() // 60) + _fake.random_int(60, 600)

    # Act & Assert
    expected = timedelta(minutes=slow_minutes * STALE_REFRESH_FACTOR)
    assert compute_stale_after(slow_minutes) == expected
    assert compute_stale_after(_fake.random_int(5, 60)) == STALE_AFTER_MIN


def test_down_warning_is_empty_for_a_healthy_source() -> None:
    # Act & Assert
    assert build_source_down_warning(0) == ""
    assert "3 j" in build_source_down_warning(3)
