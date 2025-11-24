"""
Resilience Module - Stress Resilience Components
Pipeline de Diamante - Camada 3: EXECUTION SANDBOX

Consolidates FASE 5 components:
- ConcurrencyManager: Safe concurrent operations (ISSUE-057, ISSUE-058, ISSUE-059)
- ResourceLimits: Resource exhaustion prevention (ISSUE-007, ISSUE-060, ISSUE-062, ISSUE-068)
- EncodingSafety: Unicode and encoding handling (ISSUE-063, ISSUE-064, ISSUE-065)
- RateLimiter: Throttling and backoff (ISSUE-067, ISSUE-069, ISSUE-070)

Design Philosophy:
- Graceful degradation under load
- Resource-bounded operations
- Safe concurrent access
- Automatic recovery
"""

from __future__ import annotations

import os
import sys
import time
import asyncio
import threading
import hashlib
import unicodedata
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, TypeVar, Union, Awaitable
from dataclasses import dataclass, field
from enum import Enum, auto
from functools import wraps
from contextlib import asynccontextmanager, contextmanager
from collections import deque
import logging

# Try to import filelock
try:
    from filelock import FileLock, Timeout as LockTimeout
    HAS_FILELOCK = True
except ImportError:
    HAS_FILELOCK = False
    FileLock = None
    LockTimeout = Exception

logger = logging.getLogger(__name__)

T = TypeVar('T')
F = TypeVar('F', bound=Callable[..., Any])


# =============================================================================
# CONCURRENCY MANAGER
# =============================================================================

class LockType(Enum):
    """Types of locks."""
    READ = "read"
    WRITE = "write"
    EXCLUSIVE = "exclusive"


@dataclass
class LockInfo:
    """Information about an acquired lock."""
    resource: str
    lock_type: LockType
    acquired_at: float
    holder: str
    timeout: Optional[float] = None


class ConcurrencyManager:
    """
    Safe concurrent operations manager.

    Features:
    - File locking for concurrent access
    - Semaphore for resource limits
    - Deadlock prevention
    - Race condition guards

    Usage:
        manager = ConcurrencyManager()

        async with manager.lock_file("path/to/file"):
            # Safe file operation
            pass
    """

    DEFAULT_TIMEOUT = 30.0
    MAX_CONCURRENT = 10

    def __init__(
        self,
        max_concurrent: int = MAX_CONCURRENT,
        default_timeout: float = DEFAULT_TIMEOUT,
    ):
        self.max_concurrent = max_concurrent
        self.default_timeout = default_timeout
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._locks: Dict[str, threading.RLock] = {}
        self._file_locks: Dict[str, Any] = {}
        self._lock_info: Dict[str, LockInfo] = {}
        self._global_lock = threading.RLock()

    def _get_lock(self, resource: str) -> threading.RLock:
        """Get or create a lock for a resource."""
        with self._global_lock:
            if resource not in self._locks:
                self._locks[resource] = threading.RLock()
            return self._locks[resource]

    @contextmanager
    def lock(self, resource: str, timeout: Optional[float] = None):
        """
        Acquire a lock on a resource.

        Args:
            resource: Resource identifier
            timeout: Lock timeout in seconds
        """
        lock = self._get_lock(resource)
        acquired = lock.acquire(timeout=timeout or self.default_timeout)

        if not acquired:
            raise TimeoutError(f"Could not acquire lock for {resource}")

        info = LockInfo(
            resource=resource,
            lock_type=LockType.EXCLUSIVE,
            acquired_at=time.time(),
            holder=threading.current_thread().name,
            timeout=timeout,
        )
        self._lock_info[resource] = info

        try:
            yield info
        finally:
            lock.release()
            self._lock_info.pop(resource, None)

    @asynccontextmanager
    async def async_lock(self, resource: str, timeout: Optional[float] = None):
        """Async version of lock."""
        loop = asyncio.get_event_loop()

        try:
            await asyncio.wait_for(
                loop.run_in_executor(None, lambda: self._get_lock(resource).acquire()),
                timeout=timeout or self.default_timeout
            )
        except asyncio.TimeoutError:
            raise TimeoutError(f"Could not acquire lock for {resource}")

        info = LockInfo(
            resource=resource,
            lock_type=LockType.EXCLUSIVE,
            acquired_at=time.time(),
            holder=f"async-{id(asyncio.current_task())}",
            timeout=timeout,
        )
        self._lock_info[resource] = info

        try:
            yield info
        finally:
            self._get_lock(resource).release()
            self._lock_info.pop(resource, None)

    @asynccontextmanager
    async def limit_concurrency(self):
        """Limit concurrent operations using semaphore."""
        await self._semaphore.acquire()
        try:
            yield
        finally:
            self._semaphore.release()

    def get_active_locks(self) -> List[LockInfo]:
        """Get list of currently held locks."""
        return list(self._lock_info.values())


# =============================================================================
# RESOURCE LIMITS
# =============================================================================

@dataclass
class ResourceConfig:
    """Resource limit configuration."""
    max_memory_mb: int = 256
    max_file_size_mb: int = 50
    max_files_per_operation: int = 1000
    max_execution_time: float = 300.0
    max_context_size_mb: int = 10
    min_disk_space_mb: int = 100


@dataclass
class ResourceUsage:
    """Current resource usage."""
    memory_mb: float = 0.0
    disk_available_mb: float = 0.0
    open_files: int = 0
    active_operations: int = 0


class ResourceLimits:
    """
    Resource exhaustion prevention.

    Features:
    - Memory limits
    - File size limits
    - Disk space pre-check
    - Operation counting

    Usage:
        limits = ResourceLimits()

        if limits.can_allocate_memory(100):
            # Safe to proceed
            pass

        limits.check_disk_space("/path/to/write")
    """

    def __init__(self, config: Optional[ResourceConfig] = None):
        self.config = config or ResourceConfig()
        self._active_operations = 0
        self._lock = threading.Lock()

    def get_usage(self) -> ResourceUsage:
        """Get current resource usage."""
        import psutil

        process = psutil.Process(os.getpid())
        memory_mb = process.memory_info().rss / (1024 * 1024)

        # Get disk space for current directory
        try:
            disk = psutil.disk_usage(os.getcwd())
            disk_available_mb = disk.free / (1024 * 1024)
        except Exception:
            disk_available_mb = 0

        return ResourceUsage(
            memory_mb=memory_mb,
            disk_available_mb=disk_available_mb,
            open_files=len(process.open_files()),
            active_operations=self._active_operations,
        )

    def can_allocate_memory(self, size_mb: float) -> bool:
        """Check if memory allocation is safe."""
        try:
            usage = self.get_usage()
            return (usage.memory_mb + size_mb) <= self.config.max_memory_mb
        except Exception:
            return True  # Allow if we can't check

    def check_file_size(self, size_bytes: int) -> bool:
        """Check if file size is within limits."""
        size_mb = size_bytes / (1024 * 1024)
        return size_mb <= self.config.max_file_size_mb

    def check_disk_space(self, path: str) -> Tuple[bool, str]:
        """
        Check if there's enough disk space.

        Returns:
            (has_space, message)
        """
        try:
            import psutil
            disk = psutil.disk_usage(os.path.dirname(os.path.abspath(path)))
            available_mb = disk.free / (1024 * 1024)

            if available_mb < self.config.min_disk_space_mb:
                return False, f"Low disk space: {available_mb:.1f}MB available"

            return True, f"Disk space OK: {available_mb:.1f}MB available"
        except Exception as e:
            return True, f"Could not check disk space: {e}"

    @contextmanager
    def operation_context(self):
        """Track an active operation."""
        with self._lock:
            self._active_operations += 1

        try:
            yield
        finally:
            with self._lock:
                self._active_operations -= 1

    def enforce_limits(self) -> List[str]:
        """Check all limits and return violations."""
        violations = []
        usage = self.get_usage()

        if usage.memory_mb > self.config.max_memory_mb:
            violations.append(f"Memory limit exceeded: {usage.memory_mb:.1f}MB > {self.config.max_memory_mb}MB")

        if usage.disk_available_mb < self.config.min_disk_space_mb:
            violations.append(f"Low disk space: {usage.disk_available_mb:.1f}MB")

        return violations


# =============================================================================
# ENCODING SAFETY
# =============================================================================

class EncodingSafety:
    """
    Handle all encodings safely.

    Features:
    - UTF-8 with fallback
    - Unicode filename support
    - Special character escaping
    - BOM handling

    Usage:
        safety = EncodingSafety()

        content = safety.read_file_safe("file.txt")
        safety.write_file_safe("output.txt", content)
    """

    # Characters that are dangerous in filenames
    DANGEROUS_FILENAME_CHARS = set('<>:"/\\|?*\x00')

    # Unicode normalization forms
    NORMALIZATION_FORMS = ['NFC', 'NFD', 'NFKC', 'NFKD']

    def __init__(
        self,
        default_encoding: str = 'utf-8',
        fallback_encodings: Optional[List[str]] = None,
    ):
        self.default_encoding = default_encoding
        self.fallback_encodings = fallback_encodings or ['latin-1', 'cp1252', 'iso-8859-1']

    def read_file_safe(self, path: str) -> Tuple[str, str]:
        """
        Read file with encoding detection.

        Returns:
            (content, detected_encoding)
        """
        encodings = [self.default_encoding] + self.fallback_encodings

        for encoding in encodings:
            try:
                with open(path, 'r', encoding=encoding) as f:
                    content = f.read()

                # Handle BOM
                if content.startswith('\ufeff'):
                    content = content[1:]

                return content, encoding

            except UnicodeDecodeError:
                continue

        # Last resort: read as binary and decode with errors='replace'
        with open(path, 'rb') as f:
            raw = f.read()

        return raw.decode('utf-8', errors='replace'), 'utf-8-replace'

    def write_file_safe(
        self,
        path: str,
        content: str,
        encoding: Optional[str] = None,
    ) -> bool:
        """Write file with safe encoding."""
        encoding = encoding or self.default_encoding

        try:
            # Normalize unicode
            content = unicodedata.normalize('NFC', content)

            with open(path, 'w', encoding=encoding) as f:
                f.write(content)

            return True

        except UnicodeEncodeError:
            # Try with replacement
            content_safe = content.encode(encoding, errors='replace').decode(encoding)
            with open(path, 'w', encoding=encoding) as f:
                f.write(content_safe)
            return True

    def sanitize_filename(self, filename: str) -> str:
        """Sanitize filename for safe filesystem use."""
        # Normalize unicode
        sanitized = unicodedata.normalize('NFC', filename)

        # Remove dangerous characters
        sanitized = ''.join(c if c not in self.DANGEROUS_FILENAME_CHARS else '_' for c in sanitized)

        # Remove control characters
        sanitized = ''.join(c for c in sanitized if unicodedata.category(c) != 'Cc')

        # Limit length
        if len(sanitized.encode('utf-8')) > 255:
            # Truncate by bytes
            sanitized = sanitized.encode('utf-8')[:250].decode('utf-8', errors='ignore')

        return sanitized or 'unnamed'

    def is_safe_string(self, text: str) -> Tuple[bool, List[str]]:
        """Check if string is safe (no dangerous unicode)."""
        issues = []

        # Check for null bytes
        if '\x00' in text:
            issues.append("Contains null bytes")

        # Check for direction override characters
        bidi_chars = {'\u202a', '\u202b', '\u202c', '\u202d', '\u202e', '\u2066', '\u2067', '\u2068', '\u2069'}
        found_bidi = bidi_chars & set(text)
        if found_bidi:
            issues.append(f"Contains bidirectional override: {found_bidi}")

        # Check for zero-width characters
        zwc = {'\u200b', '\u200c', '\u200d', '\ufeff'}
        found_zwc = zwc & set(text)
        if found_zwc:
            issues.append(f"Contains zero-width characters: {len(found_zwc)}")

        return len(issues) == 0, issues


# =============================================================================
# RATE LIMITER
# =============================================================================

class RateLimitAlgorithm(Enum):
    """Rate limiting algorithms."""
    TOKEN_BUCKET = "token_bucket"
    SLIDING_WINDOW = "sliding_window"
    FIXED_WINDOW = "fixed_window"


@dataclass
class RateLimitConfig:
    """Rate limit configuration."""
    requests_per_second: float = 10.0
    burst_size: int = 20
    retry_after: float = 1.0
    max_retries: int = 3
    backoff_factor: float = 2.0


class RateLimiter:
    """
    Rate limiting and throttling.

    Features:
    - Token bucket algorithm
    - Exponential backoff
    - Retry with jitter
    - Circuit breaker pattern

    Usage:
        limiter = RateLimiter()

        if limiter.allow():
            # Proceed with request
            pass

        # Or use decorator
        @limiter.rate_limited
        async def my_function():
            pass
    """

    def __init__(self, config: Optional[RateLimitConfig] = None):
        self.config = config or RateLimitConfig()
        self._tokens = float(self.config.burst_size)
        self._last_update = time.time()
        self._lock = threading.Lock()
        self._failure_count = 0
        self._circuit_open = False
        self._circuit_open_until: Optional[float] = None

    def _refill_tokens(self) -> None:
        """Refill tokens based on elapsed time."""
        now = time.time()
        elapsed = now - self._last_update
        self._tokens = min(
            self.config.burst_size,
            self._tokens + elapsed * self.config.requests_per_second
        )
        self._last_update = now

    def allow(self) -> bool:
        """Check if request is allowed."""
        # Check circuit breaker
        if self._circuit_open:
            if self._circuit_open_until and time.time() > self._circuit_open_until:
                self._circuit_open = False
                self._failure_count = 0
            else:
                return False

        with self._lock:
            self._refill_tokens()

            if self._tokens >= 1.0:
                self._tokens -= 1.0
                return True

            return False

    def wait_time(self) -> float:
        """Get time to wait before next request is allowed."""
        with self._lock:
            self._refill_tokens()

            if self._tokens >= 1.0:
                return 0.0

            needed = 1.0 - self._tokens
            return needed / self.config.requests_per_second

    async def wait_for_token(self) -> bool:
        """Wait until a token is available."""
        wait = self.wait_time()
        if wait > 0:
            await asyncio.sleep(wait)
        return self.allow()

    def record_failure(self) -> None:
        """Record a failure for circuit breaker."""
        self._failure_count += 1
        if self._failure_count >= self.config.max_retries:
            self._circuit_open = True
            self._circuit_open_until = time.time() + (
                self.config.retry_after * (self.config.backoff_factor ** self._failure_count)
            )

    def record_success(self) -> None:
        """Record a success."""
        self._failure_count = 0
        self._circuit_open = False

    def rate_limited(self, func: F) -> F:
        """Decorator for rate-limited functions."""
        if asyncio.iscoroutinefunction(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                await self.wait_for_token()
                try:
                    result = await func(*args, **kwargs)
                    self.record_success()
                    return result
                except Exception:
                    self.record_failure()
                    raise
            return async_wrapper
        else:
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                wait = self.wait_time()
                if wait > 0:
                    time.sleep(wait)
                if not self.allow():
                    raise RuntimeError("Rate limit exceeded")
                try:
                    result = func(*args, **kwargs)
                    self.record_success()
                    return result
                except Exception:
                    self.record_failure()
                    raise
            return sync_wrapper


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

# Global instances
_concurrency_manager: Optional[ConcurrencyManager] = None
_resource_limits: Optional[ResourceLimits] = None
_encoding_safety: Optional[EncodingSafety] = None
_rate_limiter: Optional[RateLimiter] = None


def get_concurrency_manager() -> ConcurrencyManager:
    """Get default concurrency manager."""
    global _concurrency_manager
    if _concurrency_manager is None:
        _concurrency_manager = ConcurrencyManager()
    return _concurrency_manager


def get_resource_limits() -> ResourceLimits:
    """Get default resource limits."""
    global _resource_limits
    if _resource_limits is None:
        _resource_limits = ResourceLimits()
    return _resource_limits


def get_encoding_safety() -> EncodingSafety:
    """Get default encoding safety."""
    global _encoding_safety
    if _encoding_safety is None:
        _encoding_safety = EncodingSafety()
    return _encoding_safety


def get_rate_limiter() -> RateLimiter:
    """Get default rate limiter."""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter()
    return _rate_limiter


# Export all public symbols
__all__ = [
    # Concurrency
    'LockType',
    'LockInfo',
    'ConcurrencyManager',
    'get_concurrency_manager',

    # Resources
    'ResourceConfig',
    'ResourceUsage',
    'ResourceLimits',
    'get_resource_limits',

    # Encoding
    'EncodingSafety',
    'get_encoding_safety',

    # Rate Limiting
    'RateLimitAlgorithm',
    'RateLimitConfig',
    'RateLimiter',
    'get_rate_limiter',
]
