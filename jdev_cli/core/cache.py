"""Performance cache system (Cursor pattern).

3-tier cache: Memory → Disk → Miss
Boris Cherny: Simple, measurable, no magic.
"""

import hashlib
import json
import time
import sqlite3
from pathlib import Path
from typing import Optional, Any
from collections import OrderedDict
from dataclasses import dataclass


@dataclass
class CacheStats:
    """Cache performance statistics."""

    hits: int = 0
    misses: int = 0
    memory_hits: int = 0
    disk_hits: int = 0

    @property
    def hit_rate(self) -> float:
        """Calculate hit rate."""
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0


class LRUCache:
    """Memory cache with LRU eviction (Cursor L1 cache)."""

    def __init__(self, maxsize: int = 1000):
        self._cache: OrderedDict = OrderedDict()
        self._maxsize = maxsize

    def get(self, key: str) -> Optional[Any]:
        """Get value, update LRU order."""
        if key in self._cache:
            self._cache.move_to_end(key)
            return self._cache[key]
        return None

    def set(self, key: str, value: Any) -> None:
        """Set value, evict if needed."""
        if key in self._cache:
            self._cache.move_to_end(key)
        else:
            self._cache[key] = value
            if len(self._cache) > self._maxsize:
                self._cache.popitem(last=False)

    def clear(self) -> None:
        """Clear all cached items."""
        self._cache.clear()

    @property
    def size(self) -> int:
        """Get current cache size."""
        return len(self._cache)


class DiskCache:
    """SQLite-based disk cache (Cursor L2 cache)."""

    def __init__(self, db_path: str = "~/.qwen-dev-cli/cache.db"):
        self.db_path = Path(db_path).expanduser()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        """Initialize SQLite database."""
        conn = sqlite3.connect(str(self.db_path))
        conn.execute("""
            CREATE TABLE IF NOT EXISTS cache (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                timestamp REAL NOT NULL,
                ttl REAL NOT NULL
            )
        """)
        conn.commit()
        conn.close()

    def get(self, key: str) -> Optional[Any]:
        """Get value if not expired."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.execute(
            "SELECT value, timestamp, ttl FROM cache WHERE key = ?",
            (key,)
        )
        row = cursor.fetchone()
        conn.close()

        if row:
            value_json, timestamp, ttl = row
            if time.time() - timestamp < ttl:
                return json.loads(value_json)
            else:
                # Expired, remove
                self.delete(key)

        return None

    def set(self, key: str, value: Any, ttl: float = 3600) -> None:
        """Set value with TTL (default 1 hour)."""
        conn = sqlite3.connect(str(self.db_path))
        conn.execute(
            "INSERT OR REPLACE INTO cache (key, value, timestamp, ttl) VALUES (?, ?, ?, ?)",
            (key, json.dumps(value), time.time(), ttl)
        )
        conn.commit()
        conn.close()

    def delete(self, key: str):
        """Delete cached value."""
        conn = sqlite3.connect(str(self.db_path))
        conn.execute("DELETE FROM cache WHERE key = ?", (key,))
        conn.commit()
        conn.close()

    def clear_expired(self):
        """Remove expired entries."""
        conn = sqlite3.connect(str(self.db_path))
        conn.execute(
            "DELETE FROM cache WHERE (? - timestamp) > ttl",
            (time.time(),)
        )
        conn.commit()
        conn.close()


class PerformanceCache:
    """3-tier cache system (Cursor pattern).
    
    L1: Memory (100ms)
    L2: Disk (500ms)
    L3: Miss (full execution)
    """

    def __init__(
        self,
        memory_size: int = 1000,
        disk_path: str = "~/.qwen-dev-cli/cache.db"
    ):
        self._memory = LRUCache(memory_size)
        self._disk = DiskCache(disk_path)
        self._stats = CacheStats()

    def get(self, key: str) -> Optional[Any]:
        """Get from cache (L1 → L2 → Miss)."""
        # Try L1 (memory)
        value = self._memory.get(key)
        if value is not None:
            self._stats.hits += 1
            self._stats.memory_hits += 1
            return value

        # Try L2 (disk)
        value = self._disk.get(key)
        if value is not None:
            self._stats.hits += 1
            self._stats.disk_hits += 1
            # Promote to L1
            self._memory.set(key, value)
            return value

        # Miss
        self._stats.misses += 1
        return None

    def set(self, key: str, value: Any, ttl: float = 3600) -> None:
        """Set value in all tiers."""
        self._memory.set(key, value)
        self._disk.set(key, value, ttl)

    def clear(self) -> None:
        """Clear all caches."""
        self._memory.clear()
        # Don't clear disk by default (persistent)

    @property
    def stats(self) -> CacheStats:
        """Get cache statistics."""
        return self._stats

    def cleanup(self):
        """Cleanup expired disk entries."""
        self._disk.clear_expired()


def cache_key(*args, **kwargs) -> str:
    """Generate cache key from arguments.
    
    Uses SHA256 hash of JSON-serialized args.
    """
    data = json.dumps({"args": args, "kwargs": kwargs}, sort_keys=True)
    return hashlib.sha256(data.encode()).hexdigest()


# Global cache instance
_cache: Optional[PerformanceCache] = None


def get_cache() -> PerformanceCache:
    """Get global cache instance (singleton)."""
    global _cache
    if _cache is None:
        _cache = PerformanceCache()
    return _cache
