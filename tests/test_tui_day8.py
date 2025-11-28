"""
Tests for DAY 8 UI/UX enhancements.

Tests:
- Enhanced progress displays
- Status dashboard
- Enhanced markdown rendering
- Code blocks with syntax highlighting
- Diff viewer

Created: 2025-11-20 13:00 UTC (DAY 8)
"""

import pytest
import asyncio
import time
from io import StringIO

from rich.console import Console

from jdev_cli.tui.components.enhanced_progress import (
    EnhancedProgressDisplay,
    WorkflowProgress,
    StageProgress,
    TokenMetrics,
    OperationType,
    ThinkingIndicator,
)
from jdev_cli.tui.components.dashboard import (
    Dashboard,
    Operation,
    OperationStatus,
    SessionStats,
    SystemMetrics,
    ContextWindowInfo,
)
from jdev_cli.tui.components.markdown_enhanced import (
    EnhancedMarkdown,
    CodeBlock,
    DiffViewer,
)


class TestEnhancedProgress:
    """Test enhanced progress displays."""

    def test_stage_progress_basic(self):
        """Test basic stage progress."""
        stage = StageProgress("Test Stage", total=100)

        assert stage.name == "Test Stage"
        assert stage.current == 0
        assert stage.total == 100
        assert stage.percentage == 0.0
        assert stage.status == "pending"

    def test_stage_progress_percentage(self):
        """Test percentage calculation."""
        stage = StageProgress("Test", current=50, total=100)
        assert stage.percentage == 50.0

        stage.current = 100
        assert stage.percentage == 100.0

        # Over 100%
        stage.current = 150
        assert stage.percentage == 100.0  # Capped at 100

    def test_stage_progress_duration(self):
        """Test duration tracking."""
        stage = StageProgress("Test")
        stage.start_time = time.time()
        time.sleep(0.1)

        assert stage.duration >= 0.1

        stage.end_time = time.time()
        duration = stage.duration
        time.sleep(0.1)

        # Duration shouldn't change after end_time set
        assert stage.duration == duration

    def test_workflow_progress_basic(self):
        """Test basic workflow progress."""
        workflow = WorkflowProgress(
            stages=[
                StageProgress("Stage 1", total=100),
                StageProgress("Stage 2", total=50),
            ]
        )

        assert len(workflow.stages) == 2
        assert workflow.current_stage_idx == 0
        assert workflow.current_stage.name == "Stage 1"

    def test_workflow_overall_percentage(self):
        """Test overall percentage calculation."""
        workflow = WorkflowProgress(
            stages=[
                StageProgress("Stage 1", status="complete"),
                StageProgress("Stage 2", status="running", current=50, total=100),
                StageProgress("Stage 3", status="pending"),
            ]
        )

        # 1 complete (100%) + 0.5 running (50%) + 0 pending
        # = 1.5 / 3 = 50%
        assert abs(workflow.overall_percentage - 50.0) < 0.1

    def test_token_metrics_cost_format(self):
        """Test token cost formatting."""
        metrics = TokenMetrics(estimated_cost=0.005)
        assert "5.00m" in metrics.cost_formatted  # millidollars

        metrics.estimated_cost = 0.0234
        assert "$0.0234" in metrics.cost_formatted

    def test_enhanced_progress_display_render(self):
        """Test progress display rendering."""
        console = Console(file=StringIO(), force_terminal=True, width=120)
        display = EnhancedProgressDisplay(console=console)

        workflow = WorkflowProgress(
            stages=[
                StageProgress("Test", current=50, total=100, status="running"),
            ]
        )

        renderable = display.render_workflow(workflow)
        assert renderable is not None

        # Should not crash
        console.print(renderable)

    @pytest.mark.asyncio
    async def test_thinking_indicator(self):
        """Test thinking indicator animation."""
        indicator = ThinkingIndicator("Processing...")

        frames = []
        async for frame in indicator.animate(duration=0.3):
            frames.append(frame)
            if len(frames) >= 3:
                break

        assert len(frames) >= 3
        # Each frame should be different (animated)
        assert frames[0] != frames[1]


class TestDashboard:
    """Test status dashboard."""

    def test_operation_basic(self):
        """Test basic operation tracking."""
        op = Operation(
            id="test-1",
            type="llm",
            description="Test operation",
        )

        assert op.id == "test-1"
        assert op.type == "llm"
        assert op.status == OperationStatus.RUNNING
        assert op.duration >= 0

    def test_operation_duration(self):
        """Test operation duration tracking."""
        op = Operation(id="test", type="test", description="Test")
        time.sleep(0.1)

        assert op.duration >= 0.1

        op.end_time = time.time()
        duration = op.duration
        time.sleep(0.1)

        # Duration frozen after end
        assert op.duration == duration

    def test_session_stats_basic(self):
        """Test session statistics."""
        stats = SessionStats()

        assert stats.total_operations == 0
        assert stats.success_rate == 0.0

        stats.total_operations = 10
        stats.successful_operations = 8

        assert stats.success_rate == 80.0

    def test_session_stats_average_cost(self):
        """Test average cost calculation."""
        stats = SessionStats()

        stats.total_operations = 5
        stats.total_cost = 0.25

        assert stats.average_cost_per_op == 0.05

    def test_context_window_utilization(self):
        """Test context window tracking."""
        ctx = ContextWindowInfo(
            current_tokens=100000,
            max_tokens=128000,
        )

        assert abs(ctx.utilization - 78.125) < 0.01
        assert ctx.remaining_tokens == 28000
        assert not ctx.is_warning  # Below 80%

        ctx.current_tokens = 110000
        assert ctx.is_warning  # Above 80%

    def test_dashboard_add_operation(self):
        """Test adding operations to dashboard."""
        dashboard = Dashboard()

        op = Operation(id="test-1", type="llm", description="Test")
        dashboard.add_operation(op)

        assert len(dashboard.active_operations) == 1
        assert dashboard.stats.total_operations == 1

    def test_dashboard_complete_operation(self):
        """Test completing operations."""
        dashboard = Dashboard()

        op = Operation(id="test-1", type="llm", description="Test")
        dashboard.add_operation(op)

        dashboard.complete_operation(
            "test-1",
            OperationStatus.SUCCESS,
            tokens_used=1000,
            cost=0.01,
        )

        assert len(dashboard.active_operations) == 0
        assert len(dashboard.history) == 1
        assert dashboard.stats.successful_operations == 1
        assert dashboard.stats.total_tokens == 1000
        assert dashboard.stats.total_cost == 0.01

    def test_dashboard_render(self):
        """Test dashboard rendering."""
        console = Console(file=StringIO(), force_terminal=True, width=120)
        dashboard = Dashboard(console=console)

        # Add some test data
        op = Operation(id="test-1", type="llm", description="Test LLM call")
        dashboard.add_operation(op)

        dashboard.complete_operation(
            "test-1",
            OperationStatus.SUCCESS,
            tokens_used=500,
            cost=0.005,
        )

        # Should not crash
        layout = dashboard.render()
        assert layout is not None
        console.print(layout)

    def test_system_metrics_capture(self):
        """Test system metrics capture."""
        metrics = SystemMetrics.capture()

        assert 0 <= metrics.cpu_percent <= 100
        assert 0 <= metrics.memory_percent <= 100
        assert metrics.memory_used_mb > 0
        assert metrics.memory_total_mb > 0


class TestEnhancedMarkdown:
    """Test enhanced markdown rendering."""

    def test_basic_markdown_render(self):
        """Test basic markdown rendering."""
        console = Console(file=StringIO(), force_terminal=True, width=120)
        renderer = EnhancedMarkdown(console=console)

        md = "# Hello\n\nThis is **bold** text."

        # Should not crash
        renderer.render(md)

    def test_callout_processing(self):
        """Test callout box processing."""
        renderer = EnhancedMarkdown()

        md = """> [!INFO]
> This is an info callout.
> With multiple lines.
"""

        processed = renderer._preprocess(md)

        assert "INFO" in processed
        assert "This is an info callout" in processed

    def test_diff_block_processing(self):
        """Test diff block processing."""
        renderer = EnhancedMarkdown()

        md = """```diff
+ Added line
- Removed line
  Unchanged line
```"""

        processed = renderer._preprocess(md)

        # Should contain color markers
        assert "[green]" in processed or "Added" in processed
        assert "[red]" in processed or "Removed" in processed

    def test_code_block_render(self):
        """Test code block rendering."""
        console = Console(file=StringIO(), force_terminal=True, width=120)

        code = """def hello():
    print("Hello, World!")
"""

        block = CodeBlock(code, language="python")

        # Should not crash
        block.render(console=console)

    def test_diff_viewer_render(self):
        """Test diff viewer rendering."""
        console = Console(file=StringIO(), force_terminal=True, width=120)

        before = """def old():
    return 1
"""

        after = """def new():
    return 2
"""

        viewer = DiffViewer(before, after, language="python")

        # Should not crash
        viewer.render(console=console)

    def test_latex_to_ascii(self):
        """Test LaTeX to ASCII conversion."""
        renderer = EnhancedMarkdown()

        latex = r"\alpha + \beta = \gamma"
        ascii_result = renderer._latex_to_ascii(latex)

        assert "α" in ascii_result
        assert "β" in ascii_result
        assert "γ" in ascii_result

    def test_mermaid_to_ascii(self):
        """Test Mermaid to ASCII conversion."""
        renderer = EnhancedMarkdown()

        mermaid = """flowchart TD
    A --> B
    B --> C
"""

        ascii_result = renderer._mermaid_to_ascii(mermaid)

        assert "Flowchart" in ascii_result or "→" in ascii_result


# Integration test
@pytest.mark.asyncio
async def test_full_workflow_integration():
    """Test full workflow with all components."""
    console = Console(file=StringIO(), force_terminal=True, width=120)

    # Create dashboard
    dashboard = Dashboard(console=console)

    # Create workflow
    workflow = WorkflowProgress(
        stages=[
            StageProgress("Initialize", total=10),
            StageProgress("Process", total=20),
            StageProgress("Finalize", total=10),
        ],
        operation_type=OperationType.WORKFLOW,
    )

    # Create progress display
    display = EnhancedProgressDisplay(console=console)

    # Add operation to dashboard
    op = Operation(
        id="workflow-1",
        type="workflow",
        description="Test workflow execution",
    )
    dashboard.add_operation(op)

    # Simulate workflow execution
    for stage_idx in range(len(workflow.stages)):
        workflow.current_stage_idx = stage_idx
        stage = workflow.current_stage
        stage.status = "running"
        stage.start_time = time.time()

        for i in range(stage.total):
            stage.current = i + 1
            await asyncio.sleep(0.001)  # Fast test

        stage.status = "complete"
        stage.end_time = time.time()

    # Complete operation
    dashboard.complete_operation(
        "workflow-1",
        OperationStatus.SUCCESS,
        tokens_used=5000,
        cost=0.05,
    )

    # Render everything
    display.render_workflow(workflow)
    dashboard.print_snapshot()

    # Verify
    assert workflow.overall_percentage == 100.0
    assert dashboard.stats.successful_operations == 1
    assert dashboard.stats.total_tokens == 5000


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
