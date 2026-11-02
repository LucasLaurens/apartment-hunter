"""The real clock — asyncio's monotonic time and its sleep."""

import asyncio

from ..domain.ports import ClockPort


class AsyncioClock(ClockPort):
    def read_now_seconds(self) -> float:
        return asyncio.get_running_loop().time()

    async def sleep(self, seconds: float) -> None:
        if seconds > 0:
            await asyncio.sleep(seconds)
