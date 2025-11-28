"""
Performance Tests for Workflow Visualizer - DAY 8 Phase 5
Tests 60fps target and render optimization
"""

import pytest
import time
from jdev_cli.tui.components.workflow_visualizer import (
    WorkflowVisualizer,
    StepStatus
)
from rich.console import Console


class TestWorkflowVisualizerPerformance:
    """Test suite for workflow visualizer performance (60fps target)"""

    def setup_method(self):
        """Setup test environment"""
        self.console = Console()
        self.viz = WorkflowVisualizer(self.console)

    def test_render_performance_60fps_target(self):
        """
        Test: Render time must be <16.67ms for 60fps
        CRITICAL: Performance regression test
        """
        # Setup complex workflow (10 steps)
        for i in range(10):
            self.viz.add_step(
                f"step{i}",
                f"Task {i}",
                dependencies=[f"step{i-1}"] if i > 0 else []
            )

        # Update all steps to RUNNING (worst case - all panels active)
        for i in range(10):
            self.viz.update_step(f"step{i}", status=StepStatus.RUNNING, progress=0.5)
            self.viz.stream_token(f"step{i}", f"Token {i}")

        # Measure render time (cold - first render)
        start = time.perf_counter()
        self.viz.render_full_view()
        cold_time_ms = (time.perf_counter() - start) * 1000

        # Measure render time (hot - with cache)
        start = time.perf_counter()
        self.viz.render_full_view()
        hot_time_ms = (time.perf_counter() - start) * 1000

        # Assertions
        TARGET_MS = 16.67  # 60fps = 16.67ms per frame

        # Cold render can be slower (building cache)
        assert cold_time_ms < 50, f"Cold render too slow: {cold_time_ms:.2f}ms > 50ms"

        # Hot render MUST be <16.67ms (60fps guarantee)
        assert hot_time_ms < TARGET_MS, (
            f"Hot render failed 60fps target: {hot_time_ms:.2f}ms > {TARGET_MS}ms"
        )

        print("\n✅ Performance OK:")
        print(f"   Cold render: {cold_time_ms:.2f}ms")
        print(f"   Hot render:  {hot_time_ms:.2f}ms (<{TARGET_MS}ms ✅)")

    def test_cache_efficiency(self):
        """
        Test: Cache should prevent redundant renders
        """
        # Setup workflow
        self.viz.add_step("step1", "Task 1")
        self.viz.update_step("step1", status=StepStatus.RUNNING)

        # First render (builds cache)
        self.viz.render_full_view()
        initial_cache_size = len(self.viz._cache)

        # Second render WITHOUT state change (should use cache)
        self.viz.render_full_view()

        # Cache should exist and be reused
        assert len(self.viz._cache) == initial_cache_size
        assert "minimap" in self.viz._cache
        assert "main" in self.viz._cache
        assert "details" in self.viz._cache

        # Verify dirty flags are clean
        assert len(self.viz._dirty_flags) == 0, "Dirty flags should be cleared after render"

    def test_differential_rendering(self):
        """
        Test: Only changed sections should be re-rendered
        """
        # Setup
        self.viz.add_step("step1", "Task 1")
        self.viz.add_step("step2", "Task 2")

        # Initial render
        self.viz.update_step("step1", status=StepStatus.RUNNING)
        self.viz.render_full_view()

        # Clear dirty flags manually to simulate stable state
        self.viz._dirty_flags.clear()

        # Update only step2 (should only dirty relevant sections)
        self.viz.update_step("step2", status=StepStatus.RUNNING)

        # Dirty flags should be set
        assert len(self.viz._dirty_flags) > 0, "Update should set dirty flags"

    def test_memory_efficiency(self):
        """
        Test: Memory usage should be reasonable (<10MB for 100 steps)
        """
        import sys

        # Setup large workflow (100 steps)
        for i in range(100):
            self.viz.add_step(f"step{i}", f"Task {i}")

        # Update all steps
        for i in range(100):
            self.viz.update_step(f"step{i}", status=StepStatus.COMPLETED, progress=1.0)

        # Render
        self.viz.render_full_view()

        # Estimate memory (rough)
        viz_size = sys.getsizeof(self.viz)
        steps_size = sum(sys.getsizeof(s) for s in self.viz.steps.values())
        cache_size = sys.getsizeof(self.viz._cache)

        total_kb = (viz_size + steps_size + cache_size) / 1024

        # Should be <10MB for 100 steps
        assert total_kb < 10 * 1024, f"Memory usage too high: {total_kb:.2f}KB"

        print(f"\n✅ Memory OK: {total_kb:.2f}KB for 100 steps")

    def test_performance_metrics_api(self):
        """
        Test: Performance metrics API should return valid data
        """
        # Setup and render
        self.viz.add_step("step1", "Task 1")
        self.viz.update_step("step1", status=StepStatus.RUNNING)
        self.viz.render_full_view()

        # Get metrics
        metrics = self.viz.get_performance_metrics()

        # Validate structure
        assert "last_frame_time_ms" in metrics
        assert "target_frame_time_ms" in metrics
        assert "current_fps" in metrics
        assert "target_fps" in metrics
        assert "performance_ok" in metrics

        # Validate values
        assert metrics["target_fps"] == 60
        assert metrics["target_frame_time_ms"] == pytest.approx(16.67, rel=0.01)
        assert isinstance(metrics["performance_ok"], bool)

        print("\n✅ Performance Metrics:")
        for key, value in metrics.items():
            print(f"   {key}: {value}")

    def test_60fps_sustained_load(self):
        """
        Test: Maintain 60fps over 100 consecutive renders
        Simulates sustained load scenario
        """
        # Setup workflow
        for i in range(5):
            self.viz.add_step(f"step{i}", f"Task {i}")

        render_times = []

        # Simulate 100 frames
        for frame in range(100):
            # Vary state slightly each frame (realistic scenario)
            step_idx = frame % 5
            progress = (frame % 100) / 100.0

            self.viz.update_step(
                f"step{step_idx}",
                status=StepStatus.RUNNING,
                progress=progress
            )

            # Measure render
            start = time.perf_counter()
            self.viz.render_full_view()
            render_time_ms = (time.perf_counter() - start) * 1000

            render_times.append(render_time_ms)

        # Statistics
        avg_time = sum(render_times) / len(render_times)
        max_time = max(render_times)
        p95_time = sorted(render_times)[int(len(render_times) * 0.95)]

        TARGET = 16.67

        # Assertions
        assert avg_time < TARGET, f"Average render time too high: {avg_time:.2f}ms > {TARGET}ms"
        assert p95_time < TARGET * 1.2, f"P95 render time too high: {p95_time:.2f}ms"

        print("\n✅ Sustained Performance (100 frames):")
        print(f"   Avg:  {avg_time:.2f}ms")
        print(f"   Max:  {max_time:.2f}ms")
        print(f"   P95:  {p95_time:.2f}ms")
        print(f"   Target: <{TARGET}ms ✅")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
