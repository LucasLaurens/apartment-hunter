"""The watch policy: when to re-crawl, when to alert, what to do when it breaks.

Both entry points held their own copy of this loop, and the copies had drifted three
ways: the CLI had no error branch at all, so one crawler raising stopped the watch for
every filter; the CLI captured its filters once, so an edit mid-watch was ignored until
restart; and the two disagreed on what the crawl received.

The clock is a dependency, which is what makes the policy testable: a whole simulated
afternoon runs in a few milliseconds, and a test can assert *when* things happened.
"""

from dataclasses import dataclass

from loguru import logger

from ...domain.entities import SearchFilter
from ...domain.ports import ClockPort
from .manage_filters import ManageFilters
from .notify_new_listings import NotifyNewListings
from .refresh_filter import RefreshFilter, RefreshOutcome

SECONDS_PER_MINUTE = 60
# How long to wait before trying again after a cycle raised. Long enough that a site
# blocking us is not hammered, short enough that a transient failure costs one cycle.
ERROR_BACKOFF_SECONDS = 60.0
# Floor on the sleep between two passes, so a filter whose deadline is already past
# cannot spin the loop.
MIN_SLEEP_SECONDS = 1.0


@dataclass(frozen=True)
class WatchReport:
    """What one pass did for one filter — the entry points turn this into text."""

    filter_name: str
    crawled: bool
    new_count: int
    purged_count: int
    notified: int

    @property
    def is_quiet(self) -> bool:
        return not (self.new_count or self.purged_count or self.notified)


@dataclass
class _Deadlines:
    """When this filter is next due to be crawled, and next due to alert."""

    next_crawl_at: float
    next_alert_at: float


class WatchFilters:
    def __init__(
        self,
        refresh: RefreshFilter,
        notify: NotifyNewListings,
        manage: ManageFilters,
        clock: ClockPort,
        crawl_interval_minutes: int | None = None,
        alert_interval_minutes: int | None = None,
    ):
        self._refresh = refresh
        self._notify = notify
        self._manage = manage
        self._clock = clock
        self._crawl_override = crawl_interval_minutes
        self._alert_override = alert_interval_minutes
        self._deadlines: dict[str, _Deadlines] = {}

    async def run_pass(self, filter_ids: list[str]) -> list[WatchReport]:
        """Do whatever is due right now, and report it.

        The filters are re-read from storage on every pass, so editing a filter takes
        effect without restarting the watch — the behaviour the web loop had and the
        CLI loop did not.
        """
        saved = await self._manage.list_all()
        watched = [f for f in saved if f.id in set(filter_ids)]
        now = self._clock.read_now_seconds()
        return [await self._run_one(target, saved, now) for target in watched]

    async def run_forever(self, filter_ids: list[str]) -> None:
        """Watch until cancelled. A failing pass costs a backoff, never the loop."""
        while True:
            try:
                for report in await self.run_pass(filter_ids):
                    if not report.is_quiet:
                        logger.info(
                            f"[watch] {report.filter_name}: {report.new_count} new, "
                            f"{report.purged_count} removed, {report.notified} alerted"
                        )
                await self._clock.sleep(self.compute_seconds_until_next_deadline())
            except Exception as exc:
                logger.error(f"[watch] pass failed: {exc}")
                await self._clock.sleep(ERROR_BACKOFF_SECONDS)

    def compute_seconds_until_next_deadline(self) -> float:
        """How long the loop may sleep before something is due again."""
        if not self._deadlines:
            return MIN_SLEEP_SECONDS
        soonest = min(
            deadline
            for entry in self._deadlines.values()
            for deadline in (entry.next_crawl_at, entry.next_alert_at)
        )
        return max(MIN_SLEEP_SECONDS, soonest - self._clock.read_now_seconds())

    async def _run_one(
        self, target: SearchFilter, saved: list[SearchFilter], now: float
    ) -> WatchReport:
        deadlines = self._deadlines.setdefault(
            target.id, _Deadlines(next_crawl_at=now, next_alert_at=now)
        )
        outcome = RefreshOutcome(new_count=0, purged_count=0)
        crawled = now >= deadlines.next_crawl_at
        if crawled:
            outcome = await self._refresh.execute(target, saved)
            deadlines.next_crawl_at = (
                now + self._resolve_crawl_interval(target) * SECONDS_PER_MINUTE
            )

        notified = 0
        if now >= deadlines.next_alert_at:
            notified = await self._notify.execute(target)
            deadlines.next_alert_at = (
                now + self._resolve_alert_interval(target) * SECONDS_PER_MINUTE
            )

        return WatchReport(
            filter_name=target.name,
            crawled=crawled,
            new_count=outcome.new_count,
            purged_count=outcome.purged_count,
            notified=notified,
        )

    def _resolve_crawl_interval(self, target: SearchFilter) -> int:
        return self._crawl_override or target.refresh_interval_minutes

    def _resolve_alert_interval(self, target: SearchFilter) -> int:
        return self._alert_override or target.notification_interval_minutes
