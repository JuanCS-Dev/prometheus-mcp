"""Reactive TUI renderer with zero UI blocking."""
import logging
logger = logging.getLogger(__name__)

import asyncio
from dataclasses import dataclass
from enum import Enum
from typing import Optional
from collections import deque

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.live import Live
from rich.panel import Panel
from rich.layout import Layout


class RenderEventType(Enum):
    """Render event types."""
    OUTPUT = "output"
    PROGRESS = "progress"
    COMPLETE = "complete"
    ERROR = "error"
    SPINNER = "spinner"
    PROGRESS_BAR = "progress_bar"


@dataclass
class RenderEvent:
    """UI render event."""
    event_type: RenderEventType
    content: str
    metadata: dict


class ReactiveRenderer:
    """Reactive TUI renderer with zero blocking."""

    def __init__(self, console: Optional[Console] = None):
        self.console = console or Console()
        self._event_queue: asyncio.Queue = asyncio.Queue()
        self._running = False
        self._render_task: Optional[asyncio.Task] = None
        self._output_buffer = deque(maxlen=1000)
        self._progress: Optional[Progress] = None
        self._live: Optional[Live] = None
        self._active_tasks: dict = {}  # task_id -> task object

    async def start(self) -> None:
        """Start renderer loop."""
        if self._running:
            return

        self._running = True
        self._render_task = asyncio.create_task(self._render_loop())

    async def stop(self) -> None:
        """Stop renderer loop."""
        if not self._running:
            return

        self._running = False
        if self._render_task:
            self._render_task.cancel()
            try:
                await self._render_task
            except asyncio.CancelledError:
                logger.debug("Render task cancelled")

    async def emit(self, event: RenderEvent) -> None:
        """Emit render event (non-blocking)."""
        await self._event_queue.put(event)

    async def _render_loop(self) -> None:
        """Main render loop (UI thread)."""
        try:
            while self._running:
                try:
                    event = await asyncio.wait_for(
                        self._event_queue.get(),
                        timeout=0.1
                    )
                except asyncio.TimeoutError:
                    continue

                await self._render_event(event)

        except asyncio.CancelledError:
            logger.debug("Event renderer cancelled")

    async def _render_event(self, event: RenderEvent) -> None:
        """Render single event."""
        if event.event_type == RenderEventType.OUTPUT:
            self.console.print(event.content, end='')
            self._output_buffer.append(event.content)

        elif event.event_type == RenderEventType.COMPLETE:
            self.console.print(f"[green]✓[/green] {event.content}")

        elif event.event_type == RenderEventType.ERROR:
            self.console.print(f"[red]✗[/red] {event.content}")

        elif event.event_type == RenderEventType.SPINNER:
            # Enhanced spinner rendering
            task_id = event.metadata.get('task_id')
            message = event.metadata.get('message', 'Processing...')
            self.console.print(f"[cyan]⠋[/cyan] {message}", end='\r')

        elif event.event_type == RenderEventType.PROGRESS_BAR:
            # Progress bar updates
            task_id = event.metadata.get('task_id')
            completed = event.metadata.get('completed', 0)
            total = event.metadata.get('total', 100)
            description = event.metadata.get('description', 'Progress')

            if not self._progress:
                self._init_progress()

            if task_id not in self._active_tasks:
                self._active_tasks[task_id] = self._progress.add_task(
                    description, total=total
                )

            self._progress.update(
                self._active_tasks[task_id],
                completed=completed,
                description=description
            )

    def _init_progress(self) -> None:
        """Initialize progress display."""
        self._progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=self.console
        )
        self._live = Live(self._progress, console=self.console, refresh_per_second=10)
        self._live.start()

    def get_output_buffer(self) -> list[str]:
        """Get current output buffer."""
        return list(self._output_buffer)


class ConcurrentRenderer:
    """Manages multiple parallel process renderings without glitches."""

    def __init__(self, console: Optional[Console] = None):
        self.console = console or Console()
        self._lock = asyncio.Lock()
        self._panels: dict = {}  # process_id -> Panel
        self._layout: Optional[Layout] = None

    async def add_process(self, process_id: str, title: str) -> None:
        """Add new process to rendering."""
        async with self._lock:
            self._panels[process_id] = Panel(
                "",
                title=f"[bold blue]{title}[/bold blue]",
                border_style="blue"
            )
            self._update_layout()

    async def update_process(self, process_id: str, content: str) -> None:
        """Update process output (thread-safe)."""
        async with self._lock:
            if process_id in self._panels:
                self._panels[process_id] = Panel(
                    content,
                    title=self._panels[process_id].title,
                    border_style="blue"
                )
                self._update_layout()

    async def complete_process(self, process_id: str, success: bool = True) -> None:
        """Mark process as complete."""
        async with self._lock:
            if process_id in self._panels:
                style = "green" if success else "red"
                symbol = "✓" if success else "✗"
                title = self._panels[process_id].title
                self._panels[process_id] = Panel(
                    self._panels[process_id].renderable,
                    title=f"{title} [{style}]{symbol}[/{style}]",
                    border_style=style
                )
                self._update_layout()

    def _update_layout(self) -> None:
        """Update layout with all panels (race-free)."""
        if not self._layout:
            self._layout = Layout()

        # Clear and rebuild layout
        self._layout.split_column(*[panel for panel in self._panels.values()])

        # Render
        self.console.print(self._layout)
