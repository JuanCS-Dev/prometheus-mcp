"""
Status Badge and Spinner Components - Visual status indicators.

Features:
- Status badges (success, error, warning, info)
- Animated spinners (dots, pulse, bounce)
- Color-coded by severity
- Smooth animations (60 FPS target)
- Composable with other components

Philosophy:
- Clear communication of state
- Non-blocking animations
- Purposeful color use
- Accessible (text alternatives)

Created: 2025-11-18 20:13 UTC
"""

import asyncio
from enum import Enum
from typing import Optional, AsyncIterator

from rich.text import Text
from rich.console import Console

from ..theme import COLORS
from ..styles import StyleCombinations


class StatusLevel(Enum):
    """Status severity levels."""
    SUCCESS = "success"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"
    PROCESSING = "processing"
    DEBUG = "debug"


class StatusBadge:
    """
    Status badge with icon and text.
    
    Examples:
        badge = StatusBadge("Operation complete", StatusLevel.SUCCESS)
        console.print(badge.render())
        
        # Animated
        async for frame in badge.render_animated():
            console.print(frame, end='\r')
    """

    # Icon mapping
    ICONS = {
        StatusLevel.SUCCESS: "✓",
        StatusLevel.ERROR: "✗",
        StatusLevel.WARNING: "⚠",
        StatusLevel.INFO: "ℹ",
        StatusLevel.PROCESSING: "⚡",
        StatusLevel.DEBUG: "🐛",
    }

    def __init__(
        self,
        text: str,
        level: StatusLevel = StatusLevel.INFO,
        show_icon: bool = True,
        animated: bool = False,
    ):
        """
        Initialize status badge.
        
        Args:
            text: Badge text
            level: Status level
            show_icon: Show icon before text
            animated: Animate badge (pulse effect)
        """
        self.text = text
        self.level = level
        self.show_icon = show_icon
        self.animated = animated

        # Get style for level
        self.style = StyleCombinations.status_badge(level.value)

    def render(self) -> Text:
        """
        Render status badge.
        
        Returns:
            Rich Text object
        """
        parts = []

        if self.show_icon:
            icon = self.ICONS.get(self.level, "•")
            parts.append(icon)

        parts.append(self.text)

        content = " ".join(parts)
        return Text(content, style=self.style)

    async def render_animated(
        self,
        duration: float = 1.5,
        fps: int = 30,
    ) -> AsyncIterator[Text]:
        """
        Render badge with pulse animation.
        
        Args:
            duration: Animation duration in seconds
            fps: Frames per second
            
        Yields:
            Text frames for animation
        """
        if not self.animated:
            yield self.render()
            return

        frames = int(duration * fps)
        frame_delay = 1.0 / fps

        for frame in range(frames):
            # Pulse effect: brightness oscillates
            progress = frame / frames
            brightness = 0.5 + 0.5 * abs(1 - 2 * progress)

            # Render with varying brightness
            # (In terminal, we approximate with bold/normal)
            if brightness > 0.7:
                text = self.render()
                text.stylize("bold")
            else:
                text = self.render()

            yield text
            await asyncio.sleep(frame_delay)

        # Final static frame
        yield self.render()


class SpinnerStyle(Enum):
    """Spinner animation styles."""
    DOTS = "dots"
    PULSE = "pulse"
    BOUNCE = "bounce"
    LINE = "line"
    DOTS_PULSE = "dots_pulse"


class Spinner:
    """
    Animated spinner for loading/processing states.
    
    Examples:
        spinner = Spinner("Loading...", style=SpinnerStyle.DOTS)
        
        # Render frames
        async for frame in spinner.spin():
            console.print(frame, end='\r')
    """

    # Spinner frame sequences
    FRAMES = {
        SpinnerStyle.DOTS: ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏'],
        SpinnerStyle.PULSE: ['⣾', '⣽', '⣻', '⢿', '⡿', '⣟', '⣯', '⣷'],
        SpinnerStyle.BOUNCE: ['▖', '▘', '▝', '▗'],
        SpinnerStyle.LINE: ['|', '/', '─', '\\'],
        SpinnerStyle.DOTS_PULSE: ['⠁', '⠂', '⠄', '⡀', '⢀', '⠠', '⠐', '⠈'],
    }

    def __init__(
        self,
        text: str = "Processing...",
        style: SpinnerStyle = SpinnerStyle.DOTS,
        color: Optional[str] = None,
    ):
        """
        Initialize spinner.
        
        Args:
            text: Spinner text
            style: Animation style
            color: Text color (hex or theme key)
        """
        self.text = text
        self.style = style
        self.color = color or COLORS['accent_blue']
        self.frames = self.FRAMES[style]

    def render(self, frame_index: int = 0) -> Text:
        """
        Render single spinner frame.
        
        Args:
            frame_index: Frame index (cycles through frames)
            
        Returns:
            Rich Text object
        """
        frame_char = self.frames[frame_index % len(self.frames)]
        content = f"{frame_char} {self.text}"
        return Text(content, style=self.color)

    async def spin(
        self,
        duration: Optional[float] = None,
        fps: int = 12,
    ) -> AsyncIterator[Text]:
        """
        Animated spinner generator.
        
        Args:
            duration: Duration in seconds (None = infinite)
            fps: Frames per second
            
        Yields:
            Text frames for animation
            
        Example:
            async for frame in spinner.spin(duration=5.0):
                console.print(frame, end='\r')
                await asyncio.sleep(1/12)
        """
        frame_index = 0
        frame_delay = 1.0 / fps
        start_time = asyncio.get_event_loop().time()

        while True:
            yield self.render(frame_index)
            frame_index = (frame_index + 1) % len(self.frames)

            # Check duration
            if duration is not None:
                elapsed = asyncio.get_event_loop().time() - start_time
                if elapsed >= duration:
                    break

            await asyncio.sleep(frame_delay)


class StatusIndicator:
    """
    Combined status indicator with icon, text, and optional spinner.
    
    Examples:
        # Static status
        status = StatusIndicator("Analyzing code", StatusLevel.INFO)
        console.print(status.render())
        
        # With spinner
        status = StatusIndicator(
            "Processing...",
            StatusLevel.PROCESSING,
            spinner=True
        )
        async for frame in status.render_animated():
            console.print(frame, end='\r')
    """

    def __init__(
        self,
        text: str,
        level: StatusLevel = StatusLevel.INFO,
        spinner: bool = False,
        spinner_style: SpinnerStyle = SpinnerStyle.DOTS,
    ):
        """
        Initialize status indicator.
        
        Args:
            text: Status text
            level: Status level
            spinner: Show animated spinner
            spinner_style: Spinner animation style
        """
        self.text = text
        self.level = level
        self.show_spinner = spinner
        self.spinner_style = spinner_style

        # Create badge
        self.badge = StatusBadge(text, level, show_icon=not spinner, animated=False)

        # Create spinner if needed
        if spinner:
            color = self._get_color_for_level(level)
            self.spinner = Spinner(text, spinner_style, color)
        else:
            self.spinner = None

    def _get_color_for_level(self, level: StatusLevel) -> str:
        """Get color for status level."""
        color_map = {
            StatusLevel.SUCCESS: COLORS['accent_green'],
            StatusLevel.ERROR: COLORS['accent_red'],
            StatusLevel.WARNING: COLORS['accent_yellow'],
            StatusLevel.INFO: COLORS['accent_blue'],
            StatusLevel.PROCESSING: COLORS['accent_purple'],
            StatusLevel.DEBUG: COLORS['text_tertiary'],
        }
        return color_map.get(level, COLORS['text_primary'])

    def render(self) -> Text:
        """
        Render status indicator (static frame).
        
        Returns:
            Rich Text object
        """
        if self.show_spinner:
            return self.spinner.render(0)
        else:
            return self.badge.render()

    async def render_animated(
        self,
        duration: Optional[float] = None,
        fps: int = 12,
    ) -> AsyncIterator[Text]:
        """
        Render animated status indicator.
        
        Args:
            duration: Animation duration (None = infinite)
            fps: Frames per second
            
        Yields:
            Text frames for animation
        """
        if self.show_spinner:
            async for frame in self.spinner.spin(duration=duration, fps=fps):
                yield frame
        else:
            async for frame in self.badge.render_animated(duration=duration or 1.5, fps=fps):
                yield frame


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def create_success_badge(text: str) -> StatusBadge:
    """Create success badge."""
    return StatusBadge(text, StatusLevel.SUCCESS)


def create_error_badge(text: str) -> StatusBadge:
    """Create error badge."""
    return StatusBadge(text, StatusLevel.ERROR)


def create_warning_badge(text: str) -> StatusBadge:
    """Create warning badge."""
    return StatusBadge(text, StatusLevel.WARNING)


def create_info_badge(text: str) -> StatusBadge:
    """Create info badge."""
    return StatusBadge(text, StatusLevel.INFO)


def create_processing_indicator(text: str) -> StatusIndicator:
    """Create processing indicator with spinner."""
    return StatusIndicator(text, StatusLevel.PROCESSING, spinner=True)


async def show_spinner_for(
    console: Console,
    text: str,
    duration: float,
    style: SpinnerStyle = SpinnerStyle.DOTS,
):
    """
    Show spinner for a duration then clear.
    
    Args:
        console: Rich console
        text: Spinner text
        duration: Duration in seconds
        style: Spinner style
        
    Example:
        await show_spinner_for(console, "Loading...", 3.0)
    """
    spinner = Spinner(text, style)

    async for frame in spinner.spin(duration=duration, fps=12):
        console.print(frame, end='\r')
        await asyncio.sleep(1/12)

    # Clear line
    console.print(" " * (len(text) + 5), end='\r')
