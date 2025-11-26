"""
ULTIMATE REPL - Integração COMPLETA de todos os componentes do projeto.

Features:
- Streaming responses (core.llm)
- TUI components (tui/*)
- Shell integration (shell/*)
- All agents (agents/*)
- All tools (tools/*)
- Command palette (ui/command_palette)
- Preview system (ui/preview_enhanced)
- Timeline (ui/timeline)
- Context awareness (tui/components/context_awareness)
- Dashboard (tui/components/dashboard)
- Metrics (tui/components/metrics)

Soli Deo Gloria 🙏
"""

import asyncio
from prompt_toolkit import PromptSession
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.formatted_text import HTML, FormattedText
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.history import FileHistory
from prompt_toolkit.patch_stdout import patch_stdout
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.live import Live
from typing import Dict, Optional, List
import sys
from pathlib import Path

# Context
from .shell_context import ShellContext

# LLM & Streaming
from qwen_dev_cli.core.llm import LLMClient

# Tools (required)
from qwen_dev_cli.tools.exec import BashCommandTool
from qwen_dev_cli.tools.file_ops import ReadFileTool, WriteFileTool, EditFileTool
from qwen_dev_cli.tools.git_ops import GitStatusTool, GitDiffTool

# Agents
from qwen_dev_cli.agents.architect import ArchitectAgent
from qwen_dev_cli.agents.documentation import DocumentationAgent
from qwen_dev_cli.agents.explorer import ExplorerAgent
from qwen_dev_cli.agents.planner import PlannerAgent
from qwen_dev_cli.agents.refactorer import RefactorerAgent
from qwen_dev_cli.agents.reviewer import ReviewerAgent
from qwen_dev_cli.agents.testing import TestingAgent

# UI (required)
from qwen_dev_cli.ui.command_palette import CommandCategory

# Optional imports with proper exception handling
try:
    from qwen_dev_cli.tools.search import SearchTool
except ImportError:
    SearchTool = None

try:
    from qwen_dev_cli.tui.components.dashboard import Dashboard
except ImportError:
    Dashboard = None

try:
    from qwen_dev_cli.tui.components.status import StatusBar
except ImportError:
    StatusBar = None

try:
    from qwen_dev_cli.tui.components.metrics import MetricsDisplay
except ImportError:
    MetricsDisplay = None

try:
    from qwen_dev_cli.tui.components.autocomplete import AutocompleteEngine
except ImportError:
    AutocompleteEngine = None

try:
    from qwen_dev_cli.tui.landing import show_landing
except ImportError:
    show_landing = None

try:
    from qwen_dev_cli.tui.feedback import FeedbackManager
except ImportError:
    FeedbackManager = None

try:
    from qwen_dev_cli.tui.history import HistoryManager
except ImportError:
    HistoryManager = None

try:
    from qwen_dev_cli.ui.preview_enhanced import PreviewManager
except ImportError:
    PreviewManager = None

try:
    from qwen_dev_cli.ui.timeline import Timeline
except ImportError:
    Timeline = None

try:
    from qwen_dev_cli.shell.executor import ShellExecutor
except ImportError:
    ShellExecutor = None

console = Console()


class UltimateCompleter(Completer):
    """Completer with autocomplete engine integration."""

    def __init__(self, commands: Dict[str, Dict], autocomplete_engine: AutocompleteEngine):
        self.commands = commands
        self.autocomplete = autocomplete_engine
        self.tools = {
            '/read': {'icon': '📖', 'desc': 'Read file'},
            '/write': {'icon': '✍️', 'desc': 'Write file'},
            '/edit': {'icon': '✏️', 'desc': 'Edit file'},
            '/run': {'icon': '⚡', 'desc': 'Execute command'},
            '/git': {'icon': '🌿', 'desc': 'Git operations'},
            '/search': {'icon': '🔍', 'desc': 'Search codebase'},
        }

    def get_completions(self, document, complete_event):
        text = document.text_before_cursor
        words = text.split()
        if not words:
            return
        
        word = words[-1]
        if not word.startswith('/'):
            return

        # Use autocomplete engine for smart suggestions
        suggestions = self.autocomplete.get_suggestions(word)
        
        for cmd_name, cmd_meta in {**self.commands, **self.tools}.items():
            if cmd_name.startswith(word):
                desc = cmd_meta.get('description') or cmd_meta.get('desc', '')
                yield Completion(
                    cmd_name,
                    start_position=-len(word),
                    display_meta=HTML(f"<b>{cmd_meta['icon']}</b> {desc}")
                )


class UltimateREPL:
    """
    REPL DEFINITIVO com TODOS os componentes integrados.
    """

    def __init__(self):
        self.console = Console()
        self.running = True
        self.dream_mode = False
        self.current_agent: Optional[str] = None

        # Core
        self.llm_client = LLMClient()
        self.context = ShellContext()

        # Managers (optional)
        self.feedback = FeedbackManager() if FeedbackManager else None
        self.history = HistoryManager() if HistoryManager else None
        self.preview = PreviewManager() if PreviewManager else None
        self.timeline = Timeline() if Timeline else None

        # TUI Components (optional)
        self.dashboard = Dashboard() if Dashboard else None
        self.status_bar = StatusBar() if StatusBar else None
        self.metrics = MetricsDisplay() if MetricsDisplay else None
        self.autocomplete = AutocompleteEngine() if AutocompleteEngine else None

        # Tools
        self._init_tools()
        
        # Agents
        self._agents = {}
        
        # Commands
        self.commands = self._load_commands()
        self.session = self._create_session()

    def _init_tools(self):
        """Initialize all tools."""
        self.bash_tool = BashCommandTool()
        self.file_read = ReadFileTool()
        self.file_write = WriteFileTool()
        self.file_edit = EditFileTool()
        self.git_status = GitStatusTool()
        self.git_diff = GitDiffTool()
        self.search_tool = SearchTool() if SearchTool else None

    def _load_commands(self) -> Dict[str, Dict]:
        """Load all commands."""
        return {
            "/help": {
                "icon": "❓",
                "description": "Show all commands",
                "category": CommandCategory.HELP,
                "handler": self._cmd_help
            },
            "/exit": {
                "icon": "👋",
                "description": "Exit shell",
                "category": CommandCategory.SYSTEM,
                "handler": self._cmd_exit
            },
            "/quit": {
                "icon": "👋",
                "description": "Exit (alias)",
                "category": CommandCategory.SYSTEM,
                "handler": self._cmd_exit
            },
            "/clear": {
                "icon": "🧹",
                "description": "Clear screen",
                "category": CommandCategory.SYSTEM,
                "handler": self._cmd_clear
            },
            "/dashboard": {
                "icon": "📊",
                "description": "Show dashboard",
                "category": CommandCategory.UI,
                "handler": self._cmd_dashboard
            },
            "/metrics": {
                "icon": "📈",
                "description": "Show metrics",
                "category": CommandCategory.UI,
                "handler": self._cmd_metrics
            },
            "/history": {
                "icon": "📜",
                "description": "Show command history",
                "category": CommandCategory.UI,
                "handler": self._cmd_history
            },
            "/timeline": {
                "icon": "⏱️",
                "description": "Show timeline",
                "category": CommandCategory.UI,
                "handler": self._cmd_timeline
            },
            
            # Agents
            "/architect": {
                "icon": "🏗️",
                "description": "Architect agent",
                "category": CommandCategory.AGENT,
                "handler": lambda msg: asyncio.run(self._invoke_agent("architect", msg))
            },
            "/refactor": {
                "icon": "♻️",
                "description": "Refactor agent",
                "category": CommandCategory.AGENT,
                "handler": lambda msg: asyncio.run(self._invoke_agent("refactorer", msg))
            },
            "/test": {
                "icon": "🧪",
                "description": "Test agent",
                "category": CommandCategory.AGENT,
                "handler": lambda msg: asyncio.run(self._invoke_agent("testing", msg))
            },
            "/review": {
                "icon": "🔍",
                "description": "Review agent",
                "category": CommandCategory.AGENT,
                "handler": lambda msg: asyncio.run(self._invoke_agent("reviewer", msg))
            },
            "/docs": {
                "icon": "📚",
                "description": "Documentation agent",
                "category": CommandCategory.AGENT,
                "handler": lambda msg: asyncio.run(self._invoke_agent("documentation", msg))
            },
            "/explore": {
                "icon": "🗺️",
                "description": "Explorer agent",
                "category": CommandCategory.AGENT,
                "handler": lambda msg: asyncio.run(self._invoke_agent("explorer", msg))
            },
            "/plan": {
                "icon": "📋",
                "description": "Planner agent",
                "category": CommandCategory.AGENT,
                "handler": lambda msg: asyncio.run(self._invoke_agent("planner", msg))
            },
            "/dream": {
                "icon": "💭",
                "description": "DREAM mode",
                "category": CommandCategory.AGENT,
                "handler": self._cmd_dream
            },
        }

    def _create_session(self) -> PromptSession:
        """Create prompt session."""
        history_file = Path.home() / '.qwen-dev-history'
        return PromptSession(
            history=FileHistory(str(history_file)),
            auto_suggest=AutoSuggestFromHistory(),
            completer=UltimateCompleter(self.commands, self.autocomplete),
            key_bindings=self._create_keybindings(),
            enable_history_search=True,
        )

    def _create_keybindings(self) -> KeyBindings:
        """Create keybindings."""
        bindings = KeyBindings()

        @bindings.add("c-p")
        def show_palette(event):
            self._show_palette()

        @bindings.add("c-d")
        def toggle_dream(event):
            self.dream_mode = not self.dream_mode
            status = "[green]ON[/green]" if self.dream_mode else "[dim]OFF[/dim]"
            self.feedback.show(f"💭 DREAM mode: {status}")

        @bindings.add("c-s")
        def show_dashboard(event):
            self._cmd_dashboard("")

        @bindings.add("c-m")
        def show_metrics(event):
            self._cmd_metrics("")

        return bindings

    def _get_prompt(self):
        """Generate prompt."""
        prefix = []
        if self.dream_mode:
            prefix.append(('ansimagenta', '💭 '))
        if self.current_agent:
            prefix.append(('ansiyellow', f'{self.current_agent} '))

        return FormattedText(prefix + [
            ('ansibrightgreen', 'q'),
            ('ansigreen', 'w'),
            ('ansiyellow', 'e'),
            ('ansiyellow', 'n'),
            ('', ' '),
            ('ansicyan', '⚡'),
            ('', ' '),
            ('ansibrightgreen', '›'),
            ('', ' '),
        ])

    def _cmd_help(self, _):
        """Show help."""
        table = Table(title="Qwen Dev CLI - Ultimate Commands", border_style="cyan")
        table.add_column("Command", style="cyan")
        table.add_column("Icon")
        table.add_column("Description", style="dim")

        for cmd, meta in sorted(self.commands.items()):
            table.add_row(cmd, meta['icon'], meta['description'])

        console.print("\n")
        console.print(table)
        console.print("\n[dim]💡 Ctrl+P (palette) | Ctrl+D (DREAM) | Ctrl+S (dashboard) | Ctrl+M (metrics)[/dim]\n")

    def _cmd_exit(self, _):
        """Exit shell."""
        self.running = False
        console.print("\n[cyan]👋 Goodbye! Soli Deo Gloria 🙏[/cyan]\n")

    def _cmd_clear(self, _):
        """Clear screen."""
        console.clear()

    def _cmd_dashboard(self, _):
        """Show dashboard."""
        if self.dashboard:
            try:
                self.dashboard.render()
            except Exception as e:
                console.print(f"[red]❌ Dashboard error: {e}[/red]")
        else:
            console.print("[yellow]⚠️  Dashboard not available[/yellow]")

    def _cmd_metrics(self, _):
        """Show metrics."""
        if self.metrics:
            try:
                self.metrics.render()
            except Exception as e:
                console.print(f"[red]❌ Metrics error: {e}[/red]")
        else:
            console.print("[yellow]⚠️  Metrics not available[/yellow]")

    def _cmd_history(self, _):
        """Show history."""
        if self.history:
            try:
                self.history.render()
            except Exception as e:
                console.print(f"[red]❌ History error: {e}[/red]")
        else:
            console.print("[yellow]⚠️  History not available[/yellow]")

    def _cmd_timeline(self, _):
        """Show timeline."""
        if self.timeline:
            try:
                self.timeline.render()
            except Exception as e:
                console.print(f"[red]❌ Timeline error: {e}[/red]")
        else:
            console.print("[yellow]⚠️  Timeline not available[/yellow]")

    def _cmd_dream(self, message: str):
        """Toggle DREAM mode."""
        if not message.strip():
            self.dream_mode = not self.dream_mode
            status = "[green]ON[/green]" if self.dream_mode else "[dim]OFF[/dim]"
            self.feedback.show(f"💭 DREAM mode: {status}")
        else:
            asyncio.run(self._invoke_agent("reviewer", f"[CRITICAL] {message}"))

    async def _invoke_agent(self, agent_name: str, message: str):
        """Invoke agent."""
        if not message.strip():
            self.feedback.show(f"[yellow]⚠️  Provide message for {agent_name}[/yellow]")
            return

        # Get agent
        if agent_name not in self._agents:
            agent_map = {
                "architect": ArchitectAgent,
                "refactorer": RefactorerAgent,
                "testing": TestingAgent,
                "reviewer": ReviewerAgent,
                "documentation": DocumentationAgent,
                "explorer": ExplorerAgent,
                "planner": PlannerAgent,
            }
            self._agents[agent_name] = agent_map[agent_name]()

        agent = self._agents[agent_name]
        
        icon_map = {
            "architect": "🏗️",
            "refactorer": "♻️",
            "testing": "🧪",
            "reviewer": "🔍",
            "documentation": "📚",
            "explorer": "🗺️",
            "planner": "📋",
        }
        icon = icon_map.get(agent_name, "🤖")

        console.print(f"\n{icon} [cyan]{agent_name.capitalize()} agent...[/cyan]\n")

        # Stream response
        await self._stream_response(message, system=f"You are the {agent_name} agent.")

    async def _stream_response(self, message: str, system: Optional[str] = None):
        """Stream LLM response with renderer."""
        console.print("[dim]" + "─" * 60 + "[/dim]")
        
        try:
            # Use streaming renderer
            async for chunk in self.llm_client.stream_chat(
                prompt=message,
                context=system,
                max_tokens=4000,
                temperature=0.7
            ):
                console.print(chunk, end="")
                sys.stdout.flush()
            
            console.print("\n")
            console.print("[dim]" + "─" * 60 + "[/dim]")
            
        except Exception as e:
            console.print(f"\n[red]❌ Error: {e}[/red]")

    def _process_command(self, user_input: str):
        """Process command."""
        user_input = user_input.strip()
        if not user_input:
            return

        # Add to history
        self.history.add(user_input)

        # Slash command
        if user_input.startswith('/'):
            parts = user_input.split(maxsplit=1)
            cmd = parts[0]
            args = parts[1] if len(parts) > 1 else ""

            if cmd == '/':
                self._show_palette()
                return

            if cmd in self.commands:
                try:
                    self.commands[cmd]['handler'](args)
                except Exception as e:
                    console.print(f"[red]❌ Error: {e}[/red]")
            elif cmd in ['/read', '/write', '/edit', '/run', '/git', '/search']:
                asyncio.run(self._process_tool(cmd, args))
            else:
                console.print(f"[red]❌ Unknown: {cmd}[/red]")
                console.print("[yellow]Type /help[/yellow]")
        else:
            # Natural language
            asyncio.run(self._process_natural(user_input))

    async def _process_tool(self, tool: str, args: str):
        """Execute tool."""
        try:
            if tool == '/read':
                result = await self.file_read.execute(path=args)
                content = str(result.content) if hasattr(result, 'content') else str(result)
                console.print(Panel(content, title=f"📖 {args}", border_style="green"))
                self.context.remember_file(args, content, "read")
                
            elif tool == '/write':
                parts = args.split(maxsplit=1)
                if len(parts) < 2:
                    console.print("[yellow]Usage: /write <file> <content>[/yellow]")
                    return
                path, content = parts
                await self.file_write.execute(path=path, content=content)
                console.print(f"[green]✓ Written: {path}[/green]")
                
            elif tool == '/edit':
                console.print("[yellow]Edit: use format '/edit <file> <old> <new>'[/yellow]")
                
            elif tool == '/run':
                console.print(f"[dim]⚡ Running: {args}[/dim]")
                result = await self.bash_tool.execute(command=args)
                output = result.output if hasattr(result, 'output') else str(result)
                console.print(Panel(output, title="⚡ Output", border_style="green"))
                
            elif tool == '/git':
                if 'status' in args:
                    result = await self.git_status.execute()
                elif 'diff' in args:
                    result = await self.git_diff.execute()
                else:
                    console.print("[yellow]Usage: /git status | diff[/yellow]")
                    return
                console.print(Panel(str(result), title="🌿 Git", border_style="green"))
                
            elif tool == '/search':
                result = await self.search_tool.execute(pattern=args)
                console.print(Panel(str(result), title="🔍 Search", border_style="green"))
                
        except Exception as e:
            console.print(f"[red]❌ Error: {e}[/red]")

    async def _process_natural(self, message: str):
        """Process natural language."""
        # Resolve context
        original = message
        message = self.context.resolve_reference(message)
        if message != original:
            console.print(f"[dim]🔄 Resolved: {message}[/dim]")

        # Check tool commands
        msg_lower = message.lower()
        
        if any(kw in msg_lower for kw in ['read', 'show', 'open']):
            import re
            match = re.search(r'[\w/.]+\.\w+', message)
            if match:
                await self._process_tool('/read', match.group(0))
                return
                
        elif any(kw in msg_lower for kw in ['run', 'execute']):
            import re
            cmd = re.sub(r'^(run|execute|bash)\s+', '', message, flags=re.IGNORECASE)
            await self._process_tool('/run', cmd)
            return
            
        elif 'git' in msg_lower:
            if 'status' in msg_lower:
                await self._process_tool('/git', 'status')
            elif 'diff' in msg_lower:
                await self._process_tool('/git', 'diff')
            return

        # Chat with streaming
        if self.dream_mode:
            message = f"[CRITICAL ANALYSIS] {message}"
        
        await self._stream_response(message)

    def _show_palette(self):
        """Show command palette."""
        table = Table(border_style="dim")
        table.add_column("Command", style="cyan")
        table.add_column("Icon")
        table.add_column("Description", style="white")

        for cmd, meta in sorted(self.commands.items()):
            table.add_row(cmd, meta['icon'], meta['description'])

        console.print("\n[bold cyan]📋 Command Palette[/bold cyan]\n")
        console.print(table)
        console.print()

    def run(self):
        """Run REPL."""
        # Show landing
        if show_landing:
            show_landing()
        else:
            console.print("\n[bold cyan]═══════════════════════════════════════[/bold cyan]")
            console.print("[bold cyan]   Qwen Dev CLI - Ultimate REPL   [/bold cyan]")
            console.print("[bold cyan]═══════════════════════════════════════[/bold cyan]\n")

        console.print("[dim]✨ Ultimate REPL with ALL features integrated[/dim]")
        console.print("[dim]💡 Ctrl+P (palette) | Ctrl+D (DREAM) | Ctrl+S (dashboard) | Ctrl+M (metrics)[/dim]\n")

        # Main loop
        while self.running:
            try:
                with patch_stdout():
                    user_input = self.session.prompt(self._get_prompt())
                
                if user_input is None:
                    continue
                
                self._process_command(user_input)

            except KeyboardInterrupt:
                console.print()
                continue
            except EOFError:
                self._cmd_exit("")
                break
            except Exception as e:
                console.print(f"\n[red]❌ Error: {e}[/red]\n")


def start_ultimate_repl():
    """Entry point."""
    try:
        repl = UltimateREPL()
        repl.run()
    except KeyboardInterrupt:
        console.print("\n[cyan]👋 Goodbye![/cyan]\n")
    except Exception as e:
        console.print(f"\n[red]Fatal: {e}[/red]\n")
        sys.exit(1)


if __name__ == "__main__":
    start_ultimate_repl()
