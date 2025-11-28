"""
Status Dashboard - Real-time System Overview (Nov 2025)

Features (inspired by Windsurf Cascade + Cursor):
- Live system metrics (CPU, memory, token rate)
- Active operations panel
- Recent history (last 5 operations)
- Cost tracker (session + total)
- Context window utilization
- Quick stats panel

Philosophy:
- Glanceable (understand system state in 1 second)
- Non-intrusive (updates don't disrupt work)
- Actionable (show what matters, hide noise)
- Performant (minimal overhead, 60 FPS)

Created: 2025-11-20 12:40 UTC (DAY 8)
"""

import asyncio
import time
import psutil
from typing import Optional, List
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.live import Live
from rich import box



class OperationStatus(Enum):
    """Status of an operation."""
    RUNNING = "running"
    SUCCESS = "success"
    ERROR = "error"
    CANCELLED = "cancelled"


@dataclass
class Operation:
    """Single operation record."""
    id: str
    type: str  # "llm", "file", "tool", "workflow"
    description: str
    status: OperationStatus = OperationStatus.RUNNING
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    tokens_used: int = 0
    cost: float = 0.0

    @property
    def duration(self) -> float:
        """Duration in seconds."""
        end = self.end_time if self.end_time else time.time()
        return end - self.start_time

    @property
    def duration_str(self) -> str:
        """Formatted duration."""
        d = self.duration
        if d < 1:
            return f"{d*1000:.0f}ms"
        elif d < 60:
            return f"{d:.1f}s"
        else:
            return f"{d/60:.1f}m"


@dataclass
class SystemMetrics:
    """System resource metrics."""
    cpu_percent: float = 0.0
    memory_percent: float = 0.0
    memory_used_mb: float = 0.0
    memory_total_mb: float = 0.0

    @classmethod
    def capture(cls) -> "SystemMetrics":
        """Capture current system metrics."""
        mem = psutil.virtual_memory()
        return cls(
            cpu_percent=psutil.cpu_percent(interval=0.1),
            memory_percent=mem.percent,
            memory_used_mb=mem.used / 1024 / 1024,
            memory_total_mb=mem.total / 1024 / 1024,
        )


@dataclass
class SessionStats:
    """Statistics for current session."""
    total_operations: int = 0
    successful_operations: int = 0
    failed_operations: int = 0
    total_tokens: int = 0
    total_cost: float = 0.0
    session_start: float = field(default_factory=time.time)

    @property
    def success_rate(self) -> float:
        """Success rate as percentage."""
        if self.total_operations == 0:
            return 0.0
        return (self.successful_operations / self.total_operations) * 100

    @property
    def session_duration(self) -> float:
        """Session duration in seconds."""
        return time.time() - self.session_start

    @property
    def average_cost_per_op(self) -> float:
        """Average cost per operation."""
        if self.total_operations == 0:
            return 0.0
        return self.total_cost / self.total_operations


@dataclass
class ContextWindowInfo:
    """Context window utilization info."""
    current_tokens: int = 0
    max_tokens: int = 128000  # Gemini 2.0 Flash default
    warning_threshold: float = 0.8  # 80% utilization warning

    @property
    def utilization(self) -> float:
        """Utilization as percentage."""
        if self.max_tokens == 0:
            return 0.0
        return (self.current_tokens / self.max_tokens) * 100

    @property
    def is_warning(self) -> bool:
        """Is context window near limit?"""
        return self.utilization >= (self.warning_threshold * 100)

    @property
    def remaining_tokens(self) -> int:
        """Remaining tokens in context window."""
        return max(0, self.max_tokens - self.current_tokens)


class Dashboard:
    """
    Real-time status dashboard.
    
    Layout:
    ┌─────────────────────────────────────────────────────┐
    │ QWEN-DEV-CLI Dashboard          [12:40:15 UTC]     │
    ├─────────────────────────────────────────────────────┤
    │ System Metrics  │  Active Operations  │  Session   │
    │ CPU:    45%     │  ⚡ LLM Gen         │  Ops: 42   │
    │ Memory: 62%     │  📝 File Write      │  ✓: 40     │
    │ Tokens: 850/s   │  🔧 Tool Exec       │  ✗: 2      │
    │                 │                     │  Cost: $0.12│
    ├─────────────────────────────────────────────────────┤
    │ Recent History (last 5)                             │
    │ ✓ Code generation           2.3s    1.2K tok  $0.01 │
    │ ✓ File analysis            0.8s    0.5K tok  $0.00 │
    │ ✗ Validation failed        1.1s    0.3K tok  $0.00 │
    └─────────────────────────────────────────────────────┘
    
    Features:
    - Live system metrics (CPU, RAM)
    - Active operations list
    - Session statistics
    - Recent operation history
    - Context window utilization
    """

    def __init__(
        self,
        console: Optional[Console] = None,
        max_history: int = 5,
    ):
        """
        Initialize dashboard.
        
        Args:
            console: Rich console
            max_history: Max operations in history
        """
        self.console = console or Console()
        self.max_history = max_history

        # State
        self.active_operations: List[Operation] = []
        self.history: List[Operation] = []
        self.stats = SessionStats()
        self.context_window = ContextWindowInfo()

        # Live display
        self._live: Optional[Live] = None

    def add_operation(self, operation: Operation) -> None:
        """
        Add new operation to dashboard.
        
        Args:
            operation: Operation to track
        """
        self.active_operations.append(operation)
        self.stats.total_operations += 1

    def complete_operation(
        self,
        operation_id: str,
        status: OperationStatus,
        tokens_used: int = 0,
        cost: float = 0.0,
    ) -> None:
        """
        Mark operation as complete.
        
        Args:
            operation_id: Operation ID
            status: Final status
            tokens_used: Tokens consumed
            cost: Cost in USD
        """
        # Find in active
        op = None
        for i, active_op in enumerate(self.active_operations):
            if active_op.id == operation_id:
                op = self.active_operations.pop(i)
                break

        if not op:
            return

        # Update operation
        op.status = status
        op.end_time = time.time()
        op.tokens_used = tokens_used
        op.cost = cost

        # Update stats
        if status == OperationStatus.SUCCESS:
            self.stats.successful_operations += 1
        elif status == OperationStatus.ERROR:
            self.stats.failed_operations += 1

        self.stats.total_tokens += tokens_used
        self.stats.total_cost += cost

        # Add to history
        self.history.insert(0, op)
        if len(self.history) > self.max_history:
            self.history.pop()

    def update_context_window(self, current_tokens: int, max_tokens: Optional[int] = None) -> None:
        """
        Update context window utilization.
        
        Args:
            current_tokens: Current token count
            max_tokens: Max tokens (updates limit if provided)
        """
        self.context_window.current_tokens = current_tokens
        if max_tokens:
            self.context_window.max_tokens = max_tokens

    def render(self) -> Layout:
        """
        Render complete dashboard.
        
        Returns:
            Rich Layout
        """
        layout = Layout()

        # Header
        header = self._render_header()

        # Main panels (3 columns)
        metrics_panel = self._render_metrics()
        active_panel = self._render_active_operations()
        session_panel = self._render_session_stats()

        # History panel
        history_panel = self._render_history()

        # Context window (if warning)
        context_panel = None
        if self.context_window.is_warning:
            context_panel = self._render_context_warning()

        # Build layout
        layout.split_column(
            Layout(header, name="header", size=3),
            Layout(name="main", ratio=2),
            Layout(history_panel, name="history", size=8),
        )

        # Split main into 3 columns
        layout["main"].split_row(
            Layout(metrics_panel, name="metrics"),
            Layout(active_panel, name="active"),
            Layout(session_panel, name="session"),
        )

        # Add context warning if needed
        if context_panel:
            layout.split_column(
                layout["header"],
                Layout(context_panel, name="context_warning", size=3),
                layout["main"],
                layout["history"],
            )

        return layout

    def _render_header(self) -> Panel:
        """Render dashboard header."""
        now = datetime.now().strftime("%H:%M:%S UTC")

        text = Text()
        text.append("QWEN-DEV-CLI Dashboard", style="bold cyan")
        text.append(" " * 20)  # Spacer
        text.append(f"[{now}]", style="dim")

        return Panel(
            text,
            style="cyan",
            box=box.HEAVY,
        )

    def _render_metrics(self) -> Panel:
        """Render system metrics panel."""
        metrics = SystemMetrics.capture()

        table = Table.grid(padding=(0, 2))
        table.add_column(style="bold")
        table.add_column(justify="right")

        # CPU
        cpu_color = "green" if metrics.cpu_percent < 50 else "yellow" if metrics.cpu_percent < 80 else "red"
        table.add_row("CPU:", f"[{cpu_color}]{metrics.cpu_percent:.0f}%[/{cpu_color}]")

        # Memory
        mem_color = "green" if metrics.memory_percent < 50 else "yellow" if metrics.memory_percent < 80 else "red"
        table.add_row(
            "Memory:",
            f"[{mem_color}]{metrics.memory_percent:.0f}%[/{mem_color}] "
            f"({metrics.memory_used_mb:.0f}/{metrics.memory_total_mb:.0f} MB)"
        )

        # Token rate (if available)
        if self.stats.session_duration > 0:
            token_rate = self.stats.total_tokens / self.stats.session_duration
            table.add_row("Tokens/s:", f"{token_rate:.0f}")

        return Panel(
            table,
            title="[bold]System[/bold]",
            border_style="cyan",
            box=box.ROUNDED,
        )

    def _render_active_operations(self) -> Panel:
        """Render active operations panel."""
        content: Text | Table
        if not self.active_operations:
            content = Text("No active operations", style="dim italic")
        else:
            table = Table.grid(padding=(0, 1))
            table.add_column()
            table.add_column()

            for op in self.active_operations[:5]:  # Show max 5
                # Icon based on type
                icon = {
                    "llm": "⚡",
                    "file": "📝",
                    "tool": "🔧",
                    "workflow": "🔄",
                }.get(op.type, "▶")

                table.add_row(
                    Text(icon, style="yellow"),
                    Text(op.description, style="yellow"),
                )

            content = table

        return Panel(
            content,
            title="[bold]Active[/bold]",
            border_style="yellow",
            box=box.ROUNDED,
        )

    def _render_session_stats(self) -> Panel:
        """Render session statistics panel."""
        table = Table.grid(padding=(0, 2))
        table.add_column(style="bold")
        table.add_column(justify="right")

        # Operations
        table.add_row("Ops:", str(self.stats.total_operations))
        table.add_row(
            "✓:",
            f"[green]{self.stats.successful_operations}[/green] "
            f"({self.stats.success_rate:.0f}%)"
        )
        table.add_row("✗:", f"[red]{self.stats.failed_operations}[/red]")

        # Tokens
        if self.stats.total_tokens > 0:
            table.add_row("Tokens:", f"{self.stats.total_tokens:,}")

        # Cost
        if self.stats.total_cost > 0:
            table.add_row("Cost:", f"[green]${self.stats.total_cost:.4f}[/green]")

        # Session time
        duration = self.stats.session_duration
        if duration < 60:
            duration_str = f"{duration:.0f}s"
        elif duration < 3600:
            duration_str = f"{duration/60:.1f}m"
        else:
            duration_str = f"{duration/3600:.1f}h"

        table.add_row("Time:", duration_str)

        return Panel(
            table,
            title="[bold]Session[/bold]",
            border_style="green",
            box=box.ROUNDED,
        )

    def _render_history(self) -> Panel:
        """Render recent operation history."""
        content: Text | Table
        if not self.history:
            content = Text("No recent operations", style="dim italic")
        else:
            table = Table(
                show_header=True,
                header_style="bold",
                box=box.SIMPLE,
                padding=(0, 1),
            )

            table.add_column("Status", justify="center", width=3)
            table.add_column("Operation", style="cyan")
            table.add_column("Time", justify="right")
            table.add_column("Tokens", justify="right")
            table.add_column("Cost", justify="right")

            for op in self.history[:self.max_history]:
                # Status icon
                if op.status == OperationStatus.SUCCESS:
                    status = Text("✓", style="bold green")
                elif op.status == OperationStatus.ERROR:
                    status = Text("✗", style="bold red")
                elif op.status == OperationStatus.CANCELLED:
                    status = Text("○", style="dim")
                else:
                    status = Text("?", style="yellow")

                # Tokens
                tokens_str = f"{op.tokens_used/1000:.1f}K" if op.tokens_used >= 1000 else str(op.tokens_used)

                # Cost
                cost_str = f"${op.cost:.2f}" if op.cost >= 0.01 else f"${op.cost*1000:.1f}m"

                table.add_row(
                    status,
                    op.description[:40],  # Truncate long descriptions
                    op.duration_str,
                    tokens_str,
                    cost_str,
                )

            content = table

        return Panel(
            content,
            title="[bold]Recent History[/bold]",
            border_style="blue",
            box=box.ROUNDED,
        )

    def _render_context_warning(self) -> Panel:
        """Render context window warning."""
        ctx = self.context_window

        text = Text()
        text.append("⚠ Context Window: ", style="bold yellow")
        text.append(f"{ctx.utilization:.0f}% ", style="yellow")
        text.append(f"({ctx.current_tokens:,}/{ctx.max_tokens:,} tokens) ", style="dim")
        text.append(f"- {ctx.remaining_tokens:,} remaining", style="yellow")

        return Panel(text, border_style="yellow")

    async def live_display(self, refresh_rate: float = 1.0) -> None:
        """
        Start live dashboard display.
        
        Args:
            refresh_rate: Refresh interval in seconds
        """
        with Live(
            self.render(),
            console=self.console,
            refresh_per_second=1 / refresh_rate,
            screen=False,  # Don't clear screen
        ) as live:
            self._live = live

            try:
                while True:
                    live.update(self.render())
                    await asyncio.sleep(refresh_rate)
            except asyncio.CancelledError:
                live.update(self.render())
                raise
            finally:
                self._live = None

    def print_snapshot(self) -> None:
        """Print single dashboard snapshot (non-live)."""
        self.console.print(self.render())


# Convenience function
def create_dashboard(console: Optional[Console] = None) -> Dashboard:
    """
    Create dashboard instance.
    
    Args:
        console: Rich console
    
    Returns:
        Dashboard instance
    """
    return Dashboard(console=console)
