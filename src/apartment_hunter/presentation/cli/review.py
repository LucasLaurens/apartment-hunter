"""`hunt review`: pass a filter's homes in review, one keystroke per decision.

Layout chosen on the prototype (ticket 04, branch `prototype/hunt-review`, variant C):
a short list on the left, the selected home's detail on the right. Rich renders; the
keys are read raw with the standard library, so no TUI framework is needed.

The screen holds no rule of its own. What is shown comes from `GetTopListings`, which
already hides dismissed homes; after a dismissal the list is read again rather than
patched locally, so a duplicate of the dismissed home vanishes with it.

The detail panel reads in the web card's order (ticket 06) and uses its words, so the
two surfaces speak one language (ticket 08). Colours are the terminal's own: `reverse`
for the selection, `green` for new, so a light terminal reads as well as a dark one.
"""

import os
import sys
import termios
import tty
import webbrowser
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import Final

from rich.console import Group, RenderableType
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from ...application.use_cases import PendingSuggestion
from ...domain.entities import Dismissal, Listing, SearchFilter
from ...domain.services import (
    SUGGESTION_THRESHOLD,
    AdvertiserKind,
    ListingGroup,
    build_rental_ban_warning,
    build_source_down_warning,
    detect_advertiser_kind,
    format_restored_label,
)
from ...domain.value_objects import (
    RENT_MAP_CREDIT,
    DismissalReason,
    ListingSort,
    MarketPosition,
    format_euros,
)
from ...infrastructure.container import Container
from ..dismissal_reasons import REASON_KEYS, REASON_LABELS
from .formatters import console, format_published_cell, format_rating_badge

# Raw keys: an arrow arrives as a three-byte escape sequence (R8).
_NEXT_KEYS: Final = frozenset({"j", "\x1b[B"})
_PREVIOUS_KEYS: Final = frozenset({"k", "\x1b[A"})
_QUIT_KEYS: Final = frozenset({"q", "\x03"})  # \x03 = Ctrl-C, swallowed by raw mode
_OPEN_KEY: Final = "o"
_DISMISS_KEY: Final = "x"
_UNDO_KEY: Final = "u"
# In the dismissed view `u` restores the selected home, as it undoes a dismissal in the
# review; `r` stays, the key the first version of this view taught.
_RESTORE_KEYS: Final = frozenset({_UNDO_KEY, "r"})
_SWITCH_VIEW_KEY: Final = "d"
_SORT_KEY: Final = "s"
_ACCEPT_KEY: Final = "o"  # the question reads « [o/N] »: anything else is a no
# Lowest vs the reference first: the review is where homes get decided (ticket 06). The
# web page keeps the newest parution first.
_REVIEW_SORTS: Final = (
    ListingSort.MARKET_POSITION,
    ListingSort.PRICE_PER_M2_ASC,
    ListingSort.PUBLISHED_DESC,
)
_SORT_LABELS: Final[dict[ListingSort, str]] = {
    ListingSort.MARKET_POSITION: "position au marché",
    ListingSort.PRICE_PER_M2_ASC: "€/m²",
    ListingSort.PUBLISHED_DESC: "parution",
}
_KEY_READ_BYTES: Final = 8  # enough for any escape sequence a terminal sends for a key

_REVIEW_HELP: Final = (
    "j/k ou ↑/↓ naviguer · o ouvrir · x écarter · u annuler · s trier · d écartés · q quitter"
)
_DISMISSED_HELP: Final = "j/k ou ↑/↓ naviguer · u restaurer · d à revoir · q quitter"
_REASON_HELP: Final = "Touche de la raison · toute autre touche annule"
_NOT_A_TERMINAL: Final = (
    "hunt review a besoin d'un terminal interactif : lancez-le directement, "
    "sans redirection ni pipe."
)
_CHROME_LINES: Final = 6  # header, blank lines, message, keys help
_CITY_WIDTH: Final = 16
_LIST_RATIO: Final = 2
_DETAIL_RATIO: Final = 3
_REASON_COLUMNS: Final = 2
_NEW_MARK: Final = "●"
_SELECTED_MARK: Final = "▶"

_ADVERTISER_LABELS: Final[dict[AdvertiserKind, str]] = {
    AdvertiserKind.PRIVATE: "Particulier",
    AdvertiserKind.AGENCY: "Agence",
    AdvertiserKind.UNKNOWN: "annonceur inconnu",
}


def format_size(listing: Listing) -> str:
    rooms = f"T{listing.rooms}" if listing.rooms else "T?"
    surface = f"{listing.surface_m2:.0f} m²" if listing.surface_m2 else "? m²"
    return f"{rooms} · {surface}"


def format_home_label(listing: Listing) -> str:
    """« 941 € CC · Poisy · T3 »: what a message names, so a dismissal says which home."""
    rooms = f"T{listing.rooms}" if listing.rooms else "T?"
    return f"{listing.price.format_total()} · {listing.location.city} · {rooms}"


def format_per_m2(listing: Listing) -> str:
    if not listing.surface_m2:
        return ""
    per_m2 = listing.price.total / Decimal(str(listing.surface_m2))
    return f"{per_m2:.1f}".replace(".", ",") + " €/m²"


def _format_advertiser(listing: Listing) -> str:
    kind = detect_advertiser_kind(listing.source, listing.advertiser)
    if kind is AdvertiserKind.AGENCY and listing.advertiser:
        return listing.advertiser
    return _ADVERTISER_LABELS[kind]


def _format_count(count: int, word: str) -> str:
    return f"{count} {word}{'s' if count > 1 else ''}"


def _render_split(
    header: str,
    left: RenderableType,
    right: RenderableType,
    message: str,
    keys_help: str,
    credit: str = "",
) -> RenderableType:
    split = Table.grid(expand=True)
    split.add_column(ratio=_LIST_RATIO)
    split.add_column(ratio=_DETAIL_RATIO)
    split.add_row(left, right)
    return Group(
        Text(header, style="bold"),
        Text(""),
        split,
        Text(""),
        Text(message, style="magenta"),
        Text(keys_help, style="dim"),
        Text(credit, style="dim"),
    )


def _render_reasons() -> RenderableType:
    """The closed list in two columns, inside the panel rather than under the help (R10)."""
    grid = Table.grid(padding=(0, 3))
    for _ in range(_REASON_COLUMNS):
        grid.add_column()
    cells = [Text.assemble((key, "bold"), f" {label}") for key, (_, label) in REASON_KEYS.items()]
    for start in range(0, len(cells), _REASON_COLUMNS):
        row = cells[start : start + _REASON_COLUMNS]
        grid.add_row(*row, *[Text("")] * (_REASON_COLUMNS - len(row)))
    return Panel(grid, title="Écarter : pour quelle raison ?")


@dataclass
class ReviewScreen:
    """The screen's own state: which homes, which one is selected, what to tell."""

    search_filter: SearchFilter
    groups: list[ListingGroup]
    cursor: int = 0
    message: str = ""
    asking_reason: bool = False
    sort: ListingSort = _REVIEW_SORTS[0]
    today: date = field(default_factory=date.today)  # dates the F/G letting-ban wording

    def find_current(self) -> ListingGroup | None:
        if not self.groups:
            return None
        self.cursor = max(0, min(self.cursor, len(self.groups) - 1))
        return self.groups[self.cursor]

    def render(self, height: int) -> RenderableType:
        header = (
            f"hunt review · « {self.search_filter.name} » · "
            f"{_format_count(len(self.groups), 'logement')} à revoir · "
            f"trié par {_SORT_LABELS[self.sort]}"
        )
        detail = self._render_detail()
        if self.asking_reason:
            detail = Group(detail, _render_reasons())
        keys_help = _REASON_HELP if self.asking_reason else _REVIEW_HELP
        # Licence Ouverte: a screen that shows positions names their source (ADR-0010).
        return _render_split(
            header, self._render_list(height), detail, self.message, keys_help, RENT_MAP_CREDIT
        )

    def _render_list(self, height: int) -> RenderableType:
        rows = Table.grid(padding=(0, 1))
        rows.add_column()  # selection
        rows.add_column()  # new
        rows.add_column(justify="right")  # total: compared down the column (R4)
        rows.add_column()  # « CC » or « charges ? », apart so the digits stay aligned
        rows.add_column()
        rows.add_column()
        rows.add_column()  # ×N sources (R12)
        rows.add_column(justify="right")  # position vs the Carte des loyers (ADR-0010)
        start = max(0, self.cursor - height // 2)
        for index, group in enumerate(self.groups[start : start + height], start=start):
            listing = group.primary
            is_new = not listing.opened
            unit = (
                Text("charges ?", style="italic")
                if listing.charges_unknown
                else Text("CC", style="dim")
            )
            style = " ".join(
                part for part, on in (("reverse", index == self.cursor), ("bold", is_new)) if on
            )
            rows.add_row(
                _SELECTED_MARK if index == self.cursor else " ",
                Text(_NEW_MARK, style="bold green") if is_new else Text(" "),
                Text(format_euros(listing.price.total)),
                unit,
                Text(format_size(listing)),
                Text(listing.location.city[:_CITY_WIDTH]),
                Text(f"×{len(group.sources)}", style="dim") if len(group.sources) > 1 else Text(""),
                _render_gap(listing),
                style=style,
            )
        return rows

    def _render_detail(self) -> RenderableType:
        group = self.find_current()
        if group is None:
            return Text("Rien à revoir.")
        listing = group.primary
        facts = Text.assemble(
            f"{format_size(listing)} · ",
            listing.floor.format_label() if listing.floor else "étage ?",
            " · DPE ",
            format_rating_badge(listing.dpe_rating),
            " GES ",
            format_rating_badge(listing.ges_rating),
        )
        money = (
            Text("loyer seul, charges ?", style="bold yellow")
            if listing.charges_unknown
            else Text(listing.price.format_display())
        )
        if per_m2 := format_per_m2(listing):
            money.append(f" · {per_m2}")
        money.append(f" · {_format_advertiser(listing)}")
        lines: list[RenderableType] = [facts, money, *_render_position(listing)]
        notes = [
            label
            for label, on in (
                ("Meublé", listing.furnished is True),
                ("Chauffage collectif", listing.collective_heating is True),
            )
            if on
        ]
        if notes:
            lines.append(Text(" · ".join(notes)))
        if ban := build_rental_ban_warning(listing.dpe_rating, self.today):
            lines.append(Text(ban, style="yellow"))
        if down := build_source_down_warning(listing.source_down_days):
            lines.append(Text(down, style="italic"))
        lines.append(Text(listing.title))
        meta = Text(f"{listing.source} · ")
        meta.append_text(format_published_cell(listing))
        if listing.images:
            meta.append(f" · {_format_count(len(listing.images), 'photo')}")
        if group.has_duplicates:
            meta.append(f" · aussi sur {', '.join(other.source for other in group.others)}")
        lines.append(meta)
        if listing.opened_at:
            lines.append(Text(format_opened_label(listing.opened_at), style="dim"))
        if listing.former_dismissal:
            lines.append(Text(listing.former_dismissal.format_mention(), style="italic"))
        if listing.restored_at:
            lines.append(Text(format_restored_label(listing.restored_at), style="dim"))
        lines.append(Text(listing.url, style="dim"))
        return Panel(
            Group(*lines), title=f"{listing.price.format_total()} · {listing.location.city}"
        )


def format_opened_label(opened_at: datetime) -> str:
    """« ouverte le 12/10/2026 »: the hunter has been through this home already."""
    return f"ouverte le {opened_at.strftime('%d/%m/%Y')}"


def format_suggestion_question(pending: PendingSuggestion) -> str:
    """« Suggestion pour « Annecy » : exclure Poisy ? 3 écarts « commune » ; masquerait
    aussi 2 logements non écartés. [o/N] »"""
    suggestion = pending.suggestion
    hidden = pending.hidden_too
    plural = "s" if hidden > 1 else ""
    cost = (
        f"masquerait aussi {_format_count(hidden, 'logement')} non écarté{plural}"
        if hidden
        else "ne masquerait aucun autre logement"
    )
    return (
        f"Suggestion pour « {pending.search_filter.name} » : {suggestion.proposal} ? "
        f"{suggestion.dismissal_count} écarts « {REASON_LABELS[suggestion.reason]} » ; "
        f"{cost}. [o/N]"
    )


def compute_next_sort(current: ListingSort) -> ListingSort:
    """position → €/m² → parution → position."""
    return _REVIEW_SORTS[(_REVIEW_SORTS.index(current) + 1) % len(_REVIEW_SORTS)]


def _render_gap(listing: Listing) -> Text:
    """Bold only outside the interval: inside, the % ranks but proves nothing."""
    position = listing.market_position
    outside = isinstance(position, MarketPosition) and position.is_outside_range
    return Text(position.format_gap(), style="bold" if outside else "dim")


def _render_position(listing: Listing) -> list[RenderableType]:
    """The position, then the reference it was measured against, when there is one."""
    position = listing.market_position
    lines: list[RenderableType] = [Text(f"Position : {position.format_label()}")]
    if isinstance(position, MarketPosition):
        lines.append(Text(f"Réf. {position.reference.format_detail()}", style="dim"))
    return lines


@dataclass
class DismissedScreen:
    """`hunt review --dismissed`: the dismissals in force, each one restorable."""

    dismissals: list[Dismissal]
    cursor: int = 0
    message: str = ""

    def find_current(self) -> Dismissal | None:
        if not self.dismissals:
            return None
        self.cursor = max(0, min(self.cursor, len(self.dismissals) - 1))
        return self.dismissals[self.cursor]

    def render(self, height: int) -> RenderableType:
        header = (
            f"hunt review --dismissed · {_format_count(len(self.dismissals), 'logement')} écarté"
        )
        header += "s" if len(self.dismissals) > 1 else ""
        return _render_split(
            header, self._render_list(height), self._render_detail(), self.message, _DISMISSED_HELP
        )

    def _render_list(self, height: int) -> RenderableType:
        rows = Table.grid(padding=(0, 1))
        rows.add_column()
        rows.add_column(justify="right")
        rows.add_column()
        rows.add_column()
        start = max(0, self.cursor - height // 2)
        for index, dismissal in enumerate(self.dismissals[start : start + height], start=start):
            selected = index == self.cursor
            rows.add_row(
                _SELECTED_MARK if selected else " ",
                Text(f"{format_euros(dismissal.total_price)} CC"),
                Text(_format_dismissed_city(dismissal)[:_CITY_WIDTH]),
                Text(REASON_LABELS[dismissal.reason], style="dim"),
                style="reverse" if selected else "",
            )
        return rows

    def _render_detail(self) -> RenderableType:
        dismissal = self.find_current()
        if dismissal is None:
            return Text("Aucun logement écarté.")
        reason = REASON_LABELS[dismissal.reason]
        if dismissal.note:
            reason += f" : {dismissal.note}"
        lines = [
            Text(f"écarté le {dismissal.dismissed_at:%d/%m/%Y} · {reason}"),
            Text(_format_snapshot(dismissal)),
        ]
        return Panel(
            Group(*lines),
            title=f"{format_euros(dismissal.total_price)} CC · {_format_dismissed_city(dismissal)}",
        )


def _format_snapshot(dismissal: Dismissal) -> str:
    """What the hunter saw when they dismissed it: surface, storey, DPE, who, where."""
    parts = [
        f"{dismissal.surface_m2:.0f}\u202fm²" if dismissal.surface_m2 else "",
        f"étage {dismissal.floor_level}" if dismissal.floor_level is not None else "",
        f"DPE {dismissal.dpe_rating.value}" if dismissal.dpe_rating else "",
        dismissal.advertiser or "",
        dismissal.source,
    ]
    return " · ".join(part for part in parts if part)


def _format_dismissed_city(dismissal: Dismissal) -> str:
    """The home key keeps the commune folded to lower case; give it back its capitals."""
    return dismissal.home_key.city.title() if dismissal.home_key else "commune ?"


def read_key() -> str:
    """One keystroke, without waiting for Enter. An arrow comes back as its sequence."""
    descriptor = sys.stdin.fileno()
    previous = termios.tcgetattr(descriptor)
    try:
        tty.setraw(descriptor)
        return os.read(descriptor, _KEY_READ_BYTES).decode(errors="ignore")
    finally:
        termios.tcsetattr(descriptor, termios.TCSADRAIN, previous)


def ask_reason() -> tuple[DismissalReason, str] | None:
    """The reason is mandatory: any key outside the list cancels the dismissal."""
    key = read_key()
    if key not in REASON_KEYS:
        return None
    reason = REASON_KEYS[key][0]
    note = (
        console.input("Texte libre (Entrée pour vide) : ")
        if reason is DismissalReason.OTHER
        else ""
    )
    return reason, note


def _compute_cursor(key: str, cursor: int) -> int:
    if key in _NEXT_KEYS:
        return cursor + 1
    if key in _PREVIOUS_KEYS:
        return max(0, cursor - 1)
    return cursor


def _render_to_terminal(screen: ReviewScreen | DismissedScreen) -> None:
    console.clear()
    console.print(screen.render(max(1, console.size.height - _CHROME_LINES)))


async def run_review(container: Container, search_filter: SearchFilter) -> None:
    if not sys.stdin.isatty():
        console.print(_NOT_A_TERMINAL)
        return
    get_top = container.make_get_top_use_case()
    dismiss = container.make_dismiss_use_case()
    restore = container.make_restore_use_case()
    open_home = container.make_open_home_use_case()
    suggest = container.make_suggest_criteria_use_case()
    screen = ReviewScreen(search_filter, [])

    async def load_homes() -> None:
        screen.groups = await get_top.execute(
            search_filter, search_filter.max_results, sort=screen.sort
        )

    await load_homes()
    last_dismissed: Listing | None = None

    while True:
        _render_to_terminal(screen)
        key = read_key()
        group = screen.find_current()
        screen.message = ""
        if key in _QUIT_KEYS:
            return
        screen.cursor = _compute_cursor(key, screen.cursor)
        if key == _SWITCH_VIEW_KEY:
            if not await run_dismissed_review(container):
                return
            await load_homes()
        elif key == _OPEN_KEY and group:
            webbrowser.open(group.primary.url)
            await open_home.execute(group.primary)
            await load_homes()
            screen.message = f"Ouvert dans le navigateur : {format_home_label(group.primary)}"
        elif key == _DISMISS_KEY and group:
            screen.asking_reason = True
            _render_to_terminal(screen)
            answer = ask_reason()
            screen.asking_reason = False
            if answer is None:
                screen.message = "Écart annulé : la raison est obligatoire."
                continue
            await dismiss.execute(group.primary, *answer)
            last_dismissed = group.primary
            await load_homes()
            screen.message = (
                f"Écarté : {format_home_label(group.primary)} ({REASON_LABELS[answer[0]]})"
                f" · {_UNDO_KEY} pour annuler"
            )
            # Asked right after the dismissal that tipped it, never applied unasked.
            for pending in await suggest.find_suggestions(group.primary):
                screen.message = format_suggestion_question(pending)
                _render_to_terminal(screen)
                if read_key() == _ACCEPT_KEY:
                    await suggest.apply_suggestion(pending)
                    revised = pending.suggestion.revised_filter
                    if revised.id == search_filter.id:
                        search_filter = screen.search_filter = revised
                    await load_homes()
                    screen.message = (
                        f"Filtre « {revised.name} » modifié : {pending.suggestion.proposal}."
                    )
                else:
                    await suggest.save_refusal(pending)
                    screen.message = (
                        f"Suggestion refusée : reposée après {SUGGESTION_THRESHOLD} nouveaux"
                        " écarts pour cette raison."
                    )
        elif key == _UNDO_KEY:
            if last_dismissed is None:
                screen.message = "Rien à annuler."
                continue
            await restore.execute(last_dismissed.id)
            await load_homes()
            screen.message = f"Écart annulé : {format_home_label(last_dismissed)}"
            last_dismissed = None
        elif key == _SORT_KEY:
            screen.sort = compute_next_sort(screen.sort)
            screen.cursor = 0
            await load_homes()
            screen.message = f"Trié par {_SORT_LABELS[screen.sort]}"


async def run_dismissed_review(container: Container) -> bool:
    """The dismissed view. True when the hunter pressed `d` for the review, False on quit."""
    if not sys.stdin.isatty():
        console.print(_NOT_A_TERMINAL)
        return False
    list_dismissed = container.make_list_dismissed_use_case()
    restore = container.make_restore_use_case()
    screen = DismissedScreen(await list_dismissed.execute())

    while True:
        _render_to_terminal(screen)
        key = read_key()
        dismissal = screen.find_current()
        screen.message = ""
        if key in _QUIT_KEYS:
            return False
        if key == _SWITCH_VIEW_KEY:
            return True
        screen.cursor = _compute_cursor(key, screen.cursor)
        if key in _RESTORE_KEYS and dismissal:
            await restore.execute(dismissal.listing_id)
            screen.dismissals = await list_dismissed.execute()
            screen.message = (
                f"Restauré : {format_euros(dismissal.total_price)} CC · "
                f"{_format_dismissed_city(dismissal)}"
            )
