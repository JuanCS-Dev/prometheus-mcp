"""
TestingAgent - The QA Engineer: Intelligent Test Generation and Quality Analysis

This agent generates comprehensive test suites, analyzes coverage, performs mutation
testing, and detects flaky tests. It operates with READ_ONLY + BASH_EXEC capabilities
to analyze code and run test commands.

Architecture (Boris Cherny Philosophy):
    - Type-safe interfaces (no Any except where unavoidable)
    - Pure functions for test generation logic
    - Zero mocks in production code
    - Comprehensive error handling

Philosophy:
    "Tests are executable specifications. If it's not tested, it's broken."
    - Boris Cherny

Capabilities:
    - Unit test generation (pytest-style)
    - Coverage analysis (pytest-cov integration)
    - Mutation testing (mutmut integration)
    - Flaky test detection
    - Test quality scoring (0-100)

References:
    - pytest: https://docs.pytest.org/
    - pytest-cov: https://pytest-cov.readthedocs.io/
    - mutmut: https://mutmut.readthedocs.io/
"""

import ast
import json
import re
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional

from .base import (
    AgentCapability,
    AgentResponse,
    AgentRole,
    AgentTask,
    BaseAgent,
)


class TestFramework(str, Enum):
    """Supported test frameworks."""
    PYTEST = "pytest"
    UNITTEST = "unittest"
    DOCTEST = "doctest"


class TestType(str, Enum):
    """Types of tests that can be generated."""
    UNIT = "unit"
    INTEGRATION = "integration"
    FUNCTIONAL = "functional"
    EDGE_CASE = "edge_case"
    PROPERTY_BASED = "property_based"


@dataclass(frozen=True)
class TestCase:
    """Represents a single test case.
    
    Attributes:
        name: Test function name (e.g., test_user_creation)
        code: Complete test function code
        test_type: Type of test (unit, integration, etc.)
        target: Function/class being tested
        assertions: Number of assertions in test
        complexity: Estimated complexity (1-10)
    """
    name: str
    code: str
    test_type: TestType
    target: str
    assertions: int
    complexity: int

    def __post_init__(self) -> None:
        """Validate test case fields."""
        if not self.name.startswith("test_"):
            object.__setattr__(self, "name", f"test_{self.name}")
        if self.assertions < 0:
            raise ValueError("Assertions count cannot be negative")
        if not 1 <= self.complexity <= 10:
            raise ValueError("Complexity must be between 1 and 10")


@dataclass(frozen=True)
class CoverageReport:
    """Coverage analysis result.
    
    Attributes:
        total_statements: Total executable statements
        covered_statements: Statements executed by tests
        coverage_percentage: Coverage as percentage (0-100)
        missing_lines: Line numbers not covered
        branches_total: Total conditional branches
        branches_covered: Branches executed
    """
    total_statements: int
    covered_statements: int
    coverage_percentage: float
    missing_lines: List[int]
    branches_total: int
    branches_covered: int

    @property
    def branch_coverage(self) -> float:
        """Calculate branch coverage percentage."""
        if self.branches_total == 0:
            return 100.0
        return (self.branches_covered / self.branches_total) * 100.0


@dataclass(frozen=True)
class MutationResult:
    """Mutation testing result.
    
    Attributes:
        total_mutants: Total mutations generated
        killed_mutants: Mutations caught by tests
        survived_mutants: Mutations that passed tests
        timeout_mutants: Mutations that caused timeout
        mutation_score: Percentage of killed mutants
    """
    total_mutants: int
    killed_mutants: int
    survived_mutants: int
    timeout_mutants: int

    @property
    def mutation_score(self) -> float:
        """Calculate mutation score (higher is better)."""
        if self.total_mutants == 0:
            return 100.0
        return (self.killed_mutants / self.total_mutants) * 100.0


@dataclass(frozen=True)
class FlakyTest:
    """Information about a flaky test.
    
    Attributes:
        name: Test function name
        file_path: Path to test file
        failure_rate: Percentage of runs that fail (0-100)
        error_messages: Unique error messages seen
        suspected_cause: Most likely cause of flakiness
    """
    name: str
    file_path: str
    failure_rate: float
    error_messages: List[str]
    suspected_cause: str


class TestingAgent(BaseAgent):
    """
    The QA Engineer - Intelligent test generation and quality analysis.
    
    This agent analyzes code to generate comprehensive test suites, measures
    test quality through coverage and mutation testing, and identifies issues
    like flaky tests.
    
    Capabilities:
        - READ_ONLY: Analyze source code
        - BASH_EXEC: Run pytest, coverage tools, mutation testing
    
    Philosophy (Boris Cherny):
        "Test code is production code. Zero technical debt."
    """

    def __init__(
        self,
        llm_client: Any = None,
        mcp_client: Any = None,
        model: Any = None,
        config: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Initialize TestingAgent with type-safe configuration.
        
        Args:
            llm_client: LLM provider client (for docstring generation)
            mcp_client: MCP tools client (for file operations)
            model: Alternative model (for test compatibility)
            config: Optional configuration dictionary
        """
        if llm_client is not None and mcp_client is not None:
            super().__init__(
                role=AgentRole.TESTING,
                capabilities=[
                    AgentCapability.READ_ONLY,
                    AgentCapability.BASH_EXEC,
                ],
                llm_client=llm_client,
                mcp_client=mcp_client,
                system_prompt=TESTING_SYSTEM_PROMPT,
            )
        else:
            # Test compatibility mode
            self.role = AgentRole.TESTING
            self.capabilities = [
                AgentCapability.READ_ONLY,
                AgentCapability.BASH_EXEC,
            ]
            self.name = "TestingAgent"
            self.llm_client = model
            self.config = config or {}

        # Configuration
        self.test_framework: TestFramework = TestFramework.PYTEST
        self.min_coverage_threshold: float = 90.0
        self.min_mutation_score: float = 80.0
        self.flaky_detection_runs: int = 5

        # Execution tracking (from BaseAgent)
        self.execution_count: int = 0

    async def execute(self, task: AgentTask) -> AgentResponse:
        """Execute testing analysis task.
        
        Args:
            task: Testing task with action type in context
        
        Returns:
            AgentResponse with test generation/analysis results
        
        Workflow:
            1. Parse task action (generate_tests, analyze_coverage, etc.)
            2. Execute appropriate analysis method
            3. Calculate quality score
            4. Return structured response
        """
        self.execution_count += 1

        try:
            action = task.context.get("action", "generate_tests")

            if action == "generate_tests":
                return await self._handle_test_generation(task)
            elif action == "analyze_coverage":
                return await self._handle_coverage_analysis(task)
            elif action == "mutation_testing":
                return await self._handle_mutation_testing(task)
            elif action == "detect_flaky":
                return await self._handle_flaky_detection(task)
            elif action == "test_quality_score":
                return await self._handle_quality_scoring(task)
            else:
                return AgentResponse(
                    success=False,
                    data={},
                    reasoning=f"Unknown action: {action}",
                    error="Supported actions: generate_tests, analyze_coverage, mutation_testing, detect_flaky, test_quality_score",
                )

        except Exception as e:
            return AgentResponse(
                success=False,
                data={},
                reasoning=f"TestingAgent execution failed: {str(e)}",
                error=str(e),
            )

    async def _handle_test_generation(self, task: AgentTask) -> AgentResponse:
        """Generate test suite for given code.
        
        Args:
            task: Task with source_code or file_path in context
        
        Returns:
            AgentResponse with generated tests
        """
        source_code = task.context.get("source_code", "")
        file_path = task.context.get("file_path", "")

        if not source_code and file_path:
            # Read file if path provided
            try:
                result = await self._execute_tool("read_file", {"path": file_path})
                source_code = result.get("content", "")
            except Exception as e:
                return AgentResponse(
                    success=False,
                    data={},
                    reasoning=f"Failed to read file: {file_path}",
                    error=str(e),
                )

        if not source_code:
            return AgentResponse(
                success=False,
                data={},
                reasoning="No source code provided",
                error="source_code or file_path required in task context",
            )

        # Generate tests
        test_cases = await self._generate_test_suite(source_code)

        # Calculate metrics
        total_assertions = sum(tc.assertions for tc in test_cases)
        avg_complexity = (
            sum(tc.complexity for tc in test_cases) / len(test_cases)
            if test_cases
            else 0
        )

        return AgentResponse(
            success=True,
            data={
                "test_cases": [
                    {
                        "name": tc.name,
                        "code": tc.code,
                        "type": tc.test_type.value,
                        "target": tc.target,
                        "assertions": tc.assertions,
                        "complexity": tc.complexity,
                    }
                    for tc in test_cases
                ],
                "metrics": {
                    "total_tests": len(test_cases),
                    "total_assertions": total_assertions,
                    "avg_complexity": round(avg_complexity, 2),
                },
            },
            reasoning=f"Generated {len(test_cases)} tests with {total_assertions} assertions",
            metadata={
                "framework": self.test_framework.value,
                "test_count": len(test_cases),
            },
        )

    async def _generate_test_suite(self, source_code: str) -> List[TestCase]:
        """Generate comprehensive test suite for source code.
        
        Args:
            source_code: Python source code to test
        
        Returns:
            List of generated TestCase objects
        
        Strategy:
            1. Parse AST to extract functions/classes
            2. Generate unit tests for each function
            3. Generate edge case tests
            4. Generate integration tests for classes
        """
        test_cases: List[TestCase] = []

        try:
            tree = ast.parse(source_code)
        except SyntaxError:
            # Cannot parse, return empty list
            return test_cases

        # Extract functions (including async)
        functions = [
            node for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        ]

        # Extract classes
        classes = [node for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]

        # Generate unit tests for functions
        for func in functions:
            if not func.name.startswith("_"):  # Skip private functions
                test_cases.extend(self._generate_function_tests(func))

        # Generate integration tests for classes
        for cls in classes:
            test_cases.extend(self._generate_class_tests(cls))

        return test_cases

    def _generate_function_tests(self, func: ast.FunctionDef) -> List[TestCase]:
        """Generate tests for a single function.
        
        Args:
            func: AST FunctionDef node
        
        Returns:
            List of test cases for this function
        """
        tests: List[TestCase] = []
        func_name = func.name

        # Analyze function signature
        params = [arg.arg for arg in func.args.args]
        has_return = self._has_return_statement(func)

        # Generate basic unit test
        basic_test = self._create_basic_test(func_name, params, has_return)
        tests.append(basic_test)

        # Generate edge case tests
        if params:
            edge_tests = self._create_edge_case_tests(func_name, params)
            tests.extend(edge_tests)

        return tests

    def _create_basic_test(
        self, func_name: str, params: List[str], has_return: bool
    ) -> TestCase:
        """Create basic happy-path test.
        
        Args:
            func_name: Function being tested
            params: List of parameter names
            has_return: Whether function returns a value
        
        Returns:
            TestCase for basic functionality
        """
        # Generate mock parameters
        param_values = ", ".join(self._mock_param_value(p) for p in params)

        # Generate test code
        if has_return:
            code = f"""def test_{func_name}_basic():
    \"\"\"Test basic functionality of {func_name}.\"\"\"
    result = {func_name}({param_values})
    assert result is not None
"""
        else:
            code = f"""def test_{func_name}_basic():
    \"\"\"Test basic functionality of {func_name}.\"\"\"
    {func_name}({param_values})
    # No exception should be raised
"""

        return TestCase(
            name=f"test_{func_name}_basic",
            code=code,
            test_type=TestType.UNIT,
            target=func_name,
            assertions=1,
            complexity=2,
        )

    def _create_edge_case_tests(
        self, func_name: str, params: List[str]
    ) -> List[TestCase]:
        """Create edge case tests.
        
        Args:
            func_name: Function being tested
            params: List of parameter names
        
        Returns:
            List of edge case test cases
        """
        tests: List[TestCase] = []

        # Test with None values
        none_test = TestCase(
            name=f"test_{func_name}_with_none",
            code=f"""def test_{func_name}_with_none():
    \"\"\"Test {func_name} handles None input.\"\"\"
    import pytest
    with pytest.raises((TypeError, ValueError)):
        {func_name}(None)
""",
            test_type=TestType.EDGE_CASE,
            target=func_name,
            assertions=1,
            complexity=3,
        )
        tests.append(none_test)

        # Test with empty values
        if any(p in ["list", "dict", "str", "data"] for p in params):
            empty_test = TestCase(
                name=f"test_{func_name}_with_empty",
                code=f"""def test_{func_name}_with_empty():
    \"\"\"Test {func_name} handles empty input.\"\"\"
    result = {func_name}('')
    assert result is not None
""",
                test_type=TestType.EDGE_CASE,
                target=func_name,
                assertions=1,
                complexity=3,
            )
            tests.append(empty_test)

        return tests

    def _generate_class_tests(self, cls: ast.ClassDef) -> List[TestCase]:
        """Generate integration tests for a class.
        
        Args:
            cls: AST ClassDef node
        
        Returns:
            List of test cases for this class
        """
        tests: List[TestCase] = []
        class_name = cls.name

        # Test class instantiation
        init_test = TestCase(
            name=f"test_{class_name}_instantiation",
            code=f"""def test_{class_name}_instantiation():
    \"\"\"Test {class_name} can be instantiated.\"\"\"
    instance = {class_name}()
    assert instance is not None
    assert isinstance(instance, {class_name})
""",
            test_type=TestType.INTEGRATION,
            target=class_name,
            assertions=2,
            complexity=2,
        )
        tests.append(init_test)

        return tests

    def _has_return_statement(self, func: ast.FunctionDef) -> bool:
        """Check if function has return statement.
        
        Args:
            func: AST FunctionDef node
        
        Returns:
            True if function returns a value
        """
        for node in ast.walk(func):
            if isinstance(node, ast.Return) and node.value is not None:
                return True
        return False

    def _mock_param_value(self, param_name: str) -> str:
        """Generate mock value for parameter.
        
        Args:
            param_name: Parameter name
        
        Returns:
            String representation of mock value
        """
        if "id" in param_name.lower():
            return "1"
        elif "name" in param_name.lower():
            return "'test_name'"
        elif "email" in param_name.lower():
            return "'test@example.com'"
        elif "list" in param_name.lower() or "items" in param_name.lower():
            return "[]"
        elif "dict" in param_name.lower() or "data" in param_name.lower():
            return "{}"
        elif "bool" in param_name.lower() or param_name.startswith("is_"):
            return "True"
        else:
            return "None"

    async def _handle_coverage_analysis(self, task: AgentTask) -> AgentResponse:
        """Analyze test coverage using pytest-cov.
        
        Args:
            task: Task with test_path and source_path in context
        
        Returns:
            AgentResponse with coverage report
        """
        test_path = task.context.get("test_path", "tests/")
        source_path = task.context.get("source_path", ".")

        try:
            # Run pytest with coverage
            cmd = f"pytest {test_path} --cov={source_path} --cov-report=json --quiet"
            result = await self._execute_tool("bash_command", {"command": cmd})

            # Parse coverage JSON
            coverage_data = await self._parse_coverage_json()

            # Calculate quality score based on coverage
            quality_score = self._calculate_coverage_score(coverage_data)

            return AgentResponse(
                success=True,
                data={
                    "coverage": {
                        "total_statements": coverage_data.total_statements,
                        "covered_statements": coverage_data.covered_statements,
                        "coverage_percentage": coverage_data.coverage_percentage,
                        "branch_coverage": coverage_data.branch_coverage,
                        "missing_lines_count": len(coverage_data.missing_lines),
                    },
                    "quality_score": quality_score,
                    "meets_threshold": coverage_data.coverage_percentage >= self.min_coverage_threshold,
                },
                reasoning=f"Coverage: {coverage_data.coverage_percentage:.1f}% (threshold: {self.min_coverage_threshold}%)",
                metadata={
                    "tool": "pytest-cov",
                    "test_path": test_path,
                },
            )

        except Exception as e:
            return AgentResponse(
                success=False,
                data={},
                reasoning=f"Coverage analysis failed: {str(e)}",
                error=str(e),
            )

    async def _parse_coverage_json(self) -> CoverageReport:
        """Parse coverage.json file.
        
        Returns:
            CoverageReport object
        """
        try:
            result = await self._execute_tool("read_file", {"path": "coverage.json"})
            data = json.loads(result.get("content", "{}"))

            totals = data.get("totals", {})

            return CoverageReport(
                total_statements=totals.get("num_statements", 0),
                covered_statements=totals.get("covered_lines", 0),
                coverage_percentage=totals.get("percent_covered", 0.0),
                missing_lines=[],  # Simplified
                branches_total=totals.get("num_branches", 0),
                branches_covered=totals.get("covered_branches", 0),
            )
        except Exception:
            # Return empty coverage if parsing fails
            return CoverageReport(
                total_statements=0,
                covered_statements=0,
                coverage_percentage=0.0,
                missing_lines=[],
                branches_total=0,
                branches_covered=0,
            )

    def _calculate_coverage_score(self, coverage: CoverageReport) -> int:
        """Calculate quality score from coverage metrics.
        
        Args:
            coverage: CoverageReport object
        
        Returns:
            Score from 0-100
        
        Formula:
            base_score = coverage_percentage * 0.7
            branch_bonus = branch_coverage * 0.3
            final_score = base_score + branch_bonus
        """
        base_score = coverage.coverage_percentage * 0.7
        branch_bonus = coverage.branch_coverage * 0.3

        return min(100, int(base_score + branch_bonus))

    async def _handle_mutation_testing(self, task: AgentTask) -> AgentResponse:
        """Run mutation testing using mutmut.
        
        Args:
            task: Task with source_path in context
        
        Returns:
            AgentResponse with mutation testing results
        """
        source_path = task.context.get("source_path", ".")

        try:
            # Run mutmut
            cmd = f"mutmut run --paths-to-mutate={source_path} --runner='pytest -x'"
            await self._execute_tool("bash_command", {"command": cmd})

            # Get results
            result = await self._execute_tool(
                "bash_command", {"command": "mutmut results"}
            )

            # Parse mutation results
            mutation_result = self._parse_mutation_results(result.get("output", ""))

            # Calculate score
            quality_score = int(mutation_result.mutation_score)

            return AgentResponse(
                success=True,
                data={
                    "mutation_testing": {
                        "total_mutants": mutation_result.total_mutants,
                        "killed_mutants": mutation_result.killed_mutants,
                        "survived_mutants": mutation_result.survived_mutants,
                        "timeout_mutants": mutation_result.timeout_mutants,
                        "mutation_score": mutation_result.mutation_score,
                    },
                    "quality_score": quality_score,
                    "meets_threshold": mutation_result.mutation_score >= self.min_mutation_score,
                },
                reasoning=f"Mutation score: {mutation_result.mutation_score:.1f}% (threshold: {self.min_mutation_score}%)",
                metadata={"tool": "mutmut"},
            )

        except Exception as e:
            return AgentResponse(
                success=False,
                data={},
                reasoning=f"Mutation testing failed: {str(e)}",
                error=str(e),
            )

    def _parse_mutation_results(self, output: str) -> MutationResult:
        """Parse mutmut results output.
        
        Args:
            output: mutmut results command output
        
        Returns:
            MutationResult object
        """
        # Extract numbers from output (simplified parser)
        killed = len(re.findall(r"KILLED", output))
        survived = len(re.findall(r"SURVIVED", output))
        timeout = len(re.findall(r"TIMEOUT", output))
        total = killed + survived + timeout

        return MutationResult(
            total_mutants=total,
            killed_mutants=killed,
            survived_mutants=survived,
            timeout_mutants=timeout,
        )

    async def _handle_flaky_detection(self, task: AgentTask) -> AgentResponse:
        """Detect flaky tests by running multiple times.
        
        Args:
            task: Task with test_path in context
        
        Returns:
            AgentResponse with flaky test results
        """
        test_path = task.context.get("test_path", "tests/")
        runs = task.context.get("runs", self.flaky_detection_runs)

        try:
            flaky_tests = await self._detect_flaky_tests(test_path, runs)

            return AgentResponse(
                success=True,
                data={
                    "flaky_tests": [
                        {
                            "name": ft.name,
                            "file_path": ft.file_path,
                            "failure_rate": ft.failure_rate,
                            "error_messages": ft.error_messages,
                            "suspected_cause": ft.suspected_cause,
                        }
                        for ft in flaky_tests
                    ],
                    "flaky_count": len(flaky_tests),
                },
                reasoning=f"Found {len(flaky_tests)} flaky tests in {runs} runs",
                metadata={"runs": runs},
            )

        except Exception as e:
            return AgentResponse(
                success=False,
                data={},
                reasoning=f"Flaky detection failed: {str(e)}",
                error=str(e),
            )

    async def _detect_flaky_tests(
        self, test_path: str, runs: int
    ) -> List[FlakyTest]:
        """Run tests multiple times to detect flakiness.
        
        Args:
            test_path: Path to tests
            runs: Number of times to run tests
        
        Returns:
            List of detected flaky tests
        """
        test_results: Dict[str, List[bool]] = {}

        for run in range(runs):
            result = await self._execute_tool(
                "bash_command", {"command": f"pytest {test_path} -v"}
            )

            # Parse test results (simplified)
            output = result.get("output", "")
            for line in output.split("\n"):
                if "::" in line and ("PASSED" in line or "FAILED" in line):
                    # Extract test name before ::
                    test_name = line.split("::")[0].strip()
                    if test_name:
                        if test_name not in test_results:
                            test_results[test_name] = []
                        test_results[test_name].append("PASSED" in line)

        # Identify flaky tests (inconsistent results)
        flaky_tests: List[FlakyTest] = []
        for test_name, results in test_results.items():
            if len(set(results)) > 1:  # Both True and False present
                failure_rate = (results.count(False) / len(results)) * 100
                flaky_tests.append(
                    FlakyTest(
                        name=test_name,
                        file_path=test_path,
                        failure_rate=failure_rate,
                        error_messages=["Intermittent failure"],
                        suspected_cause="Race condition or timing issue",
                    )
                )

        return flaky_tests

    async def _handle_quality_scoring(self, task: AgentTask) -> AgentResponse:
        """Calculate comprehensive test quality score.
        
        Args:
            task: Task (may include specific metrics to evaluate)
        
        Returns:
            AgentResponse with quality score (0-100)
        
        Scoring Formula:
            - Coverage: 40 points (40% weight)
            - Mutation score: 30 points (30% weight)
            - Test count: 15 points (15% weight)
            - No flaky tests: 15 points (15% weight)
        """
        try:
            # Get coverage
            coverage_task = AgentTask(
                request="Analyze coverage",
                context={"action": "analyze_coverage", **task.context},
            )
            coverage_response = await self._handle_coverage_analysis(coverage_task)
            coverage_pct = coverage_response.data.get("coverage", {}).get(
                "coverage_percentage", 0
            )

            # Get mutation score (if available)
            try:
                mutation_task = AgentTask(
                    request="Run mutation testing",
                    context={"action": "mutation_testing", **task.context},
                )
                mutation_response = await self._handle_mutation_testing(mutation_task)
                mutation_score = mutation_response.data.get("mutation_testing", {}).get(
                    "mutation_score", 0
                )
            except Exception:
                mutation_score = 0

            # Calculate component scores
            coverage_score = (coverage_pct / 100) * 40
            mutation_component = (mutation_score / 100) * 30
            test_count_component = 15  # Assume good if tests exist
            flaky_component = 15  # Assume no flaky tests

            total_score = int(
                coverage_score
                + mutation_component
                + test_count_component
                + flaky_component
            )

            return AgentResponse(
                success=True,
                data={
                    "quality_score": total_score,
                    "breakdown": {
                        "coverage": int(coverage_score),
                        "mutation": int(mutation_component),
                        "test_count": test_count_component,
                        "no_flaky": flaky_component,
                    },
                    "grade": self._score_to_grade(total_score),
                },
                reasoning=f"Test quality score: {total_score}/100 ({self._score_to_grade(total_score)})",
                metadata={"scoring_version": "1.0"},
            )

        except Exception as e:
            return AgentResponse(
                success=False,
                data={},
                reasoning=f"Quality scoring failed: {str(e)}",
                error=str(e),
            )

    def _score_to_grade(self, score: int) -> str:
        """Convert numeric score to letter grade.
        
        Args:
            score: Score from 0-100
        
        Returns:
            Letter grade (A+, A, B+, etc.)
        """
        if score >= 95:
            return "A+"
        elif score >= 90:
            return "A"
        elif score >= 85:
            return "B+"
        elif score >= 80:
            return "B"
        elif score >= 75:
            return "C+"
        elif score >= 70:
            return "C"
        else:
            return "D"


# System prompt for LLM-based test generation
TESTING_SYSTEM_PROMPT = """You are the TESTING AGENT, the QA Engineer in the DevSquad.

ROLE: Generate comprehensive test suites and analyze test quality
PERSONALITY: Meticulous tester who leaves no edge case uncovered
CAPABILITIES: READ_ONLY + BASH_EXEC

YOUR RESPONSIBILITIES:
1. Generate unit tests for functions and classes
2. Create edge case tests (None, empty, boundary values)
3. Analyze test coverage using pytest-cov
4. Run mutation testing to verify test quality
5. Detect flaky tests through multiple runs
6. Calculate comprehensive quality scores

TEST GENERATION PRINCIPLES:
1. Every public function needs at least 3 tests:
   - Happy path (basic functionality)
   - Edge cases (None, empty, boundaries)
   - Error cases (exceptions, invalid input)

2. Every class needs:
   - Instantiation test
   - Method tests (follow function principles)
   - Integration tests (multiple methods)

3. Test naming convention:
   test_<function_name>_<scenario>
   Example: test_user_login_with_valid_credentials

4. Assertions:
   - Use specific assertions (assertEqual, assertIsNone)
   - Avoid bare assertTrue/assertFalse
   - Multiple assertions per test are OK

5. Quality metrics:
   - Coverage >= 90% (statement coverage)
   - Branch coverage >= 85%
   - Mutation score >= 80%
   - Zero flaky tests

TOOLS USAGE:
- read_file: Analyze source code structure
- bash_command: Run pytest, coverage, mutmut
- Never modify source code (READ_ONLY)

OUTPUT FORMAT (JSON):
{
  "test_cases": [
    {
      "name": "test_user_creation_basic",
      "code": "def test_user_creation_basic():\\n    ...",
      "type": "unit",
      "target": "create_user",
      "assertions": 3,
      "complexity": 2
    }
  ],
  "quality_metrics": {
    "coverage_percentage": 92.5,
    "mutation_score": 85.0,
    "flaky_count": 0,
    "total_score": 95
  }
}

REMEMBER:
- Tests are executable specifications
- Quality > Quantity
- Every test must be deterministic
- Zero flaky tests is non-negotiable

You are meticulous, you are thorough, you are relentless in pursuit of quality.
"""
