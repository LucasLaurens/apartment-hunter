"""Opening and closing the dependency container around a CLI command."""

import sys
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from loguru import logger

from ...infrastructure.config import get_settings
from ...infrastructure.container import Container

_LOG_FORMAT = "<green>{time:HH:mm:ss}</green> | {level} | {message}"


def setup_logging() -> None:
    logger.remove()
    logger.add(sys.stderr, level=get_settings().log_level, format=_LOG_FORMAT)


@asynccontextmanager
async def open_container() -> AsyncIterator[Container]:
    """A connected Container, closed (DB + crawler browsers) whatever happens."""
    container = Container(get_settings())
    await container.repository.connect()
    try:
        yield container
    finally:
        await container.close()
