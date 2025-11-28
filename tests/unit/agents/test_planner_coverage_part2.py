"""
Tests for PlannerAgent Coverage - PART 2 (ExecutionMonitor + Helper Methods)

Tests cover:
- ExecutionMonitor: Event emission, metrics collection, monitoring lifecycle
- Helper Methods:
  - _infer_stage_name() - Generate human-readable stage names
  - _assess_risk() - Risk level assessment
  - _load_team_standards() - Load CLAUDE.md standards
- Additional PlannnerAgent functionality

Based on Anthropic Claude Code testing standards.
"""
import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch

from jdev_cli.agents.planner import (
    ExecutionMonitor,
    ExecutionEvent,
    ExecutionStrategy,
    AgentPriority,
    PlannerAgent,
    SOPStep,
    ExecutionStage,
)


# =============================================================================
# EXECUTION MONITOR TESTS
# =============================================================================

class TestExecutionMonitor:
    """Tests for ExecutionMonitor class."""

    @pytest.fixture
    def monitor(self):
        """Create a fresh ExecutionMonitor instance."""
        return ExecutionMonitor()

    def test_monitor_initialization(self, monitor):
        """Test ExecutionMonitor initializes with empty events."""
        assert monitor.events == []
        assert isinstance(monitor.events, list)

    def test_emit_single_event(self, monitor):
        """Test emitting a single execution event."""
        event = ExecutionEvent(
            timestamp="2025-01-01T12:00:00Z",
            event_type="started",
            step_id="step_1",
            agent_role="executor",
            correlation_id="corr-001"
        )

        monitor.emit(event)

        assert len(monitor.events) == 1
        assert monitor.events[0] == event

    def test_emit_multiple_events(self, monitor):
        """Test emitting multiple events."""
        events = [
            ExecutionEvent(
                timestamp="2025-01-01T12:00:00Z",
                event_type="started",
                step_id="step_1",
                agent_role="executor",
                correlation_id="corr-001"
            ),
            ExecutionEvent(
                timestamp="2025-01-01T12:00:05Z",
                event_type="completed",
                step_id="step_1",
                agent_role="executor",
                correlation_id="corr-001",
                duration_ms=5000
            ),
            ExecutionEvent(
                timestamp="2025-01-01T12:00:06Z",
                event_type="started",
                step_id="step_2",
                agent_role="tester",
                correlation_id="corr-002"
            ),
        ]

        for event in events:
            monitor.emit(event)

        assert len(monitor.events) == 3
        assert monitor.events[0].step_id == "step_1"
        assert monitor.events[1].duration_ms == 5000
        assert monitor.events[2].agent_role == "tester"

    def test_emit_started_event(self, monitor):
        """Test emitting a started event."""
        event = ExecutionEvent(
            timestamp="2025-01-01T12:00:00Z",
            event_type="started",
            step_id="design_phase",
            agent_role="architect",
            correlation_id="arch-001"
        )

        monitor.emit(event)

        assert monitor.events[0].event_type == "started"
        assert monitor.events[0].step_id == "design_phase"

    def test_emit_completed_event(self, monitor):
        """Test emitting a completed event with duration."""
        event = ExecutionEvent(
            timestamp="2025-01-01T12:00:30Z",
            event_type="completed",
            step_id="implementation",
            agent_role="coder",
            correlation_id="code-001",
            duration_ms=30000
        )

        monitor.emit(event)

        assert monitor.events[0].event_type == "completed"
        assert monitor.events[0].duration_ms == 30000

    def test_emit_failed_event(self, monitor):
        """Test emitting a failed event with error."""
        event = ExecutionEvent(
            timestamp="2025-01-01T12:00:10Z",
            event_type="failed",
            step_id="testing",
            agent_role="tester",
            correlation_id="test-001",
            duration_ms=10000,
            error="Test suite failed: 3 tests failed"
        )

        monitor.emit(event)

        assert monitor.events[0].event_type == "failed"
        assert monitor.events[0].error is not None
        assert "failed" in monitor.events[0].error

    def test_emit_checkpoint_event(self, monitor):
        """Test emitting a checkpoint event."""
        event = ExecutionEvent(
            timestamp="2025-01-01T12:01:00Z",
            event_type="checkpoint",
            step_id="stage_1_checkpoint",
            agent_role="orchestrator",
            correlation_id="orch-001",
            metadata={"checkpoint_type": "validation", "state_saved": True}
        )

        monitor.emit(event)

        assert monitor.events[0].event_type == "checkpoint"
        assert monitor.events[0].metadata["checkpoint_type"] == "validation"

    def test_emit_event_with_metadata(self, monitor):
        """Test emitting event with custom metadata."""
        event = ExecutionEvent(
            timestamp="2025-01-01T12:00:00Z",
            event_type="started",
            step_id="step_1",
            agent_role="executor",
            correlation_id="corr-001",
            metadata={
                "tokens_allocated": 4000,
                "priority": "high",
                "retries_allowed": 3
            }
        )

        monitor.emit(event)

        assert monitor.events[0].metadata["tokens_allocated"] == 4000
        assert monitor.events[0].metadata["priority"] == "high"

    def test_get_metrics_empty_monitor(self, monitor):
        """Test metrics on empty monitor."""
        metrics = monitor.get_metrics()

        assert metrics["total_events"] == 0
        assert metrics["completed_steps"] == 0
        assert metrics["failed_steps"] == 0
        assert metrics["success_rate"] == 0.0
        assert metrics["avg_duration_ms"] == 0.0

    def test_get_metrics_only_started_events(self, monitor):
        """Test metrics with only started events."""
        events = [
            ExecutionEvent(
                timestamp="2025-01-01T12:00:00Z",
                event_type="started",
                step_id=f"step_{i}",
                agent_role="executor",
                correlation_id=f"corr-{i:03d}"
            )
            for i in range(3)
        ]

        for event in events:
            monitor.emit(event)

        metrics = monitor.get_metrics()

        assert metrics["total_events"] == 3
        assert metrics["completed_steps"] == 0
        assert metrics["failed_steps"] == 0

    def test_get_metrics_with_completed(self, monitor):
        """Test metrics with completed events."""
        events = [
            ExecutionEvent(
                timestamp="2025-01-01T12:00:00Z",
                event_type="started",
                step_id="step_1",
                agent_role="executor",
                correlation_id="corr-001"
            ),
            ExecutionEvent(
                timestamp="2025-01-01T12:00:10Z",
                event_type="completed",
                step_id="step_1",
                agent_role="executor",
                correlation_id="corr-001",
                duration_ms=10000
            ),
            ExecutionEvent(
                timestamp="2025-01-01T12:00:15Z",
                event_type="completed",
                step_id="step_2",
                agent_role="tester",
                correlation_id="corr-002",
                duration_ms=5000
            ),
        ]

        for event in events:
            monitor.emit(event)

        metrics = monitor.get_metrics()

        assert metrics["total_events"] == 3
        assert metrics["completed_steps"] == 2
        assert metrics["failed_steps"] == 0
        assert metrics["success_rate"] == pytest.approx(2/3, rel=1e-2)
        assert metrics["avg_duration_ms"] == pytest.approx(7500.0, rel=1e-2)

    def test_get_metrics_with_failures(self, monitor):
        """Test metrics with failed events."""
        events = [
            ExecutionEvent(
                timestamp="2025-01-01T12:00:00Z",
                event_type="started",
                step_id="step_1",
                agent_role="executor",
                correlation_id="corr-001"
            ),
            ExecutionEvent(
                timestamp="2025-01-01T12:00:05Z",
                event_type="completed",
                step_id="step_1",
                agent_role="executor",
                correlation_id="corr-001",
                duration_ms=5000
            ),
            ExecutionEvent(
                timestamp="2025-01-01T12:00:10Z",
                event_type="started",
                step_id="step_2",
                agent_role="tester",
                correlation_id="corr-002"
            ),
            ExecutionEvent(
                timestamp="2025-01-01T12:00:15Z",
                event_type="failed",
                step_id="step_2",
                agent_role="tester",
                correlation_id="corr-002",
                duration_ms=5000,
                error="Test failed"
            ),
        ]

        for event in events:
            monitor.emit(event)

        metrics = monitor.get_metrics()

        assert metrics["total_events"] == 4
        assert metrics["completed_steps"] == 1
        assert metrics["failed_steps"] == 1
        assert metrics["success_rate"] == pytest.approx(0.25, rel=1e-2)

    def test_get_metrics_duration_calculation(self, monitor):
        """Test average duration calculation."""
        events = [
            ExecutionEvent(
                timestamp="2025-01-01T12:00:00Z",
                event_type="completed",
                step_id="step_1",
                agent_role="executor",
                correlation_id="corr-001",
                duration_ms=1000
            ),
            ExecutionEvent(
                timestamp="2025-01-01T12:00:01Z",
                event_type="completed",
                step_id="step_2",
                agent_role="executor",
                correlation_id="corr-002",
                duration_ms=2000
            ),
            ExecutionEvent(
                timestamp="2025-01-01T12:00:03Z",
                event_type="completed",
                step_id="step_3",
                agent_role="executor",
                correlation_id="corr-003",
                duration_ms=3000
            ),
        ]

        for event in events:
            monitor.emit(event)

        metrics = monitor.get_metrics()

        # Average should be (1000 + 2000 + 3000) / 3 = 2000
        assert metrics["avg_duration_ms"] == 2000.0

    def test_get_metrics_with_none_durations(self, monitor):
        """Test metrics calculation handles None durations."""
        events = [
            ExecutionEvent(
                timestamp="2025-01-01T12:00:00Z",
                event_type="completed",
                step_id="step_1",
                agent_role="executor",
                correlation_id="corr-001",
                duration_ms=1000
            ),
            ExecutionEvent(
                timestamp="2025-01-01T12:00:01Z",
                event_type="completed",
                step_id="step_2",
                agent_role="executor",
                correlation_id="corr-002",
                duration_ms=None  # No duration
            ),
        ]

        for event in events:
            monitor.emit(event)

        metrics = monitor.get_metrics()

        # Average should be 1000 / 2 = 500 (None treated as 0)
        assert metrics["avg_duration_ms"] == 500.0

    def test_events_ordering(self, monitor):
        """Test events maintain insertion order."""
        for i in range(5):
            event = ExecutionEvent(
                timestamp=f"2025-01-01T12:00:{i:02d}Z",
                event_type="started",
                step_id=f"step_{i}",
                agent_role="executor",
                correlation_id=f"corr-{i:03d}"
            )
            monitor.emit(event)

        # Verify order is maintained
        for i, event in enumerate(monitor.events):
            assert event.step_id == f"step_{i}"

    def test_monitor_preserves_event_data(self, monitor):
        """Test monitor doesn't modify events."""
        original_event = ExecutionEvent(
            timestamp="2025-01-01T12:00:00Z",
            event_type="completed",
            step_id="step_1",
            agent_role="architect",
            correlation_id="corr-001",
            duration_ms=5000,
            error=None,
            metadata={"key": "value"}
        )

        monitor.emit(original_event)
        stored_event = monitor.events[0]

        assert stored_event.timestamp == original_event.timestamp
        assert stored_event.agent_role == original_event.agent_role
        assert stored_event.metadata == original_event.metadata


# =============================================================================
# PLANNER AGENT HELPER METHODS TESTS
# =============================================================================

class TestPlannerAgentHelperMethods:
    """Tests for PlannerAgent helper methods."""

    @pytest.fixture
    def mock_llm(self):
        """Create mock LLM client."""
        client = MagicMock()
        client.generate = AsyncMock(return_value=json.dumps({
            "goal": "Test goal",
            "strategy_overview": "Test strategy",
            "sops": []
        }))
        return client

    @pytest.fixture
    def mock_mcp(self):
        """Create mock MCP client."""
        return MagicMock()

    @pytest.fixture
    def planner(self, mock_llm, mock_mcp):
        """Create PlannerAgent instance."""
        return PlannerAgent(
            llm_client=mock_llm,
            mcp_client=mock_mcp
        )

    # Tests for _infer_stage_name()
    def test_infer_stage_name_single_role(self, planner):
        """Test stage name inference with single role."""
        steps = [
            SOPStep(
                id="s1", role="architect", action="design",
                objective="Design", definition_of_done="Done"
            ),
            SOPStep(
                id="s2", role="architect", action="document",
                objective="Document", definition_of_done="Done"
            ),
        ]

        name = planner._infer_stage_name(steps)

        assert "Architect" in name
        assert "Phase" in name

    def test_infer_stage_name_multiple_roles(self, planner):
        """Test stage name inference with multiple roles."""
        steps = [
            SOPStep(
                id="s1", role="architect", action="design",
                objective="Design", definition_of_done="Done"
            ),
            SOPStep(
                id="s2", role="coder", action="implement",
                objective="Implement", definition_of_done="Done"
            ),
            SOPStep(
                id="s3", role="tester", action="test",
                objective="Test", definition_of_done="Done"
            ),
        ]

        name = planner._infer_stage_name(steps)

        assert "Multi-Agent" in name

    def test_infer_stage_name_single_step(self, planner):
        """Test stage name with single step."""
        steps = [
            SOPStep(
                id="s1", role="security", action="audit",
                objective="Audit", definition_of_done="Done"
            ),
        ]

        name = planner._infer_stage_name(steps)

        assert "Security" in name
        assert "Phase" in name

    def test_infer_stage_name_case_conversion(self, planner):
        """Test role name is properly titlecased."""
        steps = [
            SOPStep(
                id="s1", role="documenter", action="doc",
                objective="Doc", definition_of_done="Done"
            ),
        ]

        name = planner._infer_stage_name(steps)

        # Should convert "documenter" to "Documenter Phase"
        assert "Documenter" in name

    # Tests for _assess_risk()
    def test_assess_risk_low(self, planner):
        """Test risk assessment returns LOW for simple plans with security."""
        sops = [
            SOPStep(
                id="s1", role="executor", action="task",
                objective="Do task", definition_of_done="Done",
                priority=AgentPriority.LOW, cost=1.0
            ),
            SOPStep(
                id="s2", role="security", action="audit",
                objective="Audit", definition_of_done="Done",
                priority=AgentPriority.MEDIUM, cost=2.0
            ),
        ]

        risk = planner._assess_risk(sops)

        assert risk == "LOW"

    def test_assess_risk_medium_based_on_cost(self, planner):
        """Test risk assessment returns MEDIUM for moderate cost with security."""
        sops = [
            SOPStep(
                id=f"s{i}", role="executor", action="task",
                objective="Task", definition_of_done="Done",
                priority=AgentPriority.MEDIUM, cost=8.0
            )
            for i in range(2)
        ] + [
            SOPStep(
                id="s_sec", role="security", action="audit",
                objective="Audit", definition_of_done="Done",
                priority=AgentPriority.MEDIUM, cost=6.0
            )
        ]

        risk = planner._assess_risk(sops)

        assert risk == "MEDIUM"

    def test_assess_risk_medium_based_on_critical_count(self, planner):
        """Test risk assessment returns MEDIUM for critical steps with security."""
        sops = [
            SOPStep(
                id="s1", role="executor", action="task",
                objective="Task", definition_of_done="Done",
                priority=AgentPriority.CRITICAL, cost=1.0
            ),
            SOPStep(
                id="s2", role="executor", action="task",
                objective="Task", definition_of_done="Done",
                priority=AgentPriority.CRITICAL, cost=1.0
            ),
            SOPStep(
                id="s3", role="executor", action="task",
                objective="Task", definition_of_done="Done",
                priority=AgentPriority.CRITICAL, cost=1.0
            ),
            SOPStep(
                id="s_sec", role="security", action="audit",
                objective="Audit", definition_of_done="Done",
                priority=AgentPriority.MEDIUM, cost=1.0
            ),
        ]

        risk = planner._assess_risk(sops)

        assert risk == "MEDIUM"

    def test_assess_risk_high_many_critical(self, planner):
        """Test risk assessment returns HIGH with many critical steps."""
        sops = [
            SOPStep(
                id=f"s{i}", role="executor", action="task",
                objective="Task", definition_of_done="Done",
                priority=AgentPriority.CRITICAL, cost=5.0
            )
            for i in range(6)
        ]

        risk = planner._assess_risk(sops)

        assert risk == "HIGH"

    def test_assess_risk_high_high_cost(self, planner):
        """Test risk assessment returns HIGH with high total cost."""
        sops = [
            SOPStep(
                id=f"s{i}", role="executor", action="task",
                objective="Task", definition_of_done="Done",
                priority=AgentPriority.MEDIUM, cost=10.0
            )
            for i in range(6)  # Total cost: 60
        ]

        risk = planner._assess_risk(sops)

        assert risk == "HIGH"

    def test_assess_risk_high_no_security(self, planner):
        """Test risk assessment returns HIGH when no security steps."""
        sops = [
            SOPStep(
                id="s1", role="architect", action="design",
                objective="Task", definition_of_done="Done",
                priority=AgentPriority.CRITICAL, cost=1.0
            ),
            SOPStep(
                id="s2", role="coder", action="code",
                objective="Task", definition_of_done="Done",
                priority=AgentPriority.CRITICAL, cost=1.0
            ),
            SOPStep(
                id="s3", role="coder", action="code",
                objective="Task", definition_of_done="Done",
                priority=AgentPriority.CRITICAL, cost=1.0
            ),
            SOPStep(
                id="s4", role="coder", action="code",
                objective="Task", definition_of_done="Done",
                priority=AgentPriority.CRITICAL, cost=1.0
            ),
            SOPStep(
                id="s5", role="coder", action="code",
                objective="Task", definition_of_done="Done",
                priority=AgentPriority.CRITICAL, cost=1.0
            ),
            SOPStep(
                id="s6", role="tester", action="test",
                objective="Task", definition_of_done="Done",
                priority=AgentPriority.CRITICAL, cost=1.0
            ),
        ]

        risk = planner._assess_risk(sops)

        assert risk == "HIGH"

    # Tests for _load_team_standards()
    @pytest.mark.asyncio
    async def test_load_team_standards_file_exists(self, planner):
        """Test loading team standards when CLAUDE.md exists."""
        with patch.object(planner, '_execute_tool') as mock_tool:
            mock_tool.return_value = {
                "success": True,
                "content": "# CLAUDE.md\nTeam standards..."
            }

            standards = await planner._load_team_standards()

            assert "claude_md" in standards
            assert "Team standards" in standards["claude_md"]
            mock_tool.assert_called_once()

    @pytest.mark.asyncio
    async def test_load_team_standards_file_not_found(self, planner):
        """Test loading standards when CLAUDE.md doesn't exist."""
        with patch.object(planner, '_execute_tool') as mock_tool:
            mock_tool.side_effect = FileNotFoundError("CLAUDE.md not found")

            standards = await planner._load_team_standards()

            assert standards == {}

    @pytest.mark.asyncio
    async def test_load_team_standards_execute_tool_error(self, planner):
        """Test handling of execute_tool errors."""
        with patch.object(planner, '_execute_tool') as mock_tool:
            mock_tool.side_effect = Exception("Tool execution failed")

            standards = await planner._load_team_standards()

            assert standards == {}

    @pytest.mark.asyncio
    async def test_load_team_standards_empty_content(self, planner):
        """Test handling of empty CLAUDE.md content."""
        with patch.object(planner, '_execute_tool') as mock_tool:
            mock_tool.return_value = {
                "success": True,
                "content": ""
            }

            standards = await planner._load_team_standards()

            assert "claude_md" in standards
            assert standards["claude_md"] == ""

    @pytest.mark.asyncio
    async def test_load_team_standards_partial_content(self, planner):
        """Test loading standards with partial result."""
        with patch.object(planner, '_execute_tool') as mock_tool:
            mock_tool.return_value = {
                "success": True
                # Missing "content" key
            }

            standards = await planner._load_team_standards()

            assert "claude_md" in standards
            assert standards["claude_md"] == ""


# =============================================================================
# PLANNER AGENT ADDITIONAL HELPER TESTS
# =============================================================================

class TestPlannerAgentAdditionalHelpers:
    """Tests for additional PlannerAgent helper methods."""

    @pytest.fixture
    def mock_llm(self):
        """Create mock LLM client."""
        client = MagicMock()
        client.generate = AsyncMock(return_value="{}")
        return client

    @pytest.fixture
    def mock_mcp(self):
        """Create mock MCP client."""
        return MagicMock()

    @pytest.fixture
    def planner(self, mock_llm, mock_mcp):
        """Create PlannerAgent instance."""
        return PlannerAgent(
            llm_client=mock_llm,
            mcp_client=mock_mcp
        )

    def test_generate_stage_description_single_step(self, planner):
        """Test stage description generation for single step."""
        steps = [
            SOPStep(
                id="s1", role="architect", action="design system",
                objective="Create architecture", definition_of_done="Done"
            ),
        ]

        description = planner._generate_stage_description(steps)

        assert description == "Create architecture"

    def test_generate_stage_description_multiple_steps(self, planner):
        """Test stage description generation for multiple steps."""
        steps = [
            SOPStep(
                id="s1", role="coder", action="implement feature",
                objective="Write code", definition_of_done="Done"
            ),
            SOPStep(
                id="s2", role="tester", action="write tests",
                objective="Test code", definition_of_done="Done"
            ),
            SOPStep(
                id="s3", role="reviewer", action="review code",
                objective="Review", definition_of_done="Done"
            ),
        ]

        description = planner._generate_stage_description(steps)

        assert "Parallel execution" in description
        assert "3 tasks" in description

    def test_calculate_max_parallel_empty(self, planner):
        """Test max parallel calculation with no groups."""
        max_p = planner._calculate_max_parallel([])

        assert max_p == 1

    def test_calculate_max_parallel_single_groups(self, planner):
        """Test max parallel with single-step groups."""
        groups = [["s1"], ["s2"], ["s3"]]

        max_p = planner._calculate_max_parallel(groups)

        assert max_p == 1

    def test_calculate_max_parallel_mixed_groups(self, planner):
        """Test max parallel with mixed group sizes."""
        groups = [["s1"], ["s2", "s3"], ["s4", "s5", "s6"]]

        max_p = planner._calculate_max_parallel(groups)

        assert max_p == 3

    def test_generate_strategy_overview_sequential(self, planner):
        """Test strategy overview for sequential stages."""
        stages = [
            ExecutionStage(
                name="Stage 1", description="First",
                steps=[], strategy=ExecutionStrategy.SEQUENTIAL
            ),
            ExecutionStage(
                name="Stage 2", description="Second",
                steps=[], strategy=ExecutionStrategy.SEQUENTIAL
            ),
        ]

        overview = planner._generate_strategy_overview(stages)

        assert "2 stages" in overview
        # When no parallel stages, the "X stages use parallel" message is not included
        assert "parallel" not in overview or "0 stages" not in overview

    def test_generate_strategy_overview_with_parallel(self, planner):
        """Test strategy overview with parallel stages."""
        stages = [
            ExecutionStage(
                name="Stage 1", description="First",
                steps=[], strategy=ExecutionStrategy.PARALLEL
            ),
            ExecutionStage(
                name="Stage 2", description="Second",
                steps=[], strategy=ExecutionStrategy.SEQUENTIAL
            ),
            ExecutionStage(
                name="Stage 3", description="Third",
                steps=[], strategy=ExecutionStrategy.PARALLEL
            ),
        ]

        overview = planner._generate_strategy_overview(stages)

        assert "3 stages" in overview
        assert "2 stages use parallel" in overview

    def test_estimate_duration_low_cost(self, planner):
        """Test duration estimation for low cost."""
        sops = [
            SOPStep(
                id="s1", role="r", action="a",
                objective="o", definition_of_done="d",
                cost=1.0, dependencies=[]
            ),
        ]

        duration = planner._estimate_duration(sops, [["s1"]])

        assert "< 10 minutes" in duration or "<" in duration

    def test_estimate_duration_medium_cost(self, planner):
        """Test duration estimation for medium cost."""
        sops = [
            SOPStep(
                id=f"s{i}", role="r", action="a",
                objective="o", definition_of_done="d",
                cost=2.0, dependencies=[] if i == 0 else [f"s{i-1}"]
            )
            for i in range(4)
        ]

        duration = planner._estimate_duration(sops, [["s0"], ["s1"], ["s2"], ["s3"]])

        assert "10-30" in duration or "10" in duration or "30" in duration

    def test_estimate_duration_high_cost(self, planner):
        """Test duration estimation for high cost."""
        sops = [
            SOPStep(
                id=f"s{i}", role="r", action="a",
                objective="o", definition_of_done="d",
                cost=5.0, dependencies=[] if i == 0 else [f"s{i-1}"]
            )
            for i in range(5)
        ]

        duration = planner._estimate_duration(sops, [["s0"], ["s1"], ["s2"], ["s3"], ["s4"]])

        assert "hour" in duration.lower() or "60" in duration

    def test_identify_checkpoints_none(self, planner):
        """Test identifying checkpoints when none exist."""
        stages = [
            ExecutionStage(
                name="Stage 1", description="First",
                steps=[], checkpoint=False
            ),
            ExecutionStage(
                name="Stage 2", description="Second",
                steps=[], checkpoint=False
            ),
        ]

        checkpoints = planner._identify_checkpoints(stages)

        assert checkpoints == []

    def test_identify_checkpoints_multiple(self, planner):
        """Test identifying multiple checkpoints."""
        stages = [
            ExecutionStage(
                name="Design Stage", description="Design",
                steps=[], checkpoint=True
            ),
            ExecutionStage(
                name="Implementation Stage", description="Code",
                steps=[], checkpoint=False
            ),
            ExecutionStage(
                name="Testing Stage", description="Test",
                steps=[], checkpoint=True
            ),
        ]

        checkpoints = planner._identify_checkpoints(stages)

        assert len(checkpoints) == 2
        assert "Design Stage" in checkpoints
        assert "Testing Stage" in checkpoints


# =============================================================================
# EXECUTION MONITOR INTEGRATION TESTS
# =============================================================================

class TestExecutionMonitorIntegration:
    """Integration tests for ExecutionMonitor with PlannerAgent."""

    def test_monitor_full_execution_lifecycle(self):
        """Test complete execution lifecycle tracking."""
        monitor = ExecutionMonitor()

        # Simulate step execution lifecycle
        timeline = [
            ("2025-01-01T12:00:00Z", "started", "step_1", "architect"),
            ("2025-01-01T12:00:15Z", "completed", "step_1", "architect"),
            ("2025-01-01T12:00:16Z", "started", "step_2", "coder"),
            ("2025-01-01T12:01:00Z", "completed", "step_2", "coder"),
            ("2025-01-01T12:01:01Z", "started", "step_3", "tester"),
            ("2025-01-01T12:01:30Z", "completed", "step_3", "tester"),
        ]

        for ts, event_type, step_id, role in timeline:
            duration_ms = None
            if event_type == "completed":
                # Calculate duration from previous event
                pass

            event = ExecutionEvent(
                timestamp=ts,
                event_type=event_type,
                step_id=step_id,
                agent_role=role,
                correlation_id=f"{step_id}-corr",
                duration_ms=15000 if event_type == "completed" else None
            )
            monitor.emit(event)

        metrics = monitor.get_metrics()

        assert metrics["total_events"] == 6
        assert metrics["completed_steps"] == 3
        assert metrics["failed_steps"] == 0

    def test_monitor_with_failures(self):
        """Test monitoring execution with failures."""
        monitor = ExecutionMonitor()

        events = [
            ExecutionEvent(
                timestamp="2025-01-01T12:00:00Z",
                event_type="started",
                step_id="step_1",
                agent_role="executor",
                correlation_id="corr-1"
            ),
            ExecutionEvent(
                timestamp="2025-01-01T12:00:05Z",
                event_type="completed",
                step_id="step_1",
                agent_role="executor",
                correlation_id="corr-1",
                duration_ms=5000
            ),
            ExecutionEvent(
                timestamp="2025-01-01T12:00:06Z",
                event_type="started",
                step_id="step_2",
                agent_role="executor",
                correlation_id="corr-2"
            ),
            ExecutionEvent(
                timestamp="2025-01-01T12:00:10Z",
                event_type="failed",
                step_id="step_2",
                agent_role="executor",
                correlation_id="corr-2",
                duration_ms=4000,
                error="Timeout exceeded"
            ),
            ExecutionEvent(
                timestamp="2025-01-01T12:00:11Z",
                event_type="started",
                step_id="step_2_retry",
                agent_role="executor",
                correlation_id="corr-2-retry"
            ),
            ExecutionEvent(
                timestamp="2025-01-01T12:00:20Z",
                event_type="completed",
                step_id="step_2_retry",
                agent_role="executor",
                correlation_id="corr-2-retry",
                duration_ms=9000
            ),
        ]

        for event in events:
            monitor.emit(event)

        metrics = monitor.get_metrics()

        assert metrics["total_events"] == 6
        assert metrics["completed_steps"] == 2
        assert metrics["failed_steps"] == 1
        assert metrics["success_rate"] == pytest.approx(1/3, rel=1e-2)

    def test_monitor_metrics_consistency(self):
        """Test metrics remain consistent across multiple calls."""
        monitor = ExecutionMonitor()

        events = [
            ExecutionEvent(
                timestamp=f"2025-01-01T12:00:{i:02d}Z",
                event_type="completed" if i % 2 == 0 else "failed",
                step_id=f"step_{i}",
                agent_role="executor",
                correlation_id=f"corr-{i}",
                duration_ms=1000 * (i + 1),
                error="Failed" if i % 2 == 1 else None
            )
            for i in range(6)
        ]

        for event in events:
            monitor.emit(event)

        metrics1 = monitor.get_metrics()
        metrics2 = monitor.get_metrics()
        metrics3 = monitor.get_metrics()

        # Metrics should be identical across calls
        assert metrics1 == metrics2
        assert metrics2 == metrics3

    def test_monitor_event_filtering(self):
        """Test filtering events by type."""
        monitor = ExecutionMonitor()

        events = [
            ExecutionEvent(
                timestamp="2025-01-01T12:00:00Z",
                event_type="started",
                step_id="step_1",
                agent_role="executor",
                correlation_id="corr-1"
            ),
            ExecutionEvent(
                timestamp="2025-01-01T12:00:01Z",
                event_type="completed",
                step_id="step_1",
                agent_role="executor",
                correlation_id="corr-1",
                duration_ms=1000
            ),
            ExecutionEvent(
                timestamp="2025-01-01T12:00:02Z",
                event_type="checkpoint",
                step_id="checkpoint_1",
                agent_role="orchestrator",
                correlation_id="chk-1"
            ),
        ]

        for event in events:
            monitor.emit(event)

        completed = [e for e in monitor.events if e.event_type == "completed"]
        started = [e for e in monitor.events if e.event_type == "started"]
        checkpoints = [e for e in monitor.events if e.event_type == "checkpoint"]

        assert len(completed) == 1
        assert len(started) == 1
        assert len(checkpoints) == 1
        assert len(monitor.events) == 3
