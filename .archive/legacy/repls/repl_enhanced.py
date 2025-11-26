"""
Enhanced REPL para MAX-CODE CLI.

Features:
- Fuzzy command completion com preview
- Command palette (Ctrl+P) usando ui/command_palette.py EXISTENTE
- Atalhos de teclado para agentes
- Dashboard de agentes (Ctrl+A)
- Modo DREAM (Ctrl+D) - análise crítica
- Visual impressionante mas clean

Soli Deo Gloria 🙏
"""

from prompt_toolkit import PromptSession
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.history import FileHistory
import prompt_toolkit.enums
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.markdown import Markdown
from typing import Dict, Callable, Optional, Tuple
import sys
from pathlib import Path

# Importar command palette EXISTENTE (não reimplementar!)
from ..ui.command_palette import CommandPalette, Command, CommandCategory
from ui.banner import print_banner
from ui.themes import ThemeManager
from ui.dashboard import Dashboard

# Importar cliente LLM unificado com fallback Gemini
from core.llm.unified_client import UnifiedLLMClient

# Importar EPL NLP Engine para intent recognition
from core.epl.nlp_engine import recognize_intent, IntentType
from core.epl.nlp_engine_enhanced import EnhancedNLPEngine, recognize_intent_enhanced

# Importar Tool System para execução de ferramentas
from core.tools.tool_selector import ToolSelector

# Importar Context Manager para manter estado entre comandos
from cli.shell_context import ShellContext

# Importar Bash Executor para execução de comandos
from core.tools.bash_executor import BashExecutor

# Importar Git Wrapper para operações git
from core.tools.git_tool import GitTool

# Importar Web Search Tool
from core.tools.web_search_tool import WebSearchTool

# Importar Web Fetch Tool
from core.tools.web_fetch_tool import WebFetchTool

# Importar Slash Command Loader
from core.commands.slash_loader import SlashCommandLoader

# Importar agentes existentes
from agents import (
    ArchitectAgent,
    CodeAgent,
    TestAgent,
    ReviewAgent,
    FixAgent,
    DocsAgent,
    ExploreAgent,
    PlanAgent
)

console = Console()


class EnhancedCompleter(Completer):
    """
    Completer com preview de comandos E ferramentas.
    Mostra descrição e exemplo de uso.

    Features:
    - /comandos (help, exit, clear, agents, config, etc)
    - /tools (read, write, edit, search, run, grep, glob)
    - Autocomplete inteligente com fuzzy matching
    """

    def __init__(self, commands: Dict[str, Dict], tool_selector=None):
        self.commands = commands
        self.tool_selector = tool_selector

        # Adicionar ferramentas principais ao autocomplete
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
                'description': 'Edit file with changes - Example: /edit config.json line 5 to "new value"'
            },
            '/search': {
                'icon': '🔍',
                'description': 'Search for pattern - Example: /search TODO in *.py'
            },
            '/grep': {
                'icon': '🔎',
                'description': 'Grep pattern in files - Example: /grep "import os" *.py'
            },
            '/run': {
                'icon': '⚡',
                'description': 'Execute bash command - Example: /run npm install'
            },
            '/bash': {
                'icon': '💻',
                'description': 'Run bash command - Example: /bash ls -la'
            },
            '/git': {
                'icon': '🌿',
                'description': 'Git operations - Example: /git status'
            },
            '/git-status': {
                'icon': '📍',
                'description': 'Show git status - Example: /git-status'
            },
            '/git-diff': {
                'icon': '🔀',
                'description': 'Show git diff - Example: /git-diff'
            },
            '/git-log': {
                'icon': '📜',
                'description': 'Show commit history - Example: /git-log'
            },
            '/git-branch': {
                'icon': '🌿',
                'description': 'List branches - Example: /git-branch'
            },
            '/search-web': {
                'icon': '🔍',
                'description': 'Search the web - Example: /search-web Python async'
            },
            '/web-search': {
                'icon': '🌐',
                'description': 'Search the web (alias) - Example: /web-search tutorials'
            },
            '/fetch': {
                'icon': '🌐',
                'description': 'Fetch URL content - Example: /fetch https://example.com'
            },
            '/web-fetch': {
                'icon': '📄',
                'description': 'Fetch URL (alias) - Example: /web-fetch https://docs.python.org'
            },
        }

    def get_completions(self, document, complete_event):
        """Gerar completions com metadata"""
        # 🔥 BORIS FIX: Use text_before_cursor and split to get current word
        text = document.text_before_cursor
        words = text.split()

        # Get the word being typed
        if not words:
            return

        word = words[-1]

        # Se não começar com /, não autocomplete
        if not word.startswith('/'):
            return

        # Completar comandos do shell
        for cmd_name, cmd_meta in self.commands.items():
            if cmd_name.startswith(word):
                # Criar completion com preview
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

    Integra com código EXISTENTE (não reimplementa):
    - ui/command_palette.py (completo, 436 linhas)
    - ui/banner.py (banner existente)
    - ui/themes.py (temas existentes)
    - ui/dashboard.py (dashboard existente)
    - agents/* (8 agentes implementados)
    """

    def __init__(self):
        self.console = Console()
        self.theme_manager = ThemeManager()
        self.dashboard = Dashboard()
        self.running = True

        # State
        self.current_agent: Optional[str] = None
        self.dream_mode: bool = False

        # Unified LLM client with Gemini as primary (prefer_claude=False)
        self.claude_client = UnifiedLLMClient(prefer_claude=False)

        # Agent instances (lazy loading)
        self._agent_instances = {}

        # Shell Context para manter estado entre comandos
        self.context = ShellContext()

        # Tool Selector para auto-select tools (Read, Write, Edit, Bash, etc)
        self.tool_selector = ToolSelector()
        
        # Enhanced NLP Engine para detecção avançada de comandos
        self.enhanced_nlp = EnhancedNLPEngine()
        
        # Command Executor perfeito (como Claude Code)
        from core.epl.command_executor import CommandExecutor
        self.command_executor = CommandExecutor()

        # Bash Executor para comandos shell diretos
        self.bash_executor = BashExecutor()

        # Git Tool para operações git
        self.git_tool = GitTool()

        # Web Search Tool
        self.web_search_tool = WebSearchTool(max_results=10)

        # Web Fetch Tool
        self.web_fetch_tool = WebFetchTool()

        # Slash Command Loader (custom commands from .claude/commands/*.md)
        self.slash_loader = SlashCommandLoader()
        self.slash_loader.load_commands()

        # Commands and session (need tool_selector to be initialized first)
        self.commands = self._load_commands()
        self.session = self._create_session()

        # Status bar for Constitutional AI monitoring
        from ui.status_bar import StatusBar
        self.status_bar = StatusBar(console=self.console)
        self.status_bar.update(
            git_branch=self._get_git_branch(),
            tokens_used=0
        )

    def _load_commands(self) -> Dict[str, Dict]:
        """
        Carregar TODOS comandos disponíveis.
        Inclui: agentes, especiais, SOFIA, DREAM, custom slash commands
        """
        commands = {
            # Comandos especiais
            "/help": {
                "icon": "❓",
                "description": "Show all available commands",
                "category": CommandCategory.HELP,
                "handler": self._cmd_help
            },
            "/tips": {
                "icon": "💡",
                "description": "Show helpful tips to discover features",
                "category": CommandCategory.HELP,
                "handler": self._cmd_tips
            },
            "/exit": {
                "icon": "👋",
                "description": "Exit MAX-CODE shell",
                "category": CommandCategory.SYSTEM,
                "handler": self._cmd_exit
            },
            "/quit": {
                "icon": "👋",
                "description": "Exit MAX-CODE shell (alias)",
                "category": CommandCategory.SYSTEM,
                "handler": self._cmd_exit
            },
            "/clear": {
                "icon": "🧹",
                "description": "Clear screen",
                "category": CommandCategory.SYSTEM,
                "handler": self._cmd_clear
            },
            "/undo": {
                "icon": "⏪",
                "description": "Undo last action",
                "category": CommandCategory.SYSTEM,
                "handler": self._cmd_undo
            },
            "/redo": {
                "icon": "⏩",
                "description": "Redo previously undone action",
                "category": CommandCategory.SYSTEM,
                "handler": self._cmd_redo
            },
            "/history": {
                "icon": "📜",
                "description": "Show recent action history",
                "category": CommandCategory.SYSTEM,
                "handler": self._cmd_history
            },

            # Agentes (8 total)
            "/sophia": {
                "icon": "👑",
                "description": "Sophia - The Architect (system design)",
                "category": CommandCategory.AGENT,
                "handler": lambda msg: self._invoke_agent("architect", msg)
            },
            "/code": {
                "icon": "💻",
                "description": "Code generation agent",
                "category": CommandCategory.AGENT,
                "handler": lambda msg: self._invoke_agent("code", msg)
            },
            "/test": {
                "icon": "🧪",
                "description": "Test generation agent",
                "category": CommandCategory.AGENT,
                "handler": lambda msg: self._invoke_agent("test", msg)
            },
            "/review": {
                "icon": "🔍",
                "description": "Code review agent",
                "category": CommandCategory.AGENT,
                "handler": lambda msg: self._invoke_agent("review", msg)
            },
            "/fix": {
                "icon": "🔧",
                "description": "Bug fixing agent",
                "category": CommandCategory.AGENT,
                "handler": lambda msg: self._invoke_agent("fix", msg)
            },
            "/docs": {
                "icon": "📚",
                "description": "Documentation agent",
                "category": CommandCategory.AGENT,
                "handler": lambda msg: self._invoke_agent("docs", msg)
            },
            "/explore": {
                "icon": "🗺️",
                "description": "Codebase exploration agent",
                "category": CommandCategory.AGENT,
                "handler": lambda msg: self._invoke_agent("explore", msg)
            },
            "/plan": {
                "icon": "📋",
                "description": "Planning agent",
                "category": CommandCategory.AGENT,
                "handler": lambda msg: self._invoke_agent("plan", msg)
            },

            # Modos especiais (SOFIA e DREAM)
            "/sofia-plan": {
                "icon": "🎯",
                "description": "SOFIA Plan Mode - Strategic planning",
                "category": CommandCategory.AGENT,
                "handler": self._cmd_sofia_plan
            },
            "/dream": {
                "icon": "💭",
                "description": "DREAM Mode - Critical analysis and improvements",
                "category": CommandCategory.AGENT,
                "handler": self._cmd_dream
            },

            # Dashboard e UI
            "/dashboard": {
                "icon": "📊",
                "description": "Show agent dashboard",
                "category": CommandCategory.UI,
                "handler": self._cmd_dashboard
            },
            "/theme": {
                "icon": "🎨",
                "description": "Change theme (neon, fire, ocean, matrix, cyberpunk)",
                "category": CommandCategory.UI,
                "handler": self._cmd_theme
            },
        }

        # Add custom slash commands dynamically
        self._register_custom_commands(commands)

        return commands

    def _register_custom_commands(self, commands: Dict[str, Dict]):
        """
        Register custom slash commands from .claude/commands/*.md files.

        Boris: "Custom commands are user intentions crystallized.
        Load them, render them, execute them beautifully."
        """
        for cmd_name, slash_cmd in self.slash_loader.commands.items():
            # Create command key with / prefix
            cmd_key = f"/{cmd_name}"

            # Create handler that renders template and sends to Claude
            def make_handler(command):
                def handler(args_string: str):
                    # Parse arguments
                    args_list = args_string.split() if args_string else []

                    # Build args dict from command args definition
                    args_dict = {}
                    for i, arg_name in enumerate(command.args):
                        if i < len(args_list):
                            args_dict[arg_name] = args_list[i]
                        else:
                            args_dict[arg_name] = ""

                    # Render prompt with arguments
                    rendered_prompt = self.slash_loader.render_command(command.name, args_dict)

                    if not rendered_prompt:
                        console.print(f"[red]❌ Failed to render command: {command.name}[/red]")
                        return

                    # Display custom command execution
                    console.print(f"\n[dim]🎯 Executing custom command: /{command.name}[/dim]")

                    # Send to Claude for processing
                    self._process_natural(rendered_prompt)

                return handler

            # Register command
            commands[cmd_key] = {
                "icon": "⚡",  # Custom commands get lightning bolt icon
                "description": slash_cmd.description,
                "category": CommandCategory.AGENT,  # Treat as agent-like commands
                "handler": make_handler(slash_cmd)
            }

        # Log custom commands loaded
        if self.slash_loader.commands:
            console.print(f"[dim]✨ Loaded {len(self.slash_loader.commands)} custom command(s)[/dim]")

    def _create_session(self) -> PromptSession:
        """Criar prompt session com todas features"""
        history_file = Path.home() / '.max-code-history'

        return PromptSession(
            history=FileHistory(str(history_file)),
            auto_suggest=AutoSuggestFromHistory(),
            completer=EnhancedCompleter(self.commands, self.tool_selector),
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

        @bindings.add("c-a")
        def show_agents(event):
            """Agent Dashboard (Ctrl+A)"""
            console.print("\n[bold cyan]🤖 Agent Dashboard[/bold cyan]")
            console.print("[dim]Use: /agents para ver status dos agentes[/dim]\n")

        @bindings.add("c-d")
        def toggle_dream(event):
            """Toggle DREAM mode (Ctrl+D)"""
            self.dream_mode = not self.dream_mode
            mode_status = "[green]enabled[/green]" if self.dream_mode else "[dim]disabled[/dim]"
            console.print(f"\n💭 DREAM mode {mode_status}\n")

        @bindings.add("c-s")
        def enter_sofia_plan(event):
            """SOFIA Plan Mode (Ctrl+S)"""
            # Não usar event.app.exit() - isso trava o shell
            # Ao invés disso, apenas mostrar mensagem e continuar
            console.print("\n[bold cyan]🎯 SOFIA Plan Mode[/bold cyan]")
            console.print("[dim]Digite seu plano na próxima linha ou use: /plan <seu plano>[/dim]\n")

        @bindings.add("c-r")
        def search_history(event):
            """Reverse History Search (Ctrl+R)"""
            # Trigger reverse-i-search (built-in to prompt_toolkit)
            event.app.vi_state.input_mode = prompt_toolkit.enums.InputMode.INCREMENTAL_SEARCH
            
        @bindings.add("c-q")
        def show_quick_help(event):
            """Quick Help (Ctrl+Q)"""
            # 🔥 BORIS FIX: Changed from Ctrl+H to Ctrl+Q
            # Reason: Backspace sends Ctrl+H in many terminals!
            from prompt_toolkit import print_formatted_text
            from prompt_toolkit.formatted_text import HTML

            print_formatted_text()
            print_formatted_text(HTML('<cyan><b>⚡ Quick Help - Keyboard Shortcuts</b></cyan>'))
            print_formatted_text()
            print_formatted_text(HTML('  <b>Ctrl+P</b>  Command Palette'))
            print_formatted_text(HTML('  <b>Ctrl+R</b>  Search History (reverse-i-search)'))
            print_formatted_text(HTML('  <b>Ctrl+S</b>  SOFIA Plan Mode'))
            print_formatted_text(HTML('  <b>Ctrl+D</b>  Toggle DREAM Mode (critical analysis)'))
            print_formatted_text(HTML('  <b>Ctrl+A</b>  Agent Dashboard'))
            print_formatted_text(HTML('  <b>Ctrl+Q</b>  Quick Help (this help)'))
            print_formatted_text()
            print_formatted_text(HTML('  Type <b>/help</b> for full command list'))
            print_formatted_text()

        return bindings

    def _show_command_palette(self):
        """
        Show command list (simplified - no palette UI conflicts with event loop).

        🔥 BORIS FIX: Simplified to avoid asyncio conflicts
        Original CommandPalette has event loop issues when called from keybindings.
        """
        from rich.table import Table

        console.print("\n[bold cyan]📋 Available Commands[/bold cyan]\n")

        # Group commands by category
        by_category = {}
        for cmd_name, cmd_meta in self.commands.items():
            cat = cmd_meta['category'].value
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append((cmd_name, cmd_meta))

        # Display by category
        for category, cmds in sorted(by_category.items()):
            table = Table(title=f"{category.upper()}", show_header=False, border_style="dim")
            table.add_column("Command", style="cyan")
            table.add_column("Icon")
            table.add_column("Description", style="white")

            for cmd_name, cmd_meta in sorted(cmds):
                table.add_row(
                    cmd_name,
                    cmd_meta['icon'],
                    cmd_meta['description']
                )

            console.print(table)
            console.print()

        console.print("[dim]Type any command to use it, or /help for more info[/dim]\n")

    def _get_agent_instance(self, agent_name: str):
        """
        Get or create agent instance (lazy loading).

        Args:
            agent_name: Nome do agente (architect, code, test, etc.)

        Returns:
            Agent instance
        """
        if agent_name in self._agent_instances:
            return self._agent_instances[agent_name]

        # Map agent names to classes
        agent_map = {
            "architect": ArchitectAgent,
            "code": CodeAgent,
            "test": TestAgent,
            "review": ReviewAgent,
            "fix": FixAgent,
            "docs": DocsAgent,
            "explore": ExploreAgent,
            "plan": PlanAgent,
        }

        agent_class = agent_map.get(agent_name)
        if not agent_class:
            raise ValueError(f"Unknown agent: {agent_name}")

        # Instantiate agent
        agent = agent_class()
        self._agent_instances[agent_name] = agent
        return agent

    def _invoke_agent(self, agent_name: str, message: str):
        """
        Invocar agente especializado.

        Args:
            agent_name: Nome do agente (architect, code, test, etc.)
            message: Mensagem para o agente
        """
        if not message.strip():
            console.print(f"\n[yellow]Please provide a message for the {agent_name} agent[/yellow]\n")
            return

        try:
            # Get agent instance
            agent = self._get_agent_instance(agent_name)

            # Mostrar feedback
            icon_map = {
                "architect": "👑",
                "code": "💻",
                "test": "🧪",
                "review": "🔍",
                "fix": "🔧",
                "docs": "📚",
                "explore": "🗺️",
                "plan": "📋",
            }
            icon = icon_map.get(agent_name, "🤖")

            # Update status bar - agent thinking
            self.status_bar.update(
                active_agent=f"{agent_name.capitalize()}Agent",
                agent_status="thinking"
            )

            console.print(f"\n{icon} [cyan]Invoking {agent_name} agent...[/cyan]\n")

            # Process message through agent
            # Note: Agents may have different interfaces, adapt as needed
            if hasattr(agent, 'process'):
                response = agent.process(message)
                # Se response é string, está OK
                if isinstance(response, str):
                    pass
                # Se response tem atributo text ou content, extrair
                elif hasattr(response, 'text'):
                    response = response.text
                elif hasattr(response, 'content'):
                    response = str(response.content)
                elif hasattr(response, 'output'):
                    if isinstance(response.output, dict):
                        response = response.output.get('code', response.output.get('docs', str(response.output)))
                    else:
                        response = str(response.output)
            elif hasattr(agent, 'run'):
                response = agent.run(message)
                if not isinstance(response, str):
                    response = str(response)
            elif hasattr(agent, 'execute'):
                # Agents que usam execute geralmente retornam AgentResult
                from sdk.base_agent import AgentTask
                task = AgentTask(
                    id=f"task_{agent_name}_{hash(message)}",
                    description=message,
                    parameters={}
                )
                result = agent.execute(task)
                if hasattr(result, 'output'):
                    if isinstance(result.output, dict):
                        response = result.output.get('code', result.output.get('docs', str(result.output)))
                    else:
                        response = str(result.output)
                else:
                    response = str(result)
            else:
                # Fallback: use Claude client directly with agent context
                system_prompt = f"You are the {agent_name} agent. Respond according to your specialization."
                response = self.claude_client.chat(message, system=system_prompt)

            # Update status bar - agent active/completed
            self.status_bar.update(
                agent_status="idle"
            )

            # Display response with beautiful markdown rendering
            self._display_response(response)
            console.print()

        except Exception as e:
            # Reset status bar on error
            self.status_bar.update(
                active_agent=None,
                agent_status="idle"
            )
            console.print(f"\n[red]Error invoking agent: {e}[/red]\n")

    def _display_response(self, response: str):
        """
        Display agent response with beautiful markdown rendering.

        Args:
            response: Raw response text from agent
        """
        if not response:
            return

        # Check if response looks like markdown (has headers, lists, code blocks)
        has_markdown = any([
            '# ' in response or '## ' in response or '### ' in response,  # Headers
            '```' in response,  # Code blocks
            '- ' in response or '* ' in response or '1. ' in response,    # Lists
            '**' in response or '__' in response,                         # Bold
            '`' in response,                                               # Inline code
        ])

        if has_markdown:
            # Render as markdown for beautiful formatting
            try:
                md = Markdown(response)
                console.print(md)
            except Exception:
                # Fallback to plain text if markdown parsing fails
                console.print(response)
        else:
            # Plain text response - just print directly
            console.print(response)

    def _cmd_help(self, _):
        """Mostrar help de comandos"""
        table = Table(title="MAX-CODE Commands", show_header=True, border_style="cyan")
        table.add_column("Command", style="cyan", no_wrap=True)
        table.add_column("Icon", justify="center")
        table.add_column("Description", style="dim")

        # Group by category
        categories = {}
        for cmd, meta in self.commands.items():
            cat = meta['category'].value
            if cat not in categories:
                categories[cat] = []
            categories[cat].append((cmd, meta))

        # Display by category
        for category, cmds in sorted(categories.items()):
            table.add_row(f"\n[bold]{category.upper()}[/bold]", "", "", style="bold")
            for cmd, meta in sorted(cmds):
                table.add_row(cmd, meta['icon'], meta['description'])

        console.print("\n")
        console.print(table)
        console.print("\n[dim]💡 Press Ctrl+P for command palette | Ctrl+A for agent dashboard | /tips for daily tip[/dim]\n")
    
    def _cmd_tips(self, args: str):
        """Show helpful tips"""
        from core.tips_system import get_tips_system
        
        tips = get_tips_system()
        
        # Parse args
        if args.strip().lower() == "random":
            tip = tips.get_random_tip(unseen_only=True)
        elif args.strip().lower() == "daily":
            tip = tips.get_tip_of_the_day()
        else:
            # Default: tip of the day
            tip = tips.get_tip_of_the_day()
        
        # Display tip
        console.print("\n")
        console.print(Panel(
            tips.format_tip(tip),
            border_style="cyan",
            title="[bold cyan]💡 Helpful Tip[/bold cyan]",
            subtitle="[dim]Type /tips random for another | /tips daily for today's tip[/dim]"
        ))
        console.print("\n")

    def _cmd_exit(self, _):
        """Sair do shell"""
        self.running = False
        console.print("\n[cyan]👋 Goodbye! Soli Deo Gloria 🙏[/cyan]\n")

    def _cmd_clear(self, _):
        """Limpar tela"""
        console.clear()
    
    def _cmd_undo(self, _):
        """Undo last action"""
        from core.action_history import get_action_history
        
        history = get_action_history()
        
        if not history.can_undo():
            console.print("\n[yellow]⚠️  Nothing to undo[/yellow]\n")
            return
        
        description = history.undo()
        if description:
            console.print(f"\n[green]⏪ Undone:[/green] {description}\n")
        else:
            console.print("\n[red]❌ Failed to undo[/red]\n")
    
    def _cmd_redo(self, _):
        """Redo previously undone action"""
        from core.action_history import get_action_history
        
        history = get_action_history()
        
        if not history.can_redo():
            console.print("\n[yellow]⚠️  Nothing to redo[/yellow]\n")
            return
        
        description = history.redo()
        if description:
            console.print(f"\n[green]⏩ Redone:[/green] {description}\n")
        else:
            console.print("\n[red]❌ Failed to redo[/red]\n")
    
    def _cmd_history(self, _):
        """Show recent action history"""
        from core.action_history import get_action_history
        
        history = get_action_history()
        recent = history.get_history(limit=10)
        
        if not recent:
            console.print("\n[dim]No actions in history yet[/dim]\n")
            return
        
        console.print("\n[bold cyan]📜 Recent Actions[/bold cyan]\n")
        
        for i, action in enumerate(reversed(recent)):
            marker = "→" if i == 0 and history.can_undo() else " "
            timestamp = action.timestamp.strftime("%H:%M:%S")
            console.print(f"  {marker} [{timestamp}] {action.description}")
        
        console.print(f"\n[dim]Can undo: {history.can_undo()} | Can redo: {history.can_redo()}[/dim]\n")

    def _cmd_sofia_plan(self, message: str):
        """
        SOFIA Plan Mode - Planejamento estratégico.
        Usa o agent architect em modo de planejamento.
        """
        console.print("\n[cyan bold]🎯 SOFIA Plan Mode[/cyan bold]")
        console.print("[dim]Strategic planning and architecture design[/dim]\n")

        if not message.strip():
            console.print("[yellow]Please provide a planning task[/yellow]\n")
            return

        # Invocar architect agent com contexto de planejamento
        plan_message = f"[PLAN MODE - STRATEGIC] {message}"
        self._invoke_agent("architect", plan_message)

    def _cmd_dream(self, message: str):
        """
        DREAM Mode - Análise crítica e propostas de melhoria.
        Agente cético que questiona e propõe melhorias.
        """
        console.print("\n[cyan bold]💭 DREAM Mode - Critical Analysis[/cyan bold]")
        console.print("[dim]Skeptical review and improvement proposals[/dim]\n")

        if not message.strip():
            # Se não há mensagem, apenas toggle o modo
            self.dream_mode = not self.dream_mode
            mode_status = "[green]enabled[/green]" if self.dream_mode else "[dim]disabled[/dim]"
            console.print(f"💭 DREAM mode {mode_status}\n")
            return

        # Usar review agent em modo crítico
        critical_message = f"[DREAM MODE - CRITICAL ANALYSIS] {message}"
        self._invoke_agent("review", critical_message)

    def _cmd_dashboard(self, _):
        """Mostrar dashboard de agentes"""
        try:
            # Usar dashboard existente
            self.dashboard.show()
        except Exception as e:
            # Fallback simples se dashboard não funcionar
            console.print("\n[cyan bold]📊 Agent Dashboard[/cyan bold]\n")

            table = Table(show_header=True, border_style="dim")
            table.add_column("Agent", style="cyan")
            table.add_column("Icon")
            table.add_column("Status")

            agents = [
                ("Sophia (Architect)", "👑", "Ready"),
                ("Code Generator", "💻", "Ready"),
                ("Test Generator", "🧪", "Ready"),
                ("Code Reviewer", "🔍", "Ready"),
                ("Bug Fixer", "🔧", "Ready"),
                ("Documentor", "📚", "Ready"),
                ("Explorer", "🗺️", "Ready"),
                ("Planner", "📋", "Ready"),
            ]

            for name, icon, status in agents:
                table.add_row(name, icon, f"[green]{status}[/green]")

            console.print(table)
            console.print("\n[dim]Press any key to continue...[/dim]\n")

    def _cmd_theme(self, theme_name: str):
        """Trocar tema"""
        if not theme_name.strip():
            console.print("\n[yellow]Available themes: neon, fire, ocean, matrix, cyberpunk[/yellow]\n")
            return

        try:
            self.theme_manager.set_theme(theme_name.strip())
            console.print(f"\n[green]✨ Theme changed to {theme_name}[/green]\n")
        except Exception as e:
            console.print(f"\n[red]Error changing theme: {e}[/red]\n")
            console.print("[yellow]Available themes: neon, fire, ocean, matrix, cyberpunk[/yellow]\n")

    def _get_git_branch(self) -> Optional[str]:
        """Get current git branch name."""
        try:
            import subprocess
            result = subprocess.run(
                ['git', 'branch', '--show-current'],
                capture_output=True,
                text=True,
                timeout=2
            )
            if result.returncode == 0:
                return result.stdout.strip() or None
        except Exception:
            pass
        return None

    def _get_prompt(self):
        """
        Generate beautiful prompt with MAXIMUS neon colors.

        🔥 BORIS FIX: Simplified to use basic ANSI colors (no hex)
        Fixes prompt_toolkit backspace bug and None returns.
        """
        from prompt_toolkit.formatted_text import FormattedText

        # Mode indicators
        prefix_parts = []
        if self.dream_mode:
            prefix_parts.append(('ansimagenta', '💭 '))
        if self.current_agent:
            prefix_parts.append(('ansiyellow', f'{self.current_agent} '))

        # Main prompt with ANSI colors (more stable than hex)
        # Green → Yellow gradient using ANSI
        prompt_parts = prefix_parts + [
            ('ansibrightgreen', 'm'),
            ('ansibrightgreen', 'a'),
            ('ansigreen', 'x'),
            ('ansiyellow', 'i'),
            ('ansiyellow', 'm'),
            ('ansibrightyellow', 'u'),
            ('ansiyellow', 's'),
            ('', ' '),
            ('ansicyan', '⚡'),
            ('', ' '),
            ('ansibrightgreen', '›'),
            ('', ' '),
        ]

        return FormattedText(prompt_parts)

    def _process_command(self, user_input: str):
        """Processar comando ou natural language"""
        # 🔥 PHASE 0.1 FIX: Recursion limit protection (Steve Jobs Suite 1.3)
        # Anthropic Pattern: Rule-based validation at entry point
        if not hasattr(self, '_recursion_depth'):
            self._recursion_depth = 0

        self._recursion_depth += 1

        # Max 50 recursive calls (prevents stack overflow)
        if self._recursion_depth > 50:
            console.print("\n[red]❌ Recursion limit reached (50 calls)[/red]")
            console.print("[yellow]⚠️  Possible infinite loop detected[/yellow]\n")
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

                # ✨ BORIS FIX: `/` alone triggers Command Palette (like Claude Code)
                if cmd == '/' or cmd == '':
                    self._show_command_palette()
                    return

                # Verificar se é comando do shell (help, exit, etc)
                if cmd in self.commands:
                    # 🔥 BRUTAL FIX: Handle exceptions in command handlers
                    try:
                        handler = self.commands[cmd].get('handler')
                        if handler is None:
                            console.print(f"\n[red]❌ Command {cmd} has no handler[/red]\n")
                            return

                        handler(args)

                    except Exception as e:
                        console.print(f"\n[red]❌ Error executing {cmd}: {e}[/red]\n")
                        import traceback
                        if hasattr(self, 'debug') and self.debug:
                            console.print(f"[dim]{traceback.format_exc()}[/dim]")

                # Verificar se é comando de ferramenta (/read, /write, etc)
                elif cmd in ['/read', '/write', '/edit', '/search', '/grep', '/run', '/bash']:
                    # Remover o / e processar como natural language
                    tool_command = cmd[1:].capitalize() + ' ' + args
                    self._process_natural(tool_command)

                else:
                    console.print(f"\n[red]❌ Unknown command: {cmd}[/red]")
                    console.print("[yellow]💡 Type /help or press Ctrl+P for commands[/yellow]")
                    console.print("[yellow]💡 Tools: /read, /write, /edit, /search, /grep, /run[/yellow]\n")

            # Natural language
            else:
                self._process_natural(user_input)

        finally:
            # 🔥 PHASE 0.1 FIX: Always decrement recursion counter
            self._recursion_depth -= 1

    def _process_natural(self, message: str):
        """
        Processar natural language com NLP Engine + Tool System.

        Flow:
        1. Resolve context references (that file, it, etc)
        2. NLP Intent Recognition (EPL)
        3. Router: Tool execution vs Agent vs Chat
        4. Update context
        """
        try:
            # STEP 0: Resolve context references
            original_message = message
            message = self.context.resolve_reference(message)
            if message != original_message:
                console.print(f"[dim]🔄 Resolved: {message}[/dim]")

            # STEP 1.5: Verificar se é comando de execução/navegação (PRIORIDADE MÁXIMA)
            # Usar Command Executor perfeito (como Claude Code)
            # Detectar comandos de execução ANTES de qualquer análise
            
            # Verificar se parece com comando de execução (não apenas chat)
            looks_like_command = any([
                'acesse' in message.lower(),
                'navegue' in message.lower(),
                'navega' in message.lower(),
                'vá' in message.lower(),
                'vai' in message.lower(),
                'go to' in message.lower(),
                'navigate' in message.lower(),
                'execute' in message.lower(),
                'rode' in message.lower(),
                'lista' in message.lower(),
                'mostra' in message.lower(),
                'existe' in message.lower(),
                'tem' in message.lower(),
                'há' in message.lower(),
                'e me' in message.lower(),
                'e me fala' in message.lower(),
                'and' in message.lower() and ('tell' in message.lower() or 'show' in message.lower() or 'check' in message.lower()),
                # Comandos de criação/escrita de arquivo
                'cria' in message.lower() and ('arquivo' in message.lower() or 'file' in message.lower() or '.html' in message.lower() or '.py' in message.lower() or '.js' in message.lower()),
                'create' in message.lower() and ('file' in message.lower() or '.html' in message.lower()),
                'salve' in message.lower() or 'save' in message.lower(),
                'escreva' in message.lower() or 'write' in message.lower(),
            ])
            
            if looks_like_command:
                # Usar Command Executor perfeito (sem mensagens desnecessárias)
                result = self.command_executor.execute(message)
                
                if result['success']:
                    # Mostrar apenas o output, sem explicações
                    if result['output']:
                        console.print(result['output'])
                else:
                    console.print(f"[red]❌ {result['output']}[/red]")
                return
            
            # STEP 1: Detect intent using Enhanced NLP Engine (para outros casos)
            intent = self.enhanced_nlp.recognize_intent(message)
            
            execution_result = self.enhanced_nlp.detect_execution_intent(message)
            is_execution = execution_result[0] if execution_result else False
            
            if is_execution:
                # Usar Command Executor perfeito
                result = self.command_executor.execute(message)
                
                if result['success']:
                    if result['output']:
                        console.print(result['output'])
                else:
                    console.print(f"[red]❌ {result['output']}[/red]")
                return

            # STEP 2: Route based on message keywords (tool detection)
            message_lower = message.lower()

            # Detect tool commands by keywords (expandido)
            tool_keywords = {
                'read': ['read', 'open', 'show', 'cat', 'display', 'mostra', 'mostrar', 'veja', 'ver'],
                'write': ['write', 'create', 'save', 'criar', 'salvar'],
                'edit': ['edit', 'change', 'modify', 'replace', 'update', 'editar', 'alterar', 'modificar'],
                'search': ['find', 'search', 'grep', 'look for', 'buscar', 'procurar'],
                'run': ['run', 'execute', 'exec', 'bash', 'rode', 'roda', 'executa', 'execute'],
                'git': ['git status', 'git diff', 'git log', 'git branch', 'git commit', 'git push', 'git pull', 'git-'],
                'web-search': ['search-web', 'web-search', 'search web', 'google', 'duckduckgo'],
                'web-fetch': ['fetch', 'web-fetch', '/fetch', '/web-fetch', 'get url', 'download page']
            }

            detected_tool = None
            for tool, keywords in tool_keywords.items():
                if any(kw in message_lower for kw in keywords):
                    detected_tool = tool
                    break

            if detected_tool:
                # Direct tool execution (como Claude Code)
                self._execute_tool_command(message, detected_tool)

            elif intent.type in [IntentType.CODE, IntentType.FIX, IntentType.TEST,
                                IntentType.REVIEW, IntentType.DOCS, IntentType.PLAN]:
                # ANTES de chamar agente, verificar se é comando de criação de arquivo
                # Comandos de criação devem ser executados diretamente, não via agente
                is_file_creation = any([
                    'cria' in message.lower() and ('arquivo' in message.lower() or 'file' in message.lower() or '.html' in message.lower() or '.py' in message.lower()),
                    'create' in message.lower() and ('file' in message.lower() or '.html' in message.lower()),
                    'salve' in message.lower() or 'save' in message.lower(),
                    'escreva' in message.lower() and ('arquivo' in message.lower() or 'file' in message.lower()),
                ])
                
                if is_file_creation:
                    # Executar diretamente via Command Executor
                    result = self.command_executor.execute(message)
                    if result['success']:
                        if result['output']:
                            console.print(result['output'])
                    else:
                        console.print(f"[red]❌ {result['output']}[/red]")
                    return
                
                # Route para agente especializado (apenas se não for criação de arquivo)
                agent_map = {
                    IntentType.CODE: "code",
                    IntentType.FIX: "fix",
                    IntentType.TEST: "test",
                    IntentType.REVIEW: "review",
                    IntentType.DOCS: "docs",
                    IntentType.PLAN: "plan"
                }
                agent_name = agent_map.get(intent.type, "code")
                self._invoke_agent(agent_name, message)
            
            elif intent.type == IntentType.ANALYZE:
                # Análise - pode ser navegação + análise
                self._execute_analysis_command(message, intent.target)
            
            elif intent.type == IntentType.EXPLORE:
                # Exploração - pode ser navegação
                if intent.target:
                    self._execute_navigation_or_analysis(message, "navigate", intent.target)
                else:
                    # Fallback para explore agent
                    self._invoke_agent("explore", message)

            else:
                # Fallback: Chat mode com Claude
                self._chat_mode(message)

        except Exception as e:
            console.print(f"\n[red]❌ Error: {e}[/red]\n")

    def _execute_tool_command(self, message: str, detected_tool: str):
        """Execute tool command using ToolSelector (auto-selects correct tool)"""
        try:
            # Special handling for bash commands (direct execution)
            if detected_tool == 'run':
                console.print("[dim]⚡ Executing bash command...[/dim]")

                # Extract command (remove "run" keyword)
                import re
                command = re.sub(r'^(run|execute|bash)\s+', '', message, flags=re.IGNORECASE)

                # Execute using BashExecutor
                result = self.bash_executor.execute(command)

                # Display result
                tool_result = {
                    "status": result.type,  # "success" or "error"
                    "tool": "bash",
                    "output": result.content[0].text if result.content else None,
                    "error": result.content[0].text if result.type == "error" else None
                }
                self._display_tool_result(tool_result)
                return

            # Special handling for git commands (Boris Technique)
            if detected_tool in ['git', 'git-status', 'git-diff', 'git-log', 'git-branch', 'git-commit', 'git-push', 'git-pull']:
                console.print("[dim]🌿 Executing git operation...[/dim]")

                import re

                # Parse git command
                # Examples:
                # "git status" -> status()
                # "git diff config.py" -> diff(file_path="config.py")
                # "git log --oneline" -> log(oneline=True)
                # "git commit -m 'message'" -> commit(message="message")

                # Extract git operation
                git_match = re.search(r'git[\s-]+(status|diff|log|branch|commit|push|pull)', message, re.IGNORECASE)

                if git_match:
                    operation = git_match.group(1).lower()

                    # Execute git operation
                    if operation == 'status':
                        verbose = '--verbose' in message.lower() or '-v' in message.lower()
                        result = self.git_tool.status(verbose=verbose)

                    elif operation == 'diff':
                        # Extract file path if specified
                        file_match = re.search(r'diff\s+([^\s]+)', message, re.IGNORECASE)
                        file_path = file_match.group(1) if file_match else None
                        staged = '--cached' in message.lower() or '--staged' in message.lower()
                        result = self.git_tool.diff(file_path=file_path, staged=staged)

                    elif operation == 'log':
                        oneline = '--oneline' in message.lower()
                        # Extract limit if specified (default 10)
                        limit_match = re.search(r'-n\s+(\d+)', message)
                        limit = int(limit_match.group(1)) if limit_match else 10
                        result = self.git_tool.log(limit=limit, oneline=oneline)

                    elif operation == 'branch':
                        list_all = '-a' in message.lower() or '--all' in message.lower()
                        result = self.git_tool.branch(list_all=list_all)

                    elif operation == 'commit':
                        # Extract commit message
                        msg_match = re.search(r'-m\s+["\']([^"\']+)["\']', message)
                        if msg_match:
                            commit_message = msg_match.group(1)
                            add_all = '-a' in message.lower() or '--all' in message.lower()
                            result = self.git_tool.commit(message=commit_message, add_all=add_all)
                        else:
                            result = ToolResult.error("❌ Commit message required. Use: git commit -m 'message'")

                    elif operation == 'push':
                        result = self.git_tool.push()

                    elif operation == 'pull':
                        result = self.git_tool.pull()

                    else:
                        result = ToolResult.error(f"❌ Git operation '{operation}' not supported yet")

                    # Display result
                    tool_result = {
                        "status": result.type,
                        "tool": f"git-{operation}",
                        "output": result.content[0].text if result.content else None,
                        "error": result.content[0].text if result.type == "error" else None
                    }
                    self._display_tool_result(tool_result)
                    return
                else:
                    # Fallback to bash executor for unknown git commands
                    result = self.bash_executor.execute(message)
                    tool_result = {
                        "status": result.type,
                        "tool": "git",
                        "output": result.content[0].text if result.content else None,
                        "error": result.content[0].text if result.type == "error" else None
                    }
                    self._display_tool_result(tool_result)
                    return

            # Special handling for web search (Boris Technique)
            if detected_tool == 'web-search':
                console.print("[dim]🔍 Searching the web...[/dim]")

                import re

                # Extract search query (remove trigger keywords)
                query = message
                for keyword in ['search-web', 'web-search', 'search web', 'google', 'duckduckgo', '/search-web', '/web-search']:
                    query = re.sub(r'\b' + re.escape(keyword) + r'\b', '', query, flags=re.IGNORECASE)
                query = query.strip()

                if not query:
                    result = ToolResult.error("❌ Please provide a search query\n\nExample: search-web Python async tutorial")
                else:
                    # Execute web search
                    result = self.web_search_tool.search(query)

                # Display result
                tool_result = {
                    "status": result.type,
                    "tool": "web-search",
                    "output": result.content[0].text if result.content else None,
                    "error": result.content[0].text if result.type == "error" else None
                }
                self._display_tool_result(tool_result)
                return

            # Special handling for web fetch (Boris Technique)
            if detected_tool == 'web-fetch':
                console.print("[dim]🌐 Fetching URL...[/dim]")

                import re

                # Extract URL (remove keywords)
                url = message
                for kw in ['fetch', 'web-fetch', '/fetch', '/web-fetch', 'get url', 'download page']:
                    url = re.sub(r'\b' + re.escape(kw) + r'\b', '', url, flags=re.IGNORECASE)
                url = url.strip()

                if not url or not url.startswith('http'):
                    result = ToolResult.error("❌ Please provide a valid URL\n\nExample: fetch https://example.com")
                else:
                    result = self.web_fetch_tool.fetch(url)

                tool_result = {
                    "status": result.type,
                    "tool": "web-fetch",
                    "output": result.content[0].text if result.content else None,
                    "error": result.content[0].text if result.type == "error" else None
                }
                self._display_tool_result(tool_result)
                return

            # Regular tool selection
            console.print("[dim]🔧 Selecting tool...[/dim]")

            # Usa ToolSelector.select_and_execute - ELE faz TUDO
            # (seleciona tool certa baseado na descrição e executa)
            result = self.tool_selector.select_and_execute(
                task_description=message,
                parameters={}  # ToolSelector extrai params do message
            )

            # Update context if file operation
            if "file" in message.lower() and result.status == "success":
                # Extract file path from message (simple regex)
                import re
                match = re.search(r'[\w/.]+\.\w+', message)
                if match:
                    file_path = match.group(0)
                    self.context.remember_file(file_path, None, detected_tool)

            # Display result
            tool_result = {
                "status": result.status,
                "tool": result.tool_name if hasattr(result, 'tool_name') else detected_tool,
                "output": str(result.content) if result.status == "success" else None,
                "error": result.error if result.status == "error" else None
            }
            self._display_tool_result(tool_result)

        except Exception as e:
            console.print(f"[red]❌ Tool execution failed: {e}[/red]\n")
            import traceback
            console.print(f"[dim]{traceback.format_exc()}[/dim]")

    def _execute_navigation_or_analysis(self, message: str, action_type: str, target: Optional[str], secondary_action: Optional[str] = None):
        """
        Executa comandos de navegação ou análise detectados via NLP.
        
        Args:
            message: Mensagem original do usuário
            action_type: Tipo de ação (navigate, analyze, execute)
            target: Caminho ou comando extraído
            secondary_action: Ação secundária em comandos compostos
        """
        import os
        from pathlib import Path
        
        try:
            if action_type == "navigate" and target:
                # Navegar para diretório
                # Expandir ~
                if target.startswith('~'):
                    target = os.path.expanduser(target)
                
                # Verificar se existe
                path = Path(target)
                if path.exists():
                    if path.is_dir():
                        # Mudar diretório
                        os.chdir(str(path))
                        
                        # Se tem ação secundária, processar ela
                        if secondary_action:
                            self._process_secondary_action(secondary_action, str(path))
                        else:
                            # Sem ação secundária, apenas navegar (silencioso)
                            pass
                    else:
                        # É arquivo, ler conteúdo
                        from core.tools.file_reader import FileReader
                        reader = FileReader()
                        result = reader.read(str(path))
                        if result.status == "success":
                            self._display_tool_result({
                                "status": "success",
                                "tool": "file_reader",
                                "output": result.content[0].text if result.content else ""
                            })
                else:
                    console.print(f"[red]❌ Caminho não encontrado: {target}[/red]")
            
            elif action_type == "analyze" and target:
                # Análise de diretório/projeto
                console.print(f"[dim]🔍 Analisando: {target}[/dim]")
                
                # Expandir ~
                if target.startswith('~'):
                    target = os.path.expanduser(target)
                
                path = Path(target)
                if path.exists():
                    # Mudar para o diretório
                    if path.is_dir():
                        os.chdir(str(path))
                    else:
                        os.chdir(str(path.parent))
                    
                    # Executar análise
                    self._execute_analysis_command(message, str(path))
                else:
                    console.print(f"[red]❌ Caminho não encontrado: {target}[/red]")
            
            elif action_type == "execute" and target:
                # Executar comando extraído
                result = self.bash_executor.execute(target)
                self._display_tool_result({
                    "status": result.type,
                    "tool": "bash",
                    "output": result.content[0].text if result.content else None,
                    "error": result.content[0].text if result.type == "error" else None
                })
            else:
                # Tentar análise genérica
                self._execute_analysis_command(message, target)
                
        except Exception as e:
            console.print(f"[red]❌ Erro ao executar: {e}[/red]")
            import traceback
            console.print(f"[dim]{traceback.format_exc()}[/dim]")
    
    def _process_secondary_action(self, action_text: str, current_path: str):
        """
        Processa ação secundária em comandos compostos.
        
        Exemplos:
        - "me fala se existe uma subpasta chamada vcli-go"
        - "lista os arquivos"
        - "mostra o README"
        """
        import os
        from pathlib import Path
        import re
        
        action_lower = action_text.lower()
        
        # Verificar se é pergunta sobre existência
        existence_patterns = [
            r'(?:existe|tem|há|have|has)\s+(?:uma|um|a|an)?\s*(?:subpasta|pasta|diretorio|diretorio|folder|directory|arquivo|file)\s+(?:chamada|nomeada|named|called)?\s*["\']?([^"\']+)["\']?',
            r'(?:existe|tem|há|have|has)\s+["\']?([^"\']+)["\']?\s+(?:subpasta|pasta|diretorio|diretorio|folder|directory|arquivo|file)',
        ]
        
        for pattern in existence_patterns:
            match = re.search(pattern, action_lower, re.IGNORECASE)
            if match:
                item_name = match.group(1).strip()
                item_path = Path(current_path) / item_name
                
                if item_path.exists():
                    item_type = "diretório" if item_path.is_dir() else "arquivo"
                    console.print(f"[green]✓ Sim[/green], existe {item_type} chamado '{item_name}'")
                else:
                    console.print(f"[yellow]✗ Não[/yellow], não existe '{item_name}' neste diretório")
                return
        
        # Verificar se é pergunta sobre listar
        if any(word in action_lower for word in ["lista", "list", "mostra", "show", "arquivos", "files"]):
            result = self.bash_executor.execute("ls -la")
            if result.type == "success" and result.content:
                console.print(result.content[0].text)
            return
        
        # Verificar se é pergunta sobre ler arquivo específico
        read_patterns = [
            r'(?:mostra|show|leia|read|exiba|display)\s+(?:o|a|the)?\s*["\']?([^"\']+)["\']?',
            r'(?:conteudo|content|conteúdo)\s+(?:do|of|de)?\s*["\']?([^"\']+)["\']?',
        ]
        
        for pattern in read_patterns:
            match = re.search(pattern, action_lower, re.IGNORECASE)
            if match:
                file_name = match.group(1).strip()
                file_path = Path(current_path) / file_name
                
                if file_path.exists() and file_path.is_file():
                    from core.tools.file_reader import FileReader
                    reader = FileReader()
                    result = reader.read(str(file_path))
                    if result.status == "success" and result.content:
                        self._display_tool_result({
                            "status": "success",
                            "tool": "file_reader",
                            "output": result.content[0].text if result.content else ""
                        })
                else:
                    console.print(f"[yellow]✗ Arquivo não encontrado: {file_name}[/yellow]")
                return
        
        # Se não reconheceu, tentar análise genérica
        self._execute_analysis_command(action_text, current_path)
    
    def _execute_analysis_command(self, message: str, target: Optional[str]):
        """
        Executa análise de projeto/diretório.
        
        Args:
            message: Mensagem original
            target: Caminho alvo (opcional)
        """
        import os
        from pathlib import Path
        
        try:
            # Se tem target, usar; senão, usar diretório atual
            if target:
                if target.startswith('~'):
                    target = os.path.expanduser(target)
                path = Path(target)
                if path.exists():
                    if path.is_dir():
                        os.chdir(str(path))
                    else:
                        os.chdir(str(path.parent))
            
            current_dir = os.getcwd()
            console.print(f"[cyan]📊 Analisando projeto em: {current_dir}[/cyan]\n")
            
            # 1. Listar estrutura
            console.print("[bold]📁 Estrutura do projeto:[/bold]")
            result = self.bash_executor.execute("find . -maxdepth 2 -type f -name '*.py' -o -name '*.js' -o -name '*.json' -o -name '*.md' -o -name '*.txt' | head -20")
            if result.type == "success" and result.content:
                console.print(result.content[0].text)
            
            # 2. Verificar README
            readme_files = ["README.md", "README.txt", "README", "readme.md"]
            for readme in readme_files:
                readme_path = Path(current_dir) / readme
                if readme_path.exists():
                    console.print(f"\n[bold]📄 {readme}:[/bold]")
                    from core.tools.file_reader import FileReader
                    reader = FileReader()
                    result = reader.read(str(readme_path))
                    if result.status == "success" and result.content:
                        # Mostrar primeiras 30 linhas
                        all_lines = result.content[0].text.split('\n')
                        lines = all_lines[:30]
                        console.print('\n'.join(lines))
                        if len(all_lines) > 30:
                            remaining = len(all_lines) - 30
                            console.print(f"\n[dim]... ({remaining} linhas restantes)[/dim]")
                    break
            
            # 3. Verificar arquivos de configuração
            config_files = {
                "package.json": "Node.js/JavaScript",
                "requirements.txt": "Python",
                "Pipfile": "Python (Pipenv)",
                "pom.xml": "Java (Maven)",
                "build.gradle": "Java (Gradle)",
                "go.mod": "Go",
                "Cargo.toml": "Rust",
                "composer.json": "PHP",
            }
            
            console.print("\n[bold]⚙️ Tecnologias detectadas:[/bold]")
            for config_file, tech in config_files.items():
                config_path = Path(current_dir) / config_file
                if config_path.exists():
                    console.print(f"  [green]✓[/green] {tech} ({config_file})")
            
            # 4. Resumo
            console.print(f"\n[green]✓[/green] Análise concluída para: {current_dir}")
            
        except Exception as e:
            console.print(f"[red]❌ Erro na análise: {e}[/red]")
            import traceback
            console.print(f"[dim]{traceback.format_exc()}[/dim]")
    
    def _chat_mode(self, message: str):
        """
        Fallback: Chat direto com Claude API (Boris Streaming Technique).

        Philosophy:
        "Streaming creates the illusion of speed and keeps users engaged.
        The first word appearing in <200ms makes the system feel instant,
        even if the full response takes 10 seconds."
        """
        # Aplicar DREAM mode se ativo
        if self.dream_mode:
            system_prompt = "You are in DREAM mode - provide critical analysis, identify potential issues, and suggest improvements. Be constructively skeptical."
            message = f"[CRITICAL ANALYSIS] {message}"
        else:
            system_prompt = None

        # Beautiful streaming header (Boris style) with provider info
        active_provider = self.claude_client.get_active_provider()
        provider_emoji = "💭" if active_provider == "Claude" else "🔮"
        provider_label = "Claude Sonnet 4.5" if active_provider == "Claude" else "Gemini 2.5 Flash"

        console.print()
        console.print("[dim]" + "─" * 60 + "[/dim]")
        console.print(f"[bold cyan]{provider_emoji} {provider_label}[/bold cyan]")
        if active_provider == "Gemini":
            console.print("[yellow]⚡ Using Gemini fallback (Claude unavailable)[/yellow]")
        else:
            console.print("[dim]⚡ Streaming response...[/dim]")
        console.print()

        # Stream response with real-time display
        response_parts = []
        word_count = 0

        # 🔥 BORIS FIX: No try/except needed - UnifiedLLMClient handles fallback internally
        # Errors only surface if ALL providers fail (logged silently in unified_client)
        for chunk in self.claude_client.chat(message, stream=True, system=system_prompt):
            console.print(chunk, end="", style="white")
            response_parts.append(chunk)
            word_count += len(chunk.split())

            # Flush periodically for smooth streaming
            if word_count % 5 == 0:
                console.file.flush()

        # Footer
        console.print("\n")
        console.print("[dim]" + "─" * 60 + "[/dim]")
        console.print(f"[dim]✓ {word_count} words streamed[/dim]\n")

    def _display_tool_result(self, result, stream: bool = True):
        """
        Pretty print tool execution result with streaming (Boris Technique).

        Philosophy:
        "Output should appear instantly for small results, and stream
        gracefully for large results. The user should never wonder if
        the system is frozen."

        Args:
            result: Tool result dict
            stream: Enable streaming for large outputs (>500 chars)
        """
        import time
        from rich.syntax import Syntax

        output_text = result.get("output", "✅ Done")
        tool_name = result.get('tool', 'Tool')
        status = result.get("status")
        file_path = result.get("file_path", None)  # For syntax detection

        if status == "success":
            # Stream large outputs (Boris Technique: create sense of speed)
            if stream and output_text and len(output_text) > 500:
                # Show header immediately
                console.print()
                console.print(f"[bold green]✅ {tool_name}[/bold green]")
                console.print("[dim]" + "─" * 60 + "[/dim]")
                console.print()

                # Stream output word by word (feels fast but readable)
                words = output_text.split()
                for i, word in enumerate(words):
                    console.print(word, end=" ")

                    # Smart delay: faster for code, slower for prose
                    if word.endswith((':', ';', '{', '}', '(', ')')):
                        time.sleep(0.002)  # Very fast for code
                    elif word.endswith(('.', '!', '?')):
                        time.sleep(0.01)   # Slight pause at sentences
                    else:
                        time.sleep(0.005)  # Normal speed

                    # Flush every 10 words for smooth display
                    if i % 10 == 0:
                        console.file.flush()

                console.print()
                console.print()
                console.print("[dim]" + "─" * 60 + "[/dim]")
                console.print("[green]✓ Complete[/green]\n")
            else:
                # Show small outputs immediately with syntax highlighting if applicable
                display_content = self._apply_syntax_highlighting(
                    output_text,
                    file_path,
                    tool_name
                )

                console.print(Panel(
                    display_content,
                    title=f"✅ {tool_name}",
                    border_style="green"
                ))
        else:
            # Errors: always show immediately (no streaming)
            console.print(Panel(
                result.get("error", "Unknown error"),
                title=f"❌ {tool_name} Failed",
                border_style="red"
            ))
            console.print("[yellow]💡 Tip: Check command syntax or file permissions[/yellow]\n")

    def _apply_syntax_highlighting(self, content: str, file_path: Optional[str], tool_name: str):
        """
        Apply syntax highlighting to code output (Boris Technique).

        Philosophy:
        "Syntax highlighting isn't decoration - it's cognitive optimization.
        The right colors can reduce comprehension time by 40%."

        Args:
            content: Text content to display
            file_path: Optional file path for language detection
            tool_name: Tool name for context

        Returns:
            Rich Syntax object or plain string
        """
        from rich.syntax import Syntax
        from pathlib import Path

        # Only apply to file read operations or code-like content
        if tool_name not in ['read', 'FileReader', 'bash', 'file_reader']:
            return content

        # Detect language from file path
        language = "text"
        if file_path:
            ext = Path(file_path).suffix.lstrip('.')
            language_map = {
                'py': 'python',
                'js': 'javascript',
                'ts': 'typescript',
                'tsx': 'typescript',
                'jsx': 'javascript',
                'json': 'json',
                'yaml': 'yaml',
                'yml': 'yaml',
                'toml': 'toml',
                'md': 'markdown',
                'sh': 'bash',
                'bash': 'bash',
                'zsh': 'bash',
                'sql': 'sql',
                'html': 'html',
                'css': 'css',
                'rs': 'rust',
                'go': 'go',
                'java': 'java',
                'c': 'c',
                'cpp': 'cpp',
                'h': 'c',
                'hpp': 'cpp',
            }
            language = language_map.get(ext, "text")

        # Apply syntax highlighting if language detected
        if language != "text":
            try:
                return Syntax(
                    content,
                    language,
                    theme="monokai",
                    line_numbers=False,  # Already in output
                    word_wrap=True
                )
            except Exception:
                # Fallback to plain text if highlighting fails
                return content

        return content

    def run(self):
        """Run enhanced REPL with magnificent visuals"""
        # Welcome banner
        print_banner()

        console.print("[dim]✨ Shortcuts: Ctrl+P (palette) | Ctrl+S (SOFIA plan) | Ctrl+D (DREAM) | Ctrl+Q (help)[/dim]")
        console.print()

        # Display initial status bar
        console.print("[dim]Status:[/dim]")
        self.status_bar.render()
        console.print()

        # Main loop
        while self.running:
            try:
                user_input = self.session.prompt(
                    self._get_prompt()
                )

                # 🔥 BORIS FIX: Protect against None from prompt_toolkit
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
        
        # Show tip of the day on startup (first-time experience)
        from core.tips_system import get_tips_system
        tips = get_tips_system()
        
        # Only show if less than 5 tips seen (new users)
        if len(tips.seen_tips) < 5:
            tip = tips.get_tip_of_the_day()
            console.print("\n")
            console.print(Panel(
                tips.format_tip(tip),
                border_style="yellow",
                title="[bold yellow]💡 Daily Tip[/bold yellow]",
                subtitle="[dim]Type /tips for more helpful tips anytime[/dim]"
            ))
            console.print("\n")
        
        repl.run()
    except KeyboardInterrupt:
        console.print("\n[cyan]👋 Goodbye![/cyan]\n")
    except Exception as e:
        console.print(f"\n[red]Fatal error: {e}[/red]\n")
        sys.exit(1)
