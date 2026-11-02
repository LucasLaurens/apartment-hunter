"""What /api/search/status says while a search runs: each source's own state (W3)."""

from faker import Faker

from apartment_hunter.application.use_cases import SourceProgress, SourceState
from apartment_hunter.presentation.web.background_jobs import BackgroundJobs

_fake = Faker()


def test_the_status_lists_each_source_with_its_latest_word() -> None:
    # Arrange
    jobs = BackgroundJobs()
    filter_id = _fake.uuid4()
    count = _fake.random_int(1, 40)
    jobs.save_source_progress(filter_id, SourceProgress("pap", SourceState.RUNNING))
    jobs.save_source_progress(filter_id, SourceProgress("pap", SourceState.FOUND, count))
    jobs.save_source_progress(filter_id, SourceProgress("orpi", SourceState.FAILED))

    # Act
    status = jobs.read_search_status(filter_id)

    # Assert
    assert status["sources"] == [
        {"source": "orpi", "state": "failed", "count": 0},
        {"source": "pap", "state": "found", "count": count},
    ]


def test_another_filter_shows_no_source() -> None:
    # Arrange
    jobs = BackgroundJobs()
    jobs.save_source_progress(_fake.uuid4(), SourceProgress("pap", SourceState.RUNNING))

    # Act & Assert
    assert jobs.read_search_status(_fake.uuid4())["sources"] == []
