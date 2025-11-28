"""
Async Utilities.

SCALE & SUSTAIN Phase 3.1 - Async Everywhere.

Common async utilities: run_sync, gather_with_limit, timeout, retry.

Author: JuanCS Dev
Date: 2025-11-26
"""

import asyncio
import functools
from typing import (
    Awaitable,
    Callable,
    List,
    Optional,
    Sequence,
    TypeVar,
    Union,
)

T = TypeVar('T')


def run_sync(coro: Awaitable[T]) -> T:
    """
    Run an async coroutine synchronously.

    Handles the case where we're already in an async context.

    Args:
        coro: Coroutine to run

    Returns:
        Result of the coroutine
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        # No running loop, create one
        return asyncio.run(coro)

    # Already in async context, need to run in a new thread
    import concurrent.futures
    with concurrent.futures.ThreadPoolExecutor() as pool:
        future = pool.submit(asyncio.run, coro)
        return future.result()


async def gather_with_limit(
    coros: Sequence[Awaitable[T]],
    limit: int = 10,
    return_exceptions: bool = False
) -> List[Union[T, Exception]]:
    """
    Run coroutines concurrently with a concurrency limit.

    Args:
        coros: Sequence of coroutines to run
        limit: Maximum concurrent coroutines
        return_exceptions: If True, return exceptions instead of raising

    Returns:
        List of results in original order
    """
    semaphore = asyncio.Semaphore(limit)

    async def limited_coro(index: int, coro: Awaitable[T]) -> tuple[int, Union[T, Exception]]:
        async with semaphore:
            try:
                result = await coro
                return (index, result)
            except Exception as e:
                if return_exceptions:
                    return (index, e)
                raise

    tasks = [
        asyncio.create_task(limited_coro(i, coro))
        for i, coro in enumerate(coros)
    ]

    results = await asyncio.gather(*tasks, return_exceptions=return_exceptions)

    # Sort by original index and extract results
    sorted_results = sorted(results, key=lambda x: x[0] if isinstance(x, tuple) else 0)
    return [r[1] if isinstance(r, tuple) else r for r in sorted_results]


async def timeout(
    coro: Awaitable[T],
    seconds: float,
    default: Optional[T] = None
) -> Optional[T]:
    """
    Run a coroutine with a timeout.

    Args:
        coro: Coroutine to run
        seconds: Timeout in seconds
        default: Value to return on timeout

    Returns:
        Result of coroutine or default on timeout
    """
    try:
        return await asyncio.wait_for(coro, timeout=seconds)
    except asyncio.TimeoutError:
        return default


class TimeoutError(Exception):
    """Timeout error with context."""

    def __init__(self, message: str, seconds: float):
        super().__init__(message)
        self.seconds = seconds


async def timeout_or_raise(
    coro: Awaitable[T],
    seconds: float,
    message: str = "Operation timed out"
) -> T:
    """
    Run a coroutine with a timeout, raising on timeout.

    Args:
        coro: Coroutine to run
        seconds: Timeout in seconds
        message: Error message on timeout

    Returns:
        Result of coroutine

    Raises:
        TimeoutError: If operation times out
    """
    try:
        return await asyncio.wait_for(coro, timeout=seconds)
    except asyncio.TimeoutError:
        raise TimeoutError(f"{message} after {seconds}s", seconds)


def retry(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple = (Exception,)
) -> Callable[[Callable[..., Awaitable[T]]], Callable[..., Awaitable[T]]]:
    """
    Decorator to retry an async function on failure.

    Args:
        max_attempts: Maximum retry attempts
        delay: Initial delay between retries
        backoff: Multiplier for delay after each retry
        exceptions: Tuple of exceptions to catch

    Returns:
        Decorated function
    """
    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            current_delay = delay
            last_exception = None

            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        await asyncio.sleep(current_delay)
                        current_delay *= backoff

            raise last_exception

        return wrapper
    return decorator


async def retry_async(
    coro_factory: Callable[[], Awaitable[T]],
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple = (Exception,)
) -> T:
    """
    Retry a coroutine factory on failure.

    Args:
        coro_factory: Function that creates a new coroutine each call
        max_attempts: Maximum retry attempts
        delay: Initial delay between retries
        backoff: Multiplier for delay after each retry
        exceptions: Tuple of exceptions to catch

    Returns:
        Result of successful coroutine

    Example:
        result = await retry_async(
            lambda: fetch_data(url),
            max_attempts=3,
            delay=1.0
        )
    """
    current_delay = delay
    last_exception = None

    for attempt in range(max_attempts):
        try:
            return await coro_factory()
        except exceptions as e:
            last_exception = e
            if attempt < max_attempts - 1:
                await asyncio.sleep(current_delay)
                current_delay *= backoff

    raise last_exception


async def first_completed(
    coros: Sequence[Awaitable[T]],
    cancel_pending: bool = True
) -> T:
    """
    Return result of first completed coroutine.

    Args:
        coros: Coroutines to race
        cancel_pending: Cancel remaining coroutines

    Returns:
        Result of first completed coroutine
    """
    tasks = [asyncio.create_task(coro) for coro in coros]

    done, pending = await asyncio.wait(
        tasks,
        return_when=asyncio.FIRST_COMPLETED
    )

    if cancel_pending:
        for task in pending:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

    # Return first completed result
    for task in done:
        return task.result()


async def debounce(
    coro: Awaitable[T],
    wait: float
) -> T:
    """
    Debounce a coroutine execution.

    Args:
        coro: Coroutine to debounce
        wait: Wait time in seconds

    Returns:
        Result of coroutine
    """
    await asyncio.sleep(wait)
    return await coro


class AsyncLock:
    """
    Enhanced async lock with timeout support.

    Usage:
        lock = AsyncLock()
        async with lock.acquire(timeout=5.0):
            # critical section
    """

    def __init__(self):
        self._lock = asyncio.Lock()

    async def acquire(self, timeout: Optional[float] = None) -> 'AsyncLockContext':
        """Acquire lock with optional timeout."""
        return AsyncLockContext(self._lock, timeout)

    async def __aenter__(self):
        await self._lock.acquire()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self._lock.release()


class AsyncLockContext:
    """Context manager for AsyncLock with timeout."""

    def __init__(self, lock: asyncio.Lock, timeout: Optional[float]):
        self._lock = lock
        self._timeout = timeout

    async def __aenter__(self):
        if self._timeout:
            try:
                await asyncio.wait_for(self._lock.acquire(), self._timeout)
            except asyncio.TimeoutError:
                raise TimeoutError("Failed to acquire lock", self._timeout)
        else:
            await self._lock.acquire()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self._lock.release()


__all__ = [
    'run_sync',
    'gather_with_limit',
    'timeout',
    'timeout_or_raise',
    'TimeoutError',
    'retry',
    'retry_async',
    'first_completed',
    'debounce',
    'AsyncLock',
]
