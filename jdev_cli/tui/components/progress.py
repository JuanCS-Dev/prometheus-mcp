"""
from ._enums import ProgressStyle
Progress Bar Component - Animated progress indicators.

Features:
- Smooth animation with easing (cubic ease-out)
- Time estimates (elapsed + remaining)
- Percentage + fraction display
- Color gradient (0% → 100%)
- Multiple bar styles
- Non-blocking async updates

Philosophy:
- Show progress, not just status
- Predictable (time estimates)
- Smooth (no jumpy updates)
- Informative (percentage, fraction, time)

Created: 2025-11-18 20:13 UTC
"""

import asyncio
import time
from typing import Optional
from dataclasses import dataclass

from rich.console import Console
from rich.progress import (
    Progress,
    BarColumn,
    TextColumn,
    TimeRemainingColumn,
    TimeElapsedColumn,
    TaskProgressColumn,
    SpinnerColumn,
)
from rich.text import Text

from ..theme import COLORS
from ..styles import PRESET_STYLES


@dataclass
class ProgressState:
    """Progress state data."""
    current: float
    total: float
    description: str = ""
    start_time: float = 0.0

    def __post_init__(self):
        if self.start_time == 0.0:
            self.start_time = time.time()

    @property
    def percentage(self) -> float:
        """Progress as percentage (0-100)."""
        if self.total == 0:
            return 0.0
        return min(100.0, (self.current / self.total) * 100)

    @property
    def elapsed(self) -> float:
        """Time elapsed in seconds."""
        return time.time() - self.start_time

    @property
    def remaining(self) -> Optional[float]:
        """Estimated time remaining in seconds."""
        if self.current == 0 or self.percentage >= 100:
            return None

        rate = self.current / self.elapsed
        remaining_items = self.total - self.current
        return remaining_items / rate if rate > 0 else None


class ProgressBar:
    """
    Animated progress bar with easing and time estimates.
    
    Examples:
        progress = ProgressBar(0, 100, "Processing files")
        
        # Update with animation
        await progress.update_animated(50)
        
        # Render current state
        console.print(progress.render())
    """

    def __init__(
        self,
        current: float,
        total: float,
        description: str = "",
        width: int = 40,
        show_percentage: bool = True,
        show_fraction: bool = True,
        show_time: bool = True,
    ):
        """
        Initialize progress bar.
        
        Args:
            current: Current progress value
            total: Total target value
            description: Progress description
            width: Bar width in characters
            show_percentage: Show percentage (%)
            show_fraction: Show fraction (current/total)
            show_time: Show time estimates
        """
        self.state = ProgressState(current, total, description)
        self.width = width
        self.show_percentage = show_percentage
        self.show_fraction = show_fraction
        self.show_time = show_time

    def _ease_out_cubic(self, t: float) -> float:
        """
        Cubic ease-out easing function.
        
        Args:
            t: Progress (0.0 to 1.0)
            
        Returns:
            Eased progress (0.0 to 1.0)
        """
        return 1 - pow(1 - t, 3)

    def _interpolate(self, start: float, end: float, progress: float) -> float:
        """
        Interpolate between start and end with easing.
        
        Args:
            start: Start value
            end: End value
            progress: Progress (0.0 to 1.0)
            
        Returns:
            Interpolated value
        """
        eased = self._ease_out_cubic(progress)
        return start + (end - start) * eased

    def _get_bar_color(self, percentage: float) -> str:
        """
        Get bar color based on progress (gradient effect).
        
        Args:
            percentage: Progress percentage (0-100)
            
        Returns:
            Color hex string
        """
        if percentage < 33:
            return COLORS['accent_red']
        elif percentage < 66:
            return COLORS['accent_yellow']
        else:
            return COLORS['accent_green']

    def _render_bar(self, percentage: float) -> Text:
        """
        Render progress bar visual.
        
        Args:
            percentage: Progress percentage (0-100)
            
        Returns:
            Rich Text object
        """
        filled = int((percentage / 100) * self.width)
        empty = self.width - filled

        # Progress characters
        filled_char = "▓"
        empty_char = "░"

        # Color based on progress
        color = self._get_bar_color(percentage)

        # Build bar
        bar_text = filled_char * filled + empty_char * empty
        return Text(bar_text, style=color)

    def _format_time(self, seconds: Optional[float]) -> str:
        """
        Format seconds as human-readable time.
        
        Args:
            seconds: Time in seconds
            
        Returns:
            Formatted string (e.g., "2.3s", "1m 30s")
        """
        if seconds is None:
            return "—"

        if seconds < 60:
            return f"{seconds:.1f}s"

        minutes = int(seconds // 60)
        remaining_seconds = int(seconds % 60)
        return f"{minutes}m {remaining_seconds}s"

    def render(self) -> Text:
        """
        Render complete progress bar.
        
        Returns:
            Rich Text object
        """
        parts = []

        # Description
        if self.state.description:
            parts.append(Text(self.state.description + ": ", style=PRESET_STYLES.PRIMARY))

        # Bar
        parts.append(self._render_bar(self.state.percentage))

        # Percentage
        if self.show_percentage:
            pct_text = f" {self.state.percentage:.0f}%"
            parts.append(Text(pct_text, style=PRESET_STYLES.SECONDARY))

        # Fraction
        if self.show_fraction:
            fraction_text = f" ({self.state.current:.0f}/{self.state.total:.0f})"
            parts.append(Text(fraction_text, style=PRESET_STYLES.TERTIARY))

        # Time
        if self.show_time:
            elapsed_str = self._format_time(self.state.elapsed)
            remaining_str = self._format_time(self.state.remaining)
            time_text = f" ⏱️  {elapsed_str} • ~{remaining_str} remaining"
            parts.append(Text(time_text, style=PRESET_STYLES.TIMESTAMP))

        # Combine all parts
        result = Text()
        for part in parts:
            result.append(part)

        return result

    async def update_animated(
        self,
        new_value: float,
        duration: float = 0.5,
        fps: int = 30,
    ):
        """
        Update progress with smooth animation.
        
        Args:
            new_value: New progress value
            duration: Animation duration in seconds
            fps: Frames per second
            
        Example:
            await progress.update_animated(75, duration=0.5)
        """
        start_value = self.state.current
        frames = int(duration * fps)
        frame_delay = duration / frames

        for frame in range(frames + 1):
            progress_ratio = frame / frames
            interpolated = self._interpolate(start_value, new_value, progress_ratio)
            self.state.current = interpolated
            await asyncio.sleep(frame_delay)

        # Ensure final value is exact
        self.state.current = new_value

    async def animate_to(
        self,
        target: float,
        duration: float = 0.5,
        console: Optional[Console] = None,
    ):
        """
        Animate progress to target with live rendering.
        
        Args:
            target: Target progress value
            duration: Animation duration
            console: Rich console for rendering
            
        Example:
            await progress.animate_to(100, duration=2.0, console=console)
        """
        console = console or Console()
        start_value = self.state.current
        start_time = time.time()

        while True:
            elapsed = time.time() - start_time
            if elapsed >= duration:
                break

            progress_ratio = elapsed / duration
            interpolated = self._interpolate(start_value, target, progress_ratio)
            self.state.current = interpolated

            # Render current frame
            console.print(self.render(), end='\r')
            await asyncio.sleep(1/30)  # 30 FPS

        # Final frame
        self.state.current = target
        console.print(self.render())


class MultiProgressBar:
    """
    Manage multiple progress bars (for parallel tasks).
    
    Examples:
        multi = MultiProgressBar()
        task1 = multi.add_task("Task 1", total=100)
        task2 = multi.add_task("Task 2", total=50)
        
        await multi.update(task1, 50)
        await multi.update(task2, 25)
    """

    def __init__(self, console: Optional[Console] = None):
        """
        Initialize multi-progress bar manager.
        
        Args:
            console: Rich console instance
        """
        self.console = console or Console()
        self.progress_bars: dict[int, ProgressBar] = {}
        self.next_id = 0

    def add_task(
        self,
        description: str,
        total: float,
        **kwargs,
    ) -> int:
        """
        Add new progress bar.
        
        Args:
            description: Task description
            total: Total progress value
            **kwargs: Additional ProgressBar arguments
            
        Returns:
            Task ID
        """
        task_id = self.next_id
        self.next_id += 1

        bar = ProgressBar(0, total, description, **kwargs)
        self.progress_bars[task_id] = bar

        return task_id

    async def update(
        self,
        task_id: int,
        value: float,
        animated: bool = True,
    ):
        """
        Update progress for task.
        
        Args:
            task_id: Task ID
            value: New progress value
            animated: Animate transition
        """
        if task_id not in self.progress_bars:
            return

        bar = self.progress_bars[task_id]

        if animated:
            await bar.update_animated(value)
        else:
            bar.state.current = value

    def render_all(self):
        """Render all progress bars."""
        for task_id, bar in self.progress_bars.items():
            self.console.print(bar.render())

    def complete(self, task_id: int):
        """Mark task as complete."""
        if task_id in self.progress_bars:
            bar = self.progress_bars[task_id]
            bar.state.current = bar.state.total


# =============================================================================
# RICH PROGRESS WRAPPER (for Rich's built-in Progress)
# =============================================================================

def create_rich_progress(
    console: Optional[Console] = None,
    transient: bool = False,
) -> Progress:
    """
    Create Rich Progress instance with our theme.
    
    Args:
        console: Rich console
        transient: Progress disappears after completion
        
    Returns:
        Rich Progress object
        
    Example:
        progress = create_rich_progress()
        task = progress.add_task("Processing", total=100)
        
        with progress:
            for i in range(100):
                progress.update(task, advance=1)
                time.sleep(0.1)
    """
    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(
            complete_style=COLORS['accent_green'],
            finished_style=COLORS['accent_green'],
            pulse_style=COLORS['accent_blue'],
        ),
        TaskProgressColumn(),
        TimeElapsedColumn(),
        TimeRemainingColumn(),
        console=console,
        transient=transient,
    )


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

async def show_progress(
    console: Console,
    total: int,
    description: str = "Processing",
    duration: float = 2.0,
):
    """
    Show animated progress bar for demonstration.
    
    Args:
        console: Rich console
        total: Total items
        description: Progress description
        duration: Total duration in seconds
        
    Example:
        await show_progress(console, 100, "Loading files", 3.0)
    """
    bar = ProgressBar(0, total, description)
    delay = duration / total

    for i in range(total + 1):
        await bar.update_animated(i, duration=delay)
        console.print(bar.render(), end='\r')
        await asyncio.sleep(delay)

    console.print()


# =============================================================================
# FACTORY FUNCTIONS
# =============================================================================

def create_progress_bar(
    current: int = 0,
    total: int = 100,
    description: str = "Processing"
) -> ProgressBar:
    """
    Create a progress bar with default settings.
    
    Args:
        current: Current progress value
        total: Total progress value
        description: Progress description
        
    Returns:
        Configured ProgressBar instance
        
    Example:
        bar = create_progress_bar(0, 100, "Loading files")
        bar.update(50)
        console.print(bar.render())
    """
    return ProgressBar(current, total, description)
