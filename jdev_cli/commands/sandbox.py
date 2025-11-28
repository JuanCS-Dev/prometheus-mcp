"""
/sandbox command - Execute commands in isolated Docker container.

Provides safe execution environment for potentially dangerous commands.
"""

import logging
from typing import Dict, Any
from pathlib import Path
from rich.console import Console

from jdev_cli.integration.sandbox import get_sandbox, SandboxResult
from jdev_cli.integration.safety import safety_validator
from jdev_cli.commands import SlashCommand, slash_registry

logger = logging.getLogger(__name__)
console = Console()


async def handle_sandbox(args: str, context: Dict[str, Any]) -> str:
    """
    Execute command in isolated Docker sandbox.
    
    Usage:
        /sandbox <command>
        /sb <command>
        /safe <command>
    
    Examples:
        /sandbox npm install
        /sandbox pytest tests/
        /sb python test.py
        /safe rm -rf /tmp/test
    
    Args:
        args: Command to execute
        context: Execution context (session, cwd, etc.)
    
    Returns:
        Formatted output string
    """
    if not args.strip():
        return _format_help()

    sandbox = get_sandbox()

    # Check availability
    if not sandbox.is_available():
        return _format_error("Docker sandbox not available. Install Docker and ensure daemon is running.")

    # Get current directory from context
    cwd = context.get('cwd', Path.cwd())
    if isinstance(cwd, str):
        cwd = Path(cwd)

    # Extract flags (simple parsing)
    command = args.strip()
    timeout = 30
    readonly = False  # Default to writable for most commands

    # Check for timeout flag
    if '--timeout' in command:
        parts = command.split('--timeout')
        try:
            timeout_part = parts[1].strip().split()[0]
            timeout = int(timeout_part)
            command = parts[0].strip() + ' ' + ' '.join(parts[1].strip().split()[1:])
        except (IndexError, ValueError):
            pass

    # Check for readonly flag
    if '--readonly' in command:
        readonly = True
        command = command.replace('--readonly', '').strip()

    # Safety validation before execution
    tool_call = {
        "tool": "bash_command",
        "arguments": {"command": command}
    }
    is_safe, reason = safety_validator.is_safe(tool_call)

    if not is_safe:
        console.print(f"\n[yellow]⚠️  Safety Warning:[/yellow] {reason}")
        console.print("[dim]Command will execute in isolated sandbox anyway.[/dim]\n")

    console.print(f"\n[cyan]🔒 Executing in sandbox:[/cyan] {command}")
    console.print(f"[dim]Directory: {cwd}[/dim]")
    console.print(f"[dim]Timeout: {timeout}s | Mode: {'readonly' if readonly else 'writable'}[/dim]\n")

    try:
        # Execute in sandbox
        result = sandbox.execute(
            command=command,
            cwd=cwd,
            timeout=timeout,
            readonly=readonly
        )

        return _format_result(result, command)

    except Exception as e:
        logger.error(f"Sandbox execution failed: {e}")
        return _format_error(f"Execution failed: {e}")


def _format_result(result: SandboxResult, command: str) -> str:
    """Format sandbox execution result."""
    output_lines = []

    # Status header
    if result.success:
        status = "[green]✓ Success[/green]"
    else:
        status = f"[red]✗ Failed (exit {result.exit_code})[/red]"

    output_lines.append(f"\n{status}")
    output_lines.append(f"[dim]Duration: {result.duration_ms:.0f}ms | Container: {result.container_id[:12]}[/dim]\n")

    # Stdout
    if result.stdout.strip():
        output_lines.append("[cyan]Output:[/cyan]")
        output_lines.append(result.stdout.rstrip())
        output_lines.append("")

    # Stderr
    if result.stderr.strip():
        output_lines.append("[yellow]Errors/Warnings:[/yellow]")
        output_lines.append(result.stderr.rstrip())
        output_lines.append("")

    # No output case
    if not result.stdout.strip() and not result.stderr.strip():
        output_lines.append("[dim]No output produced[/dim]\n")

    return "\n".join(output_lines)


def _format_error(message: str) -> str:
    """Format error message."""
    return f"\n[red]✗ Error:[/red] {message}\n"


def _format_help() -> str:
    """Format help message."""
    help_text = """
[bold cyan]Sandbox Execution[/bold cyan]

Execute commands in isolated Docker container for safety.

[bold]Usage:[/bold]
  /sandbox <command>        Execute command in sandbox
  /sb <command>             Short alias
  /safe <command>           Safety alias

[bold]Flags:[/bold]
  --timeout N               Set timeout in seconds (default: 30)
  --readonly                Mount directory as readonly

[bold]Examples:[/bold]
  /sandbox npm install                 Test package installation
  /sandbox pytest tests/ -v            Run tests safely
  /sb python dangerous_script.py       Execute untrusted code
  /sandbox --timeout 60 npm test       Long-running command
  /sandbox --readonly cat file.txt     Read-only access

[bold]Features:[/bold]
  • Isolated filesystem (no host access)
  • Resource limits (CPU, memory)
  • Timeout protection
  • Auto-cleanup
  • Safe for untrusted code

[bold]Note:[/bold]
Requires Docker installed and daemon running.
"""
    return help_text


# Register command
slash_registry.register(SlashCommand(
    name="sandbox",
    description="Execute command in isolated Docker sandbox",
    usage="/sandbox <command> [--timeout N] [--readonly]",
    handler=handle_sandbox,
    aliases=["sb", "safe"],
    requires_session=False
))
