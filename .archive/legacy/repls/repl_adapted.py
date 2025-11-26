"""
Enhanced REPL adaptado para Qwen Dev CLI.

Features:
- Fuzzy command completion com preview
- Command palette (Ctrl+P)
- Atalhos de teclado para agentes
- Dashboard de agentes (Ctrl+A)
- Modo DREAM (Ctrl+D) - análise crítica
- Visual impressionante mas clean

Adaptado de MAX-CODE CLI
"""

from prompt_toolkit import PromptSession
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.formatted_text import HTML, FormattedText
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.history import FileHistory
import prompt_toolkit.enums
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.markdown import Markdown
from rich.syntax import Syntax
from typing import Dict, Callable, Optional, Tuple
import sys
import os
import time
from pathlib import Path

# Importar UI components (existentes no projeto)
from qwen_dev_cli.ui.command_palette import CommandCategory

# Importar Context Manager
from .shell_context import ShellContext

# Importar LLM client (usar o nosso)
from qwen_dev_cli.core.llm import LLMClient

# Importar tools (usar os nossos)
from qwen_dev_cli.tools.exec import BashCommandTool
from qwen_dev_cli.tools.file_ops import ReadFileTool, WriteFileTool
from qwen_dev_cli.tools.git_ops import GitStatusTool, GitDiffTool
from qwen_dev_cli.tools.web_search import WebSearchTool

# Importar agentes (usar os nossos)
from qwen_dev_cli.agents.architect import ArchitectAgent
from qwen_dev_cli.agents.documentation import DocumentationAgent
from qwen_dev_cli.agents.explorer import ExplorerAgent
from qwen_dev_cli.agents.planner import PlannerAgent
from qwen_dev_cli.agents.refactorer import RefactorerAgent
from qwen_dev_cli.agents.reviewer import ReviewerAgent
from qwen_dev_cli.agents.testing import TestingAgent

console = Console()


class EnhancedCompleter(Completer):
    """
    Completer com preview de comandos E ferramentas.
    """

    def __init__(self, commands: Dict[str, Dict]):
        self.commands = commands

        # Ferramentas principais
        self.tools = {
            '/read': {
                'icon': '📖',
                'description': 'Read file contents - Example: /read config.json'
            },
            '/write': {
                'icon': '✍️',
                'description': 'Write content to file - Example: /write test.txt "content"'
            },
            '/edit': {
                'icon': '✏️',
                'description': 'Edit file with changes'
            },
            '/search': {
                'icon': '🔍',
                'description': 'Search for pattern'
            },
            '/run': {
                'icon': '⚡',
                'description': 'Execute bash command'
            },
            '/bash': {
                'icon': '💻',
                'description': 'Run bash command'
            },
            '/git': {
                'icon': '🌿',
                'description': 'Git operations'
            },
        }

    def get_completions(self, document, complete_event):
        """Gerar completions com metadata"""
        text = document.text_before_cursor
        words = text.split()

        if not words:
            return

        word = words[-1]

        if not word.startswith('/'):
            return

        # Completar comandos do shell
        for cmd_name, cmd_meta in self.commands.items():
            if cmd_name.startswith(word):
                display_meta = HTML(
                    f"<b>{cmd_meta['icon']}</b> {cmd_meta['description']}"
                )

                yield Completion(
                    cmd_name,
                    start_position=-len(word),
                    display_meta=display_meta
                )

        # Completar ferramentas
        for tool_name, tool_meta in self.tools.items():
            if tool_name.startswith(word):
                display_meta = HTML(
                    f"<b>{tool_meta['icon']}</b> {tool_meta['description']}"
                )

                yield Completion(
                    tool_name,
                    start_position=-len(word),
                    display_meta=display_meta
                )


class EnhancedREPL:
    """
    REPL Enhanced com command palette, atalhos de agentes, e visual impressionante.
    """

    def __init__(self):
        self.console = Console()
        self.running = True

        # State
        self.current_agent: Optional[str] = None
        self.dream_mode: bool = False

        # LLM client
        self.llm_client = LLMClient()

        # Agent instances (lazy loading)
        self._agent_instances = {}

        # Shell Context
        self.context = ShellContext()

        # Executors
        self.bash_tool = BashCommandTool()
        self.file_read_tool = ReadFileTool()
        self.file_write_tool = WriteFileTool()
        self.git_status_tool = GitStatusTool()
        self.git_diff_tool = GitDiffTool()
        try:
            self.web_search = WebSearchTool()
        except Exception as e:
            logger.warning(f"WebSearchTool not available: {e}")
            self.web_search = None

        # Commands and session
        self.commands = self._load_commands()
        self.session = self._create_session()

    def _load_commands(self) -> Dict[str, Dict]:
        """Carregar TODOS comandos disponíveis."""
        commands = {
            # Comandos especiais
            "/help": {
                "icon": "❓",
                "description": "Show all available commands",
                "category": CommandCategory.HELP,
                "handler": self._cmd_help
            },
            "/exit": {
                "icon": "👋",
                "description": "Exit Qwen Dev CLI shell",
                "category": CommandCategory.SYSTEM,
                "handler": self._cmd_exit
            },
            "/quit": {
                "icon": "👋",
                "description": "Exit shell (alias)",
                "category": CommandCategory.SYSTEM,
                "handler": self._cmd_exit
            },
            "/clear": {
                "icon": "🧹",
                "description": "Clear screen",
                "category": CommandCategory.SYSTEM,
                "handler": self._cmd_clear
            },

            # Agentes
            "/architect": {
                "icon": "🏗️",
                "description": "Architect agent - system design",
                "category": CommandCategory.AGENT,
                "handler": lambda msg: self._invoke_agent("architect", msg)
            },
            "/refactor": {
                "icon": "♻️",
                "description": "Refactoring agent",
                "category": CommandCategory.AGENT,
                "handler": lambda msg: self._invoke_agent("refactorer", msg)
            },
            "/test": {
                "icon": "🧪",
                "description": "Test generation agent",
                "category": CommandCategory.AGENT,
                "handler": lambda msg: self._invoke_agent("testing", msg)
            },
            "/review": {
                "icon": "🔍",
                "description": "Code review agent",
                "category": CommandCategory.AGENT,
                "handler": lambda msg: self._invoke_agent("reviewer", msg)
            },
            "/docs": {
                "icon": "📚",
                "description": "Documentation agent",
                "category": CommandCategory.AGENT,
                "handler": lambda msg: self._invoke_agent("documentation", msg)
            },
            "/explore": {
                "icon": "🗺️",
                "description": "Codebase exploration agent",
                "category": CommandCategory.AGENT,
                "handler": lambda msg: self._invoke_agent("explorer", msg)
            },
            "/plan": {
                "icon": "📋",
                "description": "Planning agent",
                "category": CommandCategory.AGENT,
                "handler": lambda msg: self._invoke_agent("planner", msg)
            },

            # Modo DREAM
            "/dream": {
                "icon": "💭",
                "description": "DREAM Mode - Critical analysis",
                "category": CommandCategory.AGENT,
                "handler": self._cmd_dream
            },
        }

        return commands

    def _create_session(self) -> PromptSession:
        """Criar prompt session com todas features"""
        history_file = Path.home() / '.qwen-dev-history'

        return PromptSession(
            history=FileHistory(str(history_file)),
            auto_suggest=AutoSuggestFromHistory(),
            completer=EnhancedCompleter(self.commands),
            key_bindings=self._create_keybindings(),
            enable_history_search=True,
            vi_mode=False,
        )

    def _create_keybindings(self) -> KeyBindings:
        """Criar atalhos de teclado"""
        bindings = KeyBindings()

        @bindings.add("c-p")
        def show_palette(event):
            """Command Palette (Ctrl+P)"""
            console.print("\n[bold cyan]📋 Command Palette[/bold cyan]")
            console.print("[dim]Use: /help para ver comandos disponíveis[/dim]\n")

        @bindings.add("c-d")
        def toggle_dream(event):
            """Toggle DREAM mode (Ctrl+D)"""
            self.dream_mode = not self.dream_mode
            mode_status = "[green]enabled[/green]" if self.dream_mode else "[dim]disabled[/dim]"
            console.print(f"\n💭 DREAM mode {mode_status}\n")

        @bindings.add("c-q")
        def show_quick_help(event):
            """Quick Help (Ctrl+Q)"""
            from prompt_toolkit import print_formatted_text
            from prompt_toolkit.formatted_text import HTML

            print_formatted_text()
            print_formatted_text(HTML('<cyan><b>⚡ Quick Help - Keyboard Shortcuts</b></cyan>'))
            print_formatted_text()
            print_formatted_text(HTML('  <b>Ctrl+P</b>  Command Palette'))
            print_formatted_text(HTML('  <b>Ctrl+D</b>  Toggle DREAM Mode'))
            print_formatted_text(HTML('  <b>Ctrl+Q</b>  Quick Help'))
            print_formatted_text()
            print_formatted_text(HTML('  Type <b>/help</b> for full command list'))
            print_formatted_text()

        return bindings

    def _get_agent_instance(self, agent_name: str):
        """Get or create agent instance (lazy loading)."""
        if agent_name in self._agent_instances:
            return self._agent_instances[agent_name]

        agent_map = {
            "architect": ArchitectAgent,
            "refactorer": RefactorerAgent,
            "testing": TestingAgent,
            "reviewer": ReviewerAgent,
            "documentation": DocumentationAgent,
            "explorer": ExplorerAgent,
            "planner": PlannerAgent,
        }

        agent_class = agent_map.get(agent_name)
        if not agent_class:
            raise ValueError(f"Unknown agent: {agent_name}")

        agent = agent_class()
        self._agent_instances[agent_name] = agent
        return agent

    def _invoke_agent(self, agent_name: str, message: str):
        """Invocar agente especializado."""
        if not message.strip():
            console.print(f"\n[yellow]Please provide a message for the {agent_name} agent[/yellow]\n")
            return

        try:
            agent = self._get_agent_instance(agent_name)

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

            console.print(f"\n{icon} [cyan]Invoking {agent_name} agent...[/cyan]\n")

            # Process message through agent
            if hasattr(agent, 'process'):
                response = agent.process(message)
                if isinstance(response, str):
                    pass
                elif hasattr(response, 'text'):
                    response = response.text
                else:
                    response = str(response)
            elif hasattr(agent, 'run'):
                response = agent.run(message)
                if not isinstance(response, str):
                    response = str(response)
            else:
                # Fallback: use LLM client directly
                response = self.llm_client.query(message)

            # Display response
            self._display_response(response)
            console.print()

        except Exception as e:
            console.print(f"\n[red]Error invoking agent: {e}[/red]\n")

    def _display_response(self, response: str):
        """Display agent response with beautiful markdown rendering."""
        if not response:
            return

        # Check if looks like markdown
        has_markdown = any([
            '# ' in response or '## ' in response,
            '```' in response,
            '- ' in response or '* ' in response,
            '**' in response,
        ])

        if has_markdown:
            try:
                md = Markdown(response)
                console.print(md)
            except Exception:
                console.print(response)
        else:
            console.print(response)

    def _cmd_help(self, _):
        """Mostrar help de comandos"""
        table = Table(title="Qwen Dev CLI Commands", show_header=True, border_style="cyan")
        table.add_column("Command", style="cyan", no_wrap=True)
        table.add_column("Icon", justify="center")
        table.add_column("Description", style="dim")

        for cmd, meta in sorted(self.commands.items()):
            table.add_row(cmd, meta['icon'], meta['description'])

        console.print("\n")
        console.print(table)
        console.print("\n[dim]💡 Press Ctrl+Q for keyboard shortcuts[/dim]\n")

    def _cmd_exit(self, _):
        """Sair do shell"""
        self.running = False
        console.print("\n[cyan]👋 Goodbye![/cyan]\n")

    def _cmd_clear(self, _):
        """Limpar tela"""
        console.clear()

    def _cmd_dream(self, message: str):
        """DREAM Mode - Análise crítica."""
        console.print("\n[cyan bold]💭 DREAM Mode - Critical Analysis[/cyan bold]")
        console.print("[dim]Skeptical review and improvement proposals[/dim]\n")

        if not message.strip():
            self.dream_mode = not self.dream_mode
            mode_status = "[green]enabled[/green]" if self.dream_mode else "[dim]disabled[/dim]"
            console.print(f"💭 DREAM mode {mode_status}\n")
            return

        # Usar review agent em modo crítico
        critical_message = f"[DREAM MODE - CRITICAL ANALYSIS] {message}"
        self._invoke_agent("reviewer", critical_message)

    def _get_prompt(self):
        """Generate beautiful prompt."""
        # Mode indicators
        prefix_parts = []
        if self.dream_mode:
            prefix_parts.append(('ansimagenta', '💭 '))
        if self.current_agent:
            prefix_parts.append(('ansiyellow', f'{self.current_agent} '))

        # Main prompt
        prompt_parts = prefix_parts + [
            ('ansibrightgreen', 'q'),
            ('ansigreen', 'w'),
            ('ansiyellow', 'e'),
            ('ansiyellow', 'n'),
            ('', ' '),
            ('ansicyan', '⚡'),
            ('', ' '),
            ('ansibrightgreen', '›'),
            ('', ' '),
        ]

        return FormattedText(prompt_parts)

    def _process_command(self, user_input: str):
        """Processar comando ou natural language"""
        if not hasattr(self, '_recursion_depth'):
            self._recursion_depth = 0

        self._recursion_depth += 1

        if self._recursion_depth > 50:
            console.print("\n[red]❌ Recursion limit reached[/red]\n")
            self._recursion_depth = 0
            return

        try:
            user_input = user_input.strip()

            if not user_input:
                return

            # Comando especial
            if user_input.startswith('/'):
                parts = user_input.split(maxsplit=1)
                cmd = parts[0]
                args = parts[1] if len(parts) > 1 else ""

                if cmd == '/':
                    self._show_command_palette()
                    return

                if cmd in self.commands:
                    try:
                        handler = self.commands[cmd].get('handler')
                        if handler is None:
                            console.print(f"\n[red]❌ Command {cmd} has no handler[/red]\n")
                            return
                        handler(args)
                    except Exception as e:
                        console.print(f"\n[red]❌ Error executing {cmd}: {e}[/red]\n")

                elif cmd in ['/read', '/write', '/edit', '/search', '/run', '/bash']:
                    tool_command = cmd[1:].capitalize() + ' ' + args
                    self._process_natural(tool_command)

                else:
                    console.print(f"\n[red]❌ Unknown command: {cmd}[/red]")
                    console.print("[yellow]💡 Type /help for commands[/yellow]\n")

            # Natural language
            else:
                self._process_natural(user_input)

        finally:
            self._recursion_depth -= 1

    def _process_natural(self, message: str):
        """Processar natural language."""
        try:
            # Resolve context
            original_message = message
            message = self.context.resolve_reference(message)
            if message != original_message:
                console.print(f"[dim]🔄 Resolved: {message}[/dim]")

            # Detect tool commands
            message_lower = message.lower()

            # Tool detection
            if any(kw in message_lower for kw in ['read', 'open', 'show', 'cat']):
                self._execute_read(message)
            elif any(kw in message_lower for kw in ['write', 'create', 'save']):
                self._execute_write(message)
            elif any(kw in message_lower for kw in ['run', 'execute', 'bash']):
                self._execute_bash(message)
            elif any(kw in message_lower for kw in ['git status', 'git diff', 'git log']):
                self._execute_git(message)
            else:
                # Fallback: Chat mode
                self._chat_mode(message)

        except Exception as e:
            console.print(f"\n[red]❌ Error: {e}[/red]\n")

    def _execute_read(self, message: str):
        """Execute read command."""
        import re
        match = re.search(r'[\w/.]+\.\w+', message)
        if match:
            file_path = match.group(0)
            try:
                result = self.file_read_tool.execute(path=file_path)
                if result and hasattr(result, 'content'):
                    content = result.content
                else:
                    content = str(result)
                console.print(Panel(
                    content,
                    title=f"📖 {file_path}",
                    border_style="green"
                ))
                self.context.remember_file(file_path, content, "read")
            except Exception as e:
                console.print(f"[red]❌ Error reading file: {e}[/red]")
        else:
            console.print("[yellow]⚠️  No file path found[/yellow]")

    def _execute_write(self, message: str):
        """Execute write command."""
        console.print("[yellow]⚠️  Write command not fully implemented yet[/yellow]")

    def _execute_bash(self, message: str):
        """Execute bash command."""
        import re
        import asyncio
        command = re.sub(r'^(run|execute|bash)\s+', '', message, flags=re.IGNORECASE)
        try:
            # Run async tool in sync context
            result = asyncio.run(self.bash_tool.execute(command=command))
            output = result.output if hasattr(result, 'output') else str(result)
            console.print(Panel(
                output,
                title="⚡ Bash",
                border_style="green"
            ))
        except Exception as e:
            console.print(f"[red]❌ Error: {e}[/red]")

    def _execute_git(self, message: str):
        """Execute git command."""
        console.print("[yellow]⚠️  Git command not fully implemented yet[/yellow]")

    def _chat_mode(self, message: str):
        """Chat mode with LLM."""
        if self.dream_mode:
            message = f"[CRITICAL ANALYSIS] {message}"

        console.print()
        console.print("[dim]" + "─" * 60 + "[/dim]")
        console.print("[bold cyan]💭 Qwen Response[/bold cyan]")
        console.print()

        try:
            response = self.llm_client.query(message)
            self._display_response(response)
        except Exception as e:
            console.print(f"[red]❌ Error: {e}[/red]")

        console.print()
        console.print("[dim]" + "─" * 60 + "[/dim]")
        console.print()

    def _show_command_palette(self):
        """Show command list."""
        console.print("\n[bold cyan]📋 Available Commands[/bold cyan]\n")

        table = Table(show_header=False, border_style="dim")
        table.add_column("Command", style="cyan")
        table.add_column("Icon")
        table.add_column("Description", style="white")

        for cmd_name, cmd_meta in sorted(self.commands.items()):
            table.add_row(
                cmd_name,
                cmd_meta['icon'],
                cmd_meta['description']
            )

        console.print(table)
        console.print("\n[dim]Type any command to use it[/dim]\n")

    def run(self):
        """Run enhanced REPL"""
        # Welcome banner
        console.print("\n[bold cyan]═══════════════════════════════════════[/bold cyan]")
        console.print("[bold cyan]   Qwen Dev CLI - Enhanced REPL   [/bold cyan]")
        console.print("[bold cyan]═══════════════════════════════════════[/bold cyan]\n")

        console.print("[dim]✨ Shortcuts: Ctrl+P (commands) | Ctrl+D (DREAM) | Ctrl+Q (help)[/dim]")
        console.print()

        # Main loop
        while self.running:
            try:
                user_input = self.session.prompt(self._get_prompt())

                if user_input is None:
                    continue

                user_input = user_input.strip()
                self._process_command(user_input)

            except KeyboardInterrupt:
                console.print()
                continue

            except EOFError:
                self._cmd_exit("")
                break

            except Exception as e:
                console.print(f"\n[red]❌ Error: {e}[/red]\n")
                continue


def start_enhanced_repl():
    """Entry point para enhanced REPL"""
    try:
        repl = EnhancedREPL()
        repl.run()
    except KeyboardInterrupt:
        console.print("\n[cyan]👋 Goodbye![/cyan]\n")
    except Exception as e:
        console.print(f"\n[red]Fatal error: {e}[/red]\n")
        sys.exit(1)


if __name__ == "__main__":
    start_enhanced_repl()
