#!/usr/bin/env python3
"""
File Tree Demo - Apple-style directory tree with git integration.

Run: python3 examples/tree_demo.py
"""

import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from jdev_cli.tui.components.tree import FileTree
from jdev_cli.tui.theme import COLORS
from rich.console import Console


def print_header(text: str):
    """Print styled header."""
    print(f"\n{COLORS['accent_blue']}{'═' * 70}{COLORS['reset']}")
    print(f"{COLORS['accent_blue']}  {text}{COLORS['reset']}")
    print(f"{COLORS['accent_blue']}{'═' * 70}{COLORS['reset']}\n")


def main():
    """Run file tree demo."""
    console = Console()

    print_header("🌳 FILE TREE - Apple-style with Git Integration")

    # Get current directory
    root_path = Path.cwd()

    print(f"{COLORS['info']}Root: {root_path}{COLORS['reset']}\n")

    # Demo 1: Basic tree (top-level only)
    print_header("Demo 1: Basic Directory Tree (depth=1)")

    tree = FileTree(root_path, max_depth=1)
    console.print(tree.render())

    # Demo 2: Deeper tree (show structure)
    print_header("Demo 2: Project Structure (depth=2)")

    tree = FileTree(root_path, max_depth=2, show_hidden=False)
    console.print(tree.render())

    # Demo 3: Git integration (if in git repo)
    print_header("Demo 3: Git-Aware Tree")

    try:
        import subprocess
        result = subprocess.run(
            ["git", "rev-parse", "--git-dir"],
            capture_output=True,
            cwd=root_path,
            timeout=2
        )

        if result.returncode == 0:
            print(f"{COLORS['success']}✓ Git repository detected{COLORS['reset']}\n")

            tree = FileTree(
                root_path,
                max_depth=1,
                show_git_status=True,
                show_hidden=False
            )

            console.print(tree.render())

            # Legend
            print(f"\n{COLORS['info']}Git Status Legend:{COLORS['reset']}")
            print(f"  {COLORS['success']}● Modified{COLORS['reset']}")
            print(f"  {COLORS['accent_green']}+ Added{COLORS['reset']}")
            print(f"  {COLORS['error']}✗ Deleted{COLORS['reset']}")
            print(f"  {COLORS['warning']}? Untracked{COLORS['reset']}")
        else:
            print(f"{COLORS['dim']}Not a git repository{COLORS['reset']}")

    except Exception as e:
        print(f"{COLORS['dim']}Git not available{COLORS['reset']}")

    # Demo 4: Filter patterns
    print_header("Demo 4: Smart Filtering (exclude common patterns)")

    tree = FileTree(
        root_path,
        max_depth=2,
        show_hidden=False,
        exclude_patterns=[
            "__pycache__",
            ".git",
            "node_modules",
            "*.pyc",
            "venv",
            ".pytest_cache"
        ]
    )

    console.print(tree.render())

    # Summary
    print_header("✨ File Tree Features")

    features = [
        "Icon-based file type visualization",
        "Collapsible directory structure",
        "Git status integration (M/A/D/U indicators)",
        "Smart filtering (hide build artifacts)",
        "Configurable depth",
        "Keyboard navigation ready",
        "Apple-style elegance",
        "Performance optimized (lazy loading)"
    ]

    for feature in features:
        print(f"  {COLORS['dim']}•{COLORS['reset']} {feature}")

    print()


if __name__ == "__main__":
    main()
