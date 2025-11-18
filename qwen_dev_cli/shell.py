"""Interactive shell with tool-based architecture."""

import asyncio
import os
import json
from typing import Optional, Dict, Any
from pathlib import Path

from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table

from .core.context import ContextBuilder
from .core.conversation import ConversationManager, ConversationState
from .core.recovery import (
    ErrorRecoveryEngine,
    RecoveryContext,
    ErrorCategory,
    create_recovery_context
)

# Import LLM client (using existing implementation)
from .core.async_executor import AsyncExecutor
from .core.file_watcher import FileWatcher
from .core.file_watcher import RecentFilesTracker
try:
    from .core.llm import llm_client as default_llm_client
except ImportError:
    default_llm_client = None
from .tools.base import ToolRegistry
from .tools.file_ops import (
    ReadFileTool, WriteFileTool, EditFileTool,
    ListDirectoryTool, DeleteFileTool
)
from .tools.file_mgmt import (
    MoveFileTool, CopyFileTool, CreateDirectoryTool,
    ReadMultipleFilesTool, InsertLinesTool
)
from .tools.search import SearchFilesTool, GetDirectoryTreeTool
from .tools.exec import BashCommandTool
from .tools.git_ops import GitStatusTool, GitDiffTool
from .tools.context import GetContextTool, SaveSessionTool, RestoreBackupTool
from .tools.terminal import (
    CdTool, LsTool, PwdTool, MkdirTool, RmTool,
    CpTool, MvTool, TouchTool, CatTool
)
from .intelligence.context_enhanced import build_rich_context
from .intelligence.risk import assess_risk


class SessionContext:
    """Persistent context across shell session."""
    
    def __init__(self):
        self.cwd = os.getcwd()
        self.conversation = []
        self.modified_files = set()
        self.read_files = set()
        self.tool_calls = []
        self.history = []
    
    def track_tool_call(self, tool_name: str, args: Dict[str, Any], result: Any):
        """Track tool usage."""
        self.tool_calls.append({
            "tool": tool_name,
            "args": args,
            "result": result,
            "success": getattr(result, 'success', True)
        })
        
        # Track file operations
        if tool_name == "write_file" or tool_name == "edit_file":
            self.modified_files.add(args.get("path", ""))
        elif tool_name == "read_file":
            self.read_files.add(args.get("path", ""))


class InteractiveShell:
    """Tool-based interactive shell (Claude Code-level) with multi-turn conversation."""
    
    def __init__(self, llm_client=None, session_id: Optional[str] = None):
        self.console = Console()
        self.llm = llm_client or default_llm_client
        self.context = SessionContext()
        self.context_builder = ContextBuilder()
        
        # Phase 2.3: Multi-turn conversation manager
        if session_id is None:
            import uuid
            session_id = f"shell_{int(asyncio.get_event_loop().time() * 1000)}"
        
        self.conversation = ConversationManager(
            session_id=session_id,
            max_context_tokens=4000,
            enable_auto_recovery=True,
            max_recovery_attempts=2  # Constitutional P6
        )
        
        # Phase 3.1: Error recovery engine
        self.recovery_engine = ErrorRecoveryEngine(
            llm_client=self.llm,
            max_attempts=2,  # Constitutional P6
            enable_learning=True
        )
        
        # Setup prompt session
        history_file = Path.home() / ".qwen_shell_history"
        self.session = PromptSession(
            history=FileHistory(str(history_file)),
            auto_suggest=AutoSuggestFromHistory(),
        )
        
        # Initialize tool registry
        self.registry = ToolRegistry()
        self._register_tools()
        
        # Phase 4.3: Async executor for parallel tool execution
        self.async_executor = AsyncExecutor(max_parallel=5)
        
        # Phase 4.4: File watcher for context tracking
        self.file_watcher = FileWatcher(root_path=".", watch_extensions={'.py', '.js', '.ts', '.go', '.rs'})
        self.recent_files = RecentFilesTracker(maxsize=50)
        
        # Setup file watcher callback
        self.file_watcher.add_callback(self._on_file_changed)
        self.file_watcher.start()
    
    def _register_tools(self):
        """Register all available tools."""
        tools = [
            # File reading (4 tools)
            ReadFileTool(),
            ReadMultipleFilesTool(),
            ListDirectoryTool(),
            
            # File writing (4 tools)
            WriteFileTool(),
            EditFileTool(),
            InsertLinesTool(),
            DeleteFileTool(),
            
            # File management (3 tools)
            MoveFileTool(),
            CopyFileTool(),
            CreateDirectoryTool(),
            
            # Search (2 tools)
            SearchFilesTool(),
            GetDirectoryTreeTool(),
            
            # Execution (1 tool)
            BashCommandTool(),
            
            # Git (2 tools)
            GitStatusTool(),
            GitDiffTool(),
            
            # Context (3 tools)
            GetContextTool(),
            SaveSessionTool(),
            RestoreBackupTool(),
            
            # Terminal commands (9 tools)
            CdTool(),
            LsTool(),
            PwdTool(),
            MkdirTool(),
            RmTool(),
            CpTool(),
            MvTool(),
            TouchTool(),
            CatTool(),
        ]
        
        for tool in tools:
            self.registry.register(tool)
        
        self.console.print(f"[dim]Loaded {len(tools)} tools[/dim]")
    
    def _show_welcome(self):
        """Show welcome message."""
        welcome = Panel(
            "[bold cyan]QWEN-DEV-CLI Interactive Shell v1.0[/bold cyan]\n\n"
            f"Tools available: {len(self.registry.get_all())}\n"
            f"Working directory: {self.context.cwd}\n\n"
            "Type natural language commands or /help for system commands",
            title="🚀 AI-Powered Code Shell",
            border_style="cyan"
        )
        self.console.print(welcome)
    
    async def _execute_with_recovery(
        self,
        tool,
        tool_name: str,
        args: Dict[str, Any],
        turn
    ):
        """
        Execute tool with error recovery loop (Phase 3.1).
        
        Implements Constitutional Layer 4: Verify-Fix-Execute loop
        
        Args:
            tool: Tool instance
            tool_name: Tool name
            args: Tool arguments
            turn: Current conversation turn
        
        Returns:
            Tool result or None if recovery failed
        """
        max_attempts = self.recovery_engine.max_attempts
        
        for attempt in range(1, max_attempts + 1):
            try:
                # Execute tool
                result = await tool.execute(**args)
                
                # Track tool call (legacy)
                self.context.track_tool_call(tool_name, args, result)
                
                # Phase 2.3: Track in conversation
                self.conversation.add_tool_result(
                    turn, tool_name, args, result,
                    success=result.success,
                    error=None if result.success else str(result.data)
                )
                
                # Check if successful
                if result.success:
                    # Success! Record if this was a recovery
                    if attempt > 1:
                        self.console.print(f"[green]✓ Recovered on attempt {attempt}[/green]")
                        # Record successful recovery
                        # (recovery_context would be from previous attempt)
                    
                    return result
                
                # Tool executed but returned failure
                error_msg = str(result.data)
                
                # If last attempt, fail
                if attempt >= max_attempts:
                    self.console.print(
                        f"[red]✗ {tool_name} failed after {max_attempts} attempts[/red]"
                    )
                    return None
                
                # Attempt recovery (Constitutional P6: mandatory diagnosis)
                self.console.print(
                    f"[yellow]⚠ Attempt {attempt} failed, attempting recovery...[/yellow]"
                )
                
                # Create recovery context
                recovery_ctx = await create_recovery_context(
                    self.conversation,
                    turn,
                    tool_name,
                    args,
                    error_msg,
                    max_attempts=max_attempts
                )
                recovery_ctx.attempt_number = attempt
                
                # Attempt recovery
                recovery_result = await self.recovery_engine.attempt_recovery(recovery_ctx)
                
                if not recovery_result.success or not recovery_result.corrected_args:
                    # Recovery failed
                    self.console.print(
                        f"[red]✗ Recovery failed: {recovery_result.escalation_reason}[/red]"
                    )
                    return None
                
                # Show diagnosis
                if recovery_ctx.diagnosis:
                    self.console.print(f"[dim]Diagnosis: {recovery_ctx.diagnosis[:100]}...[/dim]")
                
                # Update args for next attempt
                if recovery_result.corrected_tool:
                    tool_name = recovery_result.corrected_tool
                    tool = self.registry.get(tool_name)
                    if not tool:
                        self.console.print(f"[red]✗ Corrected tool not found: {tool_name}[/red]")
                        return None
                
                args = recovery_result.corrected_args
                self.console.print(f"[cyan]↻ Retrying with corrected parameters...[/cyan]")
                
            except Exception as e:
                # Exception during execution
                error_msg = str(e)
                
                # Phase 2.3: Track exception
                self.conversation.add_tool_result(
                    turn, tool_name, args, None,
                    success=False, error=error_msg
                )
                
                # If last attempt, fail
                if attempt >= max_attempts:
                    self.console.print(
                        f"[red]✗ {tool_name} exception after {max_attempts} attempts: {error_msg}[/red]"
                    )
                    return None
                
                # Attempt recovery for exception
                self.console.print(
                    f"[yellow]⚠ Exception on attempt {attempt}, attempting recovery...[/yellow]"
                )
                
                # Create recovery context
                recovery_ctx = await create_recovery_context(
                    self.conversation,
                    turn,
                    tool_name,
                    args,
                    error_msg,
                    max_attempts=max_attempts
                )
                recovery_ctx.attempt_number = attempt
                
                # Attempt recovery
                recovery_result = await self.recovery_engine.attempt_recovery(recovery_ctx)
                
                if not recovery_result.success or not recovery_result.corrected_args:
                    self.console.print(
                        f"[red]✗ Recovery failed: {recovery_result.escalation_reason}[/red]"
                    )
                    return None
                
                # Update for retry
                if recovery_result.corrected_tool:
                    tool_name = recovery_result.corrected_tool
                    tool = self.registry.get(tool_name)
                
                args = recovery_result.corrected_args
                self.console.print(f"[cyan]↻ Retrying after exception...[/cyan]")
        
        # Should not reach here, but just in case
        return None
    
    async def _process_tool_calls(self, user_input: str) -> str:
        """Process user input and execute tools via LLM with conversation context (Phase 2.3)."""
        # Phase 2.3: Start new conversation turn
        turn = self.conversation.start_turn(user_input)
        
        try:
            # Import professional prompts (Phase 1.1 complete!)
            from .prompts import (
                build_system_prompt,
                build_user_prompt,
                get_examples_for_context
            )
            
            # Build prompt for LLM
            tool_schemas = self.registry.get_schemas()
            
            # Group tools by category for better understanding
            tool_list = []
            for schema in tool_schemas:
                tool_list.append(f"- {schema['name']}: {schema['description']}")
            
            system_prompt = f"""You are an AI code assistant with access to tools for file operations, git, search, and execution.

Available tools ({len(tool_schemas)} total):
{chr(10).join(tool_list)}

Current context:
- Working directory: {self.context.cwd}
- Modified files: {list(self.context.modified_files) if self.context.modified_files else 'none'}
- Read files: {list(self.context.read_files) if self.context.read_files else 'none'}
- Conversation turns: {len(self.conversation.turns)}
- Context usage: {self.conversation.context_window.get_usage_percentage():.0%}

INSTRUCTIONS:
1. Analyze the user's request (consider conversation history)
2. If it requires tools, respond ONLY with a JSON array of tool calls
3. If no tools needed, respond with helpful text

Tool call format:
[
  {{"tool": "tool_name", "args": {{"param": "value"}}}}
]

Examples:
User: "read api.py"
Response: [{{"tool": "readfile", "args": {{"path": "api.py"}}}}]

User: "show git status"
Response: [{{"tool": "gitstatus", "args": {{}}}}]

User: "search for TODO in python files"
Response: [{{"tool": "searchfiles", "args": {{"pattern": "TODO", "file_pattern": "*.py"}}}}]

User: "what time is it?"
Response: I don't have a tool to check the current time, but I can help you with code-related tasks."""
            
            # Phase 2.3: Include conversation context (Layer 3: Tool result feedback loop)
            messages = [
                {"role": "system", "content": system_prompt}
            ]
            
            # Add conversation history (last 3 turns for context)
            context_messages = self.conversation.get_context_for_llm(include_last_n=3)
            messages.extend(context_messages)
            
            # Add current user input
            messages.append({"role": "user", "content": user_input})
            
            # Get LLM response
            response = await self.llm.generate_async(
                messages=messages,
                temperature=0.1,
                max_tokens=2000
            )
            
            # Parse response
            response_text = response.get("content", "")
            tokens_used = response.get("tokens_used", len(response_text) // 4)
            
            # Phase 2.3: Add LLM response to turn
            self.conversation.add_llm_response(turn, response_text, tokens_used=tokens_used)
            
            # Try to parse as tool calls
            try:
                # Look for JSON array in response
                if '[' in response_text and ']' in response_text:
                    start = response_text.index('[')
                    end = response_text.rindex(']') + 1
                    json_str = response_text[start:end]
                    tool_calls = json.loads(json_str)
                    
                    if isinstance(tool_calls, list) and tool_calls:
                        # Phase 2.3: Add tool calls to turn
                        self.conversation.add_tool_calls(turn, tool_calls)
                        return await self._execute_tool_calls(tool_calls, turn)
            except (json.JSONDecodeError, ValueError):
                pass
            
            # If not tool calls, return as regular response
            # Phase 2.3: Transition to IDLE (no tools to execute)
            self.conversation.transition_state(ConversationState.IDLE, "text_response_only")
            return response_text
            
        except Exception as e:
            # Phase 2.3: Mark error in turn
            turn.error = str(e)
            turn.error_category = "system"
            self.conversation.transition_state(ConversationState.ERROR, f"exception: {type(e).__name__}")
            return f"Error: {str(e)}"
    
    async def _execute_tool_calls(self, tool_calls: list[Dict[str, Any]], turn) -> str:
        """Execute a sequence of tool calls with conversation tracking (Phase 2.3)."""
        results = []
        
        for call in tool_calls:
            tool_name = call.get("tool", "")
            args = call.get("args", {})
            
            tool = self.registry.get(tool_name)
            if not tool:
                error_msg = f"Unknown tool: {tool_name}"
                results.append(f"❌ {error_msg}")
                
                # Phase 2.3: Track tool failure
                self.conversation.add_tool_result(
                    turn, tool_name, args, None, 
                    success=False, error=error_msg
                )
                continue
            
            # Show what we're doing
            args_str = ', '.join(f'{k}={v}' for k, v in args.items())
            self.console.print(f"[dim]→ {tool_name}({args_str})[/dim]")
            
            # Add session context for tools that need it
            if tool_name in ['getcontext', 'savesession']:
                args['session_context'] = self.context
            
            # Execute tool with Phase 3.1: Error recovery loop
            result = await self._execute_with_recovery(
                tool, tool_name, args, turn
            )
            
            if not result:
                # Recovery failed completely
                results.append(f"❌ {tool_name} failed after recovery attempts")
                continue
            
            # Format result
            if result.success:
                if tool_name == "read_file":
                    # Show file content with syntax highlighting
                    lang = result.metadata.get("language", "text")
                    syntax = Syntax(str(result.data), lang, theme="monokai", line_numbers=True)
                    self.console.print(syntax)
                    results.append(f"✓ Read {result.metadata['path']} ({result.metadata['lines']} lines)")
                
                elif tool_name in ["write_file", "edit_file"]:
                    results.append(f"✓ {result.data}")
                    if result.metadata.get("backup"):
                        results.append(f"  Backup: {result.metadata['backup']}")
                
                elif tool_name == "search_files":
                    # Show search results as table
                    if result.data:
                        table = Table(title=f"Search Results: '{args['pattern']}'")
                        table.add_column("File", style="cyan")
                        table.add_column("Line", style="yellow", justify="right")
                        table.add_column("Text", style="white")
                        
                        for match in result.data[:10]:  # Show first 10
                            table.add_row(
                                match["file"],
                                str(match["line"]),
                                match["text"][:80]
                            )
                        
                        self.console.print(table)
                        results.append(f"✓ Found {result.metadata['count']} matches")
                    else:
                        results.append("No matches found")
                
                elif tool_name == "bash_command":
                    data = result.data
                    if data.get("stdout"):
                        self.console.print("[dim]stdout:[/dim]")
                        self.console.print(data["stdout"])
                    if data.get("stderr"):
                        self.console.print("[yellow]stderr:[/yellow]")
                        self.console.print(data["stderr"])
                    results.append(f"✓ Exit code: {data['exit_code']}")
                
                elif tool_name == "git_status":
                    data = result.data
                    status_text = f"Branch: {data['branch']}\n"
                    if data['modified']:
                        status_text += f"Modified: {', '.join(data['modified'])}\n"
                    if data['untracked']:
                        status_text += f"Untracked: {', '.join(data['untracked'])}\n"
                    if data['staged']:
                        status_text += f"Staged: {', '.join(data['staged'])}\n"
                    self.console.print(Panel(status_text, title="Git Status", border_style="green"))
                    results.append("✓ Git status retrieved")
                
                elif tool_name == "git_diff":
                    if result.data:
                        self.console.print(Syntax(result.data, "diff", theme="monokai"))
                        results.append("✓ Diff shown")
                    else:
                        results.append("No changes")
                
                elif tool_name == "get_directory_tree":
                    self.console.print(Panel(result.data, title="Directory Tree", border_style="blue"))
                    results.append("✓ Tree shown")
                
                elif tool_name == "list_directory":
                    data = result.data
                    self.console.print(f"[cyan]Directories ({len(data['directories'])}):[/cyan]")
                    for d in data['directories'][:10]:
                        self.console.print(f"  📁 {d['name']}")
                    self.console.print(f"\n[cyan]Files ({len(data['files'])}):[/cyan]")
                    for f in data['files'][:10]:
                        self.console.print(f"  📄 {f['name']} ({f['size']} bytes)")
                    results.append(f"✓ Listed {result.metadata['file_count']} files, {result.metadata['dir_count']} directories")
                
                # Terminal commands
                elif tool_name == "ls":
                    items = result.data
                    for item in items:
                        icon = "📁" if item['type'] == 'dir' else "📄"
                        name = f"[bold cyan]{item['name']}[/bold cyan]" if item['type'] == 'dir' else item['name']
                        if result.metadata.get('long_format'):
                            self.console.print(f"{icon} {name} ({item.get('size', 0)} bytes)")
                        else:
                            self.console.print(f"{icon} {name}")
                    results.append(f"✓ {result.metadata['count']} items")
                
                elif tool_name == "pwd":
                    self.console.print(f"[bold green]{result.data}[/bold green]")
                    results.append("✓ Current directory shown")
                
                elif tool_name == "cd":
                    self.console.print(f"[green]→ {result.metadata['new_cwd']}[/green]")
                    results.append(f"✓ {result.data}")
                
                elif tool_name == "cat":
                    from rich.syntax import Syntax
                    # Try to detect language from file extension
                    path = result.metadata.get('path', '')
                    lang = Path(path).suffix.lstrip('.') or 'text'
                    syntax = Syntax(result.data, lang, theme="monokai", line_numbers=True)
                    self.console.print(syntax)
                    results.append(f"✓ Displayed {result.metadata['lines']} lines")
                
                else:
                    results.append(f"✓ {result.data}")
            else:
                results.append(f"❌ {result.error}")
        
        return "\n".join(results)
    
    async def _handle_system_command(self, cmd: str) -> tuple[bool, Optional[str]]:
        """Handle system commands (/help, /exit, etc.)."""
        cmd = cmd.strip()
        
        if cmd in ["/exit", "/quit"]:
            self.console.print("[yellow]Goodbye! 👋[/yellow]")
            return True, None
        
        elif cmd == "/help":
            help_text = """
[bold]System Commands:[/bold]
  /help     - Show this help
  /exit     - Exit shell
  /tools    - List available tools
  /context  - Show session context
  /clear    - Clear screen

[bold]Natural Language Commands:[/bold]
  Just type what you want to do, e.g.:
  - "read api.py"
  - "search for UserModel in python files"
  - "show git status"
  - "list files in current directory"
"""
            self.console.print(Panel(help_text, title="Help", border_style="yellow"))
            return False, None
        
        elif cmd == "/tools":
            tools = self.registry.get_all()
            table = Table(title="Available Tools")
            table.add_column("Tool", style="cyan")
            table.add_column("Category", style="yellow")
            table.add_column("Description", style="white")
            
            for tool_name, tool in tools.items():
                table.add_row(tool_name, tool.category.value, tool.description)
            
            self.console.print(table)
            return False, None
        
        elif cmd == "/context":
            context_text = f"""
CWD: {self.context.cwd}
Modified files: {len(self.context.modified_files)}
Read files: {len(self.context.read_files)}
Tool calls: {len(self.context.tool_calls)}
"""
            self.console.print(Panel(context_text, title="Session Context", border_style="blue"))
            return False, None
        
        elif cmd == "/clear":
            self.console.clear()
        elif cmd == "/metrics":
            report = generate_constitutional_report(self.context.history)
            self.console.print(report)
            return False, None
        elif cmd == "/cache":
            cache = get_cache()
            stats = cache.get_stats()
            self.console.print(f"\n📊 Cache Stats:\n  Hits: {stats['hits']}\n  Misses: {stats['misses']}\n  Size: {stats['size']}")
            if self.file_watcher:
                wstats = self.file_watcher.get_stats()
                self.console.print(f"\n📁 File Watcher:\n  Tracked: {wstats['tracked_count']}\n  Events: {wstats['event_count']}")
            return False, None
        elif cmd.startswith("/explain "):
            command = cmd[9:].strip()
            explanation = explain_command(command)
            self.console.print(f"\n💡 {explanation}")
            return False, None
            return False, None
        
        elif cmd.startswith("/explain "):
            explanation = explain_command(cmd[9:])
            self.console.print(f"\n💡 {explanation}")
            return False, None
        else:
            return False, f"Unknown command: {cmd}"
    
    def _show_metrics(self) -> None:
        """Show constitutional metrics."""
        self.console.print("\n[bold cyan]📊 Constitutional Metrics[/bold cyan]\n")
        
        metrics = generate_constitutional_report(
            codebase_path="qwen_dev_cli",
            completeness=0.95,
            precision=0.98,
            recall=0.92
        )
        
        self.console.print(metrics.format_report())
    
    def _show_cache_stats(self) -> None:
        """Show cache statistics."""
        cache = get_cache()
        stats = cache.stats
        
        self.console.print("\n[bold cyan]💾 Cache Statistics[/bold cyan]\n")
        self.console.print(f"Hits: {stats.hits}")
        self.console.print(f"Misses: {stats.misses}")
        self.console.print(f"Hit Rate: {stats.hit_rate:.1%}")
        self.console.print(f"Memory Hits: {stats.memory_hits}")
        self.console.print(f"Disk Hits: {stats.disk_hits}")
        
        # File watcher stats
        self.console.print(f"\n[bold cyan]📁 File Watcher[/bold cyan]\n")
        self.console.print(f"Tracked Files: {self.file_watcher.tracked_files}")
        self.console.print(f"Recent Events: {len(self.file_watcher.recent_events)}")
        recent = self.recent_files.get_recent(5)
        if recent:
            self.console.print("\nRecent Files:")
            for f in recent:
                self.console.print(f"  • {f}")
    
    def _on_file_changed(self, event) -> None:
        """Handle file change events."""
        # Add to recent files tracker
        self.recent_files.add(event.path)
        
        # Invalidate cache if needed (files used in context)
        if event.event_type in ['modified', 'deleted']:
            # Could invalidate related cache entries here
            pass
    
    async def _handle_explain(self, command: str) -> None:
        """Explain a command."""
        if not command.strip():
            self.console.print("[yellow]Usage: /explain <command>[/yellow]")
            return
        
        # Build rich context
        context = build_rich_context(
            current_command=command,
            command_history=self.context.history[-10:],
            working_dir="."
        )
        
        # Get explanation
        explanation = explain_command(command, context)
        
        self.console.print(f"\n{explanation.format()}\n")
    
    async def run(self):
        self._show_welcome()
        
        # Initialize suggestion engine
        from .intelligence.engine import SuggestionEngine
        suggestion_engine = SuggestionEngine()
        from .intelligence.patterns import register_builtin_patterns
        register_builtin_patterns(suggestion_engine)
        
        # Start background file watcher task
        async def file_watcher_loop():
            while True:
                self.file_watcher.check_updates()
                await asyncio.sleep(1.0)  # Check every second
        
        watcher_task = asyncio.create_task(file_watcher_loop())
        
        try:
            while True:
                try:
                    # Get user input
                    user_input = await self.session.prompt_async("┃ > ")
                    
                    if not user_input.strip():
                        continue
                    
                    # Build rich context for intelligence features
                    rich_ctx = build_rich_context(
                        current_command=user_input,
                        command_history=self.context.history[-10:],
                        recent_errors=[],
                        working_dir="."
                    )
                
                    # Check risk before execution
                    risk = assess_risk(user_input)
                    if risk.requires_confirmation:
                        warning = get_risk_warning(risk, user_input)
                        self.console.print(f"\n{warning}\n")
                        confirm = input("Continue? [y/N]: ")
                        if confirm.lower() != 'y':
                            continue
                
                    # Handle system commands
                    if user_input.startswith("/"):
                        should_exit, message = await self._handle_system_command(user_input)
                        if message:
                            self.console.print(f"[red]{message}[/red]")
                        if should_exit:
                            break
                        continue
                
                    # Process with tools
                    response = await self._process_tool_calls(user_input)
                
                    if response:
                        # Show response
                        if response.startswith("✓") or response.startswith("❌"):
                            # Tool execution result
                            self.console.print(response)
                        else:
                            # Regular LLM response
                            md = Markdown(response)
                            self.console.print(md)
                    
                        # Show intelligent suggestions after response
                        suggestions = suggestion_engine.generate_suggestions(rich_ctx, max_suggestions=3)
                        if suggestions.suggestions:
                            self.console.print("\n[dim]💡 Suggestions:[/dim]")
                            for i, sugg in enumerate(suggestions.suggestions[:3], 1):
                                self.console.print(f"  {i}. {sugg}")
                            self.console.print()
                
                except KeyboardInterrupt:
                    continue
                except EOFError:
                    break
                except Exception as e:
                    self.console.print(f"[red]Error: {str(e)}[/red]")
        
        finally:
            # Cleanup
            self.file_watcher.stop()
            watcher_task.cancel()
            try:
                await watcher_task
            except asyncio.CancelledError:
                pass


async def main():
    """Entry point for shell."""
    shell = InteractiveShell()
    await shell.run()


if __name__ == "__main__":
    asyncio.run(main())
