#!/usr/bin/env python3
"""
Enhanced Shell Demo - Showcasing Cursor-level Intelligence.

Demonstrates:
- Context-aware autocomplete
- File tree sidebar
- Toast notifications
- Context pills
- Smart suggestions
- Biblical wisdom loading messages

"For I know the plans I have for you, declares the Lord, plans for welfare 
and not for evil, to give you a future and a hope."
- Jeremiah 29:11

Created: 2025-11-19 00:55 UTC
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import asyncio
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from jdev_cli.tui.theme import COLORS
from jdev_cli.tui.components import (
    FileTree,
    PillBar,
    ToastManager,
    create_file_pill,
    create_function_pill,
    create_tool_pill,
    create_completer
)
from jdev_cli.tui.biblical_wisdom import get_random_wisdom


async def demo_file_tree(console: Console):
    """Demonstrate file tree component."""
    console.print(f"\n[bold {COLORS['primary']}]📂 File Tree Demo[/]")
    console.print(f"[dim {COLORS['muted']}]VSCode/Cursor-style collapsible file explorer[/]\n")

    # Create file tree
    tree = FileTree(
        root_path=Path.cwd(),
        console=console,
        max_depth=2,
        show_hidden=False
    )
    tree.build_tree()

    # Expand some directories
    if tree.root_node and tree.root_node.children:
        for child in tree.root_node.children[:3]:
            if child.is_dir:
                tree.toggle_node(child)

    # Render
    panel = tree.render()
    console.print(panel)

    await asyncio.sleep(1)


async def demo_context_pills(console: Console):
    """Demonstrate context pills."""
    console.print(f"\n[bold {COLORS['primary']}]🏷️  Context Pills Demo[/]")
    console.print(f"[dim {COLORS['muted']}]Cursor @ mentions style - showing active context[/]\n")

    pill_bar = PillBar(console)

    # Add various types of pills
    pill_bar.add("main.py", create_file_pill("main.py").type)
    pill_bar.add("utils.py", create_file_pill("utils.py").type)
    pill_bar.add("process_data", create_function_pill("process_data", "main.py").type)
    pill_bar.add("read_file", create_tool_pill("read_file").type)

    # Render
    pills_view = pill_bar.render()
    if pills_view:
        console.print(pills_view)

    await asyncio.sleep(1)


async def demo_toast_notifications(console: Console):
    """Demonstrate toast notifications."""
    console.print(f"\n[bold {COLORS['primary']}]📢 Toast Notifications Demo[/]")
    console.print(f"[dim {COLORS['muted']}]VSCode-style notifications with auto-dismiss[/]\n")

    toast_manager = ToastManager(console, max_toasts=3)

    # Show different types
    toast_manager.show("Indexing codebase...", title="Info")
    await asyncio.sleep(0.5)

    toast_manager.show("File saved successfully", title="Success")
    await asyncio.sleep(0.5)

    toast_manager.show("Git changes detected", title="Warning")
    await asyncio.sleep(0.5)

    # Progress toast
    progress_toast = toast_manager.show_progress(
        "Building project...",
        title="Build",
        progress=0.0
    )

    # Simulate progress
    for i in range(5):
        await asyncio.sleep(0.3)
        toast_manager.update_progress(
            progress_toast.id,
            (i + 1) / 5,
            f"Step {i + 1}/5..."
        )

    toast_manager.dismiss(progress_toast.id)
    toast_manager.show("Build complete!", title="✅ Success")

    await asyncio.sleep(2)
    toast_manager.stop()


async def demo_biblical_wisdom(console: Console):
    """Demonstrate biblical wisdom loading messages."""
    console.print(f"\n[bold {COLORS['primary']}]📖 Biblical Wisdom Demo[/]")
    console.print(f"[dim {COLORS['muted']}]Inspirational verses while AI thinks[/]\n")

    for i in range(5):
        wisdom = get_random_wisdom()

        # Create styled panel
        text = Text()
        text.append(f"💭 {wisdom['text']}", style=f"italic {COLORS['secondary']}")
        text.append(f"\n   — {wisdom['reference']}", style=f"dim {COLORS['muted']}")

        panel = Panel(
            text,
            title=f"[bold {COLORS['accent']}]Wisdom {i+1}[/]",
            border_style=COLORS['primary'],
            padding=(1, 2)
        )

        console.print(panel)
        await asyncio.sleep(1)


async def demo_autocomplete(console: Console):
    """Demonstrate autocomplete system."""
    console.print(f"\n[bold {COLORS['primary']}]⚡ Smart Autocomplete Demo[/]")
    console.print(f"[dim {COLORS['muted']}]Context-aware completions with fuzzy search[/]\n")

    # Create mock completer
    completer = create_completer()

    # Show example completions
    console.print("[bold]Sample completions for 'read':[/]")
    console.print("  🔧 read_file - Read file contents")
    console.print("  🔧 read_multiple - Read multiple files")
    console.print("  📄 README.md - /home/user/project/README.md")
    console.print("  ⚡ read_config - function in config.py")

    await asyncio.sleep(2)


async def demo_full_integration(console: Console):
    """Demonstrate full integration."""
    console.print(f"\n[bold {COLORS['primary']}]🎯 Full Integration Demo[/]")
    console.print(f"[dim {COLORS['muted']}]All components working together[/]\n")

    # Create components
    toast_manager = ToastManager(console)
    pill_bar = PillBar(console)

    # Add context
    pill_bar.add("app.py", create_file_pill("app.py").type)
    pill_bar.add("main", create_function_pill("main", "app.py").type)

    # Show pills
    pills_view = pill_bar.render()
    if pills_view:
        console.print(pills_view)

    # Simulate workflow
    toast_manager.show("Loading context...", title="Shell")
    await asyncio.sleep(1)

    # Show wisdom
    wisdom = get_random_wisdom()
    console.print(f"\n[dim italic {COLORS['muted']}]💭 {wisdom['text']}[/]")
    console.print(f"[dim {COLORS['muted']}]   — {wisdom['reference']}[/]\n")

    await asyncio.sleep(1)

    toast_manager.show("Context ready", title="✅ Success")

    # Show file tree
    tree = FileTree(Path.cwd(), console, max_depth=1)
    tree.build_tree()
    console.print(tree.render())

    await asyncio.sleep(2)
    toast_manager.stop()


async def main():
    """Run all demos."""
    console = Console()

    # Welcome
    welcome = Panel(
        Text(
            "Enhanced Shell Demo\n\n"
            "Showcasing Cursor-level intelligence:\n"
            "✅ File Tree (collapsible)\n"
            "✅ Context Pills (@mentions)\n"
            "✅ Toast Notifications\n"
            "✅ Biblical Wisdom\n"
            "✅ Smart Autocomplete",
            style=COLORS['secondary']
        ),
        title=f"[bold {COLORS['primary']}]🚀 Qwen Dev CLI[/]",
        border_style=COLORS['accent'],
        padding=(1, 2)
    )
    console.print(welcome)

    await asyncio.sleep(2)

    # Run demos
    await demo_file_tree(console)
    await demo_context_pills(console)
    await demo_toast_notifications(console)
    await demo_biblical_wisdom(console)
    await demo_autocomplete(console)
    await demo_full_integration(console)

    # Finale
    console.print(f"\n[bold {COLORS['success']}]✅ Demo Complete![/]")
    console.print(f"[dim {COLORS['muted']}]All components working beautifully together[/]\n")

    console.print(Panel(
        Text(
            '"I can do all things through him who strengthens me."\n'
            '— Philippians 4:13',
            style=f"italic {COLORS['primary']}"
        ),
        border_style=COLORS['accent']
    ))


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 Goodbye!")
