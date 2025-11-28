#!/usr/bin/env python3
"""
✨ TUI Polish Demo - Apple-style micro-interactions

Demonstrates:
- Smooth animations
- Micro-interactions
- Loading states with Biblical wisdom
- Accessibility features
- Visual feedback

Run: python3 examples/polish_demo.py
"""

import sys
import time
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.table import Table

from jdev_cli.tui.feedback import (
    MicroInteraction,
    LoadingState,
    StateTransition,
    HapticFeedback,
)
from jdev_cli.tui.animations import (
    Animator,
    AnimationConfig,
    LoadingAnimation,
)
from jdev_cli.tui.accessibility import (
    generate_accessibility_report,
    KeyboardNavigation,
    ScreenReaderText,
)
from jdev_cli.tui.theme import COLORS
from jdev_cli.tui.wisdom import get_random_verse


def demo_micro_interactions(console: Console):
    """Demo micro-interaction effects"""
    console.print("\n[bold cyan]1️⃣ MICRO-INTERACTIONS[/bold cyan]\n")

    # Button press effect
    console.print("[dim]Button Press Animation:[/dim]")
    for _ in range(3):
        # Normal state
        button = MicroInteraction.button_press("Confirm", pressed=False)
        console.print(button)
        time.sleep(0.3)

        # Pressed state
        console.clear()
        button = MicroInteraction.button_press("Confirm", pressed=True)
        console.print(button)
        time.sleep(0.15)
        console.clear()

    console.print("✓ Button animation complete\n")
    time.sleep(0.5)

    # Selection highlights
    console.print("[dim]Selection Highlights:[/dim]")
    items = ["Option A", "Option B", "Option C"]

    for i, item in enumerate(items):
        console.clear()
        console.print("\n[dim]Use arrow keys to navigate:[/dim]\n")

        for j, opt in enumerate(items):
            selected = j == i
            focused = j == i
            line = MicroInteraction.selection_highlight(opt, selected, focused)
            console.print(line)

        time.sleep(0.5)

    console.print("\n✓ Selection demo complete\n")


def demo_animations(console: Console):
    """Demo smooth animations"""
    console.print("\n[bold cyan]2️⃣ SMOOTH ANIMATIONS[/bold cyan]\n")

    # Easing demo
    console.print("[dim]Cubic Ease-Out (Apple's favorite):[/dim]\n")

    animator = Animator(AnimationConfig(duration=1.0, easing="ease-out"))

    def draw_progress(value: float):
        width = 40
        filled = int(value * width)
        bar = "█" * filled + "░" * (width - filled)
        console.clear()
        console.print(f"Progress: [{bar}] {value*100:.0f}%")

    animator.animate(0.0, 1.0, draw_progress)
    console.print("\n✓ Animation complete\n")
    time.sleep(0.5)

    # Loading spinners
    console.print("[dim]Loading Spinners:[/dim]\n")

    spinners = ["dots", "line", "arrow", "box", "bounce"]
    for spinner_name in spinners:
        console.print(f"\n{spinner_name.capitalize()}:")
        loader = LoadingAnimation(spinner_name, speed=0.08)

        for _ in range(20):
            frame = loader.next_frame()
            console.print(f"\r  {frame} Loading...", end="")
            time.sleep(0.08)

        console.print(" ✓")

    console.print("\n✓ Spinner demo complete\n")


def demo_feedback_states(console: Console):
    """Demo visual feedback states"""
    console.print("\n[bold cyan]3️⃣ VISUAL FEEDBACK[/bold cyan]\n")

    # Success pulse
    console.print("[dim]Success Animation:[/dim]")
    MicroInteraction.success_pulse(console, "File saved successfully!")
    time.sleep(0.5)

    # Error shake
    console.print("\n[dim]Error Animation:[/dim]")
    MicroInteraction.error_shake(console, "Invalid input detected")
    time.sleep(0.5)

    # Haptic-like feedback
    console.print("\n[dim]Haptic Feedback:[/dim]")
    console.print("Tap: ", end="")
    HapticFeedback.tap(console)
    time.sleep(0.3)

    console.print("Success Pop:")
    HapticFeedback.success_pop(console)
    time.sleep(0.5)

    console.print("\n✓ Feedback demo complete\n")


def demo_loading_wisdom(console: Console):
    """Demo loading states with Biblical wisdom"""
    console.print("\n[bold cyan]4️⃣ LOADING WITH BIBLICAL WISDOM[/bold cyan]\n")

    loader = LoadingState(console)

    # Show various loading states
    operations = [
        "Indexing codebase",
        "Analyzing dependencies",
        "Building project",
        "Running tests",
    ]

    for op in operations:
        console.clear()
        console.print(f"\n[bold]Demo: {op}[/bold]\n")
        loader.show_thinking(op, show_wisdom=True)
        time.sleep(2)

    # Progress demo
    console.clear()
    console.print("\n[bold]Progress with verse:[/bold]\n")

    verse = get_random_verse("building")
    console.print(f"💎 {verse['text']}")
    console.print(f"   — {verse['reference']}\n", style="dim")

    for i in range(0, 101, 10):
        console.clear()
        console.print(f"\n💎 {verse['text']}")
        console.print(f"   — {verse['reference']}\n", style="dim")
        loader.show_progress(i, 100, "Building with purpose")
        time.sleep(0.3)

    console.print("\n✓ Loading demo complete\n")


def demo_transitions(console: Console):
    """Demo state transitions"""
    console.print("\n[bold cyan]5️⃣ STATE TRANSITIONS[/bold cyan]\n")

    # Fade in
    console.print("[dim]Fade In Effect:[/dim]")
    StateTransition.fade_in(console, "🎨 Content appears smoothly")
    time.sleep(0.5)

    # Slide in
    console.print("\n[dim]Slide In Effects:[/dim]")

    for direction in ["left", "right"]:
        console.clear()
        console.print(f"\nSliding from {direction}...")
        time.sleep(0.3)
        StateTransition.slide_in(
            console,
            f"← Content slides from {direction}",
            direction=direction,
            steps=15,
        )
        time.sleep(0.5)

    console.print("\n✓ Transition demo complete\n")


def demo_accessibility(console: Console):
    """Demo accessibility features"""
    console.print("\n[bold cyan]6️⃣ ACCESSIBILITY (WCAG)[/bold cyan]\n")

    # Keyboard shortcuts
    console.print("[dim]Keyboard Navigation:[/dim]\n")

    actions = ["quit", "help", "search", "command_palette", "next"]

    table = Table(title="♿ Keyboard Shortcuts")
    table.add_column("Action", style="cyan")
    table.add_column("Keys", style="yellow")
    table.add_column("Description", style="dim")

    for action in actions:
        shortcuts = KeyboardNavigation.get_shortcuts(action)
        keys = ", ".join(KeyboardNavigation.format_shortcut(k) for k in shortcuts[:2])
        desc = KeyboardNavigation.describe_action(action)
        table.add_row(action.replace("_", " ").title(), keys, desc)

    console.print(table)
    console.print()

    # Screen reader text
    console.print("[dim]Screen Reader Descriptions:[/dim]\n")

    sr_examples = [
        ("Status", ScreenReaderText.describe_status("success")),
        ("Progress", ScreenReaderText.describe_progress(75, 100, 75)),
        ("Code", ScreenReaderText.describe_code_block("Python", 42)),
        ("Diff", ScreenReaderText.describe_diff(15, 8)),
    ]

    for label, description in sr_examples:
        console.print(f"  [cyan]{label}:[/cyan] {description}")

    console.print()
    time.sleep(1)

    # Contrast report
    console.print("[dim]Color Contrast Report:[/dim]\n")
    generate_accessibility_report()

    console.print("\n✓ Accessibility demo complete\n")


def main():
    """Run complete polish demo"""
    console = Console()

    # Title
    console.clear()
    title = Text()
    title.append("✨ ", style="bold yellow")
    title.append("QWEN-DEV-CLI", style="bold cyan")
    title.append(" - UI Polish Demo", style="bold white")
    title.append(" ✨", style="bold yellow")

    panel = Panel(
        title,
        border_style=COLORS['accent_purple'],
        padding=(1, 2),
    )
    console.print(panel)
    console.print("\n[dim]Demonstrating Apple-style micro-interactions and polish[/dim]\n")

    time.sleep(1)

    # Run demos
    try:
        demo_micro_interactions(console)
        time.sleep(1)

        demo_animations(console)
        time.sleep(1)

        demo_feedback_states(console)
        time.sleep(1)

        demo_loading_wisdom(console)
        time.sleep(1)

        demo_transitions(console)
        time.sleep(1)

        demo_accessibility(console)

        # Final message
        console.print("\n" + "═" * 70 + "\n")

        verse = get_random_verse("completion")
        console.print(f"💎 [italic]{verse['text']}[/italic]")
        console.print(f"   [dim]— {verse['reference']}[/dim]\n")

        console.print("[bold green]✅ All polish demos complete![/bold green]")
        console.print("\n[dim]Every detail refined. Apple-level quality achieved.[/dim]\n")

    except KeyboardInterrupt:
        console.print("\n\n[yellow]Demo interrupted by user[/yellow]")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
