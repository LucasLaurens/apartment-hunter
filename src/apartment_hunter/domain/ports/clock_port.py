from abc import ABC, abstractmethod


class ClockPort(ABC):
    """Reading the time and waiting, as a dependency rather than a global.

    The watch loop's whole behaviour is *when* it does things, so a test that cannot
    control the clock has to either sleep for real or patch `asyncio.sleep` from the
    outside. Both were the reason the loop had no test at all.
    """

    @abstractmethod
    def read_now_seconds(self) -> float:
        """A monotonic reading in seconds — comparable to itself, not to a wall clock."""

    @abstractmethod
    async def sleep(self, seconds: float) -> None:
        """Yield for `seconds`. A non-positive duration returns at once."""
