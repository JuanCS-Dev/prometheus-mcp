#!/usr/bin/env python3
"""
Command Palette Demo - Cmd+K style with fuzzy search.

Run: python3 examples/palette_demo.py
"""

import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from qwen_dev_cli.tui.components.palette import (
    CommandPalette,
    Command,
    CommandCategory
)
from qwen_dev_cli.tui.theme import COLORS


def print_header(text: str):
    """Print styled header."""
    print(f"\n{COLORS['accent_blue']}{'═' * 70}{COLORS['reset']}")
    print(f"{COLORS['accent_blue']}  {text}{COLORS['reset']}")
    print(f"{COLORS['accent_blue']}{'═' * 70}{COLORS['reset']}\n")


def print_command(cmd, score=None, highlight=False):
    """Print command result."""
    color = COLORS['accent_green'] if highlight else COLORS['text']
    category_icon = "📄" if cmd.category == CommandCategory.FILE else "🔍"
    
    # Title with keybinding
    title_line = f"{color}{category_icon} {cmd.title}{COLORS['reset']}"
    if cmd.keybinding:
        title_line += f" {COLORS['dim']}({cmd.keybinding}){COLORS['reset']}"
    
    if score is not None:
        title_line += f" {COLORS['accent_yellow']}[{score:.2f}]{COLORS['reset']}"
    
    print(f"  {title_line}")
    print(f"    {COLORS['dim']}{cmd.description}{COLORS['reset']}")
    
    if cmd.use_count > 0:
        print(f"    {COLORS['dim']}Used {cmd.use_count} times{COLORS['reset']}")
    print()


def main():
    """Run command palette demo."""
    print_header("⌘ COMMAND PALETTE - Cmd+K Style with Fuzzy Search")
    
    # Initialize palette
    palette = CommandPalette()
    
    # Add file commands
    file_commands = [
        Command(
            id="file.open",
            title="Open File",
            description="Open a file in the editor",
            category=CommandCategory.FILE,
            keywords=["read", "load"],
            keybinding="Ctrl+O"
        ),
        Command(
            id="file.save",
            title="Save File",
            description="Save current file",
            category=CommandCategory.FILE,
            keywords=["write"],
            keybinding="Ctrl+S"
        ),
        Command(
            id="file.new",
            title="New File",
            description="Create a new file",
            category=CommandCategory.FILE,
            keybinding="Ctrl+N"
        ),
        Command(
            id="file.close",
            title="Close File",
            description="Close current file",
            category=CommandCategory.FILE,
            keybinding="Ctrl+W"
        ),
    ]
    
    # Add search commands
    search_commands = [
        Command(
            id="search.find",
            title="Find in Files",
            description="Search across all files",
            category=CommandCategory.SEARCH,
            keywords=["grep", "search"],
            keybinding="Ctrl+Shift+F"
        ),
        Command(
            id="search.symbol",
            title="Go to Symbol",
            description="Jump to a symbol in the project",
            category=CommandCategory.SEARCH,
            keywords=["navigate", "jump"],
            keybinding="Ctrl+T"
        ),
    ]
    
    # Add git commands
    git_commands = [
        Command(
            id="git.status",
            title="Git Status",
            description="Show working tree status",
            category=CommandCategory.GIT,
            keywords=["changes"],
        ),
        Command(
            id="git.commit",
            title="Git Commit",
            description="Record changes to the repository",
            category=CommandCategory.GIT,
            keywords=["save", "record"],
        ),
    ]
    
    # Add tool commands
    tool_commands = [
        Command(
            id="tools.index",
            title="Index Codebase",
            description="Build semantic index for fast search",
            category=CommandCategory.TOOLS,
            keywords=["cursor", "intelligence"],
        ),
        Command(
            id="tools.format",
            title="Format Code",
            description="Auto-format current file",
            category=CommandCategory.TOOLS,
            keywords=["prettier", "black"],
            keybinding="Shift+Alt+F"
        ),
    ]
    
    # Add all commands
    all_commands = file_commands + search_commands + git_commands + tool_commands
    palette.add_commands(all_commands)
    
    print(f"{COLORS['info']}✓ Loaded {len(all_commands)} commands{COLORS['reset']}\n")
    
    # Demo 1: Fuzzy search
    print_header("🔍 Demo 1: Fuzzy Search")
    
    queries = [
        ("opn", "Typo: 'opn' → matches 'Open File'"),
        ("sf", "Initials: 'sf' → matches 'Save File'"),
        ("git st", "Partial: 'git st' → matches 'Git Status'"),
        ("format", "Exact: 'format' → matches 'Format Code'"),
    ]
    
    for query, description in queries:
        print(f"{COLORS['info']}Query: \"{query}\" - {description}{COLORS['reset']}\n")
        results = palette.search(query, limit=3)
        
        if results:
            for cmd in results:
                # Calculate score for display
                score = palette.matcher.score(cmd.search_text, query)
                print_command(cmd, score=score, highlight=True)
        else:
            print(f"  {COLORS['dim']}No results{COLORS['reset']}\n")
    
    # Demo 2: Category filtering
    print_header("🏷️ Demo 2: Category Filtering")
    
    print(f"{COLORS['info']}Filter by category: FILE{COLORS['reset']}\n")
    results = palette.search("", limit=10, category=CommandCategory.FILE, include_recent=False)
    
    for cmd in results:
        print_command(cmd)
    
    # Demo 3: Recent commands
    print_header("🕐 Demo 3: Recent Commands")
    
    # Simulate usage
    cmds_to_use = ["file.open", "file.save", "git.status", "tools.index", "file.open"]
    print(f"{COLORS['info']}Simulating command usage...{COLORS['reset']}\n")
    
    for cmd_id in cmds_to_use:
        palette.execute_command(cmd_id)
        cmd = palette.get_command(cmd_id)
        print(f"  {COLORS['dim']}• Executed: {cmd.title}{COLORS['reset']}")
    
    print(f"\n{COLORS['info']}Recent commands (most used first):{COLORS['reset']}\n")
    
    recent = palette.get_recent_commands(limit=5)
    for cmd in recent:
        print_command(cmd, highlight=True)
    
    # Demo 4: Keyboard shortcuts
    print_header("⌨️ Demo 4: Keyboard Shortcuts")
    
    print(f"{COLORS['info']}Commands with keybindings:{COLORS['reset']}\n")
    
    commands_with_keys = [
        cmd for cmd in palette.commands.values() 
        if cmd.keybinding
    ]
    
    # Sort by category
    commands_with_keys.sort(key=lambda c: c.category.value)
    
    for cmd in commands_with_keys:
        category_color = COLORS['accent_blue']
        print(f"  {category_color}{cmd.keybinding:20s}{COLORS['reset']} {cmd.title}")
        print(f"  {COLORS['dim']}{' ' * 20} {cmd.description}{COLORS['reset']}")
        print()
    
    # Summary
    print_header("✨ Command Palette Features")
    
    features = [
        "Fuzzy search (typo-tolerant)",
        "Category filtering",
        "Recent commands tracking",
        "Keyboard shortcuts display",
        "Score-based ranking",
        "Keyword expansion",
        "Usage statistics",
        "< 50ms response time"
    ]
    
    for feature in features:
        print(f"  {COLORS['dim']}•{COLORS['reset']} {feature}")
    
    print()


if __name__ == "__main__":
    main()
