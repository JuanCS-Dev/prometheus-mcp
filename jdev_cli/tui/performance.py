"""Performance Monitoring - Track and ensure 30 FPS target.

Provides frame budget monitoring, FPS calculation, and performance telemetry.
"""

import time
import logging
from collections import deque
from typing import Optional, Deque
from dataclasses import dataclass
from contextlib import contextmanager

from rich.panel import Panel
from rich.table import Table
from rich.text import Text

logger = logging.getLogger(__name__)


@dataclass
class FrameMetrics:
    """Metrics for a single frame."""

    frame_time: float  # Time taken to render frame (seconds)
    timestamp: float  # When frame was rendered
    budget_exceeded: bool  # Whether frame exceeded budget
    operations: int = 0  # Number of operations in frame


class PerformanceMonitor:
    """Monitor rendering performance and ensure 30 FPS target."""

    def __init__(self, target_fps: int = 30, history_size: int = 100):
        """Initialize PerformanceMonitor.

        Args:
            target_fps: Target frames per second (default: 30)
            history_size: Number of frames to keep in history
        """
        self.target_fps = target_fps
        self.frame_budget = 1.0 / target_fps  # 33.33ms for 30 FPS
        self.history_size = history_size

        # Metrics storage
        self.frame_times: Deque[float] = deque(maxlen=history_size)
        self.frame_metrics: Deque[FrameMetrics] = deque(maxlen=history_size)

        # Current frame tracking
        self.current_frame_start: Optional[float] = None
        self.total_frames = 0
        self.budget_violations = 0

    @contextmanager
    def measure_frame(self):
        """Context manager to measure frame rendering time.

        Usage:
            with monitor.measure_frame():
                # Render frame
                layout.render()
        """
        start = time.perf_counter()

        try:
            yield
        finally:
            elapsed = time.perf_counter() - start
            self._record_frame(elapsed)

    def _record_frame(self, frame_time: float):
        """Record frame metrics.

        Args:
            frame_time: Time taken to render frame (seconds)
        """
        self.frame_times.append(frame_time)
        self.total_frames += 1

        # Check budget violation
        budget_exceeded = frame_time > (self.frame_budget * 1.5)  # 50ms threshold

        if budget_exceeded:
            self.budget_violations += 1
            logger.warning(
                f"Frame budget exceeded: {frame_time*1000:.1f}ms "
                f"(target: {self.frame_budget*1000:.1f}ms)"
            )

        # Store metrics
        metrics = FrameMetrics(
            frame_time=frame_time,
            timestamp=time.time(),
            budget_exceeded=budget_exceeded
        )
        self.frame_metrics.append(metrics)

    def get_current_fps(self) -> float:
        """Calculate current FPS based on recent frames.

        Returns:
            Current FPS (0 if no data)
        """
        if not self.frame_times:
            return 0.0

        avg_frame_time = sum(self.frame_times) / len(self.frame_times)
        return 1.0 / avg_frame_time if avg_frame_time > 0 else 0.0

    def get_avg_frame_time_ms(self) -> float:
        """Get average frame time in milliseconds.

        Returns:
            Average frame time (ms)
        """
        if not self.frame_times:
            return 0.0

        return (sum(self.frame_times) / len(self.frame_times)) * 1000

    def get_percentile_frame_time_ms(self, percentile: int = 95) -> float:
        """Get percentile frame time in milliseconds.

        Args:
            percentile: Percentile to calculate (default: 95)

        Returns:
            Percentile frame time (ms)
        """
        if not self.frame_times:
            return 0.0

        sorted_times = sorted(self.frame_times)
        index = int(len(sorted_times) * (percentile / 100))
        return sorted_times[min(index, len(sorted_times) - 1)] * 1000

    def get_stats(self) -> dict:
        """Get comprehensive performance statistics.

        Returns:
            Dict with performance stats
        """
        if not self.frame_times:
            return {
                "fps": 0.0,
                "avg_frame_ms": 0.0,
                "p95_frame_ms": 0.0,
                "budget_violations": 0,
                "total_frames": 0
            }

        current_fps = self.get_current_fps()
        avg_frame_ms = self.get_avg_frame_time_ms()
        p95_frame_ms = self.get_percentile_frame_time_ms(95)
        p99_frame_ms = self.get_percentile_frame_time_ms(99)

        violation_rate = (
            self.budget_violations / max(self.total_frames, 1) * 100
        )

        return {
            "target_fps": self.target_fps,
            "current_fps": current_fps,
            "avg_frame_ms": avg_frame_ms,
            "p95_frame_ms": p95_frame_ms,
            "p99_frame_ms": p99_frame_ms,
            "frame_budget_ms": self.frame_budget * 1000,
            "budget_violations": self.budget_violations,
            "violation_rate_pct": violation_rate,
            "total_frames": self.total_frames,
            "frames_measured": len(self.frame_times)
        }

    def render_stats_panel(self) -> Panel:
        """Render performance stats as Rich panel.

        Returns:
            Rich Panel with performance statistics
        """
        stats = self.get_stats()

        table = Table.grid(padding=(0, 2))
        table.add_column(style="dim", justify="right")
        table.add_column()

        # FPS
        fps = stats["current_fps"]
        fps_color = "bright_green" if fps >= self.target_fps else "bright_red"
        table.add_row(
            "FPS:",
            Text(f"{fps:.1f}", style=f"bold {fps_color}")
        )

        # Frame times
        avg_ms = stats["avg_frame_ms"]
        p95_ms = stats["p95_frame_ms"]

        avg_color = "bright_green" if avg_ms <= stats["frame_budget_ms"] else "bright_yellow"
        table.add_row(
            "Avg Frame:",
            Text(f"{avg_ms:.2f}ms", style=avg_color)
        )

        p95_color = "bright_green" if p95_ms <= stats["frame_budget_ms"] * 1.5 else "bright_red"
        table.add_row(
            "P95 Frame:",
            Text(f"{p95_ms:.2f}ms", style=p95_color)
        )

        # Budget violations
        violations = stats["budget_violations"]
        violation_rate = stats["violation_rate_pct"]
        violation_color = "bright_green" if violation_rate < 5 else "bright_yellow"

        table.add_row(
            "Violations:",
            Text(f"{violations} ({violation_rate:.1f}%)", style=violation_color)
        )

        # Total frames
        table.add_row(
            "Total Frames:",
            Text(str(stats["total_frames"]), style="dim")
        )

        panel = Panel(
            table,
            title="[bold bright_yellow]⚡ Performance Monitor[/bold bright_yellow]",
            border_style="bright_yellow",
            padding=(0, 1)
        )

        return panel

    def reset(self):
        """Reset all performance metrics."""
        self.frame_times.clear()
        self.frame_metrics.clear()
        self.total_frames = 0
        self.budget_violations = 0
        self.current_frame_start = None

    def should_warn(self) -> bool:
        """Check if performance warning should be shown.

        Returns:
            True if performance is below acceptable threshold
        """
        if len(self.frame_times) < 10:
            return False  # Not enough data

        current_fps = self.get_current_fps()
        violation_rate = (self.budget_violations / max(self.total_frames, 1)) * 100

        # Warn if FPS drops below 25 or violation rate > 10%
        return current_fps < 25 or violation_rate > 10


class FPSCounter:
    """Lightweight FPS counter for overlay display."""

    def __init__(self, update_interval: float = 1.0):
        """Initialize FPSCounter.

        Args:
            update_interval: How often to update FPS (seconds)
        """
        self.update_interval = update_interval
        self.frame_count = 0
        self.last_update = time.time()
        self.current_fps = 0.0

    def tick(self):
        """Register a frame."""
        self.frame_count += 1

        now = time.time()
        elapsed = now - self.last_update

        if elapsed >= self.update_interval:
            self.current_fps = self.frame_count / elapsed
            self.frame_count = 0
            self.last_update = now

    def get_fps(self) -> float:
        """Get current FPS.

        Returns:
            Current FPS
        """
        return self.current_fps

    def render_overlay(self, show_color: bool = True) -> Text:
        """Render FPS as overlay text.

        Args:
            show_color: Color code based on FPS

        Returns:
            Rich Text with FPS counter
        """
        fps = self.current_fps

        if show_color:
            if fps >= 30:
                color = "bright_green"
            elif fps >= 25:
                color = "bright_yellow"
            else:
                color = "bright_red"
        else:
            color = "white"

        return Text(f"FPS: {fps:.1f}", style=f"{color} on black")
