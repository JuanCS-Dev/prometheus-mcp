"""
JuanCS Dev-Code - Unified Entry Point
======================================

Single command with multiple modes:
    qwen                    # Interactive TUI (default)
    qwen chat "message"     # One-shot message
    qwen -p "prompt"        # Headless mode (CI/CD)
    qwen ui                 # Gradio web UI
    qwen serve              # MCP server mode
    qwen shell              # Legacy shell mode

Philosophy: One command to rule them all.

Author: JuanCS
Date: 2025-11-25
"""

from __future__ import annotations

import asyncio
from typing import Optional, List

import typer
from rich.console import Console

# Create CLI app
app = typer.Typer(
    name="qwen",
    help="JuanCS Dev-Code - AI-Powered Development Assistant",
    add_completion=True,
    invoke_without_command=True,  # Allow running without subcommand
)

console = Console()


def version_callback(value: bool):
    """Show version and exit."""
    if value:
        console.print("[bold cyan]JuanCS Dev-Code[/bold cyan] v0.0.2")
        console.print("[dim]AI-Powered Development Assistant[/dim]")
        console.print("\n[bold]Available Modes:[/bold]")
        console.print("  qwen          → Interactive TUI")
        console.print("  qwen -p       → Headless mode")
        console.print("  qwen ui       → Web UI")
        console.print("  qwen serve    → MCP Server")
        raise typer.Exit()


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    prompt: Optional[str] = typer.Option(
        None, "-p", "--prompt",
        help="Run in headless mode with given prompt"
    ),
    output_format: str = typer.Option(
        "text", "--output-format", "-o",
        help="Output format: text, json, stream-json"
    ),
    max_turns: int = typer.Option(
        10, "--max-turns",
        help="Maximum tool execution turns in headless mode"
    ),
    allowed_tools: Optional[List[str]] = typer.Option(
        None, "--allow-tool",
        help="Restrict to specific tools (can repeat)"
    ),
    version: bool = typer.Option(
        None, "--version", "-V",
        callback=version_callback, is_eager=True,
        help="Show version and exit"
    ),
):
    """
    JuanCS Dev-Code - AI-Powered Development Assistant.

    Run without arguments to start the interactive TUI.
    Use -p for headless mode (CI/CD, scripts, automation).

    Examples:
        qwen                              # Interactive TUI
        qwen -p "Create a hello.py"       # Headless one-shot
        qwen -p "Fix tests" --max-turns 5 # Limited iterations
        qwen -p "List TODOs" -o json      # JSON output
    """
    # If a subcommand is being invoked, skip default behavior
    if ctx.invoked_subcommand is not None:
        return

    # Headless mode
    if prompt:
        asyncio.run(_run_headless(
            prompt=prompt,
            output_format=output_format,
            max_turns=max_turns,
            allowed_tools=allowed_tools,
        ))
        return

    # Default: Interactive TUI
    _run_tui()


def _run_tui():
    """Run the interactive Textual TUI."""
    try:
        from jdev_cli.ui_launcher import launch_tui
        launch_tui()
    except ImportError as e:
        console.print(f"[red]Error importing TUI:[/red] {e}")
        console.print("[dim]Falling back to legacy shell...[/dim]")
        try:
            from jdev_cli.shell_fast import main as shell_main
            asyncio.run(shell_main())
        except ImportError:
            console.print("[red]No shell available. Install textual.[/red]")
            raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


async def _run_headless(
    prompt: str,
    output_format: str = "text",
    max_turns: int = 10,
    allowed_tools: Optional[List[str]] = None,
):
    """
    Run in headless mode for CI/CD and automation.

    No interactive UI - just execute and output.
    """
    import json

    try:
        from jdev_cli.ui_launcher import get_bridge

        bridge = get_bridge()

        if not bridge.is_connected:
            if output_format == "json":
                print(json.dumps({"success": False, "error": "LLM not configured"}))
            else:
                console.print("[red]Error:[/red] LLM not configured. Set GEMINI_API_KEY.")
            raise typer.Exit(1)

        # Collect response
        response_parts = []
        tool_results = []

        async for chunk in bridge.chat(prompt):
            if output_format == "stream-json":
                # Stream JSON events
                print(json.dumps({"type": "chunk", "data": chunk}))
            elif output_format == "text":
                # Print as it streams
                print(chunk, end="", flush=True)

            response_parts.append(chunk)

        full_response = "".join(response_parts)

        if output_format == "json":
            # Final JSON output
            result = {
                "success": True,
                "response": full_response,
                "tool_results": tool_results,
            }
            print(json.dumps(result, indent=2))
        elif output_format == "stream-json":
            # Final event
            print(json.dumps({"type": "complete", "success": True}))
        elif output_format == "text":
            print()  # Final newline

    except Exception as e:
        if output_format == "json":
            print(json.dumps({"success": False, "error": str(e)}))
        else:
            console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


@app.command()
def ui(
    port: int = typer.Option(7860, "--port", "-p", help="Port for web UI"),
    share: bool = typer.Option(False, "--share", help="Create public share link"),
):
    """Start the Gradio web UI."""
    console.print(f"[bold cyan]🚀 Starting Web UI on port {port}...[/bold cyan]")

    try:
        from jdev_cli.ui import create_ui
        demo = create_ui()
        demo.launch(server_port=port, share=share)
    except ImportError as e:
        console.print("[red]Error:[/red] Gradio not installed")
        console.print("[dim]Install with: pip install gradio>=6.0.0[/dim]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


@app.command()
def serve(
    host: str = typer.Option("localhost", "--host", "-h", help="Host to bind"),
    port: int = typer.Option(8000, "--port", "-p", help="Port to bind"),
):
    """Start as MCP server."""
    console.print(f"[bold cyan]🔌 Starting MCP Server at {host}:{port}...[/bold cyan]")

    try:
        from jdev_cli.cli_mcp import main as mcp_main
        asyncio.run(mcp_main())
    except ImportError as e:
        console.print("[red]Error:[/red] MCP dependencies not installed")
        console.print(f"[dim]Details: {e}[/dim]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


@app.command()
def shell(
    mode: str = typer.Option("fast", "--mode", "-m", help="Shell mode: fast, simple, main"),
):
    """Start legacy interactive shell."""
    console.print(f"[bold cyan]🐚 Starting {mode} shell...[/bold cyan]")

    try:
        if mode == "fast":
            from jdev_cli.shell_fast import main as shell_main
        elif mode == "simple":
            from jdev_cli.shell_simple import main as shell_main
        elif mode == "main":
            from jdev_cli.shell_main import main as shell_main
        else:
            console.print(f"[red]Unknown shell mode:[/red] {mode}")
            console.print("[dim]Available: fast, simple, main[/dim]")
            raise typer.Exit(1)

        asyncio.run(shell_main())

    except ImportError as e:
        console.print(f"[red]Error:[/red] Shell not available: {e}")
        raise typer.Exit(1)
    except KeyboardInterrupt:
        console.print("\n[yellow]Goodbye! 👋[/yellow]")
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


@app.command()
def chat(
    message: str = typer.Argument(..., help="Message to send"),
    no_context: bool = typer.Option(False, "--no-context", help="Disable project context"),
    output_file: Optional[str] = typer.Option(None, "--output", "-o", help="Save output to file"),
    json_output: bool = typer.Option(False, "--json", help="Output in JSON format"),
):
    """Send a single message (one-shot mode)."""
    asyncio.run(_run_headless(
        prompt=message,
        output_format="json" if json_output else "text",
    ))


@app.command()
def status():
    """Show system status."""
    try:
        from jdev_cli.ui_launcher import get_bridge

        bridge = get_bridge()

        console.print("\n[bold cyan]JuanCS Dev-Code Status[/bold cyan]\n")

        # LLM Status
        if bridge.is_connected:
            console.print(f"[green]✅ LLM:[/green] Connected ({bridge.llm.model_name})")
        else:
            console.print("[red]❌ LLM:[/red] Not configured")

        # Agents
        agent_count = len(bridge.agents.available_agents)
        console.print(f"[green]🤖 Agents:[/green] {agent_count} available")

        # Tools
        tool_count = bridge.tools.get_tool_count()
        console.print(f"[green]🔧 Tools:[/green] {tool_count} loaded")

        # Governance
        gov_status = bridge.governance.get_status_emoji()
        console.print(f"[green]👀 Governance:[/green] {gov_status}")

        # Context
        context_count = len(bridge.history.context)
        console.print(f"[green]💬 Context:[/green] {context_count} messages")

        console.print()

    except Exception as e:
        console.print(f"[red]Error getting status:[/red] {e}")
        raise typer.Exit(1)


@app.command()
def agents():
    """List available agents."""
    try:
        from jdev_cli.ui_launcher import get_agent_registry
        from rich.table import Table

        AGENT_REGISTRY = get_agent_registry()

        table = Table(title="Available Agents")
        table.add_column("Name", style="cyan")
        table.add_column("Role", style="magenta")
        table.add_column("Description", style="white")
        table.add_column("Capabilities", style="dim")

        for name, info in AGENT_REGISTRY.items():
            caps = ", ".join(info.capabilities[:3])
            if len(info.capabilities) > 3:
                caps += "..."
            table.add_row(name, info.role, info.description, caps)

        console.print(table)

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


@app.command()
def tools():
    """List available tools."""
    try:
        from jdev_cli.ui_launcher import get_bridge

        bridge = get_bridge()
        console.print(bridge.get_tool_list())

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


def cli_main():
    """CLI entry point."""
    app()


if __name__ == "__main__":
    cli_main()
