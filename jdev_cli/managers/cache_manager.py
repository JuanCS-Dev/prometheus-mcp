"""
Cache Manager.

SCALE & SUSTAIN Phase 1.1.2 - Cache Manager.

Provides multi-level caching with TTL and size limits.

Author: JuanCS Dev
Date: 2025-11-26
"""

import hashlib
import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, Generic, Optional, TypeVar
from collections import OrderedDict
import threading

T = TypeVar('T')


@dataclass
class CacheEntry(Generic[T]):
    """Cache entry with metadata."""
    value: T
    created_at: float
    expires_at: Optional[float]
    hits: int = 0
    size_bytes: int = 0

    @property
    def is_expired(self) -> bool:
        """Check if entry has expired."""
        if self.expires_at is None:
            return False
        return time.time() > self.expires_at

    def touch(self) -> None:
        """Record a cache hit."""
        self.hits += 1


@dataclass
class CacheStats:
    """Cache statistics."""
    hits: int = 0
    misses: int = 0
    evictions: int = 0
    size_bytes: int = 0
    entry_count: int = 0

    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate."""
        total = self.hits + self.misses
        if total == 0:
            return 0.0
        return self.hits / total

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "hits": self.hits,
            "misses": self.misses,
            "evictions": self.evictions,
            "hit_rate": f"{self.hit_rate:.2%}",
            "size_bytes": self.size_bytes,
            "size_mb": f"{self.size_bytes / 1024 / 1024:.2f}",
            "entry_count": self.entry_count,
        }


class CacheManager:
    """
    Multi-level cache manager with LRU eviction.

    Features:
    - Memory cache (fast, limited size)
    - Disk cache (slower, larger capacity)
    - TTL-based expiration
    - LRU eviction policy
    - Namespace isolation
    - Thread-safe operations

    Example:
        cache = CacheManager(max_memory_mb=50, max_disk_mb=500)

        # Simple get/set
        cache.set("key", "value", ttl=3600)
        value = cache.get("key")

        # With namespace
        cache.set("prompt_hash", result, namespace="llm_responses")

        # Decorator
        @cache.cached(ttl=600)
        def expensive_operation(arg):
            ...
    """

    def __init__(
        self,
        max_memory_mb: float = 50,
        max_disk_mb: float = 500,
        default_ttl: Optional[int] = 3600,
        cache_dir: Optional[Path] = None
    ):
        self._max_memory_bytes = int(max_memory_mb * 1024 * 1024)
        self._max_disk_bytes = int(max_disk_mb * 1024 * 1024)
        self._default_ttl = default_ttl
        self._cache_dir = cache_dir or Path.home() / ".cache" / "jdev"

        # Memory cache (LRU ordered dict)
        self._memory: OrderedDict[str, CacheEntry] = OrderedDict()
        self._memory_size = 0

        # Stats
        self._stats = CacheStats()

        # Thread safety
        self._lock = threading.RLock()

        # Ensure cache directory exists
        self._cache_dir.mkdir(parents=True, exist_ok=True)

    def _make_key(self, key: str, namespace: Optional[str] = None) -> str:
        """Create namespaced cache key."""
        if namespace:
            return f"{namespace}:{key}"
        return key

    def _estimate_size(self, value: Any) -> int:
        """Estimate size of value in bytes."""
        try:
            return len(json.dumps(value).encode())
        except (TypeError, ValueError):
            return len(str(value).encode())

    def get(
        self,
        key: str,
        default: Optional[T] = None,
        namespace: Optional[str] = None
    ) -> Optional[T]:
        """
        Get value from cache.

        Args:
            key: Cache key
            default: Default value if not found
            namespace: Cache namespace

        Returns:
            Cached value or default
        """
        full_key = self._make_key(key, namespace)

        with self._lock:
            # Check memory cache
            if full_key in self._memory:
                entry = self._memory[full_key]

                if entry.is_expired:
                    self._evict(full_key)
                    self._stats.misses += 1
                    return default

                # Move to end (LRU)
                self._memory.move_to_end(full_key)
                entry.touch()
                self._stats.hits += 1
                return entry.value

            # Check disk cache
            disk_value = self._get_from_disk(full_key)
            if disk_value is not None:
                self._stats.hits += 1
                # Promote to memory
                self._set_memory(full_key, disk_value, None)
                return disk_value

            self._stats.misses += 1
            return default

    def set(
        self,
        key: str,
        value: T,
        ttl: Optional[int] = None,
        namespace: Optional[str] = None
    ) -> None:
        """
        Set value in cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds (None = use default)
            namespace: Cache namespace
        """
        full_key = self._make_key(key, namespace)
        actual_ttl = ttl if ttl is not None else self._default_ttl

        with self._lock:
            self._set_memory(full_key, value, actual_ttl)

    def _set_memory(
        self,
        key: str,
        value: Any,
        ttl: Optional[int]
    ) -> None:
        """Set value in memory cache."""
        size = self._estimate_size(value)
        now = time.time()

        entry = CacheEntry(
            value=value,
            created_at=now,
            expires_at=now + ttl if ttl else None,
            size_bytes=size
        )

        # Evict if needed
        while self._memory_size + size > self._max_memory_bytes and self._memory:
            self._evict_oldest()

        # Remove existing entry if present
        if key in self._memory:
            old_entry = self._memory.pop(key)
            self._memory_size -= old_entry.size_bytes

        # Add new entry
        self._memory[key] = entry
        self._memory_size += size
        self._stats.entry_count = len(self._memory)
        self._stats.size_bytes = self._memory_size

    def _evict(self, key: str) -> None:
        """Evict a specific key."""
        if key in self._memory:
            entry = self._memory.pop(key)
            self._memory_size -= entry.size_bytes
            self._stats.evictions += 1
            self._stats.entry_count = len(self._memory)
            self._stats.size_bytes = self._memory_size

    def _evict_oldest(self) -> None:
        """Evict oldest entry (LRU)."""
        if self._memory:
            key, entry = self._memory.popitem(last=False)
            self._memory_size -= entry.size_bytes
            self._stats.evictions += 1

            # Optionally persist to disk before eviction
            if entry.expires_at is None or time.time() < entry.expires_at:
                self._set_disk(key, entry)

    def _get_disk_path(self, key: str) -> Path:
        """Get disk cache path for key."""
        key_hash = hashlib.md5(key.encode()).hexdigest()
        return self._cache_dir / f"{key_hash}.cache"

    def _get_from_disk(self, key: str) -> Optional[Any]:
        """Get value from disk cache."""
        path = self._get_disk_path(key)

        if not path.exists():
            return None

        try:
            with open(path) as f:
                data = json.load(f)

            # Check expiration
            if data.get("expires_at") and time.time() > data["expires_at"]:
                path.unlink(missing_ok=True)
                return None

            return data.get("value")

        except (json.JSONDecodeError, IOError):
            return None

    def _set_disk(self, key: str, entry: CacheEntry) -> None:
        """Set value in disk cache."""
        path = self._get_disk_path(key)

        try:
            data = {
                "key": key,
                "value": entry.value,
                "created_at": entry.created_at,
                "expires_at": entry.expires_at,
            }

            with open(path, 'w') as f:
                json.dump(data, f)

        except (TypeError, IOError):
            pass  # Skip non-serializable values

    def delete(self, key: str, namespace: Optional[str] = None) -> bool:
        """Delete key from cache."""
        full_key = self._make_key(key, namespace)

        with self._lock:
            deleted = False

            if full_key in self._memory:
                self._evict(full_key)
                deleted = True

            disk_path = self._get_disk_path(full_key)
            if disk_path.exists():
                disk_path.unlink()
                deleted = True

            return deleted

    def clear(self, namespace: Optional[str] = None) -> int:
        """Clear cache entries."""
        with self._lock:
            if namespace:
                # Clear only namespace
                prefix = f"{namespace}:"
                keys_to_delete = [k for k in self._memory if k.startswith(prefix)]
                for key in keys_to_delete:
                    self._evict(key)
                return len(keys_to_delete)
            else:
                # Clear all
                count = len(self._memory)
                self._memory.clear()
                self._memory_size = 0
                self._stats.entry_count = 0
                self._stats.size_bytes = 0
                return count

    def cached(
        self,
        ttl: Optional[int] = None,
        namespace: Optional[str] = None,
        key_func: Optional[Callable[..., str]] = None
    ) -> Callable:
        """
        Decorator for caching function results.

        Args:
            ttl: Time-to-live in seconds
            namespace: Cache namespace
            key_func: Custom function to generate cache key

        Example:
            @cache.cached(ttl=600, namespace="api")
            def fetch_data(url):
                ...
        """
        def decorator(func: Callable) -> Callable:
            def wrapper(*args, **kwargs):
                # Generate cache key
                if key_func:
                    cache_key = key_func(*args, **kwargs)
                else:
                    key_parts = [func.__name__]
                    key_parts.extend(str(a) for a in args)
                    key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
                    cache_key = ":".join(key_parts)

                # Try cache
                result = self.get(cache_key, namespace=namespace)
                if result is not None:
                    return result

                # Compute and cache
                result = func(*args, **kwargs)
                self.set(cache_key, result, ttl=ttl, namespace=namespace)
                return result

            return wrapper
        return decorator

    @property
    def stats(self) -> CacheStats:
        """Get cache statistics."""
        return self._stats

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics as dictionary."""
        return self._stats.to_dict()


__all__ = ['CacheManager', 'CacheEntry', 'CacheStats']
