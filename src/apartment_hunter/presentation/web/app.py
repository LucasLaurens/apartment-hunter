"""FastAPI web interface for Apartment Hunter."""

import asyncio
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated, Any

from fastapi import FastAPI, HTTPException, Query, Request, Response, status
from fastapi.responses import HTMLResponse, JSONResponse
from loguru import logger
from starlette.middleware.base import RequestResponseEndpoint
from starlette.middleware.trustedhost import TrustedHostMiddleware

from ...application.use_cases import ListingNotFoundError
from ...application.use_cases.get_top_listings import EVERY_SOURCE, PAGE_SIZE
from ...domain.entities import FilterBoundError, SearchFilter
from ...domain.value_objects import ListingSort, SiteRules
from ...infrastructure.config import get_settings
from ...infrastructure.container import Container
from ..dismissal_reasons import REASON_KEYS
from .background_jobs import BackgroundJobs, SearchSummary
from .dismissal_payload import parse_dismissal
from .filter_payload import apply_payload, filter_from_payload, format_filter_error
from .request_guard import is_cross_site_write, list_allowed_hosts
from .serializers import (
    dismissal_to_dict,
    filter_area_to_dict,
    filter_map_to_dict,
    filter_to_dict,
    group_to_dict,
    unreachable_source_to_dict,
)
from .ui import render_html_page

_FILTER_ID_LENGTH = 8  # short enough to read in a URL, wide enough to stay unique
_AREA_PREVIEW_ID = "area-preview"  # never saved: the form's cities and radius, read once
_SOURCE_PARAM_MAX_LENGTH = 64  # a source name is one word; the URL is the hunter's to edit

# ── Global app state ──────────────────────────────────────────────────────────

_container: Container | None = None
_jobs = BackgroundJobs()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    global _container
    _container = Container(get_settings())
    await _container.repository.connect()
    logger.info("Web server started — container ready")
    yield
    _jobs.cancel_all()
    await _container.close()
    logger.info("Web server stopped")


app = FastAPI(title="Apartment Hunter", lifespan=lifespan)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=list_allowed_hosts())


@app.middleware("http")
async def reject_cross_site_writes(
    request: Request, call_next: RequestResponseEndpoint
) -> Response:
    """A form on another site must not delete a filter or clear a « Nouveau » mark."""
    headers = request.headers
    if is_cross_site_write(
        request.method,
        headers.get("host", ""),
        headers.get("origin"),
        headers.get("sec-fetch-site"),
    ):
        return JSONResponse({"detail": "Requête refusée"}, status_code=status.HTTP_403_FORBIDDEN)
    return await call_next(request)


# ── Helpers ───────────────────────────────────────────────────────────────────


def _get_container() -> Container:
    assert _container is not None, "Container not initialised"
    return _container


async def _find_filter(filter_id: str) -> SearchFilter:
    manage = _get_container().make_manage_filters_use_case()
    filters = await manage.list_all()
    target = next((f for f in filters if f.id == filter_id), None)
    if not target:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Filter '{filter_id}' not found"
        )
    return target


def _require_filter_id(body: dict[str, Any]) -> str:
    filter_id = body.get("filter_id")
    if not filter_id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "filter_id required")
    return str(filter_id)


async def _save_filter(search_filter: SearchFilter) -> dict[str, Any]:
    manage = _get_container().make_manage_filters_use_case()
    await manage.save(search_filter)
    return filter_to_dict(search_filter)


# ── Routes ────────────────────────────────────────────────────────────────────


@app.get("/", response_class=HTMLResponse)
async def render_index() -> str:
    return render_html_page()


@app.get("/api/filters")
async def list_filters() -> list[dict[str, Any]]:
    manage = _get_container().make_manage_filters_use_case()
    filters = await manage.list_all()
    return [filter_to_dict(f) for f in filters]


@app.post("/api/filters")
async def create_filter(body: dict[str, Any]) -> dict[str, Any]:
    try:
        new_id = str(uuid.uuid4())[:_FILTER_ID_LENGTH]
        return await _save_filter(filter_from_payload(new_id, body))
    except FilterBoundError as exc:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, format_filter_error(exc)
        ) from exc
    except Exception as exc:
        logger.error(f"Failed to create filter: {exc}")
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc


@app.put("/api/filters/{filter_id}")
async def update_filter(filter_id: str, body: dict[str, Any]) -> dict[str, Any]:
    try:
        stored = await _find_filter(filter_id)
        return await _save_filter(apply_payload(stored, body))
    except HTTPException:
        raise
    except FilterBoundError as exc:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, format_filter_error(exc)
        ) from exc
    except Exception as exc:
        logger.error(f"Failed to update filter {filter_id}: {exc}")
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc


@app.delete("/api/filters/{filter_id}")
async def delete_filter(filter_id: str) -> dict[str, str]:
    manage = _get_container().make_manage_filters_use_case()
    await manage.delete(filter_id)
    return {"status": "deleted"}


@app.get("/api/counts")
async def count_per_filter() -> dict[str, int]:
    """Return listing count per filter (all filters, concurrent).

    Counted with the filter's own `max_results`, the same cap the list view uses —
    a badge reading higher than the list it opens reads as a broken filter.
    """
    manage = _get_container().make_manage_filters_use_case()
    filters = await manage.list_all()

    async def _count_filter(f: SearchFilter) -> tuple[str, int]:
        try:
            get_top = _get_container().make_get_top_use_case()
            homes = await get_top.execute(f, limit=f.max_results)
            return f.id, len(homes)
        except Exception:
            return f.id, 0

    results = await asyncio.gather(*[_count_filter(f) for f in filters])
    return dict(results)


@app.get("/api/listings")
async def list_listings(
    filter_id: str,
    page: int = 1,
    sort: str | None = None,
    # Read back from the page's URL, so anyone can type it: bounded, and only ever compared.
    source: Annotated[str, Query(max_length=_SOURCE_PARAM_MAX_LENGTH)] = EVERY_SOURCE,
) -> dict[str, Any]:
    target = await _find_filter(filter_id)
    get_top = _get_container().make_get_top_use_case()
    listing_sort = ListingSort.from_value(sort)
    listing_page = await get_top.execute_paginated(
        target, page=page, sort=listing_sort, source=source
    )
    return {
        "items": [group_to_dict(group) for group in listing_page.groups],
        "total": listing_page.total,
        "source_counts": listing_page.source_counts,
        "last_searched_at": (
            listing_page.last_searched_at.isoformat() if listing_page.last_searched_at else None
        ),
        "unreachable_sources": [
            unreachable_source_to_dict(source) for source in listing_page.unreachable
        ],
        "page": listing_page.page,
        "page_size": PAGE_SIZE,
        "pages": listing_page.pages,
        # Echoed so the UI can show the order actually applied, not the one requested.
        "sort": listing_sort.value,
    }


@app.get("/api/filters/{filter_id}/map")
async def read_filter_map(filter_id: str) -> dict[str, Any]:
    """The homes of a filter by commune, placed by our own geocoding (ticket 14)."""
    target = await _find_filter(filter_id)
    return filter_map_to_dict(await _get_container().make_map_use_case().execute(target))


@app.get("/api/area")
async def read_area(cities: str, radius_km: float) -> dict[str, Any]:
    """Communes in radius of what the filter form holds, saved or not.

    Read through the form's own translator, so the bounds `SearchFilter` refuses (radius
    outside 1–150 km) are refused here too, before any geocoding call.
    """
    try:
        preview = filter_from_payload(_AREA_PREVIEW_ID, {"cities": cities, "radius_km": radius_km})
    except ValueError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from exc
    if not preview.cities:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Au moins une ville.")
    return filter_area_to_dict(await _get_container().make_map_use_case().find_area(preview))


@app.get("/api/settings/site-rules")
async def read_site_rules() -> dict[str, str]:
    rules = await _get_container().make_site_rules_use_case().load_site_rules()
    return {"rules": rules.value}


@app.put("/api/settings/site-rules")
async def update_site_rules(body: dict[str, Any]) -> dict[str, str]:
    """The hunter's choice for every crawl from the next one (ADR-0012)."""
    try:
        rules = SiteRules(str(body.get("rules")))
    except ValueError as exc:
        allowed = ", ".join(r.value for r in SiteRules)
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, f"rules: {allowed}") from exc
    await _get_container().make_site_rules_use_case().save_site_rules(rules)
    return {"rules": rules.value}


@app.get("/api/dismissal-reasons")
async def list_dismissal_reasons() -> list[dict[str, str]]:
    """The closed list, with the keys `hunt review` uses: one gesture for both screens."""
    return [
        {"key": key, "value": reason.value, "label": label}
        for key, (reason, label) in REASON_KEYS.items()
    ]


@app.post("/api/listings/{listing_id}/dismiss")
async def dismiss_listing(listing_id: str, body: dict[str, Any]) -> dict[str, str]:
    """Dismiss the home this listing advertises (ADR-0009): its duplicates go with it."""
    try:
        reason, note = parse_dismissal(body)
    except ValueError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from exc
    try:
        await _get_container().make_dismiss_use_case().execute_by_id(listing_id, reason, note)
    except ListingNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Annonce introuvable") from exc
    return {"status": "dismissed"}


@app.get("/api/dismissals")
async def list_dismissals() -> list[dict[str, Any]]:
    dismissals = await _get_container().make_list_dismissed_use_case().execute()
    return [dismissal_to_dict(dismissal) for dismissal in dismissals]


@app.delete("/api/dismissals/{listing_id}")
async def restore_listing(listing_id: str) -> dict[str, str]:
    """Undo and restore are one gesture: the dismissal stays as a trace, lifted."""
    await _get_container().make_restore_use_case().execute(listing_id)
    return {"status": "restored"}


@app.post("/api/listings/{listing_id}/opened")
async def mark_listing_opened(listing_id: str) -> dict[str, str]:
    """The hunter followed the listing's link: its home, duplicates included, is opened."""
    try:
        await _get_container().make_open_home_use_case().execute_by_id(listing_id)
    except ListingNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Annonce introuvable") from exc
    return {"status": "opened"}


async def _run_search(filter_id: str) -> SearchSummary:
    """Crawl + purge in the background so the HTTP request never blocks (no timeout).

    Results land in the DB as each source finishes; the UI polls /api/search/status
    and refreshes the (fast) DB-backed listing view meanwhile.
    """
    target = await _find_filter(filter_id)
    saved = await _get_container().make_manage_filters_use_case().list_all()
    outcome = (
        await _get_container()
        .make_refresh_use_case()
        .execute(
            target, saved, report=lambda progress: _jobs.save_source_progress(filter_id, progress)
        )
    )
    return SearchSummary(new_count=outcome.new_count, purged_count=outcome.purged_count)


@app.post("/api/search")
async def trigger_search(body: dict[str, Any]) -> dict[str, str]:
    filter_id = _require_filter_id(body)
    await _find_filter(filter_id)  # 404 if unknown

    if not _jobs.is_searching(filter_id):  # never start a second crawl for one filter
        _jobs.start_search(filter_id, lambda: _run_search(filter_id))
    return {"status": "searching"}


@app.get("/api/search/status")
async def read_search_status(filter_id: str) -> dict[str, Any]:
    return _jobs.read_search_status(filter_id)


@app.post("/api/watch/start")
async def start_watch(body: dict[str, Any]) -> dict[str, str]:
    filter_id = _require_filter_id(body)
    await _find_filter(filter_id)  # 404 if unknown

    if not _jobs.start_watch(filter_id, lambda: _watch_loop(filter_id)):
        return {"status": "already_watching"}
    logger.info(f"Watch started for filter {filter_id!r}")
    return {"status": "started"}


@app.post("/api/watch/stop")
async def stop_watch(body: dict[str, Any]) -> dict[str, str]:
    filter_id = _require_filter_id(body)
    _jobs.stop_watch(filter_id)
    logger.info(f"Watch stopped for filter {filter_id!r}")
    return {"status": "stopped"}


@app.get("/api/watch/status")
async def read_watch_status(filter_id: str) -> dict[str, bool]:
    return {"watching": _jobs.is_watching(filter_id)}


# ── Background watch ──────────────────────────────────────────────────────────


async def _watch_loop(filter_id: str) -> None:
    """Delegate to the watch policy — the schedule, the purge and the backoff live there.

    This function used to hold its own copy of that policy, which had drifted from the
    CLI's copy in three ways. What is left here is what belongs to the web adapter:
    which filter to watch, and the task that carries it.
    """
    await _get_container().make_watch_use_case().run_forever([filter_id])
