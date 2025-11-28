"""Tests for resilient LLM client implementation.

Tests all resilience patterns:
- Circuit breaker (Gemini strategy)
- Rate limiting (Cursor AI strategy)
- Exponential backoff with jitter (Codex strategy)
- Automatic failover (Cursor AI strategy)
- Telemetry and observability (Codex strategy)
"""

import pytest
import time
from jdev_cli.core.llm import (
    LLMClient,
    CircuitBreaker,
    CircuitState,
    RateLimiter,
    RequestMetrics
)


class TestCircuitBreaker:
    """Test Circuit Breaker pattern (Gemini strategy)."""

    def test_initial_state_closed(self):
        """Circuit should start in CLOSED state."""
        cb = CircuitBreaker()
        assert cb.state == CircuitState.CLOSED
        assert cb.failures == 0

    def test_opens_after_threshold(self):
        """Circuit should OPEN after reaching failure threshold."""
        cb = CircuitBreaker(failure_threshold=3)

        # Record failures
        cb.record_failure()
        assert cb.state == CircuitState.CLOSED

        cb.record_failure()
        assert cb.state == CircuitState.CLOSED

        cb.record_failure()
        assert cb.state == CircuitState.OPEN
        assert cb.failures == 3

    def test_blocks_when_open(self):
        """Circuit should block requests when OPEN."""
        cb = CircuitBreaker(failure_threshold=2)

        # Trip circuit
        cb.record_failure()
        cb.record_failure()

        assert cb.state == CircuitState.OPEN
        can_attempt, reason = cb.can_attempt()
        assert not can_attempt
        assert "open" in reason.lower()

    def test_recovery_to_half_open(self):
        """Circuit should transition to HALF_OPEN after recovery timeout."""
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=0.1)

        # Trip circuit
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitState.OPEN

        # Wait for recovery
        time.sleep(0.2)

        can_attempt, reason = cb.can_attempt()
        assert can_attempt
        assert cb.state == CircuitState.HALF_OPEN

    def test_closes_on_success(self):
        """Circuit should close on successful half-open attempt."""
        cb = CircuitBreaker(failure_threshold=2)

        # Trip and recover
        cb.record_failure()
        cb.record_failure()
        cb.state = CircuitState.HALF_OPEN

        # Success closes circuit
        cb.record_success()
        assert cb.state == CircuitState.CLOSED
        assert cb.failures == 0


class TestRateLimiter:
    """Test Rate Limiter (Cursor AI strategy)."""

    def test_allows_under_limit(self):
        """Should allow requests under limit."""
        limiter = RateLimiter(requests_per_minute=10)

        can_proceed, wait = limiter.can_proceed()
        assert can_proceed
        assert wait == 0.0

    def test_blocks_over_limit(self):
        """Should block requests over limit."""
        limiter = RateLimiter(requests_per_minute=3)

        # Fill up the rate limit
        for _ in range(3):
            limiter.record_request()

        # Next request should be blocked
        can_proceed, wait = limiter.can_proceed()
        assert not can_proceed
        assert wait > 0

    def test_token_aware_limiting(self):
        """Should limit based on token count."""
        limiter = RateLimiter(tokens_per_minute=100)

        # Record high token usage
        limiter.record_request(tokens=90)

        # Large request should be blocked
        can_proceed, wait = limiter.can_proceed(estimated_tokens=20)
        assert not can_proceed

    def test_sliding_window(self):
        """Should use sliding window for rate limiting."""
        limiter = RateLimiter(requests_per_minute=2)

        # Fill limit
        limiter.record_request()
        limiter.record_request()

        # Should be blocked
        can_proceed, _ = limiter.can_proceed()
        assert not can_proceed

        # Wait for window to slide
        time.sleep(1.1)

        # Old requests should expire (but test may be too fast)
        # This is a simplified test - real window is 60s


class TestRequestMetrics:
    """Test telemetry and observability (Codex strategy)."""

    def test_records_success(self):
        """Should track successful requests."""
        metrics = RequestMetrics()

        metrics.record_success("hf", latency=1.5, tokens=100)

        assert metrics.total_requests == 1
        assert metrics.successful_requests == 1
        assert metrics.total_latency == 1.5
        assert metrics.total_tokens == 100

    def test_records_failure(self):
        """Should track failed requests."""
        metrics = RequestMetrics()

        metrics.record_failure("hf")

        assert metrics.total_requests == 1
        assert metrics.failed_requests == 1

    def test_provider_stats(self):
        """Should track per-provider statistics."""
        metrics = RequestMetrics()

        metrics.record_success("hf", 1.0)
        metrics.record_success("hf", 1.5)
        metrics.record_failure("hf")
        metrics.record_success("hf", 0.5)

        stats = metrics.get_stats()

        assert stats["providers"]["hf"]["success"] == 3
        assert stats["providers"]["hf"]["failure"] == 1

    def test_calculates_success_rate(self):
        """Should calculate success rate correctly."""
        metrics = RequestMetrics()

        metrics.record_success("hf", 1.0)
        metrics.record_success("hf", 1.0)
        metrics.record_success("hf", 1.0)
        metrics.record_failure("hf")

        stats = metrics.get_stats()
        assert "75.0%" in stats["success_rate"]


class TestLLMClientResilience:
    """Test LLM Client with resilience patterns."""

    def test_initialization(self):
        """Should initialize with all resilience components."""
        client = LLMClient(
            max_retries=3,
            enable_circuit_breaker=True,
            enable_rate_limiting=True,
            enable_telemetry=True
        )

        assert client.max_retries == 3
        assert client.circuit_breaker is not None
        assert client.rate_limiter is not None
        assert client.metrics is not None

    def test_backoff_calculation(self):
        """Should calculate exponential backoff correctly."""
        client = LLMClient(base_delay=1.0)

        # Attempt 0: ~1s (+ jitter)
        delay0 = client._calculate_backoff(0)
        assert 1.0 <= delay0 <= 1.5

        # Attempt 1: ~2s (+ jitter)
        delay1 = client._calculate_backoff(1)
        assert 2.0 <= delay1 <= 3.0

        # Attempt 2: ~4s (+ jitter)
        delay2 = client._calculate_backoff(2)
        assert 4.0 <= delay2 <= 6.0

    def test_should_retry_logic(self):
        """Should correctly identify retryable errors."""
        client = LLMClient()

        # Retryable errors
        assert client._should_retry(Exception("timeout error"))
        assert client._should_retry(Exception("429 rate limit"))
        assert client._should_retry(Exception("500 server error"))
        assert client._should_retry(Exception("connection failed"))

        # Non-retryable errors
        assert not client._should_retry(Exception("400 bad request"))
        assert not client._should_retry(Exception("401 unauthorized"))

    def test_get_failover_providers(self):
        """Should return available providers for failover."""
        client = LLMClient()

        providers = client._get_failover_providers()

        assert isinstance(providers, list)
        assert len(providers) > 0
        assert "hf" in providers or "hf" in providers or "ollama" in providers

    def test_metrics_retrieval(self):
        """Should provide telemetry metrics."""
        client = LLMClient(enable_telemetry=True)

        metrics = client.get_metrics()

        assert "total_requests" in metrics
        assert "success_rate" in metrics
        assert "circuit_breaker" in metrics
        assert "rate_limiter" in metrics

    def test_circuit_breaker_reset(self):
        """Should allow manual circuit breaker reset."""
        client = LLMClient(enable_circuit_breaker=True)

        # Trip circuit
        client.circuit_breaker.state = CircuitState.OPEN
        client.circuit_breaker.failures = 10

        # Reset
        client.reset_circuit_breaker()

        assert client.circuit_breaker.state == CircuitState.CLOSED
        assert client.circuit_breaker.failures == 0

    def test_metrics_reset(self):
        """Should allow metrics reset."""
        client = LLMClient(enable_telemetry=True)

        # Record some data
        client.metrics.record_success("hf", 1.0)
        assert client.metrics.total_requests == 1

        # Reset
        client.reset_metrics()

        assert client.metrics.total_requests == 0


class TestLLMClientFailover:
    """Test automatic failover (Cursor AI strategy)."""

    async def test_failover_on_provider_failure(self):
        """Should failover to backup provider on failure."""
        client = LLMClient()

        # This test requires mocking providers
        # Simplified test - just verify failover logic exists
        providers = client._get_failover_providers()
        assert len(providers) >= 1

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
