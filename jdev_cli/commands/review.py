"""
/review command - Review session changes and activity.

Provides comprehensive view of current session modifications.
"""

import logging
from typing import Dict, Any, Optional
from pathlib import Path
from datetime import datetime
import subprocess
from rich.console import Console

from jdev_cli.commands import SlashCommand, slash_registry

logger = logging.getLogger(__name__)
console = Console()


async def handle_review(args: str, context: Dict[str, Any]) -> str:
    """
    Review current session changes and activity.
    
    Usage:
        /review              Show session summary
        /review --diff       Show git diffs of modified files
        /review --stats      Show detailed statistics
        /review --export     Export report to file
    
    Args:
        args: Command flags
        context: Execution context with session data
    
    Returns:
        Formatted review output
    """
    session = context.get('session')

    if not session:
        return _format_error("No active session to review")

    # Parse flags
    show_diff = '--diff' in args
    show_stats = '--stats' in args
    export = '--export' in args

    # Build review output
    output_lines = []

    # Session header
    output_lines.append(_format_session_header(session))
    output_lines.append("")

    # Files modified
    if session.modified_files:
        output_lines.append(_format_modified_files(session.modified_files, show_diff))
        output_lines.append("")

    # Files read
    if session.read_files:
        output_lines.append(_format_read_files(session.read_files))
        output_lines.append("")

    # Tool calls
    output_lines.append(_format_tool_calls(session))
    output_lines.append("")

    # Statistics
    if show_stats:
        output_lines.append(_format_statistics(session))
        output_lines.append("")

    # Git status
    git_status = _get_git_status(context.get('cwd', Path.cwd()))
    if git_status:
        output_lines.append(git_status)
        output_lines.append("")

    review_text = "\n".join(output_lines)

    # Export if requested
    if export:
        export_path = _export_review(session, review_text)
        output_lines.append(f"[green]✓ Review exported to:[/green] {export_path}")

    return "\n".join(output_lines)


def _format_session_header(session) -> str:
    """Format session header."""
    lines = [
        "[bold cyan]Session Review[/bold cyan]",
        f"[dim]Session ID:[/dim] {session.session_id[:8]}...",
        f"[dim]Started:[/dim] {session.created_at.strftime('%Y-%m-%d %H:%M:%S')}",
    ]

    # Calculate duration
    duration = datetime.now() - session.created_at
    hours = duration.seconds // 3600
    minutes = (duration.seconds % 3600) // 60

    duration_str = []
    if hours > 0:
        duration_str.append(f"{hours}h")
    if minutes > 0:
        duration_str.append(f"{minutes}m")
    if not duration_str:
        duration_str.append("<1m")

    lines.append(f"[dim]Duration:[/dim] {' '.join(duration_str)}")

    return "\n".join(lines)


def _format_modified_files(files: set, show_diff: bool = False) -> str:
    """Format modified files section."""
    lines = [f"[green]Files Modified ({len(files)}):[/green]"]

    for file in sorted(files):
        lines.append(f"  ✓ {file}")

        if show_diff:
            diff = _get_file_diff(file)
            if diff:
                lines.append(f"[dim]{diff}[/dim]")

    return "\n".join(lines)


def _format_read_files(files: set) -> str:
    """Format read files section."""
    max_display = 15
    sorted_files = sorted(files)

    lines = [f"[yellow]Files Read ({len(files)}):[/yellow]"]

    for file in sorted_files[:max_display]:
        lines.append(f"  • {file}")

    if len(files) > max_display:
        remaining = len(files) - max_display
        lines.append(f"  [dim]... and {remaining} more[/dim]")

    return "\n".join(lines)


def _format_tool_calls(session) -> str:
    """Format tool calls statistics."""
    return f"[cyan]Tool Calls:[/cyan] {session.tool_calls_count}"


def _format_statistics(session) -> str:
    """Format detailed statistics."""
    lines = ["[bold]Session Statistics:[/bold]"]

    # Calculate LOC stats if git is available
    loc_stats = _calculate_loc_changes(session.modified_files)

    if loc_stats:
        lines.append(f"  Lines Added:   [green]+{loc_stats['added']}[/green]")
        lines.append(f"  Lines Removed: [red]-{loc_stats['removed']}[/red]")
        lines.append(f"  Net Change:    {loc_stats['net']:+d}")

    # File type breakdown
    file_types = _analyze_file_types(session.modified_files)
    if file_types:
        lines.append("\n[bold]File Types Modified:[/bold]")
        for ext, count in sorted(file_types.items(), key=lambda x: x[1], reverse=True):
            lines.append(f"  {ext}: {count}")

    return "\n".join(lines)


def _get_git_status(cwd: Path) -> Optional[str]:
    """Get git status for current directory."""
    try:
        result = subprocess.run(
            ['git', 'status', '--short'],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=2
        )

        if result.returncode == 0 and result.stdout.strip():
            lines = ["[bold]Git Status:[/bold]"]

            for line in result.stdout.strip().split('\n')[:10]:
                status = line[:2]
                file = line[3:]

                if 'M' in status:
                    lines.append(f"  [yellow]M[/yellow] {file}")
                elif 'A' in status:
                    lines.append(f"  [green]A[/green] {file}")
                elif 'D' in status:
                    lines.append(f"  [red]D[/red] {file}")
                elif '?' in status:
                    lines.append(f"  [dim]?[/dim] {file}")
                else:
                    lines.append(f"  {status} {file}")

            if len(result.stdout.strip().split('\n')) > 10:
                lines.append("  [dim]... more files[/dim]")

            return "\n".join(lines)
    except Exception:
        pass

    return None


def _get_file_diff(filepath: str) -> Optional[str]:
    """Get git diff for a file."""
    try:
        result = subprocess.run(
            ['git', 'diff', '--unified=0', filepath],
            capture_output=True,
            text=True,
            timeout=2
        )

        if result.returncode == 0 and result.stdout.strip():
            # Return first few lines of diff
            lines = result.stdout.strip().split('\n')[:5]
            return "\n    ".join(lines)
    except Exception:
        pass

    return None


def _calculate_loc_changes(files: set) -> Optional[Dict[str, int]]:
    """Calculate lines of code changes."""
    try:
        result = subprocess.run(
            ['git', 'diff', '--numstat'] + list(files),
            capture_output=True,
            text=True,
            timeout=2
        )

        if result.returncode == 0:
            added = 0
            removed = 0

            for line in result.stdout.strip().split('\n'):
                if not line:
                    continue
                parts = line.split('\t')
                if len(parts) >= 2:
                    try:
                        added += int(parts[0])
                        removed += int(parts[1])
                    except ValueError:
                        pass

            return {
                'added': added,
                'removed': removed,
                'net': added - removed
            }
    except Exception:
        pass

    return None


def _analyze_file_types(files: set) -> Dict[str, int]:
    """Analyze file types in modified files."""
    types = {}

    for file in files:
        ext = Path(file).suffix or 'no extension'
        types[ext] = types.get(ext, 0) + 1

    return types


def _export_review(session, review_text: str) -> Path:
    """Export review to file."""
    review_dir = Path(".qwen/reviews")
    review_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"review_{session.session_id[:8]}_{timestamp}.txt"
    filepath = review_dir / filename

    # Strip ANSI codes for plain text export
    import re
    plain_text = re.sub(r'\[.*?\]', '', review_text)

    filepath.write_text(plain_text)

    return filepath


def _format_error(message: str) -> str:
    """Format error message."""
    return f"\n[red]✗ Error:[/red] {message}\n"


# Register command
slash_registry.register(SlashCommand(
    name="review",
    description="Review session changes and activity",
    usage="/review [--diff] [--stats] [--export]",
    handler=handle_review,
    aliases=["rv", "status"],
    requires_session=True
))
