"""
Performance Tests Configuration
================================

Shared fixtures for performance testing:
- Benchmarking utilities
- Load testing fixtures
- Metrics collection

Based on:
- pytest-benchmark patterns
- Locust load testing
- Google Agent Evaluation metrics
"""

import pytest
import time
import statistics
import json
import asyncio
from pathlib import Path
from typing import Dict, Any, List, Callable, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime
from functools import wraps
import threading
import resource


# ==============================================================================
# DATA CLASSES
# ==============================================================================

@dataclass
class BenchmarkResult:
    """Result of a benchmark run."""
    name: str
    iterations: int
    total_time_s: float
    mean_time_s: float
    median_time_s: float
    std_dev_s: float
    min_time_s: float
    max_time_s: float
    ops_per_second: float
    memory_peak_mb: float = 0.0
    passed_threshold: bool = True
    threshold_ms: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class LoadTestResult:
    """Result of a load test."""
    name: str
    total_requests: int
    successful_requests: int
    failed_requests: int
    total_time_s: float
    requests_per_second: float
    mean_response_time_ms: float
    p50_ms: float
    p95_ms: float
    p99_ms: float
    max_response_time_ms: float
    error_rate: float
    concurrent_users: int


@dataclass
class PerformanceMetrics:
    """Aggregated performance metrics."""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    benchmarks: List[BenchmarkResult] = field(default_factory=list)
    load_tests: List[LoadTestResult] = field(default_factory=list)
    system_info: Dict[str, Any] = field(default_factory=dict)


# ==============================================================================
# BENCHMARK FIXTURES
# ==============================================================================

@pytest.fixture
def benchmark_runner():
    """Provide benchmark execution utilities."""
    class BenchmarkRunner:
        def __init__(self):
            self.results: List[BenchmarkResult] = []
            self.thresholds = {
                "fast": 10,      # 10ms
                "normal": 100,   # 100ms
                "slow": 1000,    # 1s
                "very_slow": 5000,  # 5s
            }

        def run(
            self,
            func: Callable,
            name: str = None,
            iterations: int = 100,
            warmup: int = 5,
            threshold_ms: float = None,
            args: tuple = (),
            kwargs: dict = None
        ) -> BenchmarkResult:
            """Run benchmark on function."""
            if kwargs is None:
                kwargs = {}
            if name is None:
                name = func.__name__

            # Warmup runs
            for _ in range(warmup):
                func(*args, **kwargs)

            # Benchmark runs
            times = []
            for _ in range(iterations):
                start = time.perf_counter()
                func(*args, **kwargs)
                elapsed = time.perf_counter() - start
                times.append(elapsed)

            # Calculate statistics
            mean_time = statistics.mean(times)
            result = BenchmarkResult(
                name=name,
                iterations=iterations,
                total_time_s=sum(times),
                mean_time_s=mean_time,
                median_time_s=statistics.median(times),
                std_dev_s=statistics.stdev(times) if len(times) > 1 else 0,
                min_time_s=min(times),
                max_time_s=max(times),
                ops_per_second=1 / mean_time if mean_time > 0 else float('inf'),
                threshold_ms=threshold_ms,
                passed_threshold=threshold_ms is None or (mean_time * 1000) <= threshold_ms
            )

            self.results.append(result)
            return result

        async def run_async(
            self,
            func: Callable,
            name: str = None,
            iterations: int = 100,
            warmup: int = 5,
            threshold_ms: float = None,
            args: tuple = (),
            kwargs: dict = None
        ) -> BenchmarkResult:
            """Run benchmark on async function."""
            if kwargs is None:
                kwargs = {}
            if name is None:
                name = func.__name__

            # Warmup runs
            for _ in range(warmup):
                await func(*args, **kwargs)

            # Benchmark runs
            times = []
            for _ in range(iterations):
                start = time.perf_counter()
                await func(*args, **kwargs)
                elapsed = time.perf_counter() - start
                times.append(elapsed)

            # Calculate statistics
            mean_time = statistics.mean(times)
            result = BenchmarkResult(
                name=name,
                iterations=iterations,
                total_time_s=sum(times),
                mean_time_s=mean_time,
                median_time_s=statistics.median(times),
                std_dev_s=statistics.stdev(times) if len(times) > 1 else 0,
                min_time_s=min(times),
                max_time_s=max(times),
                ops_per_second=1 / mean_time if mean_time > 0 else float('inf'),
                threshold_ms=threshold_ms,
                passed_threshold=threshold_ms is None or (mean_time * 1000) <= threshold_ms
            )

            self.results.append(result)
            return result

        def assert_threshold(self, result: BenchmarkResult):
            """Assert that benchmark passed threshold."""
            assert result.passed_threshold, (
                f"Benchmark '{result.name}' exceeded threshold: "
                f"{result.mean_time_s * 1000:.2f}ms > {result.threshold_ms}ms"
            )

        def get_summary(self) -> Dict[str, Any]:
            """Get summary of all benchmarks."""
            return {
                "total_benchmarks": len(self.results),
                "passed": sum(1 for r in self.results if r.passed_threshold),
                "failed": sum(1 for r in self.results if not r.passed_threshold),
                "results": [r.to_dict() for r in self.results]
            }

    return BenchmarkRunner()


@pytest.fixture
def memory_profiler():
    """Provide memory profiling utilities."""
    class MemoryProfiler:
        def __init__(self):
            self.baseline = self._get_memory_mb()

        def _get_memory_mb(self) -> float:
            """Get current memory usage in MB."""
            usage = resource.getrusage(resource.RUSAGE_SELF)
            return usage.ru_maxrss / 1024  # Convert KB to MB on Linux

        def get_current(self) -> float:
            """Get current memory usage."""
            return self._get_memory_mb()

        def get_delta(self) -> float:
            """Get memory delta from baseline."""
            return self._get_memory_mb() - self.baseline

        def reset_baseline(self):
            """Reset memory baseline."""
            self.baseline = self._get_memory_mb()

        def profile(self, func: Callable, *args, **kwargs) -> tuple[Any, float]:
            """Profile function memory usage."""
            self.reset_baseline()
            result = func(*args, **kwargs)
            delta = self.get_delta()
            return result, delta

    return MemoryProfiler()


# ==============================================================================
# LOAD TEST FIXTURES
# ==============================================================================

@pytest.fixture
def load_tester():
    """Provide load testing utilities."""
    class LoadTester:
        def __init__(self):
            self.results: List[LoadTestResult] = []

        def run(
            self,
            func: Callable,
            name: str = None,
            total_requests: int = 100,
            concurrent_users: int = 10,
            timeout_s: float = 30,
            args: tuple = (),
            kwargs: dict = None
        ) -> LoadTestResult:
            """Run load test with concurrent users."""
            if kwargs is None:
                kwargs = {}
            if name is None:
                name = func.__name__

            response_times = []
            errors = []
            lock = threading.Lock()

            def worker(request_id: int):
                try:
                    start = time.perf_counter()
                    func(*args, **kwargs)
                    elapsed_ms = (time.perf_counter() - start) * 1000
                    with lock:
                        response_times.append(elapsed_ms)
                except Exception as e:
                    with lock:
                        errors.append(str(e))

            # Create thread pool
            threads = []
            start_time = time.perf_counter()

            for i in range(total_requests):
                t = threading.Thread(target=worker, args=(i,))
                threads.append(t)

                # Limit concurrent threads
                if len([t for t in threads if t.is_alive()]) >= concurrent_users:
                    # Wait for some threads to finish
                    for t in threads:
                        if t.is_alive():
                            t.join(timeout=0.1)

                t.start()

            # Wait for all threads
            for t in threads:
                t.join(timeout=timeout_s)

            total_time = time.perf_counter() - start_time

            # Calculate percentiles
            sorted_times = sorted(response_times) if response_times else [0]
            p50_idx = int(len(sorted_times) * 0.50)
            p95_idx = int(len(sorted_times) * 0.95)
            p99_idx = int(len(sorted_times) * 0.99)

            result = LoadTestResult(
                name=name,
                total_requests=total_requests,
                successful_requests=len(response_times),
                failed_requests=len(errors),
                total_time_s=total_time,
                requests_per_second=len(response_times) / total_time if total_time > 0 else 0,
                mean_response_time_ms=statistics.mean(response_times) if response_times else 0,
                p50_ms=sorted_times[p50_idx] if sorted_times else 0,
                p95_ms=sorted_times[min(p95_idx, len(sorted_times) - 1)] if sorted_times else 0,
                p99_ms=sorted_times[min(p99_idx, len(sorted_times) - 1)] if sorted_times else 0,
                max_response_time_ms=max(response_times) if response_times else 0,
                error_rate=len(errors) / total_requests if total_requests > 0 else 0,
                concurrent_users=concurrent_users
            )

            self.results.append(result)
            return result

        async def run_async(
            self,
            func: Callable,
            name: str = None,
            total_requests: int = 100,
            concurrent_users: int = 10,
            args: tuple = (),
            kwargs: dict = None
        ) -> LoadTestResult:
            """Run async load test."""
            if kwargs is None:
                kwargs = {}
            if name is None:
                name = func.__name__

            response_times = []
            errors = []
            semaphore = asyncio.Semaphore(concurrent_users)

            async def worker(request_id: int):
                async with semaphore:
                    try:
                        start = time.perf_counter()
                        await func(*args, **kwargs)
                        elapsed_ms = (time.perf_counter() - start) * 1000
                        response_times.append(elapsed_ms)
                    except Exception as e:
                        errors.append(str(e))

            start_time = time.perf_counter()
            tasks = [worker(i) for i in range(total_requests)]
            await asyncio.gather(*tasks)
            total_time = time.perf_counter() - start_time

            # Calculate percentiles
            sorted_times = sorted(response_times) if response_times else [0]
            p50_idx = int(len(sorted_times) * 0.50)
            p95_idx = int(len(sorted_times) * 0.95)
            p99_idx = int(len(sorted_times) * 0.99)

            result = LoadTestResult(
                name=name,
                total_requests=total_requests,
                successful_requests=len(response_times),
                failed_requests=len(errors),
                total_time_s=total_time,
                requests_per_second=len(response_times) / total_time if total_time > 0 else 0,
                mean_response_time_ms=statistics.mean(response_times) if response_times else 0,
                p50_ms=sorted_times[p50_idx] if sorted_times else 0,
                p95_ms=sorted_times[min(p95_idx, len(sorted_times) - 1)] if sorted_times else 0,
                p99_ms=sorted_times[min(p99_idx, len(sorted_times) - 1)] if sorted_times else 0,
                max_response_time_ms=max(response_times) if response_times else 0,
                error_rate=len(errors) / total_requests if total_requests > 0 else 0,
                concurrent_users=concurrent_users
            )

            self.results.append(result)
            return result

    return LoadTester()


# ==============================================================================
# PERFORMANCE THRESHOLDS
# ==============================================================================

@pytest.fixture
def performance_thresholds():
    """Performance thresholds for different operations."""
    return {
        # Agent operations (ms)
        "agent_init": 100,
        "agent_process_simple": 500,
        "agent_process_complex": 2000,
        "agent_tool_call": 200,

        # File operations (ms)
        "file_read_small": 10,
        "file_read_large": 100,
        "file_write_small": 20,
        "file_search": 50,

        # LLM operations (ms)
        "llm_tokenize": 10,
        "llm_prompt_build": 50,
        "llm_parse_response": 20,

        # Orchestration (ms)
        "task_queue": 5,
        "state_transition": 10,
        "context_switch": 50,

        # Memory limits (MB)
        "memory_per_agent": 50,
        "memory_per_session": 200,
        "memory_total": 500,

        # Throughput (requests/sec)
        "min_throughput": 10,
        "target_throughput": 50,
    }


# ==============================================================================
# REPORT GENERATION
# ==============================================================================

@pytest.fixture
def performance_reporter(tmp_path):
    """Generate performance reports."""
    class PerformanceReporter:
        def __init__(self, output_dir: Path):
            self.output_dir = output_dir
            self.metrics = PerformanceMetrics()

        def add_benchmark(self, result: BenchmarkResult):
            self.metrics.benchmarks.append(result)

        def add_load_test(self, result: LoadTestResult):
            self.metrics.load_tests.append(result)

        def generate_report(self) -> Path:
            """Generate JSON report."""
            report_path = self.output_dir / f"performance_report_{datetime.now():%Y%m%d_%H%M%S}.json"

            report = {
                "timestamp": self.metrics.timestamp,
                "summary": {
                    "total_benchmarks": len(self.metrics.benchmarks),
                    "benchmarks_passed": sum(1 for b in self.metrics.benchmarks if b.passed_threshold),
                    "total_load_tests": len(self.metrics.load_tests),
                },
                "benchmarks": [asdict(b) for b in self.metrics.benchmarks],
                "load_tests": [asdict(l) for l in self.metrics.load_tests],
            }

            report_path.write_text(json.dumps(report, indent=2))
            return report_path

        def print_summary(self):
            """Print summary to console."""
            print("\n" + "=" * 60)
            print("PERFORMANCE TEST SUMMARY")
            print("=" * 60)

            if self.metrics.benchmarks:
                print("\nBenchmarks:")
                for b in self.metrics.benchmarks:
                    status = "✓" if b.passed_threshold else "✗"
                    print(f"  {status} {b.name}: {b.mean_time_s * 1000:.2f}ms (threshold: {b.threshold_ms}ms)")

            if self.metrics.load_tests:
                print("\nLoad Tests:")
                for l in self.metrics.load_tests:
                    print(f"  {l.name}: {l.requests_per_second:.1f} req/s, p95: {l.p95_ms:.1f}ms")

            print("=" * 60)

    return PerformanceReporter(tmp_path)
