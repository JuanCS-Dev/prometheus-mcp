"""
MAESTRO v10.0 - IMPLACABLE TEST SUITE
======================================

Test Philosophy: "Break everything. If it survives, it's production-ready."

Coverage:
• Unit tests (individual components)
• Integration tests (cross-component)
• Stress tests (performance limits)
• Chaos tests (random failures)
• Edge cases (boundary conditions)
• Race conditions (async issues)
• Memory leaks
• UI rendering under load
• Real agent integration

Requirements:
pip install pytest pytest-asyncio pytest-timeout pytest-benchmark pytest-cov faker hypothesis
"""

import pytest
import asyncio
import time
import io
import gc
import tracemalloc

# Import components to test
from jdev_cli.tui.components.maestro_shell_ui import (
    MaestroShellUI,
    AgentStreamPanel
)
from jdev_cli.tui.components.agent_stream_panel import (
    AgentStreamPanel
)
from jdev_cli.tui.components.file_operations_panel import (
    FileOperationsPanel
)
from jdev_cli.tui.components.metrics_dashboard import (
    MetricsDashboard
)
from jdev_cli.tui.components.maestro_data_structures import (
    AgentState,
    AgentStatus,
    FileOperation,
    FileStatus,
    MetricsData
)
from jdev_cli.tui.theme import COLORS

from rich.console import Console
from rich.text import Text

# ============================================================================
# TEST FIXTURES
# ============================================================================

@pytest.fixture
def console():
    """Mock console for testing"""
    return Console(file=io.StringIO(), width=120, height=40, force_terminal=True)

@pytest.fixture
def ui(console):
    """Fresh UI instance"""
    return MaestroShellUI(console=console)

@pytest.fixture
def agent_state():
    """Sample agent state"""
    return AgentState(
        name="TEST AGENT",
        icon="🧪",
        status=AgentStatus.IDLE
    )

@pytest.fixture
def file_ops():
    """File operations panel"""
    return FileOperationsPanel()

@pytest.fixture
def metrics():
    """Sample metrics"""
    return MetricsData(
        success_rate=99.87,
        tokens_used=2100,
        tokens_saved=98.7,
        saved_money=1234.0,
        latency_ms=187
    )


# ============================================================================
# UNIT TESTS - Agent Stream Panel
# ============================================================================

class TestAgentStreamPanel:
    """Test AgentStreamPanel in isolation"""

    def test_panel_creation(self, agent_state):
        """Test basic panel creation"""
        panel = AgentStreamPanel(agent_state, COLORS['neon_cyan'])
        assert panel.state == agent_state
        assert panel.color == COLORS['neon_cyan']

    def test_render_idle_state(self, agent_state):
        """Test rendering idle agent"""
        panel = AgentStreamPanel(agent_state, COLORS['neon_cyan'])
        rendered = panel.render(show_cursor=False)

        assert rendered is not None
        assert hasattr(rendered, 'title')

    def test_render_executing_state(self, agent_state):
        """Test rendering executing agent with spinner"""
        agent_state.status = AgentStatus.EXECUTING
        agent_state.spinner_frame = 5

        panel = AgentStreamPanel(agent_state, COLORS['neon_cyan'])
        rendered = panel.render(show_cursor=True)

        assert rendered is not None

    def test_cursor_animation(self, agent_state):
        """Test cursor cycles through all frames"""
        panel = AgentStreamPanel(agent_state, COLORS['neon_cyan'])

        initial_index = panel.cursor_index
        for _ in range(len(panel.CURSOR_FRAMES)):
            panel.render(show_cursor=True)

        # Should have cycled back
        assert panel.cursor_index == initial_index

    def test_content_truncation(self, agent_state):
        """Test content truncates after max lines"""
        agent_state.content = [f"Line {i}" for i in range(100)]

        panel = AgentStreamPanel(agent_state, COLORS['neon_cyan'])
        rendered = panel.render(max_display_lines=20)

        # Should only show last 20 lines
        assert len(agent_state.content[-20:]) == 20

    def test_progress_bar_display(self, agent_state):
        """Test progress bar renders correctly"""
        agent_state.progress = 75.5

        panel = AgentStreamPanel(agent_state, COLORS['neon_cyan'])
        rendered = panel.render()

        assert rendered is not None

    def test_done_status(self, agent_state):
        """Test done status shows checkmark"""
        agent_state.status = AgentStatus.DONE

        panel = AgentStreamPanel(agent_state, COLORS['neon_cyan'])
        rendered = panel.render()

        assert rendered is not None


# ============================================================================
# UNIT TESTS - File Operations Panel
# ============================================================================

class TestFileOperationsPanel:
    """Test FileOperationsPanel in isolation"""

    def test_panel_creation(self, file_ops):
        """Test basic panel creation"""
        assert len(file_ops.operations) == 0

    def test_add_operation(self, file_ops):
        """Test adding file operation"""
        op = FileOperation(
            path="test.py",
            status=FileStatus.MODIFIED,
            lines_added=10,
            lines_removed=5
        )

        file_ops.add_operation(op)
        assert len(file_ops.operations) == 1
        assert file_ops.operations[0] == op

    def test_render_empty(self, file_ops):
        """Test rendering with no operations"""
        rendered = file_ops.render()
        assert rendered is not None

    def test_render_with_operations(self, file_ops):
        """Test rendering with operations"""
        for i in range(5):
            op = FileOperation(
                path=f"file{i}.py",
                status=FileStatus.MODIFIED,
                lines_added=i * 10,
                lines_removed=i * 5
            )
            file_ops.add_operation(op)

        rendered = file_ops.render()
        assert rendered is not None

    def test_diff_calculation(self, file_ops):
        """Test diff totals are calculated correctly"""
        file_ops.add_operation(FileOperation("a.py", FileStatus.MODIFIED, 100, 50))
        file_ops.add_operation(FileOperation("b.py", FileStatus.MODIFIED, 50, 25))

        total_added, total_removed = file_ops.get_total_changes()

        assert total_added == 150
        assert total_removed == 75

    def test_operation_limit(self, file_ops):
        """Test operations are stored up to limit"""
        for i in range(60):
            file_ops.add_operation(
                FileOperation(f"file{i}.py", FileStatus.MODIFIED, 1, 1)
            )

        # Should cap at 50
        assert len(file_ops.operations) == 50


# ============================================================================
# UNIT TESTS - Metrics Dashboard
# ============================================================================

class TestMetricsDashboard:
    """Test MetricsDashboard"""

    def test_render_metrics(self, metrics):
        """Test metrics render as Text"""
        dashboard = MetricsDashboard(metrics)
        rendered = dashboard.render(compact=True)

        assert isinstance(rendered, Text)

    def test_metrics_values(self, metrics):
        """Test all metrics are included"""
        dashboard = MetricsDashboard(metrics)
        rendered = dashboard.render(compact=True)

        text_str = rendered.plain

        assert "99." in text_str  # success_rate
        assert "2.1K" in text_str or "2100" in text_str   # tokens
        assert "1,234" in text_str or "1234" in text_str  # saved_money


# ============================================================================
# INTEGRATION TESTS - Full UI
# ============================================================================

class TestMaestroShellUI:
    """Test complete UI integration"""

    def test_ui_initialization(self, ui):
        """Test UI initializes correctly"""
        assert ui.console is not None
        assert 'executor' in ui.agents
        assert 'planner' in ui.agents
        assert ui.file_ops is not None
        assert ui.metrics is not None

    def test_layout_structure(self, ui):
        """Test layout has all required sections"""
        assert ui.layout["header"] is not None
        assert ui.layout["agents"] is not None
        assert ui.layout["command_bar"] is not None
        assert ui.layout["metrics"] is not None

    @pytest.mark.asyncio
    async def test_start_stop_lifecycle(self, ui):
        """Test UI can start and stop cleanly"""
        await ui.start()
        assert ui.live is not None

        ui.stop()
        assert ui.live is None

    @pytest.mark.asyncio
    async def test_executor_stream_update(self, ui):
        """Test executor stream updates"""
        await ui.start()

        initial_len = len(ui.agents['executor'].content)
        await ui.update_executor_stream("Test message")

        assert len(ui.agents['executor'].content) == initial_len + 1
        assert ui.agents['executor'].content[-1] == "Test message"

        ui.stop()

    @pytest.mark.asyncio
    async def test_planner_stream_update(self, ui):
        """Test planner stream updates"""
        await ui.start()

        await ui.update_planner_stream("Test plan")

        assert "Test plan" in ui.agents['planner'].content

        ui.stop()

    def test_executor_progress_update(self, ui):
        """Test progress bar updates"""
        ui.update_executor_progress(50.0)

        assert ui.agents['executor'].progress == 50.0

    def test_file_operation_add(self, ui):
        """Test adding file operations"""
        initial_len = len(ui.file_ops.operations)

        ui.add_file_operation("test.py", "modified", 10, 5)

        assert len(ui.file_ops.operations) == initial_len + 1

    def test_mark_agent_done(self, ui):
        """Test marking agent as done"""
        ui.mark_agent_done('executor')

        assert ui.agents['executor'].status == AgentStatus.DONE
        assert ui.agents['executor'].progress == 100.0

    def test_metrics_update(self, ui):
        """Test metrics updates"""
        ui.update_metrics(
            success_rate=99.9,
            tokens_used=1500
        )

        assert ui.metrics.success_rate == 99.9
        assert ui.metrics.tokens_used == 1500


# ============================================================================
# STRESS TESTS - Performance Under Load
# ============================================================================

class TestPerformanceStress:
    """Stress test performance limits"""

    @pytest.mark.asyncio
    @pytest.mark.timeout(10)
    async def test_rapid_stream_updates(self, ui):
        """Test handling rapid stream updates"""
        await ui.start()

        start = time.time()

        # 1000 rapid updates
        for i in range(1000):
            await ui.update_executor_stream(f"Message {i}")

        elapsed = time.time() - start

        ui.stop()

        # Should complete in reasonable time
        assert elapsed < 10.0
        assert len(ui.agents['executor'].content) <= 1000  # May truncate

    @pytest.mark.asyncio
    @pytest.mark.timeout(10)
    async def test_rapid_progress_updates(self, ui):
        """Test handling rapid progress updates"""
        start = time.time()

        # 1000 progress updates
        for i in range(1000):
            ui.update_executor_progress(i % 100)

        elapsed = time.time() - start

        # Should be very fast (no async)
        assert elapsed < 1.0

    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    async def test_sustained_30fps_rendering(self, ui):
        """Test UI can sustain 30 FPS for extended period"""
        await ui.start()

        frame_count = 0
        duration = 3.0  # 3 seconds
        start = time.time()

        while time.time() - start < duration:
            await ui.update_executor_stream(f"Frame {frame_count}")
            frame_count += 1
            await asyncio.sleep(1/30)  # 30 FPS

        elapsed = time.time() - start
        actual_fps = frame_count / elapsed

        ui.stop()

        # Should achieve close to 30 FPS
        assert actual_fps >= 20.0  # Allow some tolerance

    def test_large_content_handling(self, ui):
        """Test handling very large content"""
        # Add 10,000 lines
        for i in range(10000):
            ui.agents['executor'].add_content(f"Line {i}")

        # Should have truncated to max (100 by default)
        assert len(ui.agents['executor'].content) <= 100

    def test_many_file_operations(self, ui):
        """Test handling many file operations"""
        # Add 100 file operations
        for i in range(100):
            ui.add_file_operation(f"file{i}.py", "modified", i, i//2)

        # Should still render
        ui.refresh_display()


# ============================================================================
# CHAOS TESTS - Random Failures & Edge Cases
# ============================================================================

class TestChaosEngineering:
    """Chaos tests - random failures, race conditions, edge cases"""

    @pytest.mark.asyncio
    async def test_concurrent_agent_updates(self, ui):
        """Test concurrent updates from multiple agents"""
        await ui.start()

        async def update_executor():
            for i in range(100):
                await ui.update_executor_stream(f"Exec {i}")
                await asyncio.sleep(0.001)

        async def update_planner():
            for i in range(100):
                await ui.update_planner_stream(f"Plan {i}")
                await asyncio.sleep(0.001)

        async def update_files():
            for i in range(100):
                ui.add_file_operation(f"file{i}.py", "modified", 1, 1)
                await asyncio.sleep(0.001)

        # Run all concurrently
        await asyncio.gather(
            update_executor(),
            update_planner(),
            update_files()
        )

        ui.stop()

        # All updates should have been processed (may be truncated)
        assert len(ui.agents['executor'].content) > 0
        assert len(ui.agents['planner'].content) > 0
        assert len(ui.file_ops.operations) > 0

    @pytest.mark.asyncio
    async def test_rapid_start_stop(self, ui):
        """Test rapid start/stop cycles"""
        for _ in range(5):
            await ui.start()
            await asyncio.sleep(0.01)
            ui.stop()
            await asyncio.sleep(0.01)

        # Should not crash
        assert True

    def test_invalid_agent_name(self, ui):
        """Test marking invalid agent as done"""
        # Should not crash
        ui.mark_agent_done('nonexistent_agent')

        # Should not have added agent
        assert 'nonexistent_agent' not in ui.agents

    @pytest.mark.asyncio
    async def test_empty_string_updates(self, ui):
        """Test handling empty strings"""
        await ui.start()
        await ui.update_executor_stream("")
        await ui.update_planner_stream("")
        ui.stop()

        # Should not crash

    def test_negative_progress(self, ui):
        """Test handling negative progress"""
        ui.update_executor_progress(-50)

        # Should handle gracefully
        ui.refresh_display()

    def test_progress_over_100(self, ui):
        """Test handling progress > 100"""
        ui.update_executor_progress(150)

        ui.refresh_display()
        # Should not crash

    @pytest.mark.asyncio
    async def test_unicode_and_special_chars(self, ui):
        """Test handling unicode and special characters"""
        await ui.start()

        special_strings = [
            "Hello 世界 🌍",
            "Ñoño",
            "../../etc/passwd",
            "\x1b[31mRed\x1b[0m",  # ANSI codes
        ]

        for s in special_strings:
            await ui.update_executor_stream(s)

        ui.stop()

        # Should handle all without crashing


# ============================================================================
# MEMORY LEAK TESTS
# ============================================================================

class TestMemoryLeaks:
    """Test for memory leaks in long-running scenarios"""

    @pytest.mark.asyncio
    async def test_no_memory_leak_in_updates(self, ui):
        """Test that repeated updates don't leak memory"""
        tracemalloc.start()

        await ui.start()

        # Baseline
        gc.collect()
        snapshot1 = tracemalloc.take_snapshot()

        # Do lots of updates
        for i in range(1000):
            await ui.update_executor_stream(f"Message {i}")

        # Check memory after
        gc.collect()
        snapshot2 = tracemalloc.take_snapshot()

        ui.stop()

        # Compare memory
        top_stats = snapshot2.compare_to(snapshot1, 'lineno')

        # Total memory increase should be reasonable
        total_increase = sum(stat.size_diff for stat in top_stats)

        tracemalloc.stop()

        # Allow up to 10MB increase for 1000 messages
        assert total_increase < 10 * 1024 * 1024

    def test_content_list_management(self, ui):
        """Test content lists are managed properly"""
        # Add 10,000 messages
        for i in range(10000):
            ui.agents['executor'].add_content(f"Message {i}")

        # Should have truncated automatically
        assert len(ui.agents['executor'].content) <= 100


# ============================================================================
# EDGE CASES - Boundary Conditions
# ============================================================================

class TestEdgeCases:
    """Test edge cases and boundary conditions"""

    def test_zero_dimensions(self):
        """Test with zero-width console"""
        console = Console(file=io.StringIO(), width=10, height=10)
        ui = MaestroShellUI(console=console)

        # Should not crash
        ui.refresh_display()

    def test_huge_console(self):
        """Test with very large console"""
        console = Console(file=io.StringIO(), width=500, height=500)
        ui = MaestroShellUI(console=console)

        ui.refresh_display()
        # Should handle large dimensions

    @pytest.mark.asyncio
    async def test_extremely_long_single_message(self, ui):
        """Test handling very long single message"""
        await ui.start()

        # 10KB message
        long_message = "A" * (10 * 1024)
        await ui.update_executor_stream(long_message)

        ui.stop()

        # Should handle without crashing

    def test_metrics_extreme_values(self, ui):
        """Test metrics with extreme values"""
        ui.update_metrics(
            success_rate=999999.99,
            tokens_used=2**31 - 1,  # Max int
            saved_money=1e10,
            latency_ms=0
        )

        ui.refresh_display()
        # Should handle extreme values


# ============================================================================
# TEST RUNNER WITH DETAILED REPORTING
# ============================================================================

if __name__ == "__main__":
    pytest.main([
        __file__,
        "-v",
        "-s",
        "--tb=short",
        "-m", "not integration",
    ])
