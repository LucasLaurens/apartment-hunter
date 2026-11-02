"""A clock the test moves by hand — no real waiting anywhere."""

from apartment_hunter.domain.ports import ClockPort


class ManualClock(ClockPort):
    """Time only advances when the test says so, or when something sleeps on it.

    A sleep is recorded and applied instantly, so a whole simulated afternoon of
    watching runs in microseconds and the test can assert *how long* the loop chose to
    wait — which is the part of the watch policy that matters.
    """

    def __init__(self, start: float = 0.0) -> None:
        self._now = start
        self.slept: list[float] = []

    def read_now_seconds(self) -> float:
        return self._now

    async def sleep(self, seconds: float) -> None:
        self.slept.append(seconds)
        self.advance(max(0.0, seconds))

    def advance(self, seconds: float) -> None:
        self._now += seconds
