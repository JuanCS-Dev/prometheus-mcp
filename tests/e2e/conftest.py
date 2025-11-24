"""
E2E Test Configuration and Fixtures
=====================================

Global fixtures for E2E tests including:
- Real LLM client configuration
- Metrics collection (Google ADK pattern)
- Evalset loading (Anthropic pattern)
- Workspace setup
- Performance thresholds

Based on:
- Anthropic Claude Code Best Practices (Nov 2025)
- Google Agent Evaluation Framework (2025)
"""

import pytest
import asyncio
import os
import json
import time
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from datetime import datetime


# ==============================================================================
# REAL LLM CONFIGURATION
# ==============================================================================

REAL_LLM_PROVIDERS = {
    "ollama": os.getenv("OLLAMA_HOST", "http://localhost:11434"),
    "gemini": os.getenv("GEMINI_API_KEY"),
    "openai": os.getenv("OPENAI_API_KEY"),
    "anthropic": os.getenv("ANTHROPIC_API_KEY"),
}


def pytest_addoption(parser):
    """Add custom command line options."""
    parser.addoption(
        "--real-llm",
        action="store_true",
        default=False,
        help="Use real LLM instead of mocks"
    )
    parser.addoption(
        "--llm-provider",
        action="store",
        default="ollama",
        help="LLM provider to use (ollama, gemini, openai, anthropic)"
    )


@pytest.fixture(scope="session")
def use_real_llm(request):
    """Check if real LLM should be used."""
    return request.config.getoption("--real-llm")


@pytest.fixture(scope="session")
def llm_provider(request):
    """Get configured LLM provider."""
    return request.config.getoption("--llm-provider")


@pytest.fixture(scope="session")
def real_llm_client(use_real_llm, llm_provider):
    """
    Real LLM client for integration tests.

    Priority: Ollama (local) > Configured provider
    """
    if not use_real_llm:
        pytest.skip("Real LLM not requested (use --real-llm)")

    # Try to create client based on provider
    from qwen_dev_cli.core.llm import LLMClient

    provider_key = REAL_LLM_PROVIDERS.get(llm_provider)
    if not provider_key:
        pytest.skip(f"No API key for provider: {llm_provider}")

    try:
        client = LLMClient(provider=llm_provider)
        return client
    except Exception as e:
        pytest.skip(f"Failed to create LLM client: {e}")


# ==============================================================================
# METRICS COLLECTION (Google ADK Pattern)
# ==============================================================================

@dataclass
class TrajectoryMetrics:
    """Metrics for trajectory evaluation."""
    test_name: str
    exact_match: bool = False
    in_order_match: bool = False
    any_order_match: bool = False
    precision: float = 0.0
    recall: float = 0.0
    f1_score: float = 0.0
    expected_trajectory: List[str] = field(default_factory=list)
    actual_trajectory: List[str] = field(default_factory=list)


@dataclass
class PerformanceMetrics:
    """Performance metrics for a test."""
    test_name: str
    duration_ms: float
    memory_mb: float = 0.0
    passed: bool = True


class MetricsCollector:
    """
    Collect and report test metrics.

    Implements Google ADK evaluation patterns.
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.trajectory_metrics: Dict[str, TrajectoryMetrics] = {}
            cls._instance.performance_metrics: Dict[str, PerformanceMetrics] = {}
            cls._instance.test_results: List[Dict] = []
            cls._instance.start_time = time.time()
        return cls._instance

    def record_trajectory(
        self,
        test_name: str,
        expected: List[str],
        actual: List[str]
    ):
        """Record trajectory metrics for a test."""
        metrics = TrajectoryMetrics(
            test_name=test_name,
            expected_trajectory=expected,
            actual_trajectory=actual,
            exact_match=expected == actual,
            in_order_match=self._is_subsequence(expected, actual),
            any_order_match=set(expected) <= set(actual),
            precision=self._calculate_precision(expected, actual),
            recall=self._calculate_recall(expected, actual),
        )
        metrics.f1_score = self._calculate_f1(metrics.precision, metrics.recall)
        self.trajectory_metrics[test_name] = metrics

    def record_performance(
        self,
        test_name: str,
        duration_ms: float,
        memory_mb: float = 0.0,
        passed: bool = True
    ):
        """Record performance metrics for a test."""
        self.performance_metrics[test_name] = PerformanceMetrics(
            test_name=test_name,
            duration_ms=duration_ms,
            memory_mb=memory_mb,
            passed=passed
        )

    def _is_subsequence(self, expected: List[str], actual: List[str]) -> bool:
        """Check if expected is a subsequence of actual."""
        it = iter(actual)
        return all(item in it for item in expected)

    def _calculate_precision(self, expected: List[str], actual: List[str]) -> float:
        """Calculate trajectory precision."""
        if not actual:
            return 0.0
        matching = len(set(expected) & set(actual))
        return matching / len(actual)

    def _calculate_recall(self, expected: List[str], actual: List[str]) -> float:
        """Calculate trajectory recall."""
        if not expected:
            return 1.0
        matching = len(set(expected) & set(actual))
        return matching / len(expected)

    def _calculate_f1(self, precision: float, recall: float) -> float:
        """Calculate F1 score."""
        if precision + recall == 0:
            return 0.0
        return 2 * (precision * recall) / (precision + recall)

    def generate_report(self) -> Dict[str, Any]:
        """Generate comprehensive metrics report."""
        total_duration = time.time() - self.start_time

        # Trajectory summary
        trajectory_summary = {
            "total_tests": len(self.trajectory_metrics),
            "exact_match_rate": sum(
                1 for m in self.trajectory_metrics.values() if m.exact_match
            ) / max(len(self.trajectory_metrics), 1),
            "avg_precision": sum(
                m.precision for m in self.trajectory_metrics.values()
            ) / max(len(self.trajectory_metrics), 1),
            "avg_recall": sum(
                m.recall for m in self.trajectory_metrics.values()
            ) / max(len(self.trajectory_metrics), 1),
            "avg_f1": sum(
                m.f1_score for m in self.trajectory_metrics.values()
            ) / max(len(self.trajectory_metrics), 1),
        }

        # Performance summary
        performance_summary = {
            "total_tests": len(self.performance_metrics),
            "avg_duration_ms": sum(
                m.duration_ms for m in self.performance_metrics.values()
            ) / max(len(self.performance_metrics), 1),
            "max_duration_ms": max(
                (m.duration_ms for m in self.performance_metrics.values()),
                default=0
            ),
            "pass_rate": sum(
                1 for m in self.performance_metrics.values() if m.passed
            ) / max(len(self.performance_metrics), 1),
        }

        return {
            "total_duration_seconds": total_duration,
            "trajectory_summary": trajectory_summary,
            "performance_summary": performance_summary,
            "trajectory_details": {
                name: {
                    "exact_match": m.exact_match,
                    "precision": m.precision,
                    "recall": m.recall,
                    "f1": m.f1_score,
                }
                for name, m in self.trajectory_metrics.items()
            },
            "timestamp": datetime.now().isoformat(),
        }


@pytest.fixture(scope="session")
def metrics_collector():
    """Session-scoped metrics collector."""
    collector = MetricsCollector()
    yield collector

    # Generate report at end of session
    report = collector.generate_report()
    report_path = Path(__file__).parent / "E2E_METRICS_REPORT.json"
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)

    print(f"\n{'='*60}")
    print("E2E TEST METRICS REPORT")
    print(f"{'='*60}")
    print(f"Trajectory Tests: {report['trajectory_summary']['total_tests']}")
    print(f"  Exact Match Rate: {report['trajectory_summary']['exact_match_rate']:.1%}")
    print(f"  Avg Precision: {report['trajectory_summary']['avg_precision']:.1%}")
    print(f"  Avg Recall: {report['trajectory_summary']['avg_recall']:.1%}")
    print(f"  Avg F1: {report['trajectory_summary']['avg_f1']:.1%}")
    print(f"\nPerformance Tests: {report['performance_summary']['total_tests']}")
    print(f"  Avg Duration: {report['performance_summary']['avg_duration_ms']:.1f}ms")
    print(f"  Pass Rate: {report['performance_summary']['pass_rate']:.1%}")
    print(f"\nFull report: {report_path}")


# ==============================================================================
# EVALSET SUPPORT (Anthropic Pattern)
# ==============================================================================

@dataclass
class EvalCase:
    """Single evaluation case from an evalset."""
    name: str
    input: str
    expected_output: str
    expected_trajectory: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    difficulty: str = "medium"
    timeout_seconds: float = 30.0


@pytest.fixture
def load_evalset():
    """Load evaluation set from JSON file."""
    def _load(evalset_name: str) -> List[EvalCase]:
        evalset_dir = Path(__file__).parent.parent / "evalsets"
        evalset_path = evalset_dir / f"{evalset_name}.json"

        if not evalset_path.exists():
            pytest.skip(f"Evalset not found: {evalset_name}")

        with open(evalset_path) as f:
            data = json.load(f)

        cases = []
        for case_data in data.get("cases", []):
            cases.append(EvalCase(
                name=case_data.get("name", "unnamed"),
                input=case_data.get("input", ""),
                expected_output=case_data.get("expected_output", ""),
                expected_trajectory=case_data.get("expected_trajectory", []),
                tags=case_data.get("tags", []),
                difficulty=case_data.get("difficulty", "medium"),
                timeout_seconds=case_data.get("timeout_seconds", 30.0),
            ))

        return cases

    return _load


@pytest.fixture
def run_evalset(metrics_collector):
    """Run all cases in an evalset and collect metrics."""
    async def _run(evalset: List[EvalCase], executor):
        results = []

        for case in evalset:
            start_time = time.perf_counter()

            try:
                result = await asyncio.wait_for(
                    executor(case.input),
                    timeout=case.timeout_seconds
                )
                duration_ms = (time.perf_counter() - start_time) * 1000
                passed = case.expected_output in str(result.output)

                # Record trajectory if available
                if hasattr(result, 'trajectory') and case.expected_trajectory:
                    metrics_collector.record_trajectory(
                        case.name,
                        case.expected_trajectory,
                        result.trajectory
                    )

                metrics_collector.record_performance(
                    case.name,
                    duration_ms,
                    passed=passed
                )

                results.append({
                    "case": case.name,
                    "passed": passed,
                    "duration_ms": duration_ms,
                    "output": str(result.output)[:500],
                })

            except asyncio.TimeoutError:
                results.append({
                    "case": case.name,
                    "passed": False,
                    "error": "timeout",
                })
            except Exception as e:
                results.append({
                    "case": case.name,
                    "passed": False,
                    "error": str(e),
                })

        return results

    return _run


# ==============================================================================
# WORKSPACE FIXTURES
# ==============================================================================

@pytest.fixture
def e2e_workspace(tmp_path):
    """Create a standard workspace for E2E tests."""
    workspace = tmp_path / "e2e_project"
    workspace.mkdir()

    # Standard project structure
    (workspace / "src").mkdir()
    (workspace / "src" / "__init__.py").write_text("")
    (workspace / "src" / "main.py").write_text('''"""Main module."""

def main():
    """Main entry point."""
    print("Hello, World!")

def add(a: int, b: int) -> int:
    """Add two numbers."""
    return a + b

if __name__ == "__main__":
    main()
''')

    (workspace / "tests").mkdir()
    (workspace / "tests" / "__init__.py").write_text("")
    (workspace / "tests" / "test_main.py").write_text('''"""Tests for main module."""
import pytest
from src.main import main, add

def test_main():
    """Test main function runs without error."""
    main()

def test_add():
    """Test add function."""
    assert add(2, 3) == 5
    assert add(-1, 1) == 0
''')

    (workspace / "pyproject.toml").write_text('''[project]
name = "e2e-test-project"
version = "1.0.0"
requires-python = ">=3.10"

[project.optional-dependencies]
test = ["pytest>=8.0"]
''')

    (workspace / "README.md").write_text("# E2E Test Project\n")

    # Initialize git
    os.system(f"cd {workspace} && git init -q && git add . && git commit -m 'Initial' -q 2>/dev/null")

    old_cwd = os.getcwd()
    os.chdir(workspace)

    yield workspace

    os.chdir(old_cwd)


# ==============================================================================
# PERFORMANCE FIXTURES
# ==============================================================================

@pytest.fixture
def benchmark_thresholds():
    """Define benchmark thresholds for E2E tests."""
    return {
        # Input processing
        "input_validation_ms": 10,
        "input_enhancement_ms": 50,
        "prompt_analysis_ms": 100,

        # Execution
        "file_read_ms": 100,
        "file_write_ms": 200,
        "command_execution_ms": 5000,

        # Agent operations
        "agent_init_ms": 500,
        "simple_task_ms": 10000,
        "complex_task_ms": 60000,

        # Memory limits
        "max_memory_mb": 500,
    }


@pytest.fixture
def performance_timer():
    """Context manager for timing operations."""
    class Timer:
        def __init__(self):
            self.start = 0
            self.end = 0

        def __enter__(self):
            self.start = time.perf_counter()
            return self

        def __exit__(self, *args):
            self.end = time.perf_counter()

        @property
        def elapsed_ms(self):
            return (self.end - self.start) * 1000

    return Timer


# ==============================================================================
# ASYNC HELPERS
# ==============================================================================

@pytest.fixture
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def with_timeout():
    """Run async code with timeout."""
    async def _run_with_timeout(coro, timeout: float = 30.0):
        try:
            return await asyncio.wait_for(coro, timeout=timeout)
        except asyncio.TimeoutError:
            return {"error": "timeout", "timeout_seconds": timeout}
    return _run_with_timeout


# ==============================================================================
# MARKERS CONFIGURATION
# ==============================================================================

def pytest_configure(config):
    """Configure custom markers."""
    config.addinivalue_line("markers", "e2e: End-to-end tests")
    config.addinivalue_line("markers", "security: Security tests")
    config.addinivalue_line("markers", "senior: Senior developer persona tests")
    config.addinivalue_line("markers", "vibe_coder: Beginner persona tests")
    config.addinivalue_line("markers", "script_kid: Security/attacker persona tests")
    config.addinivalue_line("markers", "real_llm: Tests requiring real LLM")
    config.addinivalue_line("markers", "slow: Tests taking > 30 seconds")


# ==============================================================================
# MOCK HELPERS
# ==============================================================================

class MockLLMResponse:
    """Mock LLM response for testing."""
    def __init__(self, content: str, trajectory: List[str] = None):
        self.content = content
        self.output = content
        self.trajectory = trajectory or []
        self.success = True


class MockLLMClient:
    """Mock LLM client for fast testing."""

    def __init__(self, responses: Dict[str, str] = None):
        self.responses = responses or {}
        self.call_history = []
        self.default_response = "I understand. Let me help you with that."

    async def generate(self, prompt: str, **kwargs) -> MockLLMResponse:
        """Generate mock response."""
        self.call_history.append({"prompt": prompt, **kwargs})

        for key, response in self.responses.items():
            if key.lower() in prompt.lower():
                return MockLLMResponse(response)

        return MockLLMResponse(self.default_response)

    async def stream(self, prompt: str, **kwargs):
        """Stream mock response."""
        response = await self.generate(prompt, **kwargs)
        for word in response.content.split():
            yield word + " "
            await asyncio.sleep(0.01)


@pytest.fixture
def mock_llm():
    """Create mock LLM client."""
    return MockLLMClient()


@pytest.fixture
def mock_llm_with_responses():
    """Create mock LLM with configurable responses."""
    def _create(responses: Dict[str, str]):
        return MockLLMClient(responses)
    return _create


# ==============================================================================
# REPORT GENERATION
# ==============================================================================

def pytest_terminal_summary(terminalreporter, exitstatus, config):
    """Add custom summary to pytest output."""
    if hasattr(terminalreporter, 'stats'):
        passed = len(terminalreporter.stats.get('passed', []))
        failed = len(terminalreporter.stats.get('failed', []))
        skipped = len(terminalreporter.stats.get('skipped', []))

        terminalreporter.write_sep("=", "E2E TEST SUMMARY")
        terminalreporter.write_line(f"Passed: {passed}")
        terminalreporter.write_line(f"Failed: {failed}")
        terminalreporter.write_line(f"Skipped: {skipped}")

        if failed > 0:
            terminalreporter.write_line(
                "\nSecurity tests MUST pass. Review failed tests.",
                red=True
            )
