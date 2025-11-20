"""
🎬 TUI Animations - Apple-style smooth transitions
Implements cubic bezier easing, fade effects, and smooth state changes

UX Polish Sprint additions:
- Loading spinners (dots, bars, braille)
- Fade in/out effects
- Micro-interactions (pulse, bounce)
"""

import time
import math
import asyncio
from typing import Callable, Optional, Literal
from dataclasses import dataclass
from rich.console import Console
from rich.text import Text


@dataclass
class AnimationConfig:
    """Configuration for animations"""
    duration: float = 0.3  # seconds
    easing: str = "ease-out"  # ease-in, ease-out, ease-in-out, linear
    fps: int = 60


class Easing:
    """Easing functions for smooth animations"""
    
    @staticmethod
    def linear(t: float) -> float:
        """Linear easing"""
        return t
    
    @staticmethod
    def ease_in(t: float) -> float:
        """Ease-in (cubic)"""
        return t * t * t
    
    @staticmethod
    def ease_out(t: float) -> float:
        """Ease-out (cubic) - Apple's favorite"""
        return 1 - pow(1 - t, 3)
    
    @staticmethod
    def ease_in_out(t: float) -> float:
        """Ease-in-out (cubic)"""
        if t < 0.5:
            return 4 * t * t * t
        return 1 - pow(-2 * t + 2, 3) / 2
    
    @staticmethod
    def spring(t: float) -> float:
        """Spring easing (bouncy)"""
        return 1 - math.cos(t * math.pi * 2) * (1 - t)
    
    @staticmethod
    def elastic(t: float) -> float:
        """Elastic easing"""
        if t == 0 or t == 1:
            return t
        p = 0.3
        return pow(2, -10 * t) * math.sin((t - p / 4) * (2 * math.pi) / p) + 1


def get_easing_function(name: str) -> Callable[[float], float]:
    """Get easing function by name"""
    easing_map = {
        "linear": Easing.linear,
        "ease-in": Easing.ease_in,
        "ease-out": Easing.ease_out,
        "ease-in-out": Easing.ease_in_out,
        "spring": Easing.spring,
        "elastic": Easing.elastic,
    }
    return easing_map.get(name, Easing.ease_out)


class Animator:
    """Handles smooth animations"""
    
    def __init__(self, config: Optional[AnimationConfig] = None):
        self.config = config or AnimationConfig()
        self.easing_func = get_easing_function(self.config.easing)
    
    def animate(
        self,
        start: float,
        end: float,
        callback: Callable[[float], None],
        duration: Optional[float] = None,
    ) -> None:
        """
        Animate from start to end value
        
        Args:
            start: Starting value
            end: Ending value
            callback: Function to call with interpolated value
            duration: Override default duration
        """
        duration = duration or self.config.duration
        frame_time = 1.0 / self.config.fps
        elapsed = 0.0
        
        while elapsed < duration:
            t = elapsed / duration
            eased = self.easing_func(t)
            value = start + (end - start) * eased
            callback(value)
            
            time.sleep(frame_time)
            elapsed += frame_time
        
        # Final frame
        callback(end)
    
    def fade_in(self, callback: Callable[[float], None]) -> None:
        """Fade in from 0 to 1"""
        self.animate(0.0, 1.0, callback)
    
    def fade_out(self, callback: Callable[[float], None]) -> None:
        """Fade out from 1 to 0"""
        self.animate(1.0, 0.0, callback)


class StateTransition:
    """Manages state transitions with animations"""
    
    def __init__(self, initial_state: str):
        self.current_state = initial_state
        self.animator = Animator(AnimationConfig(duration=0.2))
    
    def transition_to(
        self,
        new_state: str,
        on_exit: Optional[Callable] = None,
        on_enter: Optional[Callable] = None,
    ) -> None:
        """
        Transition from current state to new state
        
        Args:
            new_state: Target state
            on_exit: Callback when leaving current state
            on_enter: Callback when entering new state
        """
        if new_state == self.current_state:
            return
        
        # Exit current state with fade-out
        if on_exit:
            self.animator.fade_out(lambda opacity: on_exit(opacity))
        
        # Update state
        old_state = self.current_state
        self.current_state = new_state
        
        # Enter new state with fade-in
        if on_enter:
            self.animator.fade_in(lambda opacity: on_enter(opacity))


class LoadingAnimation:
    """Smooth loading animations"""
    
    SPINNERS = {
        "dots": ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"],
        "line": ["—", "\\", "|", "/"],
        "arrow": ["←", "↖", "↑", "↗", "→", "↘", "↓", "↙"],
        "box": ["◰", "◳", "◲", "◱"],
        "bounce": ["⠁", "⠂", "⠄", "⡀", "⢀", "⠠", "⠐", "⠈"],
    }
    
    def __init__(self, style: str = "dots", speed: float = 0.08):
        self.frames = self.SPINNERS.get(style, self.SPINNERS["dots"])
        self.speed = speed
        self.current_frame = 0
    
    def next_frame(self) -> str:
        """Get next frame in animation"""
        frame = self.frames[self.current_frame]
        self.current_frame = (self.current_frame + 1) % len(self.frames)
        return frame
    
    def animate_pulse(self, text: str, width: int = 40) -> str:
        """Animate a pulsing progress bar"""
        frame = self.current_frame % width
        bar = " " * width
        
        if frame < width // 2:
            pos = frame
        else:
            pos = width - frame - 1
        
        bar = bar[:pos] + "█" + bar[pos + 1:]
        self.current_frame += 1
        
        return f"{text} [{bar}]"


class SlideTransition:
    """Slide-in/slide-out transitions"""
    
    @staticmethod
    def slide_in(text: str, width: int, progress: float) -> str:
        """Slide text in from right"""
        visible_chars = int(len(text) * progress)
        return text[:visible_chars].rjust(width)
    
    @staticmethod
    def slide_out(text: str, width: int, progress: float) -> str:
        """Slide text out to left"""
        visible_chars = int(len(text) * (1 - progress))
        return text[:visible_chars].ljust(width)


# Pre-configured animators
smooth_animator = Animator(AnimationConfig(duration=0.3, easing="ease-out"))
quick_animator = Animator(AnimationConfig(duration=0.15, easing="ease-out"))
spring_animator = Animator(AnimationConfig(duration=0.4, easing="spring"))


# ===== UX POLISH SPRINT: ADVANCED ANIMATIONS =====

class LoadingSpinner:
    """
    Modern loading spinners (UX Polish Sprint)
    
    Styles:
    - dots: "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏" (braille, 10 frames)
    - line: "|/-\\" (classic, 4 frames)
    - arc: "◜◠◝◞◡◟" (arc, 6 frames)
    - dots3: "⣾⣽⣻⢿⡿⣟⣯⣷" (3-dot, 8 frames)
    - pulse: "●○○ ●●○ ●●● ○●● ○○●" (pulse, 5 frames)
    """
    
    SPINNERS = {
        "dots": ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"],
        "line": ["|", "/", "-", "\\"],
        "arc": ["◜", "◠", "◝", "◞", "◡", "◟"],
        "dots3": ["⣾", "⣽", "⣻", "⢿", "⡿", "⣟", "⣯", "⣷"],
        "pulse": ["●○○", "●●○", "●●●", "○●●", "○○●"],
        "bounce": ["⠁", "⠂", "⠄", "⡀", "⢀", "⠠", "⠐", "⠈"],
    }
    
    def __init__(self, style: str = "dots", color: str = "cyan"):
        """
        Initialize spinner
        
        Args:
            style: Spinner style (dots, line, arc, dots3, pulse, bounce)
            color: Rich color name
        """
        self.frames = self.SPINNERS.get(style, self.SPINNERS["dots"])
        self.color = color
        self.current_frame = 0
        self.running = False
    
    def get_frame(self) -> Text:
        """Get current frame as Rich Text"""
        frame = self.frames[self.current_frame % len(self.frames)]
        self.current_frame += 1
        return Text(frame, style=f"bold {self.color}")
    
    async def spin(self, console: Console, message: str = "Loading", duration: float = 2.0):
        """
        Animate spinner for duration
        
        Args:
            console: Rich Console
            message: Message to show
            duration: How long to spin (seconds)
        """
        from rich.live import Live
        
        self.running = True
        start_time = time.time()
        
        with Live(console=console, refresh_per_second=10) as live:
            while self.running and (time.time() - start_time) < duration:
                frame = self.get_frame()
                text = Text()
                text.append(frame)
                text.append(f" {message}", style="dim")
                live.update(text)
                await asyncio.sleep(0.1)
    
    def stop(self):
        """Stop spinner"""
        self.running = False


class FadeEffect:
    """
    Fade in/out effects (UX Polish Sprint)
    
    Uses opacity simulation with dim/bold styles
    """
    
    @staticmethod
    def fade_in(text: str, progress: float, color: str = "white") -> Text:
        """
        Fade text in (0.0 → 1.0)
        
        Args:
            text: Text to fade
            progress: 0.0 (invisible) to 1.0 (full)
            color: Text color
        """
        result = Text(text)
        
        if progress < 0.3:
            # Very dim (0-30%)
            result.stylize(f"dim {color}")
        elif progress < 0.6:
            # Medium (30-60%)
            result.stylize(color)
        else:
            # Bold (60-100%)
            result.stylize(f"bold {color}")
        
        return result
    
    @staticmethod
    def fade_out(text: str, progress: float, color: str = "white") -> Text:
        """
        Fade text out (1.0 → 0.0)
        
        Args:
            text: Text to fade
            progress: 1.0 (full) to 0.0 (invisible)
            color: Text color
        """
        return FadeEffect.fade_in(text, 1.0 - progress, color)
    
    @staticmethod
    async def fade_in_animated(
        console: Console,
        text: str,
        duration: float = 0.5,
        color: str = "white"
    ):
        """Animate fade in effect"""
        from rich.live import Live
        
        steps = 20
        delay = duration / steps
        
        with Live(console=console, refresh_per_second=30) as live:
            for i in range(steps + 1):
                progress = i / steps
                faded = FadeEffect.fade_in(text, progress, color)
                live.update(faded)
                await asyncio.sleep(delay)


class MicroInteraction:
    """
    Subtle micro-interactions (UX Polish Sprint)
    
    Examples:
    - Pulse: Scale effect (success, error)
    - Bounce: Attention grabber
    - Shake: Error indication
    """
    
    @staticmethod
    def pulse(text: str, scale: float = 1.2) -> str:
        """
        Pulse effect (grow slightly)
        
        Args:
            text: Text to pulse
            scale: Scale factor (1.0 = normal, 1.2 = 20% bigger)
        """
        # Simulate scale with spacing
        if scale > 1.0:
            return f" {text} "
        return text
    
    @staticmethod
    async def bounce_text(console: Console, text: str, color: str = "cyan"):
        """
        Bounce animation (4 frames)
        
        Args:
            console: Rich Console
            text: Text to bounce
            color: Text color
        """
        from rich.live import Live
        
        # Bounce positions (vertical offset simulation)
        positions = [0, -1, -2, -1, 0]  # Simulate bounce
        
        with Live(console=console, refresh_per_second=30) as live:
            for pos in positions:
                # Simulate vertical offset with newlines
                bounced = Text()
                if pos < 0:
                    bounced.append("" * abs(pos))  # Empty lines
                bounced.append(text, style=f"bold {color}")
                live.update(bounced)
                await asyncio.sleep(0.1)
    
    @staticmethod
    async def shake_text(console: Console, text: str, color: str = "red"):
        """
        Shake animation (error indication)
        
        Args:
            console: Rich Console
            text: Text to shake
            color: Text color (typically red for errors)
        """
        from rich.live import Live
        
        # Shake offsets (horizontal simulation)
        offsets = [0, -1, 1, -1, 1, 0]
        
        with Live(console=console, refresh_per_second=30) as live:
            for offset in offsets:
                shaken = Text()
                if offset < 0:
                    shaken.append(" " * abs(offset))
                shaken.append(text, style=f"bold {color}")
                live.update(shaken)
                await asyncio.sleep(0.05)


# ===== CONVENIENCE FUNCTIONS =====

async def show_loading(console: Console, message: str = "Processing", duration: float = 2.0):
    """Quick loading spinner"""
    spinner = LoadingSpinner(style="dots", color="cyan")
    await spinner.spin(console, message, duration)


async def fade_in_message(console: Console, message: str, color: str = "green"):
    """Quick fade in effect"""
    await FadeEffect.fade_in_animated(console, message, duration=0.5, color=color)


async def success_pulse(console: Console, message: str = "✓ Success"):
    """Show success with pulse effect"""
    pulse_text = MicroInteraction.pulse(message, scale=1.2)
    await fade_in_message(console, pulse_text, color="green")


async def error_shake(console: Console, message: str = "✗ Error"):
    """Show error with shake effect"""
    await MicroInteraction.shake_text(console, message, color="red")
