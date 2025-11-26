"""
REPL MASTERPIECE - A DIVINE CODING EXPERIENCE 🎨

"Perfeição não é quando não há nada a adicionar,
mas quando não há nada a remover." - Antoine de Saint-Exupéry

Features:
- Streaming que parece mágica ✨
- Feedback imediato e satisfatório 🎯
- Comandos que FUNCIONAM na primeira vez 💪
- Visual que inspira criatividade 🌈
- Performance que impressiona ⚡

Soli Deo Gloria 🙏
"""

import asyncio
import os
import warnings

# Silence ALL warnings (gRPC, absl, etc)
os.environ['GRPC_VERBOSITY'] = 'ERROR'
os.environ['GLOG_minloglevel'] = '3'  # 3 = FATAL only
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
warnings.filterwarnings('ignore')
import sys
import io
# Redirect stderr temporarily during imports to suppress gRPC warnings
_original_stderr = sys.stderr
sys.stderr = io.StringIO()

from prompt_toolkit import PromptSession
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.formatted_text import HTML, FormattedText
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.history import FileHistory
from prompt_toolkit.patch_stdout import patch_stdout
from prompt_toolkit.styles import Style
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.markdown import Markdown
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.live import Live
from rich.text import Text
from rich.syntax import Syntax
from typing import Dict, Optional, List
import time
from pathlib import Path

# Restore stderr after imports
sys.stderr = _original_stderr

# Core
from .shell_context import ShellContext
from .intent_detector import IntentDetector
from qwen_dev_cli.core.llm import LLMClient
from qwen_dev_cli.ui.command_palette import CommandCategory

# Phase 2: Integration Coordinator
from qwen_dev_cli.core.integration_coordinator import Coordinator
from qwen_dev_cli.core.integration_types import EventType

# Setup clean logging
from qwen_dev_cli.core.logging_setup import setup_logging
setup_logging()

# Tools
from qwen_dev_cli.tools.exec import BashCommandTool
from qwen_dev_cli.tools.file_ops import ReadFileTool, WriteFileTool, EditFileTool
from qwen_dev_cli.tools.git_ops import GitStatusTool, GitDiffTool

# Agents (ALL SQUAD)
from qwen_dev_cli.agents.architect import ArchitectAgent
from qwen_dev_cli.agents.documentation import DocumentationAgent
from qwen_dev_cli.agents.explorer import ExplorerAgent
from qwen_dev_cli.agents.planner import PlannerAgent
from qwen_dev_cli.agents.refactorer import RefactorerAgent
from qwen_dev_cli.agents.reviewer import ReviewerAgent
from qwen_dev_cli.agents.refactorer import RefactorerAgent
from qwen_dev_cli.agents.testing import TestingAgent
from qwen_dev_cli.agents.performance import PerformanceAgent
from qwen_dev_cli.agents.security import SecurityAgent

# TUI Components (já implementados!)
from qwen_dev_cli.tui.animations import LoadingAnimation, Animator
from qwen_dev_cli.tui.components.enhanced_progress import TokenMetrics
from qwen_dev_cli.streaming.renderer import ReactiveRenderer
from qwen_dev_cli.tui.minimal_output import MinimalOutput, StreamingMinimal

console = Console()


class SmartCompleter(Completer):
    """Completer FUZZY com dropdown estilo VSCode."""

    def __init__(self, commands: Dict[str, Dict]):
        self.commands = commands
        self.tools = {
            '/read': {'icon': '📖', 'desc': 'Read file', 'example': '/read config.json'},
            '/write': {'icon': '✍️', 'desc': 'Write file', 'example': '/write test.txt "hello"'},
            '/edit': {'icon': '✏️', 'desc': 'Edit file', 'example': '/edit file.py'},
            '/run': {'icon': '⚡', 'desc': 'Execute', 'example': '/run ls -la'},
            '/git': {'icon': '🌿', 'desc': 'Git ops', 'example': '/git status'},
        }

    def _fuzzy_match(self, pattern: str, text: str) -> int:
        """
        Fuzzy matching score (higher is better).
        Returns score or 0 if no match.
        """
        pattern = pattern.lower()
        text = text.lower()
        
        # Exact prefix match (highest priority)
        if text.startswith(pattern):
            return 1000 + len(pattern)
        
        # Contains match
        if pattern in text:
            return 500 + len(pattern)
        
        # Fuzzy match (all chars present in order)
        score = 0
        pattern_idx = 0
        
        for i, char in enumerate(text):
            if pattern_idx < len(pattern) and char == pattern[pattern_idx]:
                score += (100 - i)  # Earlier matches score higher
                pattern_idx += 1
        
        # All chars matched?
        if pattern_idx == len(pattern):
            return score
        
        return 0

    def get_completions(self, document, complete_event):
        text = document.text_before_cursor
        words = text.split()
        if not words:
            return
        
        word = words[-1]
        if not word.startswith('/'):
            return

        # Remove leading '/'
        query = word[1:].lower()
        all_items = {**self.commands, **self.tools}
        
        # Score all commands
        matches = []
        for cmd_name, cmd_meta in all_items.items():
            cmd_key = cmd_name[1:]  # Remove '/'
            score = self._fuzzy_match(query, cmd_key)
            
            if score > 0:
                desc = cmd_meta.get('description') or cmd_meta.get('desc', '')
                example = cmd_meta.get('example', '')
                
                # Rich display with icon and description
                display_text = f"{cmd_meta['icon']} {cmd_name:14} {desc}"
                if example:
                    display_text += f" • [dim]{example}[/dim]"
                
                matches.append((score, cmd_name, display_text))
        
        # Sort by score (descending)
        matches.sort(reverse=True, key=lambda x: x[0])
        
        # Yield top 10 matches
        for score, cmd_name, display_text in matches[:10]:
            yield Completion(
                cmd_name,
                start_position=-len(word),
                display=display_text,
                display_meta=HTML(f"<ansicyan>score: {score}</ansicyan>")
            )


class MasterpieceREPL:
    """
    REPL OBRA-PRIMA - Experiência divina de coding.
    """

    def __init__(self):
        self.console = Console()
        self.running = True
        self.dream_mode = False
        self.current_agent: Optional[str] = None
        
        # State
        self.command_count = 0
        self.session_start = time.time()

        # Core
        self.llm_client = LLMClient()
        self.context = ShellContext()
        self.intent_detector = IntentDetector()
        
        # PHASE 2: Integration Coordinator (Central Nervous System)
        self.coordinator = Coordinator(cwd=os.getcwd())
        
        # Register agents (Phase 2.2)
        self._register_agents()
        
        console.print("[dim]✨ Integration coordinator initialized[/dim]")
        
        # TUI enhancements ✨ (já implementados!)
        try:
            self.loading_animation = LoadingAnimation(style="dots", speed=0.08)
            self.animator = Animator()
            self.token_metrics = TokenMetrics()
            self.minimal_output = MinimalOutput()
        except Exception:
            # Fallback if TUI not available
            self.loading_animation = None
            self.animator = None
            self.token_metrics = None
            self.minimal_output = None
        
        # Output settings (Nov 2025 best practices)
        self.output_mode = "auto"  # auto, full, minimal, summary
        self.last_response = ""  # Store for /expand command

        # Tools
        self.bash_tool = BashCommandTool()
        self.file_read = ReadFileTool()
        self.file_write = WriteFileTool()
        self.file_edit = EditFileTool()
        self.git_status = GitStatusTool()
        self.git_diff = GitDiffTool()

        # Agents (lazy load)
        self._agents = {}

        # Commands
        self.commands = self._load_commands()
        self.session = self._create_session()
    
    def _format_agent_output(self, agent_name: str, response, intent_type) -> str:
        """Format agent output beautifully (human-readable).
        
        Boris Cherny: "Code is read 10x more than written. So is output."
        """
        from rich.text import Text
        from rich.panel import Panel
        from rich import box
        
        # Handle errors
        if not response.success:
            return f"❌ **{agent_name} Failed**\n\n{response.error}"
        
        # Special formatting for ReviewerAgent v3.0
        if agent_name == "ReviewerAgent" and isinstance(response.data, dict):
            # Extract report (agent wraps it in 'report' key)
            data = response.data.get('report', response.data)
            
            # Header
            score = data.get('score', 0)
            approved = data.get('approved', False)
            metrics = data.get('metrics', [])
            
            lines = [
                "# 🔍 CODE REVIEW COMPLETE (v3.0 - McCabe Analysis)\n",
                f"**Score:** {score}/100",
                f"**Status:** {'✅ APPROVED for merge' if approved else '❌ CHANGES REQUIRED'}\n",
            ]
            
            # Function Metrics
            if metrics:
                lines.append("## 📊 Function Complexity Analysis\n")
                for m in metrics[:10]:  # Show top 10
                    lines.append(f"- `{m.get('function_name')}`: Complexity={m.get('complexity')}, Args={m.get('args_count')}, LOC={m.get('loc')}")
                if len(metrics) > 10:
                    lines.append(f"  ... and {len(metrics) - 10} more functions")
                lines.append("")
            
            # Issues (new structure)
            issues = data.get('issues', [])
            if issues:
                # Group by severity
                critical = [i for i in issues if i.get('severity') == 'CRITICAL']
                high = [i for i in issues if i.get('severity') == 'HIGH']
                medium = [i for i in issues if i.get('severity') == 'MEDIUM']
                
                if critical:
                    lines.append("## 🚨 CRITICAL Issues\n")
                    for issue in critical:
                        lines.append(f"- **{issue.get('file')}:{issue.get('line')}** [{issue.get('category')}]")
                        lines.append(f"  {issue.get('message')}")
                        if issue.get('suggestion'):
                            lines.append(f"  💡 *{issue.get('suggestion')}*")
                    lines.append("")
                
                if high:
                    lines.append("## ⚠️ HIGH Priority\n")
                    for issue in high:
                        lines.append(f"- **{issue.get('file')}:{issue.get('line')}** - {issue.get('message')}")
                    lines.append("")
                
                if medium:
                    lines.append("## 📝 Medium Priority\n")
                    for issue in medium:
                        lines.append(f"- {issue.get('file')}:{issue.get('line')} - {issue.get('message')}")
                    lines.append("")
            
            # Summary
            summary = data.get('summary', '')
            if summary:
                lines.append("## Summary\n")
                lines.append(summary)
                lines.append("")
            
            # Next Steps
            next_steps = data.get('next_steps', [])
            if next_steps:
                lines.append("## 🎯 Next Steps\n")
                for step in next_steps:
                    lines.append(f"- {step}")
            
            return "\n".join(lines)
        
        # Generic formatting for other agents
        if isinstance(response.data, dict):
            # Try to extract meaningful info
            summary = response.data.get('summary', response.data.get('result', ''))
            if summary:
                return f"**{agent_name} Result:**\n\n{summary}"
            
            # Fallback: format dict nicely
            import json
            formatted = json.dumps(response.data, indent=2)
            return f"**{agent_name} Result:**\n\n```json\n{formatted}\n```"
        
        # Plain string output
        return str(response.data)
    
    def _register_agents(self):
        """Register all agents with coordinator (Phase 2.2).
        
        Creates adapter to convert between agent.execute() and coordinator.invoke().
        """
        from qwen_dev_cli.core.integration_types import IntentType, AgentResponse
        from qwen_dev_cli.agents.base import AgentTask
        
        # Agent adapter: convert execute(AgentTask) → invoke(request, context)
        async def make_agent_adapter(agent_class, intent_type):
            """Create adapter for agent."""
            # Initialize agent with required dependencies
            agent_instance = agent_class(
                llm_client=self.llm_client,
                mcp_client=None  # Optional for now
            )
            
            async def adapter_invoke(request: str, context: dict) -> AgentResponse:
                """Adapt agent.execute() to coordinator protocol."""
                import re
                
                # Extract file paths from request (e.g., "review file.py")
                file_matches = re.findall(r'[\w\-./]+\.[\w]+', request)
                
                # Enrich context with extracted files
                enriched_context = dict(context) if context else {}
                if file_matches:
                    enriched_context['files'] = file_matches
                    enriched_context['target_files'] = file_matches  # Agent might use this
                
                # Create AgentTask from request
                task = AgentTask(
                    request=request,
                    context=enriched_context,
                    session_id="shell_session"
                )
                
                # Execute agent
                response = await agent_instance.execute(task)
                
                # Format output beautifully (Boris Cherny: UX matters)
                output = self._format_agent_output(
                    agent_class.__name__,
                    response,
                    intent_type
                )
                
                return {
                    "success": response.success,
                    "output": output,
                    "metadata": response.metadata,
                    "execution_time_ms": 0.0,
                    "tokens_used": None
                }
            
            return adapter_invoke
        
        # Register ReviewerAgent only (Phase 2.2 - incremental)
        try:
            reviewer_adapter = asyncio.run(make_agent_adapter(ReviewerAgent, IntentType.REVIEW))
            
            # Wrap in a class that has invoke method (protocol compliance)
            class AgentWrapper:
                def __init__(self, invoke_func):
                    self.invoke = invoke_func
            
            self.coordinator.register_agent(
                IntentType.REVIEW,
                AgentWrapper(reviewer_adapter)
            )
            
            console.print("[dim]  → ReviewerAgent registered[/dim]")
            
            # Register RefactorerAgent
            refactorer_adapter = asyncio.run(make_agent_adapter(RefactorerAgent, IntentType.REFACTOR))
            self.coordinator.register_agent(
                IntentType.REFACTOR,
                AgentWrapper(refactorer_adapter)
            )
            console.print("[dim]  → RefactorerAgent registered[/dim]")
            
        except Exception as e:
            console.print(f"[yellow]⚠️  Agent registration failed: {e}[/yellow]")

    def _load_commands(self) -> Dict[str, Dict]:
        """Load commands with rich metadata."""
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
            "/status": {
                "icon": "📊",
                "description": "Show session status",
                "category": CommandCategory.SYSTEM,
                "handler": self._cmd_status
            },
            "/expand": {
                "icon": "📖",
                "description": "Show full last response",
                "category": CommandCategory.SYSTEM,
                "handler": self._cmd_expand
            },
            "/mode": {
                "icon": "🎛️",
                "description": "Change output mode (auto/full/minimal)",
                "category": CommandCategory.SYSTEM,
                "handler": self._cmd_mode
            },
            
            # Agents
            "/architect": {
                "icon": "🏗️",
                "description": "Architect agent - system design",
                "category": CommandCategory.AGENT,
                "handler": lambda msg: asyncio.run(self._invoke_agent("architect", msg))
            },
            "/refactor": {
                "icon": "♻️",
                "description": "Refactor agent - improve code",
                "category": CommandCategory.AGENT,
                "handler": lambda msg: asyncio.run(self._invoke_agent("refactorer", msg))
            },
            "/test": {
                "icon": "🧪",
                "description": "Test agent - generate tests",
                "category": CommandCategory.AGENT,
                "handler": lambda msg: asyncio.run(self._invoke_agent("testing", msg))
            },
            "/review": {
                "icon": "🔍",
                "description": "Review agent - code review",
                "category": CommandCategory.AGENT,
                "handler": lambda msg: asyncio.run(self._invoke_agent("reviewer", msg))
            },
            "/refactor": {
                "icon": "♻️",
                "description": "Refactor agent - improve code",
                "category": CommandCategory.AGENT,
                "handler": lambda msg: asyncio.run(self._invoke_agent("refactorer", msg))
            },
            "/docs": {
                "icon": "📚",
                "description": "Documentation agent",
                "category": CommandCategory.AGENT,
                "handler": lambda msg: asyncio.run(self._invoke_agent("documentation", msg))
            },
            "/explore": {
                "icon": "🗺️",
                "description": "Explorer agent - navigate code",
                "category": CommandCategory.AGENT,
                "handler": lambda msg: asyncio.run(self._invoke_agent("explorer", msg))
            },
            "/plan": {
                "icon": "📋",
                "description": "Planner agent - strategic planning",
                "category": CommandCategory.AGENT,
                "handler": lambda msg: asyncio.run(self._invoke_agent("planner", msg))
            },
            "/dream": {
                "icon": "💭",
                "description": "DREAM mode - critical analysis",
                "category": CommandCategory.AGENT,
                "handler": self._cmd_dream
            },
            "/performance": {
                "icon": "⚡",
                "description": "Performance agent - optimize speed",
                "category": CommandCategory.AGENT,
                "handler": lambda msg: asyncio.run(self._invoke_agent("performance", msg))
            },
            "/security": {
                "icon": "🔒",
                "description": "Security agent - find vulnerabilities",
                "category": CommandCategory.AGENT,
                "handler": lambda msg: asyncio.run(self._invoke_agent("security", msg))
            },
        }

    def _create_session(self) -> PromptSession:
        """Create session with clean, modern prompt."""
        history_file = Path.home() / '.qwen-dev-history'
        
        # Clean style - let Rich handle the visuals
        clean_style = Style.from_dict({
            '': '#00d4aa',                      # Default text color (teal)
            'placeholder': '#666666 italic',    # Placeholder
        })
        
        return PromptSession(
            message=[('class:prompt', '⚡ › ')],  # Clean prompt symbol
            history=FileHistory(str(history_file)),
            auto_suggest=AutoSuggestFromHistory(),
            completer=SmartCompleter(self.commands),
            key_bindings=self._create_keybindings(),
            enable_history_search=True,
            complete_while_typing=True,
            complete_in_thread=True,
            mouse_support=False,  # DISABLED: Allow terminal mouse (copy/paste/select)
            placeholder="Ask anything or type / for commands...",
            style=clean_style,
            multiline=False,
        )

    def _create_keybindings(self) -> KeyBindings:
        """Create intuitive keybindings."""
        bindings = KeyBindings()

        @bindings.add("c-p")
        def show_palette(event):
            """Command Palette"""
            self._show_palette()

        @bindings.add("c-d")
        def toggle_dream(event):
            """DREAM mode"""
            self.dream_mode = not self.dream_mode
            status = "🟢 ON" if self.dream_mode else "⚫ OFF"
            console.print(f"\n💭 DREAM mode: [bold]{status}[/bold]\n")

        @bindings.add("c-s")
        def show_status(event):
            """Session status"""
            self._cmd_status("")

        @bindings.add("c-l")
        def clear_screen(event):
            """Clear screen"""
            console.clear()

        @bindings.add("c-o")
        def expand_response(event):
            """Expand last response"""
            self._cmd_expand("")

        return bindings

    def _get_prompt(self):
        """Generate beautiful prompt with neon box (max-code style)."""
        # Max-code style: > | prompt text with border
        # Neon gradient: green → yellow
        
        prefix = []
        
        if self.dream_mode:
            prefix.append(('ansimagenta bold', '💭 '))
        
        if self.current_agent:
            prefix.append(('ansiyellow bold', f'{self.current_agent} '))

        # Prompt line: > | with placeholder hint
        return FormattedText(prefix + [
            ('ansigreen bold', '>'),
            ('', ' '),
            ('ansiyellow bold', '|'),
            ('', ' '),
        ])

    def _cmd_help(self, _):
        """Show MINIMAL help (Nov 2025)."""
        console.print("\n[bold cyan]Commands[/bold cyan]")
        
        # Group by category
        categories = {
            'system': [],
            'agent': []
        }
        
        for cmd, meta in self.commands.items():
            cat = meta['category'].value
            if cat in categories:
                categories[cat].append((cmd, meta))
        
        # Render compact (two columns)
        for cat_name, cat_key in [('System', 'system'), ('Agents', 'agent')]:
            if cat_key in categories and categories[cat_key]:
                console.print(f"\n[dim]{cat_name}:[/dim]")
                items = sorted(categories[cat_key])
                
                # Single column (cleaner for longer descriptions)
                for cmd, meta in items:
                    console.print(f"  {meta['icon']} [cyan]{cmd:14}[/cyan] [dim]{meta['description']}[/dim]")
        
        console.print("\n[dim]💡 Ctrl+P palette • Ctrl+O expand • Tab autocomplete • Natural chat[/dim]\n")

    def _cmd_exit(self, _):
        """Exit with style."""
        duration = int(time.time() - self.session_start)
        minutes = duration // 60
        seconds = duration % 60
        
        console.print("\n[bold cyan]Session Summary:[/bold cyan]")
        console.print(f"  • Commands executed: [green]{self.command_count}[/green]")
        console.print(f"  • Duration: [green]{minutes}m {seconds}s[/green]")
        console.print("\n[bold yellow]👋 Goodbye! Keep coding! ✨[/bold yellow]")
        console.print("[dim]Soli Deo Gloria 🙏[/dim]\n")
        
        # Cleanup to avoid "Unclosed client session" warnings
        self._cleanup()
        
        self.running = False
    
    def _cleanup(self):
        """Cleanup aiohttp sessions silently."""
        import warnings
        warnings.filterwarnings('ignore', message='.*Unclosed.*')
        warnings.filterwarnings('ignore', message='.*unclosed.*')
    
    def __del__(self):
        """Destructor - cleanup warnings."""
        self._cleanup()

    def _cmd_expand(self, _):
        """Show full last response."""
        if not self.last_response:
            console.print("[yellow]No previous response to expand[/yellow]\n")
            return
        
        console.print("\n[bold cyan]📖 Full Response[/bold cyan]")
        console.print("─" * 60)
        console.print(self.last_response, style="white")
        console.print("─" * 60)
        console.print(f"[dim]{len(self.last_response.split())} words • {len(self.last_response)} chars[/dim]\n")
    
    def _cmd_mode(self, args: str):
        """Change output mode."""
        modes = ['auto', 'full', 'minimal', 'summary']
        
        if not args or args not in modes:
            console.print(f"[yellow]Current mode: {self.output_mode}[/yellow]")
            console.print(f"[dim]Available: {', '.join(modes)}[/dim]")
            console.print(f"[dim]Usage: /mode <mode>[/dim]\n")
            return
        
        self.output_mode = args
        console.print(f"[green]✓ Output mode: {args}[/green]\n")
    
    def _cmd_clear(self, _):
        """Clear with feedback."""
        console.clear()
        console.print("[dim]✨ Screen cleared[/dim]\n")

    def _cmd_status(self, _):
        """Show session status."""
        duration = int(time.time() - self.session_start)
        
        panel = Panel.fit(
            f"""[bold]Session Status[/bold]

⏱️  Duration: [cyan]{duration}s[/cyan]
🎯 Commands: [green]{self.command_count}[/green]
💭 DREAM mode: [yellow]{'ON' if self.dream_mode else 'OFF'}[/yellow]
🤖 Current agent: [magenta]{self.current_agent or 'None'}[/magenta]
📁 Context: [blue]{len(self.context.file_history)} files[/blue]

[dim]Shortcuts: Ctrl+P (palette) • Ctrl+O (expand) • Ctrl+D (dream) • Ctrl+L (clear)[/dim]
            """,
            border_style="cyan",
            title="📊 Status"
        )
        console.print("\n")
        console.print(panel)
        console.print()

    def _cmd_dream(self, message: str):
        """Toggle DREAM mode."""
        if not message.strip():
            self.dream_mode = not self.dream_mode
            status = "🟢 ENABLED" if self.dream_mode else "⚫ DISABLED"
            console.print(f"\n💭 [bold]DREAM mode {status}[/bold]\n")
        else:
            asyncio.run(self._invoke_agent("reviewer", f"[CRITICAL ANALYSIS] {message}"))

    async def _invoke_agent(self, agent_name: str, message: str):
        """Invoke agent with beautiful feedback."""
        if not message.strip():
            console.print(f"[yellow]⚠️  Please provide a message for the {agent_name} agent[/yellow]\n")
            return

        # INJECT PROJECT CONTEXT 🧠
        # Se mencionar path, adiciona contexto do projeto
        import re
        import os
        
        project_context = ""
        path_match = re.search(r'["\']?(/[\w\-/.]+)["\']?', message)
        
        if path_match:
            project_path = path_match.group(1)
            if os.path.exists(project_path):
                console.print(f"[dim]📁 Analyzing project at {project_path}...[/dim]")
                
                # Build context from project
                context_parts = [f"Project Path: {project_path}"]
                
                # README
                for readme_name in ['README.md', 'readme.md', 'README']:
                    readme_path = os.path.join(project_path, readme_name)
                    if os.path.exists(readme_path):
                        try:
                            with open(readme_path, 'r') as f:
                                readme_content = f.read()[:2000]  # First 2000 chars
                                context_parts.append(f"\n=== README ===\n{readme_content}")
                                break
                        except:
                            pass
                
                # pyproject.toml ou package.json
                for config_file in ['pyproject.toml', 'package.json', 'setup.py']:
                    config_path = os.path.join(project_path, config_file)
                    if os.path.exists(config_path):
                        try:
                            with open(config_path, 'r') as f:
                                config_content = f.read()[:1000]
                                context_parts.append(f"\n=== {config_file} ===\n{config_content}")
                                break
                        except:
                            pass
                
                # Structure
                try:
                    import subprocess
                    result = subprocess.run(
                        ['ls', '-la', project_path],
                        capture_output=True,
                        text=True,
                        timeout=2
                    )
                    if result.returncode == 0:
                        context_parts.append(f"\n=== Structure ===\n{result.stdout[:1000]}")
                except:
                    pass
                
                project_context = "\n".join(context_parts)
                
                # Prepend context to message
                message = f"{project_context}\n\n{message}"

        # Get agent (normalize name)
        # Intent detector returns: architect, refactorer, testing, reviewer, documentation, explorer, planner
        # Agents are: ArchitectAgent, RefactorerAgent, TestingAgent, ReviewerAgent, DocumentationAgent, ExplorerAgent, PlannerAgent
        
        if agent_name not in self._agents:
            agent_map = {
                "architect": ArchitectAgent,
                "refactor": RefactorerAgent,
                "refactorer": RefactorerAgent,
                "test": TestingAgent,
                "testing": TestingAgent,
                "review": ReviewerAgent,
                "reviewer": ReviewerAgent,
                "docs": DocumentationAgent,
                "documentation": DocumentationAgent,
                "explore": ExplorerAgent,
                "explorer": ExplorerAgent,
                "plan": PlannerAgent,
                "planner": PlannerAgent,
                "performance": PerformanceAgent,
                "perf": PerformanceAgent,
                "security": SecurityAgent,
                "sec": SecurityAgent,
            }
            
            # Show loading with smooth animation
            spinner_frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
            
            with Progress(
                SpinnerColumn(spinner_name="dots", style="cyan"),
                TextColumn(f"[bold cyan]✨ Loading {agent_name} agent..."),
                console=console,
                transient=True
            ) as progress:
                task = progress.add_task("load", total=None)
                
                # Initialize agent with required dependencies
                try:
                    # Try without args first (some agents don't need them)
                    self._agents[agent_name] = agent_map[agent_name]()
                except TypeError:
                    # If needs args, pass llm_client and mcp_client (None for mcp)
                    self._agents[agent_name] = agent_map[agent_name](
                        llm_client=self.llm_client,
                        mcp_client=None  # We don't use MCP in shell mode
                    )
                
                await asyncio.sleep(0.3)  # Smooth loading feel

        self.current_agent = agent_name
        
        icon_map = {
            "architect": "🏗️",
            "refactorer": "♻️",
            "refactor": "♻️",
            "testing": "🧪",
            "test": "🧪",
            "reviewer": "🔍",
            "review": "🔍",
            "documentation": "📚",
            "docs": "📚",
            "explorer": "🗺️",
            "explore": "🗺️",
            "planner": "📋",
            "plan": "📋",
            "performance": "⚡",
            "perf": "⚡",
            "security": "🔒",
            "sec": "🔒",
        }
        icon = icon_map.get(agent_name, "🤖")

        console.print(f"\n{icon} [bold cyan]{agent_name.capitalize()} Agent[/bold cyan]\n")

        # Stream response
        await self._stream_response(message, system=f"You are the {agent_name} agent.")
        
        self.current_agent = None

    async def _stream_response(self, message: str, system: Optional[str] = None):
        """Stream with MINIMAL OUTPUT (Nov 2025 style)."""
        console.print("[dim]" + "─" * 60 + "[/dim]")
        
        buffer = []
        word_count = 0
        char_count = 0
        start_time = time.time()
        
        # Initialize streaming minimal
        streamer = StreamingMinimal() if self.minimal_output else None
        
        # Initialize metrics
        if self.token_metrics:
            self.token_metrics.input_tokens = len(message.split())
            self.token_metrics.output_tokens = 0
        
        try:
            async for chunk in self.llm_client.stream_chat(
                prompt=message,
                context=system,
                max_tokens=4000,
                temperature=0.7
            ):
                buffer.append(chunk)
                char_count += len(chunk)
                
                # Streaming minimal mode
                if streamer:
                    streamer.add_chunk(chunk)
                    
                    # Only show if under threshold
                    if not streamer.should_truncate:
                        console.print(chunk, end="", style="white")
                else:
                    console.print(chunk, end="", style="white")
                
                # Count words
                if ' ' in chunk or '\n' in chunk:
                    word_count += len(chunk.split())
                    
                    # Update metrics
                    if self.token_metrics:
                        self.token_metrics.output_tokens = word_count
                        elapsed = time.time() - start_time
                        if elapsed > 0:
                            self.token_metrics.tokens_per_second = word_count / elapsed
                
                sys.stdout.flush()
            
            # Store full response for /expand
            full_response = ''.join(buffer)
            self.last_response = full_response
            
            # Enhanced stats (minimal style)
            duration = time.time() - start_time
            wps = int(word_count / duration) if duration > 0 else 0
            
            console.print()
            
            # Compact stats (Nov 2025 style)
            console.print()
            console.print("─" * 60)
            cost = self.token_metrics.cost_formatted if (self.token_metrics and self.token_metrics.estimated_cost > 0) else None
            stats_parts = [f"✓ {word_count} words in {duration:.1f}s ({wps} wps)"]
            if cost:
                stats_parts.append(cost)
            console.print(f"[dim green]{' • '.join(stats_parts)}[/dim green]")
            console.print()
            
        except Exception as e:
            console.print(f"\n[red]❌ Error: {e}[/red]")
            console.print("[yellow]💡 Tip: Check connection[/yellow]\n")

    def _process_command(self, user_input: str):
        """Process with smart routing."""
        user_input = user_input.strip()
        if not user_input:
            return

        self.command_count += 1

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
                    console.print(f"\n[red]❌ Error: {e}[/red]")
                    console.print("[yellow]💡 Tip: Type /help for usage[/yellow]\n")
            
            elif cmd in ['/read', '/write', '/edit', '/run', '/git']:
                asyncio.run(self._process_tool(cmd, args))
            
            else:
                console.print(f"\n[red]❌ Unknown command: {cmd}[/red]")
                console.print("[yellow]💡 Type /help to see available commands[/yellow]\n")
        
        else:
            # Natural language
            asyncio.run(self._process_natural(user_input))

    async def _process_tool(self, tool: str, args: str):
        """Execute tool with rich feedback."""
        try:
            if tool == '/read':
                if not args:
                    console.print("[yellow]Usage: /read <file>[/yellow]\n")
                    return
                
                console.print(f"[dim]📖 Reading {args}...[/dim]")
                result = await self.file_read.execute(path=args)
                content = str(result.content) if hasattr(result, 'content') else str(result)
                
                # Detect language for syntax highlighting
                ext = Path(args).suffix.lstrip('.')
                lang_map = {
                    'py': 'python', 'js': 'javascript', 'ts': 'typescript',
                    'json': 'json', 'yaml': 'yaml', 'yml': 'yaml',
                    'md': 'markdown', 'sh': 'bash'
                }
                language = lang_map.get(ext, 'text')
                
                if language != 'text':
                    syntax = Syntax(content, language, theme="monokai", line_numbers=True)
                    console.print(Panel(syntax, title=f"📖 {args}", border_style="green"))
                else:
                    console.print(Panel(content, title=f"📖 {args}", border_style="green"))
                
                self.context.remember_file(args, content, "read")
                console.print(f"[dim]✓ Read {len(content)} characters[/dim]\n")
                
            elif tool == '/write':
                parts = args.split(maxsplit=1)
                if len(parts) < 2:
                    console.print("[yellow]Usage: /write <file> <content>[/yellow]\n")
                    return
                
                path, content = parts
                console.print(f"[dim]✍️  Writing to {path}...[/dim]")
                await self.file_write.execute(path=path, content=content)
                console.print(f"[green]✓ Written {len(content)} characters to {path}[/green]\n")
                
            elif tool == '/edit':
                console.print("[yellow]💡 Edit mode coming soon! Use /write for now.[/yellow]\n")
                
            elif tool == '/run':
                if not args:
                    console.print("[yellow]Usage: /run <command>[/yellow]\n")
                    return
                
                console.print(f"[dim]⚡ Running: {args}[/dim]")
                result = await self.bash_tool.execute(command=args)
                output = result.output if hasattr(result, 'output') else str(result)
                
                console.print(Panel(
                    output if output else "[dim]No output[/dim]",
                    title="⚡ Output",
                    border_style="green"
                ))
                console.print(f"[dim]✓ Completed in {result.duration if hasattr(result, 'duration') else '?'}s[/dim]\n")
                
            elif tool == '/git':
                if not args:
                    console.print("[yellow]Usage: /git status | diff[/yellow]\n")
                    return
                
                if 'status' in args:
                    console.print("[dim]🌿 Git status...[/dim]")
                    result = await self.git_status.execute()
                elif 'diff' in args:
                    console.print("[dim]🌿 Git diff...[/dim]")
                    result = await self.git_diff.execute()
                else:
                    console.print("[yellow]Usage: /git status | diff[/yellow]\n")
                    return
                
                console.print(Panel(str(result), title="🌿 Git", border_style="green"))
                console.print("[dim]✓ Git operation complete[/dim]\n")
                
        except Exception as e:
            console.print(f"\n[red]❌ Error: {e}[/red]")
            console.print("[yellow]💡 Check file permissions and path[/yellow]\n")

    async def _process_natural(self, message: str):
        """Process natural language with smart detection."""
        # Resolve context
        original = message
        message = self.context.resolve_reference(message)
        if message != original:
            console.print(f"[dim]🔄 Context: {message}[/dim]")

        # PHASE 2: Try coordinator first (agent auto-routing)
        coordinator_response = await self.coordinator.process_message(message)
        
        if coordinator_response:
            # Agent handled the message
            console.print(f"\n{coordinator_response}\n")
            return

        # Smart tool detection (fallback if no agent)
        msg_lower = message.lower()
        
        # File operations
        if any(kw in msg_lower for kw in ['read', 'show', 'open', 'cat']):
            import re
            match = re.search(r'[\w/.]+\.\w+', message)
            if match:
                await self._process_tool('/read', match.group(0))
                return
        
        # Bash execution
        if any(kw in msg_lower for kw in ['run', 'execute', 'bash']):
            import re
            cmd = re.sub(r'^.*(run|execute|bash)\s+', '', message, flags=re.IGNORECASE)
            await self._process_tool('/run', cmd)
            return
        
        # Git operations
        if 'git' in msg_lower:
            if 'status' in msg_lower:
                await self._process_tool('/git', 'status')
                return
            elif 'diff' in msg_lower:
                await self._process_tool('/git', 'diff')
                return

        # FALLBACK: Old agent detection (kept for compatibility)
        should_use_agent, detected_agent = self.intent_detector.should_use_agent(message)
        
        if should_use_agent and detected_agent:
            # Auto-route para agent apropriado
            icon_map = {
                "architect": "🏗️",
                "refactorer": "♻️",
                "testing": "🧪",
                "reviewer": "🔍",
                "documentation": "📚",
                "explorer": "🗺️",
                "planner": "📋",
                "performance": "⚡",
                "security": "🔒",
            }
            icon = icon_map.get(detected_agent, "🤖")
            console.print(f"[dim]{icon} Auto-routing to {detected_agent} agent...[/dim]")
            await self._invoke_agent(detected_agent, message)
            return

        # Chat mode with streaming
        if self.dream_mode:
            message = f"[CRITICAL ANALYSIS MODE] {message}"
        
        await self._stream_response(message)

    def _show_palette(self):
        """Show command palette."""
        console.print("\n[bold cyan]📋 Commands[/bold cyan]\n")
        
        # Minimal single column
        for cmd, meta in sorted(self.commands.items()):
            console.print(f"  {meta['icon']} [cyan]{cmd:14}[/cyan] [dim]{meta['description']}[/dim]")
        
        console.print("\n[dim]Tab autocomplete • /help details[/dim]\n")

    def run(self):
        """Run the masterpiece."""
        # Simple startup message (banner disabled for now)
        console.print("\n[bold cyan]JuanCS Dev CLI[/bold cyan] [dim]v0.2.0[/dim]")
        console.print("[dim]Type [bold cyan]/help[/bold cyan] or just start chatting ✨[/dim]\n")

        # Main loop
        while self.running:
            try:
                with patch_stdout():
                    user_input = self.session.prompt()
                
                if user_input is None:
                    continue
                
                self._process_command(user_input)

            except KeyboardInterrupt:
                console.print("\n[dim]💡 Press Ctrl+C again or type /exit to quit[/dim]\n")
                continue
            
            except EOFError:
                self._cmd_exit("")
                break
            
            except Exception as e:
                console.print(f"\n[red]❌ Unexpected error: {e}[/red]")
                console.print("[yellow]💡 Please report this if it persists[/yellow]\n")


def start_masterpiece_repl():
    """Entry point."""
    import warnings
    
    # Suppress aiohttp cleanup warnings
    warnings.filterwarnings('ignore', category=ResourceWarning)
    warnings.filterwarnings('ignore', message='.*Unclosed.*')
    warnings.filterwarnings('ignore', message='.*unclosed.*')
    
    try:
        repl = MasterpieceREPL()
        repl.run()
    except KeyboardInterrupt:
        console.print("\n\n[bold yellow]👋 Goodbye![/bold yellow]\n")
    except Exception as e:
        console.print(f"\n[red]Fatal error: {e}[/red]\n")
        import traceback
        console.print(f"[dim]{traceback.format_exc()}[/dim]\n")
        sys.exit(1)


if __name__ == "__main__":
    start_masterpiece_repl()
