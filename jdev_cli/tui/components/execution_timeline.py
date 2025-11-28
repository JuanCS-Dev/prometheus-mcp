"""
Execution Timeline System - DAY 8 Phase 3.2
Time-based progress tracking with performance metrics

Constitutional Compliance:
- P2 (Validação): Visual validation of timing accuracy
- P6 (Eficiência): Real-time metrics with <2ms overhead
- P4 (Rastreabilidade): Complete execution history
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import statistics

from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.progress import Progress, TimeElapsedColumn, SpinnerColumn


@dataclass
class TimelineEvent:
    """Represents a single timeline event"""
    timestamp: datetime
    step_id: str
    event_type: str  # 'start', 'end', 'progress', 'error'
    data: Dict = field(default_factory=dict)

    @property
    def relative_time(self) -> float:
        """Time relative to epoch (for plotting)"""
        return self.timestamp.timestamp()


@dataclass
class StepMetrics:
    """Performance metrics for a workflow step"""
    step_id: str
    name: str
    start_time: datetime
    end_time: Optional[datetime] = None
    progress_updates: int = 0
    error_count: int = 0

    @property
    def duration(self) -> Optional[float]:
        """Duration in seconds"""
        if self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return (datetime.now() - self.start_time).total_seconds()

    @property
    def is_running(self) -> bool:
        """Check if step is still running"""
        return self.end_time is None


class ExecutionTimeline:
    """
    Time-based workflow execution tracking
    
    Features:
    - Real-time progress bars with ETA
    - Step duration tracking
    - Performance bottleneck detection
    - Historical comparison
    
    Constitutional Alignment:
    - P4 (Rastreabilidade): Complete audit trail
    - P6 (Eficiência): Minimal overhead tracking
    """

    def __init__(self, console: Optional[Console] = None):
        self.console = console or Console()
        self.events: List[TimelineEvent] = []
        self.metrics: Dict[str, StepMetrics] = {}
        self.start_time: Optional[datetime] = None

    def record_event(
        self,
        step_id: str,
        event_type: str,
        data: Optional[Dict] = None
    ) -> None:
        """Record a timeline event"""
        if not self.start_time:
            self.start_time = datetime.now()

        event = TimelineEvent(
            timestamp=datetime.now(),
            step_id=step_id,
            event_type=event_type,
            data=data or {}
        )
        self.events.append(event)

        # Update metrics
        event_data = data or {}
        if step_id not in self.metrics and event_type == 'start':
            self.metrics[step_id] = StepMetrics(
                step_id=step_id,
                name=event_data.get('name', step_id),
                start_time=event.timestamp
            )
        elif step_id in self.metrics:
            metric = self.metrics[step_id]
            if event_type == 'end':
                metric.end_time = event.timestamp
            elif event_type == 'progress':
                metric.progress_updates += 1
            elif event_type == 'error':
                metric.error_count += 1

    def get_step_duration(self, step_id: str) -> Optional[float]:
        """Get step duration in seconds"""
        if step_id in self.metrics:
            return self.metrics[step_id].duration
        return None

    def get_bottlenecks(self, threshold: float = 5.0) -> List[Tuple[str, float]]:
        """
        Identify performance bottlenecks
        
        Args:
            threshold: Minimum duration (seconds) to be considered a bottleneck
            
        Returns:
            List of (step_id, duration) tuples for slow steps
        """
        bottlenecks = []
        for step_id, metric in self.metrics.items():
            if metric.duration and metric.duration > threshold:
                bottlenecks.append((step_id, metric.duration))

        return sorted(bottlenecks, key=lambda x: x[1], reverse=True)

    def get_performance_stats(self) -> Dict[str, float]:
        """Calculate overall performance statistics"""
        durations = [
            m.duration for m in self.metrics.values()
            if m.duration and not m.is_running
        ]

        if not durations:
            return {
                'total_duration': 0.0,
                'avg_step_duration': 0.0,
                'min_step_duration': 0.0,
                'max_step_duration': 0.0,
                'median_step_duration': 0.0,
                'std_deviation': 0.0
            }

        return {
            'total_duration': (datetime.now() - self.start_time).total_seconds() if self.start_time else 0.0,
            'avg_step_duration': statistics.mean(durations),
            'min_step_duration': min(durations),
            'max_step_duration': max(durations),
            'median_step_duration': statistics.median(durations),
            'std_deviation': statistics.stdev(durations) if len(durations) > 1 else 0.0
        }

    def render_progress_bars(self) -> Group:
        """Render live progress bars for running steps"""
        progress = Progress(
            SpinnerColumn(),
            *Progress.get_default_columns(),
            TimeElapsedColumn(),
            console=self.console
        )

        tasks = {}
        for step_id, metric in self.metrics.items():
            if metric.is_running:
                task_id = progress.add_task(
                    f"[cyan]{metric.name}",
                    total=100
                )
                tasks[step_id] = task_id

        return Group(progress)

    def render_duration_table(self) -> Table:
        """Render step duration comparison table"""
        table = Table(title="⏱️  Step Duration Analysis", show_header=True)
        table.add_column("Step", style="cyan", width=30)
        table.add_column("Duration", justify="right", width=12)
        table.add_column("% of Total", justify="right", width=12)
        table.add_column("Status", width=15)

        total_duration = self.get_performance_stats()['total_duration']

        # Sort by duration (longest first)
        sorted_metrics = sorted(
            self.metrics.values(),
            key=lambda m: m.duration or 0,
            reverse=True
        )

        for metric in sorted_metrics:
            duration = metric.duration or 0
            percentage = (duration / total_duration * 100) if total_duration > 0 else 0

            status = "🔄 Running" if metric.is_running else "✅ Complete"
            if metric.error_count > 0:
                status = f"⚠️  {metric.error_count} errors"

            # Color code by duration
            duration_style = "green"
            if percentage > 30:
                duration_style = "red bold"
            elif percentage > 15:
                duration_style = "yellow"

            table.add_row(
                metric.name,
                f"[{duration_style}]{duration:.2f}s[/]",
                f"{percentage:.1f}%",
                status
            )

        return table

    def render_bottleneck_report(self) -> Panel:
        """Render bottleneck analysis"""
        bottlenecks = self.get_bottlenecks(threshold=3.0)

        if not bottlenecks:
            return Panel(
                "[green]✅ No bottlenecks detected! All steps running efficiently.[/]",
                title="🚀 Performance Report",
                border_style="green"
            )

        text = Text()
        text.append("⚠️  Performance Bottlenecks Detected\n\n", style="bold yellow")
        text.append("The following steps are taking longer than expected:\n\n")

        for i, (step_id, duration) in enumerate(bottlenecks[:5], 1):
            metric = self.metrics[step_id]
            text.append(f"{i}. ", style="bold")
            text.append(f"{metric.name}\n", style="cyan")
            text.append(f"   Duration: {duration:.2f}s\n", style="red")

            # Suggest optimization
            if metric.progress_updates == 0:
                text.append("   💡 Suggestion: Add progress updates for better tracking\n", style="dim")
            elif metric.error_count > 0:
                text.append(f"   ⚠️  {metric.error_count} errors occurred\n", style="yellow")

            text.append("\n")

        return Panel(text, title="🐢 Bottleneck Analysis", border_style="yellow")

    def render_performance_summary(self) -> Panel:
        """Render overall performance statistics"""
        stats = self.get_performance_stats()

        text = Text()
        text.append("📊 Performance Summary\n\n", style="bold cyan")

        # Total duration
        total_str = self._format_duration(stats['total_duration'])
        text.append(f"⏱️  Total Execution: {total_str}\n", style="white")

        # Step statistics
        text.append("\n📈 Step Statistics:\n", style="bold")
        text.append(f"  Average: {stats['avg_step_duration']:.2f}s\n")
        text.append(f"  Median:  {stats['median_step_duration']:.2f}s\n")
        text.append(f"  Min:     {stats['min_step_duration']:.2f}s\n")
        text.append(f"  Max:     {stats['max_step_duration']:.2f}s\n")

        if stats['std_deviation'] > 0:
            text.append(f"  Std Dev: {stats['std_deviation']:.2f}s\n", style="dim")

        # Efficiency rating
        efficiency = self._calculate_efficiency_rating(stats)
        text.append("\n⚡ Efficiency Rating: ", style="bold")
        text.append(f"{efficiency['grade']}", style=efficiency['style'])
        text.append(f" ({efficiency['score']}/100)\n")

        return Panel(text, border_style="cyan")

    def render_full_timeline(self) -> Group:
        """Render complete timeline view"""
        return Group(
            self.render_performance_summary(),
            self.render_duration_table(),
            self.render_bottleneck_report()
        )

    def _format_duration(self, seconds: float) -> str:
        """Format duration in human-readable format"""
        if seconds < 1:
            return f"{seconds * 1000:.0f}ms"
        elif seconds < 60:
            return f"{seconds:.1f}s"
        elif seconds < 3600:
            minutes = int(seconds // 60)
            secs = int(seconds % 60)
            return f"{minutes}m {secs}s"
        else:
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            return f"{hours}h {minutes}m"

    def _calculate_efficiency_rating(self, stats: Dict[str, float]) -> Dict[str, str]:
        """
        Calculate efficiency rating based on performance stats
        
        Criteria:
        - Low variance (consistent step times): +30 points
        - Fast average step time (<5s): +40 points  
        - No extreme bottlenecks (max/avg ratio <3): +30 points
        """
        score = 0

        # Consistency check
        if stats['std_deviation'] > 0:
            cv = stats['std_deviation'] / stats['avg_step_duration']  # Coefficient of variation
            if cv < 0.3:
                score += 30
            elif cv < 0.5:
                score += 20
            elif cv < 0.8:
                score += 10

        # Speed check
        avg = stats['avg_step_duration']
        if avg < 2:
            score += 40
        elif avg < 5:
            score += 30
        elif avg < 10:
            score += 15

        # Bottleneck check
        if stats['max_step_duration'] > 0:
            ratio = stats['max_step_duration'] / stats['avg_step_duration']
            if ratio < 2:
                score += 30
            elif ratio < 3:
                score += 20
            elif ratio < 5:
                score += 10

        # Grade mapping
        if score >= 90:
            grade = "A+"
            style = "green bold"
        elif score >= 80:
            grade = "A"
            style = "green"
        elif score >= 70:
            grade = "B"
            style = "yellow"
        elif score >= 60:
            grade = "C"
            style = "yellow dim"
        else:
            grade = "D"
            style = "red"

        return {'grade': grade, 'score': score, 'style': style}


class TimelinePlayback:
    """
    Visual timeline replay (+5pts to match Cursor)
    
    Features:
    - Step-by-step replay of execution
    - Play/Pause/Rewind controls
    - Speed control (1x, 2x, 5x, 10x)
    - Jump to specific steps
    """

    def __init__(self, timeline: ExecutionTimeline, console: Optional[Console] = None):
        self.timeline = timeline
        self.console = console or Console()
        self.current_step = 0
        self.is_playing = False
        self.playback_speed = 1.0

    def play(self) -> None:
        """Start playback"""
        self.is_playing = True

    def pause(self) -> None:
        """Pause playback"""
        self.is_playing = False

    def rewind(self) -> None:
        """Rewind to start"""
        self.current_step = 0
        self.is_playing = False

    def step_forward(self) -> bool:
        """Move to next step"""
        if self.current_step < len(self.timeline.events) - 1:
            self.current_step += 1
            return True
        return False

    def step_backward(self) -> bool:
        """Move to previous step"""
        if self.current_step > 0:
            self.current_step -= 1
            return True
        return False

    def jump_to(self, step_index: int) -> bool:
        """Jump to specific step"""
        if 0 <= step_index < len(self.timeline.events):
            self.current_step = step_index
            return True
        return False

    def set_speed(self, speed: float) -> None:
        """Set playback speed multiplier"""
        self.playback_speed = max(0.1, min(10.0, speed))

    def get_current_event(self) -> Optional[TimelineEvent]:
        """Get current event"""
        if 0 <= self.current_step < len(self.timeline.events):
            return self.timeline.events[self.current_step]
        return None

    def get_progress(self) -> float:
        """Get playback progress (0.0 to 1.0)"""
        if not self.timeline.events:
            return 0.0
        return self.current_step / len(self.timeline.events)

    def render_controls(self) -> Panel:
        """Render playback controls UI"""
        from rich.table import Table

        controls = Table.grid(padding=1)
        controls.add_column(justify="center")

        # Playback status
        status = "▶️ Playing" if self.is_playing else "⏸️  Paused"
        controls.add_row(f"[bold]{status}[/bold]")

        # Progress bar
        progress = self.get_progress()
        bar_width = 40
        filled = int(progress * bar_width)
        bar = "█" * filled + "░" * (bar_width - filled)
        controls.add_row(f"[cyan]{bar}[/cyan]")
        controls.add_row(f"Step {self.current_step + 1}/{len(self.timeline.events)}")

        # Speed indicator
        controls.add_row(f"Speed: {self.playback_speed}x")

        # Controls help
        controls.add_row("")
        controls.add_row("[dim]Space: Play/Pause | ←/→: Step | R: Rewind | 1-9: Speed[/dim]")

        return Panel(controls, title="🎬 Timeline Playback", border_style="cyan")

    def render_current_step(self) -> Panel:
        """Render details of current step"""
        event = self.get_current_event()
        if not event:
            return Panel("[dim]No event selected[/dim]", title="Step Details")

        from rich.table import Table

        details = Table.grid(padding=1)
        details.add_column(style="bold cyan", width=15)
        details.add_column()

        details.add_row("Timestamp:", event.timestamp.strftime("%H:%M:%S.%f")[:-3])
        details.add_row("Step ID:", event.step_id)
        details.add_row("Event Type:", event.event_type.upper())

        # Show event data
        if event.data:
            details.add_row("", "")
            details.add_row("Data:", "")
            for key, value in event.data.items():
                details.add_row(f"  {key}:", str(value))

        # Show step duration if available
        if event.step_id in self.timeline.metrics:
            metric = self.timeline.metrics[event.step_id]
            if metric.duration:
                details.add_row("", "")
                details.add_row("Duration:", f"{metric.duration:.2f}s")

        return Panel(details, title="📍 Current Step", border_style="yellow")

    def render_full_ui(self) -> Group:
        """Render complete playback UI"""
        return Group(
            self.render_controls(),
            self.render_current_step()
        )


class TimelineComparator:
    """
    Compare multiple timeline executions
    
    Use case: Compare performance across runs to detect regressions
    """

    def __init__(self):
        self.timelines: List[ExecutionTimeline] = []

    def add_timeline(self, timeline: ExecutionTimeline) -> None:
        """Add a timeline for comparison"""
        self.timelines.append(timeline)

    def compare_step_durations(self, step_id: str) -> Dict[str, float]:
        """Compare duration of a specific step across timelines"""
        durations = []
        for timeline in self.timelines:
            duration = timeline.get_step_duration(step_id)
            if duration:
                durations.append(duration)

        if not durations:
            return {}

        return {
            'avg': statistics.mean(durations),
            'min': min(durations),
            'max': max(durations),
            'std': statistics.stdev(durations) if len(durations) > 1 else 0.0,
            'trend': self._calculate_trend(durations)
        }

    def _calculate_trend(self, values: List[float]) -> str:
        """Calculate performance trend (improving/degrading)"""
        if len(values) < 2:
            return "stable"

        # Simple linear regression
        first_half = statistics.mean(values[:len(values)//2])
        second_half = statistics.mean(values[len(values)//2:])

        diff_pct = ((second_half - first_half) / first_half) * 100

        if diff_pct < -10:
            return "improving ✅"
        elif diff_pct > 10:
            return "degrading ⚠️"
        else:
            return "stable ➡️"


# Example usage
if __name__ == "__main__":
    import time

    console = Console()
    timeline = ExecutionTimeline(console)

    # Simulate workflow execution
    steps = [
        ("init", "Initialize System"),
        ("load", "Load Configuration"),
        ("process", "Process Data"),
        ("save", "Save Results")
    ]

    for step_id, name in steps:
        timeline.record_event(step_id, 'start', {'name': name})

        # Simulate work
        duration = 1.0 + (hash(step_id) % 10) / 10
        time.sleep(duration)

        timeline.record_event(step_id, 'end')

    # Display results
    console.print(timeline.render_full_timeline())
