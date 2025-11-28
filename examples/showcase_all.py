#!/usr/bin/env python3
"""
🎬 QWEN-DEV-CLI: COMPLETE SHOWCASE
All TUI components + Cursor intelligence in one demo.

This is our masterpiece. This is what we built.

Run: python3 examples/showcase_all.py
"""

import sys
import time
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from jdev_cli.intelligence.indexer import SemanticIndexer
from jdev_cli.tui.components.toasts import ToastManager, ToastType
from jdev_cli.tui.components.palette import CommandPalette, Command, CommandCategory
from jdev_cli.tui.components.tree import FileTree
from jdev_cli.tui.wisdom import wisdom_system
from jdev_cli.tui.theme import COLORS
from rich.console import Console
from rich.panel import Panel
from rich.text import Text


def print_title():
    """Print showcase title."""
    console = Console()

    title_text = Text()
    title_text.append("🎬 QWEN-DEV-CLI ", style="bold cyan")
    title_text.append("COMPLETE SHOWCASE\n", style="bold white")
    title_text.append("\n")
    title_text.append("TUI Components + Cursor Intelligence\n", style="dim")
    title_text.append("Built with surgical precision. Zero compromises.\n", style="dim italic")

    panel = Panel(
        title_text,
        border_style="cyan",
        padding=(1, 2)
    )

    console.print("\n")
    console.print(panel)
    console.print("\n")


def section(title: str, icon: str = "📦"):
    """Print section divider."""
    print(f"\n{COLORS['accent_purple']}{'─' * 70}{COLORS['reset']}")
    print(f"{COLORS['accent_purple']}  {icon} {title}{COLORS['reset']}")
    print(f"{COLORS['accent_purple']}{'─' * 70}{COLORS['reset']}\n")


def main():
    """Run complete showcase."""
    console = Console()

    print_title()

    # 1. Biblical Wisdom System
    section("BIBLICAL WISDOM SYSTEM", "💎")

    print(f"{COLORS['info']}Drawing wisdom from Scripture...{COLORS['reset']}\n")

    verse = wisdom_system.get_by_category("building")
    print(f"  {COLORS['accent_purple']}Category: Building{COLORS['reset']}")
    print(f"  {COLORS['success']}{verse.reference}{COLORS['reset']}")
    print(f"  {COLORS['text']}\"{verse.text}\"{COLORS['reset']}")

    time.sleep(1)

    # 2. Semantic Indexer (Cursor Magic)
    section("SEMANTIC INDEXER - Cursor-Style Intelligence", "🔍")

    print(f"{COLORS['info']}⚡ Indexing codebase...{COLORS['reset']}")

    indexer = SemanticIndexer(root_path=".")

    start = time.time()
    count = indexer.index_codebase()
    elapsed = time.time() - start

    stats = indexer.get_stats()

    print(f"{COLORS['success']}✓ Indexed {count} files in {elapsed:.2f}s{COLORS['reset']}")
    print(f"\n  Files: {stats['files_indexed']}")
    print(f"  Symbols: {stats['total_symbols']}")
    print(f"  Unique: {stats['unique_symbols']}")

    # Search demo
    print(f"\n{COLORS['info']}Searching for 'Tool'...{COLORS['reset']}\n")

    results = indexer.search_symbols("Tool", limit=3)
    for symbol in results:
        print(f"  {COLORS['accent_green']}• {symbol.name}{COLORS['reset']} "
              f"{COLORS['dim']}({symbol.type}) at {symbol.file_path}:{symbol.line_number}{COLORS['reset']}")

    time.sleep(1)

    # 3. Toast Notifications
    section("TOAST NOTIFICATIONS - Gemini-Inspired", "🔔")

    toast_manager = ToastManager(max_toasts=5)

    # Add different types
    toasts_to_add = [
        (ToastType.SUCCESS, "Build Complete", "Project compiled successfully in 2.3s"),
        (ToastType.WARNING, "Large File", "Consider splitting file (> 1000 lines)"),
        (ToastType.ERROR, "Type Error", "Expected 'str', got 'int' at line 42"),
        (ToastType.WISDOM, "Proverbs 16:3", "Commit your work to the LORD, and your plans will be established"),
    ]

    for toast_type, title, message in toasts_to_add:
        toast_manager.add_toast(toast_type, title, message, duration=5.0)

    print(f"{COLORS['info']}Active toasts (priority order):{COLORS['reset']}\n")

    for i, toast in enumerate(toast_manager.toasts, 1):
        icon_color = toast.color
        print(f"  {i}. {icon_color}{toast.icon} {toast.title}{COLORS['reset']}")
        print(f"     {COLORS['dim']}{toast.message}{COLORS['reset']}")
        print()

    time.sleep(1)

    # 4. Command Palette
    section("COMMAND PALETTE - Cmd+K Style", "⌘")

    palette = CommandPalette()

    # Add sample commands
    commands = [
        Command("file.open", "Open File", "Open a file", CommandCategory.FILE, keybinding="Ctrl+O"),
        Command("file.save", "Save File", "Save current file", CommandCategory.FILE, keybinding="Ctrl+S"),
        Command("git.status", "Git Status", "Show repository status", CommandCategory.GIT),
        Command("tools.format", "Format Code", "Auto-format", CommandCategory.TOOLS, keybinding="Shift+Alt+F"),
    ]

    palette.add_commands(commands)

    # Fuzzy search demo
    queries = ["opn", "fmt", "git"]

    for query in queries:
        results = palette.search(query, limit=2)

        print(f"{COLORS['info']}Query: \"{query}\"{COLORS['reset']}")

        for cmd in results:
            score = palette.matcher.score(cmd.search_text, query)
            print(f"  {COLORS['accent_green']}→ {cmd.title}{COLORS['reset']} "
                  f"{COLORS['dim']}({cmd.category.value}){COLORS['reset']} "
                  f"{COLORS['accent_yellow']}[{score:.2f}]{COLORS['reset']}")
        print()

    time.sleep(1)

    # 5. File Tree
    section("FILE TREE - Apple-Style Visualization", "🌳")

    print(f"{COLORS['info']}Current directory structure:{COLORS['reset']}\n")

    tree = FileTree(Path.cwd(), max_depth=1, show_hidden=False)
    console.print(tree.render())

    time.sleep(1)

    # Summary
    section("SUMMARY - What We Built", "✨")

    accomplishments = [
        ("🔍 Semantic Indexer", f"{count} files, {stats['total_symbols']} symbols in {elapsed:.2f}s"),
        ("🔔 Toast System", "5-level priority queue with Biblical wisdom"),
        ("⌘ Command Palette", "Fuzzy search, < 50ms response"),
        ("🌳 File Tree", "13 file types, Git integration"),
        ("💎 Biblical Wisdom", "27 verses across 6 categories"),
        ("🎨 Theme System", "35 colors, WCAG AA compliant"),
    ]

    print(f"{COLORS['success']}What we accomplished:{COLORS['reset']}\n")

    for feature, detail in accomplishments:
        print(f"  {COLORS['dim']}•{COLORS['reset']} {feature}")
        print(f"    {COLORS['dim']}{detail}{COLORS['reset']}")
        print()

    # Final verse
    print(f"\n{COLORS['accent_purple']}{'═' * 70}{COLORS['reset']}")
    final_verse = wisdom_system.get_by_category("excellence")
    print(f"\n  {COLORS['success']}{final_verse.reference}{COLORS['reset']}")
    print(f"  {COLORS['text']}\"{final_verse.text}\"{COLORS['reset']}")
    print(f"\n{COLORS['accent_purple']}{'═' * 70}{COLORS['reset']}\n")

    # Stats
    print(f"{COLORS['dim']}Built with ❤️ by Célula Híbrida (Maximus + AI){COLORS['reset']}")
    print(f"{COLORS['dim']}Quality-first. Zero compromises. Disruptive excellence.{COLORS['reset']}\n")


if __name__ == "__main__":
    main()
