"""Tests for Day 7 recovery enhancements.

Tests:
- RetryPolicy (exponential backoff, jitter, smart decisions)
- RecoveryCircuitBreaker (state transitions, failure detection)
"""

import time

from jdev_cli.core.recovery import (
    RetryPolicy,
    RecoveryCircuitBreaker
)


class TestRetryPolicy:
    """Test retry policy with exponential backoff."""

    def test_initialization(self):
        """Test retry policy initialization."""
        policy = RetryPolicy(
            base_delay=1.0,
            max_delay=60.0,
            exponential_base=2.0,
            jitter=True
        )

        assert policy.base_delay == 1.0
        assert policy.max_delay == 60.0
        assert policy.exponential_base == 2.0
        assert policy.jitter is True

    def test_exponential_backoff_calculation(self):
        """Test exponential backoff delay calculation."""
        policy = RetryPolicy(base_delay=1.0, jitter=False)

        # Attempt 1: 1.0 * (2^0) = 1.0
        assert policy.get_delay(1) == 1.0

        # Attempt 2: 1.0 * (2^1) = 2.0
        assert policy.get_delay(2) == 2.0

        # Attempt 3: 1.0 * (2^2) = 4.0
        assert policy.get_delay(3) == 4.0

        # Attempt 4: 1.0 * (2^3) = 8.0
        assert policy.get_delay(4) == 8.0

    def test_max_delay_enforcement(self):
        """Test max delay cap is enforced."""
        policy = RetryPolicy(
            base_delay=1.0,
            max_delay=10.0,
            jitter=False
        )

        # Attempt 10: would be 512, but capped at 10
        delay = policy.get_delay(10)
        assert delay == 10.0

    def test_jitter_adds_randomness(self):
        """Test jitter adds random variation."""
        policy = RetryPolicy(base_delay=10.0, jitter=True)

        delays = [policy.get_delay(1) for _ in range(100)]

        # All delays should be different (due to jitter)
        assert len(set(delays)) > 50  # At least 50 unique values

        # All delays should be in range [10.0, 12.5] (10 + 25% jitter)
        assert all(10.0 <= d <= 12.5 for d in delays)

    def test_should_retry_max_attempts(self):
        """Test won't retry beyond max attempts."""
        policy = RetryPolicy()

        assert policy.should_retry(1, 3, Exception("test")) is True
        assert policy.should_retry(2, 3, Exception("test")) is True
        assert policy.should_retry(3, 3, Exception("test")) is False
        assert policy.should_retry(4, 3, Exception("test")) is False

    def test_should_retry_keyboard_interrupt(self):
        """Test won't retry on keyboard interrupt."""
        policy = RetryPolicy()

        assert policy.should_retry(1, 3, KeyboardInterrupt()) is False
        assert policy.should_retry(1, 3, SystemExit()) is False

    def test_should_retry_transient_errors(self):
        """Test retries on transient errors."""
        policy = RetryPolicy()

        transient_errors = [
            Exception("Connection timeout"),
            Exception("Request timed out"),
            Exception("Service temporarily unavailable"),
            Exception("Rate limit exceeded"),
            Exception("Bad gateway 502"),
        ]

        for error in transient_errors:
            assert policy.should_retry(1, 3, error) is True

    def test_should_not_retry_permanent_errors(self):
        """Test won't retry on permanent errors."""
        policy = RetryPolicy()

        permanent_errors = [
            Exception("File not found"),
            Exception("404 Not Found"),
            Exception("Unauthorized 401"),
            Exception("Forbidden 403"),
            Exception("Invalid syntax"),
        ]

        for error in permanent_errors:
            assert policy.should_retry(1, 3, error) is False


class TestRecoveryCircuitBreaker:
    """Test circuit breaker pattern."""

    def test_initialization(self):
        """Test circuit breaker initialization."""
        breaker = RecoveryCircuitBreaker(
            failure_threshold=5,
            success_threshold=2,
            timeout=60.0
        )

        assert breaker.failure_threshold == 5
        assert breaker.success_threshold == 2
        assert breaker.timeout == 60.0
        assert breaker.state == "CLOSED"
        assert breaker.failure_count == 0

    def test_closed_allows_requests(self):
        """Test CLOSED state allows all requests."""
        breaker = RecoveryCircuitBreaker()

        allowed, reason = breaker.should_allow_recovery()
        assert allowed is True
        assert "closed" in reason.lower()

    def test_opens_on_threshold_failures(self):
        """Test circuit opens after threshold failures."""
        breaker = RecoveryCircuitBreaker(failure_threshold=3)

        # Record 3 failures
        for _ in range(3):
            breaker.record_failure()

        assert breaker.state == "OPEN"
        assert breaker.failure_count == 3

    def test_open_rejects_requests(self):
        """Test OPEN state rejects requests."""
        breaker = RecoveryCircuitBreaker(failure_threshold=1, timeout=60.0)

        # Open the circuit
        breaker.record_failure()
        assert breaker.state == "OPEN"

        # Should reject
        allowed, reason = breaker.should_allow_recovery()
        assert allowed is False
        assert "open" in reason.lower()

    def test_half_open_after_timeout(self):
        """Test transitions to HALF_OPEN after timeout."""
        breaker = RecoveryCircuitBreaker(failure_threshold=1, timeout=0.1)

        # Open the circuit
        breaker.record_failure()
        assert breaker.state == "OPEN"

        # Wait for timeout
        time.sleep(0.15)

        # Should transition to HALF_OPEN
        allowed, reason = breaker.should_allow_recovery()
        assert allowed is True
        assert breaker.state == "HALF_OPEN"
        assert "half-open" in reason.lower()

    def test_closes_on_success_threshold(self):
        """Test closes after success threshold in HALF_OPEN."""
        breaker = RecoveryCircuitBreaker(
            failure_threshold=1,
            success_threshold=2,
            timeout=0.1
        )

        # Open and wait
        breaker.record_failure()
        time.sleep(0.15)
        breaker.should_allow_recovery()  # Trigger HALF_OPEN

        assert breaker.state == "HALF_OPEN"

        # Record 2 successes
        breaker.record_success()
        assert breaker.state == "HALF_OPEN"

        breaker.record_success()
        assert breaker.state == "CLOSED"
        assert breaker.failure_count == 0

    def test_reopens_on_failure_in_half_open(self):
        """Test reopens on failure during HALF_OPEN."""
        breaker = RecoveryCircuitBreaker(failure_threshold=1, timeout=0.1)

        # Open and wait
        breaker.record_failure()
        time.sleep(0.15)
        breaker.should_allow_recovery()  # Trigger HALF_OPEN

        assert breaker.state == "HALF_OPEN"

        # Fail again
        breaker.record_failure()
        assert breaker.state == "OPEN"

    def test_get_status(self):
        """Test get_status returns correct info."""
        breaker = RecoveryCircuitBreaker()

        status = breaker.get_status()

        assert status['state'] == 'CLOSED'
        assert status['failure_count'] == 0
        assert status['success_count'] == 0
        assert 'failure_threshold' in status
        assert 'success_threshold' in status

    def test_reset(self):
        """Test reset clears state."""
        breaker = RecoveryCircuitBreaker(failure_threshold=1)

        # Open circuit
        breaker.record_failure()
        assert breaker.state == "OPEN"

        # Reset
        breaker.reset()
        assert breaker.state == "CLOSED"
        assert breaker.failure_count == 0
        assert breaker.success_count == 0

    def test_prevents_cascading_failures(self):
        """Test circuit breaker prevents cascading failures."""
        breaker = RecoveryCircuitBreaker(failure_threshold=5)

        # Simulate cascading failures
        failures = 0
        for attempt in range(20):
            allowed, _ = breaker.should_allow_recovery()

            if allowed:
                # Simulate failure
                breaker.record_failure()
                failures += 1
            else:
                # Circuit open, prevented attempt
                break

        # Should have stopped at 5 failures
        assert failures == 5
        assert breaker.state == "OPEN"
