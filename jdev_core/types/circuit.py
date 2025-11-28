"""
Unified Circuit Breaker Types.

SCALE & SUSTAIN Phase 1.3 - Type Consolidation.

Consolidated from:
- jdev_cli/core/llm.py:44 (simple dataclass)
- jdev_tui/core/llm_client.py:33 (async with stats)

Author: JuanCS Dev
Date: 2025-11-26
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, List, Tuple
import asyncio
import time


class CircuitState(Enum):
    """
    Circuit breaker states.

    CLOSED: Normal operation, requests pass through
    OPEN: Service failing, requests rejected immediately
    HALF_OPEN: Testing recovery, limited requests allowed
    """
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker behavior."""
    failure_threshold: int = 5       # Failures before opening
    success_threshold: int = 2       # Successes before closing from half-open
    recovery_timeout: float = 30.0   # Seconds before trying half-open
    half_open_max_calls: int = 3     # Max calls in half-open state


@dataclass
class CircuitBreakerStats:
    """Statistics for observability."""
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    rejected_calls: int = 0
    state_changes: List[Tuple[str, float]] = field(default_factory=list)
    last_failure_time: Optional[float] = None
    last_failure_reason: Optional[str] = None


class CircuitBreaker:
    """
    Unified Circuit Breaker Pattern Implementation.

    Prevents cascading failures by stopping requests to failing services.
    Supports both sync and async usage patterns.

    Usage (sync):
        breaker = CircuitBreaker()
        can_try, msg = breaker.can_attempt()
        if can_try:
            try:
                result = external_call()
                breaker.record_success()
            except Exception:
                breaker.record_failure()

    Usage (async context manager):
        async with breaker.call():
            result = await external_service()
    """

    def __init__(
        self,
        name: str = "default",
        config: Optional[CircuitBreakerConfig] = None
    ):
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: Optional[float] = None
        self._half_open_calls = 0
        self._lock = asyncio.Lock()
        self.stats = CircuitBreakerStats()

    @property
    def state(self) -> CircuitState:
        """Get current state, checking for timeout transition."""
        if self._state == CircuitState.OPEN:
            if self._last_failure_time:
                elapsed = time.time() - self._last_failure_time
                if elapsed >= self.config.recovery_timeout:
                    return CircuitState.HALF_OPEN
        return self._state

    @property
    def is_closed(self) -> bool:
        return self.state == CircuitState.CLOSED

    @property
    def is_open(self) -> bool:
        return self.state == CircuitState.OPEN

    @property
    def is_half_open(self) -> bool:
        return self.state == CircuitState.HALF_OPEN

    def can_attempt(self) -> Tuple[bool, str]:
        """
        Check if request can be attempted (sync API).

        Returns:
            Tuple of (can_proceed, reason_message)
        """
        current_state = self.state

        if current_state == CircuitState.CLOSED:
            return True, "Circuit closed"

        if current_state == CircuitState.OPEN:
            return False, "Circuit open (cooling down)"

        # HALF_OPEN state
        if self._half_open_calls < self.config.half_open_max_calls:
            self._half_open_calls += 1
            return True, f"Circuit half-open (test {self._half_open_calls}/{self.config.half_open_max_calls})"

        return False, "Circuit half-open limit reached"

    def record_success(self) -> None:
        """Record successful call."""
        self.stats.total_calls += 1
        self.stats.successful_calls += 1
        self._failure_count = 0

        if self._state == CircuitState.HALF_OPEN:
            self._success_count += 1
            if self._success_count >= self.config.success_threshold:
                self._transition_to(CircuitState.CLOSED)

    def record_failure(self, reason: Optional[str] = None) -> None:
        """Record failed call."""
        self.stats.total_calls += 1
        self.stats.failed_calls += 1
        self._failure_count += 1
        self._last_failure_time = time.time()
        self.stats.last_failure_time = self._last_failure_time
        self.stats.last_failure_reason = reason

        if self._state == CircuitState.HALF_OPEN:
            # Any failure in half-open immediately opens
            self._transition_to(CircuitState.OPEN)
        elif self._failure_count >= self.config.failure_threshold:
            self._transition_to(CircuitState.OPEN)

    def _transition_to(self, new_state: CircuitState) -> None:
        """Internal state transition with logging."""
        if self._state != new_state:
            self.stats.state_changes.append((new_state.value, time.time()))
            self._state = new_state

            if new_state == CircuitState.HALF_OPEN:
                self._half_open_calls = 0
                self._success_count = 0
            elif new_state == CircuitState.CLOSED:
                self._failure_count = 0

    def reset(self) -> None:
        """Force reset to closed state."""
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._half_open_calls = 0
        self._last_failure_time = None


# Backward compatibility alias (simple dataclass version)
@dataclass
class SimpleCircuitBreaker:
    """
    Simple dataclass-based circuit breaker for backward compatibility.

    Deprecated: Use CircuitBreaker class for new code.
    """
    failure_threshold: int = 5
    recovery_timeout: float = 60.0
    half_open_max_calls: int = 3

    failures: int = 0
    state: CircuitState = CircuitState.CLOSED
    last_failure_time: Optional[float] = None
    half_open_calls: int = 0

    def record_success(self) -> None:
        self.failures = 0
        if self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.CLOSED

    def record_failure(self) -> None:
        self.failures += 1
        self.last_failure_time = time.time()
        if self.failures >= self.failure_threshold:
            self.state = CircuitState.OPEN

    def can_attempt(self) -> Tuple[bool, str]:
        if self.state == CircuitState.CLOSED:
            return True, "Circuit closed"

        if self.state == CircuitState.OPEN:
            if self.last_failure_time and \
               (time.time() - self.last_failure_time) >= self.recovery_timeout:
                self.state = CircuitState.HALF_OPEN
                self.half_open_calls = 0
                return True, "Circuit half-open"
            return False, "Circuit open"

        if self.half_open_calls < self.half_open_max_calls:
            self.half_open_calls += 1
            return True, f"Half-open test {self.half_open_calls}"

        return False, "Half-open limit"


__all__ = [
    'CircuitState',
    'CircuitBreakerConfig',
    'CircuitBreakerStats',
    'CircuitBreaker',
    'SimpleCircuitBreaker',  # Backward compat
]
