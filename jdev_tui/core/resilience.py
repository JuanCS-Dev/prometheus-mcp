"""
Resilience Module - Thread Safety and Concurrency Primitives
============================================================

CHAOS ORCHESTRATOR - RESILIENCE ENGINEERING (Nov 2025)

Provides thread-safe primitives for critical operations:
- AsyncLock: Async-safe lock wrapper
- ThreadSafeList: Thread-safe list operations
- ThreadSafeDict: Thread-safe dict operations
- RateLimiter: Rate limiting for API calls

Compliance: Vértice Constitution v3.0 - P2 (Robustness)
"""

from __future__ import annotations

import asyncio
import threading
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any, Dict, Generic, Iterator, List, Optional, TypeVar

T = TypeVar('T')


# =============================================================================
# ASYNC-SAFE LOCK
# =============================================================================

class AsyncLock:
    """
    Async-safe lock that works in both sync and async contexts.

    Usage:
        lock = AsyncLock()

        # Async context
        async with lock:
            await do_something()

        # Sync context (falls back to threading lock)
        with lock.sync():
            do_something()
    """

    def __init__(self, name: str = "unnamed"):
        self.name = name
        self._async_lock = asyncio.Lock()
        self._thread_lock = threading.RLock()

    async def __aenter__(self):
        await self._async_lock.acquire()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self._async_lock.release()
        return False

    @asynccontextmanager
    async def acquire_async(self):
        """Explicit async acquisition."""
        await self._async_lock.acquire()
        try:
            yield
        finally:
            self._async_lock.release()

    def sync(self):
        """Return sync context manager."""
        return self._thread_lock


# =============================================================================
# THREAD-SAFE COLLECTIONS
# =============================================================================

class ThreadSafeList(Generic[T]):
    """
    Thread-safe list with atomic operations.

    All operations are protected by a lock to prevent race conditions.
    """

    def __init__(self, initial: Optional[List[T]] = None):
        self._data: List[T] = list(initial) if initial else []
        self._lock = threading.RLock()

    def append(self, item: T) -> None:
        """Append item atomically."""
        with self._lock:
            self._data.append(item)

    def extend(self, items: List[T]) -> None:
        """Extend list atomically."""
        with self._lock:
            self._data.extend(items)

    def pop(self, index: int = -1) -> T:
        """Pop item atomically."""
        with self._lock:
            return self._data.pop(index)

    def remove(self, item: T) -> None:
        """Remove item atomically."""
        with self._lock:
            self._data.remove(item)

    def clear(self) -> None:
        """Clear list atomically."""
        with self._lock:
            self._data.clear()

    def get(self, index: int, default: Optional[T] = None) -> Optional[T]:
        """Get item by index atomically."""
        with self._lock:
            try:
                return self._data[index]
            except IndexError:
                return default

    def set(self, index: int, value: T) -> None:
        """Set item at index atomically."""
        with self._lock:
            self._data[index] = value

    def copy(self) -> List[T]:
        """Return a copy of the list atomically."""
        with self._lock:
            return self._data.copy()

    def find(self, predicate) -> Optional[T]:
        """Find first item matching predicate atomically."""
        with self._lock:
            for item in self._data:
                if predicate(item):
                    return item
            return None

    def find_index(self, predicate) -> int:
        """Find index of first item matching predicate atomically."""
        with self._lock:
            for i, item in enumerate(self._data):
                if predicate(item):
                    return i
            return -1

    def update_where(self, predicate, updater) -> int:
        """Update items matching predicate atomically. Returns count updated."""
        with self._lock:
            count = 0
            for i, item in enumerate(self._data):
                if predicate(item):
                    self._data[i] = updater(item)
                    count += 1
            return count

    def __len__(self) -> int:
        with self._lock:
            return len(self._data)

    def __iter__(self) -> Iterator[T]:
        """Iterate over a copy to prevent modification during iteration."""
        with self._lock:
            return iter(self._data.copy())

    def __bool__(self) -> bool:
        with self._lock:
            return bool(self._data)


class ThreadSafeDict(Generic[T]):
    """
    Thread-safe dictionary with atomic operations.
    """

    def __init__(self, initial: Optional[Dict[str, T]] = None):
        self._data: Dict[str, T] = dict(initial) if initial else {}
        self._lock = threading.RLock()

    def get(self, key: str, default: Optional[T] = None) -> Optional[T]:
        """Get item atomically."""
        with self._lock:
            return self._data.get(key, default)

    def set(self, key: str, value: T) -> None:
        """Set item atomically."""
        with self._lock:
            self._data[key] = value

    def delete(self, key: str) -> Optional[T]:
        """Delete item atomically, returning value or None."""
        with self._lock:
            return self._data.pop(key, None)

    def update(self, items: Dict[str, T]) -> None:
        """Update multiple items atomically."""
        with self._lock:
            self._data.update(items)

    def keys(self) -> List[str]:
        """Return list of keys atomically."""
        with self._lock:
            return list(self._data.keys())

    def values(self) -> List[T]:
        """Return list of values atomically."""
        with self._lock:
            return list(self._data.values())

    def items(self) -> List[tuple]:
        """Return list of items atomically."""
        with self._lock:
            return list(self._data.items())

    def copy(self) -> Dict[str, T]:
        """Return a copy atomically."""
        with self._lock:
            return self._data.copy()

    def clear(self) -> None:
        """Clear dict atomically."""
        with self._lock:
            self._data.clear()

    def __contains__(self, key: str) -> bool:
        with self._lock:
            return key in self._data

    def __len__(self) -> int:
        with self._lock:
            return len(self._data)


# =============================================================================
# RATE LIMITER
# =============================================================================

@dataclass
class RateLimiterConfig:
    """Configuration for rate limiter."""
    requests_per_second: float = 10.0
    burst_size: int = 20
    retry_after_seconds: float = 1.0


class RateLimiter:
    """
    Token bucket rate limiter for API calls.

    Prevents overwhelming external services with too many requests.
    """

    def __init__(self, config: Optional[RateLimiterConfig] = None):
        self.config = config or RateLimiterConfig()
        self._tokens = float(self.config.burst_size)
        self._last_refill = time.time()
        self._lock = threading.Lock()

    def _refill(self) -> None:
        """Refill tokens based on elapsed time."""
        now = time.time()
        elapsed = now - self._last_refill
        self._tokens = min(
            self.config.burst_size,
            self._tokens + elapsed * self.config.requests_per_second
        )
        self._last_refill = now

    def try_acquire(self) -> bool:
        """
        Try to acquire a token.

        Returns:
            True if token acquired, False if rate limited
        """
        with self._lock:
            self._refill()
            if self._tokens >= 1.0:
                self._tokens -= 1.0
                return True
            return False

    async def acquire(self) -> None:
        """Wait until a token is available."""
        while not self.try_acquire():
            await asyncio.sleep(self.config.retry_after_seconds)

    def get_status(self) -> Dict[str, Any]:
        """Get rate limiter status."""
        with self._lock:
            self._refill()
            return {
                "available_tokens": self._tokens,
                "burst_size": self.config.burst_size,
                "requests_per_second": self.config.requests_per_second,
            }


# =============================================================================
# DEBOUNCER
# =============================================================================

class Debouncer:
    """
    Debouncer for UI updates and expensive operations.

    Ensures a function is called at most once per interval.
    """

    def __init__(self, delay_seconds: float = 0.1):
        self.delay = delay_seconds
        self._last_call: Dict[str, float] = {}
        self._lock = threading.Lock()

    def should_call(self, key: str = "default") -> bool:
        """Check if enough time has passed since last call."""
        now = time.time()
        with self._lock:
            last = self._last_call.get(key, 0)
            if now - last >= self.delay:
                self._last_call[key] = now
                return True
            return False

    def reset(self, key: str = "default") -> None:
        """Reset debouncer for a key."""
        with self._lock:
            self._last_call.pop(key, None)


# =============================================================================
# RETRY HELPER
# =============================================================================

@dataclass
class RetryConfig:
    """Configuration for retry behavior."""
    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 30.0
    exponential_base: float = 2.0
    jitter: float = 0.1


async def retry_async(
    func,
    config: Optional[RetryConfig] = None,
    on_retry: Optional[callable] = None,
):
    """
    Retry an async function with exponential backoff.

    Args:
        func: Async function to retry
        config: Retry configuration
        on_retry: Optional callback on retry (attempt, error, delay)

    Returns:
        Result of successful function call

    Raises:
        Last exception if all attempts fail
    """
    import random
    config = config or RetryConfig()
    last_error = None

    for attempt in range(1, config.max_attempts + 1):
        try:
            return await func()
        except Exception as e:
            last_error = e

            if attempt == config.max_attempts:
                raise

            # Calculate delay with exponential backoff and jitter
            delay = min(
                config.base_delay * (config.exponential_base ** (attempt - 1)),
                config.max_delay
            )
            delay *= (1 + random.uniform(-config.jitter, config.jitter))

            if on_retry:
                on_retry(attempt, e, delay)

            await asyncio.sleep(delay)

    raise last_error


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    'AsyncLock',
    'ThreadSafeList',
    'ThreadSafeDict',
    'RateLimiter',
    'RateLimiterConfig',
    'Debouncer',
    'RetryConfig',
    'retry_async',
]
