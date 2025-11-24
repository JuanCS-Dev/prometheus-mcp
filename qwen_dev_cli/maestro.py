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

import asyncio
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
from rich.live import Live
from rich.spinner import Spinner
from rich import print as rprint
from rich.prompt import Confirm

# Real agents v6.0 integration
from qwen_dev_cli.core.llm import LLMClient
from qwen_dev_cli.core.mcp_client import MCPClient
from qwen_dev_cli.tools.base import ToolRegistry
from qwen_dev_cli.agents.base import AgentTask
from qwen_dev_cli.agents.planner import PlannerAgent
from qwen_dev_cli.agents.explorer import ExplorerAgent
from qwen_dev_cli.agents.reviewer import ReviewerAgent

# Governance integration (Phase 5 - Nov 2025)
from qwen_dev_cli.maestro_governance import MaestroGovernance, render_sofia_counsel

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
        self.governance = None  # MaestroGovernance instance (Phase 5)

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
                    steps = "\n".join(f"• {s.get('action', s)}" for s in steps_list)
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
    stream: bool = True,
    with_governance: bool = True
) -> dict:
    """
    Delegates execution to the specific v6.0 Agent.

    Args:
        agent_name: Name of agent (planner, reviewer, explorer)
        prompt: User prompt/request
        context: Additional context
        stream: Enable streaming output (future: real-time updates)
        with_governance: Enable governance checks (default: True)

    Returns:
        dict: Agent response data (ExecutionPlan, ReviewReport, etc.)
    """
    start_time = datetime.now()
    agent_name = agent_name.lower()

    # Validate agent exists
    if agent_name not in state.agents:
        raise ValueError(f"Agent '{agent_name}' not found in swarm. Available: {list(state.agents.keys())}")

    target_agent = state.agents[agent_name]

    console.print(f"\n[bold blue]⚡ {target_agent.role.value.upper()}[/bold blue] [dim]activated[/dim]")

    try:
        # Create the standardized Task object (BaseAgent protocol)
        task = AgentTask(
            request=prompt,
            context=context or {},
            metadata={"interface": "maestro_v7", "timestamp": datetime.now().isoformat()}
        )

        # GOVERNANCE INTEGRATION (Phase 5 - Nov 2025)
        # Execute through governance pipeline if available and enabled
        if with_governance and state.governance:
            with Progress(
                SpinnerColumn("dots12"),
                TextColumn("[bold blue]{task.description}"),
                console=console,
                transient=True
            ) as progress:
                spinner_task = progress.add_task("Reasoning with governance...", total=None)

                # Execute with constitutional checks
                response = await state.governance.execute_with_governance(
                    agent=target_agent,
                    task=task
                )

                progress.update(spinner_task, completed=True)
        else:
            # Fallback: Execute without governance
            with Progress(
                SpinnerColumn("dots12"),
                TextColumn("[bold blue]{task.description}"),
                console=console,
                transient=True
            ) as progress:
                spinner_task = progress.add_task("Reasoning...", total=None)

                # THE REAL CALL to agent's neural core
                response = await target_agent.execute(task)

                progress.update(spinner_task, completed=True)

        duration = (datetime.now() - start_time).total_seconds()

        # Check success
        if not response.success:
            render_error(f"{agent_name.title()} reported failure", response.error or "Unknown error")
            return {"status": "failed", "error": response.error, "reasoning": response.reasoning}

        render_success("Task Complete", duration)

        # Log reasoning for debugging
        logger.info(f"{agent_name} reasoning: {response.reasoning}")

        # Return the payload (already a dict from Pydantic model_dump())
        return response.data

    except Exception as e:
        render_error(f"Crash in {agent_name}", str(e))
        logger.exception(f"Agent {agent_name} crash details")
        raise

# ============================================================================
# INITIALIZATION (Lazy Loading - Fast Startup)
# ============================================================================

async def ensure_initialized():
    """Hydrate the Swarm - Real initialization with v6.0 agents"""
    if state.initialized:
        return
    
    console.print("\n[dim]🔌 Connecting to Matrix (LLM & MCP)...[/dim]")
    
    try:
        # 1. Core Infrastructure
        with console.status("[bold green]Bootstrapping Neural Core...[/bold green]"):
            state.llm_client = LLMClient()  # Uses config from .env
            
            # Initialize tool registry and MCP adapter
            registry = ToolRegistry()
            state.mcp_client = MCPClient(registry)
        
        # 2. Wake up the Agents v6.0
        with console.status("[bold green]Bootstrapping Neural Agents...[/bold green]"):
            state.agents = {
                "planner": PlannerAgent(state.llm_client, state.mcp_client),
                "explorer": ExplorerAgent(state.llm_client, state.mcp_client),
                "reviewer": ReviewerAgent(state.llm_client, state.mcp_client)
                # Add Security, Refactorer here as they're implemented
            }

            # Optional: Pre-load Explorer graph cache
            try:
                if hasattr(state.agents["explorer"], "load_graph"):
                    await state.agents["explorer"].load_graph()
            except:
                pass  # First run, no cache yet

        # 3. Initialize Constitutional Governance (Phase 5 - Nov 2025)
        try:
            state.governance = MaestroGovernance(
                llm_client=state.llm_client,
                mcp_client=state.mcp_client,
                enable_governance=True,
                enable_counsel=True,
                enable_observability=True,
                auto_risk_detection=True
            )
            await state.governance.initialize()
        except Exception as e:
            logger.warning(f"Governance initialization failed: {e}")
            console.print(f"[yellow]⚠️  Running without governance (degraded mode)[/yellow]")
            state.governance = None

        state.initialized = True
        console.print("[green]✓[/green] [bold]Vértice-MAXIMUS Online[/bold]\n")
        
    except Exception as e:
        render_error("Bootstrap Failed", str(e))
        logger.exception("Initialization error details")
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
        pass
    
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
        "files": [str(target_path)],
        "deep_mode": deep,
        "auto_fix": fix
    }
    
    result = await execute_agent_task("reviewer", f"Review {target}", context)
    
    # Render results
    if "issues" in result:
        table = Table(title="🔍 Review Results", border_style="yellow")
        table.add_column("Severity", style="red")
        table.add_column("File", style="cyan")
        table.add_column("Line", style="dim")
        table.add_column("Issue", style="white")
        
        for issue in result.get("issues", [])[:20]:  # Limit to 20
            table.add_row(
                issue.get("severity", "UNKNOWN"),
                issue.get("file", ""),
                str(issue.get("line", "")),
                issue.get("message", "")[:60]
            )
        
        console.print(table)
        console.print(f"\n[dim]Score: {result.get('score', 0)}/100[/dim]")

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

@agent_app.async_command("sofia")
async def agent_sofia(
    question: Annotated[str, typer.Argument(help="Ethical question or dilemma to consult Sofia about")],
):
    """
    🕊️  Consult Sofia (Wise Counselor) for ethical guidance.

    Sofia provides philosophical counsel using Socratic method and virtue ethics
    from Early Christianity (Pre-Nicene, 50-325 AD).

    Example:
        maestro agent sofia "Should I implement aggressive caching that might compromise user privacy?"
        maestro agent sofia "How do I balance feature velocity with code quality?"
    """
    await ensure_initialized()

    if not state.governance:
        render_error("Sofia not available", "Governance system not initialized")
        raise typer.Exit(1)

    console.print("\n[bold magenta]🕊️  Consulting Sofia (Wise Counselor)...[/bold magenta]")
    console.print("[dim]Sofia will deliberate on your question using virtue ethics and Socratic method[/dim]\n")

    try:
        # Ask Sofia directly (no worker agent involved)
        result = await state.governance.ask_sofia(question)

        # Render beautiful counsel output
        render_sofia_counsel(result)

    except Exception as e:
        render_error("Sofia consultation failed", str(e))
        logger.exception("Sofia command error")
        raise typer.Exit(1)

@agent_app.async_command("governance")
async def agent_governance_status():
    """
    🛡️  Show governance system status.

    Displays status of Justiça (governance) and Sofia (counselor) systems,
    including configuration and availability.

    Example:
        maestro agent governance
    """
    await ensure_initialized()

    if not state.governance:
        console.print("[yellow]⚠️  Governance system not initialized[/yellow]")
        raise typer.Exit(1)

    status = state.governance.get_governance_status()

    # Create status table
    table = Table(title="🛡️  Constitutional Governance Status", border_style="cyan")
    table.add_column("Component", style="cyan")
    table.add_column("Status", style="white")
    table.add_column("Details", style="dim")

    # Add rows
    table.add_row(
        "System",
        "✅ Online" if status["initialized"] else "❌ Offline",
        "Governance pipeline active"
    )

    table.add_row(
        "Justiça (Governance)",
        "✅ Active" if status["justica_available"] else "❌ Unavailable",
        "Constitutional checks enabled" if status["governance_enabled"] else "Disabled"
    )

    table.add_row(
        "Sofia (Counselor)",
        "✅ Active" if status["sofia_available"] else "❌ Unavailable",
        "Ethical counsel enabled" if status["counsel_enabled"] else "Disabled"
    )

    table.add_row(
        "Observability",
        "✅ Active" if status["observability_enabled"] else "❌ Disabled",
        "OpenTelemetry tracing"
    )

    table.add_row(
        "Risk Detection",
        "✅ Auto" if status["auto_risk_detection"] else "⚙️  Manual",
        "Automatic risk level detection"
    )

    console.print(table)

    # Show usage hint
    console.print("\n[dim]Commands:[/dim]")
    console.print("[dim]  • maestro agent sofia \"<question>\"  - Consult Sofia for ethical guidance[/dim]")
    console.print("[dim]  • maestro agent plan/review/explore  - All protected by governance[/dim]")

# ============================================================================
# COMMANDS: CONFIGURATION
# ============================================================================

@config_app.command("show")
def config_show():
    """📋 Show current configuration"""
    table = Table(title="⚙️  Configuration", border_style="blue")
    table.add_column("Key", style="cyan")
    table.add_column("Value", style="white")
    
    # Mock config
    config = {
        "log_file": "maestro.log",
        "agents_initialized": str(state.initialized),
        "python_version": sys.version.split()[0],
        "context_size": len(state.context)
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
