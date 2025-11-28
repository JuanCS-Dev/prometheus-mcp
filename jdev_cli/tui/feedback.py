"""
🎯 Visual Feedback System - Micro-interactions that delight

Inspired by Apple's Human Interface Guidelines:
- Immediate visual response
- Clear state changes
- Purposeful motion
- Respectful of user attention

Features:
- Button press effects
- Selection highlights
- Error shakes
- Success pulses
- Loading states with Biblical wisdom
"""

import time
from typing import Optional
from dataclasses import dataclass
from rich.console import Console
from rich.text import Text
from rich.panel import Panel

from .theme import COLORS
from .wisdom import get_random_verse
from .animations import Easing


@dataclass
class FeedbackConfig:
    """Configuration for visual feedback"""
    duration: float = 0.3
    intensity: float = 1.0
    sound: bool = False  # Future: terminal bell


class MicroInteraction:
    """Micro-interactions for common UI actions"""

    @staticmethod
    def button_press(text: str, pressed: bool = False) -> Text:
        """
        Button press effect
        
        Args:
            text: Button label
            pressed: Whether button is pressed
        
        Returns:
            Styled button text
        """
        if pressed:
            # Pressed state: darker, slightly smaller appearance
            styled = Text(f"▼ {text} ▼", style=f"bold {COLORS['accent_blue']}")
        else:
            # Normal state
            styled = Text(f"[ {text} ]", style=f"bold {COLORS['text_primary']}")

        return styled

    @staticmethod
    def selection_highlight(
        text: str,
        selected: bool = False,
        focused: bool = False,
    ) -> Text:
        """
        Selection/focus highlight effect
        
        Args:
            text: Item text
            selected: Whether item is selected
            focused: Whether item has focus
        
        Returns:
            Styled text with highlight
        """
        if selected and focused:
            # Both selected and focused: bold blue background
            return Text(f" ▸ {text} ", style=f"bold white on {COLORS['accent_blue']}")
        elif selected:
            # Selected but not focused: dimmed
            return Text(f" ✓ {text} ", style=f"{COLORS['accent_blue']}")
        elif focused:
            # Focused but not selected: subtle highlight
            return Text(f" › {text} ", style=f"bold {COLORS['text_primary']}")
        else:
            # Normal state
            return Text(f"   {text} ", style=COLORS['text_secondary'])

    @staticmethod
    def error_shake(console: Console, message: str, shakes: int = 3) -> None:
        """
        Shake animation for errors (like macOS login shake)
        
        Args:
            console: Rich console
            message: Error message
            shakes: Number of shakes (default 3)
        """
        panel = Panel(
            message,
            border_style=COLORS['error'],
            title="❌ Error",
        )

        for i in range(shakes * 2):
            # Calculate shake offset
            offset = 2 if i % 2 == 0 else -2

            # Clear and reprint with offset
            console.clear()
            console.print(" " * abs(offset) if offset > 0 else "")
            console.print(panel)

            time.sleep(0.05)

        # Final position (centered)
        console.clear()
        console.print(panel)

    @staticmethod
    def success_pulse(
        console: Console,
        message: str,
        pulses: int = 2,
    ) -> None:
        """
        Pulse animation for success (like iOS success checkmark)
        
        Args:
            console: Rich console
            message: Success message
            pulses: Number of pulses
        """
        for pulse in range(pulses):
            # Scale up
            for scale in [1.0, 1.1, 1.2, 1.1, 1.0]:
                console.clear()

                # Simulate scale with extra padding/spacing
                padding = int(scale * 2) - 2

                panel = Panel(
                    message,
                    border_style=COLORS['success'],
                    title="✅ Success",
                    padding=(padding, padding),
                )

                console.print(panel)
                time.sleep(0.05)

            time.sleep(0.1)


class LoadingState:
    """Loading states with Biblical wisdom"""

    def __init__(self, console: Optional[Console] = None):
        self.console = console or Console()
        self.current_verse = None

    def show_thinking(
        self,
        operation: str = "Processing",
        show_wisdom: bool = True,
    ) -> None:
        """
        Show thinking/loading state
        
        Args:
            operation: Operation being performed
            show_wisdom: Show Biblical verse
        """
        from .components.status import StatusBadge, SpinnerType

        # Get verse if enabled
        verse_text = ""
        if show_wisdom:
            self.current_verse = get_random_verse(category="perseverance")
            verse_text = f"\n\n💎 {self.current_verse['text']}\n   — {self.current_verse['reference']}"

        # Create loading panel
        spinner = StatusBadge.loading(
            f"{operation}...",
            spinner_type=SpinnerType.DOTS,
        )

        content = Text()
        content.append(spinner.render())
        content.append(verse_text, style=COLORS['text_secondary'])

        panel = Panel(
            content,
            border_style=COLORS['accent_purple'],
            title="⏳ Please wait",
            padding=(1, 2),
        )

        self.console.print(panel)

    def show_progress(
        self,
        current: int,
        total: int,
        operation: str = "Processing",
    ) -> None:
        """
        Show progress with percentage
        
        Args:
            current: Current progress
            total: Total items
            operation: Operation description
        """
        from .components.progress import ProgressBar, ProgressConfig

        percentage = int((current / total) * 100) if total > 0 else 0

        config = ProgressConfig(
            width=40,
            show_percentage=True,
            show_bar=True,
            show_time=True,
        )

        progress = ProgressBar(current, total, config)

        panel = Panel(
            progress.render(),
            border_style=COLORS['accent_blue'],
            title=f"⚡ {operation}",
            padding=(1, 2),
        )

        self.console.print(panel)


class StateTransition:
    """Smooth state transitions"""

    @staticmethod
    def fade_in(console: Console, content: str, steps: int = 10) -> None:
        """
        Fade in content
        
        Args:
            console: Rich console
            content: Content to fade in
            steps: Number of fade steps
        """
        for step in range(steps + 1):
            opacity = step / steps
            eased = Easing.ease_out(opacity)

            # Simulate opacity with color intensity
            # This is a simplification - real terminals don't support opacity
            alpha_char = " ░▒▓█"[int(eased * 4)]

            console.clear()

            # Show content with increasing "opacity"
            if eased < 0.3:
                console.print(f"[dim]{content}[/dim]")
            elif eased < 0.7:
                console.print(content)
            else:
                console.print(f"[bold]{content}[/bold]")

            time.sleep(0.03)

    @staticmethod
    def slide_in(
        console: Console,
        content: str,
        direction: str = "left",
        steps: int = 15,
    ) -> None:
        """
        Slide in content from direction
        
        Args:
            console: Rich console
            content: Content to slide in
            direction: 'left', 'right', 'top', 'bottom'
            steps: Number of animation steps
        """
        width = console.width

        for step in range(steps + 1):
            progress = step / steps
            eased = Easing.ease_out(progress)

            console.clear()

            if direction == "left":
                offset = int(width * (1 - eased))
                console.print(" " * offset + content)
            elif direction == "right":
                offset = int(width * (1 - eased))
                console.print(content.rjust(width - offset))
            else:  # top/bottom
                if direction == "top":
                    lines_offset = int(10 * (1 - eased))
                    console.print("\n" * lines_offset)
                console.print(content)

            time.sleep(0.02)


class HapticFeedback:
    """
    Haptic-like feedback through visual cues
    
    Since terminal can't provide true haptic feedback,
    we use rapid visual changes to create similar effect
    """

    @staticmethod
    def tap(console: Console) -> None:
        """Light tap feedback"""
        # Quick flash
        console.print("✓", style="bold green")
        time.sleep(0.05)

    @staticmethod
    def error_buzz(console: Console) -> None:
        """Error buzz feedback (like wrong password)"""
        # Rapid color changes
        for _ in range(3):
            console.print("✗", style="bold red")
            time.sleep(0.05)
            console.clear()
            time.sleep(0.05)

    @staticmethod
    def success_pop(console: Console) -> None:
        """Success pop feedback"""
        # Expanding checkmark
        symbols = ["·", "•", "●", "✓", "✓"]
        for symbol in symbols:
            console.clear()
            console.print(symbol, style="bold green", justify="center")
            time.sleep(0.04)


# Pre-configured feedback instances
standard_feedback = MicroInteraction()
loading_feedback = LoadingState()
