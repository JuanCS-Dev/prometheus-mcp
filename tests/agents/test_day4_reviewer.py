"""
Test suite for ReviewerAgent (Day 4).

Philosophy (Boris Cherny):
    "Tests are specifications that execute."
    - Test real scenarios, not mocks
    - Cover edge cases exhaustively
    - Validate Constitutional compliance
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from qwen_dev_cli.agents.base import AgentTask, TaskStatus
from qwen_dev_cli.agents.reviewer import ReviewerAgent, QualityGate, ReviewReport


@pytest.fixture
def mock_llm_client():
    """Mock LLM client."""
    client = MagicMock()
    client.generate_content = AsyncMock(return_value=MagicMock(
        text="Code review complete with good quality. Recommend approval."
    ))
    return client


@pytest.fixture
def mock_mcp_client():
    """Mock MCP server."""
    return MagicMock()


@pytest.fixture
def reviewer_agent(mock_llm_client, mock_mcp_client):
    """Create ReviewerAgent instance."""
    return ReviewerAgent(mock_llm_client, mock_mcp_client)


class TestReviewerAgentInitialization:
    """Test ReviewerAgent initialization."""
    
    def test_initialization(self, reviewer_agent):
        """Test agent initializes with correct role and capabilities."""
        assert reviewer_agent.role.value == "reviewer"
        assert len(reviewer_agent.capabilities) == 2
        assert reviewer_agent.constitutional_rules is not None
    
    def test_constitutional_rules_loaded(self, reviewer_agent):
        """Test constitutional rules are loaded."""
        assert "principles" in reviewer_agent.constitutional_rules
        assert "quality_standards" in reviewer_agent.constitutional_rules
        assert len(reviewer_agent.constitutional_rules["principles"]) == 6


class TestCodeQualityGate:
    """Test code quality gate (Gate 1)."""
    
    @pytest.mark.asyncio
    async def test_gate_passes_with_good_code(self, reviewer_agent):
        """Test quality gate passes with well-written code."""
        file_contents = {
            "test.py": '''
def calculate_sum(numbers: List[int]) -> int:
    """Calculate sum of numbers.
    
    Args:
        numbers: List of integers
    
    Returns:
        Sum of all numbers
    """
    return sum(numbers)
'''
        }
        
        gate = await reviewer_agent._gate_code_quality(file_contents)
        
        assert gate.name == "Code Quality"
        assert gate.passed
        assert gate.score >= 70
        assert len(gate.issues) == 0
    
    @pytest.mark.asyncio
    async def test_gate_detects_long_functions(self, reviewer_agent):
        """Test gate detects functions exceeding 50 lines."""
        long_function = "def long_func():\n" + "    pass\n" * 60
        file_contents = {"test.py": long_function}
        
        gate = await reviewer_agent._gate_code_quality(file_contents)
        
        assert any("exceed 50 lines" in issue for issue in gate.issues)
        assert gate.score < 100
    
    @pytest.mark.asyncio
    async def test_gate_detects_poor_documentation(self, reviewer_agent):
        """Test gate detects insufficient documentation."""
        file_contents = {
            "test.py": '''
def func1():
    pass

def func2():
    pass

def func3():
    """Only one docstring."""
    pass
'''
        }
        
        gate = await reviewer_agent._gate_code_quality(file_contents)
        
        assert any("Documentation coverage" in issue for issue in gate.issues)
        assert gate.score < 100
    
    @pytest.mark.asyncio
    async def test_gate_detects_naming_violations(self, reviewer_agent):
        """Test gate detects PEP 8 naming violations."""
        file_contents = {
            "test.py": '''
def CamelCaseFunction():
    pass

class snake_case_class:
    pass
'''
        }
        
        gate = await reviewer_agent._gate_code_quality(file_contents)
        
        assert len(gate.recommendations) > 0
        assert gate.score < 100


class TestSecurityGate:
    """Test security gate (Gate 2)."""
    
    @pytest.mark.asyncio
    async def test_gate_passes_with_secure_code(self, reviewer_agent):
        """Test security gate passes with secure code."""
        file_contents = {
            "test.py": '''
import os
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("API_KEY")
'''
        }
        
        gate = await reviewer_agent._gate_security(file_contents)
        
        assert gate.name == "Security"
        assert gate.passed
        assert gate.score == 100
    
    @pytest.mark.asyncio
    async def test_gate_detects_hardcoded_passwords(self, reviewer_agent):
        """Test gate detects hardcoded passwords."""
        file_contents = {
            "test.py": 'password = "secret123"'
        }
        
        gate = await reviewer_agent._gate_security(file_contents)
        
        assert not gate.passed
        assert any("hardcoded_password" in issue for issue in gate.issues)
        assert gate.score < 100
    
    @pytest.mark.asyncio
    async def test_gate_detects_api_keys(self, reviewer_agent):
        """Test gate detects hardcoded API keys."""
        file_contents = {
            "test.py": 'api_key = "sk-1234567890abcdef"'
        }
        
        gate = await reviewer_agent._gate_security(file_contents)
        
        assert not gate.passed
        assert any("api_key" in issue for issue in gate.issues)
    
    @pytest.mark.asyncio
    async def test_gate_detects_sql_injection(self, reviewer_agent):
        """Test gate detects SQL injection risks."""
        file_contents = {
            "test.py": '''
query = "SELECT * FROM users WHERE id = " + user_id
cursor.execute(query)
'''
        }
        
        gate = await reviewer_agent._gate_security(file_contents)
        
        assert not gate.passed
        assert any("sql_injection" in issue for issue in gate.issues)
    
    @pytest.mark.asyncio
    async def test_gate_detects_command_injection(self, reviewer_agent):
        """Test gate detects command injection risks."""
        file_contents = {
            "test.py": 'os.system("rm -rf " + user_input)'
        }
        
        gate = await reviewer_agent._gate_security(file_contents)
        
        assert not gate.passed
        assert any("command_injection" in issue for issue in gate.issues)
    
    @pytest.mark.asyncio
    async def test_gate_detects_unsafe_eval(self, reviewer_agent):
        """Test gate detects unsafe eval usage."""
        file_contents = {
            "test.py": 'result = eval(user_input)'
        }
        
        gate = await reviewer_agent._gate_security(file_contents)
        
        assert not gate.passed
        assert any("unsafe_eval" in issue for issue in gate.issues)


class TestTestingGate:
    """Test testing gate (Gate 3)."""
    
    @pytest.mark.asyncio
    async def test_gate_passes_with_good_coverage(self, reviewer_agent):
        """Test gate passes with adequate test coverage."""
        file_contents = {
            "module.py": "def func(): pass",
            "test_module.py": "def test_func(): pass"
        }
        context = {"test_coverage": 90}
        
        gate = await reviewer_agent._gate_testing(file_contents, context)
        
        assert gate.name == "Testing"
        assert gate.passed
        assert gate.score >= 70
    
    @pytest.mark.asyncio
    async def test_gate_fails_with_low_coverage(self, reviewer_agent):
        """Test gate fails with low test coverage."""
        file_contents = {"module.py": "def func(): pass"}
        context = {"test_coverage": 50}
        
        gate = await reviewer_agent._gate_testing(file_contents, context)
        
        assert not gate.passed
        assert any("coverage" in issue.lower() for issue in gate.issues)
    
    @pytest.mark.asyncio
    async def test_gate_detects_missing_tests(self, reviewer_agent):
        """Test gate detects missing test files."""
        file_contents = {
            "module.py": "def func(): pass",
            "utils.py": "def helper(): pass"
        }
        context = {"test_coverage": 0}
        
        gate = await reviewer_agent._gate_testing(file_contents, context)
        
        assert not gate.passed
        assert any("No test files" in issue for issue in gate.issues)
    
    @pytest.mark.asyncio
    async def test_gate_warns_about_mocks(self, reviewer_agent):
        """Test gate warns about excessive mock usage."""
        file_contents = {
            "test_module.py": '''
from unittest.mock import Mock, MagicMock

def test_something():
    mock_obj = Mock()
    mock_obj.method.return_value = True
'''
        }
        context = {"test_coverage": 90}
        
        gate = await reviewer_agent._gate_testing(file_contents, context)
        
        assert any("mock" in rec.lower() for rec in gate.recommendations)


class TestPerformanceGate:
    """Test performance gate (Gate 4)."""
    
    @pytest.mark.asyncio
    async def test_gate_passes_with_efficient_code(self, reviewer_agent):
        """Test gate passes with efficient code."""
        file_contents = {
            "test.py": '''
def process_data(items):
    with open("data.txt") as f:
        return [item.strip() for item in items]
'''
        }
        
        gate = await reviewer_agent._gate_performance(file_contents)
        
        assert gate.name == "Performance"
        assert gate.passed
        assert gate.score >= 70
    
    @pytest.mark.asyncio
    async def test_gate_detects_nested_loops(self, reviewer_agent):
        """Test gate detects deeply nested loops."""
        file_contents = {
            "test.py": '''
for i in range(n):
    for j in range(n):
        for k in range(n):
            for m in range(n):
                process(i, j, k, m)
'''
        }
        
        gate = await reviewer_agent._gate_performance(file_contents)
        
        assert any("nested loops" in issue for issue in gate.issues)
        assert gate.score < 100
    
    @pytest.mark.asyncio
    async def test_gate_detects_resource_leaks(self, reviewer_agent):
        """Test gate detects unclosed file handles."""
        file_contents = {
            "test.py": '''
def read_data():
    f = open("data.txt")
    return f.read()
'''
        }
        
        gate = await reviewer_agent._gate_performance(file_contents)
        
        assert any("context managers" in rec for rec in gate.recommendations)


class TestConstitutionalGate:
    """Test constitutional compliance gate (Gate 5)."""
    
    @pytest.mark.asyncio
    async def test_gate_passes_with_typed_code(self, reviewer_agent):
        """Test gate passes with properly typed code."""
        file_contents = {
            "test.py": '''
from typing import List

def process(items: List[int]) -> int:
    try:
        return sum(items)
    except Exception as e:
        return 0
'''
        }
        
        gate = await reviewer_agent._gate_constitutional(file_contents)
        
        assert gate.name == "Constitutional Compliance"
        assert gate.passed
        assert gate.score >= 80
    
    @pytest.mark.asyncio
    async def test_gate_detects_missing_type_hints(self, reviewer_agent):
        """Test gate detects missing type hints."""
        file_contents = {
            "test.py": '''
def func1(a, b):
    return a + b

def func2(x, y):
    return x * y

def func3(items: List[int]) -> int:
    return sum(items)
'''
        }
        
        gate = await reviewer_agent._gate_constitutional(file_contents)
        
        assert any("Type hint coverage" in issue for issue in gate.issues)
        assert gate.score < 100
    
    @pytest.mark.asyncio
    async def test_gate_recommends_error_handling(self, reviewer_agent):
        """Test gate recommends error handling."""
        file_contents = {
            "test.py": '''
def risky_operation():
    result = 1 / 0
    return result
'''
        }
        
        gate = await reviewer_agent._gate_constitutional(file_contents)
        
        assert any("error handling" in rec.lower() for rec in gate.recommendations)


class TestReviewerAgentExecution:
    """Test ReviewerAgent.execute() method."""
    
    @pytest.mark.asyncio
    async def test_execute_with_valid_files(self, reviewer_agent, mock_mcp_client):
        """Test execute with valid file list."""
        mock_mcp_client.call_tool = AsyncMock(return_value={
            "success": True,
            "content": "def func(): pass"
        })
        
        task = AgentTask(
            request="Review code quality",
            context={
                "files": ["test.py"],
                "test_coverage": 90
            },
            session_id="test_session"
        )
        
        result = await reviewer_agent.execute(task)
        
        assert result.success
        assert "report" in result.data
        assert isinstance(result.data["report"], dict)
    
    @pytest.mark.asyncio
    async def test_execute_generates_comprehensive_report(self, reviewer_agent, mock_mcp_client):
        """Test execute generates comprehensive review report."""
        mock_mcp_client.call_tool = AsyncMock(return_value={
            "success": True,
            "content": '''
def well_documented_function(x: int, y: int) -> int:
    """Add two numbers.
    
    Args:
        x: First number
        y: Second number
    
    Returns:
        Sum of x and y
    """
    try:
        return x + y
    except Exception:
        return 0
'''
        })
        
        task = AgentTask(
            request="Review code",
            context={
                "files": ["math_utils.py"],
                "test_coverage": 95
            },
            session_id="test_session"
        )
        
        result = await reviewer_agent.execute(task)
        
        assert result.success
        report = result.data["report"]
        assert "grade" in report
        assert "overall_score" in report
        assert "gates" in report
        assert len(report["gates"]) == 5
    
    @pytest.mark.asyncio
    async def test_execute_fails_without_files(self, reviewer_agent):
        """Test execute fails without files or diff."""
        task = AgentTask(
            request="Review code",
            context={},
            session_id="test_session"
        )
        
        result = await reviewer_agent.execute(task)
        
        assert not result.success
        assert "error" in result.data


class TestGradeCalculation:
    """Test grade calculation logic."""
    
    def test_calculate_grade_aplus(self, reviewer_agent):
        """Test A+ grade calculation."""
        assert reviewer_agent._calculate_grade(95) == "A+"
        assert reviewer_agent._calculate_grade(100) == "A+"
    
    def test_calculate_grade_a(self, reviewer_agent):
        """Test A grade calculation."""
        assert reviewer_agent._calculate_grade(90) == "A"
        assert reviewer_agent._calculate_grade(94) == "A"
    
    def test_calculate_grade_b(self, reviewer_agent):
        """Test B grade calculation."""
        assert reviewer_agent._calculate_grade(80) == "B"
        assert reviewer_agent._calculate_grade(89) == "B"
    
    def test_calculate_grade_c(self, reviewer_agent):
        """Test C grade calculation."""
        assert reviewer_agent._calculate_grade(70) == "C"
        assert reviewer_agent._calculate_grade(79) == "C"
    
    def test_calculate_grade_d(self, reviewer_agent):
        """Test D grade calculation."""
        assert reviewer_agent._calculate_grade(60) == "D"
        assert reviewer_agent._calculate_grade(69) == "D"
    
    def test_calculate_grade_f(self, reviewer_agent):
        """Test F grade calculation."""
        assert reviewer_agent._calculate_grade(59) == "F"
        assert reviewer_agent._calculate_grade(0) == "F"


class TestHelperMethods:
    """Test helper methods for pattern detection."""
    
    def test_find_long_functions(self, reviewer_agent):
        """Test finding functions exceeding 50 lines."""
        code = "def long_func():\n" + "    pass\n" * 60
        long_funcs = reviewer_agent._find_long_functions(code)
        
        assert len(long_funcs) == 1
        assert "long_func" in long_funcs
    
    def test_calculate_doc_coverage_full(self, reviewer_agent):
        """Test doc coverage calculation with 100% coverage."""
        code = '''
def func1():
    """Docstring 1."""
    pass

def func2():
    """Docstring 2."""
    pass
'''
        coverage = reviewer_agent._calculate_doc_coverage(code)
        assert coverage == 100
    
    def test_calculate_doc_coverage_partial(self, reviewer_agent):
        """Test doc coverage calculation with partial coverage."""
        code = '''
def func1():
    """Docstring."""
    pass

def func2():
    pass

def func3():
    pass
'''
        coverage = reviewer_agent._calculate_doc_coverage(code)
        assert coverage == 33  # 1 out of 3
    
    def test_check_naming_conventions_violations(self, reviewer_agent):
        """Test naming convention violation detection."""
        code = '''
def CamelCase():
    pass

class snake_case:
    pass
'''
        issues = reviewer_agent._check_naming_conventions(code)
        
        assert len(issues) == 2
        assert any("CamelCase" in issue for issue in issues)
        assert any("snake_case" in issue for issue in issues)
    
    def test_find_nested_loops_simple(self, reviewer_agent):
        """Test nested loop detection - simple case."""
        code = '''
for i in range(10):
    for j in range(10):
        print(i, j)
'''
        depth = reviewer_agent._find_nested_loops(code)
        assert depth == 2
    
    def test_find_nested_loops_deep(self, reviewer_agent):
        """Test nested loop detection - deep nesting."""
        code = '''
for i in range(n):
    for j in range(n):
        for k in range(n):
            process(i, j, k)
'''
        depth = reviewer_agent._find_nested_loops(code)
        assert depth == 3


class TestRealWorldScenarios:
    """Test real-world code review scenarios."""
    
    @pytest.mark.asyncio
    async def test_review_production_ready_code(self, reviewer_agent, mock_mcp_client):
        """Test reviewing production-ready code."""
        mock_mcp_client.call_tool = AsyncMock(return_value={
            "success": True,
            "content": '''
from typing import List, Optional

def calculate_average(numbers: List[float]) -> Optional[float]:
    """Calculate average of numbers.
    
    Args:
        numbers: List of numbers to average
    
    Returns:
        Average value or None if list is empty
    """
    try:
        if not numbers:
            return None
        return sum(numbers) / len(numbers)
    except Exception as e:
        logging.error(f"Error calculating average: {e}")
        return None
'''
        })
        
        task = AgentTask(
            request="Review production code",
            context={
                "files": ["math_utils.py"],
                "test_coverage": 95
            },
            session_id="test_session"
        )
        
        result = await reviewer_agent.execute(task)
        
        assert result.success
        report = result.data["report"]
        assert report["approved"]
        assert report["grade"] in ["A+", "A"]
    
    @pytest.mark.asyncio
    async def test_review_insecure_code(self, reviewer_agent, mock_mcp_client):
        """Test reviewing code with security issues."""
        mock_mcp_client.call_tool = AsyncMock(return_value={
            "success": True,
            "content": '''
password = "admin123"
api_key = "sk-1234567890"

def execute_query(user_input):
    query = "SELECT * FROM users WHERE name = " + user_input
    cursor.execute(query)
'''
        })
        
        task = AgentTask(
            request="Review security",
            context={
                "files": ["auth.py"],
                "test_coverage": 80
            },
            session_id="test_session"
        )
        
        result = await reviewer_agent.execute(task)
        
        assert result.success
        report = result.data["report"]
        assert not report["approved"]
        assert len(report["critical_issues"]) > 0
        assert report["grade"] in ["D", "F"]
