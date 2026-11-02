from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from ...domain.entities import Listing, SearchFilter
from ...domain.services import (
    THERMAL_SIEVE_LABEL,
    ListingGroup,
    build_source_down_warning,
    is_thermal_sieve,
)
from ...domain.value_objects import DpeRating

console = Console()

_DPE_COLORS = {
    "A": "bright_green",
    "B": "green",
    "C": "yellow_green",
    "D": "yellow",
    "E": "orange3",
    "F": "orange_red1",
    "G": "red",
}


def format_published_cell(listing: Listing) -> Text:
    """Publication date, marked when it is only our first-seen fallback.

    A "vu" prefix keeps the two apart: sites like Century 21 or Laforêt publish no
    date, so showing their crawl time unmarked would read as a fresh listing.
    """
    cell = (
        Text(listing.format_published_label())
        if listing.has_site_publication_date
        else Text(f"vu {listing.format_published_label()}", style="dim italic")
    )
    if warning := build_source_down_warning(listing.source_down_days):
        cell.append(f"\n{warning}", style="dim italic")
    return cell


def format_price_cell(listing: Listing) -> Text:
    """Monthly total, marked when no charges are accounted for.

    The budget is reasoned charges included, so printing a rent-only total unmarked
    understates the real cost by roughly a tenth — same mark as the web card.
    """
    total = Text(listing.price.format_total())
    if listing.charges_unknown:
        total.append("\ncharges ?", style="dim italic")
    return total


def format_rating_badge(rating: DpeRating | None) -> Text:
    """Coloured A–G badge shared by the DPE and GES columns ('—' when unknown)."""
    if not rating:
        return Text("—")
    color = _DPE_COLORS.get(rating.value, "white")
    return Text(f" {rating.value} ", style=f"bold {color} on grey11")


def _format_duplicate_note(group: ListingGroup) -> str:
    """Which other sources carry this same home — one line, never a hidden listing."""
    if not group.has_duplicates:
        return ""
    others = ", ".join(listing.source for listing in group.others)
    return f"\n[dim]aussi sur {others}[/]"


def print_listings(groups: list[ListingGroup], search_filter: SearchFilter) -> None:
    if not groups:
        console.print(f"[yellow]No listings found for filter '[bold]{search_filter.name}[/]'[/]")
        return

    table = Table(
        title=f"Top {len(groups)} listings — {search_filter.name}",
        box=box.ROUNDED,
        show_lines=True,
        highlight=True,
    )

    table.add_column("#", style="dim", width=3, justify="right")
    table.add_column("Title / Link", min_width=30)
    table.add_column("Price", justify="right", style="bold green")
    table.add_column("Surface", justify="right")
    table.add_column("Rooms", justify="center")
    table.add_column("Floor", justify="center")
    table.add_column("DPE", justify="center")
    table.add_column("GES", justify="center")
    table.add_column("Location")
    table.add_column("Parution", style="dim")
    table.add_column("Source", style="dim")

    for i, group in enumerate(groups, 1):
        listing = group.primary
        dpe_text = format_rating_badge(listing.dpe_rating)
        ges_text = format_rating_badge(listing.ges_rating)

        floor_text = listing.floor.format_label() if listing.floor else "?"
        surface_text = f"{listing.surface_m2:.0f}m²" if listing.surface_m2 else "?"
        rooms_text = str(listing.rooms) if listing.rooms else "?"
        price_text = format_price_cell(listing)

        published = format_published_cell(listing)

        extras = []
        if listing.furnished:
            extras.append("🪑")
        if listing.collective_heating:
            extras.append("🔥")
        title_line = f"[link={listing.url}][blue]{listing.title}[/][/link]"
        if extras:
            title_line += " " + " ".join(extras)
        if is_thermal_sieve(listing.dpe_rating):
            title_line += f"\n[orange3]{THERMAL_SIEVE_LABEL}[/]"
        title_line += _format_duplicate_note(group)

        table.add_row(
            str(i),
            title_line,
            price_text,
            surface_text,
            rooms_text,
            floor_text,
            dpe_text,
            ges_text,
            listing.location.format_display(),
            published,
            listing.source,
        )

    console.print(table)


def print_filter_summary(search_filter: SearchFilter) -> None:
    lines = [
        f"[bold]Cities:[/] {', '.join(search_filter.cities)} ±{search_filter.radius_km}km",
    ]
    if search_filter.excluded_cities:
        lines.append(f"[bold]Excluded:[/] {', '.join(search_filter.excluded_cities)}")
    if search_filter.max_price:
        lines.append(
            f"[bold]Price:[/] {search_filter.min_price or 0}–{search_filter.max_price}€/mo"
        )
    if search_filter.min_surface_m2:
        lines.append(f"[bold]Surface:[/] {search_filter.min_surface_m2}m²+")
    if search_filter.min_rooms:
        lines.append(f"[bold]Rooms:[/] {search_filter.min_rooms}+")
    if search_filter.accepted_dpe_ratings:
        accepted = ", ".join(sorted(r.value for r in search_filter.accepted_dpe_ratings))
        lines.append(f"[bold]DPE acceptés:[/] {accepted}")
    flags = []
    if search_filter.exclude_ground_floor:
        flags.append("no ground floor")
    if search_filter.exclude_first_floor:
        flags.append("no 1st floor")
    if search_filter.top_floor_only:
        flags.append("top floor only")
    if search_filter.furnished is not None:
        flags.append("furnished" if search_filter.furnished else "unfurnished")
    if flags:
        lines.append(f"[bold]Flags:[/] {', '.join(flags)}")

    console.print(
        Panel("\n".join(lines), title=f"[bold]{search_filter.name}[/]", border_style="blue")
    )
