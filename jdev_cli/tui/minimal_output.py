"""
Minimal Output Renderer - Nov 2025 Best Practices
Implements radical minimalism with strategic whitespace
"""

from typing import Optional, List
from rich.console import Console
from rich.text import Text
from rich.panel import Panel
from rich.columns import Columns
import re

console = Console()


class MinimalOutput:
    """
    Minimalist output following Nov 2025 best practices:
    - Concise by default
    - Strategic whitespace
    - Clear visual hierarchy
    - Purposeful color use
    """

    @staticmethod
    def truncate_text(text: str, max_lines: int = 15, max_chars: int = 120) -> tuple[str, bool]:
        """
        Smart truncation that preserves meaning.
        
        Returns:
            (truncated_text, was_truncated)
        """
        lines = text.split('\n')
        truncated = False

        # Truncate lines
        if len(lines) > max_lines:
            lines = lines[:max_lines]
            truncated = True

        # Truncate each line
        processed_lines = []
        for line in lines:
            if len(line) > max_chars:
                processed_lines.append(line[:max_chars] + "...")
                truncated = True
            else:
                processed_lines.append(line)

        return '\n'.join(processed_lines), truncated

    @staticmethod
    def smart_summarize(text: str, target_lines: int = 10) -> str:
        """
        Intelligent summarization that keeps structure.
        Preserves:
        - Headers (##, ###)
        - Code blocks (```)
        - Lists (-, *, 1.)
        - Key paragraphs
        """
        lines = text.split('\n')

        if len(lines) <= target_lines:
            return text

        # Priority scoring
        important_lines = []

        for i, line in enumerate(lines):
            score = 0
            stripped = line.strip()

            # Headers (high priority)
            if stripped.startswith('#'):
                score += 10

            # Code blocks
            if '```' in stripped:
                score += 8

            # Lists
            if re.match(r'^[\-\*\d]+\.?\s', stripped):
                score += 5

            # Short lines (likely important)
            if len(stripped) < 80 and len(stripped) > 10:
                score += 3

            # Contains keywords
            if any(kw in stripped.lower() for kw in ['error', 'warning', 'important', 'note']):
                score += 7

            if score > 0:
                important_lines.append((score, i, line))

        # Sort by score and take top N
        important_lines.sort(reverse=True, key=lambda x: x[0])
        selected_indices = sorted([idx for _, idx, _ in important_lines[:target_lines]])

        # Rebuild with context
        result = []
        last_idx = -2

        for idx in selected_indices:
            if idx - last_idx > 1:
                result.append("...")
            result.append(lines[idx])
            last_idx = idx

        if selected_indices[-1] < len(lines) - 1:
            result.append("...")

        return '\n'.join(result)

    @staticmethod
    def render_response(text: str, mode: str = "auto") -> None:
        """
        Render response with intelligent truncation.
        
        Modes:
        - auto: Smart decision based on length
        - full: Show everything
        - minimal: Aggressive truncation
        - summary: Intelligent summarization
        """
        lines = text.split('\n')
        line_count = len(lines)
        char_count = len(text)
        word_count = len(text.split())

        # Decision logic
        if mode == "auto":
            if line_count <= 20 and char_count <= 2000:
                mode = "full"
            elif line_count > 50 or char_count > 5000:
                mode = "summary"
            else:
                mode = "minimal"

        # Render based on mode
        if mode == "full":
            console.print(text, style="white")

        elif mode == "minimal":
            truncated, was_truncated = MinimalOutput.truncate_text(text, max_lines=15)
            console.print(truncated, style="white")

            if was_truncated:
                console.print(f"\n[dim]... truncated ({line_count} lines total)[/dim]")
                console.print("[dim]💡 Tip: Use [cyan]/expand[/cyan] to see full output[/dim]")

        elif mode == "summary":
            summary = MinimalOutput.smart_summarize(text, target_lines=12)
            console.print(summary, style="white")
            console.print(f"\n[dim]📝 Showing key points from {line_count} lines[/dim]")
            console.print("[dim]💡 Use [cyan]/expand[/cyan] for complete response[/dim]")

    @staticmethod
    def render_compact_list(items: List[str], title: Optional[str] = None) -> None:
        """
        Render list in compact columns (2025 style).
        """
        if title:
            console.print(f"\n[bold cyan]{title}[/bold cyan]")

        # Auto-detect best column count
        max_item_len = max(len(item) for item in items)
        terminal_width = console.width

        if max_item_len < 30:
            cols = 3
        elif max_item_len < 50:
            cols = 2
        else:
            cols = 1

        # Render in columns
        if cols > 1:
            columns = Columns(
                [Text(f"  • {item}", style="dim") for item in items],
                equal=True,
                expand=False
            )
            console.print(columns)
        else:
            for item in items:
                console.print(f"  • [dim]{item}[/dim]")

        console.print()

    @staticmethod
    def render_code_block(code: str, language: str = "bash", max_lines: int = 20) -> None:
        """
        Render code with smart truncation.
        """
        from rich.syntax import Syntax

        lines = code.split('\n')

        if len(lines) > max_lines:
            # Show first N-2 lines + separator + last line
            truncated_code = '\n'.join(lines[:max_lines-2] + ['# ... truncated ...', lines[-1]])
            syntax = Syntax(truncated_code, language, theme="monokai", line_numbers=False)
            console.print(Panel(syntax, border_style="dim", title=f"[dim]{language}[/dim]"))
            console.print(f"[dim]({len(lines)} lines total)[/dim]\n")
        else:
            syntax = Syntax(code, language, theme="monokai", line_numbers=False)
            console.print(Panel(syntax, border_style="dim", title=f"[dim]{language}[/dim]"))

    @staticmethod
    def render_stats(
        words: int,
        chars: int,
        duration: float,
        wps: int,
        cost: Optional[str] = None
    ) -> None:
        """
        Minimal stats line (2025 style).
        """
        # Build compact stats
        parts = [
            f"{words}w",
            f"{duration:.1f}s",
            f"{wps}wps"
        ]

        if cost:
            parts.append(cost)

        stats = " • ".join(parts)
        console.print(f"[dim]{stats}[/dim]\n")


class StreamingMinimal:
    """
    Minimalist streaming output (Nov 2025 standards).
    """

    def __init__(self):
        self.buffer = []
        self.line_count = 0
        self.should_truncate = False
        self.max_visible_lines = 20

    def add_chunk(self, chunk: str) -> None:
        """Add chunk and decide if should show."""
        self.buffer.append(chunk)
        self.line_count += chunk.count('\n')

        # Auto-truncate after threshold
        if self.line_count > self.max_visible_lines and not self.should_truncate:
            self.should_truncate = True
            console.print("\n[dim]... streaming continues (use /expand to see all) ...[/dim]")

    def get_display_buffer(self) -> str:
        """Get what should be displayed."""
        full_text = ''.join(self.buffer)

        if not self.should_truncate:
            return full_text

        # Show first N lines only during streaming
        lines = full_text.split('\n')
        return '\n'.join(lines[:self.max_visible_lines])

    def finalize(self) -> str:
        """Return full buffer at end."""
        return ''.join(self.buffer)
