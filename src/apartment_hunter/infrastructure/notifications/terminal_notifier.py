"""Terminal notifier — prints a clear, readable block to stdout.

No OS push, no email: new listings surface either here (terminal) or via the
web UI's "Nouveau" badge (in-app bell).
"""

from rich.console import Console
from rich.markup import escape

from ...application.use_cases import format_alert_line
from ...domain.entities import Listing, SearchFilter
from ...domain.ports import NotifierPort
from ...domain.value_objects import RENT_MAP_CREDIT

_MAX_LISTED = 10  # beyond that the block stops being readable in a terminal


class TerminalNotifier(NotifierPort):
    name = "terminal"

    def __init__(self, console: Console | None = None) -> None:
        self._console = console or Console()

    async def notify(self, listings: list[Listing], search_filter: SearchFilter) -> None:
        # Scraped text and the filter name go through `escape`: Rich would otherwise read
        # a title such as "[link=…]" as markup and print something the site never wrote.
        count = len(listings)
        plural = "nouvelle annonce" if count == 1 else "nouvelles annonces"
        self._console.print(
            f"\n[bold green]🔔 {count} {plural}[/] · [bold]{escape(search_filter.name)}[/]"
        )
        for listing in listings[:_MAX_LISTED]:
            self._console.print(f"  • {escape(format_alert_line(listing))}")
            self._console.print(f"    [dim blue]{escape(listing.url)}[/]")
        if count > _MAX_LISTED:
            self._console.print(f"  [dim]… +{count - _MAX_LISTED} de plus[/]")
        # Licence Ouverte: the block shows positions, so it names their source.
        self._console.print(f"  [dim]{escape(RENT_MAP_CREDIT)}[/]")
