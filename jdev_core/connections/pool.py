"""
Generic Connection Pool.

SCALE & SUSTAIN Phase 3.2 - Connection Pooling.

A generic, reusable connection pool implementation.

Author: JuanCS Dev
Date: 2025-11-26
"""

import asyncio
import time
from dataclasses import dataclass, field
from typing import Callable, Generic, Optional, TypeVar

T = TypeVar('T')


class PoolExhaustedError(Exception):
    """Raised when pool has no available connections."""
    pass


@dataclass
class PoolConfig:
    """Connection pool configuration."""

    min_size: int = 1
    max_size: int = 10
    max_idle_time: float = 300.0  # 5 minutes
    acquire_timeout: float = 30.0
    validate_on_acquire: bool = True
    validate_on_release: bool = False


@dataclass
class PoolStats:
    """Connection pool statistics."""

    total_connections: int = 0
    available_connections: int = 0
    in_use_connections: int = 0
    total_acquires: int = 0
    total_releases: int = 0
    total_timeouts: int = 0
    total_errors: int = 0
    avg_acquire_time_ms: float = 0.0
    created_at: float = field(default_factory=time.time)

    @property
    def uptime_seconds(self) -> float:
        return time.time() - self.created_at


class ConnectionPool(Generic[T]):
    """
    Generic async connection pool.

    Usage:
        pool = ConnectionPool(
            factory=create_connection,
            validator=check_connection,
            closer=close_connection,
            config=PoolConfig(min_size=2, max_size=10)
        )
        await pool.initialize()

        async with pool.acquire() as conn:
            # use connection
            pass

        await pool.close()
    """

    def __init__(
        self,
        factory: Callable[[], T],
        validator: Optional[Callable[[T], bool]] = None,
        closer: Optional[Callable[[T], None]] = None,
        config: Optional[PoolConfig] = None
    ):
        """
        Initialize connection pool.

        Args:
            factory: Function to create new connections
            validator: Function to validate connection health
            closer: Function to close connections
            config: Pool configuration
        """
        self._factory = factory
        self._validator = validator or (lambda c: True)
        self._closer = closer or (lambda c: None)
        self._config = config or PoolConfig()

        self._available: asyncio.Queue[tuple[T, float]] = asyncio.Queue()
        self._in_use: set[T] = set()
        self._lock = asyncio.Lock()
        self._stats = PoolStats()
        self._closed = False
        self._cleanup_task: Optional[asyncio.Task] = None

    @property
    def stats(self) -> PoolStats:
        """Get pool statistics."""
        self._stats.available_connections = self._available.qsize()
        self._stats.in_use_connections = len(self._in_use)
        self._stats.total_connections = (
            self._stats.available_connections + self._stats.in_use_connections
        )
        return self._stats

    async def initialize(self) -> None:
        """Initialize pool with minimum connections."""
        for _ in range(self._config.min_size):
            conn = await self._create_connection()
            if conn:
                await self._available.put((conn, time.time()))

        # Start cleanup task
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())

    async def _create_connection(self) -> Optional[T]:
        """Create a new connection."""
        try:
            if asyncio.iscoroutinefunction(self._factory):
                conn = await self._factory()
            else:
                loop = asyncio.get_event_loop()
                conn = await loop.run_in_executor(None, self._factory)
            return conn
        except Exception:
            self._stats.total_errors += 1
            return None

    async def _validate_connection(self, conn: T) -> bool:
        """Validate a connection."""
        try:
            if asyncio.iscoroutinefunction(self._validator):
                return await self._validator(conn)
            else:
                loop = asyncio.get_event_loop()
                return await loop.run_in_executor(None, self._validator, conn)
        except Exception:
            return False

    async def _close_connection(self, conn: T) -> None:
        """Close a connection."""
        try:
            if asyncio.iscoroutinefunction(self._closer):
                await self._closer(conn)
            else:
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, self._closer, conn)
        except Exception:
            pass

    async def acquire(self) -> 'PooledConnection[T]':
        """
        Acquire a connection from the pool.

        Returns:
            PooledConnection context manager

        Raises:
            PoolExhaustedError: If no connection available within timeout
        """
        if self._closed:
            raise PoolExhaustedError("Pool is closed")

        start_time = time.time()

        async with self._lock:
            # Try to get from available pool
            while not self._available.empty():
                conn, created_at = await self._available.get()

                # Check if connection is stale
                if time.time() - created_at > self._config.max_idle_time:
                    await self._close_connection(conn)
                    continue

                # Validate if required
                if self._config.validate_on_acquire:
                    if not await self._validate_connection(conn):
                        await self._close_connection(conn)
                        continue

                self._in_use.add(conn)
                self._stats.total_acquires += 1
                elapsed = (time.time() - start_time) * 1000
                self._update_avg_acquire_time(elapsed)
                return PooledConnection(self, conn)

            # Create new if under max
            total = self._available.qsize() + len(self._in_use)
            if total < self._config.max_size:
                conn = await self._create_connection()
                if conn:
                    self._in_use.add(conn)
                    self._stats.total_acquires += 1
                    elapsed = (time.time() - start_time) * 1000
                    self._update_avg_acquire_time(elapsed)
                    return PooledConnection(self, conn)

        # Wait for available connection
        try:
            conn, _ = await asyncio.wait_for(
                self._available.get(),
                timeout=self._config.acquire_timeout
            )
            async with self._lock:
                self._in_use.add(conn)
            self._stats.total_acquires += 1
            elapsed = (time.time() - start_time) * 1000
            self._update_avg_acquire_time(elapsed)
            return PooledConnection(self, conn)
        except asyncio.TimeoutError:
            self._stats.total_timeouts += 1
            raise PoolExhaustedError(
                f"No connection available within {self._config.acquire_timeout}s"
            )

    def _update_avg_acquire_time(self, elapsed_ms: float) -> None:
        """Update average acquire time."""
        count = self._stats.total_acquires
        current_avg = self._stats.avg_acquire_time_ms
        self._stats.avg_acquire_time_ms = (
            (current_avg * (count - 1) + elapsed_ms) / count
        )

    async def release(self, conn: T) -> None:
        """Release a connection back to the pool."""
        async with self._lock:
            if conn in self._in_use:
                self._in_use.remove(conn)

                # Validate before returning to pool
                if self._config.validate_on_release:
                    if not await self._validate_connection(conn):
                        await self._close_connection(conn)
                        self._stats.total_releases += 1
                        return

                await self._available.put((conn, time.time()))
                self._stats.total_releases += 1

    async def _cleanup_loop(self) -> None:
        """Periodically clean up idle connections."""
        while not self._closed:
            await asyncio.sleep(60)  # Check every minute

            async with self._lock:
                # Remove stale connections
                temp_connections = []
                while not self._available.empty():
                    conn, created_at = await self._available.get()
                    if time.time() - created_at > self._config.max_idle_time:
                        await self._close_connection(conn)
                    else:
                        temp_connections.append((conn, created_at))

                # Keep at least min_size connections
                while len(temp_connections) < self._config.min_size:
                    conn = await self._create_connection()
                    if conn:
                        temp_connections.append((conn, time.time()))

                # Return to queue
                for item in temp_connections:
                    await self._available.put(item)

    async def close(self) -> None:
        """Close all connections and the pool."""
        self._closed = True

        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass

        # Close all connections
        while not self._available.empty():
            conn, _ = await self._available.get()
            await self._close_connection(conn)

        for conn in list(self._in_use):
            await self._close_connection(conn)
            self._in_use.remove(conn)


class PooledConnection(Generic[T]):
    """Context manager for pooled connections."""

    def __init__(self, pool: ConnectionPool[T], connection: T):
        self._pool = pool
        self._connection = connection

    @property
    def connection(self) -> T:
        """Get the underlying connection."""
        return self._connection

    async def __aenter__(self) -> T:
        return self._connection

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self._pool.release(self._connection)


__all__ = [
    'ConnectionPool',
    'PoolConfig',
    'PoolStats',
    'PoolExhaustedError',
    'PooledConnection',
]
