"""
Storage Interfaces.

SCALE & SUSTAIN Phase 2.2 - Interface Extraction.

Defines interfaces for storage and caching:
- IStorage: Key-value storage
- ICache: Caching layer

Author: JuanCS Dev
Date: 2025-11-26
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, TypeVar, Generic
from datetime import datetime

T = TypeVar('T')


@dataclass
class ICacheStats:
    """Cache statistics."""
    hits: int = 0
    misses: int = 0
    size: int = 0
    max_size: int = 0
    evictions: int = 0

    @property
    def hit_rate(self) -> float:
        """Calculate hit rate."""
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0


@dataclass
class CacheEntry(Generic[T]):
    """Cache entry with metadata."""
    key: str
    value: T
    created_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    access_count: int = 0
    last_accessed: datetime = field(default_factory=datetime.utcnow)

    @property
    def is_expired(self) -> bool:
        """Check if entry has expired."""
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at


class IStorage(ABC):
    """
    Interface for key-value storage.

    Provides persistent storage for application data.

    Example:
        storage = MyStorage()
        await storage.set("user:123", {"name": "Juan"})
        user = await storage.get("user:123")
    """

    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        """
        Get value by key.

        Args:
            key: Storage key

        Returns:
            Value or None if not found
        """
        pass

    @abstractmethod
    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None
    ) -> None:
        """
        Set value for key.

        Args:
            key: Storage key
            value: Value to store
            ttl: Time-to-live in seconds
        """
        pass

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """
        Delete key.

        Args:
            key: Key to delete

        Returns:
            True if key existed
        """
        pass

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """
        Check if key exists.

        Args:
            key: Key to check

        Returns:
            True if exists
        """
        pass

    async def get_many(self, keys: List[str]) -> Dict[str, Any]:
        """Get multiple values."""
        return {k: await self.get(k) for k in keys}

    async def set_many(
        self,
        items: Dict[str, Any],
        ttl: Optional[int] = None
    ) -> None:
        """Set multiple values."""
        for k, v in items.items():
            await self.set(k, v, ttl)

    async def delete_many(self, keys: List[str]) -> int:
        """Delete multiple keys. Returns count deleted."""
        count = 0
        for k in keys:
            if await self.delete(k):
                count += 1
        return count


class ICache(ABC):
    """
    Interface for caching layer.

    Provides in-memory caching with optional persistence.

    Example:
        cache = MyCache(max_size=1000)
        cache.set("result", data, ttl=300)
        if cache.has("result"):
            data = cache.get("result")
    """

    @abstractmethod
    def get(self, key: str) -> Optional[Any]:
        """
        Get cached value.

        Args:
            key: Cache key

        Returns:
            Cached value or None
        """
        pass

    @abstractmethod
    def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None
    ) -> None:
        """
        Set cache value.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds
        """
        pass

    @abstractmethod
    def delete(self, key: str) -> bool:
        """Delete cached value."""
        pass

    @abstractmethod
    def clear(self) -> None:
        """Clear all cached values."""
        pass

    @abstractmethod
    def has(self, key: str) -> bool:
        """Check if key is cached."""
        pass

    @property
    @abstractmethod
    def stats(self) -> ICacheStats:
        """Get cache statistics."""
        pass

    def get_or_set(
        self,
        key: str,
        factory,
        ttl: Optional[int] = None
    ) -> Any:
        """
        Get value or compute and cache it.

        Args:
            key: Cache key
            factory: Function to compute value if missing
            ttl: Time-to-live

        Returns:
            Cached or computed value
        """
        value = self.get(key)
        if value is not None:
            return value
        value = factory()
        self.set(key, value, ttl)
        return value


__all__ = [
    'IStorage',
    'ICache',
    'ICacheStats',
    'CacheEntry',
]
