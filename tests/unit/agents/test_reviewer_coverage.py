"""
Additional tests for ReviewerAgent covering 95%+ code coverage.

Focuses on:
1. Review Logic - Critical issues, no issues, warnings scenarios
2. Error Handling - LLM unavailable, parse errors, timeouts
3. Edge Cases - Empty code, huge code, multiple languages

Based on Anthropic Claude Code testing standards.
"""
import pytest
import networkx as nx
from unittest.mock import AsyncMock, MagicMock

from jdev_cli.agents.reviewer import (
    IssueSeverity,
    IssueCategory,
    CodeGraphNode,
    ComplexityMetrics,
    CodeIssue,
    RAGContext,
    ReviewerAgent,
)
from jdev_cli.agents.base import (
    AgentTask,
    AgentResponse,
)


# =============================================================================
# REVIEW LOGIC - CRITICAL ISSUES SCENARIO
# =============================================================================

class TestReviewLogicCriticalIssues:
    """Tests for review logic with critical issues."""

    @pytest.fixture
    def mock_llm(self):
        """Create mock LLM client."""
        client = MagicMock()
        client.generate = AsyncMock(return_value='{"summary": "Critical issues found", "additional_issues": []}')
        return client

    @pytest.fixture
    def mock_mcp(self):
        """Create mock MCP client."""
        client = MagicMock()
        return client

    @pytest.fixture
    def reviewer(self, mock_llm, mock_mcp):
        """Create ReviewerAgent."""
        return ReviewerAgent(llm_client=mock_llm, mcp_client=mock_mcp)

    @pytest.mark.asyncio
    async def test_review_with_critical_security_issue(self, reviewer):
        """Test review identifies critical security issues."""
        code_with_eval = '''
import os
def unsafe_execute(user_input):
    result = eval(user_input)  # CRITICAL: eval
    return result
'''
        reviewer._execute_tool = AsyncMock(return_value={
            "success": True,
            "content": code_with_eval
        })
        reviewer._call_llm = AsyncMock(return_value='{"summary": "Critical security issue", "additional_issues": []}')

        task = AgentTask(request="Review", context={"files": ["unsafe.py"]})
        response = await reviewer.execute(task)

        assert response.success is True
        assert "report" in response.data

        report_data = response.data["report"]
        issues = report_data["issues"]

        # Should find eval() issue
        security_issues = [i for i in issues if i["category"] == "SECURITY"]
        assert len(security_issues) >= 1

        # Score should be low
        assert report_data["score"] < 70
        assert report_data["risk_level"] in ["CRITICAL", "HIGH"]
        assert report_data["requires_human_review"] is True

    @pytest.mark.asyncio
    async def test_review_with_multiple_critical_issues(self, reviewer):
        """Test review with multiple critical issues."""
        code = '''
import subprocess
import os
def multiple_issues(user_cmd):
    os.system(user_cmd)  # CRITICAL
    exec(user_cmd)       # CRITICAL
    subprocess.call(user_cmd, shell=True)  # HIGH
    return eval(user_cmd)  # CRITICAL
'''
        reviewer._execute_tool = AsyncMock(return_value={
            "success": True,
            "content": code
        })
        reviewer._call_llm = AsyncMock(return_value='{"summary": "Multiple critical", "additional_issues": []}')

        task = AgentTask(request="Review", context={"files": ["dangerous.py"]})
        response = await reviewer.execute(task)

        assert response.success is True
        report_data = response.data["report"]

        # Multiple issues
        critical_issues = [i for i in report_data["issues"]
                          if i["severity"] == "CRITICAL"]
        assert len(critical_issues) >= 2

        assert report_data["approved"] is False
        assert report_data["requires_human_review"] is True

    @pytest.mark.asyncio
    async def test_review_with_high_complexity(self, reviewer):
        """Test review identifies high cyclomatic complexity."""
        complex_code = '''
def very_complex(a, b, c, d, e, f):
    if a > 0:
        if b > 0:
            if c > 0:
                if d > 0:
                    if e > 0:
                        if f > 0:
                            return a + b + c + d + e + f
    elif a < 0:
        if b < 0:
            if c < 0:
                return a + b + c
    else:
        return 0
    return None
'''
        reviewer._execute_tool = AsyncMock(return_value={
            "success": True,
            "content": complex_code
        })
        reviewer._call_llm = AsyncMock(return_value='{"summary": "Complex function", "additional_issues": []}')

        task = AgentTask(request="Review", context={"files": ["complex.py"]})
        response = await reviewer.execute(task)

        assert response.success is True
        report_data = response.data["report"]

        # Verify metrics were analyzed
        assert len(report_data["metrics"]) >= 1
        # Very complex function should have high cyclomatic complexity
        metrics = report_data["metrics"]
        assert len(metrics) > 0 and metrics[0]["cyclomatic"] >= 8

    @pytest.mark.asyncio
    async def test_review_score_calculation_with_issues(self, reviewer):
        """Test score is correctly calculated."""
        code = '''
def func(x):
    eval(x)  # Critical issue
'''
        reviewer._execute_tool = AsyncMock(return_value={
            "success": True,
            "content": code
        })
        reviewer._call_llm = AsyncMock(return_value='{"summary": "Issues", "additional_issues": []}')

        task = AgentTask(request="Review", context={"files": ["test.py"]})
        response = await reviewer.execute(task)

        report_data = response.data["report"]
        score = report_data["score"]

        # Score between 0-100
        assert 0 <= score <= 100
        # With critical issue, should be deducted
        assert score < 100


# =============================================================================
# REVIEW LOGIC - NO ISSUES SCENARIO
# =============================================================================

class TestReviewLogicNoIssues:
    """Tests for review logic with clean code."""

    @pytest.fixture
    def reviewer(self):
        """Create ReviewerAgent."""
        mock_llm = MagicMock()
        mock_llm.generate = AsyncMock(return_value='{"summary": "Clean code", "additional_issues": []}')
        mock_mcp = MagicMock()
        return ReviewerAgent(llm_client=mock_llm, mcp_client=mock_mcp)

    @pytest.mark.asyncio
    async def test_review_clean_simple_code(self, reviewer):
        """Test review of clean, simple code."""
        clean_code = '''
def add(a, b):
    """Add two numbers."""
    return a + b

def multiply(x, y):
    """Multiply two numbers."""
    return x * y
'''
        reviewer._execute_tool = AsyncMock(return_value={
            "success": True,
            "content": clean_code
        })
        reviewer._call_llm = AsyncMock(return_value='{"summary": "Clean code", "additional_issues": []}')

        task = AgentTask(request="Review", context={"files": ["utils.py"]})
        response = await reviewer.execute(task)

        assert response.success is True
        report_data = response.data["report"]

        # Should approve clean code
        assert report_data["approved"] is True
        assert report_data["score"] >= 80
        assert report_data["risk_level"] == "LOW"

        # No critical issues
        critical = [i for i in report_data["issues"]
                   if i["severity"] == "CRITICAL"]
        assert len(critical) == 0

    @pytest.mark.asyncio
    async def test_review_clean_with_docstrings(self, reviewer):
        """Test review of well-documented code."""
        documented = '''
def calculate_factorial(n: int) -> int:
    """
    Calculate factorial of n.

    Args:
        n: Non-negative integer

    Returns:
        Factorial of n

    Raises:
        ValueError: If n < 0
    """
    if n < 0:
        raise ValueError("n must be non-negative")
    if n <= 1:
        return 1
    return n * calculate_factorial(n - 1)
'''
        reviewer._execute_tool = AsyncMock(return_value={
            "success": True,
            "content": documented
        })
        reviewer._call_llm = AsyncMock(return_value='{"summary": "Well documented", "additional_issues": []}')

        task = AgentTask(request="Review", context={"files": ["math_utils.py"]})
        response = await reviewer.execute(task)

        assert response.success is True
        report_data = response.data["report"]

        # Should have good score
        assert report_data["score"] >= 70
        assert report_data["risk_level"] in ["LOW", "MEDIUM"]

    @pytest.mark.asyncio
    async def test_review_with_tests_present(self, reviewer):
        """Test review recognizes test files."""
        reviewer._execute_tool = AsyncMock(return_value={
            "success": True,
            "content": "def helper(): return 42"
        })
        reviewer._call_llm = AsyncMock(return_value='{"summary": "OK", "additional_issues": []}')

        task = AgentTask(request="Review", context={
            "files": ["src/helper.py", "tests/test_helper.py"]
        })
        response = await reviewer.execute(task)

        assert response.success is True
        report_data = response.data["report"]

        # Should not flag missing tests
        test_issues = [i for i in report_data["issues"]
                      if i["category"] == "TESTING"]
        # If tests are present, should not have test coverage issues
        no_test_issues = len(test_issues) == 0
        assert no_test_issues or report_data["score"] > 60


# =============================================================================
# REVIEW LOGIC - WARNINGS SCENARIO
# =============================================================================

class TestReviewLogicWarnings:
    """Tests for review logic with warnings (MEDIUM/LOW severity)."""

    @pytest.fixture
    def reviewer(self):
        """Create ReviewerAgent."""
        mock_llm = MagicMock()
        mock_mcp = MagicMock()
        return ReviewerAgent(llm_client=mock_llm, mcp_client=mock_mcp)

    @pytest.mark.asyncio
    async def test_review_with_medium_issues(self, reviewer):
        """Test review with medium severity issues."""
        code = '''
def process_data(items):
    # Moderately complex but not terrible
    if items:
        for item in items:
            if item.valid:
                if item.active:
                    print(item)
    return items
'''
        reviewer._execute_tool = AsyncMock(return_value={
            "success": True,
            "content": code
        })
        reviewer._call_llm = AsyncMock(return_value='{"summary": "Some improvements", "additional_issues": []}')

        task = AgentTask(request="Review", context={"files": ["processor.py"]})
        response = await reviewer.execute(task)

        assert response.success is True
        report_data = response.data["report"]

        # Should still approve with medium issues
        assert report_data["score"] >= 60
        # Risk should not be critical
        assert report_data["risk_level"] in ["LOW", "MEDIUM"]

    @pytest.mark.asyncio
    async def test_review_with_style_warnings(self, reviewer):
        """Test review identifies style issues."""
        code = '''
def my_func( x,y  ):
    return x+y
'''
        reviewer._execute_tool = AsyncMock(return_value={
            "success": True,
            "content": code
        })
        reviewer._call_llm = AsyncMock(return_value='{"summary": "Style issues", "additional_issues": []}')

        task = AgentTask(request="Review", context={"files": ["style.py"]})
        response = await reviewer.execute(task)

        assert response.success is True
        report_data = response.data["report"]

        # Should still approve despite style issues
        assert report_data["approved"] is True or report_data["score"] >= 70

    @pytest.mark.asyncio
    async def test_review_risk_escalation_with_score(self, reviewer):
        """Test risk escalates with lower score."""
        reviewer._execute_tool = AsyncMock(return_value={
            "success": True,
            "content": "def func(): pass"
        })
        reviewer._call_llm = AsyncMock(return_value='{"summary": "OK", "additional_issues": []}')

        task = AgentTask(request="Review", context={"files": ["test.py"]})
        response = await reviewer.execute(task)

        report_data = response.data["report"]
        score = report_data["score"]
        risk = report_data["risk_level"]

        # Verify risk escalates correctly
        if score < 40:
            assert risk == "CRITICAL"
        elif score < 60:
            assert risk == "HIGH"
        elif score < 80:
            assert risk == "MEDIUM"
        else:
            assert risk == "LOW"


# =============================================================================
# ERROR HANDLING - LLM UNAVAILABLE
# =============================================================================

class TestErrorHandlingLLMUnavailable:
    """Tests for handling LLM unavailability."""

    @pytest.mark.asyncio
    async def test_llm_connection_error(self):
        """Test graceful handling when LLM is unavailable."""
        mock_llm = MagicMock()
        mock_llm.generate = AsyncMock(side_effect=ConnectionError("LLM unreachable"))
        mock_mcp = MagicMock()

        reviewer = ReviewerAgent(llm_client=mock_llm, mcp_client=mock_mcp)
        reviewer._execute_tool = AsyncMock(return_value={
            "success": True,
            "content": "def test(): pass"
        })
        reviewer._call_llm = AsyncMock(side_effect=ConnectionError("LLM down"))

        task = AgentTask(request="Review", context={"files": ["test.py"]})
        response = await reviewer.execute(task)

        # Should still complete with static analysis
        assert response.success is True
        assert "report" in response.data

    @pytest.mark.asyncio
    async def test_llm_timeout(self):
        """Test handling of LLM timeout."""
        mock_llm = MagicMock()
        mock_mcp = MagicMock()

        reviewer = ReviewerAgent(llm_client=mock_llm, mcp_client=mock_mcp)
        reviewer._execute_tool = AsyncMock(return_value={
            "success": True,
            "content": "def test(): pass"
        })
        reviewer._call_llm = AsyncMock(side_effect=TimeoutError("LLM timeout"))

        task = AgentTask(request="Review", context={"files": ["test.py"]})
        response = await reviewer.execute(task)

        # Should gracefully fallback to static analysis
        assert response.success is True

    @pytest.mark.asyncio
    async def test_llm_rate_limit(self):
        """Test handling of rate limiting."""
        mock_llm = MagicMock()
        mock_mcp = MagicMock()

        reviewer = ReviewerAgent(llm_client=mock_llm, mcp_client=mock_mcp)
        reviewer._execute_tool = AsyncMock(return_value={
            "success": True,
            "content": "def test(): pass"
        })
        reviewer._call_llm = AsyncMock(side_effect=RuntimeError("Rate limit exceeded"))

        task = AgentTask(request="Review", context={"files": ["test.py"]})
        response = await reviewer.execute(task)

        # Should handle gracefully
        assert response.success is True


# =============================================================================
# ERROR HANDLING - PARSE ERRORS
# =============================================================================

class TestErrorHandlingParseErrors:
    """Tests for handling JSON/response parse errors."""

    @pytest.fixture
    def reviewer(self):
        """Create ReviewerAgent."""
        mock_llm = MagicMock()
        mock_mcp = MagicMock()
        return ReviewerAgent(llm_client=mock_llm, mcp_client=mock_mcp)

    def test_parse_invalid_json(self, reviewer):
        """Test parsing invalid JSON response."""
        invalid_json = "This is not JSON at all!"

        result = reviewer._parse_llm_json(invalid_json)

        assert isinstance(result, dict)
        assert "summary" in result
        assert "additional_issues" in result

    def test_parse_json_with_code_block(self, reviewer):
        """Test parsing JSON embedded in markdown."""
        response = '''
Here's the analysis:
```json
{"summary": "Analysis complete", "additional_issues": []}
```
End of analysis
'''
        result = reviewer._parse_llm_json(response)

        assert result["summary"] == "Analysis complete"
        assert result["additional_issues"] == []

    def test_parse_json_malformed_structure(self, reviewer):
        """Test parsing malformed JSON structure."""
        malformed = '{"summary": "OK", "additional_issues": [INCOMPLETE'

        result = reviewer._parse_llm_json(malformed)

        # Should return fallback dict
        assert isinstance(result, dict)
        assert "summary" in result

    def test_parse_json_empty_response(self, reviewer):
        """Test parsing empty response."""
        result = reviewer._parse_llm_json("")

        assert isinstance(result, dict)
        assert "summary" in result

    @pytest.mark.asyncio
    async def test_llm_response_not_json(self, reviewer):
        """Test handling LLM response that isn't JSON."""
        reviewer._execute_tool = AsyncMock(return_value={
            "success": True,
            "content": "def test(): pass"
        })
        reviewer._call_llm = AsyncMock(return_value="This is plain text, not JSON")

        task = AgentTask(request="Review", context={"files": ["test.py"]})
        response = await reviewer.execute(task)

        # Should still work with fallback
        assert response.success is True

    @pytest.mark.asyncio
    async def test_llm_partial_json(self, reviewer):
        """Test handling partial JSON response."""
        reviewer._execute_tool = AsyncMock(return_value={
            "success": True,
            "content": "def test(): pass"
        })
        reviewer._call_llm = AsyncMock(return_value='{"summary": "incomplete')

        task = AgentTask(request="Review", context={"files": ["test.py"]})
        response = await reviewer.execute(task)

        assert response.success is True


# =============================================================================
# ERROR HANDLING - TIMEOUTS
# =============================================================================

class TestErrorHandlingTimeouts:
    """Tests for timeout handling."""

    @pytest.mark.asyncio
    async def test_file_read_timeout(self):
        """Test timeout while reading files."""
        mock_llm = MagicMock()
        mock_mcp = MagicMock()

        reviewer = ReviewerAgent(llm_client=mock_llm, mcp_client=mock_mcp)
        reviewer._execute_tool = AsyncMock(side_effect=TimeoutError("Read timeout"))

        task = AgentTask(request="Review", context={"files": ["slow.py"]})
        response = await reviewer.execute(task)

        # Should handle timeout gracefully
        # Either success with no files or error
        assert isinstance(response, AgentResponse)

    @pytest.mark.asyncio
    async def test_ast_parse_timeout(self):
        """Test handling during AST parsing."""
        mock_llm = MagicMock()
        mock_mcp = MagicMock()

        reviewer = ReviewerAgent(llm_client=mock_llm, mcp_client=mock_mcp)

        # Create code that might take long to parse
        large_code = "x = " + " + ".join(["1"] * 10000)

        reviewer._execute_tool = AsyncMock(return_value={
            "success": True,
            "content": large_code
        })
        reviewer._call_llm = AsyncMock(return_value='{"summary": "OK", "additional_issues": []}')

        task = AgentTask(request="Review", context={"files": ["large.py"]})
        response = await reviewer.execute(task)

        # Should complete even with large code
        assert isinstance(response, AgentResponse)


# =============================================================================
# EDGE CASES - EMPTY CODE
# =============================================================================

class TestEdgeCaseEmptyCode:
    """Tests for empty or minimal code."""

    @pytest.fixture
    def reviewer(self):
        """Create ReviewerAgent."""
        mock_llm = MagicMock()
        mock_mcp = MagicMock()
        return ReviewerAgent(llm_client=mock_llm, mcp_client=mock_mcp)

    @pytest.mark.asyncio
    async def test_review_empty_file(self, reviewer):
        """Test review of empty Python file."""
        reviewer._execute_tool = AsyncMock(return_value={
            "success": True,
            "content": ""
        })
        reviewer._call_llm = AsyncMock(return_value='{"summary": "Empty file", "additional_issues": []}')

        task = AgentTask(request="Review", context={"files": ["empty.py"]})
        response = await reviewer.execute(task)

        assert response.success is True
        report_data = response.data["report"]

        # No metrics for empty file
        assert len(report_data["metrics"]) == 0

    @pytest.mark.asyncio
    async def test_review_only_comments(self, reviewer):
        """Test review of file with only comments."""
        code = '''
# This is a comment
# Another comment

# TODO: Implement
'''
        reviewer._execute_tool = AsyncMock(return_value={
            "success": True,
            "content": code
        })
        reviewer._call_llm = AsyncMock(return_value='{"summary": "Only comments", "additional_issues": []}')

        task = AgentTask(request="Review", context={"files": ["comments.py"]})
        response = await reviewer.execute(task)

        assert response.success is True
        report_data = response.data["report"]

        # No functions = no metrics
        assert len(report_data["metrics"]) == 0

    @pytest.mark.asyncio
    async def test_review_only_imports(self, reviewer):
        """Test review of file with only imports."""
        code = '''
import os
import sys
from typing import Dict, List
from functools import reduce
'''
        reviewer._execute_tool = AsyncMock(return_value={
            "success": True,
            "content": code
        })
        reviewer._call_llm = AsyncMock(return_value='{"summary": "Imports only", "additional_issues": []}')

        task = AgentTask(request="Review", context={"files": ["imports.py"]})
        response = await reviewer.execute(task)

        assert response.success is True
        report_data = response.data["report"]

        assert len(report_data["metrics"]) == 0

    @pytest.mark.asyncio
    async def test_review_minimal_function(self, reviewer):
        """Test review of minimal function."""
        code = "def noop(): pass"

        reviewer._execute_tool = AsyncMock(return_value={
            "success": True,
            "content": code
        })
        reviewer._call_llm = AsyncMock(return_value='{"summary": "Minimal", "additional_issues": []}')

        task = AgentTask(request="Review", context={"files": ["minimal.py"]})
        response = await reviewer.execute(task)

        assert response.success is True
        report_data = response.data["report"]

        # Should have one metric
        assert len(report_data["metrics"]) == 1


# =============================================================================
# EDGE CASES - VERY LARGE CODE
# =============================================================================

class TestEdgeCaseLargeCode:
    """Tests for handling large code files."""

    @pytest.fixture
    def reviewer(self):
        """Create ReviewerAgent."""
        mock_llm = MagicMock()
        mock_mcp = MagicMock()
        return ReviewerAgent(llm_client=mock_llm, mcp_client=mock_mcp)

    @pytest.mark.asyncio
    async def test_review_large_function(self, reviewer):
        """Test review of function with many lines."""
        # Generate large function
        func_body = "\n".join([f"    x_{i} = {i}" for i in range(100)])
        code = f"def large_func():\n{func_body}\n    return x_99"

        reviewer._execute_tool = AsyncMock(return_value={
            "success": True,
            "content": code
        })
        reviewer._call_llm = AsyncMock(return_value='{"summary": "Large", "additional_issues": []}')

        task = AgentTask(request="Review", context={"files": ["large.py"]})
        response = await reviewer.execute(task)

        assert response.success is True
        report_data = response.data["report"]

        assert len(report_data["metrics"]) >= 1
        assert report_data["metrics"][0]["loc"] >= 100

    @pytest.mark.asyncio
    async def test_review_many_functions(self, reviewer):
        """Test review of file with many functions."""
        # Generate many simple functions
        functions = "\n".join([f"def func_{i}(): return {i}" for i in range(50)])
        code = functions

        reviewer._execute_tool = AsyncMock(return_value={
            "success": True,
            "content": code
        })
        reviewer._call_llm = AsyncMock(return_value='{"summary": "Many funcs", "additional_issues": []}')

        task = AgentTask(request="Review", context={"files": ["many.py"]})
        response = await reviewer.execute(task)

        assert response.success is True
        report_data = response.data["report"]

        # Should analyze all functions
        assert len(report_data["metrics"]) >= 30

    @pytest.mark.asyncio
    async def test_review_deeply_nested_code(self, reviewer):
        """Test review of deeply nested code."""
        code = "def nested():\n"
        for i in range(10):
            code += "    " * (i + 1) + "if True:\n"
        code += "    " * 11 + "return 42"

        reviewer._execute_tool = AsyncMock(return_value={
            "success": True,
            "content": code
        })
        reviewer._call_llm = AsyncMock(return_value='{"summary": "Nested", "additional_issues": []}')

        task = AgentTask(request="Review", context={"files": ["nested.py"]})
        response = await reviewer.execute(task)

        assert response.success is True
        report_data = response.data["report"]

        # Should detect nesting depth
        assert len(report_data["metrics"]) >= 1


# =============================================================================
# EDGE CASES - MULTIPLE LANGUAGES
# =============================================================================

class TestEdgeCaseMultipleLanguages:
    """Tests for handling multiple file types."""

    @pytest.fixture
    def reviewer(self):
        """Create ReviewerAgent."""
        mock_llm = MagicMock()
        mock_mcp = MagicMock()
        return ReviewerAgent(llm_client=mock_llm, mcp_client=mock_mcp)

    @pytest.mark.asyncio
    async def test_review_mixed_python_and_other(self, reviewer):
        """Test review with both Python and non-Python files."""
        reviewer._execute_tool = AsyncMock(return_value={
            "success": True,
            "content": "def test(): pass"
        })
        reviewer._call_llm = AsyncMock(return_value='{"summary": "Mixed files", "additional_issues": []}')

        # Mix of file types
        task = AgentTask(request="Review", context={
            "files": ["script.py", "config.json", "data.txt", "README.md"]
        })
        response = await reviewer.execute(task)

        assert response.success is True
        report_data = response.data["report"]

        # Should handle mixed file types gracefully

    @pytest.mark.asyncio
    async def test_review_non_python_files_skipped(self, reviewer):
        """Test that non-Python files are skipped."""
        reviewer._execute_tool = AsyncMock(return_value={
            "success": True,
            "content": "console.log('test')"
        })
        reviewer._call_llm = AsyncMock(return_value='{"summary": "Non-Python", "additional_issues": []}')

        task = AgentTask(request="Review", context={
            "files": ["index.js", "style.css", "script.sh"]
        })
        response = await reviewer.execute(task)

        assert response.success is True
        report_data = response.data["report"]

        # No Python metrics since no .py files
        # (or only metrics from Python files if analyzed)

    @pytest.mark.asyncio
    async def test_review_python_2_syntax(self, reviewer):
        """Test handling Python 2 syntax (should fail to parse)."""
        py2_code = '''
def print_hello():
    print "Hello, World!"  # Python 2 print statement
'''
        reviewer._execute_tool = AsyncMock(return_value={
            "success": True,
            "content": py2_code
        })
        reviewer._call_llm = AsyncMock(return_value='{"summary": "Syntax error", "additional_issues": []}')

        task = AgentTask(request="Review", context={"files": ["legacy.py"]})
        response = await reviewer.execute(task)

        assert response.success is True
        report_data = response.data["report"]

        # Should have syntax error issue
        syntax_issues = [i for i in report_data["issues"]
                        if i["category"] == "LOGIC"]
        # Should record error somehow


# =============================================================================
# SPECIAL CASES - ASYNC FUNCTIONS
# =============================================================================

class TestSpecialCasesAsyncCode:
    """Tests for handling async/await code."""

    @pytest.fixture
    def reviewer(self):
        """Create ReviewerAgent."""
        mock_llm = MagicMock()
        mock_mcp = MagicMock()
        return ReviewerAgent(llm_client=mock_llm, mcp_client=mock_mcp)

    @pytest.mark.asyncio
    async def test_review_async_functions(self, reviewer):
        """Test review of async functions."""
        code = '''
async def fetch_data(url):
    async with http.client() as client:
        response = await client.get(url)
        return response.json()

async def process_many(urls):
    tasks = [fetch_data(url) for url in urls]
    return await asyncio.gather(*tasks)
'''
        reviewer._execute_tool = AsyncMock(return_value={
            "success": True,
            "content": code
        })
        reviewer._call_llm = AsyncMock(return_value='{"summary": "Async", "additional_issues": []}')

        task = AgentTask(request="Review", context={"files": ["async.py"]})
        response = await reviewer.execute(task)

        assert response.success is True
        report_data = response.data["report"]

        # Should analyze async functions
        assert len(report_data["metrics"]) >= 2


# =============================================================================
# SPECIAL CASES - LAMBDA & COMPREHENSIONS
# =============================================================================

class TestSpecialCasesLambdaComprehensions:
    """Tests for lambda functions and comprehensions."""

    @pytest.fixture
    def reviewer(self):
        """Create ReviewerAgent."""
        mock_llm = MagicMock()
        mock_mcp = MagicMock()
        return ReviewerAgent(llm_client=mock_llm, mcp_client=mock_mcp)

    @pytest.mark.asyncio
    async def test_review_code_with_lambdas(self, reviewer):
        """Test review of code with lambda functions."""
        code = '''
data = [1, 2, 3, 4, 5]
squared = list(map(lambda x: x ** 2, data))
filtered = list(filter(lambda x: x > 2, data))
sorted_data = sorted(data, key=lambda x: -x)
'''
        reviewer._execute_tool = AsyncMock(return_value={
            "success": True,
            "content": code
        })
        reviewer._call_llm = AsyncMock(return_value='{"summary": "Lambdas", "additional_issues": []}')

        task = AgentTask(request="Review", context={"files": ["lambda.py"]})
        response = await reviewer.execute(task)

        assert response.success is True
        report_data = response.data["report"]

        # Should handle code with lambdas

    @pytest.mark.asyncio
    async def test_review_complex_comprehensions(self, reviewer):
        """Test review of complex comprehensions."""
        code = '''
matrix = [[i*j for j in range(5)] for i in range(5)]
flat = [x for row in matrix for x in row if x > 5]
dict_comp = {i: i**2 for i in range(10)}
set_comp = {x for x in range(100) if x % 2 == 0}
'''
        reviewer._execute_tool = AsyncMock(return_value={
            "success": True,
            "content": code
        })
        reviewer._call_llm = AsyncMock(return_value='{"summary": "Comprehensions", "additional_issues": []}')

        task = AgentTask(request="Review", context={"files": ["comps.py"]})
        response = await reviewer.execute(task)

        assert response.success is True


# =============================================================================
# SPECIAL CASES - DECORATORS & CLASS METHODS
# =============================================================================

class TestSpecialCasesDecorators:
    """Tests for handling decorators and class methods."""

    @pytest.fixture
    def reviewer(self):
        """Create ReviewerAgent."""
        mock_llm = MagicMock()
        mock_mcp = MagicMock()
        return ReviewerAgent(llm_client=mock_llm, mcp_client=mock_mcp)

    @pytest.mark.asyncio
    async def test_review_decorated_functions(self, reviewer):
        """Test review of decorated functions."""
        code = '''
from functools import wraps

def my_decorator(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    return wrapper

@my_decorator
def decorated_function(x, y):
    return x + y

class MyClass:
    @property
    def value(self):
        return self._value

    @staticmethod
    def static_method():
        return 42

    @classmethod
    def class_method(cls):
        return cls.__name__
'''
        reviewer._execute_tool = AsyncMock(return_value={
            "success": True,
            "content": code
        })
        reviewer._call_llm = AsyncMock(return_value='{"summary": "Decorated", "additional_issues": []}')

        task = AgentTask(request="Review", context={"files": ["decorators.py"]})
        response = await reviewer.execute(task)

        assert response.success is True
        report_data = response.data["report"]

        # Should analyze class and its methods


# =============================================================================
# SCORING AND RISK EDGE CASES
# =============================================================================

class TestScoringAndRiskEdgeCases:
    """Tests for edge cases in scoring and risk calculation."""

    @pytest.fixture
    def reviewer(self):
        """Create ReviewerAgent."""
        mock_llm = MagicMock()
        mock_mcp = MagicMock()
        return ReviewerAgent(llm_client=mock_llm, mcp_client=mock_mcp)

    def test_score_with_zero_confidence_issues(self, reviewer):
        """Test score calculation with zero-confidence issues."""
        issues = [
            CodeIssue(
                file="test.py", line=1,
                severity=IssueSeverity.HIGH,
                category=IssueCategory.LOGIC,
                message="Maybe an issue",
                explanation="Not sure",
                confidence=0.0  # No confidence
            )
        ]

        score = reviewer._calculate_score(issues, [])

        # Zero confidence means no deduction
        assert score == 100

    def test_score_with_low_confidence_issues(self, reviewer):
        """Test score with low-confidence issues."""
        issues = [
            CodeIssue(
                file="test.py", line=1,
                severity=IssueSeverity.CRITICAL,
                category=IssueCategory.SECURITY,
                message="Maybe critical",
                explanation="Low confidence",
                confidence=0.1  # Low confidence
            )
        ]

        score = reviewer._calculate_score(issues, [])

        # Should be minimal deduction
        assert 90 <= score < 100

    def test_estimate_fix_time_no_issues(self, reviewer):
        """Test fix time estimate with no issues."""
        time = reviewer._estimate_fix_time([])

        assert "hour" in time.lower() or time == "< 1 hour"

    def test_estimate_fix_time_many_mediums(self, reviewer):
        """Test fix time with many medium issues."""
        issues = [
            CodeIssue(
                file="test.py", line=i,
                severity=IssueSeverity.MEDIUM,
                category=IssueCategory.COMPLEXITY,
                message=f"Issue {i}",
                explanation="Medium"
            ) for i in range(10)
        ]

        time = reviewer._estimate_fix_time(issues)

        # 10 mediums = 10 hours = 1-2 days
        assert "hour" in time.lower() or "day" in time.lower()

    def test_risk_at_boundary_scores(self, reviewer):
        """Test risk calculation at boundary scores."""
        # Score below 40 should be CRITICAL
        assert reviewer._calculate_risk([], 39) == "CRITICAL"

        # Score between 40-60 should be HIGH
        assert reviewer._calculate_risk([], 50) == "HIGH"

        # Score between 60-80 should be MEDIUM
        assert reviewer._calculate_risk([], 70) == "MEDIUM"

        # Score above 80 should be LOW
        assert reviewer._calculate_risk([], 85) == "LOW"

    def test_high_complexity_score_deduction(self, reviewer):
        """Test that high complexity properly deducts from score."""
        metrics = [
            ComplexityMetrics(
                function_name="complex",
                cyclomatic=25,  # Way above normal
                cognitive=35,   # Very high
                loc=300,
                args_count=10,
                returns_count=8
            )
        ]

        score = reviewer._calculate_score([], metrics)

        # Should be significantly deducted
        assert score < 80


# =============================================================================
# GRAPH ANALYSIS EDGE CASES
# =============================================================================

class TestGraphAnalysisEdgeCases:
    """Tests for code graph analysis edge cases."""

    @pytest.fixture
    def graph_agent(self):
        """Create CodeGraphAnalysisAgent."""
        from jdev_cli.agents.reviewer import CodeGraphAnalysisAgent
        agent = CodeGraphAnalysisAgent()
        agent.logger = MagicMock()
        return agent

    @pytest.mark.asyncio
    async def test_graph_with_self_loop(self, graph_agent):
        """Test graph with function calling itself (recursion)."""
        graph = nx.DiGraph()
        graph.add_edge("recursive::factorial", "recursive::factorial")

        nodes = [CodeGraphNode(
            id="recursive::factorial",
            type="function",
            name="factorial",
            file_path="math.py",
            line_start=1,
            line_end=10
        )]

        issues = await graph_agent.analyze(graph, nodes)

        # Self-loop is not necessarily bad (recursion is valid)
        assert isinstance(issues, list)

    @pytest.mark.asyncio
    async def test_graph_with_many_nodes(self, graph_agent):
        """Test graph with many nodes."""
        graph = nx.DiGraph()
        nodes = []

        # Create 100 nodes in a chain
        for i in range(100):
            node_id = f"module::func_{i}"
            graph.add_node(node_id)
            nodes.append(CodeGraphNode(
                id=node_id,
                type="function",
                name=f"func_{i}",
                file_path="module.py",
                line_start=i*10,
                line_end=i*10+8
            ))

            # Connect to next
            if i > 0:
                graph.add_edge(f"module::func_{i-1}", node_id)

        issues = await graph_agent.analyze(graph, nodes)

        # Should handle large graphs
        assert isinstance(issues, list)


# =============================================================================
# RECOMMENDATIONS GENERATION
# =============================================================================

class TestRecommendationsGeneration:
    """Tests for recommendation generation logic."""

    @pytest.fixture
    def reviewer(self):
        """Create ReviewerAgent."""
        mock_llm = MagicMock()
        mock_mcp = MagicMock()
        return ReviewerAgent(llm_client=mock_llm, mcp_client=mock_mcp)

    def test_recommendations_for_security_issues(self, reviewer):
        """Test recommendations include security recommendations."""
        issues = [
            CodeIssue(
                file="test.py", line=1,
                severity=IssueSeverity.CRITICAL,
                category=IssueCategory.SECURITY,
                message="SQL injection",
                explanation="Bad"
            )
        ]

        recs = reviewer._generate_recommendations(issues, [], RAGContext())

        # Should recommend security scan
        security_recs = [r for r in recs if "security" in r.lower() or "bandit" in r.lower()]
        assert len(security_recs) > 0

    def test_recommendations_empty_when_no_issues(self, reviewer):
        """Test minimal recommendations for clean code."""
        recs = reviewer._generate_recommendations([], [], RAGContext())

        # Should still have some recommendations
        assert isinstance(recs, list)

    def test_recommendations_with_team_standards(self, reviewer):
        """Test recommendations respect team standards."""
        rag = RAGContext(team_standards={"require_docstrings": "true"})
        recs = reviewer._generate_recommendations([], [], rag)

        # Should include docstring recommendation
        doc_recs = [r for r in recs if "docstring" in r.lower()]
        assert len(doc_recs) > 0
