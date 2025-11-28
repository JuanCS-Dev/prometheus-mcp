"""
Enhanced Progress System - Nov 2025 Standards

Features (inspired by Claude 4.5 + Cursor):
- Multi-stage workflow progress
- Real-time token consumption tracking
- Parallel task visualization
- LLM thinking indicators
- Cost estimation display
- Speed metrics (tokens/sec, operations/sec)

Philosophy:
- Transparency > Mystique (show what's happening)
- Predictability (time + cost estimates)
- Context-aware (adapt to operation type)
- Performance-focused (60 FPS, minimal overhead)

Created: 2025-11-20 12:30 UTC (DAY 8)
"""

import asyncio
import time
from typing import Optional, List, AsyncIterator
from dataclasses import dataclass, field
from enum import Enum

from rich.console import Console, Group
from rich.live import Live
from rich.panel import Panel
from rich.progress import (
    Progress,
    BarColumn,
    TextColumn,
    TimeRemainingColumn,
    TimeElapsedColumn,
    TaskProgressColumn,
    SpinnerColumn,
)
from rich.table import Table
from rich.text import Text

from ..theme import COLORS


class OperationType(Enum):
    """Types of operations for context-aware display."""
    LLM_GENERATION = "llm_gen"
    FILE_OPERATION = "file_op"
    TOOL_EXECUTION = "tool_exec"
    WORKFLOW = "workflow"
    TESTING = "testing"
    VALIDATION = "validation"


@dataclass
class TokenMetrics:
    """Token consumption tracking."""
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    tokens_per_second: float = 0.0
    estimated_cost: float = 0.0  # in USD

    @property
    def cost_formatted(self) -> str:
        """Format cost as USD."""
        if self.estimated_cost < 0.01:
            return f"${self.estimated_cost * 1000:.2f}m"  # millidollars
        return f"${self.estimated_cost:.4f}"


@dataclass
class StageProgress:
    """Progress for a single stage in workflow."""
    name: str
    current: int = 0
    total: int = 100
    status: str = "pending"  # pending, running, complete, error
    start_time: float = 0.0
    end_time: float = 0.0

    @property
    def percentage(self) -> float:
        """Progress as percentage."""
        if self.total == 0:
            return 0.0
        return min(100.0, (self.current / self.total) * 100)

    @property
    def duration(self) -> float:
        """Duration in seconds."""
        if self.start_time == 0:
            return 0.0
        end = self.end_time if self.end_time > 0 else time.time()
        return end - self.start_time


@dataclass
class WorkflowProgress:
    """Multi-stage workflow progress tracking."""
    stages: List[StageProgress] = field(default_factory=list)
    current_stage_idx: int = 0
    tokens: TokenMetrics = field(default_factory=TokenMetrics)
    operation_type: OperationType = OperationType.WORKFLOW

    @property
    def current_stage(self) -> Optional[StageProgress]:
        """Get currently running stage."""
        if 0 <= self.current_stage_idx < len(self.stages):
            return self.stages[self.current_stage_idx]
        return None

    @property
    def overall_percentage(self) -> float:
        """Overall progress across all stages."""
        if not self.stages:
            return 0.0

        completed = 0.0
        total = len(self.stages)

        # Count each stage contribution
        for stage in self.stages:
            if stage.status == "complete":
                completed += 1.0
            elif stage.status == "running":
                completed += stage.percentage / 100.0
            # pending stages contribute 0

        return (completed / total) * 100 if total > 0 else 0.0

    @property
    def total_duration(self) -> float:
        """Total duration across all stages."""
        return sum(s.duration for s in self.stages)


class EnhancedProgressDisplay:
    """
    Enhanced progress display with multi-stage support.
    
    Features:
    - Multi-stage workflow visualization
    - Token consumption tracking
    - Real-time cost estimation
    - Parallel task indicators
    - LLM thinking animations
    
    Examples:
        display = EnhancedProgressDisplay()
        workflow = WorkflowProgress(
            stages=[
                StageProgress("Planning", total=100),
                StageProgress("Execution", total=200),
                StageProgress("Validation", total=50),
            ]
        )
        
        async with display.live_update(workflow):
            for stage_idx in range(len(workflow.stages)):
                workflow.current_stage_idx = stage_idx
                stage = workflow.current_stage
                stage.status = "running"
                stage.start_time = time.time()
                
                for i in range(stage.total):
                    stage.current = i + 1
                    await asyncio.sleep(0.01)
                
                stage.status = "complete"
                stage.end_time = time.time()
    """

    def __init__(self, console: Optional[Console] = None):
        """
        Initialize enhanced progress display.
        
        Args:
            console: Rich console (creates new if None)
        """
        self.console = console or Console()
        self._live: Optional[Live] = None

    def render_workflow(self, workflow: WorkflowProgress) -> Group:
        """
        Render complete workflow progress.
        
        Args:
            workflow: Workflow progress data
        
        Returns:
            Rich Group renderable
        """
        elements: List[Panel | Table] = []

        # Overall progress bar
        overall_bar = self._render_overall_progress(workflow)
        elements.append(overall_bar)

        # Stage details
        stage_table = self._render_stages(workflow)
        elements.append(stage_table)

        # Metrics (tokens, cost, speed)
        if workflow.tokens.total_tokens > 0:
            metrics = self._render_metrics(workflow)
            elements.append(metrics)

        return Group(*elements)

    def _render_overall_progress(self, workflow: WorkflowProgress) -> Panel:
        """Render overall progress bar."""
        percentage = workflow.overall_percentage

        # Create progress bar
        bar_width = 40
        filled = int(bar_width * percentage / 100)
        bar = "█" * filled + "░" * (bar_width - filled)

        # Color based on percentage
        if percentage < 30:
            color = COLORS["info"]
        elif percentage < 70:
            color = COLORS["warning"]
        else:
            color = COLORS["success"]

        text = Text()
        text.append("Overall Progress: ", style="bold")
        text.append(f"{percentage:.1f}%", style=f"bold {color}")
        text.append(f"\n{bar}", style=color)

        # Add duration
        duration = workflow.total_duration
        if duration > 0:
            text.append(f"\nTime: {duration:.1f}s", style="dim")

        return Panel(text, border_style=color, padding=(0, 1))

    def _render_stages(self, workflow: WorkflowProgress) -> Table:
        """Render stage details as table."""
        table = Table(
            show_header=True,
            header_style="bold cyan",
            border_style="dim",
            padding=(0, 1),
        )

        table.add_column("Stage", style="cyan")
        table.add_column("Status", justify="center")
        table.add_column("Progress", justify="right")
        table.add_column("Time", justify="right")

        for idx, stage in enumerate(workflow.stages):
            # Status icon
            if stage.status == "complete":
                status = Text("✓", style="bold green")
            elif stage.status == "error":
                status = Text("✗", style="bold red")
            elif stage.status == "running":
                status = Text("⚡", style="bold yellow")
            else:
                status = Text("○", style="dim")

            # Progress
            progress_text = f"{stage.percentage:.0f}%"
            if stage.status == "running":
                progress_text += f" ({stage.current}/{stage.total})"

            # Time
            time_text = f"{stage.duration:.1f}s" if stage.duration > 0 else "-"

            # Highlight current stage
            name_style = "bold yellow" if idx == workflow.current_stage_idx else ""

            table.add_row(
                Text(stage.name, style=name_style),
                status,
                progress_text,
                time_text,
            )

        return table

    def _render_metrics(self, workflow: WorkflowProgress) -> Panel:
        """Render token and cost metrics."""
        tokens = workflow.tokens

        text = Text()

        # Token consumption
        text.append("🔤 Tokens: ", style="bold cyan")
        text.append(f"{tokens.total_tokens:,} ", style="cyan")
        text.append(f"(↓{tokens.input_tokens:,} ↑{tokens.output_tokens:,})", style="dim")

        # Speed
        if tokens.tokens_per_second > 0:
            text.append("\n⚡ Speed: ", style="bold yellow")
            text.append(f"{tokens.tokens_per_second:.0f} tok/s", style="yellow")

        # Cost
        if tokens.estimated_cost > 0:
            text.append("\n💰 Cost: ", style="bold green")
            text.append(tokens.cost_formatted, style="green")

        return Panel(
            text,
            title="[bold]Metrics[/bold]",
            border_style="cyan",
            padding=(0, 1),
        )

    async def live_update(
        self,
        workflow: WorkflowProgress,
        refresh_rate: float = 0.1,
    ) -> AsyncIterator[None]:
        """
        Context manager for live progress updates.
        
        Args:
            workflow: Workflow to track
            refresh_rate: Update frequency in seconds
        
        Yields:
            None (updates happen in background)
        
        Example:
            async with display.live_update(workflow):
                # Your work here
                await do_work()
        """
        with Live(
            self.render_workflow(workflow),
            console=self.console,
            refresh_per_second=1 / refresh_rate,
            transient=True,
        ) as live:
            self._live = live

            try:
                # Update loop
                while True:
                    live.update(self.render_workflow(workflow))
                    await asyncio.sleep(refresh_rate)
            except asyncio.CancelledError:
                # Final update
                live.update(self.render_workflow(workflow))
                raise
            finally:
                self._live = None


class ThinkingIndicator:
    """
    Animated 'thinking' indicator for LLM operations.
    
    Shows what the LLM is doing (Claude 4.5 style):
    - "Analyzing codebase..."
    - "Generating solution..."
    - "Validating changes..."
    """

    FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]

    def __init__(
        self,
        message: str = "Thinking...",
        console: Optional[Console] = None,
    ):
        """
        Initialize thinking indicator.
        
        Args:
            message: Status message
            console: Rich console
        """
        self.message = message
        self.console = console or Console()
        self._frame_idx = 0

    async def animate(self, duration: Optional[float] = None) -> AsyncIterator[str]:
        """
        Animate thinking indicator.
        
        Args:
            duration: Duration in seconds (None = infinite)
        
        Yields:
            Rendered frame
        """
        start = time.time()

        while True:
            # Check duration
            if duration and (time.time() - start) >= duration:
                break

            # Render frame
            frame = self.FRAMES[self._frame_idx % len(self.FRAMES)]
            text = Text()
            text.append(frame, style="bold cyan")
            text.append(f" {self.message}", style="cyan")

            yield str(text)

            self._frame_idx += 1
            await asyncio.sleep(0.1)  # 10 FPS


# Convenience function for simple progress
def create_simple_progress(description: str = "") -> Progress:
    """
    Create simple progress bar (for backward compatibility).
    
    Args:
        description: Progress description
    
    Returns:
        Rich Progress instance
    """
    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TimeRemainingColumn(),
        TimeElapsedColumn(),
        console=Console(),
    )
