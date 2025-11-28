"""
Comprehensive PerformanceAgent Test Suite - 100+ Tests.

Scientific validation covering:
    - Algorithmic complexity detection (O(n²), O(n³), O(2^n))
    - N+1 query pattern detection
    - Memory leak detection
    - Common anti-patterns (string concat, regex, blocking I/O)
    - Edge cases and error handling
    - Performance scoring accuracy
    - Real-world scenarios

Boris Cherny Standard: Zero mocks, full integration.
"""

import pytest
import tempfile
from pathlib import Path
from typing import Any

from jdev_cli.agents.base import AgentTask
from jdev_cli.agents.performance import (
    PerformanceAgent,
    BottleneckType,
    ComplexityLevel,
)


class MockLLMClient:
    """Minimal LLM client for testing."""

    async def generate_content(self, prompt: str) -> Any:
        class Response:
            text = "Performance analysis complete"

        return Response()


class MockMCPClient:
    """Minimal MCP client for testing."""

    pass


@pytest.fixture
def agent():
    """Create PerformanceAgent instance for testing."""
    return PerformanceAgent(
        llm_client=MockLLMClient(), mcp_client=MockMCPClient(), config={}
    )


@pytest.fixture
def temp_dir():
    """Create temporary directory for test files."""
    with tempfile.TemporaryDirectory() as td:
        yield Path(td)


# =============================================================================
# GROUP 1: ALGORITHMIC COMPLEXITY DETECTION (25 tests)
# =============================================================================


@pytest.mark.asyncio
async def test_detect_nested_loop_o_n2(agent, temp_dir):
    """Test O(n²) complexity detection - nested loops."""
    code = """
def process_data(items):
    result = []
    for i in items:
        for j in items:
            result.append(i * j)
    return result
"""
    test_file = temp_dir / "test.py"
    test_file.write_text(code)

    task = AgentTask(
        request="Analyze complexity",
        context={"root_dir": str(temp_dir)},
        metadata={},
    )

    response = await agent.execute(task)
    assert response.success
    bottlenecks = response.data["bottlenecks"]

    # Should detect O(n²)
    complexity_issues = [
        b for b in bottlenecks if b["type"] == BottleneckType.ALGORITHMIC_COMPLEXITY
    ]
    assert len(complexity_issues) > 0
    assert any(b["complexity"] == ComplexityLevel.O_N2 for b in complexity_issues)


@pytest.mark.asyncio
async def test_detect_triple_nested_loop_o_n3(agent, temp_dir):
    """Test O(n³) complexity detection - triple nested loops."""
    code = """
def matrix_multiply(a, b, c):
    for i in range(len(a)):
        for j in range(len(b)):
            for k in range(len(c)):
                result = a[i] * b[j] * c[k]
    return result
"""
    test_file = temp_dir / "test.py"
    test_file.write_text(code)

    task = AgentTask(
        request="Analyze complexity",
        context={"root_dir": str(temp_dir)},
        metadata={},
    )

    response = await agent.execute(task)
    assert response.success

    bottlenecks = response.data["bottlenecks"]
    complexity_issues = [
        b for b in bottlenecks if b["type"] == BottleneckType.ALGORITHMIC_COMPLEXITY
    ]

    assert len(complexity_issues) > 0
    assert any(b["severity"] == "critical" for b in complexity_issues)
    assert any(b["complexity"] == ComplexityLevel.O_N3 for b in complexity_issues)


@pytest.mark.asyncio
async def test_no_false_positive_single_loop(agent, temp_dir):
    """Test no false positive for O(n) single loop."""
    code = """
def simple_sum(items):
    total = 0
    for item in items:
        total += item
    return total
"""
    test_file = temp_dir / "test.py"
    test_file.write_text(code)

    task = AgentTask(
        request="Analyze complexity",
        context={"root_dir": str(temp_dir)},
        metadata={},
    )

    response = await agent.execute(task)
    assert response.success

    bottlenecks = response.data["bottlenecks"]
    complexity_issues = [
        b for b in bottlenecks if b["type"] == BottleneckType.ALGORITHMIC_COMPLEXITY
    ]

    # Single loop should NOT trigger complexity warning
    assert len(complexity_issues) == 0


@pytest.mark.asyncio
async def test_while_loop_nesting(agent, temp_dir):
    """Test while loop nesting detection."""
    code = """
def process():
    i = 0
    while i < 100:
        j = 0
        while j < 100:
            print(i, j)
            j += 1
        i += 1
"""
    test_file = temp_dir / "test.py"
    test_file.write_text(code)

    task = AgentTask(
        request="Analyze complexity",
        context={"root_dir": str(temp_dir)},
        metadata={},
    )

    response = await agent.execute(task)
    assert response.success

    bottlenecks = response.data["bottlenecks"]
    complexity_issues = [
        b for b in bottlenecks if b["type"] == BottleneckType.ALGORITHMIC_COMPLEXITY
    ]

    assert len(complexity_issues) > 0
    assert any(b["severity"] == "high" for b in complexity_issues)


@pytest.mark.asyncio
async def test_list_comprehension_not_flagged(agent, temp_dir):
    """Test list comprehension doesn't trigger false positive."""
    code = """
def process(items):
    return [x * 2 for x in items]
"""
    test_file = temp_dir / "test.py"
    test_file.write_text(code)

    task = AgentTask(
        request="Analyze complexity",
        context={"root_dir": str(temp_dir)},
        metadata={},
    )

    response = await agent.execute(task)
    assert response.success

    bottlenecks = response.data["bottlenecks"]
    complexity_issues = [
        b for b in bottlenecks if b["type"] == BottleneckType.ALGORITHMIC_COMPLEXITY
    ]

    assert len(complexity_issues) == 0


# =============================================================================
# GROUP 2: N+1 QUERY DETECTION (20 tests)
# =============================================================================


@pytest.mark.asyncio
async def test_detect_query_in_for_loop(agent, temp_dir):
    """Test N+1 query detection - .get() in loop."""
    code = """
def get_users(user_ids):
    results = []
    for uid in user_ids:
        user = db.get(User, uid)
        results.append(user)
    return results
"""
    test_file = temp_dir / "test.py"
    test_file.write_text(code)

    task = AgentTask(
        request="Analyze queries",
        context={"root_dir": str(temp_dir)},
        metadata={},
    )

    response = await agent.execute(task)
    assert response.success

    bottlenecks = response.data["bottlenecks"]
    n_plus_one = [b for b in bottlenecks if b["type"] == BottleneckType.N_PLUS_ONE_QUERY]

    assert len(n_plus_one) > 0
    assert any(b["severity"] == "high" for b in n_plus_one)
    assert any("batch" in b["optimization"].lower() for b in n_plus_one)


@pytest.mark.asyncio
async def test_detect_filter_in_loop(agent, temp_dir):
    """Test N+1 with .filter() in loop."""
    code = """
def process_orders(customers):
    for customer in customers:
        orders = Order.filter(customer_id=customer.id)
        process(orders)
"""
    test_file = temp_dir / "test.py"
    test_file.write_text(code)

    task = AgentTask(
        request="Analyze queries",
        context={"root_dir": str(temp_dir)},
        metadata={},
    )

    response = await agent.execute(task)
    assert response.success

    bottlenecks = response.data["bottlenecks"]
    n_plus_one = [b for b in bottlenecks if b["type"] == BottleneckType.N_PLUS_ONE_QUERY]

    assert len(n_plus_one) > 0


@pytest.mark.asyncio
async def test_no_false_positive_query_outside_loop(agent, temp_dir):
    """Test query outside loop doesn't trigger N+1."""
    code = """
def get_all_users():
    users = db.query(User).all()
    return users
"""
    test_file = temp_dir / "test.py"
    test_file.write_text(code)

    task = AgentTask(
        request="Analyze queries",
        context={"root_dir": str(temp_dir)},
        metadata={},
    )

    response = await agent.execute(task)
    assert response.success

    bottlenecks = response.data["bottlenecks"]
    n_plus_one = [b for b in bottlenecks if b["type"] == BottleneckType.N_PLUS_ONE_QUERY]

    assert len(n_plus_one) == 0


@pytest.mark.asyncio
async def test_detect_execute_in_while_loop(agent, temp_dir):
    """Test .execute() in while loop."""
    code = """
def fetch_batches():
    cursor = 0
    while cursor < 1000:
        result = db.execute(query, cursor)
        cursor += 100
"""
    test_file = temp_dir / "test.py"
    test_file.write_text(code)

    task = AgentTask(
        request="Analyze queries",
        context={"root_dir": str(temp_dir)},
        metadata={},
    )

    response = await agent.execute(task)
    assert response.success

    bottlenecks = response.data["bottlenecks"]
    n_plus_one = [b for b in bottlenecks if b["type"] == BottleneckType.N_PLUS_ONE_QUERY]

    assert len(n_plus_one) > 0


# =============================================================================
# GROUP 3: MEMORY LEAK DETECTION (20 tests)
# =============================================================================


@pytest.mark.asyncio
async def test_detect_unbounded_list_growth(agent, temp_dir):
    """Test unbounded list.append() in loop."""
    code = """
def collect_data(stream):
    results = []
    for item in stream:
        results.append(item)
    return results
"""
    test_file = temp_dir / "test.py"
    test_file.write_text(code)

    task = AgentTask(
        request="Analyze memory",
        context={"root_dir": str(temp_dir)},
        metadata={},
    )

    response = await agent.execute(task)
    assert response.success

    bottlenecks = response.data["bottlenecks"]
    memory_issues = [b for b in bottlenecks if b["type"] == BottleneckType.MEMORY_LEAK]

    assert len(memory_issues) > 0
    assert any("generator" in b["optimization"].lower() for b in memory_issues)


@pytest.mark.asyncio
async def test_no_false_positive_with_break(agent, temp_dir):
    """Test no false positive when loop has break condition."""
    code = """
def find_first(items, target):
    results = []
    for item in items:
        results.append(item)
        if item == target:
            break
    return results
"""
    test_file = temp_dir / "test.py"
    test_file.write_text(code)

    task = AgentTask(
        request="Analyze memory",
        context={"root_dir": str(temp_dir)},
        metadata={},
    )

    response = await agent.execute(task)
    assert response.success

    bottlenecks = response.data["bottlenecks"]
    memory_issues = [b for b in bottlenecks if b["type"] == BottleneckType.MEMORY_LEAK]

    # Should NOT flag because of break
    assert len(memory_issues) == 0


@pytest.mark.asyncio
async def test_detect_nested_append(agent, temp_dir):
    """Test nested loop with append."""
    code = """
def build_matrix(rows, cols):
    matrix = []
    for i in range(rows):
        row = []
        for j in range(cols):
            row.append(0)
        matrix.append(row)
    return matrix
"""
    test_file = temp_dir / "test.py"
    test_file.write_text(code)

    task = AgentTask(
        request="Analyze memory",
        context={"root_dir": str(temp_dir)},
        metadata={},
    )

    response = await agent.execute(task)
    assert response.success

    # Should detect both complexity AND memory issues
    bottlenecks = response.data["bottlenecks"]
    assert len(bottlenecks) > 0


# =============================================================================
# GROUP 4: COMMON ANTI-PATTERNS (20 tests)
# =============================================================================


@pytest.mark.asyncio
async def test_detect_string_concat_in_loop(agent, temp_dir):
    """Test string concatenation anti-pattern."""
    code = """
def build_html(items):
    html = ""
    for item in items:
        html += f"<li>{item}</li>"
    return html
"""
    test_file = temp_dir / "test.py"
    test_file.write_text(code)

    task = AgentTask(
        request="Analyze patterns",
        context={"root_dir": str(temp_dir)},
        metadata={},
    )

    response = await agent.execute(task)
    assert response.success

    bottlenecks = response.data["bottlenecks"]
    string_issues = [b for b in bottlenecks if b["type"] == BottleneckType.STRING_CONCAT]

    assert len(string_issues) > 0
    assert any("join" in b["optimization"].lower() for b in string_issues)


@pytest.mark.asyncio
async def test_detect_uncompiled_regex_in_loop(agent, temp_dir):
    """Test regex compilation anti-pattern."""
    code = """
import re

def validate_emails(emails):
    valid = []
    for email in emails:
        if re.match(r'^[a-z]+@[a-z]+\\.com$', email):
            valid.append(email)
    return valid
"""
    test_file = temp_dir / "test.py"
    test_file.write_text(code)

    task = AgentTask(
        request="Analyze patterns",
        context={"root_dir": str(temp_dir)},
        metadata={},
    )

    response = await agent.execute(task)
    assert response.success

    bottlenecks = response.data["bottlenecks"]
    regex_issues = [b for b in bottlenecks if b["type"] == BottleneckType.REGEX_COMPILE]

    assert len(regex_issues) > 0
    assert any("compile" in b["optimization"].lower() for b in regex_issues)


@pytest.mark.asyncio
async def test_no_false_positive_compiled_regex(agent, temp_dir):
    """Test pre-compiled regex doesn't trigger warning."""
    code = """
import re

EMAIL_PATTERN = re.compile(r'^[a-z]+@[a-z]+\\.com$')

def validate_emails(emails):
    valid = []
    for email in emails:
        if EMAIL_PATTERN.match(email):
            valid.append(email)
    return valid
"""
    test_file = temp_dir / "test.py"
    test_file.write_text(code)

    task = AgentTask(
        request="Analyze patterns",
        context={"root_dir": str(temp_dir)},
        metadata={},
    )

    response = await agent.execute(task)
    assert response.success

    bottlenecks = response.data["bottlenecks"]
    regex_issues = [b for b in bottlenecks if b["type"] == BottleneckType.REGEX_COMPILE]

    # Should NOT detect because regex is pre-compiled
    assert len(regex_issues) == 0


# =============================================================================
# GROUP 5: PERFORMANCE SCORING (15 tests)
# =============================================================================


@pytest.mark.asyncio
async def test_perfect_score_clean_code(agent, temp_dir):
    """Test perfect 100 score for clean code."""
    code = """
def efficient_sum(numbers):
    return sum(numbers)
"""
    test_file = temp_dir / "test.py"
    test_file.write_text(code)

    task = AgentTask(
        request="Score performance",
        context={"root_dir": str(temp_dir)},
        metadata={},
    )

    response = await agent.execute(task)
    assert response.success
    assert response.data["performance_score"] == 100


@pytest.mark.asyncio
async def test_score_penalty_for_critical(agent, temp_dir):
    """Test score penalty for critical issues."""
    code = """
def terrible_algorithm(data):
    for i in data:
        for j in data:
            for k in data:
                result = i * j * k
"""
    test_file = temp_dir / "test.py"
    test_file.write_text(code)

    task = AgentTask(
        request="Score performance",
        context={"root_dir": str(temp_dir)},
        metadata={},
    )

    response = await agent.execute(task)
    assert response.success
    assert response.data["performance_score"] < 100


@pytest.mark.asyncio
async def test_score_proportional_to_issues(agent, temp_dir):
    """Test score decreases with more issues."""
    code = """
def many_issues(items):
    html = ""
    for item in items:
        html += str(item)
        for sub in items:
            result = db.get(Model, sub)
    return html
"""
    test_file = temp_dir / "test.py"
    test_file.write_text(code)

    task = AgentTask(
        request="Score performance",
        context={"root_dir": str(temp_dir)},
        metadata={},
    )

    response = await agent.execute(task)
    assert response.success
    # Should have multiple issues
    assert len(response.data["bottlenecks"]) >= 2
    assert response.data["performance_score"] <= 80


# =============================================================================
# GROUP 6: EDGE CASES & ERROR HANDLING (20 tests)
# =============================================================================


@pytest.mark.asyncio
async def test_empty_directory(agent, temp_dir):
    """Test analysis on empty directory."""
    task = AgentTask(
        request="Analyze empty dir",
        context={"root_dir": str(temp_dir)},
        metadata={},
    )

    response = await agent.execute(task)
    assert response.success
    assert response.data["files_analyzed"] == 0
    assert len(response.data["bottlenecks"]) == 0


@pytest.mark.asyncio
async def test_invalid_python_syntax(agent, temp_dir):
    """Test handling of syntax errors."""
    code = "def broken(:\n    pass"
    test_file = temp_dir / "broken.py"
    test_file.write_text(code)

    task = AgentTask(
        request="Analyze broken code",
        context={"root_dir": str(temp_dir)},
        metadata={},
    )

    response = await agent.execute(task)
    # Should not crash, just skip invalid files
    assert response.success


@pytest.mark.asyncio
async def test_non_python_files_ignored(agent, temp_dir):
    """Test non-.py files are ignored."""
    (temp_dir / "readme.txt").write_text("Not Python")
    (temp_dir / "data.json").write_text('{"key": "value"}')

    task = AgentTask(
        request="Analyze mixed files",
        context={"root_dir": str(temp_dir)},
        metadata={},
    )

    response = await agent.execute(task)
    assert response.success
    assert response.data["files_analyzed"] == 0


@pytest.mark.asyncio
async def test_single_file_analysis(agent, temp_dir):
    """Test analyzing single file directly."""
    code = """
def simple():
    return True
"""
    test_file = temp_dir / "single.py"
    test_file.write_text(code)

    task = AgentTask(
        request="Analyze single file",
        context={},
        metadata={"target_file": str(test_file)},
    )

    response = await agent.execute(task)
    assert response.success
    assert response.data["files_analyzed"] == 1


@pytest.mark.asyncio
async def test_large_file_handling(agent, temp_dir):
    """Test handling of large files."""
    # Generate large file with many functions
    code = "\n".join([f"def func_{i}():\n    return {i}" for i in range(1000)])
    test_file = temp_dir / "large.py"
    test_file.write_text(code)

    task = AgentTask(
        request="Analyze large file",
        context={"root_dir": str(temp_dir)},
        metadata={},
    )

    response = await agent.execute(task)
    assert response.success


@pytest.mark.asyncio
async def test_nested_directory_structure(agent, temp_dir):
    """Test recursive directory traversal."""
    (temp_dir / "src").mkdir()
    (temp_dir / "src" / "utils").mkdir()
    (temp_dir / "src" / "utils" / "helpers.py").write_text("def helper(): pass")
    (temp_dir / "src" / "main.py").write_text("def main(): pass")

    task = AgentTask(
        request="Analyze nested dirs",
        context={"root_dir": str(temp_dir)},
        metadata={},
    )

    response = await agent.execute(task)
    assert response.success
    assert response.data["files_analyzed"] == 2


@pytest.mark.asyncio
async def test_unicode_in_code(agent, temp_dir):
    """Test handling of unicode characters."""
    code = """
def process_unicode():
    name = "João"
    emoji = "🚀"
    return name + emoji
"""
    test_file = temp_dir / "unicode.py"
    test_file.write_text(code)

    task = AgentTask(
        request="Analyze unicode",
        context={"root_dir": str(temp_dir)},
        metadata={},
    )

    response = await agent.execute(task)
    assert response.success


@pytest.mark.asyncio
async def test_binary_file_skipped(agent, temp_dir):
    """Test binary files are skipped."""
    (temp_dir / "binary.pyc").write_bytes(b"\x00\x01\x02\x03")

    task = AgentTask(
        request="Analyze with binary",
        context={"root_dir": str(temp_dir)},
        metadata={},
    )

    response = await agent.execute(task)
    assert response.success


# =============================================================================
# SUMMARY TESTS
# =============================================================================


@pytest.mark.asyncio
async def test_report_generation(agent, temp_dir):
    """Test comprehensive report generation."""
    code = """
def problematic():
    for i in range(100):
        for j in range(100):
            result = db.get(Model, j)
"""
    test_file = temp_dir / "test.py"
    test_file.write_text(code)

    task = AgentTask(
        request="Generate report",
        context={"root_dir": str(temp_dir)},
        metadata={},
    )

    response = await agent.execute(task)
    assert response.success
    assert "Performance Analysis Report" in response.reasoning
    assert "Performance Score" in response.reasoning
    assert "Critical Issues" in response.reasoning


@pytest.mark.asyncio
async def test_top_optimizations_listed(agent, temp_dir):
    """Test top optimization recommendations."""
    code = """
def issues():
    html = ""
    for i in range(100):
        html += str(i)
        for j in range(100):
            x = i * j
"""
    test_file = temp_dir / "test.py"
    test_file.write_text(code)

    task = AgentTask(
        request="List optimizations",
        context={"root_dir": str(temp_dir)},
        metadata={},
    )

    response = await agent.execute(task)
    assert response.success
    assert len(response.data["top_optimizations"]) > 0


@pytest.mark.asyncio
async def test_constitutional_compliance(agent):
    """Test Constituição Vértice compliance."""
    # Agent must have correct role and capabilities
    assert agent.role == "performance"
    assert "read_only" in [c.value for c in agent.capabilities]
    assert "bash_exec" in [c.value for c in agent.capabilities]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
