"""
Tests for connection pool.

SCALE & SUSTAIN Phase 3.2 validation.
"""

import pytest

from jdev_core.connections import (
    ConnectionPool,
    PoolConfig,
    PoolStats,
    PoolExhaustedError,
)


class MockConnection:
    """Mock connection for testing."""

    def __init__(self, id: int):
        self.id = id
        self.closed = False

    def close(self):
        self.closed = True


class TestPoolConfig:
    """Test PoolConfig dataclass."""

    def test_default_config(self):
        """Test default configuration values."""
        config = PoolConfig()

        assert config.min_size == 1
        assert config.max_size == 10
        assert config.max_idle_time == 300.0
        assert config.acquire_timeout == 30.0
        assert config.validate_on_acquire is True

    def test_custom_config(self):
        """Test custom configuration."""
        config = PoolConfig(
            min_size=5,
            max_size=20,
            acquire_timeout=10.0
        )

        assert config.min_size == 5
        assert config.max_size == 20
        assert config.acquire_timeout == 10.0


class TestPoolStats:
    """Test PoolStats dataclass."""

    def test_stats_default(self):
        """Test default stats values."""
        stats = PoolStats()

        assert stats.total_connections == 0
        assert stats.available_connections == 0
        assert stats.in_use_connections == 0

    def test_stats_uptime(self):
        """Test uptime calculation."""
        import time
        stats = PoolStats(created_at=time.time() - 10)

        assert stats.uptime_seconds >= 10


class TestConnectionPool:
    """Test ConnectionPool class."""

    @pytest.fixture
    def connection_counter(self):
        """Counter for tracking connection creation."""
        return {"count": 0}

    def create_factory(self, counter):
        """Create a connection factory."""
        def factory():
            counter["count"] += 1
            return MockConnection(counter["count"])
        return factory

    @pytest.mark.asyncio
    async def test_pool_initialization(self, connection_counter):
        """Test pool creates min_size connections on init."""
        config = PoolConfig(min_size=3, max_size=10)
        pool = ConnectionPool(
            factory=self.create_factory(connection_counter),
            config=config
        )

        await pool.initialize()

        assert connection_counter["count"] == 3
        assert pool.stats.available_connections == 3

        await pool.close()

    @pytest.mark.asyncio
    async def test_acquire_and_release(self, connection_counter):
        """Test acquiring and releasing connections."""
        config = PoolConfig(min_size=1, max_size=5)
        pool = ConnectionPool(
            factory=self.create_factory(connection_counter),
            config=config
        )
        await pool.initialize()

        # Acquire connection
        async with await pool.acquire() as conn:
            assert isinstance(conn, MockConnection)
            assert pool.stats.in_use_connections == 1

        # After release
        assert pool.stats.in_use_connections == 0
        assert pool.stats.available_connections == 1

        await pool.close()

    @pytest.mark.asyncio
    async def test_pool_creates_new_connections(self, connection_counter):
        """Test pool creates new connections when needed."""
        config = PoolConfig(min_size=1, max_size=5)
        pool = ConnectionPool(
            factory=self.create_factory(connection_counter),
            config=config
        )
        await pool.initialize()

        # Acquire multiple connections
        conn1 = await pool.acquire()
        conn2 = await pool.acquire()
        conn3 = await pool.acquire()

        assert pool.stats.in_use_connections == 3
        assert connection_counter["count"] == 3

        # Release all
        await pool.release(conn1.connection)
        await pool.release(conn2.connection)
        await pool.release(conn3.connection)

        await pool.close()

    @pytest.mark.asyncio
    async def test_pool_exhaustion(self, connection_counter):
        """Test pool exhaustion raises error."""
        config = PoolConfig(min_size=1, max_size=2, acquire_timeout=0.1)
        pool = ConnectionPool(
            factory=self.create_factory(connection_counter),
            config=config
        )
        await pool.initialize()

        # Exhaust the pool
        conn1 = await pool.acquire()
        conn2 = await pool.acquire()

        # Next acquire should timeout
        with pytest.raises(PoolExhaustedError):
            await pool.acquire()

        await pool.release(conn1.connection)
        await pool.release(conn2.connection)
        await pool.close()

    @pytest.mark.asyncio
    async def test_pool_stats_tracking(self, connection_counter):
        """Test pool statistics are tracked."""
        config = PoolConfig(min_size=1, max_size=5)
        pool = ConnectionPool(
            factory=self.create_factory(connection_counter),
            config=config
        )
        await pool.initialize()

        # Initial stats
        stats = pool.stats
        assert stats.total_acquires == 0

        # Acquire and release
        async with await pool.acquire():
            pass

        stats = pool.stats
        assert stats.total_acquires == 1
        assert stats.total_releases == 1

        await pool.close()

    @pytest.mark.asyncio
    async def test_pool_validation(self, connection_counter):
        """Test connection validation on acquire."""
        valid_ids = {1, 2}  # Only connections 1 and 2 are valid

        def validator(conn):
            return conn.id in valid_ids

        config = PoolConfig(min_size=1, max_size=5, validate_on_acquire=True)
        pool = ConnectionPool(
            factory=self.create_factory(connection_counter),
            validator=validator,
            config=config
        )
        await pool.initialize()

        # First connection should be valid
        async with await pool.acquire() as conn:
            assert conn.id == 1

        await pool.close()

    @pytest.mark.asyncio
    async def test_pool_close(self, connection_counter):
        """Test pool closes all connections."""
        closures = []

        def closer(conn):
            closures.append(conn.id)

        config = PoolConfig(min_size=3, max_size=5)
        pool = ConnectionPool(
            factory=self.create_factory(connection_counter),
            closer=closer,
            config=config
        )
        await pool.initialize()

        await pool.close()

        assert len(closures) == 3
