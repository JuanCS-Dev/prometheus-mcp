"""
Connection Manager.

SCALE & SUSTAIN Phase 3.2 - Connection Pooling.

Centralized connection management for all external services.

Author: JuanCS Dev
Date: 2025-11-26
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional

from .pool import ConnectionPool, PoolConfig, PoolStats


class ConnectionType(Enum):
    """Types of managed connections."""

    DATABASE = "database"
    HTTP = "http"
    REDIS = "redis"
    CUSTOM = "custom"


@dataclass
class ConnectionConfig:
    """Configuration for a connection type."""

    name: str
    conn_type: ConnectionType
    pool_config: PoolConfig = field(default_factory=PoolConfig)
    connection_params: Dict[str, Any] = field(default_factory=dict)
    enabled: bool = True


class ConnectionManager:
    """
    Centralized connection manager.

    Manages multiple connection pools for different services.

    Usage:
        manager = ConnectionManager()

        # Register a database pool
        manager.register(
            ConnectionConfig(
                name="main_db",
                conn_type=ConnectionType.DATABASE,
                connection_params={"database": "app.db"}
            ),
            factory=create_db_connection
        )

        await manager.initialize()

        # Use connections
        async with manager.acquire("main_db") as conn:
            # use connection
            pass

        await manager.close()
    """

    def __init__(self):
        self._pools: Dict[str, ConnectionPool] = {}
        self._configs: Dict[str, ConnectionConfig] = {}
        self._initialized = False

    def register(
        self,
        config: ConnectionConfig,
        factory: Any,
        validator: Any = None,
        closer: Any = None
    ) -> None:
        """
        Register a connection pool.

        Args:
            config: Connection configuration
            factory: Connection factory function
            validator: Optional connection validator
            closer: Optional connection closer
        """
        if config.enabled:
            pool = ConnectionPool(
                factory=factory,
                validator=validator,
                closer=closer,
                config=config.pool_config
            )
            self._pools[config.name] = pool
            self._configs[config.name] = config

    async def initialize(self) -> None:
        """Initialize all registered pools."""
        for pool in self._pools.values():
            await pool.initialize()
        self._initialized = True

    async def acquire(self, name: str) -> Any:
        """
        Acquire a connection from a named pool.

        Args:
            name: Pool name

        Returns:
            PooledConnection context manager
        """
        if name not in self._pools:
            raise KeyError(f"Unknown connection pool: {name}")
        return await self._pools[name].acquire()

    def get_stats(self, name: Optional[str] = None) -> Dict[str, PoolStats]:
        """
        Get pool statistics.

        Args:
            name: Optional pool name. If None, returns all pools.

        Returns:
            Dictionary of pool names to stats
        """
        if name:
            if name not in self._pools:
                raise KeyError(f"Unknown connection pool: {name}")
            return {name: self._pools[name].stats}
        return {name: pool.stats for name, pool in self._pools.items()}

    def get_config(self, name: str) -> ConnectionConfig:
        """Get configuration for a pool."""
        if name not in self._configs:
            raise KeyError(f"Unknown connection pool: {name}")
        return self._configs[name]

    @property
    def pool_names(self) -> list[str]:
        """Get list of registered pool names."""
        return list(self._pools.keys())

    @property
    def is_initialized(self) -> bool:
        """Check if manager is initialized."""
        return self._initialized

    async def health_check(self) -> Dict[str, bool]:
        """
        Check health of all pools.

        Returns:
            Dictionary of pool names to health status
        """
        results = {}
        for name, pool in self._pools.items():
            try:
                async with await pool.acquire() as conn:
                    results[name] = True
            except Exception:
                results[name] = False
        return results

    async def close(self, name: Optional[str] = None) -> None:
        """
        Close connection pool(s).

        Args:
            name: Optional pool name. If None, closes all pools.
        """
        if name:
            if name in self._pools:
                await self._pools[name].close()
                del self._pools[name]
                del self._configs[name]
        else:
            for pool in self._pools.values():
                await pool.close()
            self._pools.clear()
            self._configs.clear()
            self._initialized = False


# Global connection manager instance
_global_manager: Optional[ConnectionManager] = None


def get_connection_manager() -> ConnectionManager:
    """Get or create the global connection manager."""
    global _global_manager
    if _global_manager is None:
        _global_manager = ConnectionManager()
    return _global_manager


async def initialize_connections() -> None:
    """Initialize the global connection manager."""
    manager = get_connection_manager()
    if not manager.is_initialized:
        await manager.initialize()


async def close_connections() -> None:
    """Close all global connections."""
    global _global_manager
    if _global_manager:
        await _global_manager.close()
        _global_manager = None


__all__ = [
    'ConnectionManager',
    'ConnectionConfig',
    'ConnectionType',
    'get_connection_manager',
    'initialize_connections',
    'close_connections',
]
