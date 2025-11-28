"""
Maestro Shell v7.0: The Ultimate AI-Powered CLI (Nov 2025)

Supersonic. Reliable. Minimal. Production-Ready.

Architecture:
- Typer (FastAPI of CLIs) + async-typer for async support
- Rich for gorgeous terminal UI
- Structured logging (no noise)
- Graceful error handling
- Auto-completion for all shells
- Type-safe commands
- Sub-command architecture
- Streaming output for real-time feedback

Based on 2025 best practices:
- https://typer.tiangolo.com/
- https://rich.readthedocs.io/
- FastAPI-style async patterns
"""

import sys
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, Annotated
from enum import Enum

# Silence the noise FIRST
import os
os.environ["GRPC_VERBOSITY"] = "ERROR"
os.environ["GLOG_minloglevel"] = "3"

# Modern CLI Stack (2025)
from async_typer import AsyncTyper
import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.syntax import Syntax
from rich.markdown import Markdown
from rich.prompt import Confirm

# Your agents
from .agents.planner import PlannerAgent
from .agents.explorer import ExplorerAgent
from .agents.reviewer import ReviewerAgent
from .core.llm import LLMClient
from .core.mcp import MCPClient
from .agents.base import AgentTask, AgentResponse

# ============================================================================
# CONFIGURATION & SETUP
# ============================================================================

# Global console (singleton)
console = Console()

# Structured logging (file-only, no terminal pollution)
logging.basicConfig(
    filename='maestro.log',
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Main app (Typer instance)
app = AsyncTyper(
    name="maestro",
    help="🎯 Maestro - AI-Powered Development CLI v7.0",
    add_completion=True,
    rich_markup_mode="rich"
)

# Sub-apps for modularity
agent_app = AsyncTyper(help="🤖 Agent commands")
config_app = AsyncTyper(help="⚙️  Configuration commands")

app.add_typer(agent_app, name="agent")
app.add_typer(config_app, name="config")

# ============================================================================
# GLOBAL STATE (Minimalist Context)
# ============================================================================

class GlobalState:
    """Minimal global state - keep it light"""
    def __init__(self):
        self.agents = {}
        self.context = {}
        self.initialized = False
        self.llm_client = None
        self.mcp_client = None

state = GlobalState()

# ============================================================================
# OUTPUT FORMATTERS (Beautiful, Fast, Informative)
# ============================================================================

class OutputFormat(str, Enum):
    """Output format options"""
    table = "table"
    json = "json"
    markdown = "markdown"
    plain = "plain"

def render_plan(data: dict, format: OutputFormat = OutputFormat.table):
    """Render execution plan beautifully"""
    if format == OutputFormat.table:
        table = Table(
            title="📋 Execution Plan",
            show_header=True,
            header_style="bold cyan",
            border_style="blue"
        )
        table.add_column("#", style="dim", width=4)
        table.add_column("Stage", style="cyan")
        table.add_column("Steps", style="white")
        table.add_column("Status", style="green")

        for idx, stage in enumerate(data.get("stages", []), 1):
            steps_list = stage.get("steps", [])
            if isinstance(steps_list, list):
                if steps_list and isinstance(steps_list[0], dict):
                    steps = "\n".join(f"• {s.get('action', s.get('objective', 'Unknown'))}" for s in steps_list)
                else:
                    steps = "\n".join(f"• {s}" for s in steps_list)
            else:
                steps = str(steps_list)

            table.add_row(
                str(idx),
                stage.get("name", "Unknown"),
                steps,
                "✓ Ready"
            )

        console.print(table)

    elif format == OutputFormat.json:
        import json
        console.print_json(json.dumps(data, indent=2))

    elif format == OutputFormat.markdown:
        md = f"# {data.get('goal', 'Plan')}\n\n"
        for stage in data.get("stages", []):
            md += f"## {stage.get('name')}\n"
            for step in stage.get("steps", []):
                if isinstance(step, dict):
                    md += f"- {step.get('action', step.get('objective', 'Unknown'))}\n"
                else:
                    md += f"- {step}\n"
            md += "\n"
        console.print(Markdown(md))

    else:  # plain
        console.print(data)

def render_code(code: str, language: str = "python"):
    """Render code with syntax highlighting"""
    syntax = Syntax(code, language, theme="monokai", line_numbers=True)
    console.print(Panel(syntax, title=f"📝 {language.upper()}", border_style="green"))

def render_error(error: str, details: Optional[str] = None):
    """Render errors beautifully"""
    console.print(f"\n[bold red]❌ Error:[/bold red] {error}")
    if details:
        console.print(f"[dim]{details}[/dim]")
    logger.error(f"{error} | {details}")

def render_success(message: str, duration: Optional[float] = None):
    """Render success message"""
    if duration:
        console.print(f"\n[bold green]✅ {message}[/bold green] [dim]({duration:.2f}s)[/dim]")
    else:
        console.print(f"\n[bold green]✅ {message}[/bold green]")

# ============================================================================
# ASYNC AGENT EXECUTION (Fast, Non-Blocking, Beautiful)
# ============================================================================

async def execute_agent_task(
    agent_name: str,
    prompt: str,
    context: dict = None,
    stream: bool = True
) -> dict:
    """
    Execute agent task with beautiful streaming output.
    
    Args:
        agent_name: Name of agent (planner, reviewer, explorer)
        prompt: User prompt/request
        context: Additional context
        stream: Enable streaming output
    
    Returns:
        dict: Agent response data
    """
    start_time = datetime.now()

    console.print(f"\n[bold blue]🤖 {agent_name.upper()}[/bold blue] [dim]processing...[/dim]")

    try:
        # Show spinner while processing
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            transient=True
        ) as progress:
            task_desc = progress.add_task(f"Analyzing: {prompt[:40]}...", total=None)

            # Real agent execution
            agent = state.agents.get(agent_name)
            if not agent:
                raise ValueError(f"Agent '{agent_name}' not initialized")

            agent_task = AgentTask(
                request=prompt,
                context=context or {}
            )

            response: AgentResponse = await agent.execute(agent_task)
            progress.update(task_desc, completed=True)

        if not response.success:
            raise Exception(response.error or "Agent execution failed")

        duration = (datetime.now() - start_time).total_seconds()
        render_success(f"{agent_name.capitalize()} completed", duration)

        return response.data

    except Exception as e:
        render_error(f"{agent_name} failed", str(e))
        raise

# ============================================================================
# INITIALIZATION (Lazy Loading - Fast Startup)
# ============================================================================

async def ensure_initialized():
    """Lazy initialization - only when needed"""
    if state.initialized:
        return

    console.print("\n[dim]Initializing agents...[/dim]")

    try:
        # Initialize LLM and MCP clients
        state.llm_client = LLMClient()
        state.mcp_client = MCPClient()

        # Initialize agents (lazy)
        state.agents['planner'] = PlannerAgent(state.llm_client, state.mcp_client)
        state.agents['reviewer'] = ReviewerAgent(state.llm_client, state.mcp_client)
        state.agents['explorer'] = ExplorerAgent(state.llm_client, state.mcp_client)

        state.initialized = True
        console.print("[green]✓[/green] [dim]Ready[/dim]\n")

    except Exception as e:
        render_error("Initialization failed", str(e))
        raise

# ============================================================================
# COMMANDS: AGENT OPERATIONS
# ============================================================================

@agent_app.async_command("plan")
async def agent_plan(
    goal: Annotated[str, typer.Argument(help="What do you want to accomplish?")],
    output: Annotated[OutputFormat, typer.Option("--output", "-o", help="Output format")] = OutputFormat.table,
    context_file: Annotated[Optional[Path], typer.Option("--context", "-c", help="Context file")] = None,
):
    """
    🎯 Generate execution plan using the Planner agent.
    
    Example:
        maestro agent plan "Implement user authentication with JWT"
        maestro agent plan "Refactor database layer" --output json
    """
    await ensure_initialized()

    context = {}
    if context_file and context_file.exists():
        # Load context from file
        import json
        with open(context_file) as f:
            context = json.load(f)

    result = await execute_agent_task("planner", goal, context)
    render_plan(result, output)

@agent_app.async_command("review")
async def agent_review(
    target: Annotated[str, typer.Argument(help="File or directory to review")],
    deep: Annotated[bool, typer.Option("--deep", help="Deep analysis mode")] = False,
    fix: Annotated[bool, typer.Option("--fix", help="Auto-fix issues")] = False,
):
    """
    🔍 Review code using the Reviewer agent.
    
    Example:
        maestro agent review src/auth.py
        maestro agent review . --deep
    """
    await ensure_initialized()

    target_path = Path(target)
    if not target_path.exists():
        render_error(f"Path not found: {target}")
        raise typer.Exit(1)

    context = {
        "files": [str(target_path)] if target_path.is_file() else [str(f) for f in target_path.rglob("*.py")],
        "deep_mode": deep,
        "auto_fix": fix
    }

    result = await execute_agent_task("reviewer", f"Review {target}", context)

    # Render results
    report = result.get("report", result)
    if "issues" in report:
        table = Table(title="🔍 Review Results", border_style="yellow")
        table.add_column("Severity", style="red")
        table.add_column("File", style="cyan")
        table.add_column("Line", style="dim")
        table.add_column("Issue", style="white")

        for issue in report.get("issues", [])[:20]:  # Limit to 20
            table.add_row(
                issue.get("severity", "UNKNOWN"),
                issue.get("file", ""),
                str(issue.get("line", "")),
                issue.get("message", "")[:60]
            )

        console.print(table)
        console.print(f"\n[dim]Score: {report.get('score', 0)}/100[/dim]")
        console.print(f"[dim]Approved: {report.get('approved', False)}[/dim]")

@agent_app.async_command("explore")
async def agent_explore(
    operation: Annotated[str, typer.Argument(help="Operation: map, blast-radius, search, insights")],
    target: Annotated[Optional[str], typer.Argument(help="Target entity/file")] = None,
    root: Annotated[Path, typer.Option("--root", "-r", help="Repository root")] = Path("."),
):
    """
    🗺️  Explore codebase using the Explorer agent.
    
    Operations:
        map          - Build repository knowledge graph
        blast-radius - Analyze impact of changes
        search       - Semantic code search
        insights     - Generate architectural insights
    
    Example:
        maestro agent explore map
        maestro agent explore blast-radius "authenticate_user"
        maestro agent explore search "database transaction handlers"
    """
    await ensure_initialized()

    context = {
        "operation": operation,
        "root_dir": str(root)
    }

    if target:
        context["target"] = target

    prompt = f"{operation} {target or ''}"
    result = await execute_agent_task("explorer", prompt, context)

    # Render based on operation
    if operation == "map":
        console.print(Panel(
            f"""[bold]Repository Map[/bold]
            
📊 Total Entities: {result.get('total_entities', 0)}
📁 Files: {result.get('files_analyzed', 0)}
🔥 Hotspots: {len(result.get('hotspots', []))}
💀 Dead Code: {result.get('dead_code', 0)} entities""",
            border_style="cyan"
        ))

        if result.get('hotspots'):
            console.print("\n[bold yellow]🔥 Hotspots (High Coupling):[/bold yellow]")
            for hotspot in result['hotspots'][:5]:
                console.print(f"  • {hotspot}")

    elif operation == "blast-radius":
        console.print(Panel(
            f"""[bold]Blast Radius Analysis[/bold]
            
🎯 Target: {target}
⚠️  Risk Level: {result.get('risk_level', 'UNKNOWN')}
📦 Impacted Files: {len(result.get('impacted_files', []))}
🔗 Dependencies: {len(result.get('transitive_dependencies', []))}""",
            border_style="red" if result.get('risk_level') == 'HIGH' else "yellow"
        ))

    else:
        console.print(result)

# ============================================================================
# COMMANDS: CONFIGURATION
# ============================================================================

@config_app.command("show")
def config_show():
    """📋 Show current configuration"""
    table = Table(title="⚙️  Configuration", border_style="blue")
    table.add_column("Key", style="cyan")
    table.add_column("Value", style="white")

    config = {
        "log_file": "maestro.log",
        "agents_initialized": str(state.initialized),
        "python_version": sys.version.split()[0],
        "context_size": len(state.context),
        "available_agents": ", ".join(state.agents.keys()) if state.agents else "None"
    }

    for key, value in config.items():
        table.add_row(key, value)

    console.print(table)

@config_app.command("reset")
def config_reset(
    force: Annotated[bool, typer.Option("--force", "-f", help="Skip confirmation")] = False
):
    """🔄 Reset configuration to defaults"""
    if not force:
        confirmed = Confirm.ask("Reset all configuration?")
        if not confirmed:
            console.print("[yellow]Cancelled[/yellow]")
            raise typer.Exit(0)

    state.context.clear()
    state.initialized = False
    render_success("Configuration reset")

# ============================================================================
# ROOT COMMANDS (Top-level convenience)
# ============================================================================

@app.command()
def version():
    """📦 Show version information"""
    console.print(Panel.fit(
        "[bold cyan]Maestro Shell v7.0[/bold cyan]\n"
        "[dim]The Ultimate AI-Powered CLI (2025)[/dim]\n\n"
        "Built with:\n"
        "  • Typer (CLI framework)\n"
        "  • Rich (Terminal UI)\n"
        "  • async-typer (Async support)",
        border_style="cyan"
    ))

@app.command()
def info():
    """ℹ️  System information"""
    console.print(Panel(
        f"""[bold]System Information[/bold]

🐍 Python: {sys.version.split()[0]}
📁 Working Directory: {Path.cwd()}
📝 Log File: maestro.log
🤖 Agents: {len(state.agents)} initialized
💾 Context Size: {len(state.context)} items""",
        border_style="blue"
    ))

# ============================================================================
# STARTUP HOOK (Welcome Message)
# ============================================================================

@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Verbose mode")] = False
):
    """
    🎯 Maestro - AI-Powered Development CLI v7.0
    
    The supersonic, reliable, minimal shell for AI-assisted development.
    """
    if ctx.invoked_subcommand is None:
        # Show welcome if no command
        console.print(Panel.fit(
            "[bold cyan]🎯 Maestro Shell v7.0[/bold cyan]\n\n"
            "Quick Start:\n"
            "  [cyan]maestro agent plan[/cyan] \"your goal\"\n"
            "  [cyan]maestro agent review[/cyan] src/\n"
            "  [cyan]maestro agent explore[/cyan] map\n\n"
            "Type [cyan]maestro --help[/cyan] for all commands",
            border_style="cyan"
        ))

    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        console.print("[dim]Verbose mode enabled[/dim]")

# ============================================================================
# ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    try:
        app()
    except KeyboardInterrupt:
        console.print("\n[yellow]👋 Goodbye![/yellow]")
        sys.exit(130)
    except Exception as e:
        console.print(f"\n[bold red]Fatal error:[/bold red] {e}")
        logger.exception("Fatal error")
        sys.exit(1)
