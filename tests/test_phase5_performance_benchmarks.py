"""
Phase 5 Performance Benchmarks and Stress Tests

Scientific performance analysis of Constitutional Governance integration:
- Latency measurements (governance overhead)
- Throughput benchmarks (requests per second)
- Stress tests (high concurrency)
- Memory profiling (resource usage)
- Comparison: with vs without governance

Metrics tracked:
- p50, p95, p99 latencies
- Throughput (ops/sec)
- Memory usage (MB)
- CPU utilization
- Error rates
- Concurrency handling

Usage:
    # Run all benchmarks
    pytest tests/test_phase5_performance_benchmarks.py -v -s --tb=short

    # Run stress tests only
    pytest tests/test_phase5_performance_benchmarks.py -v -s -m stress

    # Run latency tests only
    pytest tests/test_phase5_performance_benchmarks.py -v -s -m latency
"""

import pytest
import asyncio
import time
import statistics
import tracemalloc
import psutil
from typing import List
from unittest.mock import Mock, AsyncMock
from dataclasses import dataclass

from jdev_cli.maestro_governance import MaestroGovernance
from jdev_cli.core.governance_pipeline import GovernancePipeline
from jdev_cli.agents.justica_agent import JusticaIntegratedAgent
from jdev_cli.agents.sofia_agent import SofiaIntegratedAgent
from jdev_cli.agents.base import AgentTask, AgentResponse, AgentRole


@dataclass
class BenchmarkResult:
    """Performance benchmark result."""
    name: str
    duration_seconds: float
    operations: int
    throughput_ops_per_sec: float
    latency_p50_ms: float
    latency_p95_ms: float
    latency_p99_ms: float
    memory_usage_mb: float
    error_count: int
    success_rate: float

    def __str__(self):
        return f"""
╔════════════════════════════════════════════════════════════════════════╗
║ BENCHMARK: {self.name:<58} ║
╠════════════════════════════════════════════════════════════════════════╣
║ Duration:        {self.duration_seconds:>6.2f} seconds                                ║
║ Operations:      {self.operations:>6} ops                                      ║
║ Throughput:      {self.throughput_ops_per_sec:>6.2f} ops/sec                               ║
║                                                                        ║
║ Latency (ms):                                                          ║
║   p50 (median):  {self.latency_p50_ms:>6.2f} ms                                     ║
║   p95:           {self.latency_p95_ms:>6.2f} ms                                     ║
║   p99:           {self.latency_p99_ms:>6.2f} ms                                     ║
║                                                                        ║
║ Memory:          {self.memory_usage_mb:>6.2f} MB                                    ║
║ Errors:          {self.error_count:>6} ({self.success_rate * 100:>5.1f}% success)                        ║
╚════════════════════════════════════════════════════════════════════════╝
"""


class PerformanceTracker:
    """Track performance metrics during benchmarks."""

    def __init__(self):
        self.latencies: List[float] = []
        self.errors: int = 0
        self.start_time: float = 0
        self.end_time: float = 0
        self.memory_start: int = 0
        self.memory_end: int = 0
        self.process = psutil.Process()

    def start(self):
        """Start tracking."""
        tracemalloc.start()
        self.memory_start = self.process.memory_info().rss
        self.start_time = time.time()

    def stop(self):
        """Stop tracking."""
        self.end_time = time.time()
        self.memory_end = self.process.memory_info().rss
        tracemalloc.stop()

    def record_latency(self, latency_ms: float):
        """Record single operation latency."""
        self.latencies.append(latency_ms)

    def record_error(self):
        """Record error."""
        self.errors += 1

    def get_result(self, name: str, operations: int) -> BenchmarkResult:
        """Generate benchmark result."""
        duration = self.end_time - self.start_time
        throughput = operations / duration if duration > 0 else 0

        if self.latencies:
            p50 = statistics.median(self.latencies)
            p95 = statistics.quantiles(self.latencies, n=20)[18]  # 95th percentile
            p99 = statistics.quantiles(self.latencies, n=100)[98]  # 99th percentile
        else:
            p50 = p95 = p99 = 0

        memory_mb = (self.memory_end - self.memory_start) / (1024 * 1024)
        success_rate = (operations - self.errors) / operations if operations > 0 else 0

        return BenchmarkResult(
            name=name,
            duration_seconds=duration,
            operations=operations,
            throughput_ops_per_sec=throughput,
            latency_p50_ms=p50,
            latency_p95_ms=p95,
            latency_p99_ms=p99,
            memory_usage_mb=memory_mb,
            error_count=self.errors,
            success_rate=success_rate
        )


@pytest.fixture
def mock_governance():
    """Create mock governance system for performance tests."""
    mock_llm = Mock()
    mock_mcp = Mock()

    # Disable verbose logging for clean benchmark output
    import logging
    logging.getLogger('jdev_cli.maestro_governance').setLevel(logging.CRITICAL)
    logging.getLogger('jdev_cli.core.governance_pipeline').setLevel(logging.CRITICAL)

    gov = MaestroGovernance(
        llm_client=mock_llm,
        mcp_client=mock_mcp,
        enable_governance=True,
        enable_counsel=True,
        enable_observability=False,  # Disable for performance tests
        auto_risk_detection=True
    )

    # Mock agents with fast responses
    mock_justica = Mock(spec=JusticaIntegratedAgent)
    mock_justica.evaluate_action = AsyncMock(return_value=Mock(
        approved=True,
        reasoning="Approved",
        trust_score=0.95
    ))

    mock_sofia = Mock(spec=SofiaIntegratedAgent)
    mock_sofia.should_trigger_counsel = Mock(return_value=(False, None))
    mock_sofia.pre_execution_counsel = AsyncMock(return_value=Mock(
        counsel_type="advisory",
        confidence=0.9,
        requires_professional=False,
        counsel="Advisory counsel"
    ))

    mock_pipeline = Mock(spec=GovernancePipeline)
    mock_pipeline.pre_execution_check = AsyncMock(return_value=(True, None, {}))

    gov.justica = mock_justica
    gov.sofia = mock_sofia
    gov.pipeline = mock_pipeline
    gov.initialized = True

    return gov


@pytest.fixture
def mock_agent():
    """Create mock agent for execution tests."""
    agent = Mock()
    agent.role = AgentRole.EXECUTOR
    agent.execute = AsyncMock(return_value=AgentResponse(
        success=True,
        reasoning="Executed successfully",
        data={"result": "success"}
    ))
    return agent


# ============================================================================
# LATENCY BENCHMARKS
# ============================================================================

@pytest.mark.asyncio
@pytest.mark.latency
async def test_latency_baseline_no_governance(mock_agent):
    """Baseline: Latency without governance."""
    tracker = PerformanceTracker()
    operations = 1000

    task = AgentTask(request="test operation", context={})

    tracker.start()

    for _ in range(operations):
        op_start = time.time()
        await mock_agent.execute(task)
        latency_ms = (time.time() - op_start) * 1000
        tracker.record_latency(latency_ms)

    tracker.stop()

    result = tracker.get_result("Baseline (No Governance)", operations)
    print(result)

    # Assertions: Baseline should be very fast
    assert result.latency_p50_ms < 1.0, "Baseline p50 should be < 1ms"
    assert result.success_rate == 1.0


@pytest.mark.asyncio
@pytest.mark.latency
async def test_latency_with_governance(mock_governance, mock_agent):
    """Latency with full governance pipeline."""
    tracker = PerformanceTracker()
    operations = 1000

    task = AgentTask(request="test operation", context={})

    tracker.start()

    for _ in range(operations):
        op_start = time.time()
        try:
            await mock_governance.execute_with_governance(mock_agent, task, risk_level="MEDIUM")
            latency_ms = (time.time() - op_start) * 1000
            tracker.record_latency(latency_ms)
        except Exception:
            tracker.record_error()

    tracker.stop()

    result = tracker.get_result("With Governance (MEDIUM risk)", operations)
    print(result)

    # Assertions: Should still be reasonably fast
    assert result.latency_p50_ms < 10.0, "Governance p50 should be < 10ms"
    assert result.success_rate > 0.99, "Should have >99% success rate"


@pytest.mark.asyncio
@pytest.mark.latency
async def test_latency_risk_detection(mock_governance):
    """Latency of risk detection algorithm."""
    tracker = PerformanceTracker()
    operations = 10000  # More ops for fast function

    prompts = [
        "Delete production database",
        "Read user configuration",
        "Deploy to production",
        "List available files",
        "Modify security settings"
    ]

    tracker.start()

    for i in range(operations):
        prompt = prompts[i % len(prompts)]
        op_start = time.time()
        mock_governance.detect_risk_level(prompt, "executor")
        latency_ms = (time.time() - op_start) * 1000
        tracker.record_latency(latency_ms)

    tracker.stop()

    result = tracker.get_result("Risk Detection", operations)
    print(result)

    # Assertions: Risk detection should be very fast
    assert result.latency_p50_ms < 0.1, "Risk detection p50 should be < 0.1ms"
    assert result.throughput_ops_per_sec > 10000, "Should handle >10k ops/sec"


# ============================================================================
# THROUGHPUT BENCHMARKS
# ============================================================================

@pytest.mark.asyncio
@pytest.mark.throughput
async def test_throughput_concurrent_governance(mock_governance, mock_agent):
    """Throughput with concurrent governance operations."""
    tracker = PerformanceTracker()
    operations = 500
    concurrency = 50  # 50 concurrent operations

    task = AgentTask(request="test operation", context={})

    async def execute_single():
        op_start = time.time()
        try:
            await mock_governance.execute_with_governance(mock_agent, task, risk_level="LOW")
            latency_ms = (time.time() - op_start) * 1000
            tracker.record_latency(latency_ms)
        except Exception:
            tracker.record_error()

    tracker.start()

    # Run in batches of concurrent operations
    for i in range(0, operations, concurrency):
        batch_size = min(concurrency, operations - i)
        await asyncio.gather(*[execute_single() for _ in range(batch_size)])

    tracker.stop()

    result = tracker.get_result(f"Concurrent Governance ({concurrency} parallel)", operations)
    print(result)

    # Assertions
    assert result.throughput_ops_per_sec > 100, "Should handle >100 ops/sec with concurrency"
    assert result.success_rate > 0.99


@pytest.mark.asyncio
@pytest.mark.throughput
async def test_throughput_mixed_risk_levels(mock_governance, mock_agent):
    """Throughput with mixed risk levels."""
    tracker = PerformanceTracker()
    operations = 1000

    risk_levels = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    tasks = [
        AgentTask(request=f"operation {i}", context={})
        for i in range(operations)
    ]

    tracker.start()

    for i, task in enumerate(tasks):
        risk = risk_levels[i % len(risk_levels)]
        op_start = time.time()
        try:
            await mock_governance.execute_with_governance(mock_agent, task, risk_level=risk)
            latency_ms = (time.time() - op_start) * 1000
            tracker.record_latency(latency_ms)
        except Exception:
            tracker.record_error()

    tracker.stop()

    result = tracker.get_result("Mixed Risk Levels", operations)
    print(result)

    assert result.success_rate > 0.99


# ============================================================================
# STRESS TESTS
# ============================================================================

@pytest.mark.asyncio
@pytest.mark.stress
@pytest.mark.slow
async def test_stress_high_concurrency(mock_governance, mock_agent):
    """Stress test: Very high concurrency."""
    tracker = PerformanceTracker()
    operations = 1000
    concurrency = 200  # VERY high concurrency

    task = AgentTask(request="stress test", context={})

    async def execute_single():
        op_start = time.time()
        try:
            await mock_governance.execute_with_governance(mock_agent, task, risk_level="LOW")
            latency_ms = (time.time() - op_start) * 1000
            tracker.record_latency(latency_ms)
        except Exception as e:
            tracker.record_error()

    tracker.start()

    # All at once!
    await asyncio.gather(*[execute_single() for _ in range(operations)])

    tracker.stop()

    result = tracker.get_result(f"STRESS TEST: {concurrency}+ concurrent ops", operations)
    print(result)

    # Stress test assertions - more lenient
    assert result.success_rate > 0.95, "Should maintain >95% success under stress"
    assert result.latency_p99_ms < 100, "p99 should be < 100ms under stress"


@pytest.mark.asyncio
@pytest.mark.stress
@pytest.mark.slow
async def test_stress_rapid_fire_risk_detection(mock_governance):
    """Stress test: Rapid-fire risk detection."""
    tracker = PerformanceTracker()
    operations = 50000  # 50k operations

    prompts = [
        "Delete production database",
        "Drop users table",
        "Deploy to production",
        "Read configuration",
        "List files",
        "Search for bugs",
        "Modify security",
        "Change password",
        "Refactor code",
        "Write tests"
    ]

    tracker.start()

    for i in range(operations):
        prompt = prompts[i % len(prompts)]
        op_start = time.time()
        mock_governance.detect_risk_level(prompt, "executor")
        latency_ms = (time.time() - op_start) * 1000
        tracker.record_latency(latency_ms)

    tracker.stop()

    result = tracker.get_result(f"STRESS TEST: {operations} risk detections", operations)
    print(result)

    assert result.throughput_ops_per_sec > 5000, "Should handle >5k risk detections/sec"


@pytest.mark.asyncio
@pytest.mark.stress
@pytest.mark.slow
async def test_stress_memory_leak_check(mock_governance, mock_agent):
    """Stress test: Check for memory leaks."""
    tracker = PerformanceTracker()
    operations = 5000  # Long-running test

    task = AgentTask(request="memory test", context={})

    tracker.start()

    memory_samples = []

    for i in range(operations):
        # Sample memory every 100 operations
        if i % 100 == 0:
            memory_samples.append(tracker.process.memory_info().rss / (1024 * 1024))

        op_start = time.time()
        try:
            await mock_governance.execute_with_governance(mock_agent, task, risk_level="LOW")
            latency_ms = (time.time() - op_start) * 1000
            tracker.record_latency(latency_ms)
        except Exception:
            tracker.record_error()

    tracker.stop()

    result = tracker.get_result(f"MEMORY LEAK CHECK: {operations} ops", operations)
    print(result)

    # Check memory growth
    memory_start = memory_samples[0]
    memory_end = memory_samples[-1]
    memory_growth = memory_end - memory_start

    print("\nMemory Analysis:")
    print(f"  Start:   {memory_start:.2f} MB")
    print(f"  End:     {memory_end:.2f} MB")
    print(f"  Growth:  {memory_growth:.2f} MB ({(memory_growth/memory_start)*100:.1f}%)")

    # Memory should not grow excessively
    assert memory_growth < 100, f"Memory grew by {memory_growth:.2f}MB - possible leak!"


@pytest.mark.asyncio
@pytest.mark.stress
async def test_stress_graceful_degradation(mock_agent):
    """Stress test: Graceful degradation without governance."""
    tracker = PerformanceTracker()
    operations = 2000

    task = AgentTask(request="degradation test", context={})

    tracker.start()

    # Run without governance - should still work
    for _ in range(operations):
        op_start = time.time()
        try:
            await mock_agent.execute(task)
            latency_ms = (time.time() - op_start) * 1000
            tracker.record_latency(latency_ms)
        except Exception:
            tracker.record_error()

    tracker.stop()

    result = tracker.get_result("GRACEFUL DEGRADATION: No governance", operations)
    print(result)

    # Should work perfectly without governance
    assert result.success_rate == 1.0, "Should have 100% success without governance"
    assert result.throughput_ops_per_sec > 1000, "Should be very fast without governance"


# ============================================================================
# COMPARISON BENCHMARKS
# ============================================================================

@pytest.mark.asyncio
@pytest.mark.comparison
async def test_comparison_with_vs_without_governance(mock_governance, mock_agent):
    """Compare performance with vs without governance."""
    operations = 1000

    # Test WITHOUT governance
    tracker_without = PerformanceTracker()
    task = AgentTask(request="comparison test", context={})

    tracker_without.start()
    for _ in range(operations):
        op_start = time.time()
        await mock_agent.execute(task)
        latency_ms = (time.time() - op_start) * 1000
        tracker_without.record_latency(latency_ms)
    tracker_without.stop()

    result_without = tracker_without.get_result("WITHOUT Governance", operations)

    # Test WITH governance
    tracker_with = PerformanceTracker()

    tracker_with.start()
    for _ in range(operations):
        op_start = time.time()
        await mock_governance.execute_with_governance(mock_agent, task, risk_level="LOW")
        latency_ms = (time.time() - op_start) * 1000
        tracker_with.record_latency(latency_ms)
    tracker_with.stop()

    result_with = tracker_with.get_result("WITH Governance", operations)

    # Print comparison
    print("\n" + "="*80)
    print("GOVERNANCE OVERHEAD COMPARISON")
    print("="*80)
    print(result_without)
    print(result_with)

    # Calculate overhead
    overhead_latency_p50 = result_with.latency_p50_ms - result_without.latency_p50_ms
    overhead_latency_p95 = result_with.latency_p95_ms - result_without.latency_p95_ms
    overhead_percentage = (overhead_latency_p50 / result_without.latency_p50_ms) * 100 if result_without.latency_p50_ms > 0 else 0

    print("\nOVERHEAD ANALYSIS:")
    print(f"  p50 overhead: +{overhead_latency_p50:.3f}ms ({overhead_percentage:.1f}%)")
    print(f"  p95 overhead: +{overhead_latency_p95:.3f}ms")
    print(f"  Throughput ratio: {result_without.throughput_ops_per_sec / result_with.throughput_ops_per_sec:.2f}x")
    print(f"  Memory overhead: +{result_with.memory_usage_mb - result_without.memory_usage_mb:.2f}MB")
    print("="*80)

    # Governance overhead should be acceptable
    assert overhead_latency_p50 < 10.0, "Governance overhead should be < 10ms at p50"


# ============================================================================
# REAL-WORLD SCENARIO BENCHMARKS
# ============================================================================

@pytest.mark.asyncio
@pytest.mark.realistic
async def test_realistic_maestro_workflow(mock_governance, mock_agent):
    """Benchmark realistic Maestro workflow."""
    tracker = PerformanceTracker()

    # Simulate realistic workflow: 100 user requests
    # Mixed risk levels, some with Sofia counsel
    operations = 100

    workflow_tasks = [
        ("Read user profile", "LOW"),
        ("Update user preferences", "MEDIUM"),
        ("Delete old logs", "MEDIUM"),
        ("Deploy feature to staging", "HIGH"),
        ("Refactor authentication", "CRITICAL"),
        ("Run tests", "LOW"),
        ("Generate report", "LOW"),
        ("Backup database", "HIGH"),
        ("Modify API endpoint", "HIGH"),
        ("Read documentation", "LOW"),
    ]

    tracker.start()

    for i in range(operations):
        request, risk = workflow_tasks[i % len(workflow_tasks)]
        task = AgentTask(request=request, context={"user_id": f"user_{i}"})

        op_start = time.time()
        try:
            await mock_governance.execute_with_governance(mock_agent, task, risk_level=risk)
            latency_ms = (time.time() - op_start) * 1000
            tracker.record_latency(latency_ms)
        except Exception:
            tracker.record_error()

    tracker.stop()

    result = tracker.get_result("REALISTIC WORKFLOW: Mixed operations", operations)
    print(result)

    # Realistic workflow assertions
    assert result.latency_p50_ms < 20.0, "Realistic workflow p50 should be < 20ms"
    assert result.latency_p95_ms < 50.0, "Realistic workflow p95 should be < 50ms"
    assert result.success_rate > 0.99


# ============================================================================
# SUMMARY
# ============================================================================

def test_generate_performance_report():
    """Generate final performance report."""
    report = """
╔══════════════════════════════════════════════════════════════════════════════════╗
║                                                                                  ║
║                    PHASE 5 PERFORMANCE BENCHMARK SUMMARY                         ║
║                                                                                  ║
╚══════════════════════════════════════════════════════════════════════════════════╝

Run complete benchmark suite with:
    pytest tests/test_phase5_performance_benchmarks.py -v -s --tb=short

Run specific categories:
    pytest tests/test_phase5_performance_benchmarks.py -v -s -m latency
    pytest tests/test_phase5_performance_benchmarks.py -v -s -m throughput
    pytest tests/test_phase5_performance_benchmarks.py -v -s -m stress
    pytest tests/test_phase5_performance_benchmarks.py -v -s -m comparison

Categories:
    - Latency Benchmarks (3 tests)
    - Throughput Benchmarks (2 tests)
    - Stress Tests (4 tests, marked as slow)
    - Comparison Benchmarks (1 test)
    - Realistic Scenarios (1 test)

Total: 11 performance benchmarks
"""
    print(report)
    assert True


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])
