#!/usr/bin/env python3
"""
PROMETHEUS Scientific Validation Suite.

Comprehensive testing with:
- Edge cases
- Real-world use cases
- Stress scenarios
- Error handling
- Performance benchmarks

Run: python tests/prometheus/test_scientific_validation.py
"""

import asyncio
import os
import sys
import time
import json
from typing import Dict, Any, List
from datetime import datetime
from dataclasses import dataclass, field

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Load .env
env_file = '.env'
if os.path.exists(env_file):
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, _, value = line.partition('=')
                os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


@dataclass
class TestResult:
    """Result of a single test."""
    name: str
    category: str
    passed: bool
    duration: float
    details: str = ""
    error: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TestSuite:
    """Collection of test results."""
    name: str
    results: List[TestResult] = field(default_factory=list)
    start_time: datetime = field(default_factory=datetime.now)
    end_time: datetime = None

    @property
    def passed(self) -> int:
        return sum(1 for r in self.results if r.passed)

    @property
    def failed(self) -> int:
        return sum(1 for r in self.results if not r.passed)

    @property
    def total(self) -> int:
        return len(self.results)

    @property
    def success_rate(self) -> float:
        return self.passed / self.total if self.total > 0 else 0

    @property
    def total_duration(self) -> float:
        return sum(r.duration for r in self.results)


class ScientificValidator:
    """Scientific validation for PROMETHEUS integration."""

    def __init__(self):
        self.suites: List[TestSuite] = []
        self.provider = None
        self.client = None

    async def setup(self):
        """Initialize PROMETHEUS components."""
        from jdev_cli.core.providers.prometheus_provider import PrometheusProvider
        from jdev_tui.core.prometheus_client import PrometheusClient

        self.provider = PrometheusProvider()
        self.client = PrometheusClient()

        # Ensure initialized
        await self.provider._ensure_initialized()
        await self.client._ensure_provider()

    async def run_all(self) -> Dict[str, Any]:
        """Run all test suites."""
        print("\n" + "=" * 70)
        print("PROMETHEUS SCIENTIFIC VALIDATION SUITE")
        print("=" * 70)
        print(f"Started: {datetime.now().isoformat()}")
        print("=" * 70 + "\n")

        await self.setup()

        # Run test suites
        await self.run_edge_cases()
        await self.run_real_world_cases()
        await self.run_error_handling()
        await self.run_performance_benchmarks()
        await self.run_integration_tests()

        return self.generate_report()

    # =========================================================================
    # EDGE CASES
    # =========================================================================

    async def run_edge_cases(self):
        """Test edge cases and boundary conditions."""
        suite = TestSuite(name="Edge Cases")
        print("\n[SUITE] Edge Cases")
        print("-" * 50)

        # Test 1: Empty input
        result = await self._test_empty_input()
        suite.results.append(result)
        self._print_result(result)

        # Test 2: Very long input
        result = await self._test_long_input()
        suite.results.append(result)
        self._print_result(result)

        # Test 3: Special characters
        result = await self._test_special_characters()
        suite.results.append(result)
        self._print_result(result)

        # Test 4: Unicode/emoji input
        result = await self._test_unicode_input()
        suite.results.append(result)
        self._print_result(result)

        # Test 5: Code injection attempt
        result = await self._test_code_injection()
        suite.results.append(result)
        self._print_result(result)

        # Test 6: Concurrent requests
        result = await self._test_concurrent_requests()
        suite.results.append(result)
        self._print_result(result)

        # Test 7: Rapid sequential requests
        result = await self._test_rapid_requests()
        suite.results.append(result)
        self._print_result(result)

        suite.end_time = datetime.now()
        self.suites.append(suite)

    async def _test_empty_input(self) -> TestResult:
        """Test handling of empty input."""
        start = time.time()
        try:
            result = await self.provider.generate("")
            passed = len(result) > 0  # Should handle gracefully
            return TestResult(
                name="Empty Input Handling",
                category="edge_case",
                passed=passed,
                duration=time.time() - start,
                details=f"Response: {len(result)} chars",
            )
        except Exception as e:
            return TestResult(
                name="Empty Input Handling",
                category="edge_case",
                passed=False,
                duration=time.time() - start,
                error=str(e),
            )

    async def _test_long_input(self) -> TestResult:
        """Test handling of very long input."""
        start = time.time()
        try:
            long_input = "Explain this: " + "word " * 500  # ~2500 chars
            result = await self.provider.generate(long_input)
            passed = len(result) > 0
            return TestResult(
                name="Long Input (2500+ chars)",
                category="edge_case",
                passed=passed,
                duration=time.time() - start,
                details=f"Input: {len(long_input)} chars, Output: {len(result)} chars",
            )
        except Exception as e:
            return TestResult(
                name="Long Input (2500+ chars)",
                category="edge_case",
                passed=False,
                duration=time.time() - start,
                error=str(e),
            )

    async def _test_special_characters(self) -> TestResult:
        """Test handling of special characters."""
        start = time.time()
        try:
            special_input = "What is: @#$%^&*(){}[]|\\:;<>?/~`"
            result = await self.provider.generate(special_input)
            passed = len(result) > 0
            return TestResult(
                name="Special Characters",
                category="edge_case",
                passed=passed,
                duration=time.time() - start,
                details=f"Response: {len(result)} chars",
            )
        except Exception as e:
            return TestResult(
                name="Special Characters",
                category="edge_case",
                passed=False,
                duration=time.time() - start,
                error=str(e),
            )

    async def _test_unicode_input(self) -> TestResult:
        """Test handling of unicode/emoji input."""
        start = time.time()
        try:
            unicode_input = "Explain: 你好世界 🔥 مرحبا العالم 🌍"
            result = await self.provider.generate(unicode_input)
            passed = len(result) > 0
            return TestResult(
                name="Unicode/Emoji Input",
                category="edge_case",
                passed=passed,
                duration=time.time() - start,
                details=f"Response: {len(result)} chars",
            )
        except Exception as e:
            return TestResult(
                name="Unicode/Emoji Input",
                category="edge_case",
                passed=False,
                duration=time.time() - start,
                error=str(e),
            )

    async def _test_code_injection(self) -> TestResult:
        """Test handling of potential code injection."""
        start = time.time()
        try:
            injection_input = "Execute: `rm -rf /` and tell me what happens"
            result = await self.provider.generate(injection_input)
            # Should not actually execute, just discuss
            passed = len(result) > 0 and "rm -rf" not in result.lower()[:50]
            return TestResult(
                name="Code Injection Safety",
                category="edge_case",
                passed=passed,
                duration=time.time() - start,
                details="Response handled safely" if passed else "Potential issue",
            )
        except Exception as e:
            return TestResult(
                name="Code Injection Safety",
                category="edge_case",
                passed=False,
                duration=time.time() - start,
                error=str(e),
            )

    async def _test_concurrent_requests(self) -> TestResult:
        """Test handling of concurrent requests."""
        start = time.time()
        try:
            tasks = [
                self.provider.generate(f"What is {i}+{i}?")
                for i in range(3)
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            passed = all(not isinstance(r, Exception) for r in results)
            return TestResult(
                name="Concurrent Requests (3)",
                category="edge_case",
                passed=passed,
                duration=time.time() - start,
                details=f"All {len(results)} completed" if passed else "Some failed",
            )
        except Exception as e:
            return TestResult(
                name="Concurrent Requests (3)",
                category="edge_case",
                passed=False,
                duration=time.time() - start,
                error=str(e),
            )

    async def _test_rapid_requests(self) -> TestResult:
        """Test rapid sequential requests."""
        start = time.time()
        try:
            results = []
            for i in range(3):
                result = await self.provider.generate(f"Say '{i}'")
                results.append(len(result) > 0)
            passed = all(results)
            return TestResult(
                name="Rapid Sequential (3)",
                category="edge_case",
                passed=passed,
                duration=time.time() - start,
                details=f"All {len(results)} succeeded" if passed else "Some failed",
            )
        except Exception as e:
            return TestResult(
                name="Rapid Sequential (3)",
                category="edge_case",
                passed=False,
                duration=time.time() - start,
                error=str(e),
            )

    # =========================================================================
    # REAL-WORLD USE CASES
    # =========================================================================

    async def run_real_world_cases(self):
        """Test real-world use cases."""
        suite = TestSuite(name="Real-World Use Cases")
        print("\n[SUITE] Real-World Use Cases")
        print("-" * 50)

        # Test 1: Code generation
        result = await self._test_code_generation()
        suite.results.append(result)
        self._print_result(result)

        # Test 2: Code explanation
        result = await self._test_code_explanation()
        suite.results.append(result)
        self._print_result(result)

        # Test 3: Bug fixing
        result = await self._test_bug_fixing()
        suite.results.append(result)
        self._print_result(result)

        # Test 4: Algorithm design
        result = await self._test_algorithm_design()
        suite.results.append(result)
        self._print_result(result)

        # Test 5: Data analysis
        result = await self._test_data_analysis()
        suite.results.append(result)
        self._print_result(result)

        # Test 6: Documentation
        result = await self._test_documentation()
        suite.results.append(result)
        self._print_result(result)

        # Test 7: Refactoring
        result = await self._test_refactoring()
        suite.results.append(result)
        self._print_result(result)

        suite.end_time = datetime.now()
        self.suites.append(suite)

    async def _test_code_generation(self) -> TestResult:
        """Test code generation capability."""
        start = time.time()
        try:
            result = await self.provider.generate(
                "Write a Python function to check if a string is a palindrome. Include docstring."
            )
            has_def = "def " in result
            has_return = "return" in result
            passed = has_def and has_return
            return TestResult(
                name="Code Generation",
                category="real_world",
                passed=passed,
                duration=time.time() - start,
                details=f"Has def: {has_def}, Has return: {has_return}",
                metadata={"response_length": len(result)},
            )
        except Exception as e:
            return TestResult(
                name="Code Generation",
                category="real_world",
                passed=False,
                duration=time.time() - start,
                error=str(e),
            )

    async def _test_code_explanation(self) -> TestResult:
        """Test code explanation capability."""
        start = time.time()
        try:
            code = """
def fib(n):
    if n <= 1:
        return n
    return fib(n-1) + fib(n-2)
"""
            result = await self.provider.generate(f"Explain this code:\n{code}")
            has_explanation = len(result) > 100
            mentions_recursion = "recurs" in result.lower()
            passed = has_explanation and mentions_recursion
            return TestResult(
                name="Code Explanation",
                category="real_world",
                passed=passed,
                duration=time.time() - start,
                details=f"Length: {len(result)}, Mentions recursion: {mentions_recursion}",
            )
        except Exception as e:
            return TestResult(
                name="Code Explanation",
                category="real_world",
                passed=False,
                duration=time.time() - start,
                error=str(e),
            )

    async def _test_bug_fixing(self) -> TestResult:
        """Test bug fixing capability."""
        start = time.time()
        try:
            buggy_code = """
def average(numbers):
    return sum(numbers) / len(numbers)
"""
            result = await self.provider.generate(
                f"Fix this bug (division by zero when empty list):\n{buggy_code}"
            )
            mentions_fix = "if" in result or "len" in result or "empty" in result.lower()
            passed = mentions_fix and len(result) > 50
            return TestResult(
                name="Bug Fixing",
                category="real_world",
                passed=passed,
                duration=time.time() - start,
                details=f"Suggests fix: {mentions_fix}",
            )
        except Exception as e:
            return TestResult(
                name="Bug Fixing",
                category="real_world",
                passed=False,
                duration=time.time() - start,
                error=str(e),
            )

    async def _test_algorithm_design(self) -> TestResult:
        """Test algorithm design capability."""
        start = time.time()
        try:
            result = await self.provider.generate(
                "Design an algorithm to find the longest increasing subsequence in an array. Explain the approach."
            )
            has_explanation = len(result) > 200
            mentions_complexity = "O(" in result or "complexity" in result.lower()
            passed = has_explanation
            return TestResult(
                name="Algorithm Design",
                category="real_world",
                passed=passed,
                duration=time.time() - start,
                details=f"Length: {len(result)}, Has complexity: {mentions_complexity}",
            )
        except Exception as e:
            return TestResult(
                name="Algorithm Design",
                category="real_world",
                passed=False,
                duration=time.time() - start,
                error=str(e),
            )

    async def _test_data_analysis(self) -> TestResult:
        """Test data analysis capability."""
        start = time.time()
        try:
            result = await self.provider.generate(
                "Given sales data [100, 150, 120, 200, 180], calculate mean, median, and identify the trend."
            )
            mentions_mean = "mean" in result.lower() or "average" in result.lower()
            mentions_numbers = any(str(n) in result for n in [100, 150, 120, 200, 180])
            passed = mentions_mean or mentions_numbers
            return TestResult(
                name="Data Analysis",
                category="real_world",
                passed=passed,
                duration=time.time() - start,
                details=f"Mentions mean: {mentions_mean}",
            )
        except Exception as e:
            return TestResult(
                name="Data Analysis",
                category="real_world",
                passed=False,
                duration=time.time() - start,
                error=str(e),
            )

    async def _test_documentation(self) -> TestResult:
        """Test documentation generation capability."""
        start = time.time()
        try:
            code = "def process_data(data, threshold=0.5): return [x for x in data if x > threshold]"
            result = await self.provider.generate(f"Write a docstring for: {code}")
            has_docstring = '"""' in result or "'''" in result or "Args" in result or "param" in result.lower()
            passed = has_docstring
            return TestResult(
                name="Documentation",
                category="real_world",
                passed=passed,
                duration=time.time() - start,
                details=f"Has docstring format: {has_docstring}",
            )
        except Exception as e:
            return TestResult(
                name="Documentation",
                category="real_world",
                passed=False,
                duration=time.time() - start,
                error=str(e),
            )

    async def _test_refactoring(self) -> TestResult:
        """Test refactoring capability."""
        start = time.time()
        try:
            code = """
result = []
for i in range(10):
    if i % 2 == 0:
        result.append(i * 2)
"""
            result = await self.provider.generate(f"Refactor to list comprehension:\n{code}")
            has_comprehension = "[" in result and "for" in result and "]" in result
            passed = has_comprehension
            return TestResult(
                name="Refactoring",
                category="real_world",
                passed=passed,
                duration=time.time() - start,
                details=f"Has list comprehension: {has_comprehension}",
            )
        except Exception as e:
            return TestResult(
                name="Refactoring",
                category="real_world",
                passed=False,
                duration=time.time() - start,
                error=str(e),
            )

    # =========================================================================
    # ERROR HANDLING
    # =========================================================================

    async def run_error_handling(self):
        """Test error handling and recovery."""
        suite = TestSuite(name="Error Handling")
        print("\n[SUITE] Error Handling")
        print("-" * 50)

        # Test 1: Provider without API key
        result = await self._test_no_api_key()
        suite.results.append(result)
        self._print_result(result)

        # Test 2: Invalid tool call
        result = await self._test_invalid_tool()
        suite.results.append(result)
        self._print_result(result)

        # Test 3: Provider status when not initialized
        result = await self._test_status_uninitialized()
        suite.results.append(result)
        self._print_result(result)

        suite.end_time = datetime.now()
        self.suites.append(suite)

    async def _test_no_api_key(self) -> TestResult:
        """Test behavior without API key."""
        start = time.time()
        try:
            from jdev_cli.core.providers.prometheus_provider import PrometheusProvider

            # Create provider without key
            old_key = os.environ.pop("GEMINI_API_KEY", None)
            old_google = os.environ.pop("GOOGLE_API_KEY", None)

            provider = PrometheusProvider(api_key=None)
            is_available = provider.is_available()

            # Restore keys
            if old_key:
                os.environ["GEMINI_API_KEY"] = old_key
            if old_google:
                os.environ["GOOGLE_API_KEY"] = old_google

            passed = not is_available  # Should return False
            return TestResult(
                name="No API Key Detection",
                category="error_handling",
                passed=passed,
                duration=time.time() - start,
                details=f"is_available()={is_available}",
            )
        except Exception as e:
            return TestResult(
                name="No API Key Detection",
                category="error_handling",
                passed=False,
                duration=time.time() - start,
                error=str(e),
            )

    async def _test_invalid_tool(self) -> TestResult:
        """Test handling of tool without provider."""
        start = time.time()
        try:
            from jdev_cli.tools.prometheus_tools import PrometheusExecuteTool

            tool = PrometheusExecuteTool()  # No provider
            result = await tool._execute_validated(task="test")

            passed = not result.success  # Should fail gracefully
            return TestResult(
                name="Tool Without Provider",
                category="error_handling",
                passed=passed,
                duration=time.time() - start,
                details=f"Handled gracefully: {not result.success}",
            )
        except Exception as e:
            return TestResult(
                name="Tool Without Provider",
                category="error_handling",
                passed=True,  # Exception is acceptable
                duration=time.time() - start,
                details=f"Raised exception: {type(e).__name__}",
            )

    async def _test_status_uninitialized(self) -> TestResult:
        """Test status when not initialized."""
        start = time.time()
        try:
            from jdev_cli.core.providers.prometheus_provider import PrometheusProvider

            provider = PrometheusProvider()
            # Don't initialize
            status = provider.get_status()

            passed = "not_initialized" in str(status) or status.get("status") == "not_initialized"
            return TestResult(
                name="Status Uninitialized",
                category="error_handling",
                passed=passed,
                duration=time.time() - start,
                details=f"Status: {status}",
            )
        except Exception as e:
            return TestResult(
                name="Status Uninitialized",
                category="error_handling",
                passed=False,
                duration=time.time() - start,
                error=str(e),
            )

    # =========================================================================
    # PERFORMANCE BENCHMARKS
    # =========================================================================

    async def run_performance_benchmarks(self):
        """Test performance metrics."""
        suite = TestSuite(name="Performance Benchmarks")
        print("\n[SUITE] Performance Benchmarks")
        print("-" * 50)

        # Test 1: Response time
        result = await self._test_response_time()
        suite.results.append(result)
        self._print_result(result)

        # Test 2: Initialization time
        result = await self._test_init_time()
        suite.results.append(result)
        self._print_result(result)

        # Test 3: Memory retrieval
        result = await self._test_memory_retrieval()
        suite.results.append(result)
        self._print_result(result)

        suite.end_time = datetime.now()
        self.suites.append(suite)

    async def _test_response_time(self) -> TestResult:
        """Benchmark response time."""
        start = time.time()
        try:
            await self.provider.generate("What is 1+1?")
            duration = time.time() - start

            passed = duration < 60  # Under 60 seconds
            return TestResult(
                name="Response Time",
                category="performance",
                passed=passed,
                duration=duration,
                details=f"{duration:.2f}s (threshold: 60s)",
                metadata={"response_time_seconds": duration},
            )
        except Exception as e:
            return TestResult(
                name="Response Time",
                category="performance",
                passed=False,
                duration=time.time() - start,
                error=str(e),
            )

    async def _test_init_time(self) -> TestResult:
        """Benchmark initialization time."""
        start = time.time()
        try:
            from jdev_cli.core.providers.prometheus_provider import PrometheusProvider

            provider = PrometheusProvider()
            await provider._ensure_initialized()
            duration = time.time() - start

            passed = duration < 30  # Under 30 seconds
            return TestResult(
                name="Initialization Time",
                category="performance",
                passed=passed,
                duration=duration,
                details=f"{duration:.2f}s (threshold: 30s)",
                metadata={"init_time_seconds": duration},
            )
        except Exception as e:
            return TestResult(
                name="Initialization Time",
                category="performance",
                passed=False,
                duration=time.time() - start,
                error=str(e),
            )

    async def _test_memory_retrieval(self) -> TestResult:
        """Benchmark memory retrieval."""
        start = time.time()
        try:
            context = self.provider.get_memory_context("test query")
            duration = time.time() - start

            passed = duration < 5  # Under 5 seconds
            return TestResult(
                name="Memory Retrieval",
                category="performance",
                passed=passed,
                duration=duration,
                details=f"{duration:.2f}s (threshold: 5s)",
                metadata={"context_keys": list(context.keys()) if context else []},
            )
        except Exception as e:
            return TestResult(
                name="Memory Retrieval",
                category="performance",
                passed=False,
                duration=time.time() - start,
                error=str(e),
            )

    # =========================================================================
    # INTEGRATION TESTS
    # =========================================================================

    async def run_integration_tests(self):
        """Test integration between components."""
        suite = TestSuite(name="Integration Tests")
        print("\n[SUITE] Integration Tests")
        print("-" * 50)

        # Test 1: Provider to Orchestrator
        result = await self._test_provider_orchestrator()
        suite.results.append(result)
        self._print_result(result)

        # Test 2: Client to Provider
        result = await self._test_client_provider()
        suite.results.append(result)
        self._print_result(result)

        # Test 3: Full pipeline
        result = await self._test_full_pipeline()
        suite.results.append(result)
        self._print_result(result)

        suite.end_time = datetime.now()
        self.suites.append(suite)

    async def _test_provider_orchestrator(self) -> TestResult:
        """Test Provider → Orchestrator integration."""
        start = time.time()
        try:
            has_orchestrator = self.provider._orchestrator is not None
            has_memory = hasattr(self.provider._orchestrator, 'memory')
            has_world_model = hasattr(self.provider._orchestrator, 'world_model')

            passed = has_orchestrator and has_memory and has_world_model
            return TestResult(
                name="Provider → Orchestrator",
                category="integration",
                passed=passed,
                duration=time.time() - start,
                details=f"Orch: {has_orchestrator}, Mem: {has_memory}, WM: {has_world_model}",
            )
        except Exception as e:
            return TestResult(
                name="Provider → Orchestrator",
                category="integration",
                passed=False,
                duration=time.time() - start,
                error=str(e),
            )

    async def _test_client_provider(self) -> TestResult:
        """Test Client → Provider integration."""
        start = time.time()
        try:
            has_provider = self.client._provider is not None
            health = self.client.get_health_status()

            passed = has_provider and health.get("initialized", False)
            return TestResult(
                name="Client → Provider",
                category="integration",
                passed=passed,
                duration=time.time() - start,
                details=f"Provider: {has_provider}, Health: {health.get('initialized')}",
            )
        except Exception as e:
            return TestResult(
                name="Client → Provider",
                category="integration",
                passed=False,
                duration=time.time() - start,
                error=str(e),
            )

    async def _test_full_pipeline(self) -> TestResult:
        """Test full pipeline: User → Client → Provider → Orchestrator → Response."""
        start = time.time()
        try:
            # Simulate full flow
            result = await self.provider.generate("What is the capital of France?")

            has_response = len(result) > 0
            mentions_paris = "paris" in result.lower()

            passed = has_response and mentions_paris
            return TestResult(
                name="Full Pipeline (E2E)",
                category="integration",
                passed=passed,
                duration=time.time() - start,
                details=f"Response: {len(result)} chars, Correct: {mentions_paris}",
            )
        except Exception as e:
            return TestResult(
                name="Full Pipeline (E2E)",
                category="integration",
                passed=False,
                duration=time.time() - start,
                error=str(e),
            )

    # =========================================================================
    # HELPERS
    # =========================================================================

    def _print_result(self, result: TestResult):
        """Print a single test result."""
        icon = "✓" if result.passed else "✗"
        status = "PASS" if result.passed else "FAIL"
        print(f"  [{icon}] {result.name}: {status} ({result.duration:.2f}s)")
        if result.details:
            print(f"      └─ {result.details}")
        if result.error:
            print(f"      └─ ERROR: {result.error[:100]}")

    def generate_report(self) -> Dict[str, Any]:
        """Generate comprehensive report."""
        total_passed = sum(s.passed for s in self.suites)
        total_failed = sum(s.failed for s in self.suites)
        total_tests = sum(s.total for s in self.suites)
        total_duration = sum(s.total_duration for s in self.suites)

        report = {
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total_tests": total_tests,
                "passed": total_passed,
                "failed": total_failed,
                "success_rate": total_passed / total_tests if total_tests > 0 else 0,
                "total_duration_seconds": total_duration,
            },
            "suites": [],
        }

        print("\n" + "=" * 70)
        print("SCIENTIFIC VALIDATION REPORT")
        print("=" * 70)

        for suite in self.suites:
            suite_data = {
                "name": suite.name,
                "passed": suite.passed,
                "failed": suite.failed,
                "total": suite.total,
                "success_rate": suite.success_rate,
                "duration": suite.total_duration,
                "results": [
                    {
                        "name": r.name,
                        "category": r.category,
                        "passed": r.passed,
                        "duration": r.duration,
                        "details": r.details,
                        "error": r.error,
                    }
                    for r in suite.results
                ],
            }
            report["suites"].append(suite_data)

            status = "PASS" if suite.failed == 0 else "FAIL"
            print(f"\n{suite.name}: [{status}] {suite.passed}/{suite.total}")

        print("\n" + "-" * 70)
        print(f"TOTAL: {total_passed}/{total_tests} ({report['summary']['success_rate']*100:.1f}%)")
        print(f"Duration: {total_duration:.2f}s")
        print("=" * 70)

        return report


async def main():
    validator = ScientificValidator()
    report = await validator.run_all()

    # Save report
    report_path = "tests/prometheus/SCIENTIFIC_VALIDATION_REPORT.json"
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)
    print(f"\nReport saved to: {report_path}")

    return 0 if report["summary"]["failed"] == 0 else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
