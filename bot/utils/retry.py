import asyncio
import logging
from typing import Callable, Awaitable, Type, Tuple


async def retry(
    func: Callable[..., Awaitable],
    *args,
    attempts: int = 3,
    base_delay: float = 0.5,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    logger: logging.Logger | None = None,
):
    """Execute ``func`` with retry on failure.

    Parameters
    ----------
    func: Callable[..., Awaitable]
        Asynchronous function to execute.
    attempts: int
        Maximum number of attempts before giving up.
    base_delay: float
        Initial delay in seconds for exponential backoff.
    exceptions: Tuple[Type[Exception], ...]
        Exceptions that trigger a retry.
    logger: logging.Logger | None
        Optional logger for warnings.
    """

    delay = base_delay
    for attempt in range(1, attempts + 1):
        try:
            return await func(*args)
        except exceptions as exc:  # type: ignore[misc]
            if attempt == attempts:
                raise
            if logger:
                logger.warning("Retry %d/%d after error: %s", attempt, attempts, exc)
            await asyncio.sleep(delay)
            delay *= 2
