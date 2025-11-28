"""
LSPHandler - LSP Code Intelligence Commands.

SCALE & SUSTAIN Phase 1.2 - CC Reduction.

Handles all /lsp commands:
- /lsp (start server)
- /lsp hover
- /lsp goto
- /lsp refs
- /lsp diag
- /lsp complete
- /lsp signature

Author: JuanCS Dev
Date: 2025-11-26
"""

from pathlib import Path
from typing import TYPE_CHECKING

from rich.panel import Panel

from .dispatcher import CommandResult

if TYPE_CHECKING:
    from jdev_cli.shell_main import InteractiveShell


class LSPHandler:
    """Handler for LSP-related commands."""

    def __init__(self, shell: 'InteractiveShell'):
        """Initialize with shell reference."""
        self.shell = shell
        self.console = shell.console

    def _check_lsp_initialized(self) -> CommandResult | None:
        """Check if LSP is initialized. Returns error result if not."""
        if not self.shell._lsp_initialized:
            return CommandResult.error("[yellow]⚠ LSP not initialized. Run /lsp first.[/yellow]")
        return None

    def _parse_location(self, location_str: str) -> tuple[Path, int, int] | CommandResult:
        """
        Parse file:line:char location string.

        Returns tuple (file_path, line, char) or CommandResult on error.
        """
        parts = location_str.split(":")
        if len(parts) != 3:
            return CommandResult.error("[red]Usage: /lsp <cmd> <file>:<line>:<char>[/red]")

        try:
            file_path = Path(parts[0])
            line = int(parts[1])
            char = int(parts[2])
            return (file_path, line, char)
        except ValueError:
            return CommandResult.error("[red]Invalid line or character number[/red]")

    async def handle_lsp_start(self, cmd: str) -> CommandResult:
        """Handle /lsp command - start LSP server."""
        if not self.shell._lsp_initialized:
            self.console.print("[cyan]🔧 Starting LSP server...[/cyan]")
            success = await self.shell.lsp_client.start()

            if success:
                self.shell._lsp_initialized = True
                self.console.print("[green]✓ LSP server started successfully[/green]")
                self.console.print(f"[dim]Language: {self.shell.lsp_client.language.value}[/dim]")
                self.console.print("\n[bold]LSP Features:[/bold]")
                self.console.print("  /lsp hover <file>:<line>:<char>     - Hover documentation")
                self.console.print("  /lsp goto <file>:<line>:<char>      - Go to definition")
                self.console.print("  /lsp refs <file>:<line>:<char>      - Find references")
                self.console.print("  /lsp diag <file>                    - Show diagnostics")
                self.console.print("  /lsp complete <file>:<line>:<char>  - Code completions 🆕")
                self.console.print("  /lsp signature <file>:<line>:<char> - Signature help 🆕")
            else:
                self.console.print("[red]✗ Failed to start LSP server[/red]")
                self.console.print("[dim]Install: pip install python-lsp-server[all][/dim]")
        else:
            self.console.print("[yellow]⚠ LSP server already running[/yellow]")

        return CommandResult.ok()

    async def handle_hover(self, cmd: str) -> CommandResult:
        """Handle /lsp hover command."""
        if error := self._check_lsp_initialized():
            return error

        try:
            location = cmd[11:].strip()  # Remove "/lsp hover "
            parsed = self._parse_location(location)
            if isinstance(parsed, CommandResult):
                return parsed

            file_path, line, char = parsed
            hover_info = await self.shell.lsp_client.hover(file_path, line, char)

            if hover_info:
                self.console.print(Panel(
                    hover_info.contents,
                    title=f"Hover: {file_path}:{line}:{char}",
                    border_style="cyan"
                ))
            else:
                self.console.print("[dim]No hover information available[/dim]")

        except Exception as e:
            return CommandResult.error(f"[red]Error: {e}[/red]")

        return CommandResult.ok()

    async def handle_goto(self, cmd: str) -> CommandResult:
        """Handle /lsp goto command."""
        if error := self._check_lsp_initialized():
            return error

        try:
            location = cmd[10:].strip()  # Remove "/lsp goto "
            parsed = self._parse_location(location)
            if isinstance(parsed, CommandResult):
                return parsed

            file_path, line, char = parsed
            definitions = await self.shell.lsp_client.definition(file_path, line, char)

            if definitions:
                self.console.print(f"\n[bold]Found {len(definitions)} definition(s):[/bold]\n")
                for loc in definitions:
                    file = Path(loc.uri.replace("file://", ""))
                    self.console.print(
                        f"  [cyan]{file}:{loc.range.start.line}:{loc.range.start.character}[/cyan]"
                    )
            else:
                self.console.print("[dim]No definition found[/dim]")

        except Exception as e:
            return CommandResult.error(f"[red]Error: {e}[/red]")

        return CommandResult.ok()

    async def handle_refs(self, cmd: str) -> CommandResult:
        """Handle /lsp refs command."""
        if error := self._check_lsp_initialized():
            return error

        try:
            location = cmd[10:].strip()  # Remove "/lsp refs "
            parsed = self._parse_location(location)
            if isinstance(parsed, CommandResult):
                return parsed

            file_path, line, char = parsed
            references = await self.shell.lsp_client.references(file_path, line, char)

            if references:
                self.console.print(f"\n[bold]Found {len(references)} reference(s):[/bold]\n")
                for loc in references:
                    file = Path(loc.uri.replace("file://", ""))
                    self.console.print(
                        f"  [cyan]{file}:{loc.range.start.line}:{loc.range.start.character}[/cyan]"
                    )
            else:
                self.console.print("[dim]No references found[/dim]")

        except Exception as e:
            return CommandResult.error(f"[red]Error: {e}[/red]")

        return CommandResult.ok()

    async def handle_diag(self, cmd: str) -> CommandResult:
        """Handle /lsp diag command."""
        if error := self._check_lsp_initialized():
            return error

        try:
            file_path = Path(cmd[10:].strip())  # Remove "/lsp diag "
            diagnostics = await self.shell.lsp_client.diagnostics(file_path)

            if diagnostics:
                self.console.print(f"\n[bold]Diagnostics for {file_path}:[/bold]\n")
                for diag in diagnostics:
                    severity_colors = {
                        1: "red",      # Error
                        2: "yellow",   # Warning
                        3: "blue",     # Info
                        4: "dim"       # Hint
                    }
                    color = severity_colors.get(diag.severity, "white")

                    self.console.print(
                        f"  [{color}]{diag.severity_name}[/{color}] "
                        f"Line {diag.range.start.line + 1}: {diag.message}"
                    )
            else:
                self.console.print(f"[green]✓ No diagnostics for {file_path}[/green]")

        except Exception as e:
            return CommandResult.error(f"[red]Error: {e}[/red]")

        return CommandResult.ok()

    async def handle_complete(self, cmd: str) -> CommandResult:
        """Handle /lsp complete command."""
        if error := self._check_lsp_initialized():
            return error

        try:
            location = cmd[14:].strip()  # Remove "/lsp complete "
            parsed = self._parse_location(location)
            if isinstance(parsed, CommandResult):
                return parsed

            file_path, line, char = parsed
            completions = await self.shell.lsp_client.completion(file_path, line, char)

            if completions:
                self.console.print(f"\n[bold]Code Completions ({len(completions)} items):[/bold]\n")
                for item in completions[:20]:  # Show top 20
                    kind_emoji = {
                        "Function": "🔧", "Method": "⚙️", "Variable": "📦",
                        "Class": "📚", "Module": "📁", "Constant": "🔒"
                    }.get(item.kind_name, "•")

                    detail = f" - {item.detail}" if item.detail else ""
                    self.console.print(
                        f"  {kind_emoji} [cyan]{item.label}[/cyan]{detail}"
                    )
                    if item.documentation:
                        doc_preview = item.documentation[:60]
                        self.console.print(f"     [dim]{doc_preview}[/dim]")

                if len(completions) > 20:
                    self.console.print(f"\n[dim]... and {len(completions) - 20} more[/dim]")
            else:
                self.console.print("[dim]No completions available[/dim]")

        except Exception as e:
            return CommandResult.error(f"[red]Error: {e}[/red]")

        return CommandResult.ok()

    async def handle_signature(self, cmd: str) -> CommandResult:
        """Handle /lsp signature command."""
        if error := self._check_lsp_initialized():
            return error

        try:
            location = cmd[15:].strip()  # Remove "/lsp signature "
            parsed = self._parse_location(location)
            if isinstance(parsed, CommandResult):
                return parsed

            file_path, line, char = parsed
            sig_help = await self.shell.lsp_client.signature_help(file_path, line, char)

            if sig_help and sig_help.signatures:
                active_sig = sig_help.signatures[sig_help.active_signature]

                self.console.print("\n[bold]Function Signature:[/bold]")
                self.console.print(f"  [cyan]{active_sig.label}[/cyan]\n")

                if active_sig.documentation:
                    self.console.print(f"[dim]{active_sig.documentation}[/dim]\n")

                if active_sig.parameters:
                    self.console.print("[bold]Parameters:[/bold]")
                    for i, param in enumerate(active_sig.parameters):
                        marker = "→" if i == sig_help.active_parameter else " "
                        style = "bold cyan" if i == sig_help.active_parameter else "dim"
                        self.console.print(f"  {marker} [{style}]{param.label}[/{style}]")
                        if param.documentation:
                            self.console.print(f"    [dim]{param.documentation}[/dim]")
            else:
                self.console.print("[dim]No signature help available[/dim]")

        except Exception as e:
            return CommandResult.error(f"[red]Error: {e}[/red]")

        return CommandResult.ok()
