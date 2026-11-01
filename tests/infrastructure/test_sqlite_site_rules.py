"""The hunter's choice about the sites' rules outlives the process (ADR-0012)."""

from pathlib import Path

from apartment_hunter.domain.value_objects import SiteRules
from apartment_hunter.infrastructure.storage.sqlite_repository import SqliteRepository


async def _open_repository(tmp_path: Path) -> SqliteRepository:
    repository = SqliteRepository(str(tmp_path / "hunter.db"))
    await repository.connect()
    return repository


async def test_the_rules_are_honoured_until_the_hunter_says_otherwise(tmp_path: Path) -> None:
    # Arrange
    repository = await _open_repository(tmp_path)

    # Act & Assert
    assert await repository.load_site_rules() is SiteRules.HONOURED
    await repository.close()


async def test_a_choice_survives_a_reconnection_and_can_be_taken_back(tmp_path: Path) -> None:
    # Arrange
    repository = await _open_repository(tmp_path)
    await repository.save_site_rules(SiteRules.IGNORED)
    await repository.close()

    # Act
    reopened = await _open_repository(tmp_path)
    kept = await reopened.load_site_rules()
    await reopened.save_site_rules(SiteRules.HONOURED)

    # Assert
    assert kept is SiteRules.IGNORED
    assert await reopened.load_site_rules() is SiteRules.HONOURED
    await reopened.close()
