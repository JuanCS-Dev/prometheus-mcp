#!/usr/bin/env python3
"""
Toast Notifications Demo - Gemini-inspired feedback system.

Run: python3 examples/toasts_demo.py
"""

import sys
import time
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from jdev_cli.tui.components.toasts import ToastManager, ToastType
from jdev_cli.tui.theme import COLORS


def render_toast(toast, width=60):
    """Render a toast as text (simple version)."""
    # Icon and title
    header = f"{toast.icon} {toast.title}"

    # Message (word wrap)
    words = toast.message.split()
    lines = []
    current_line = []
    current_length = 0

    for word in words:
        if current_length + len(word) + 1 <= width - 4:
            current_line.append(word)
            current_length += len(word) + 1
        else:
            if current_line:
                lines.append(' '.join(current_line))
            current_line = [word]
            current_length = len(word)

    if current_line:
        lines.append(' '.join(current_line))

    # Build toast
    output = []
    output.append("┌" + "─" * (width - 2) + "┐")
    output.append(f"│ {toast.color}{header}{COLORS['reset']}" + " " * (width - len(header) - 4) + "│")
    output.append("├" + "─" * (width - 2) + "┤")

    for line in lines:
        padding = width - len(line) - 4
        output.append(f"│ {line}" + " " * padding + " │")

    output.append("└" + "─" * (width - 2) + "┘")

    return "\n".join(output)


def main():
    """Demo toast system."""
    print(f"\n{COLORS['accent_blue']}{'═' * 70}{COLORS['reset']}")
    print(f"{COLORS['accent_blue']}  🔔 TOAST NOTIFICATION SYSTEM - Gemini-inspired{COLORS['reset']}")
    print(f"{COLORS['accent_blue']}{'═' * 70}{COLORS['reset']}\n")

    manager = ToastManager(max_toasts=5)

    # Demo 1: Success toast
    print(f"{COLORS['info']}[Demo 1] Adding SUCCESS toast:{COLORS['reset']}\n")
    manager.add_toast(
        type=ToastType.SUCCESS,
        title="File Saved",
        message="config.yaml has been saved successfully",
        duration=5.0
    )

    toast = manager.toasts[0]
    print(render_toast(toast))
    print()
    time.sleep(1)

    # Demo 2: Warning toast
    print(f"{COLORS['info']}[Demo 2] Adding WARNING toast:{COLORS['reset']}\n")
    manager.add_toast(
        type=ToastType.WARNING,
        title="Large File",
        message="This file is over 5MB. Consider splitting it into smaller files.",
        duration=5.0
    )

    toast = manager.toasts[0]  # Warning has priority
    print(render_toast(toast))
    print()
    time.sleep(1)

    # Demo 3: Error toast (highest priority)
    print(f"{COLORS['info']}[Demo 3] Adding ERROR toast (highest priority):{COLORS['reset']}\n")
    manager.add_toast(
        type=ToastType.ERROR,
        title="Syntax Error",
        message="Line 42: unexpected token '}'. Expected ';' before closing brace.",
        duration=0  # Persistent
    )

    toast = manager.toasts[0]  # Error jumps to top
    print(render_toast(toast))
    print()
    time.sleep(1)

    # Demo 4: Biblical Wisdom toast
    print(f"{COLORS['info']}[Demo 4] Adding WISDOM toast:{COLORS['reset']}\n")
    manager.add_toast(
        type=ToastType.WISDOM,
        title="Proverbs 16:3",
        message="Commit to the LORD whatever you do, and he will establish your plans.",
        duration=8.0
    )

    toast = [t for t in manager.toasts if t.type == ToastType.WISDOM][0]
    print(render_toast(toast))
    print()
    time.sleep(1)

    # Demo 5: Info toast
    print(f"{COLORS['info']}[Demo 5] Adding INFO toast:{COLORS['reset']}\n")
    manager.add_toast(
        type=ToastType.INFO,
        title="Indexing Complete",
        message="Indexed 141 files with 1470 symbols in 0.51s",
        duration=4.0
    )

    toast = [t for t in manager.toasts if t.type == ToastType.INFO][0]
    print(render_toast(toast))
    print()

    # Show all active toasts
    print(f"\n{COLORS['accent_purple']}{'─' * 70}{COLORS['reset']}")
    print(f"{COLORS['accent_purple']}  📊 Active Toast Queue (Priority Order){COLORS['reset']}")
    print(f"{COLORS['accent_purple']}{'─' * 70}{COLORS['reset']}\n")

    for i, toast in enumerate(manager.toasts, 1):
        type_color = toast.color
        duration_text = f"{toast.duration}s" if toast.duration > 0 else "persistent"
        print(f"  {i}. {type_color}{toast.icon} {toast.type.value.upper()}{COLORS['reset']} "
              f"{COLORS['dim']}({duration_text}){COLORS['reset']}")
        print(f"     {toast.title}")
        print()

    # Summary
    print(f"{COLORS['accent_green']}{'═' * 70}{COLORS['reset']}")
    print(f"{COLORS['accent_green']}  ✨ Toast System Features{COLORS['reset']}")
    print(f"{COLORS['accent_green']}{'═' * 70}{COLORS['reset']}\n")

    features = [
        "Priority Queue (Error > Warning > Wisdom > Info > Success)",
        "Auto-dismiss timers (persistent option for errors)",
        "Max queue size (overflow protection)",
        "Beautiful icons and colors (Gemini-inspired)",
        "Biblical wisdom integration (unique feature!)",
        "Non-intrusive feedback (top-right positioning)"
    ]

    for feature in features:
        print(f"  {COLORS['dim']}•{COLORS['reset']} {feature}")

    print()


if __name__ == "__main__":
    main()
