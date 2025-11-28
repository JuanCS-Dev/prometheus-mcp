"""
IndexHandler - Indexing and Search Commands.

SCALE & SUSTAIN Phase 1.2 - CC Reduction.

Handles: /index, /find, /suggest

Author: JuanCS Dev
Date: 2025-11-26
"""

import time
from pathlib import Path
from typing import TYPE_CHECKING

from .dispatcher import CommandResult

if TYPE_CHECKING:
    from jdev_cli.shell_main import InteractiveShell


class IndexHandler:
    """Handler for indexing and search commands."""

    def __init__(self, shell: 'InteractiveShell'):
        """Initialize with shell reference."""
        self.shell = shell
        self.console = shell.console

    async def handle_index(self, cmd: str) -> CommandResult:
        """Handle /index command."""
        self.console.print("[cyan]🔍 Indexing codebase...[/cyan]")
        start = time.time()
        count = self.shell.indexer.index_codebase(force=True)
        elapsed = time.time() - start

        stats = self.shell.indexer.get_stats()

        self.console.print(f"[green]✓ Indexed {count} files in {elapsed:.2f}s[/green]")
        self.console.print(f"  Total symbols: {stats['total_symbols']}")
        self.console.print(f"  Unique names:  {stats['unique_symbols']}")
        self.shell._indexer_initialized = True

        return CommandResult.ok()

    async def handle_find(self, cmd: str) -> CommandResult:
        """Handle /find <query> command."""
        query = cmd[6:].strip()  # Remove "/find "

        if not query:
            return CommandResult.error("[red]Usage: /find <symbol_name>[/red]")

        if not self.shell._indexer_initialized:
            self.console.print("[yellow]⚠ Index not initialized. Run /index first.[/yellow]")
            return CommandResult.ok()

        results = self.shell.indexer.search_symbols(query, limit=10)

        if not results:
            self.console.print(f"[dim]No symbols found for: {query}[/dim]")
            return CommandResult.ok()

        self.console.print(f"\n[bold]Found {len(results)} symbols:[/bold]\n")
        for symbol in results:
            type_style = "green" if symbol.type == "class" else "blue"
            self.console.print(
                f"  [{type_style}]{symbol.name}[/{type_style}] "
                f"[dim]({symbol.type})[/dim] "
                f"[yellow]{symbol.file_path}:{symbol.line_number}[/yellow]"
            )
            if symbol.docstring:
                doc_preview = symbol.docstring.split('\n')[0][:60]
                self.console.print(f"    [dim]→ {doc_preview}...[/dim]")

        return CommandResult.ok()

    async def handle_suggest(self, cmd: str) -> CommandResult:
        """Handle /suggest <file> command."""
        file_arg = cmd[9:].strip()  # Remove "/suggest "

        if not file_arg:
            return CommandResult.error("[red]Usage: /suggest <file>[/red]")

        try:
            file_path = Path(file_arg)
            if not file_path.exists():
                return CommandResult.error(f"[red]File not found: {file_path}[/red]")

            # Get file recommendations
            recommendations = self.shell.suggestion_engine.suggest_related_files(file_path, max_suggestions=5)

            if recommendations:
                self.console.print(f"\n[bold]💡 Related files for {file_path.name}:[/bold]\n")

                for rec in recommendations:
                    rel_path = rec.file_path.relative_to(Path.cwd()) if rec.file_path.is_relative_to(Path.cwd()) else rec.file_path
                    score_bar = "█" * int(rec.relevance_score * 10)

                    type_emoji = {
                        'import': '📦',
                        'test': '🧪',
                        'dependency': '🔗',
                        'similar': '📄'
                    }.get(rec.relationship_type, '📌')

                    self.console.print(
                        f"  {type_emoji} [cyan]{rel_path}[/cyan]\n"
                        f"     {rec.reason}\n"
                        f"     Relevance: [{score_bar:<10}] {rec.relevance_score:.0%}"
                    )
            else:
                self.console.print(f"[dim]No related files found for {file_path.name}[/dim]")

            # Get code suggestions
            code_suggestions = self.shell.suggestion_engine.suggest_edits(file_path)

            if code_suggestions:
                self.console.print("\n[bold]🔧 Code suggestions:[/bold]\n")

                for sug in code_suggestions[:5]:  # Top 5
                    impact_colors = {
                        'high': 'red',
                        'medium': 'yellow',
                        'low': 'blue'
                    }
                    color = impact_colors.get(sug.impact, 'white')

                    self.console.print(
                        f"  Line {sug.line_number}: [{color}]{sug.impact.upper()}[/{color}] {sug.suggestion}"
                    )

        except Exception as e:
            return CommandResult.error(f"[red]Error: {e}[/red]")

        return CommandResult.ok()
