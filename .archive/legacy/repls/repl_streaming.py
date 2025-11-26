"""
Enhanced REPL com STREAMING REAL (como GitHub Copilot CLI).

Features:
- Streaming responses (char-by-char rendering)
- Tool execution com feedback imediato
- Command palette
- Context memory
- Agents integration

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
from rich.markdown import Markdown
from rich.live import Live
from rich.text import Text
from typing import Dict, Optional
import sys
from pathlib import Path

# UI Components
from qwen_dev_cli.ui.command_palette import CommandCategory

# Context Manager
from .shell_context import ShellContext

# LLM Client (com streaming)
from qwen_dev_cli.core.llm import LLMClient

# Tools
from qwen_dev_cli.tools.exec import BashCommandTool
from qwen_dev_cli.tools.file_ops import ReadFileTool, WriteFileTool
from qwen_dev_cli.tools.git_ops import GitStatusTool, GitDiffTool

# Agents
from qwen_dev_cli.agents.architect import ArchitectAgent
from qwen_dev_cli.agents.documentation import DocumentationAgent
from qwen_dev_cli.agents.explorer import ExplorerAgent
from qwen_dev_cli.agents.planner import PlannerAgent
from qwen_dev_cli.agents.refactorer import RefactorerAgent
from qwen_dev_cli.agents.reviewer import ReviewerAgent
from qwen_dev_cli.agents.testing import TestingAgent

console = Console()


class EnhancedCompleter(Completer):
    """Completer com preview."""

    def __init__(self, commands: Dict[str, Dict]):
        self.commands = commands
        self.tools = {
            '/read': {'icon': '📖', 'description': 'Read file'},
            '/write': {'icon': '✍️', 'description': 'Write file'},
            '/run': {'icon': '⚡', 'description': 'Execute command'},
            '/git': {'icon': '🌿', 'description': 'Git operations'},
        }

    def get_completions(self, document, complete_event):
        text = document.text_before_cursor
        words = text.split()
        if not words:
            return
        word = words[-1]
        if not word.startswith('/'):
            return

        for cmd_name, cmd_meta in {**self.commands, **self.tools}.items():
            if cmd_name.startswith(word):
                yield Completion(
                    cmd_name,
                    start_position=-len(word),
                    display_meta=HTML(f"<b>{cmd_meta['icon']}</b> {cmd_meta['description']}")
                )


class StreamingREPL:
    """REPL com streaming real como GitHub Copilot CLI."""

    def __init__(self):
        self.console = Console()
        self.running = True
        self.dream_mode = False
        self.current_agent: Optional[str] = None

        # LLM Client (async)
        self.llm_client = LLMClient()

        # Context
        self.context = ShellContext()

        # Tools
        self.bash_tool = BashCommandTool()
        self.file_read = ReadFileTool()
        self.file_write = WriteFileTool()
        self.git_status = GitStatusTool()
        self.git_diff = GitDiffTool()

        # Agents (lazy load)
        self._agents = {}

        # Commands
        self.commands = self._load_commands()
        self.session = self._create_session()

    def _load_commands(self) -> Dict[str, Dict]:
        """Carregar comandos."""
        return {
            "/help": {
                "icon": "❓",
                "description": "Show commands",
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
        """Criar prompt session."""
        history_file = Path.home() / '.qwen-dev-history'
        return PromptSession(
            history=FileHistory(str(history_file)),
            auto_suggest=AutoSuggestFromHistory(),
            completer=EnhancedCompleter(self.commands),
            key_bindings=self._create_keybindings(),
            enable_history_search=True,
        )

    def _create_keybindings(self) -> KeyBindings:
        """Criar atalhos de teclado."""
        bindings = KeyBindings()

        @bindings.add("c-p")
        def show_palette(event):
            console.print("\n[bold cyan]📋 Command Palette[/bold cyan]")
            console.print("[dim]Type /help to see all commands[/dim]\n")

        @bindings.add("c-d")
        def toggle_dream(event):
            self.dream_mode = not self.dream_mode
            status = "[green]ON[/green]" if self.dream_mode else "[dim]OFF[/dim]"
            console.print(f"\n💭 DREAM mode: {status}\n")

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
        table = Table(title="Qwen Dev CLI Commands", border_style="cyan")
        table.add_column("Command", style="cyan")
        table.add_column("Icon")
        table.add_column("Description", style="dim")

        for cmd, meta in sorted(self.commands.items()):
            table.add_row(cmd, meta['icon'], meta['description'])

        console.print("\n")
        console.print(table)
        console.print("\n[dim]💡 Ctrl+P for palette | Ctrl+D for DREAM mode[/dim]\n")

    def _cmd_exit(self, _):
        """Exit shell."""
        self.running = False
        console.print("\n[cyan]👋 Goodbye![/cyan]\n")

    def _cmd_clear(self, _):
        """Clear screen."""
        console.clear()

    def _cmd_dream(self, message: str):
        """Toggle DREAM mode."""
        if not message.strip():
            self.dream_mode = not self.dream_mode
            status = "[green]ON[/green]" if self.dream_mode else "[dim]OFF[/dim]"
            console.print(f"\n💭 DREAM mode: {status}\n")
        else:
            asyncio.run(self._invoke_agent("reviewer", f"[CRITICAL] {message}"))

    async def _invoke_agent(self, agent_name: str, message: str):
        """Invoke agent (async)."""
        if not message.strip():
            console.print(f"[yellow]⚠️  Provide message for {agent_name}[/yellow]")
            return

        # Get agent instance
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
        await self._stream_llm_response(message, system=f"You are the {agent_name} agent.")

    async def _stream_llm_response(self, message: str, system: Optional[str] = None):
        """Stream LLM response char-by-char (como GitHub Copilot CLI)."""
        console.print("[dim]" + "─" * 60 + "[/dim]")
        
        buffer = []
        char_count = 0
        
        try:
            # Stream chat (usando API correta: prompt + context)
            async for chunk in self.llm_client.stream_chat(
                prompt=message,
                context=system,
                max_tokens=4000,
                temperature=0.7
            ):
                # Print chunk immediately
                console.print(chunk, end="")
                buffer.append(chunk)
                char_count += len(chunk)
                
                # Flush every 10 chars for smooth streaming
                if char_count % 10 == 0:
                    sys.stdout.flush()
            
            console.print("\n")
            console.print("[dim]" + "─" * 60 + "[/dim]")
            
        except Exception as e:
            console.print(f"\n[red]❌ Error: {e}[/red]")

    def _process_command(self, user_input: str):
        """Process command or query."""
        user_input = user_input.strip()
        if not user_input:
            return

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
            elif cmd in ['/read', '/write', '/run', '/git']:
                asyncio.run(self._process_tool(cmd, args))
            else:
                console.print(f"[red]❌ Unknown: {cmd}[/red]")
                console.print("[yellow]Type /help for commands[/yellow]")
        else:
            # Natural language query
            asyncio.run(self._process_natural(user_input))

    async def _process_tool(self, tool: str, args: str):
        """Execute tool command."""
        try:
            if tool == '/read':
                result = await self.file_read.execute(path=args)
                console.print(Panel(
                    str(result.content) if hasattr(result, 'content') else str(result),
                    title=f"📖 {args}",
                    border_style="green"
                ))
                self.context.remember_file(args, str(result), "read")
                
            elif tool == '/write':
                parts = args.split(maxsplit=1)
                if len(parts) < 2:
                    console.print("[yellow]Usage: /write <file> <content>[/yellow]")
                    return
                path, content = parts
                result = await self.file_write.execute(path=path, content=content)
                console.print(f"[green]✓ Written to {path}[/green]")
                
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
                
        except Exception as e:
            console.print(f"[red]❌ Error: {e}[/red]")

    async def _process_natural(self, message: str):
        """Process natural language with streaming."""
        # Resolve context
        original = message
        message = self.context.resolve_reference(message)
        if message != original:
            console.print(f"[dim]🔄 Resolved: {message}[/dim]")

        # Check if tool command
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

        # Chat mode with streaming
        if self.dream_mode:
            message = f"[CRITICAL ANALYSIS] {message}"
        
        await self._stream_llm_response(message)

    def _show_palette(self):
        """Show command palette."""
        table = Table(border_style="dim")
        table.add_column("Command", style="cyan")
        table.add_column("Icon")
        table.add_column("Description", style="white")

        for cmd, meta in sorted(self.commands.items()):
            table.add_row(cmd, meta['icon'], meta['description'])

        console.print("\n[bold cyan]📋 Commands[/bold cyan]\n")
        console.print(table)
        console.print()

    def run(self):
        """Run REPL."""
        # Banner
        console.print("\n[bold cyan]═══════════════════════════════════════[/bold cyan]")
        console.print("[bold cyan]   Qwen Dev CLI - Streaming REPL   [/bold cyan]")
        console.print("[bold cyan]═══════════════════════════════════════[/bold cyan]\n")
        console.print("[dim]✨ Ctrl+P (palette) | Ctrl+D (DREAM) | /help (commands)[/dim]\n")

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


def start_streaming_repl():
    """Entry point."""
    try:
        repl = StreamingREPL()
        repl.run()
    except KeyboardInterrupt:
        console.print("\n[cyan]👋 Goodbye![/cyan]\n")
    except Exception as e:
        console.print(f"\n[red]Fatal: {e}[/red]\n")
        sys.exit(1)


if __name__ == "__main__":
    start_streaming_repl()
