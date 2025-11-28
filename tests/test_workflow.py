"""
Tests for Phase 3.2: Multi-Step Workflow Orchestration

Tests dependency graph, Tree-of-Thought, checkpoints, and auto-critique.
"""

import pytest
from unittest.mock import Mock, AsyncMock
from pathlib import Path
import tempfile

from jdev_cli.core.workflow import (
    WorkflowEngine,
    WorkflowStep,
    ThoughtPath,
    DependencyGraph,
    TreeOfThought,
    AutoCritique,
    CheckpointManager,
    Transaction,
    StepStatus,
)


class TestDependencyGraph:
    """Test dependency graph."""

    def test_add_step(self):
        """Test adding steps to graph."""
        graph = DependencyGraph()

        step1 = WorkflowStep("step1", "tool1", {})
        step2 = WorkflowStep("step2", "tool2", {}, dependencies=["step1"])

        graph.add_step(step1)
        graph.add_step(step2)

        assert len(graph.nodes) == 2
        assert len(graph.edges) == 1
        assert ("step1", "step2") in graph.edges

    def test_topological_sort_simple(self):
        """Test topological sort with simple dependencies."""
        graph = DependencyGraph()

        step1 = WorkflowStep("step1", "tool1", {})
        step2 = WorkflowStep("step2", "tool2", {}, dependencies=["step1"])
        step3 = WorkflowStep("step3", "tool3", {}, dependencies=["step2"])

        graph.add_step(step1)
        graph.add_step(step2)
        graph.add_step(step3)

        sorted_steps = graph.topological_sort()

        assert len(sorted_steps) == 3
        assert sorted_steps[0].step_id == "step1"
        assert sorted_steps[1].step_id == "step2"
        assert sorted_steps[2].step_id == "step3"

    def test_topological_sort_complex(self):
        """Test topological sort with complex dependencies."""
        graph = DependencyGraph()

        step1 = WorkflowStep("step1", "tool1", {})
        step2 = WorkflowStep("step2", "tool2", {})
        step3 = WorkflowStep("step3", "tool3", {}, dependencies=["step1", "step2"])

        graph.add_step(step1)
        graph.add_step(step2)
        graph.add_step(step3)

        sorted_steps = graph.topological_sort()

        assert len(sorted_steps) == 3
        # step3 must be last
        assert sorted_steps[2].step_id == "step3"
        # step1 and step2 can be in any order
        assert sorted_steps[0].step_id in ["step1", "step2"]

    def test_cycle_detection(self):
        """Test cycle detection."""
        graph = DependencyGraph()

        step1 = WorkflowStep("step1", "tool1", {}, dependencies=["step2"])
        step2 = WorkflowStep("step2", "tool2", {}, dependencies=["step1"])

        graph.add_step(step1)
        graph.add_step(step2)

        with pytest.raises(ValueError, match="cycle"):
            graph.topological_sort()

    def test_parallel_groups(self):
        """Test finding parallel execution groups."""
        graph = DependencyGraph()

        step1 = WorkflowStep("step1", "tool1", {})
        step2 = WorkflowStep("step2", "tool2", {})
        step3 = WorkflowStep("step3", "tool3", {}, dependencies=["step1", "step2"])

        graph.add_step(step1)
        graph.add_step(step2)
        graph.add_step(step3)

        groups = graph.find_parallel_groups()

        # step1 and step2 can run in parallel
        assert len(groups) >= 2
        # step3 must run after both
        assert any(step3 in group for group in groups)


class TestTreeOfThought:
    """Test Tree-of-Thought planning."""

    def test_naive_path_generation(self):
        """Test fallback naive path generation."""
        tot = TreeOfThought(llm_client=None)

        path = tot._generate_naive_path("Test goal", ["tool1", "tool2"])

        assert path.path_id == "naive_path"
        assert path.description == "Direct approach"
        assert path.total_score > 0

    def test_score_paths(self):
        """Test path scoring."""
        tot = TreeOfThought()

        path1 = ThoughtPath("path1", "Fast", [])
        path2 = ThoughtPath("path2", "Safe", [])

        scored = tot.score_paths([path1, path2])

        assert len(scored) == 2
        assert all(p.total_score >= 0 for p in scored)

    def test_select_best_path(self):
        """Test best path selection."""
        tot = TreeOfThought()

        # Path with fewer steps (more efficient) but no validation
        path1 = ThoughtPath("path1", "Fast but unsafe", [
            WorkflowStep("step1", "tool1", {})
        ])

        # Path with validation step (safer, better)
        path2 = ThoughtPath("path2", "Safe path", [
            WorkflowStep("step1", "tool1", {}),
            WorkflowStep("step2", "test_tool", {})  # Validation step
        ])

        best = tot.select_best_path([path1, path2])

        # path2 should win due to validation step
        assert best.path_id == "path2"


class TestAutoCritique:
    """Test auto-critique system."""

    def test_lei_calculation_clean_code(self):
        """Test LEI calculation for clean code."""
        critique_system = AutoCritique()

        clean_result = Mock()
        clean_result.data = """
def hello():
    return "Hello, World!"
"""

        lei = critique_system._calculate_lei(clean_result)

        assert lei < 1.0  # Clean code

    def test_lei_calculation_lazy_code(self):
        """Test LEI calculation for lazy code."""
        critique_system = AutoCritique()

        lazy_result = Mock()
        lazy_result.data = """
def hello():
    # TODO: implement
    pass
    
def world():
    raise NotImplementedError
"""

        lei = critique_system._calculate_lei(lazy_result)

        assert lei >= 1.0  # Lazy code detected

    def test_critique_success(self):
        """Test critique of successful step."""
        critique_system = AutoCritique()

        step = WorkflowStep("step1", "tool1", {})
        step.execution_time = 0.5

        result = Mock()
        result.success = True
        result.data = "Clean implementation"

        critique = critique_system.critique_step(step, result)

        assert critique.passed
        assert critique.lei < 1.0
        assert critique.completeness_score > 0.9

    def test_critique_lazy_code(self):
        """Test critique detects lazy code."""
        critique_system = AutoCritique()

        step = WorkflowStep("step1", "tool1", {})

        result = Mock()
        result.success = True
        result.data = "# TODO: implement\npass"

        critique = critique_system.critique_step(step, result)

        assert not critique.passed
        assert critique.lei >= 1.0
        assert any("Lazy" in issue for issue in critique.issues)

    def test_critique_slow_execution(self):
        """Test critique detects slow execution."""
        critique_system = AutoCritique()

        step = WorkflowStep("step1", "tool1", {})
        step.execution_time = 15.0  # Slow

        result = Mock()
        result.success = True

        critique = critique_system.critique_step(step, result)

        assert critique.efficiency_score < 0.7


class TestCheckpointManager:
    """Test checkpoint system."""

    def test_create_checkpoint(self):
        """Test creating checkpoint."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = CheckpointManager(backup_dir=Path(tmpdir))

            context = {"key": "value"}
            completed = ["step1", "step2"]

            checkpoint = manager.create_checkpoint("cp1", context, completed)

            assert checkpoint.checkpoint_id == "cp1"
            assert checkpoint.context == context
            assert checkpoint.completed_steps == completed

    def test_backup_file(self):
        """Test file backup."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = CheckpointManager(backup_dir=Path(tmpdir))

            # Create test file
            test_file = Path(tmpdir) / "test.txt"
            test_file.write_text("original content")

            # Create checkpoint and backup
            manager.create_checkpoint("cp1", {}, [])
            manager.backup_file("cp1", str(test_file))

            # Check backup was created
            checkpoint = manager.checkpoints["cp1"]
            assert str(test_file) in checkpoint.file_backups
            assert Path(checkpoint.file_backups[str(test_file)]).exists()

    def test_restore_checkpoint(self):
        """Test restoring checkpoint."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = CheckpointManager(backup_dir=Path(tmpdir))

            # Create test file
            test_file = Path(tmpdir) / "test.txt"
            test_file.write_text("original content")

            # Create checkpoint and backup
            manager.create_checkpoint("cp1", {}, [])
            manager.backup_file("cp1", str(test_file))

            # Modify file
            test_file.write_text("modified content")

            # Restore
            success = manager.restore_checkpoint("cp1")

            assert success
            assert test_file.read_text() == "original content"


class TestTransaction:
    """Test transactional execution."""

    def test_add_operation(self):
        """Test adding operations to transaction."""
        tx = Transaction("tx1")

        step = WorkflowStep("step1", "tool1", {})
        result = Mock()

        tx.add_operation(step, result)

        assert len(tx.operations) == 1
        assert tx.operations[0] == (step, result)

    @pytest.mark.asyncio
    async def test_commit(self):
        """Test transaction commit."""
        tx = Transaction("tx1")

        await tx.commit()

        assert tx.committed

    @pytest.mark.asyncio
    async def test_rollback(self):
        """Test transaction rollback."""
        tx = Transaction("tx1")

        step1 = WorkflowStep("step1", "tool1", {})
        step2 = WorkflowStep("step2", "tool2", {})

        tx.add_operation(step1, Mock())
        tx.add_operation(step2, Mock())

        checkpoint_manager = Mock()
        success = await tx.rollback(checkpoint_manager)

        assert success
        assert not tx.committed


class TestWorkflowStep:
    """Test workflow step."""

    def test_step_creation(self):
        """Test creating workflow step."""
        step = WorkflowStep(
            step_id="step1",
            tool_name="read_file",
            args={"path": "test.py"},
            dependencies=[]
        )

        assert step.step_id == "step1"
        assert step.tool_name == "read_file"
        assert step.status == StepStatus.PENDING

    def test_step_serialization(self):
        """Test step serialization."""
        step = WorkflowStep("step1", "tool1", {"arg": "value"})
        step.status = StepStatus.COMPLETED

        data = step.to_dict()

        assert data["step_id"] == "step1"
        assert data["tool_name"] == "tool1"
        assert data["status"] == "completed"


class TestWorkflowEngine:
    """Test workflow engine integration."""

    @pytest.mark.asyncio
    async def test_engine_initialization(self):
        """Test creating workflow engine."""
        llm = Mock()
        recovery = Mock()
        tools = Mock()
        tools.get_all.return_value = {"tool1": Mock(), "tool2": Mock()}

        engine = WorkflowEngine(llm, recovery, tools)

        assert engine.llm == llm
        assert engine.recovery == recovery
        assert engine.tools == tools
        assert isinstance(engine.tree_of_thought, TreeOfThought)
        assert isinstance(engine.dependency_graph, DependencyGraph)
        assert isinstance(engine.auto_critique, AutoCritique)
        assert isinstance(engine.checkpoints, CheckpointManager)

    @pytest.mark.asyncio
    async def test_simple_workflow_execution(self):
        """Test executing simple workflow."""
        # Mock components
        llm = Mock()
        recovery = Mock()

        # Mock tool
        mock_tool = Mock()
        mock_result = Mock()
        mock_result.success = True
        mock_result.data = "Clean result"
        mock_tool.execute = AsyncMock(return_value=mock_result)

        tools = Mock()
        tools.get_all.return_value = {"test_tool": mock_tool}
        tools.get.return_value = mock_tool

        engine = WorkflowEngine(llm, recovery, tools)

        # Override Tree-of-Thought to return simple path
        simple_path = ThoughtPath(
            path_id="test_path",
            description="Test path",
            steps=[
                WorkflowStep("step1", "test_tool", {"arg": "value"})
            ]
        )
        simple_path.completeness_score = 0.9
        simple_path.validation_score = 0.9
        simple_path.efficiency_score = 0.9
        simple_path.calculate_score()

        engine.tree_of_thought.generate_paths = AsyncMock(return_value=[simple_path])

        # Execute workflow
        result = await engine.execute_workflow("Test goal")

        assert result.success
        assert len(result.completed_steps) == 1
        assert result.completed_steps[0].status == StepStatus.COMPLETED


class TestConstitutionalCompliance:
    """Test Constitutional Layer 2 compliance."""

    def test_lei_threshold_enforcement(self):
        """Test LEI < 1.0 threshold is enforced."""
        critique_system = AutoCritique()

        assert critique_system.lei_threshold == 1.0

    def test_tree_of_thought_scoring_weights(self):
        """Test Constitutional scoring weights."""
        tot = TreeOfThought()

        path = ThoughtPath("test", "Test", [])
        path.completeness_score = 1.0
        path.validation_score = 1.0
        path.efficiency_score = 1.0

        score = path.calculate_score()

        # Should use Constitutional weights (0.4, 0.3, 0.3)
        expected = 1.0 * 0.4 + 1.0 * 0.3 + 1.0 * 0.3
        assert score == expected

    def test_auto_critique_all_checks(self):
        """Test auto-critique performs all Constitutional checks."""
        critique_system = AutoCritique()

        step = WorkflowStep("step1", "tool1", {})
        step.execution_time = 0.5

        result = Mock()
        result.success = True
        result.data = "Clean code"

        critique = critique_system.critique_step(step, result)

        # Must check: completeness (P1), validation (P2), efficiency (P6), LEI
        assert hasattr(critique, 'completeness_score')
        assert hasattr(critique, 'validation_passed')
        assert hasattr(critique, 'efficiency_score')
        assert hasattr(critique, 'lei')


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
