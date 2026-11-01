import asyncio
import os
from datetime import datetime, timedelta
from typing import Annotated

import typer
from rich.prompt import Confirm

from ...application.use_cases import WatchReport
from ...domain.entities import DEFAULT_RADIUS_KM, MIN_INTERVAL_MINUTES, SearchFilter
from ...domain.value_objects import SiteRules
from ...infrastructure.container import Container
from ..web.request_guard import SERVE_HOST_ENV
from .adhoc import AdHocCriteria
from .filter_wizard import ask_filter
from .formatters import console, print_filter_summary, print_listings
from .review import run_dismissed_review, run_review
from .session import open_container, setup_logging

app = typer.Typer(
    name="hunt", help="Apartment Hunter — find your next rental", add_completion=False
)
filter_app = typer.Typer(help="Manage search filters")
app.add_typer(filter_app, name="filter")
rules_app = typer.Typer(
    help="Whether crawls follow robots.txt and the sites' terms (shared with the web page)",
    invoke_without_command=True,
)
app.add_typer(rules_app, name="rules")

_DEFAULT_SERVE_HOST = "127.0.0.1"
_DEFAULT_SERVE_PORT = 8080


def _pick_filter(filters: list[SearchFilter], filter_name: str | None) -> SearchFilter:
    """The named filter, or the first saved one when no name was given."""
    if not filters:
        console.print(
            "[red]No filters configured. Run: hunt filter add "
            "(or pass --city for an ad-hoc search)[/]"
        )
        raise typer.Exit(1)
    if not filter_name:
        return filters[0]
    matches = [f for f in filters if f.name.lower() == filter_name.lower()]
    if not matches:
        console.print(f"[red]Filter '{filter_name}' not found[/]")
        raise typer.Exit(1)
    return matches[0]


def _reject_short_interval(flag: str, minutes: int | None) -> None:
    """A watch override below the minimum would re-crawl every tick — refuse it.

    The flags bypass `SearchFilter`, so its bounds can't protect the loop here.
    """
    if minutes is not None and minutes < MIN_INTERVAL_MINUTES:
        console.print(f"[red]{flag} must be at least {MIN_INTERVAL_MINUTES} minutes[/]")
        raise typer.Exit(1)


async def _run_search_cycle(
    container: Container,
    search_filter: SearchFilter,
    limit: int | None = None,
    skip_purge: bool = False,
) -> None:
    saved = await container.make_manage_filters_use_case().list_all()

    # Ad-hoc searches aren't in the saved keep-set, so purging against one would drop
    # almost everything — the refresh use case is told not to purge at all.
    refresh = container.make_refresh_use_case()
    outcome = await refresh.execute(search_filter, saved, purge=not skip_purge)

    msg = f"[dim]Fetched — {outcome.new_count} new listings saved"
    if outcome.purged_count:
        msg += f", {outcome.purged_count} stale removed"
    console.print(msg + "[/]")

    get_top = container.make_get_top_use_case()
    listings = await get_top.execute(search_filter, limit=limit or search_filter.max_results)
    print_listings(listings, search_filter)


@app.command()
def search(
    filter_name: Annotated[
        str | None, typer.Option("--filter", "-f", help="Saved filter name to use")
    ] = None,
    limit: Annotated[
        int | None,
        typer.Option("--limit", "-n", help="Max results (default: filter's max_results)"),
    ] = None,
    # ── Ad-hoc filter flags (mirror the web "Modifier le filtre" form) ──
    # Passing --city builds a throwaway filter and ignores saved ones; nothing is saved.
    city: Annotated[
        str | None,
        typer.Option(
            "--city",
            "-c",
            help="Villes (comma-separated). Given → ad-hoc search, ignores saved filters",
        ),
    ] = None,
    radius: Annotated[float, typer.Option("--radius", help="Rayon (km)")] = DEFAULT_RADIUS_KM,
    exclude: Annotated[
        str | None, typer.Option("--exclude", help="Villes exclues (comma-separated)")
    ] = None,
    min_price: Annotated[int | None, typer.Option("--min-price", help="Prix min (€/mois)")] = None,
    max_price: Annotated[int | None, typer.Option("--max-price", help="Prix max (€/mois)")] = None,
    min_surface: Annotated[
        float | None, typer.Option("--min-surface", help="Surface min (m²)")
    ] = None,
    min_rooms: Annotated[int | None, typer.Option("--min-rooms", help="Pièces min")] = None,
    max_rooms: Annotated[int | None, typer.Option("--max-rooms", help="Pièces max")] = None,
    furnished: Annotated[
        bool | None,
        typer.Option("--furnished/--unfurnished", help="Meublé / non meublé (défaut: peu importe)"),
    ] = None,
    no_ground_floor: Annotated[
        bool, typer.Option("--no-ground-floor", help="Exclure rez-de-chaussée")
    ] = False,
    no_first_floor: Annotated[
        bool, typer.Option("--no-first-floor", help="Exclure 1er étage")
    ] = False,
    top_floor: Annotated[
        bool, typer.Option("--top-floor", help="Dernier étage uniquement")
    ] = False,
    dpe: Annotated[
        str | None,
        typer.Option(
            "--dpe",
            help=(
                "DPE acceptés, lettres séparées par virgules (ex: A,B,C,D). Vide = aucun filtre DPE"
            ),
        ),
    ] = None,
) -> None:
    """One-shot: crawl all sources and display matching listings.

    With no --city, uses a saved filter (first, or --filter NAME). With --city,
    builds an ad-hoc filter from the flags below — handy to test criteria from the
    terminal without saving anything.
    """
    setup_logging()

    adhoc = (
        AdHocCriteria(
            city=city,
            radius_km=radius,
            excluded=exclude,
            min_price=min_price,
            max_price=max_price,
            min_surface_m2=min_surface,
            min_rooms=min_rooms,
            max_rooms=max_rooms,
            furnished=furnished,
            exclude_ground_floor=no_ground_floor,
            exclude_first_floor=no_first_floor,
            top_floor_only=top_floor,
            dpe=dpe,
            limit=limit,
        )
        if city
        else None
    )

    async def _run() -> None:
        async with open_container() as container:
            if adhoc:
                target = adhoc.to_filter()
                print_filter_summary(target)
                await _run_search_cycle(container, target, limit=limit, skip_purge=True)
                return

            manage = container.make_manage_filters_use_case()
            target = _pick_filter(await manage.list_all(), filter_name)
            print_filter_summary(target)
            await _run_search_cycle(container, target, limit=limit)

    asyncio.run(_run())


@app.command()
def watch(
    filter_name: Annotated[str | None, typer.Option("--filter", "-f")] = None,
    interval: Annotated[
        int | None,
        typer.Option("--interval", "-i", help="Override notification interval (minutes)"),
    ] = None,
    refresh: Annotated[
        int | None, typer.Option("--refresh", "-r", help="Override auto-refresh interval (minutes)")
    ] = None,
) -> None:
    """Polling mode: re-crawl on the refresh interval, notify on the notification interval."""
    setup_logging()
    _reject_short_interval("--interval", interval)
    _reject_short_interval("--refresh", refresh)

    async def _run() -> None:
        async with open_container() as container:
            manage = container.make_manage_filters_use_case()
            # full keep-set for purge — never drop another filter's listings
            saved = await manage.list_all()
            filters = [f for f in saved if f.enabled]

            if not filters:
                console.print("[red]No active filters. Run: hunt filter add[/]")
                raise typer.Exit(1)

            if filter_name:
                filters = [f for f in filters if f.name.lower() == filter_name.lower()]
                if not filters:
                    console.print(f"[red]Filter '{filter_name}' not found[/]")
                    raise typer.Exit(1)

            console.print(f"[green]Watching {len(filters)} filter(s). Ctrl+C to stop.[/]")
            await _watch_loop(container, filters, interval, refresh)

    asyncio.run(_run())


async def _watch_loop(
    container: Container,
    filters: list[SearchFilter],
    interval: int | None,
    refresh: int | None,
) -> None:
    """Watch until interrupted, reporting each pass in the terminal.

    The schedule, the purge and the recovery from a failing crawler live in the watch
    policy. This loop used to hold its own copy — which, unlike the web's, had no error
    branch at all, so one crawler raising stopped the watch for every filter.
    """
    watch = container.make_watch_use_case(
        crawl_interval_minutes=refresh,
        alert_interval_minutes=interval,
    )
    watched_ids = [f.id for f in filters]
    try:
        while True:
            for report in await watch.run_pass(watched_ids):
                _print_watch_report(report)
            await asyncio.sleep(watch.compute_seconds_until_next_deadline())
    except (KeyboardInterrupt, asyncio.CancelledError):
        console.print("\n[yellow]Stopped.[/]")


def _print_watch_report(report: WatchReport) -> None:
    """One line per filter that actually did something — silence otherwise."""
    if report.is_quiet:
        return
    changes = []
    if report.new_count:
        changes.append(f"{report.new_count} new")
    if report.purged_count:
        changes.append(f"{report.purged_count} removed")
    if changes:
        console.print(f"[dim]{report.filter_name}: {', '.join(changes)}[/]")
    if report.notified:
        console.print(
            f"[green]Notified {report.notified} new listings for '{report.filter_name}'[/]"
        )


@app.command()
def review(
    filter_name: Annotated[
        str | None, typer.Option("--filter", "-f", help="Saved filter name to review")
    ] = None,
    dismissed: Annotated[
        bool, typer.Option("--dismissed", help="Open on the dismissed homes; u restores one")
    ] = False,
) -> None:
    """Review a filter's homes in the terminal; dismiss one with a keystroke."""
    setup_logging()

    async def _run() -> None:
        async with open_container() as container:
            if dismissed and not await run_dismissed_review(container):
                return
            filters = await container.make_manage_filters_use_case().list_all()
            await run_review(container, _pick_filter(filters, filter_name))

    asyncio.run(_run())


_DEFAULT_UNSEEN_DAYS = 7


@app.command()
def clean(
    unseen_days: Annotated[
        int,
        typer.Option(
            "--unseen-days",
            min=0,
            help="Also drop listings no crawl has returned for this many days (0 = all)",
        ),
    ] = _DEFAULT_UNSEEN_DAYS,
    cache: Annotated[
        bool,
        typer.Option("--cache", help="Also delete the downloaded Carte des loyers"),
    ] = False,
    yes: Annotated[bool, typer.Option("--yes", "-y", help="Skip the confirmation")] = False,
) -> None:
    """Drop stale listings: those no saved filter wants, and those no crawl sees any more."""
    setup_logging()

    async def _run() -> None:
        async with open_container() as container:
            cleaner = container.make_clean_use_case()
            stale = await cleaner.find_stale(datetime.now() - timedelta(days=unseen_days))
            console.print(
                f"{len(stale.irrelevant)} annonce(s) hors de tout filtre, "
                f"{len(stale.unseen)} non revue(s) depuis {unseen_days} j."
            )
            if stale.total and (yes or Confirm.ask("Les supprimer ?", default=False)):
                deleted = await cleaner.delete(stale)
                console.print(
                    f"[green]{deleted} annonce(s) supprimée(s).[/] "
                    "Les logements écartés ou ouverts restent mémorisés."
                )
            if cache:
                container.rent_references.delete_downloads()
                console.print("Carte des loyers effacée, retéléchargée au prochain besoin.")

    asyncio.run(_run())
    console.print(
        "[dim]Les caches en mémoire (géocodage, pages détail, robots.txt) vivent dans "
        "chaque processus : redémarrer `hunt serve` les vide.[/]"
    )


@filter_app.command("add")
def add_filter() -> None:
    """Interactive wizard to add a search filter."""
    setup_logging()
    console.print("[bold blue]New Search Filter Wizard[/]\n")

    search_filter = ask_filter()
    print_filter_summary(search_filter)
    if not Confirm.ask("Save this filter?", default=True):
        return

    async def _save() -> None:
        async with open_container() as container:
            await container.make_manage_filters_use_case().save(search_filter)
        console.print(f"[green]Filter '[bold]{search_filter.name}[/]' saved.[/]")

    asyncio.run(_save())


@filter_app.command("list")
def list_filters() -> None:
    """List all saved filters."""
    setup_logging()

    async def _run() -> None:
        async with open_container() as container:
            filters = await container.make_manage_filters_use_case().list_all()

        if not filters:
            console.print("[yellow]No filters yet. Run: hunt filter add[/]")
            return

        for f in filters:
            status = "[green]●[/]" if f.enabled else "[red]○[/]"
            console.print(
                f"{status} [{f.id}] [bold]{f.name}[/] — {', '.join(f.cities)} "
                f"±{f.radius_km}km — refresh {f.refresh_interval_minutes}min, "
                f"notify {f.notification_interval_minutes}min"
            )

    asyncio.run(_run())


@filter_app.command("delete")
def delete_filter(filter_id: str) -> None:
    """Delete a filter by ID."""
    setup_logging()

    async def _run() -> None:
        async with open_container() as container:
            await container.make_manage_filters_use_case().delete(filter_id)
        console.print(f"[green]Filter '{filter_id}' deleted.[/]")

    asyncio.run(_run())


_SITE_RULES_LABELS = {
    SiteRules.HONOURED: "respectées : robots.txt et les conditions d'utilisation des sites",
    SiteRules.IGNORED: "ignorées : robots.txt et les conditions d'utilisation des sites",
}
_IGNORE_WARNING = (
    "Bien'ici, Locservice, FNAIM et 2A Immobilier interdisent l'extraction automatique de "
    "leurs annonces, et robots.txt ferme des pages de PAP et de Foncia. En ignorant ces "
    "règles, vous en êtes seul responsable. Les protections anti-bot restent respectées."
)


def _save_site_rules(rules: SiteRules) -> None:
    async def _run() -> None:
        async with open_container() as container:
            await container.make_site_rules_use_case().save_site_rules(rules)

    asyncio.run(_run())
    console.print(f"Règles des sites {_SITE_RULES_LABELS[rules]}, dès la prochaine recherche.")


@rules_app.callback()
def print_rules(ctx: typer.Context) -> None:
    """Show the current choice (ADR-0012)."""
    if ctx.invoked_subcommand is not None:
        return
    setup_logging()

    async def _run() -> SiteRules:
        async with open_container() as container:
            return await container.make_site_rules_use_case().load_site_rules()

    console.print(f"Règles des sites {_SITE_RULES_LABELS[asyncio.run(_run())]}.")


@rules_app.command("ignore")
def ignore_rules(
    yes: Annotated[bool, typer.Option("--yes", "-y", help="Skip the confirmation")] = False,
) -> None:
    """Set robots.txt and the sites' terms aside, at your own risk."""
    setup_logging()
    console.print(f"[yellow]{_IGNORE_WARNING}[/]")
    if not yes and not Confirm.ask("Ignorer les règles des sites ?", default=False):
        console.print("Rien n'a changé.")
        return
    _save_site_rules(SiteRules.IGNORED)


@rules_app.command("honour")
def save_honoured_rules() -> None:
    """Follow robots.txt and the sites' terms again (the default)."""
    setup_logging()
    _save_site_rules(SiteRules.HONOURED)


@app.command()
def serve(
    host: Annotated[str, typer.Option("--host", help="Bind host")] = _DEFAULT_SERVE_HOST,
    port: Annotated[int, typer.Option("--port", "-p", help="Port")] = _DEFAULT_SERVE_PORT,
    reload: Annotated[bool, typer.Option("--reload", help="Hot-reload (dev mode)")] = False,
) -> None:
    """Launch the local web interface."""
    setup_logging()
    try:
        import uvicorn
    except ImportError:
        console.print("[red]uvicorn not installed. Run: uv add uvicorn[standard][/]")
        raise typer.Exit(1) from None

    os.environ[SERVE_HOST_ENV] = host
    console.print(f"[green]Web interface → http://{host}:{port}[/]")
    console.print("[dim]Ctrl+C to stop[/]")
    uvicorn.run(
        "apartment_hunter.presentation.web.app:app",
        host=host,
        port=port,
        reload=reload,
        log_level="warning",
    )


if __name__ == "__main__":
    app()
