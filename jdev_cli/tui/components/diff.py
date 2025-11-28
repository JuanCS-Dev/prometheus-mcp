"""
Diff Viewer Component - GitHub-style diff display.

Features:
- Unified diff (default)
- Side-by-side diff (wide terminals)
- Line numbers on both sides
- Color-coded changes (+ green, - red)
- Context line control
- Expand/collapse unchanged hunks

Philosophy:
- Clear visualization of changes
- Scannable (line numbers, colors)
- Flexible (unified or side-by-side)
- GitHub-quality aesthetics

Created: 2025-11-18 20:50 UTC
"""

import difflib
from typing import Optional, List
from enum import Enum

from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.table import Table

from ..theme import COLORS
from ..styles import PRESET_STYLES


class DiffMode(Enum):
    """Diff display modes."""
    UNIFIED = "unified"
    SIDE_BY_SIDE = "side_by_side"


class DiffLine:
    """Single line in a diff."""

    def __init__(
        self,
        line_type: str,  # '+', '-', ' ', or '@@'
        content: str,
        old_line_no: Optional[int] = None,
        new_line_no: Optional[int] = None,
    ):
        """
        Initialize diff line.
        
        Args:
            line_type: Line type ('+' = add, '-' = remove, ' ' = context)
            content: Line content
            old_line_no: Line number in old file
            new_line_no: Line number in new file
        """
        self.line_type = line_type
        self.content = content
        self.old_line_no = old_line_no
        self.new_line_no = new_line_no

    @property
    def is_addition(self) -> bool:
        """Check if line is an addition."""
        return self.line_type == '+'

    @property
    def is_deletion(self) -> bool:
        """Check if line is a deletion."""
        return self.line_type == '-'

    @property
    def is_context(self) -> bool:
        """Check if line is context."""
        return self.line_type == ' '

    @property
    def is_hunk_header(self) -> bool:
        """Check if line is hunk header."""
        return self.line_type == '@@'


class DiffViewer:
    """
    Diff viewer with multiple display modes.
    
    Examples:
        diff = DiffViewer(old_content, new_content)
        console.print(diff.render())
        
        # Side-by-side for wide terminals
        console.print(diff.render(mode=DiffMode.SIDE_BY_SIDE))
    """

    def __init__(
        self,
        old_content: str,
        new_content: str,
        old_label: str = "Old",
        new_label: str = "New",
        context_lines: int = 3,
    ):
        """
        Initialize diff viewer.
        
        Args:
            old_content: Old file content
            new_content: New file content
            old_label: Label for old version
            new_label: Label for new version
            context_lines: Number of context lines around changes
        """
        self.old_content = old_content
        self.new_content = new_content
        self.old_label = old_label
        self.new_label = new_label
        self.context_lines = context_lines

        # Parse diff
        self.diff_lines = self._compute_diff()

    def _compute_diff(self) -> List[DiffLine]:
        """
        Compute diff between old and new content.
        
        Returns:
            List of DiffLine objects
        """
        old_lines = self.old_content.splitlines(keepends=False)
        new_lines = self.new_content.splitlines(keepends=False)

        # Use difflib for unified diff
        diff = difflib.unified_diff(
            old_lines,
            new_lines,
            fromfile=self.old_label,
            tofile=self.new_label,
            n=self.context_lines,
            lineterm='',
        )

        result = []
        old_line_no = 0
        new_line_no = 0

        for line in diff:
            # Skip file headers
            if line.startswith('---') or line.startswith('+++'):
                continue

            # Hunk header (@@)
            if line.startswith('@@'):
                result.append(DiffLine('@@', line))
                # Parse line numbers from hunk header
                # Example: @@ -10,5 +12,6 @@
                parts = line.split('@@')[1].strip().split()
                if len(parts) >= 2:
                    old_part = parts[0].lstrip('-').split(',')
                    new_part = parts[1].lstrip('+').split(',')
                    old_line_no = int(old_part[0])
                    new_line_no = int(new_part[0])
                continue

            # Determine line type and update line numbers
            if line.startswith('+'):
                result.append(DiffLine('+', line[1:], None, new_line_no))
                new_line_no += 1
            elif line.startswith('-'):
                result.append(DiffLine('-', line[1:], old_line_no, None))
                old_line_no += 1
            elif line.startswith(' '):
                result.append(DiffLine(' ', line[1:], old_line_no, new_line_no))
                old_line_no += 1
                new_line_no += 1

        return result

    def _render_unified(self) -> Text:
        """
        Render unified diff format.
        
        Returns:
            Rich Text object
        """
        result = Text()

        for diff_line in self.diff_lines:
            if diff_line.is_hunk_header:
                # Hunk header (cyan)
                result.append(diff_line.content + '\n', style=PRESET_STYLES.INFO)

            elif diff_line.is_addition:
                # Addition (green background)
                line_no = f"{diff_line.new_line_no:4d}" if diff_line.new_line_no else "    "
                result.append(f"+{line_no} │ ", style=PRESET_STYLES.DIFF_ADD)
                result.append(diff_line.content + '\n', style=PRESET_STYLES.DIFF_ADD)

            elif diff_line.is_deletion:
                # Deletion (red background)
                line_no = f"{diff_line.old_line_no:4d}" if diff_line.old_line_no else "    "
                result.append(f"-{line_no} │ ", style=PRESET_STYLES.DIFF_REMOVE)
                result.append(diff_line.content + '\n', style=PRESET_STYLES.DIFF_REMOVE)

            elif diff_line.is_context:
                # Context (normal)
                line_no = f"{diff_line.old_line_no:4d}" if diff_line.old_line_no else "    "
                result.append(f" {line_no} │ ", style=PRESET_STYLES.DIFF_CONTEXT)
                result.append(diff_line.content + '\n', style=PRESET_STYLES.TERTIARY)

        return result

    def _render_side_by_side(self) -> Table:
        """
        Render side-by-side diff format.
        
        Returns:
            Rich Table object
        """
        table = Table(
            show_header=True,
            header_style=PRESET_STYLES.TABLE_HEADER,
            border_style=COLORS['border_muted'],
            expand=False,
        )

        # Add columns
        table.add_column("Old", style=PRESET_STYLES.PRIMARY, width=50)
        table.add_column("New", style=PRESET_STYLES.PRIMARY, width=50)

        # Group consecutive changes
        old_lines: List[str] = []
        new_lines: List[str] = []

        for diff_line in self.diff_lines:
            if diff_line.is_hunk_header:
                # Flush pending lines
                if old_lines or new_lines:
                    self._add_side_by_side_row(table, old_lines, new_lines)
                    old_lines = []
                    new_lines = []

                # Add hunk header
                table.add_row(
                    Text(diff_line.content, style=PRESET_STYLES.INFO),
                    Text(diff_line.content, style=PRESET_STYLES.INFO),
                )

            elif diff_line.is_deletion:
                old_lines.append(f"-{diff_line.old_line_no:4d} │ {diff_line.content}")

            elif diff_line.is_addition:
                new_lines.append(f"+{diff_line.new_line_no:4d} │ {diff_line.content}")

            elif diff_line.is_context:
                # Flush pending lines
                if old_lines or new_lines:
                    self._add_side_by_side_row(table, old_lines, new_lines)
                    old_lines = []
                    new_lines = []

                # Add context line
                line_text = f" {diff_line.old_line_no:4d} │ {diff_line.content}"
                table.add_row(
                    Text(line_text, style=PRESET_STYLES.TERTIARY),
                    Text(f" {diff_line.new_line_no:4d} │ {diff_line.content}", style=PRESET_STYLES.TERTIARY),
                )

        # Flush remaining lines
        if old_lines or new_lines:
            self._add_side_by_side_row(table, old_lines, new_lines)

        return table

    def _add_side_by_side_row(
        self,
        table: Table,
        old_lines: List[str],
        new_lines: List[str],
    ):
        """Add a row to side-by-side table."""
        max_lines = max(len(old_lines), len(new_lines))

        for i in range(max_lines):
            old_text = old_lines[i] if i < len(old_lines) else ""
            new_text = new_lines[i] if i < len(new_lines) else ""

            table.add_row(
                Text(old_text, style=PRESET_STYLES.DIFF_REMOVE if old_text else None),
                Text(new_text, style=PRESET_STYLES.DIFF_ADD if new_text else None),
            )

    def render(
        self,
        mode: DiffMode = DiffMode.UNIFIED,
        title: Optional[str] = None,
    ) -> Panel:
        """
        Render diff with specified mode.
        
        Args:
            mode: Display mode (unified or side-by-side)
            title: Panel title
            
        Returns:
            Rich Panel object
        """
        if mode == DiffMode.UNIFIED:
            content = self._render_unified()
        else:
            content = self._render_side_by_side()

        # Default title if not provided
        if title is None:
            title = f"Diff: {self.old_label} → {self.new_label}"

        return Panel(
            content,
            title=title,
            title_align="left",
            border_style=COLORS['accent_blue'],
            padding=(0, 1),
            expand=False,
        )

    def get_stats(self) -> dict:
        """
        Get diff statistics.
        
        Returns:
            Dictionary with additions, deletions, changes
        """
        additions = sum(1 for line in self.diff_lines if line.is_addition)
        deletions = sum(1 for line in self.diff_lines if line.is_deletion)

        return {
            'additions': additions,
            'deletions': deletions,
            'changes': additions + deletions,
        }


# =============================================================================
# QUICK DIFF FUNCTIONS
# =============================================================================

def show_diff(
    console: Console,
    old_content: str,
    new_content: str,
    mode: DiffMode = DiffMode.UNIFIED,
    old_label: str = "Old",
    new_label: str = "New",
):
    """
    Quick helper to show diff.
    
    Args:
        console: Rich console
        old_content: Old content
        new_content: New content
        mode: Display mode
        old_label: Old version label
        new_label: New version label
    """
    diff = DiffViewer(old_content, new_content, old_label, new_label)
    console.print(diff.render(mode=mode))


def create_file_diff(
    old_path: str,
    new_path: str,
    context_lines: int = 3,
) -> DiffViewer:
    """
    Create diff viewer from file paths.
    
    Args:
        old_path: Path to old file
        new_path: Path to new file
        context_lines: Context lines
        
    Returns:
        DiffViewer instance
    """
    with open(old_path, 'r') as f:
        old_content = f.read()

    with open(new_path, 'r') as f:
        new_content = f.read()

    return DiffViewer(
        old_content,
        new_content,
        old_label=old_path,
        new_label=new_path,
        context_lines=context_lines,
    )


def compare_strings(
    old: str,
    new: str,
    console: Optional[Console] = None,
) -> None:
    """
    Quick comparison of two strings.
    
    Args:
        old: Old string
        new: New string
        console: Rich console (creates new if None)
    """
    console = console or Console()
    diff = DiffViewer(old, new, "Before", "After")
    console.print(diff.render())

    # Show stats
    stats = diff.get_stats()
    console.print(
        f"\n[green]+{stats['additions']}[/green] "
        f"[red]-{stats['deletions']}[/red] "
        f"({stats['changes']} changes total)"
    )
