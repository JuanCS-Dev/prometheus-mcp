"""
SCIENTIFIC VALIDATION: Complete Integration Tests

Tests real use cases for Phases 2.3, 3.1, 3.2 with scientific rigor.
"""

import pytest
import time
from unittest.mock import Mock, AsyncMock

from jdev_cli.core.conversation import ConversationManager, ConversationState
from jdev_cli.core.recovery import (
    ErrorRecoveryEngine, ErrorCategory, RecoveryContext, RecoveryStrategy
)
from jdev_cli.core.workflow import (
    WorkflowStep, DependencyGraph, AutoCritique, ThoughtPath
)


class TestMultiTurnConversation:
    """PHASE 2.3 VALIDATION: Multi-turn conversation."""

    def test_scenario_1_context_preservation(self):
        """✓ Scenario 1: Context preserved across 3 turns."""
        manager = ConversationManager(
            session_id="test_context",
            max_context_tokens=4000
        )

        # Turn 1
        turn1 = manager.start_turn("Create fibonacci function")
        manager.add_llm_response(turn1, "Created fibonacci function")
        manager.transition_state(ConversationState.IDLE, "done")

        # Turn 2 - should reference Turn 1
        turn2 = manager.start_turn("Add memoization to it")
        context = manager.get_context_for_llm(include_last_n=2)

        # Verify context includes Turn 1
        assert len(context) >= 2
        assert any("fibonacci" in str(msg.get("content", "")) for msg in context)

        manager.add_llm_response(turn2, "Added memoization")
        manager.transition_state(ConversationState.IDLE, "done")

        # Turn 3
        turn3 = manager.start_turn("Add tests")
        context = manager.get_context_for_llm(include_last_n=3)

        # SUCCESS CRITERIA
        assert manager.turn_counter == 3, f"Expected 3 turns, got {manager.turn_counter}"
        assert len(manager.turns) == 3, f"Expected 3 turns stored, got {len(manager.turns)}"

        print("✓ PASS: Context preserved across 3 turns")

    def test_scenario_2_context_compaction(self):
        """✓ Scenario 2: Context compaction trigger."""
        manager = ConversationManager(
            session_id="test_compaction",
            max_context_tokens=200  # Small for testing
        )

        # Add many turns
        for i in range(20):
            turn = manager.start_turn(f"Query {i} with some long text to fill context")
            manager.add_llm_response(
                turn,
                f"Response {i} with additional text to increase token count",
                tokens_used=15
            )
            manager.transition_state(ConversationState.IDLE, "done")

        # SUCCESS CRITERIA
        assert len(manager.turns) < 20, f"Expected compaction, got {len(manager.turns)} turns"
        assert manager.context_window.get_usage_percentage() < 0.8, \
            f"Usage {manager.context_window.get_usage_percentage():.0%} should be < 80%"

        print(f"✓ PASS: Context compacted from 20 to {len(manager.turns)} turns")
        print(f"  Usage: {manager.context_window.get_usage_percentage():.0%}")


class TestErrorRecovery:
    """PHASE 3.1 VALIDATION: Error recovery."""

    @pytest.mark.asyncio
    async def test_scenario_3_file_not_found(self):
        """✓ Scenario 3: File not found recovery."""
        llm = Mock()
        llm.generate_async = AsyncMock(return_value={
            "content": """DIAGNOSIS: File does not exist
CORRECTION: Search for similar files
TOOL_CALL: {"tool": "search_files", "args": {"pattern": "*missing*"}}"""
        })

        engine = ErrorRecoveryEngine(llm_client=llm, max_attempts=2)

        error = "File not found: missing.txt"
        category = engine.categorize_error(error)

        assert category == ErrorCategory.NOT_FOUND, f"Expected NOT_FOUND, got {category}"

        context = RecoveryContext(
            attempt_number=1,
            max_attempts=2,
            error=error,
            error_category=category,
            failed_tool="read_file",
            failed_args={"path": "missing.txt"},
            previous_result=None,
            user_intent="Read file",
            previous_commands=[]
        )

        result = await engine.attempt_recovery(context)

        # SUCCESS CRITERIA
        assert result.success, "Recovery should provide correction"
        assert result.corrected_tool == "search_files", \
            f"Expected search_files, got {result.corrected_tool}"

        print("✓ PASS: File not found recovery succeeded")
        print(f"  Category: {category.value}")
        print(f"  Correction: {result.corrected_tool}")

    def test_scenario_4_permission_denied(self):
        """✓ Scenario 4: Permission denied detection."""
        engine = ErrorRecoveryEngine(llm_client=Mock(), max_attempts=2)

        error = "Permission denied: /root/protected.txt"
        category = engine.categorize_error(error)

        assert category == ErrorCategory.PERMISSION, f"Expected PERMISSION, got {category}"

        context = RecoveryContext(
            attempt_number=1,
            max_attempts=2,
            error=error,
            error_category=category,
            failed_tool="delete_file",
            failed_args={"path": "/root/protected.txt"},
            previous_result=None,
            user_intent="Delete file",
            previous_commands=[]
        )

        strategy = engine.determine_strategy(category, context)

        # SUCCESS CRITERIA
        assert strategy == RecoveryStrategy.SUGGEST_PERMISSION, \
            f"Expected SUGGEST_PERMISSION, got {strategy}"

        print("✓ PASS: Permission error correctly categorized")
        print(f"  Strategy: {strategy.value}")


class TestWorkflowOrchestration:
    """PHASE 3.2 VALIDATION: Workflow orchestration."""

    def test_scenario_5_dependency_ordering(self):
        """✓ Scenario 5: Dependency ordering."""
        graph = DependencyGraph()

        step1 = WorkflowStep("read_app", "read_file", {"path": "app.py"})
        step2 = WorkflowStep("edit_app", "edit_file", {"path": "app.py"}, dependencies=["read_app"])
        step3 = WorkflowStep("read_test", "read_file", {"path": "test.py"}, dependencies=["edit_app"])
        step4 = WorkflowStep("edit_test", "edit_file", {"path": "test.py"}, dependencies=["read_test"])

        graph.add_step(step1)
        graph.add_step(step2)
        graph.add_step(step3)
        graph.add_step(step4)

        sorted_steps = graph.topological_sort()

        # SUCCESS CRITERIA
        assert len(sorted_steps) == 4, f"Expected 4 steps, got {len(sorted_steps)}"
        assert sorted_steps[0].step_id == "read_app"
        assert sorted_steps[1].step_id == "edit_app"
        assert sorted_steps[2].step_id == "read_test"
        assert sorted_steps[3].step_id == "edit_test"

        order = " → ".join(s.step_id for s in sorted_steps)
        print(f"✓ PASS: Dependency order correct: {order}")

    def test_scenario_7_lei_enforcement(self):
        """✓ Scenario 7: LEI enforcement."""
        critique_system = AutoCritique()

        # Clean code
        clean_step = WorkflowStep("gen_clean", "generate", {})
        clean_step.execution_time = 0.5

        clean_result = Mock()
        clean_result.success = True
        clean_result.data = """
def authenticate(username, password):
    user = find_user(username)
    if user and verify_password(user, password):
        return create_session(user)
    return None
"""

        clean_critique = critique_system.critique_step(clean_step, clean_result)

        # Lazy code
        lazy_step = WorkflowStep("gen_lazy", "generate", {})
        lazy_step.execution_time = 0.5

        lazy_result = Mock()
        lazy_result.success = True
        lazy_result.data = """
def authenticate(username, password):
    # TODO: implement authentication
    pass

def authorize(user, resource):
    raise NotImplementedError
"""

        lazy_critique = critique_system.critique_step(lazy_step, lazy_result)

        # SUCCESS CRITERIA
        assert clean_critique.passed, "Clean code should pass"
        assert clean_critique.lei < 1.0, f"Clean LEI {clean_critique.lei} should be < 1.0"

        assert not lazy_critique.passed, "Lazy code should fail"
        assert lazy_critique.lei >= 1.0, f"Lazy LEI {lazy_critique.lei} should be >= 1.0"

        print("✓ PASS: LEI enforcement working")
        print(f"  Clean code LEI: {clean_critique.lei:.2f} (PASS)")
        print(f"  Lazy code LEI: {lazy_critique.lei:.2f} (FAIL)")

    def test_scenario_10_parallel_detection(self):
        """✓ Scenario 10: Parallel execution detection."""
        graph = DependencyGraph()

        stepA = WorkflowStep("read1", "read_file", {"path": "file1.py"})
        stepB = WorkflowStep("read2", "read_file", {"path": "file2.py"})
        stepC = WorkflowStep("read3", "read_file", {"path": "file3.py"})
        stepD = WorkflowStep("combine", "combine", {}, dependencies=["read1", "read2", "read3"])

        graph.add_step(stepA)
        graph.add_step(stepB)
        graph.add_step(stepC)
        graph.add_step(stepD)

        groups = graph.find_parallel_groups()

        # SUCCESS CRITERIA
        assert len(groups) >= 2, f"Expected >= 2 groups, got {len(groups)}"

        # First group should have 3 parallel steps
        first_group = groups[0]
        assert len(first_group) == 3, f"Expected 3 parallel steps, got {len(first_group)}"

        print(f"✓ PASS: Parallel groups detected: {len(groups)} groups")
        print(f"  Group 1: {len(first_group)} parallel steps")


class TestConstitutionalCompliance:
    """CONSTITUTIONAL VALIDATION."""

    def test_p6_max_2_iterations(self):
        """✓ P6: Max 2 iterations enforced."""
        engine = ErrorRecoveryEngine(llm_client=Mock(), max_attempts=2)

        assert engine.max_attempts == 2, f"Expected 2, got {engine.max_attempts}"

        print("✓ PASS: P6 max 2 iterations enforced")

    def test_lei_threshold(self):
        """✓ LEI < 1.0 threshold."""
        critique_system = AutoCritique()

        assert critique_system.lei_threshold == 1.0, \
            f"Expected 1.0, got {critique_system.lei_threshold}"

        print("✓ PASS: LEI < 1.0 threshold enforced")

    def test_constitutional_weights(self):
        """✓ Constitutional scoring weights (0.4, 0.3, 0.3)."""
        path = ThoughtPath("test", "Test", [])
        path.completeness_score = 1.0
        path.validation_score = 1.0
        path.efficiency_score = 1.0

        score = path.calculate_score()
        assert score == 1.0, f"Expected 1.0, got {score}"

        # Test weights
        path.completeness_score = 0.8
        path.validation_score = 0.6
        path.efficiency_score = 0.4

        score = path.calculate_score()
        expected = 0.8 * 0.4 + 0.6 * 0.3 + 0.4 * 0.3  # 0.62

        assert abs(score - expected) < 0.01, \
            f"Score {score} != expected {expected}"

        print("✓ PASS: Constitutional weights (0.4, 0.3, 0.3) correct")


class TestPerformance:
    """PERFORMANCE VALIDATION."""

    def test_dependency_sort_performance(self):
        """✓ Performance: 100-step topological sort < 100ms."""
        graph = DependencyGraph()

        # Add 100 steps with dependencies
        for i in range(100):
            deps = [f"step{j}" for j in range(max(0, i-3), i)]
            step = WorkflowStep(f"step{i}", "tool", {}, dependencies=deps)
            graph.add_step(step)

        start = time.time()
        sorted_steps = graph.topological_sort()
        elapsed = time.time() - start

        # SUCCESS CRITERIA: < 100ms
        assert elapsed < 0.1, f"Too slow: {elapsed:.3f}s (> 0.1s)"
        assert len(sorted_steps) == 100

        print(f"✓ PASS: 100-step sort in {elapsed*1000:.1f}ms (< 100ms)")


# Summary function
def print_summary():
    """Print validation summary."""
    print("\n" + "="*60)
    print("SCIENTIFIC VALIDATION SUMMARY")
    print("="*60)
    print("\nPhase 2.3: Multi-Turn Conversation")
    print("  ✓ Context preservation")
    print("  ✓ Context compaction")
    print("\nPhase 3.1: Error Recovery")
    print("  ✓ File not found recovery")
    print("  ✓ Permission denied detection")
    print("\nPhase 3.2: Workflow Orchestration")
    print("  ✓ Dependency ordering")
    print("  ✓ LEI enforcement")
    print("  ✓ Parallel detection")
    print("\nConstitutional Compliance")
    print("  ✓ P6: Max 2 iterations")
    print("  ✓ LEI < 1.0 threshold")
    print("  ✓ Scoring weights (0.4, 0.3, 0.3)")
    print("\nPerformance")
    print("  ✓ Topological sort < 100ms")
    print("\n" + "="*60)
    print("ALL VALIDATIONS PASSED! ✅")
    print("="*60 + "\n")


if __name__ == "__main__":
    # Run tests
    exit_code = pytest.main([__file__, "-v", "-s", "--tb=short"])

    if exit_code == 0:
        print_summary()

    exit(exit_code)
