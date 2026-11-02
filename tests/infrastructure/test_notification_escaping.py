"""The terminal alert renders scraped text as text, never as Rich markup."""

from dataclasses import replace

from rich.console import Console

from apartment_hunter.domain.value_objects import RENT_MAP_CREDIT
from apartment_hunter.infrastructure.notifications.terminal_notifier import TerminalNotifier
from tests.fakes.builders import build_listing, build_search_filter

_WIDE_ENOUGH = 400  # one alert line must not wrap, or the assertion would split it


async def test_the_terminal_alert_prints_scraped_markup_as_text_and_names_the_source() -> None:
    # Arrange — a title Rich would otherwise read as a style and a link
    hostile = "[bold red][link=https://evil.example]Offre[/link][/bold red]"
    listing = replace(build_listing(), title=hostile)
    console = Console(record=True, width=_WIDE_ENOUGH, color_system=None)

    # Act
    await TerminalNotifier(console).notify([listing], build_search_filter())

    # Assert
    text = console.export_text()
    assert hostile in text
    assert RENT_MAP_CREDIT in text
