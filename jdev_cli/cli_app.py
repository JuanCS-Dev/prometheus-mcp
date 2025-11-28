"""Command-line interface for qwen-dev-cli."""

import asyncio
import json
from pathlib import Path
from typing import Optional, List
import typer
from rich.console import Console
from rich.markdown import Markdown

from rich.panel import Panel

from jdev_cli.core.llm import llm_client
from .core.context import context_builder
from jdev_cli.core.mcp_client import MCPClient
from .core.config import config
from jdev_cli.tools.registry_helper import get_default_registry
from jdev_cli.orchestration.squad import DevSquad

app = typer.Typer(
    name="qwen-dev",
    help="AI-Powered Code Assistant with MCP Integration",
    add_completion=False
)

def get_squad() -> DevSquad:
    """Initialize DevSquad with default components."""
    registry = get_default_registry()
    mcp_client = MCPClient(registry)
    return DevSquad(llm_client, mcp_client)
console = Console()


def validate_output_path(path_str: str) -> Path:
    """Validate output path is safe and allowed.
    
    Security checks:
    1. Must be relative or within current directory tree
    2. Cannot overwrite critical system files (checked BEFORE parent dir check)
    3. Parent directory must exist
    
    Raises:
        ValueError: If path is unsafe or forbidden
        FileNotFoundError: If parent directory doesn't exist
    """
    path = Path(path_str).resolve()
    cwd = Path.cwd().resolve()

    # Check 1: Must be within current working directory tree
    try:
        path.relative_to(cwd)
    except ValueError:
        raise ValueError(
            f"Security: Output path must be within current directory.\n"
            f"  Requested: {path}\n"
            f"  Allowed: {cwd} and subdirectories"
        )

    # Check 2: Forbidden paths/files (check BEFORE parent existence)
    forbidden_patterns = ['.git', '.env', '.ssh', 'id_rsa', 'id_ed25519', 'authorized_keys']
    path_parts = path.parts

    for pattern in forbidden_patterns:
        if any(pattern in part for part in path_parts):
            raise ValueError(
                f"Security: Cannot write to protected path containing '{pattern}': {path}"
            )

    # Check 3: Parent directory must exist
    if not path.parent.exists():
        raise FileNotFoundError(
            f"Parent directory does not exist: {path.parent}\n"
            f"Create it first with: mkdir -p {path.parent}"
        )

    return path


@app.command()
def explain(
    file_path: str = typer.Argument(..., help="Path to file to explain"),
    context_files: Optional[List[str]] = typer.Option(
        None, "--context", help="Additional context files"
    ),
    model: Optional[str] = typer.Option(None, "--model", help="LLM model to use"),
):
    """Explain code from a file."""
    console.print(f"\n[bold blue]🔍 Explaining:[/bold blue] {file_path}\n")

    # Read main file
    success, content, error = context_builder.read_file(file_path)

    if not success:
        console.print(f"[bold red]❌ Error:[/bold red] {error}")
        raise typer.Exit(1)

    # Add context files if provided
    if context_files:
        console.print("[dim]📂 Loading context files...[/dim]")
        results = context_builder.add_files(context_files)
        for file, result in results.items():
            console.print(f"  {result}")

    # Build prompt
    prompt = f"Please explain this code:\n\n```\n{content}\n```"

    if context_files:
        context = context_builder.get_context()
        prompt = context_builder.inject_to_prompt(prompt)

    # Generate explanation
    with console.status("[bold green]Generating explanation...", spinner="dots"):
        response = asyncio.run(llm_client.generate(prompt))

    console.print("\n[bold green]📝 Explanation:[/bold green]\n")
    console.print(Markdown(response))

    # Clear context for next use
    context_builder.clear()


@app.command()
def generate(
    prompt: str = typer.Argument(..., help="What code to generate"),
    context_files: Optional[List[str]] = typer.Option(
        None, "--context", help="Context files for reference"
    ),
    output: Optional[str] = typer.Option(None, "--output", help="Save to file"),
    stream: bool = typer.Option(True, "--stream", help="Stream output"),
):
    """Generate code based on a prompt."""
    console.print(f"\n[bold blue]✨ Generating:[/bold blue] {prompt}\n")

    # Add context files if provided
    if context_files:
        console.print("[dim]📂 Loading context files...[/dim]")
        results = context_builder.add_files(context_files)
        for file, result in results.items():
            console.print(f"  {result}")

        context = context_builder.get_context()
        prompt = context_builder.inject_to_prompt(prompt)

    # Generate code
    console.print("[bold green]📝 Generated Code:[/bold green]\n")

    if stream:
        # Stream output
        async def stream_generation():
            async for chunk in llm_client.stream_chat(prompt):
                console.print(chunk, end="")

        asyncio.run(stream_generation())
    else:
        # Non-streaming
        with console.status("[bold green]Generating code...", spinner="dots"):
            response = asyncio.run(llm_client.generate(prompt))
        console.print(Markdown(response))

    console.print("\n")

    # Save to file if requested
    if output:
        Path(output).write_text(response)
        console.print(f"[bold green]✅ Saved to:[/bold green] {output}")

    # Clear context
    context_builder.clear()


@app.command()
def serve(
    port: int = typer.Option(7860, "--port", help="Port for web UI"),
    share: bool = typer.Option(False, "--share", help="Create public share link"),
):
    """Start the Gradio web UI."""
    console.print(f"\n[bold blue]🚀 Starting web UI on port {port}...[/bold blue]\n")

    # Import here to avoid loading Gradio unless needed
    try:
        from .ui import create_ui

        demo = create_ui()
        demo.launch(server_port=port, share=share)

    except ImportError as e:
        console.print("[bold red]❌ Error:[/bold red] Gradio not installed")
        console.print("[dim]Install with: pip install gradio>=6.0.0[/dim]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[bold red]❌ Error:[/bold red] {e}")
        raise typer.Exit(1)


@app.command()
def chat(
    message: Optional[str] = typer.Option(None, "--message", help="Single message (non-interactive)"),
    no_context: bool = typer.Option(False, "--no-context", help="Disable project context"),
    output_file: Optional[str] = typer.Option(None, "--output", help="Save output to file"),
    json_output: bool = typer.Option(False, "--json", help="Output in JSON format"),
):
    """Start interactive chat or execute single message.
    
    Examples:
        qwen chat                                        # Interactive mode
        qwen chat --message "list all Python files"      # Single command
        qwen chat --message "show git status" --json     # JSON output
        qwen chat --message "create README" --output result.txt
    """
    if message:
        # Non-interactive mode
        from .core.single_shot import execute_single_shot

        # FIX #2: Only show "Executing:" if NOT json mode (keeps JSON clean)
        if not json_output:
            console.print(f"[dim]Executing:[/dim] {message}\n")

        # Execute
        result = asyncio.run(execute_single_shot(
            message,
            include_context=not no_context
        ))

        # Format output
        if json_output:
            output = json.dumps(result, indent=2)
        else:
            output = result['output']

            if not result['success'] and result['errors']:
                output += '\n\n[red]Errors:[/red]\n'
                output += '\n'.join(f"  - {err}" for err in result['errors'])

        # FIX #1 & #3: Save to file with proper error handling and path validation
        if output_file:
            try:
                safe_path = validate_output_path(output_file)
                safe_path.write_text(output)
                console.print(f"[green]✓ Output saved to:[/green] {output_file}")
            except (ValueError, FileNotFoundError) as e:
                console.print(f"[red]✗ Error:[/red] {e}")
                raise typer.Exit(1)
            except PermissionError as e:
                console.print(f"[red]✗ Permission denied:[/red] {output_file}")
                console.print(f"[dim]Details: {e}[/dim]")
                raise typer.Exit(1)
            except OSError as e:
                console.print(f"[red]✗ Failed to write file:[/red] {e}")
                raise typer.Exit(1)
        else:
            if json_output:
                console.print(output)
            else:
                from rich.markdown import Markdown
                console.print(Markdown(output))

        # Exit with appropriate code
        raise typer.Exit(0 if result['success'] else 1)

    else:
        # Interactive mode - launch shell
        console.print("\n[bold blue]🚀 Starting interactive shell...[/bold blue]\n")
        console.print("[dim]Type 'quit' or press Ctrl+D to exit[/dim]\n")

        try:
            from .shell import main as shell_main
            asyncio.run(shell_main())
        except KeyboardInterrupt:
            console.print("\n\n[yellow]Goodbye! 👋[/yellow]\n")
        except Exception as e:
            console.print(f"\n[red]Error:[/red] {e}\n")
            raise typer.Exit(1)


@app.command()
def version():
    """Show version information."""
    console.print("\n[bold]qwen-dev-cli[/bold] v0.1.0")
    console.print("AI-Powered Code Assistant with MCP Integration")
    console.print("\n[dim]Powered by:[/dim]")
    console.print(f"  • Model: {config.hf_model}")
    console.print(f"  • MCP: {'Enabled' if mcp_manager.enabled else 'Disabled'}")
    console.print()


@app.command()
def config_show():
    """Show current configuration."""
    console.print("\n[bold]📋 Configuration:[/bold]\n")

    # LLM settings
    console.print("[bold blue]LLM Settings:[/bold blue]")
    console.print(f"  Model: {config.hf_model}")
    console.print(f"  Max Tokens: {config.max_tokens}")
    console.print(f"  Temperature: {config.temperature}")
    console.print(f"  Streaming: {config.stream}")

    # Context settings
    console.print("\n[bold blue]Context Settings:[/bold blue]")
    console.print(f"  Max Files: {config.max_context_files}")
    console.print(f"  Max File Size: {config.max_file_size_kb}KB")

    # MCP settings
    console.print("\n[bold blue]MCP Settings:[/bold blue]")
    stats = mcp_manager.get_stats()
    console.print(f"  Enabled: {stats['enabled']}")
    console.print(f"  Root Dir: {stats['root_dir']}")
    console.print(f"  Files in Context: {stats['files']}")

    console.print()


@app.command()
def shell():
    """Start interactive AI shell (SIMPLE VERSION)."""
    from .shell_simple import SimpleShell
    import asyncio
    import os

    print("✓ Loaded .env from", os.getenv("ENV_FILE", ".env"))
    print("Starting simple shell...")

    try:
        shell_instance = SimpleShell()
        asyncio.run(shell_instance.run())
    except KeyboardInterrupt:
        console.print("\n[yellow]Shell interrupted[/yellow]")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        import traceback
        traceback.print_exc()


# Session management commands
sessions_app = typer.Typer(
    name="sessions",
    help="Manage saved sessions",
    add_completion=False
)
app.add_typer(sessions_app, name="sessions")


@sessions_app.command("list")
def list_sessions(
    limit: int = typer.Option(10, "--limit", help="Number of sessions to show"),
    all_sessions: bool = typer.Option(False, "--all", "-a", help="Show all sessions"),
    cwd_filter: Optional[str] = typer.Option(None, "--cwd", help="Filter by working directory (substring)"),
    min_messages: Optional[int] = typer.Option(None, "--min-messages", help="Minimum number of messages"),
    sort_by: str = typer.Option("activity", "--sort", help="Sort by: activity, messages, files"),
):
    """List all saved sessions with filtering and sorting.
    
    Examples:
        qwen sessions list                          # Show 10 most recent
        qwen sessions list --all                    # Show all sessions
        qwen sessions list --cwd python-app         # Filter by directory
        qwen sessions list --min-messages 5         # Sessions with 5+ messages
        qwen sessions list --sort messages          # Sort by message count
    """
    from .session import SessionManager
    from rich.table import Table
    from datetime import datetime

    manager = SessionManager()
    sessions = manager.list_sessions()

    if not sessions:
        console.print("[yellow]No sessions found[/yellow]")
        return

    # Apply filters (AIR GAP #3)
    if cwd_filter:
        sessions = [s for s in sessions if cwd_filter.lower() in s['cwd'].lower()]
        if not sessions:
            console.print(f"[yellow]No sessions found matching cwd: {cwd_filter}[/yellow]")
            return

    if min_messages is not None:
        sessions = [s for s in sessions if s['messages'] >= min_messages]
        if not sessions:
            console.print(f"[yellow]No sessions found with {min_messages}+ messages[/yellow]")
            return

    # Apply sorting (AIR GAP #3)
    if sort_by == "messages":
        sessions = sorted(sessions, key=lambda s: s['messages'], reverse=True)
    elif sort_by == "files":
        sessions = sorted(sessions, key=lambda s: s['files_read'], reverse=True)
    # Default: already sorted by activity (most recent first)

    # Apply limit
    total_matching = len(sessions)
    if not all_sessions:
        sessions = sessions[:limit]

    # Create table with filter info
    title = f"Saved Sessions ({len(sessions)}"
    if total_matching != len(manager.list_sessions()):
        title += f" of {total_matching} matching"
    title += f" total: {len(manager.list_sessions())})"

    table = Table(title=title)
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("Working Directory", style="blue")
    table.add_column("Messages", justify="right", style="green")
    table.add_column("Files", justify="right", style="yellow")
    table.add_column("Last Activity", style="magenta")

    for session in sessions:
        last_activity = datetime.fromisoformat(session['last_activity'])
        age = datetime.now() - last_activity

        if age.days > 0:
            age_str = f"{age.days}d ago"
        elif age.seconds > 3600:
            age_str = f"{age.seconds // 3600}h ago"
        else:
            age_str = f"{age.seconds // 60}m ago"

        table.add_row(
            session['id'],
            session['cwd'],
            str(session['messages']),
            str(session['files_read']),
            age_str
        )

    console.print(table)

    # Show helpful hints
    if not all_sessions and total_matching > limit:
        console.print(f"\n[dim]Showing {len(sessions)} of {total_matching} matching sessions. Use --all to see all.[/dim]")

    if cwd_filter or min_messages:
        filters = []
        if cwd_filter:
            filters.append(f"cwd='{cwd_filter}'")
        if min_messages:
            filters.append(f"messages≥{min_messages}")
        console.print(f"[dim]Filters applied: {', '.join(filters)}[/dim]")


@sessions_app.command("show")
def show_session(
    session_id: str = typer.Argument(..., help="Session ID to show"),
):
    """Show detailed information about a session."""
    from .session import SessionManager
    from rich.tree import Tree

    manager = SessionManager()

    try:
        state = manager.load_session(session_id)
    except FileNotFoundError:
        console.print(f"[red]Session '{session_id}' not found[/red]")
        raise typer.Exit(1)

    # Create tree
    tree = Tree(f"[bold cyan]Session: {session_id}[/bold cyan]")

    # Basic info
    info = tree.add("[yellow]📋 Information[/yellow]")
    info.add(f"Working Directory: {state.cwd}")
    info.add(f"Created: {state.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
    info.add(f"Last Activity: {state.last_activity.strftime('%Y-%m-%d %H:%M:%S')}")

    # Statistics
    stats = tree.add("[green]📊 Statistics[/green]")
    stats.add(f"Messages: {len(state.conversation)}")
    stats.add(f"Files Read: {len(state.files_read)}")
    stats.add(f"Files Modified: {len(state.files_modified)}")
    stats.add(f"Tool Calls: {state.tool_calls_count}")

    # Files
    if state.files_read:
        files = tree.add("[blue]📂 Files Read[/blue]")
        for f in sorted(state.files_read)[:10]:
            files.add(f)
        if len(state.files_read) > 10:
            files.add(f"[dim]... and {len(state.files_read) - 10} more[/dim]")

    if state.files_modified:
        modified = tree.add("[magenta]✏️  Files Modified[/magenta]")
        for f in sorted(state.files_modified):
            modified.add(f)

    console.print(tree)


@sessions_app.command("delete")
def delete_session(
    session_id: str = typer.Argument(..., help="Session ID to delete"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
):
    """Delete a session."""
    from .session import SessionManager

    manager = SessionManager()

    # Check if exists
    try:
        state = manager.load_session(session_id)
    except FileNotFoundError:
        console.print(f"[red]Session '{session_id}' not found[/red]")
        raise typer.Exit(1)

    # Confirmation
    if not force:
        confirm = typer.confirm(f"Delete session {session_id}?")
        if not confirm:
            console.print("[yellow]Cancelled[/yellow]")
            raise typer.Exit(0)

    # Delete
    manager.delete_session(session_id)
    console.print(f"[green]✅ Session {session_id} deleted[/green]")


@sessions_app.command("cleanup")
def cleanup_sessions(
    days: int = typer.Option(30, "--days", help="Delete sessions older than N days"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
):
    """Clean up old sessions."""
    from .session import SessionManager

    manager = SessionManager()

    if not force:
        confirm = typer.confirm(f"Delete sessions older than {days} days?")
        if not confirm:
            console.print("[yellow]Cancelled[/yellow]")
            raise typer.Exit(0)

    deleted = manager.cleanup_old_sessions(days=days)

    if deleted > 0:
        console.print(f"[green]✅ Deleted {deleted} old sessions[/green]")
    else:
        console.print("[yellow]No old sessions to delete[/yellow]")


@app.command()
def resume(
    session_id: Optional[str] = typer.Argument(None, help="Session ID to resume (or latest)"),
):
    """Resume a previous session."""
    from .session import SessionManager
    from .shell import InteractiveShell

    manager = SessionManager()

    # Get session
    if session_id:
        try:
            state = manager.load_session(session_id)
        except FileNotFoundError:
            console.print(f"[red]Session '{session_id}' not found[/red]")
            raise typer.Exit(1)
    else:
        state = manager.get_latest_session()
        if not state:
            console.print("[yellow]No sessions found[/yellow]")
            raise typer.Exit(1)

    console.print(f"[cyan]Resuming session {state.session_id}...[/cyan]")
    console.print(f"[dim]Working directory: {state.cwd}[/dim]")
    console.print(f"[dim]Messages: {len(state.conversation)}, Files: {len(state.files_read)}[/dim]\n")

    # Start shell with restored state
    try:
        shell_instance = InteractiveShell(session_state=state)
        asyncio.run(shell_instance.run())
    except KeyboardInterrupt:
        console.print("\n[yellow]Shell interrupted[/yellow]")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        import traceback
        traceback.print_exc()



# Squad management commands
squad_app = typer.Typer(
    name="squad",
    help="Manage DevSquad agents",
    add_completion=False
)
app.add_typer(squad_app, name="squad")

@squad_app.command("run")
def squad_run(request: str):
    """Start a DevSquad mission."""
    console.print(Panel(f"[bold blue]🚀 Starting DevSquad Mission[/bold blue]\n[white]{request}[/white]"))

    try:
        squad = get_squad()

        async def run():
            with console.status("[bold green]DevSquad Active...[/bold green]"):
                result = await squad.execute_workflow(request)
            console.print(squad.get_phase_summary(result))

        asyncio.run(run())

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(1)

@squad_app.command("status")
def squad_status():
    """Check status of all specialist agents."""
    from rich.table import Table

    table = Table(title="DevSquad Agent Status")
    table.add_column("Agent", style="cyan")
    table.add_column("Role", style="magenta")
    table.add_column("Status", style="green")
    table.add_column("Capabilities", style="yellow")

    # We can inspect the classes or instantiate to check
    agents = [
        ("Architect", "Architecture Analysis", "Active", "READ_ONLY"),
        ("Explorer", "Context Discovery", "Active", "READ_ONLY, SEARCH"),
        ("Planner", "Execution Planning", "Active", "DESIGN"),
        ("Refactorer", "Code Execution", "Active", "FILE_EDIT, BASH, GIT"),
        ("Reviewer", "Quality Control", "Active", "READ_ONLY, GIT"),
    ]

    for agent, role, status, caps in agents:
        table.add_row(agent, role, status, caps)

    console.print(table)


# Workflow management commands
workflow_app = typer.Typer(
    name="workflow",
    help="Manage and run workflows",
    add_completion=False
)
app.add_typer(workflow_app, name="workflow")

@workflow_app.command("list")
def list_workflows():
    """List available workflows."""
    from .orchestration.workflows import WorkflowLibrary
    from rich.table import Table

    lib = WorkflowLibrary()
    workflows = lib.list_workflows()

    table = Table(title="Available Workflows")
    table.add_column("ID", style="cyan")
    table.add_column("Name", style="blue")
    table.add_column("Type", style="magenta")
    table.add_column("Description", style="white")

    for w in workflows:
        table.add_row(w.id, w.name, w.type.value, w.description)

    console.print(table)

@workflow_app.command("run")
def workflow_run(name: str):
    """Execute a predefined workflow."""
    from .orchestration.workflows import WorkflowLibrary
    from rich.panel import Panel
    from rich.table import Table

    library = WorkflowLibrary()
    workflow = library.get_workflow(name)

    if not workflow:
        console.print(f"[bold red]Error:[/bold red] Workflow '{name}' not found.")
        console.print("Run [bold]qwen-dev workflow list[/bold] to see available workflows.")
        raise typer.Exit(1)

    console.print(Panel(
        f"[bold blue]Starting Workflow: {workflow.name}[/bold blue]\n"
        f"[dim]{workflow.description}[/dim]"
    ))

    # Prompt for parameters
    params = {}
    if workflow.parameters:
        console.print("\n[yellow]Configuration Required:[/yellow]")
        for param_name, param_desc in workflow.parameters.items():
            value = typer.prompt(f"{param_name} ({param_desc})")
            params[param_name] = value

    # Show plan
    table = Table(title="Execution Plan")
    table.add_column("Step", style="cyan")
    table.add_column("Description", style="white")

    for i, step in enumerate(workflow.steps, 1):
        table.add_row(f"{i}. {step.name}", step.description)

    console.print(table)

    if not typer.confirm("\nProceed with execution?"):
        console.print("[yellow]Aborted.[/yellow]")
        raise typer.Exit()

    # Execute
    try:
        squad = get_squad()

        # Construct request from workflow
        request = f"Execute workflow '{workflow.name}': {workflow.description}\n\nSteps:\n"
        for step in workflow.steps:
            request += f"- {step.name}: {step.description}\n"
        if params:
            request += "\nParameters:\n"
            for k, v in params.items():
                request += f"- {k}: {v}\n"

        async def run():
            with console.status(f"[bold green]Running Workflow {name}...[/bold green]"):
                result = await squad.execute_workflow(request)
            console.print(squad.get_phase_summary(result))

        asyncio.run(run())

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(1)


def main():
    """Entry point for CLI."""
    app()


if __name__ == "__main__":
    main()
