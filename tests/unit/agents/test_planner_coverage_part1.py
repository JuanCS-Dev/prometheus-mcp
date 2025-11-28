"""
Test coverage for PlannerAgent v5.0 - Part 1
Focuses on: DependencyAnalyzer.detect_cycles() + PlannerAgent._robust_json_parse()

Coverage Targets:
1. DependencyAnalyzer.detect_cycles() - Circular dependency detection
2. PlannerAgent._robust_json_parse() - Robust JSON parsing with fallbacks
"""

import json
import pytest
from unittest.mock import MagicMock

from jdev_cli.agents.planner import (
    PlannerAgent,
    DependencyAnalyzer,
    SOPStep,
)


# ============================================================================
# TEST FIXTURES
# ============================================================================

@pytest.fixture
def mock_llm_client():
    """Mock LLM client"""
    return MagicMock()


@pytest.fixture
def mock_mcp_client():
    """Mock MCP client"""
    return MagicMock()


@pytest.fixture
def planner_agent(mock_llm_client, mock_mcp_client):
    """Create a PlannerAgent instance for testing"""
    agent = PlannerAgent(llm_client=mock_llm_client, mcp_client=mock_mcp_client)
    return agent


@pytest.fixture
def sample_steps_no_cycles():
    """Create SOP steps with no cycles (linear chain A→B→C)"""
    return [
        SOPStep(
            id="step-a",
            role="architect",
            action="Design system",
            objective="Create architecture",
            definition_of_done="Architecture documented",
            dependencies=[],
            cost=2.0,
        ),
        SOPStep(
            id="step-b",
            role="coder",
            action="Implement code",
            objective="Write implementation",
            definition_of_done="Code working",
            dependencies=["step-a"],
            cost=5.0,
        ),
        SOPStep(
            id="step-c",
            role="tester",
            action="Write tests",
            objective="Verify correctness",
            definition_of_done="Tests passing",
            dependencies=["step-b"],
            cost=3.0,
        ),
    ]


@pytest.fixture
def sample_steps_simple_cycle():
    """Create SOP steps with simple cycle A→B→A"""
    return [
        SOPStep(
            id="step-a",
            role="agent1",
            action="Action A",
            objective="Do A",
            definition_of_done="A done",
            dependencies=["step-b"],
            cost=1.0,
        ),
        SOPStep(
            id="step-b",
            role="agent2",
            action="Action B",
            objective="Do B",
            definition_of_done="B done",
            dependencies=["step-a"],
            cost=1.0,
        ),
    ]


@pytest.fixture
def sample_steps_complex_cycle():
    """Create SOP steps with complex cycle A→B→C→A"""
    return [
        SOPStep(
            id="step-a",
            role="agent1",
            action="Action A",
            objective="Do A",
            definition_of_done="A done",
            dependencies=["step-c"],
            cost=1.0,
        ),
        SOPStep(
            id="step-b",
            role="agent2",
            action="Action B",
            objective="Do B",
            definition_of_done="B done",
            dependencies=["step-a"],
            cost=1.0,
        ),
        SOPStep(
            id="step-c",
            role="agent3",
            action="Action C",
            objective="Do C",
            definition_of_done="C done",
            dependencies=["step-b"],
            cost=1.0,
        ),
    ]


@pytest.fixture
def sample_steps_self_loop():
    """Create SOP steps with self-loop A→A"""
    return [
        SOPStep(
            id="step-a",
            role="agent1",
            action="Action A",
            objective="Do A",
            definition_of_done="A done",
            dependencies=["step-a"],
            cost=1.0,
        ),
    ]


@pytest.fixture
def sample_steps_partial_cycle():
    """Create SOP steps where only some steps have a cycle"""
    return [
        SOPStep(
            id="step-a",
            role="agent1",
            action="Action A",
            objective="Do A",
            definition_of_done="A done",
            dependencies=[],
            cost=1.0,
        ),
        SOPStep(
            id="step-b",
            role="agent2",
            action="Action B",
            objective="Do B",
            definition_of_done="B done",
            dependencies=["step-a"],
            cost=1.0,
        ),
        SOPStep(
            id="step-c",
            role="agent3",
            action="Action C",
            objective="Do C",
            definition_of_done="C done",
            dependencies=["step-d"],
            cost=1.0,
        ),
        SOPStep(
            id="step-d",
            role="agent4",
            action="Action D",
            objective="Do D",
            definition_of_done="D done",
            dependencies=["step-c"],
            cost=1.0,
        ),
    ]


# ============================================================================
# TEST SUITE 1: DependencyAnalyzer.detect_cycles()
# ============================================================================

class TestDetectCycles:
    """Test cases for DependencyAnalyzer.detect_cycles()"""

    def test_detect_cycles_no_cycles(self, sample_steps_no_cycles):
        """Test detection when there are NO cycles (linear chain)"""
        cycles = DependencyAnalyzer.detect_cycles(sample_steps_no_cycles)
        assert cycles == [], "Should detect no cycles in linear chain"
        assert isinstance(cycles, list), "Should return a list"

    def test_detect_cycles_simple_cycle_ab(self, sample_steps_simple_cycle):
        """Test detection of simple A→B→A cycle"""
        cycles = DependencyAnalyzer.detect_cycles(sample_steps_simple_cycle)
        assert len(cycles) > 0, "Should detect at least one cycle"
        # Verify cycle contains both nodes
        cycle = cycles[0]
        assert "step-a" in cycle, "Cycle should contain step-a"
        assert "step-b" in cycle, "Cycle should contain step-b"

    def test_detect_cycles_complex_cycle(self, sample_steps_complex_cycle):
        """Test detection of complex A→B→C→A cycle"""
        cycles = DependencyAnalyzer.detect_cycles(sample_steps_complex_cycle)
        assert len(cycles) > 0, "Should detect at least one cycle"
        cycle = cycles[0]
        # All three steps should be in the cycle
        assert "step-a" in cycle, "Cycle should contain step-a"
        assert "step-b" in cycle, "Cycle should contain step-b"
        assert "step-c" in cycle, "Cycle should contain step-c"

    def test_detect_cycles_self_loop(self, sample_steps_self_loop):
        """Test detection of self-loop A→A"""
        cycles = DependencyAnalyzer.detect_cycles(sample_steps_self_loop)
        assert len(cycles) > 0, "Should detect self-loop as cycle"
        cycle = cycles[0]
        assert "step-a" in cycle, "Self-loop cycle should contain the step"

    def test_detect_cycles_partial_cycle(self, sample_steps_partial_cycle):
        """Test detection in mixed graph (some steps with cycle, some without)"""
        cycles = DependencyAnalyzer.detect_cycles(sample_steps_partial_cycle)
        assert len(cycles) > 0, "Should detect cycle even with non-cyclic steps"
        # The cycle should only include step-c and step-d
        cycle = cycles[0]
        assert "step-c" in cycle, "Cycle should contain step-c"
        assert "step-d" in cycle, "Cycle should contain step-d"

    def test_detect_cycles_empty_list(self):
        """Test with empty step list"""
        cycles = DependencyAnalyzer.detect_cycles([])
        assert cycles == [], "Empty step list should have no cycles"

    def test_detect_cycles_single_step_no_deps(self):
        """Test with single step that has no dependencies"""
        steps = [
            SOPStep(
                id="step-a",
                role="agent",
                action="Action",
                objective="Do it",
                definition_of_done="Done",
                dependencies=[],
            )
        ]
        cycles = DependencyAnalyzer.detect_cycles(steps)
        assert cycles == [], "Single step with no dependencies should have no cycles"

    def test_detect_cycles_multiple_independent_chains(self):
        """Test with multiple independent linear chains"""
        steps = [
            SOPStep(
                id="step-1",
                role="agent",
                action="Action 1",
                objective="Do 1",
                definition_of_done="Done 1",
                dependencies=[],
            ),
            SOPStep(
                id="step-2",
                role="agent",
                action="Action 2",
                objective="Do 2",
                definition_of_done="Done 2",
                dependencies=["step-1"],
            ),
            SOPStep(
                id="step-3",
                role="agent",
                action="Action 3",
                objective="Do 3",
                definition_of_done="Done 3",
                dependencies=[],
            ),
            SOPStep(
                id="step-4",
                role="agent",
                action="Action 4",
                objective="Do 4",
                definition_of_done="Done 4",
                dependencies=["step-3"],
            ),
        ]
        cycles = DependencyAnalyzer.detect_cycles(steps)
        assert cycles == [], "Multiple independent chains should have no cycles"

    def test_detect_cycles_return_type(self, sample_steps_simple_cycle):
        """Test that detect_cycles returns correct type"""
        cycles = DependencyAnalyzer.detect_cycles(sample_steps_simple_cycle)
        assert isinstance(cycles, list), "Should return a list"
        if cycles:
            assert isinstance(cycles[0], list), "Each cycle should be a list"
            assert all(isinstance(node, str) for node in cycles[0]), "Cycle nodes should be strings"


# ============================================================================
# TEST SUITE 2: PlannerAgent._robust_json_parse()
# ============================================================================

class TestRobustJsonParse:
    """Test cases for PlannerAgent._robust_json_parse()"""

    def test_parse_valid_json(self, planner_agent):
        """Test parsing valid JSON"""
        json_str = '{"sops": [], "plan_id": "test-123"}'
        result = planner_agent._robust_json_parse(json_str)
        assert result is not None, "Should parse valid JSON"
        assert result["plan_id"] == "test-123"
        assert isinstance(result["sops"], list)

    def test_parse_valid_json_with_nested_objects(self, planner_agent):
        """Test parsing valid JSON with nested structures"""
        json_str = json.dumps({
            "plan": {
                "id": "plan-1",
                "steps": [
                    {"id": "step-1", "name": "Design"},
                    {"id": "step-2", "name": "Implement"}
                ]
            }
        })
        result = planner_agent._robust_json_parse(json_str)
        assert result is not None
        assert result["plan"]["id"] == "plan-1"
        assert len(result["plan"]["steps"]) == 2

    def test_parse_json_with_markdown_fence_json(self, planner_agent):
        """Test parsing JSON wrapped in ```json markdown blocks"""
        json_str = """
```json
{
    "sops": [
        {"id": "step-1", "role": "architect"}
    ],
    "plan_id": "markdown-test"
}
```
"""
        result = planner_agent._robust_json_parse(json_str)
        assert result is not None, "Should parse JSON from markdown fence"
        assert result["plan_id"] == "markdown-test"
        assert len(result["sops"]) == 1

    def test_parse_json_with_markdown_fence_no_lang(self, planner_agent):
        """Test parsing JSON wrapped in plain ``` markdown blocks"""
        json_str = """
```
{
    "id": "test",
    "value": 42
}
```
"""
        result = planner_agent._robust_json_parse(json_str)
        assert result is not None, "Should parse JSON from plain markdown fence"
        assert result["id"] == "test"
        assert result["value"] == 42

    def test_parse_json_with_preamble_and_markdown(self, planner_agent):
        """Test parsing JSON with text preamble and markdown fence"""
        json_str = """
Here's your plan:

```json
{
    "plan_id": "preamble-test",
    "stages": 3
}
```

That's all!
"""
        result = planner_agent._robust_json_parse(json_str)
        assert result is not None, "Should extract JSON despite preamble"
        assert result["plan_id"] == "preamble-test"

    def test_parse_partial_json(self, planner_agent):
        """Test parsing partial JSON (missing closing braces)"""
        json_str = '{"id": "partial", "data": {"nested": "value"}'
        result = planner_agent._robust_json_parse(json_str)
        # May or may not parse depending on regex strategy, but should not crash
        assert isinstance(result, (dict, type(None)))

    def test_parse_json_with_trailing_commas(self, planner_agent):
        """Test parsing JSON with trailing commas (common LLM mistake)"""
        json_str = '''{
            "steps": [
                {"id": "1", "name": "Design"},
                {"id": "2", "name": "Code"},
            ],
            "config": {
                "parallel": true,
            }
        }'''
        result = planner_agent._robust_json_parse(json_str)
        assert result is not None, "Should fix trailing commas"
        assert len(result["steps"]) == 2
        assert result["config"]["parallel"] is True

    def test_parse_json_array_wrapped(self, planner_agent):
        """Test parsing JSON array at top level, wrapped in expected structure"""
        json_str = """
[
    {"id": "step-1", "role": "architect"},
    {"id": "step-2", "role": "coder"}
]
"""
        result = planner_agent._robust_json_parse(json_str)
        assert result is not None, "Should parse JSON array"
        # Result can be either wrapped dict or direct array
        if isinstance(result, dict):
            assert "sops" in result, "Should wrap array in {sops: ...}"
            assert len(result["sops"]) == 2
        else:
            # Direct array parsing
            assert isinstance(result, list)
            assert len(result) == 2

    def test_parse_invalid_json_returns_none(self, planner_agent):
        """Test parsing completely invalid JSON returns None"""
        json_str = "This is not JSON at all @#$%"
        result = planner_agent._robust_json_parse(json_str)
        assert result is None, "Should return None for unparseable input"

    def test_parse_json_with_extra_whitespace(self, planner_agent):
        """Test parsing JSON with excessive whitespace"""
        json_str = """

        {
            "plan":    "test"  ,
            "status"  :  "ready"
        }

        """
        result = planner_agent._robust_json_parse(json_str)
        assert result is not None, "Should handle whitespace"
        assert result["plan"] == "test"

    def test_parse_json_with_special_characters(self, planner_agent):
        """Test parsing JSON with special characters and escapes"""
        json_str = json.dumps({
            "message": "Deploy to \"production\" environment\n with newlines",
            "path": "C:\\Users\\John\\file.txt",
            "emoji": "✅"
        })
        result = planner_agent._robust_json_parse(json_str)
        assert result is not None
        assert "production" in result["message"]
        assert result["emoji"] == "✅"

    def test_parse_json_complex_nested(self, planner_agent):
        """Test parsing deeply nested JSON structures"""
        json_str = json.dumps({
            "plan": {
                "stages": [
                    {
                        "name": "Stage 1",
                        "steps": [
                            {
                                "id": "1",
                                "config": {
                                    "timeout": 300,
                                    "retry": {"max": 3, "backoff": "exponential"}
                                }
                            }
                        ]
                    }
                ]
            }
        })
        result = planner_agent._robust_json_parse(json_str)
        assert result is not None
        assert result["plan"]["stages"][0]["steps"][0]["config"]["retry"]["backoff"] == "exponential"

    def test_parse_json_with_numbers(self, planner_agent):
        """Test parsing JSON with various number formats"""
        json_str = json.dumps({
            "integer": 42,
            "float": 3.14159,
            "negative": -100,
            "scientific": 1.23e-4,
            "zero": 0
        })
        result = planner_agent._robust_json_parse(json_str)
        assert result is not None
        assert result["integer"] == 42
        assert abs(result["float"] - 3.14159) < 0.00001
        assert result["negative"] == -100

    def test_parse_json_with_boolean_and_null(self, planner_agent):
        """Test parsing JSON with boolean and null values"""
        json_str = json.dumps({
            "active": True,
            "disabled": False,
            "nullable": None,
            "list_with_null": [1, None, 3]
        })
        result = planner_agent._robust_json_parse(json_str)
        assert result is not None
        assert result["active"] is True
        assert result["disabled"] is False
        assert result["nullable"] is None
        assert result["list_with_null"][1] is None

    def test_parse_json_empty_objects(self, planner_agent):
        """Test parsing JSON with empty objects and arrays"""
        json_str = '{"empty_obj": {}, "empty_arr": [], "data": "value"}'
        result = planner_agent._robust_json_parse(json_str)
        assert result is not None
        assert result["empty_obj"] == {}
        assert result["empty_arr"] == []

    def test_parse_json_unicode(self, planner_agent):
        """Test parsing JSON with unicode characters"""
        json_str = json.dumps({
            "chinese": "你好世界",
            "arabic": "مرحبا",
            "emoji_text": "🚀 Rocket to success"
        })
        result = planner_agent._robust_json_parse(json_str)
        assert result is not None
        assert "世界" in result["chinese"]
        assert "🚀" in result["emoji_text"]

    def test_parse_json_multiline_strings(self, planner_agent):
        """Test parsing JSON with multiline string content"""
        json_str = json.dumps({
            "multiline_doc": "Line 1\nLine 2\nLine 3",
            "description": "Multi-step\nexecution\nplan"
        })
        result = planner_agent._robust_json_parse(json_str)
        assert result is not None
        assert "\n" in result["multiline_doc"]
        assert result["multiline_doc"].count("\n") == 2

    def test_parse_json_with_html_entities(self, planner_agent):
        """Test parsing JSON that might contain HTML-like content"""
        json_str = json.dumps({
            "html_content": "<div>Hello</div>",
            "script_content": "if (x > 5) { return true; }"
        })
        result = planner_agent._robust_json_parse(json_str)
        assert result is not None
        assert "<div>" in result["html_content"]
        assert "if (x > 5)" in result["script_content"]

    def test_parse_json_from_middle_of_text(self, planner_agent):
        """Test parsing JSON embedded in longer text"""
        text = """
        Some preamble text here...
        Let me generate a plan for you:

        {
            "plan_id": "embedded-123",
            "steps": 5
        }

        That's your plan! Good luck.
        """
        result = planner_agent._robust_json_parse(text)
        assert result is not None, "Should extract JSON from middle of text"
        assert result["plan_id"] == "embedded-123"

    def test_parse_json_with_duplicated_keys(self, planner_agent):
        """Test parsing JSON with duplicated keys (last one wins in valid JSON)"""
        # Note: This is technically invalid JSON, but some parsers handle it
        json_str = '{"key": "first", "key": "second"}'
        result = planner_agent._robust_json_parse(json_str)
        # In standard JSON, last value wins
        if result is not None:
            assert result["key"] == "second"

    def test_parse_json_robustness_with_extra_quotes(self, planner_agent):
        """Test fallback strategies with various quote issues"""
        # This is broken JSON but testing robustness
        json_str = '{"status": \'incomplete\'}'  # Single quotes instead of double
        result = planner_agent._robust_json_parse(json_str)
        # May or may not parse; just ensure no crash
        assert isinstance(result, (dict, type(None)))


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

class TestDependencyAnalyzerIntegration:
    """Integration tests for DependencyAnalyzer with other methods"""

    def test_detect_cycles_before_parallel_group_analysis(self, sample_steps_simple_cycle):
        """Test that cycle detection is used before parallel analysis"""
        cycles = DependencyAnalyzer.detect_cycles(sample_steps_simple_cycle)
        assert len(cycles) > 0, "Should detect cycle"

        # Even if we try parallel groups, it should handle gracefully
        parallel_groups = DependencyAnalyzer.find_parallel_groups(sample_steps_simple_cycle)
        # Result depends on implementation, but should not crash

    def test_detect_cycles_and_critical_path(self, sample_steps_no_cycles):
        """Test cycle detection with critical path analysis"""
        cycles = DependencyAnalyzer.detect_cycles(sample_steps_no_cycles)
        assert cycles == [], "Should find no cycles"

        critical_path = DependencyAnalyzer.find_critical_path(sample_steps_no_cycles)
        assert len(critical_path) > 0, "Should find critical path"
        assert critical_path[0] == "step-a", "Should start with step-a"
        assert critical_path[-1] == "step-c", "Should end with step-c"


class TestPlannerAgentJsonParsing:
    """Integration tests for PlannerAgent JSON parsing"""

    def test_parse_execution_plan_json(self, planner_agent):
        """Test parsing a realistic ExecutionPlan JSON response"""
        plan_json = json.dumps({
            "plan_id": "plan-12345",
            "goal": "Implement new feature",
            "strategy_overview": "Multi-stage execution",
            "sops": [
                {
                    "id": "step-1",
                    "role": "architect",
                    "action": "Design",
                    "objective": "Create design",
                    "definition_of_done": "Design complete",
                    "dependencies": [],
                    "cost": 2.0
                },
                {
                    "id": "step-2",
                    "role": "coder",
                    "action": "Implement",
                    "objective": "Write code",
                    "definition_of_done": "Code done",
                    "dependencies": ["step-1"],
                    "cost": 5.0
                }
            ]
        })
        result = planner_agent._robust_json_parse(plan_json)
        assert result is not None
        assert result["plan_id"] == "plan-12345"
        assert len(result["sops"]) == 2

    def test_parse_llm_response_with_extra_text(self, planner_agent):
        """Test parsing LLM response with explanation text"""
        llm_response = """
I've created an execution plan for your request. Here's the breakdown:

```json
{
    "plan_id": "dynamic-plan",
    "goal": "Fix critical bug",
    "sops": [
        {
            "id": "step-1",
            "role": "investigator",
            "action": "Investigate",
            "objective": "Find root cause",
            "definition_of_done": "Root cause identified"
        }
    ]
}
```

This plan focuses on proper investigation before any fixes.
"""
        result = planner_agent._robust_json_parse(llm_response)
        assert result is not None
        assert result["goal"] == "Fix critical bug"


# ============================================================================
# EDGE CASE & STRESS TESTS
# ============================================================================

class TestEdgeCases:
    """Edge case tests for robustness"""

    def test_detect_cycles_large_graph(self):
        """Test cycle detection on larger graph"""
        steps = []
        # Create 100-step linear chain
        for i in range(100):
            deps = [f"step-{i-1}"] if i > 0 else []
            steps.append(SOPStep(
                id=f"step-{i}",
                role="agent",
                action=f"Action {i}",
                objective=f"Do {i}",
                definition_of_done=f"Done {i}",
                dependencies=deps,
            ))

        cycles = DependencyAnalyzer.detect_cycles(steps)
        assert cycles == [], "Large linear graph should have no cycles"

    def test_parse_json_very_large_object(self, planner_agent):
        """Test parsing very large JSON object"""
        large_data = {
            "steps": [
                {"id": f"step-{i}", "value": i, "data": "x" * 100}
                for i in range(1000)
            ]
        }
        json_str = json.dumps(large_data)
        result = planner_agent._robust_json_parse(json_str)
        assert result is not None
        assert len(result["steps"]) == 1000

    def test_detect_cycles_with_missing_dependencies(self):
        """Test cycle detection when dependencies reference non-existent steps"""
        steps = [
            SOPStep(
                id="step-a",
                role="agent",
                action="Action A",
                objective="Do A",
                definition_of_done="Done",
                dependencies=["step-nonexistent"],
            )
        ]
        cycles = DependencyAnalyzer.detect_cycles(steps)
        # Should handle gracefully without crashing
        assert isinstance(cycles, list)

    def test_parse_json_with_null_input(self, planner_agent):
        """Test parsing with None input"""
        # This tests robustness to unexpected input
        try:
            result = planner_agent._robust_json_parse(None)
            # If it doesn't crash, that's good
            assert result is None or isinstance(result, dict)
        except (TypeError, AttributeError):
            # Acceptable to fail on None input
            pass

    def test_parse_json_empty_string(self, planner_agent):
        """Test parsing empty string"""
        result = planner_agent._robust_json_parse("")
        assert result is None, "Empty string should return None"

    def test_parse_json_whitespace_only(self, planner_agent):
        """Test parsing whitespace-only string"""
        result = planner_agent._robust_json_parse("   \n\t   ")
        assert result is None, "Whitespace-only string should return None"


# ============================================================================
# PARAMETRIZED TESTS
# ============================================================================

class TestParametrized:
    """Parametrized tests for comprehensive coverage"""

    @pytest.mark.parametrize("json_str,expected_keys", [
        ('{"a": 1, "b": 2}', ["a", "b"]),
        ('{"id": "test", "data": null}', ["id", "data"]),
        ('{"arr": [1, 2, 3]}', ["arr"]),
    ])
    def test_parse_various_valid_json(self, planner_agent, json_str, expected_keys):
        """Test parsing various valid JSON formats"""
        result = planner_agent._robust_json_parse(json_str)
        assert result is not None
        for key in expected_keys:
            assert key in result

    @pytest.mark.parametrize("invalid_json", [
        "{invalid}",
        "[incomplete",
        "not json",
        "{'single': 'quotes'}",
        "{,}",
    ])
    def test_parse_invalid_json(self, planner_agent, invalid_json):
        """Test that invalid JSON either parses or returns None gracefully"""
        result = planner_agent._robust_json_parse(invalid_json)
        # Should be None or dict (if fallback succeeded)
        assert result is None or isinstance(result, dict)

    @pytest.mark.parametrize("step_count", [1, 2, 5, 10])
    def test_cycle_detection_various_sizes(self, step_count):
        """Test cycle detection on graphs of various sizes"""
        steps = []
        for i in range(step_count):
            deps = [f"step-{i-1}"] if i > 0 else []
            steps.append(SOPStep(
                id=f"step-{i}",
                role="agent",
                action=f"Action {i}",
                objective=f"Do {i}",
                definition_of_done=f"Done {i}",
                dependencies=deps,
            ))
        cycles = DependencyAnalyzer.detect_cycles(steps)
        assert cycles == [], f"Linear chain of size {step_count} should have no cycles"
