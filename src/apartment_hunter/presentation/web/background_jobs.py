"""Crawl and watch tasks running behind the HTTP requests that started them.

Keeping them in one object (instead of four module-level dicts) means a task, its
state and its result are created and dropped together, and the routes only ask
questions like "is this filter already searching?".
"""

import asyncio
from collections.abc import Callable, Coroutine
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from loguru import logger

from ...application.use_cases import SourceProgress

type SearchJob = Callable[[], Coroutine[Any, Any, SearchSummary]]
type WatchJob = Callable[[], Coroutine[Any, Any, None]]


class SearchState(StrEnum):
    IDLE = "idle"
    SEARCHING = "searching"
    DONE = "done"


@dataclass(frozen=True)
class SearchSummary:
    new_count: int
    purged_count: int


class BackgroundJobs:
    """One crawl and one watch loop at most per filter id."""

    def __init__(self) -> None:
        self._search_tasks: dict[str, asyncio.Task[None]] = {}
        self._search_states: dict[str, SearchState] = {}
        self._search_results: dict[str, SearchSummary] = {}
        self._search_sources: dict[str, dict[str, SourceProgress]] = {}
        self._watch_tasks: dict[str, asyncio.Task[None]] = {}

    # ── Searches ──────────────────────────────────────────────────────────────

    def is_searching(self, filter_id: str) -> bool:
        return self._search_states.get(filter_id) is SearchState.SEARCHING

    def start_search(self, filter_id: str, search: SearchJob) -> None:
        """Run `search` detached so the HTTP request returns before the crawl ends."""
        self._search_states[filter_id] = SearchState.SEARCHING
        self._search_results.pop(filter_id, None)
        self._search_sources[filter_id] = {}
        self._search_tasks[filter_id] = asyncio.create_task(self._run_search(filter_id, search))

    async def _run_search(self, filter_id: str, search: SearchJob) -> None:
        try:
            self._search_results[filter_id] = await search()
            self._search_states[filter_id] = SearchState.DONE
        except Exception as exc:
            logger.error(f"Search failed for filter {filter_id}: {exc}")
            self._search_states[filter_id] = SearchState.IDLE

    def save_source_progress(self, filter_id: str, progress: SourceProgress) -> None:
        """The latest word from one source of this filter's running search (W3)."""
        self._search_sources.setdefault(filter_id, {})[progress.source] = progress

    def read_search_status(self, filter_id: str) -> dict[str, Any]:
        state = self._search_states.get(filter_id, SearchState.IDLE)
        summary = self._search_results.get(filter_id)
        sources = self._search_sources.get(filter_id, {})
        status: dict[str, Any] = {
            "status": state.value,
            "sources": [
                {"source": p.source, "state": p.state.value, "count": p.count}
                for p in sorted(sources.values(), key=lambda p: p.source)
            ],
        }
        if summary:
            status["new_count"] = summary.new_count
            status["purged_count"] = summary.purged_count
        return status

    # ── Watches ───────────────────────────────────────────────────────────────

    def is_watching(self, filter_id: str) -> bool:
        task = self._watch_tasks.get(filter_id)
        return task is not None and not task.done()

    def start_watch(self, filter_id: str, watch: WatchJob) -> bool:
        """Start the watch loop; False when one is already running for this filter."""
        if self.is_watching(filter_id):
            return False
        self._watch_tasks[filter_id] = asyncio.create_task(watch())
        return True

    def stop_watch(self, filter_id: str) -> None:
        task = self._watch_tasks.pop(filter_id, None)
        if task and not task.done():
            task.cancel()

    def cancel_all(self) -> None:
        for task in list(self._watch_tasks.values()):
            task.cancel()
        self._watch_tasks.clear()
