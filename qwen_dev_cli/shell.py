"""Interactive shell with tool-based architecture."""

import asyncio
import os
import time
import json
from datetime import datetime
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

# P1: Import error parser and danger detector
from .core.error_parser import error_parser, ErrorAnalysis
from .core.danger_detector import danger_detector, DangerWarning, DangerLevel

# P2: Import enhanced help system
from .core.help_system import help_system

# Import LLM client (using existing implementation)
from .core.async_executor import AsyncExecutor
from .core.file_watcher import FileWatcher
from .core.file_watcher import RecentFilesTracker
from .intelligence.indexer import SemanticIndexer
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

# TUI Components (Phase 5: Integration)
from .tui.components.message import MessageBox, Message, create_assistant_message
from .tui.components.status import StatusBadge, StatusLevel, Spinner, SpinnerStyle, create_processing_indicator
from .tui.components.progress import ProgressBar
from .tui.components.code import CodeBlock, CodeSnippet
from .tui.components.diff import DiffViewer, DiffMode
from .tui.theme import COLORS
from .tui.styles import PRESET_STYLES, get_rich_theme

# Phase 2: Enhanced Input System (DAY 8)
from .tui.input_enhanced import EnhancedInputSession, InputContext
from .tui.history import CommandHistory, HistoryEntry, SessionReplay

# Phase 3: Visual Workflow System (DAY 8)
from .tui.components.workflow_visualizer import WorkflowVisualizer, StepStatus
from .tui.components.execution_timeline import ExecutionTimeline

# Phase 4: Command Palette (Integration Sprint Week 1)
from .tui.components.palette import (
    create_default_palette, CommandPalette, Command, CommandCategory,
    CATEGORY_CONFIG
)

# Phase 5: Animations (Integration Sprint Week 1: Day 3)
from .tui.animations import Animator, AnimationConfig, StateTransition

# Phase 6: Dashboard (Integration Sprint Week 1: Day 3)
from .tui.components.dashboard import Dashboard, Operation, OperationStatus

# Phase 7: Token Tracking (Boris Cherny Foundation)
from .core.token_tracker import TokenTracker


class SessionContext:
    """Persistent context across shell session."""
    
    def __init__(self):
        self.cwd = os.getcwd()
        self.conversation = []
        self.modified_files = set()
        self.read_files = set()
        self.tool_calls = []
        self.history = []
        # Week 2 Integration: Preview settings
        self.preview_enabled = True
    
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
    
    def __init__(self, llm_client=None, session_id: Optional[str] = None, session_state=None):
        # TUI-enhanced console with custom theme
        self.console = Console(theme=get_rich_theme())
        self.llm = llm_client or default_llm_client
        self.context = SessionContext()
        self.context_builder = ContextBuilder()
        
        # P2: Rich context builder
        from .core.context_rich import RichContextBuilder
        self.rich_context = RichContextBuilder()
        
        # P2: Rich context builder
        from .core.context_rich import RichContextBuilder
        self.rich_context = RichContextBuilder()
        
        # Session state management (AIR GAP #2)
        from .session import SessionManager, SessionState
        self.session_manager = SessionManager()
        
        if session_state:
            # Resume existing session
            self.session_state = session_state
            session_id = session_state.session_id
        else:
            # Create new session
            if session_id is None:
                session_id = f"shell_{int(time.time() * 1000)}"
            self.session_state = self.session_manager.create_session(cwd=Path.cwd())
            self.session_state.session_id = session_id
        
        # Phase 2.3: Multi-turn conversation manager
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
        
        # Setup enhanced input session (DAY 8: Phase 2)
        history_file = Path.home() / ".qwen_shell_history"
        self.input_context = InputContext(
            cwd=str(Path.cwd()),
            recent_files=[],
            command_history=[],
            session_data={}
        )
        self.enhanced_input = EnhancedInputSession(
            history_file=history_file,
            context=self.input_context
        )
        
        # Command history with analytics (DAY 8: Phase 2)
        self.cmd_history = CommandHistory()
        self.session_replay = SessionReplay(self.cmd_history)
        
        # Workflow visualization (DAY 8: Phase 3)
        self.workflow_viz = WorkflowVisualizer(console=self.console)
        self.execution_timeline = ExecutionTimeline(console=self.console)
        
        # Command Palette (Integration Sprint Week 1: Day 1)
        self.palette = create_default_palette()
        self._register_palette_commands()
        
        # Token Tracking (Integration Sprint Week 1: Day 1 - Task 1.2 - ACTIVATED)
        self.token_tracker = TokenTracker(
            budget=1000000,  # 1M tokens budget
            cost_per_1k=0.002  # Gemini Pro pricing ($0.002 per 1k tokens)
        )
        
        from .tui.components.context_awareness import ContextAwarenessEngine
        self.context_engine = ContextAwarenessEngine(
            max_context_tokens=100_000,  # 100k token window
            console=self.console
        )
        
        # Animations (Integration Sprint Week 1: Day 3 - Task 1.5)
        self.animator = Animator(AnimationConfig(duration=0.3, easing="ease-out"))
        self.state_transition = StateTransition("idle")
        
        # Dashboard (Integration Sprint Week 1: Day 3 - Task 1.6)
        self.dashboard = Dashboard(console=self.console, max_history=5)
        
        # Legacy session (fallback)
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
        
        # Phase 5: Semantic indexer (Cursor-style intelligence)
        self.indexer = SemanticIndexer(root_path=os.getcwd())
        self.indexer.load_cache()  # Load from cache if available
        self._indexer_initialized = False
    
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
    
    def _register_palette_commands(self):
        """Register commands in command palette (Ctrl+K)."""
        # File operations
        self.palette.add_command(Command(
            id="file.read",
            title="Read File",
            description="Read and display file contents",
            category=CommandCategory.FILE,
            keywords=["open", "cat", "view", "show"],
            keybinding=None,
            action=lambda: self._palette_read_file()
        ))
        
        self.palette.add_command(Command(
            id="file.write",
            title="Write File",
            description="Create or overwrite a file",
            category=CommandCategory.FILE,
            keywords=["create", "save", "new"],
            action=lambda: self._palette_write_file()
        ))
        
        self.palette.add_command(Command(
            id="file.edit",
            title="Edit File",
            description="Edit file with AI assistance",
            category=CommandCategory.EDIT,
            keywords=["modify", "change", "update", "fix"],
            action=lambda: self._palette_edit_file()
        ))
        
        # Git operations
        self.palette.add_command(Command(
            id="git.status",
            title="Git Status",
            description="Show git repository status",
            category=CommandCategory.GIT,
            keywords=["git", "status", "changes", "diff"],
            action=lambda: self._palette_git_status()
        ))
        
        self.palette.add_command(Command(
            id="git.diff",
            title="Git Diff",
            description="Show git diff",
            category=CommandCategory.GIT,
            keywords=["git", "diff", "changes"],
            action=lambda: self._palette_git_diff()
        ))
        
        # Search operations
        self.palette.add_command(Command(
            id="search.files",
            title="Search Files",
            description="Search for text in files",
            category=CommandCategory.SEARCH,
            keywords=["find", "grep", "search", "locate"],
            action=lambda: self._palette_search_files()
        ))
        
        # Help & System
        self.palette.add_command(Command(
            id="help.main",
            title="Help",
            description="Show main help",
            category=CommandCategory.HELP,
            keywords=["help", "docs", "guide"],
            keybinding="?",
            action=lambda: help_system.show_main_help()
        ))
        
        self.palette.add_command(Command(
            id="system.clear",
            title="Clear Screen",
            description="Clear the terminal screen",
            category=CommandCategory.SYSTEM,
            keywords=["clear", "cls", "clean"],
            action=lambda: os.system('clear')
        ))
        
        # Tools commands
        self.palette.add_command(Command(
            id="tools.list",
            title="List Available Tools",
            description="Show all registered tools",
            category=CommandCategory.TOOLS,
            keywords=["tools", "list", "available"],
            action=lambda: self._palette_list_tools()
        ))
    
    def _show_welcome(self):
        """Show welcome message with TUI styling."""
        from rich.text import Text
        
        # Build styled welcome content
        content = Text()
        content.append("QWEN-DEV-CLI Interactive Shell ", style=PRESET_STYLES.EMPHASIS)
        content.append("v1.0", style=PRESET_STYLES.SUCCESS)
        content.append("\n\n")
        content.append(f"🔧 Tools available: ", style=PRESET_STYLES.SECONDARY)
        content.append(f"{len(self.registry.get_all())}\n", style=PRESET_STYLES.INFO)
        content.append(f"📁 Working directory: ", style=PRESET_STYLES.SECONDARY)
        content.append(f"{self.context.cwd}\n\n", style=PRESET_STYLES.PATH)
        content.append("Type natural language commands or ", style=PRESET_STYLES.TERTIARY)
        content.append("/help", style=PRESET_STYLES.COMMAND)
        content.append(" for system commands", style=PRESET_STYLES.TERTIARY)
        
        welcome = Panel(
            content,
            title="[bold]🚀 AI-Powered Code Shell[/bold]",
            border_style=COLORS['accent_blue'],
            padding=(1, 2)
        )
        self.console.print(welcome)
    
    async def _execute_with_recovery(
        self,
        tool,
        tool_name: str,
        args: Dict[str, Any],
        turn
    ):
        """Execute tool with error recovery (refactored for SRP)."""
        max_attempts = self.recovery_engine.max_attempts
        
        for attempt in range(1, max_attempts + 1):
            result, success = await self._attempt_tool_execution(
                tool, tool_name, args, turn, attempt
            )
            
            if success:
                if attempt > 1:
                    self.console.print(f"[green]✓ Recovered on attempt {attempt}[/green]")
                return result
            
            # Try recovery if not last attempt
            if attempt < max_attempts:
                corrected_args = await self._handle_execution_failure(
                    tool_name, args, result, turn, attempt, max_attempts
                )
                if corrected_args:
                    args = corrected_args
            else:
                self.console.print(f"[red]✗ {tool_name} failed after {max_attempts} attempts[/red]")
                return None
        
        return None

    async def _attempt_tool_execution(
        self, tool, tool_name: str, args: Dict[str, Any], turn, attempt: int
    ):
        """Execute single tool attempt and track result."""
        try:
            result = await tool.execute(**args)
            
            # Track tool call
            self.context.track_tool_call(tool_name, args, result)
            
            # Track in conversation
            self.conversation.add_tool_result(
                turn, tool_name, args, result,
                success=result.success,
                error=None if result.success else str(result.data)
            )
            
            return result, result.success
            
        except Exception as e:
            logger.error(f"Tool {tool_name} raised exception: {e}")
            
            # Track exception
            self.conversation.add_tool_result(
                turn, tool_name, args, None,
                success=False,
                error=str(e)
            )
            
            # Create error result
            from dataclasses import dataclass
            @dataclass
            class ErrorResult:
                success: bool = False
                data: str = str(e)
            
            return ErrorResult(), False

    async def _handle_execution_failure(
        self, tool_name: str, args: Dict[str, Any], result, turn, 
        attempt: int, max_attempts: int
    ):
        """Handle tool execution failure and attempt recovery."""
        error_msg = str(result.data) if result else "Unknown error"
        
        self.console.print(
            f"[yellow]Attempting recovery for {tool_name} (attempt {attempt}/{max_attempts})[/yellow]"
        )
        
        try:
            # Build recovery context
            recovery_ctx = create_recovery_context(
                error=error_msg,
                tool_name=tool_name,
                args=args,
                category=ErrorCategory.PARAMETER_ERROR
            )
            
            # Get diagnosis from LLM
            diagnosis = await self.recovery_engine.diagnose_error(
                recovery_ctx, self.conversation.get_recent_context(max_turns=3)
            )
            
            if diagnosis:
                self.console.print(f"[dim]Diagnosis: {diagnosis}[/dim]")
            
            # Attempt parameter correction
            corrected = await self.recovery_engine.attempt_recovery(
                recovery_ctx, self.registry
            )
            
            if corrected and 'args' in corrected:
                self.console.print("[green]✓ Generated corrected parameters[/green]")
                return corrected['args']
            else:
                self.console.print("[yellow]No correction found[/yellow]")
                return None
                
        except Exception as e:
            logger.error(f"Recovery failed: {e}")
            self.console.print(f"[red]Recovery error: {e}[/red]")
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
            except (json.JSONDecodeError, ValueError) as e:
                logger.debug(f"Response is not tool calls JSON: {e}")
            
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
        
        # Week 2 Integration: Initialize workflow for tool execution
        if len(tool_calls) > 1:
            self.workflow_viz.start_workflow(f"Execute {len(tool_calls)} tools")
        
        for i, call in enumerate(tool_calls):
            tool_name = call.get("tool", "")
            args = call.get("args", {})
            
            # Week 2 Integration: Add workflow step for this tool
            step_id = f"tool_{tool_name}_{i}"
            dependencies = [f"tool_{tool_calls[i-1].get('tool', '')}_{i-1}"] if i > 0 else []
            self.workflow_viz.add_step(
                step_id,
                f"Execute {tool_name}",
                StepStatus.PENDING,
                dependencies=dependencies
            )
            
            tool = self.registry.get(tool_name)
            if not tool:
                error_msg = f"Unknown tool: {tool_name}"
                results.append(f"❌ {error_msg}")
                
                # Week 2 Integration: Mark step as failed
                self.workflow_viz.update_step_status(step_id, StepStatus.FAILED)
                
                # Phase 2.3: Track tool failure
                self.conversation.add_tool_result(
                    turn, tool_name, args, None, 
                    success=False, error=error_msg
                )
                continue
            
            # Week 2 Integration: Start executing step
            self.workflow_viz.update_step_status(step_id, StepStatus.RUNNING)
            
            # Week 2 Day 2: Add operation to dashboard
            op_id = f"{tool_name}_{i}_{int(time.time() * 1000)}"
            operation = Operation(
                id=op_id,
                type=tool_name,
                description=f"{tool_name}({', '.join(f'{k}={v}' for k, v in list(args.items())[:2])})",
                status=OperationStatus.RUNNING
            )
            self.dashboard.add_operation(operation)
            
            # TUI: Show status badge for operation
            args_str = ', '.join(f'{k}={v}' for k, v in args.items() if len(str(v)) < 50)
            status = StatusBadge(f"{tool_name}({args_str})", StatusLevel.PROCESSING, show_icon=True)
            self.console.print(status.render())
            
            # Add session context for tools that need it
            if tool_name in ['getcontext', 'savesession']:
                args['session_context'] = self.context
            
            # Week 2 Integration: Pass console and preview settings to file tools
            if tool_name in ['write_file', 'edit_file']:
                args['console'] = self.console
                args['preview'] = getattr(self.context, 'preview_enabled', True)
            
            # Execute tool with Phase 3.1: Error recovery loop
            result = await self._execute_with_recovery(
                tool, tool_name, args, turn
            )
            
            if not result:
                # Recovery failed completely
                results.append(f"❌ {tool_name} failed after recovery attempts")
                # Week 2 Integration: Mark as failed
                self.workflow_viz.update_step_status(step_id, StepStatus.FAILED)
                # Week 2 Day 2: Update dashboard
                self.dashboard.complete_operation(op_id, OperationStatus.ERROR)
                continue
            
            # Week 2 Integration: Mark step completion based on result
            if result.success:
                self.workflow_viz.update_step_status(step_id, StepStatus.COMPLETED)
                # Week 2 Day 2: Update dashboard with success
                self.dashboard.complete_operation(
                    op_id,
                    OperationStatus.SUCCESS,
                    tokens_used=result.metadata.get('tokens', 0),
                    cost=result.metadata.get('cost', 0.0)
                )
            else:
                self.workflow_viz.update_step_status(step_id, StepStatus.FAILED)
                # Week 2 Day 2: Update dashboard with error
                self.dashboard.complete_operation(op_id, OperationStatus.ERROR)
            
            # Format result
            if result.success:
                if tool_name == "read_file":
                    # TUI: Enhanced code block with language badge
                    lang = result.metadata.get("language", "text")
                    code_block = CodeBlock(
                        str(result.data),
                        language=lang,
                        show_line_numbers=True,
                        show_language=True,
                        copyable=True
                    )
                    self.console.print(code_block.render())
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
                        # TUI: GitHub-style diff viewer
                        # Parse diff to extract old/new content (simplified for now)
                        diff_viewer = DiffViewer("", result.data, "Working Copy", "Uncommitted")
                        self.console.print(Panel(
                            Syntax(result.data, "diff", theme="monokai"),
                            title="[bold]Git Diff[/bold]",
                            border_style=COLORS['accent_blue']
                        ))
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
        
        # Week 2 Integration: Complete workflow and show visualization
        if len(tool_calls) > 1:
            self.workflow_viz.complete_workflow()
            # Show workflow visualization if any step failed
            if any(step.status == StepStatus.FAILED for step in self.workflow_viz.current_workflow.steps):
                viz = self.workflow_viz.render_workflow()
                self.console.print("\n")
                self.console.print(viz)
        
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
  /help       - Show this help
  /exit       - Exit shell
  /tools      - List available tools
  /context    - Show session context
  /clear      - Clear screen
  /metrics    - Show constitutional metrics
  /cache      - Show cache statistics
  /tokens     - Show token usage & budget 💰
  /workflow   - Show workflow visualization 🔄
  /dash       - Show operations dashboard 📊
  /preview    - Enable file preview (default) 👁️
  /nopreview  - Disable file preview ⚡

[bold]History & Analytics:[/bold] 🆕
  /history    - Show command history
  /stats      - Show usage statistics
  /sessions   - List previous sessions

[bold]Cursor-style Intelligence:[/bold]
  /index      - Index codebase (Cursor magic!)
  /find NAME  - Search symbols by name
  /explain X  - Explain command/concept

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
            return False, None
        
        # DAY 8: History commands
        elif cmd == "/history":
            entries = self.cmd_history.get_recent(limit=20)
            if not entries:
                self.console.print("[dim]No command history yet.[/dim]")
                return False, None
            
            table = Table(title="Command History (Last 20)")
            table.add_column("#", style="dim", width=4)
            table.add_column("Time", style="cyan", width=10)
            table.add_column("Command", style="white")
            table.add_column("Status", style="green", width=8)
            table.add_column("Duration", style="yellow", width=10)
            
            for i, entry in enumerate(reversed(entries), 1):
                status = "✓ OK" if entry.success else "✗ FAIL"
                status_style = "green" if entry.success else "red"
                time_str = entry.timestamp.split('T')[1][:8]
                cmd_preview = entry.command[:60] + "..." if len(entry.command) > 60 else entry.command
                
                table.add_row(
                    str(i),
                    time_str,
                    cmd_preview,
                    f"[{status_style}]{status}[/{status_style}]",
                    f"{entry.duration_ms}ms"
                )
            
            self.console.print(table)
            return False, None
        
        elif cmd == "/stats":
            stats = self.cmd_history.get_statistics(days=7)
            
            self.console.print("\n[bold cyan]📊 Command Statistics (Last 7 Days)[/bold cyan]\n")
            self.console.print(f"  Total commands: [bold]{stats['total_commands']}[/bold]")
            self.console.print(f"  Success rate:   [bold green]{stats['success_rate']}%[/bold green]")
            self.console.print(f"  Avg duration:   [yellow]{stats['avg_duration_ms']}ms[/yellow]")
            self.console.print(f"  Total tokens:   [cyan]{stats['total_tokens']:,}[/cyan]")
            
            if stats['top_commands']:
                self.console.print("\n[bold]Top Commands:[/bold]")
                for cmd_stat in stats['top_commands'][:5]:
                    cmd_preview = cmd_stat['command'][:50]
                    self.console.print(f"  • {cmd_preview}: [bold]{cmd_stat['count']}[/bold] times")
            
            return False, None
        
        elif cmd == "/sessions":
            sessions = self.session_replay.list_sessions(limit=10)
            if not sessions:
                self.console.print("[dim]No previous sessions found.[/dim]")
                return False, None
            
            table = Table(title="Recent Sessions")
            table.add_column("Session ID", style="cyan")
            table.add_column("Start Time", style="yellow")
            table.add_column("Commands", style="white", width=10)
            table.add_column("Tokens", style="magenta", width=10)
            table.add_column("Files", style="green", width=8)
            
            for session in sessions:
                start_time = session['start_time'].split('T')[0]
                table.add_row(
                    session['session_id'][:20] + "...",
                    start_time,
                    str(session['command_count']),
                    f"{session['total_tokens']:,}",
                    str(len(session['files_modified']))
                )
            
            self.console.print(table)
            return False, None
        
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
        
        elif cmd == "/index":
            # Phase 5: Semantic indexer
            self.console.print("[cyan]🔍 Indexing codebase...[/cyan]")
            import time
            start = time.time()
            count = self.indexer.index_codebase(force=True)
            elapsed = time.time() - start
            
            stats = self.indexer.get_stats()
            
            self.console.print(f"[green]✓ Indexed {count} files in {elapsed:.2f}s[/green]")
            self.console.print(f"  Total symbols: {stats['total_symbols']}")
            self.console.print(f"  Unique names:  {stats['unique_symbols']}")
            self._indexer_initialized = True
            return False, None
        
        elif cmd.startswith("/find "):
            # Phase 5: Symbol search
            query = cmd[6:].strip()
            
            if not self._indexer_initialized:
                self.console.print("[yellow]⚠ Index not initialized. Run /index first.[/yellow]")
                return False, None
            
            results = self.indexer.search_symbols(query, limit=10)
            
            if not results:
                self.console.print(f"[dim]No symbols found for: {query}[/dim]")
                return False, None
            
            self.console.print(f"\n[bold]Found {len(results)} symbols:[/bold]\n")
            for symbol in results:
                type_style = "green" if symbol.type == "class" else "blue"
                self.console.print(
                    f"  [{type_style}]{symbol.name}[/{type_style}] "
                    f"[dim]({symbol.type})[/dim] "
                    f"[yellow]{symbol.file_path}:{symbol.line_number}[/yellow]"
                )
                if symbol.docstring:
                    doc_preview = symbol.docstring.split('\n')[0][:60]
                    self.console.print(f"    [dim]→ {doc_preview}...[/dim]")
            
            return False, None
        
        elif cmd == "/workflow":
            # Workflow Visualizer (Task 1.4)
            if self.workflow_viz.current_workflow:
                viz = self.workflow_viz.render_workflow()
                self.console.print(viz)
            else:
                self.console.print("[dim]No active workflow. Execute a command to see workflow.[/dim]")
            return False, None
        
        elif cmd == "/dash" or cmd == "/dashboard":
            # Dashboard (Week 2 Day 2: Auto-updating dashboard)
            dashboard_view = self.dashboard.render()
            self.console.print(dashboard_view)
            return False, None
        
        elif cmd == "/preview":
            # Week 2 Integration: Enable preview
            self.context.preview_enabled = True
            return False, "[green]✓ Preview enabled for file operations[/green]"
        
        elif cmd == "/nopreview":
            # Week 2 Integration: Disable preview
            self.context.preview_enabled = False
            return False, "[yellow]⚠ Preview disabled. Files will be written directly.[/yellow]"
        
        elif cmd == "/tokens":
            # Token Tracking (Integration Sprint Week 1: Day 1 - Task 1.2)
            # Show detailed token usage
            token_panel = self.context_engine.render_token_usage_realtime()
            self.console.print(token_panel)
            
            # Show token usage history
            if self.context_engine.window.usage_history:
                history_table = Table(title="Token Usage History (Last 10 Interactions)")
                history_table.add_column("Time", style="cyan", width=10)
                history_table.add_column("Input", justify="right", width=10)
                history_table.add_column("Output", justify="right", width=10)
                history_table.add_column("Total", justify="right", width=10)
                history_table.add_column("Cost", justify="right", width=10)
                
                for snapshot in list(self.context_engine.window.usage_history)[-10:]:
                    history_table.add_row(
                        snapshot.timestamp.strftime("%H:%M:%S"),
                        f"{snapshot.input_tokens:,}",
                        f"{snapshot.output_tokens:,}",
                        f"{snapshot.total_tokens:,}",
                        f"${snapshot.cost_estimate_usd:.4f}"
                    )
                
                self.console.print(history_table)
            else:
                self.console.print("\n[dim]No token usage history yet. Start a conversation to track tokens.[/dim]")
            
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
            # Cache invalidation deferred - would require cache key tracking
            logger.debug(f"File {event.path} {event.event_type} - cache invalidation not yet implemented")
    
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
    
    # Command Palette Helper Methods (Integration Sprint Week 1)
    
    async def _palette_read_file(self):
        """Read file action from palette."""
        file_path = await self.enhanced_input.prompt_async("File path: ")
        if file_path:
            await self._process_request_with_llm(f"read {file_path}", None)
    
    async def _palette_write_file(self):
        """Write file action from palette."""
        file_path = await self.enhanced_input.prompt_async("File path: ")
        if file_path:
            content = await self.enhanced_input.prompt_async("Content: ")
            if content:
                await self._process_request_with_llm(f"write {file_path} with: {content}", None)
    
    async def _palette_edit_file(self):
        """Edit file action from palette."""
        file_path = await self.enhanced_input.prompt_async("File path: ")
        if file_path:
            instruction = await self.enhanced_input.prompt_async("Edit instruction: ")
            if instruction:
                await self._process_request_with_llm(f"edit {file_path}: {instruction}", None)
    
    async def _palette_git_status(self):
        """Git status action from palette."""
        tool = self.registry.get("git_status")
        result = await tool.execute()
        self.console.print(result.data.get("output", ""))
    
    async def _palette_git_diff(self):
        """Git diff action from palette."""
        tool = self.registry.get("git_diff")
        result = await tool.execute()
        self.console.print(result.data.get("output", ""))
    
    async def _palette_search_files(self):
        """Search files action from palette."""
        pattern = await self.enhanced_input.prompt_async("Search pattern: ")
        if pattern:
            await self._process_request_with_llm(f"search for {pattern}", None)
    
    def _palette_list_tools(self):
        """List tools action from palette."""
        tools = self.registry.list_tools()
        table = Table(title="Available Tools")
        table.add_column("Tool", style="cyan")
        table.add_column("Description", style="white")
        
        for tool_name in tools:
            tool = self.registry.get(tool_name)
            table.add_row(tool_name, tool.description if hasattr(tool, 'description') else "")
        
        self.console.print(table)
    
    async def _show_palette_interactive(self) -> Optional[Command]:
        """Show interactive palette and return selected command."""
        # Show search prompt
        query = await self.enhanced_input.prompt_async("[cyan]Command Palette >[/cyan] ")
        
        if not query or not query.strip():
            return None
        
        # Fuzzy search
        results = self.palette.search(query, limit=10)
        
        if not results:
            self.console.print("[yellow]No commands found[/yellow]")
            return None
        
        # Display results
        self.console.print("\n[cyan]Results:[/cyan]")
        for i, cmd in enumerate(results, 1):
            category_icon = CATEGORY_CONFIG.get(cmd.category, {}).get('icon', '📄')
            self.console.print(f"  {i}. {category_icon} {cmd.title} - [dim]{cmd.description}[/dim]")
        
        # Get selection
        try:
            selection = await self.enhanced_input.prompt_async("\nSelect (1-10) or Enter to cancel: ")
            if selection and selection.isdigit():
                idx = int(selection) - 1
                if 0 <= idx < len(results):
                    return results[idx]
        except (ValueError, IndexError):
            pass
        
        return None
    
    async def run(self):
        """Interactive REPL with Cursor+Claude+Gemini best practices."""
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
                await asyncio.sleep(1.0)
        
        watcher_task = asyncio.create_task(file_watcher_loop())
        
        try:
            while True:
                try:
                    # [IDLE] Get user input (DAY 8: Enhanced input)
                    start_time = time.time()
                    user_input = await self.enhanced_input.prompt_async()
                    
                    # Handle Command Palette (Ctrl+K) - Integration Sprint Week 1
                    if user_input == "__PALETTE__":
                        self.console.print("\n[cyan]✨ Command Palette[/cyan]\n")
                        
                        # Show palette interactively
                        selected = await self._show_palette_interactive()
                        
                        if selected:
                            try:
                                self.console.print(f"\n[dim]Executing: {selected.title}[/dim]\n")
                                # Execute command action
                                result = selected.action()
                                if asyncio.iscoroutine(result):
                                    await result
                            except Exception as e:
                                self.console.print(f"[red]Error executing command: {e}[/red]")
                        
                        continue
                    
                    # Handle empty input or Ctrl+D
                    if user_input is None or not user_input.strip():
                        if user_input is None:  # Ctrl+D
                            self.console.print("[cyan]👋 Goodbye![/cyan]")
                            break
                        continue
                    
                    # Handle system commands (quit, help, etc)
                    if user_input.strip().lower() in ['quit', 'exit', 'q']:
                        self.console.print("[cyan]👋 Goodbye![/cyan]")
                        break
                    elif user_input.strip().lower() == 'help':
                        # P2: Enhanced help system
                        help_system.show_main_help()
                        continue
                    elif user_input.strip().lower().startswith('help '):
                        # P2: Topic-specific help
                        topic = user_input.strip()[5:].strip()
                        if topic == 'examples':
                            help_system.show_examples()
                        else:
                            help_system.show_examples(topic)
                        continue
                    elif user_input.strip().lower() == '/tutorial':
                        # P2: Interactive tutorial
                        help_system.show_tutorial()
                        continue
                    elif user_input.strip().lower().startswith('/explain '):
                        # P2: Command explanation
                        command = user_input.strip()[9:].strip()
                        explanation = help_system.explain_command(command)
                        self.console.print(explanation)
                        continue
                    elif user_input.startswith("/"):
                        should_exit, message = await self._handle_system_command(user_input)
                        if message:
                            self.console.print(message)
                        if should_exit:
                            break
                        continue
                    
                    # [THINKING] Process request with LLM
                    success = True
                    try:
                        # Start workflow visualization (Task 1.4)
                        self.workflow_viz.start_workflow("Process User Request")
                        self.workflow_viz.add_step("parse_input", "Parsing user input", StepStatus.RUNNING)
                        
                        await self._process_request_with_llm(user_input, suggestion_engine)
                        
                        # Complete workflow
                        self.workflow_viz.update_step_status("parse_input", StepStatus.COMPLETED)
                        self.workflow_viz.complete_workflow()
                        
                        # Show token usage after LLM response (Integration Sprint Week 1: Task 1.2)
                        if self.context_engine.window.current_output_tokens > 0:
                            token_panel = self.context_engine.render_token_usage_realtime()
                            self.console.print(token_panel)
                            
                            # Warning if approaching limit
                            usage_percent = (self.context_engine.window.total_tokens / 
                                           self.context_engine.max_context_tokens * 100)
                            
                            if usage_percent >= 90:
                                self.console.print(
                                    "\n[bold red]⚠️  WARNING: Context window >90% full![/bold red]"
                                )
                                self.console.print(
                                    "[yellow]Consider using /clear to reset context[/yellow]\n"
                                )
                            elif usage_percent >= 80:
                                self.console.print(
                                    "\n[yellow]⚠️  Context window >80% full[/yellow]\n"
                                )
                    
                    except Exception as proc_error:
                        success = False
                        raise proc_error
                    finally:
                        # Track command in history (DAY 8: Phase 2)
                        duration_ms = int((time.time() - start_time) * 1000)
                        history_entry = HistoryEntry(
                            timestamp=datetime.now().isoformat(),
                            command=user_input[:200],  # Limit to 200 chars
                            cwd=str(Path.cwd()),
                            success=success,
                            duration_ms=duration_ms,
                            tokens_used=0,  # Will be updated later
                            tool_calls=len(self.context.tool_calls),
                            files_modified=list(self.context.modified_files),
                            session_id=self.session_state.session_id
                        )
                        self.cmd_history.add(history_entry)
                        
                        # Update input context
                        self.enhanced_input.update_context(
                            cwd=str(Path.cwd()),
                            recent_files=list(self.recent_files.get_recent()),
                            command_history=self.cmd_history.get_recent(limit=10)
                        )
                
                except KeyboardInterrupt:
                    self.console.print("\n[dim]Use 'quit' to exit[/dim]")
                    continue
                except EOFError:
                    break
                except Exception as e:
                    # Claude pattern: Never crash, specific error handling
                    await self._handle_error(e, user_input)
        
        finally:
            # Auto-save session on exit (AIR GAP #2)
            try:
                self.session_manager.save_session(self.session_state)
                self.console.print(f"[dim]💾 Session auto-saved: {self.session_state.session_id}[/dim]")
            except Exception as e:
                logger.warning(f"Failed to auto-save session: {e}")
            
            # Cleanup
            self.file_watcher.stop()
            watcher_task.cancel()
            try:
                await watcher_task
            except asyncio.CancelledError:
                logger.debug("File watcher task cancelled successfully")
    
    async def _process_request_with_llm(self, user_input: str, suggestion_engine):
        """
        Process user request with LLM using Cursor+Claude+Gemini patterns.
        
        Cursor: Multi-step breakdown with visual feedback
        Claude: Explicit state machine + tiered safety
        Gemini: Visual hierarchy + typography
        """
        import time
        
        # Track user message in session (AIR GAP #2)
        self.session_state.add_message("user", user_input)
        
        # P2: Build rich context (enhanced)
        context_dict = self.rich_context.build_rich_context(
            include_git=True,
            include_env=True,
            include_recent=True
        )
        
        # Old format for compatibility
        rich_ctx = build_rich_context(
            current_command=user_input,
            command_history=self.context.history[-10:],
            recent_errors=[],
            working_dir=os.getcwd()
        )
        
        # Step 1/3: Analyze request (Cursor: multi-step breakdown)
        self.state_transition.transition_to("thinking")
        self.workflow_viz.add_step("analyze", "Analyzing request", StepStatus.RUNNING)
        
        # Track operation in dashboard (Task 1.6)
        op_id = f"llm_{int(time.time() * 1000)}"
        operation = Operation(
            id=op_id,
            type="llm",
            description=f"Process: {user_input[:40]}...",
            status=OperationStatus.RUNNING
        )
        self.dashboard.add_operation(operation)
        
        # Animated status message (Task 1.5)
        from rich.text import Text
        text = Text("[THINKING] Step 1/3: Analyzing request...", style="cyan")
        self.console.print(text)
        start_time = time.time()
        
        # Get LLM suggestion
        try:
            suggestion = await self._get_command_suggestion(user_input, rich_ctx)
            self.workflow_viz.update_step_status("analyze", StepStatus.COMPLETED)
        except Exception as e:
            self.workflow_viz.update_step_status("analyze", StepStatus.FAILED)
            self.console.print(f"[red]❌ LLM failed: {e}[/red]")
            self.console.print("[yellow]💡 Tip: Check your API key (HF_TOKEN)[/yellow]")
            return
        
        elapsed = time.time() - start_time
        self.console.print(f"[cyan][THINKING][/cyan] Step 2/3: Command ready [dim]({elapsed:.1f}s)[/dim] ✓")
        
        # Step 3/3: Show suggestion (Gemini: visual hierarchy)
        self.console.print()
        self.console.print(f"[dim]You:[/dim] {user_input}")
        self.console.print()
        self.console.print("[bold]💡 Suggested action:[/bold]")
        self.console.print(f"   [cyan]{suggestion}[/cyan]")
        self.console.print()
        
        # P1: Danger detection with visual warnings
        self.workflow_viz.add_step("safety", "Safety check", StepStatus.RUNNING)
        danger_warning = danger_detector.analyze(suggestion)
        
        if danger_warning:
            self.workflow_viz.update_step_status("safety", StepStatus.WARNING)
            # Show rich visual warning
            warning_panel = danger_detector.get_visual_warning(danger_warning)
            self.console.print(warning_panel)
            self.console.print()
            
            # Get appropriate confirmation prompt
            prompt_text = danger_detector.format_confirmation_prompt(danger_warning, suggestion)
            self.console.print(prompt_text, end="")
            
            user_confirmation = input()
            
            # Validate confirmation
            if not danger_detector.validate_confirmation(danger_warning, user_confirmation, suggestion):
                self.console.print("[yellow]❌ Cancelled - confirmation failed[/yellow]")
                return
            
            self.console.print("[green]✓ Confirmation accepted[/green]")
        else:
            # Old safety system as fallback
            risk = assess_risk(suggestion)
            safety_level = self._get_safety_level(suggestion)
            
            if safety_level == 2:  # Dangerous (fallback for old system)
                self.console.print("[red]⚠️  DANGEROUS COMMAND[/red]")
                self.console.print(f"[yellow]This will: {risk.description}[/yellow]")
                confirm = input("Type command name to confirm: ").strip()
                if confirm != suggestion.split()[0]:
                    self.console.print("[yellow]Cancelled[/yellow]")
                    return
            elif safety_level == 1:  # Needs confirmation
                self.console.print("[yellow]⚠️  Requires confirmation[/yellow]")
                confirm = input("Execute? [y/N] ").strip().lower()
                if confirm not in ['y', 'yes']:
                    self.console.print("[dim]Cancelled[/dim]")
                    return
            else:  # Safe
                self.console.print("[green]✓ Safe command[/green]")
                confirm = input("Execute? [Y/n] ").strip().lower()
                if not confirm:  # Default yes for safe commands
                    confirm = 'y'
                if confirm not in ['y', 'yes']:
                    self.console.print("[dim]Cancelled[/dim]")
                    return
        
        # [EXECUTING] Run command
        self.state_transition.transition_to("executing")
        self.workflow_viz.update_step_status("safety", StepStatus.COMPLETED)
        self.workflow_viz.add_step("execute", "Executing command", StepStatus.RUNNING)
        
        # Animated status message (Task 1.5)
        text = Text("[EXECUTING] Running command...", style="cyan")
        self.console.print(text)
        self.console.print()
        
        try:
            result = await self._execute_command(suggestion)
            
            # Show result
            if result.get('success'):
                self.state_transition.transition_to("success")
                self.workflow_viz.update_step_status("execute", StepStatus.COMPLETED)
                
                # Complete dashboard operation (Task 1.6)
                self.dashboard.complete_operation(op_id, OperationStatus.SUCCESS, tokens_used=0, cost=0.0)
                
                # Animated success message (Task 1.5)
                text = Text("✓ Success", style="green bold")
                self.console.print(text)
                if result.get('output'):
                    self.console.print(result['output'])
                
                # Track assistant response in session (AIR GAP #2)
                response = f"Executed: {suggestion}\nOutput: {result.get('output', '')[:200]}"
                self.session_state.add_message("assistant", response)
                self.session_state.increment_tool_calls()
            else:
                self.state_transition.transition_to("error")
                self.workflow_viz.update_step_status("execute", StepStatus.FAILED)
                
                # Complete dashboard operation as error (Task 1.6)
                self.dashboard.complete_operation(op_id, OperationStatus.ERROR)
                
                # Animated error message (Task 1.5)
                text = Text("❌ Failed", style="red bold")
                self.console.print(text)
                
                # P1: Intelligent error parsing
                if result.get('error'):
                    error_text = result['error']
                    self.console.print(f"[red]{error_text}[/red]")
                    self.console.print()
                    
                    # Parse error and show suggestions
                    analysis = error_parser.parse(error_text, suggestion)
                    
                    # Show user-friendly message
                    self.console.print(f"[yellow]💡 {analysis.user_friendly}[/yellow]")
                    self.console.print()
                    
                    # Show suggestions
                    if analysis.suggestions:
                        self.console.print("[bold]Suggestions:[/bold]")
                        for i, sug in enumerate(analysis.suggestions[:3], 1):
                            self.console.print(f"  {i}. [cyan]{sug}[/cyan]")
                        self.console.print()
                    
                    # Show auto-fix if available
                    if analysis.can_auto_fix and analysis.auto_fix_command:
                        self.console.print(f"[green]Auto-fix: {analysis.auto_fix_command}[/green]")
                        fix = input("Run auto-fix? [y/N] ").strip().lower()
                        if fix == 'y':
                            fix_result = await self._execute_command(analysis.auto_fix_command)
                            if fix_result['success']:
                                self.console.print("[green]✓ Auto-fix completed[/green]")
                                if fix_result['output']:
                                    self.console.print(fix_result['output'])
        
        except Exception as e:
            self.console.print(f"[red]❌ Execution failed: {e}[/red]")
        
        # Add to history
        self.context.history.append(user_input)
    
    async def _get_command_suggestion(self, user_request: str, context: dict) -> str:
        """Get command suggestion from LLM."""
        if not self.llm:
            # Fallback: basic regex parsing (Claude: graceful degradation)
            return self._fallback_suggest(user_request)
        
        # P2: Build prompt with RICH context (Cursor: context injection)
        rich_context = self.rich_context.build_rich_context()
        context_str = self.rich_context.format_context_for_llm(rich_context)
        
        prompt = f"""User request: {user_request}

{context_str}

Suggest ONE shell command to accomplish this task.
Output ONLY the command, no explanation, no markdown."""
        
        # Call LLM with error handling
        try:
            response = await self.llm.generate(prompt)
            
            # Handle None or empty response
            if not response:
                return self._fallback_suggest(user_request)
            
            # Parse command from response
            command = self._extract_command(response)
            return command
        
        except Exception as e:
            # Any LLM error: fallback gracefully
            self.console.print(f"[yellow]⚠️  LLM unavailable, using fallback[/yellow]")
            return self._fallback_suggest(user_request)
    
    def _fallback_suggest(self, user_request: str) -> str:
        """Fallback suggestion using regex (when LLM unavailable)."""
        req_lower = user_request.lower()
        
        # Simple pattern matching
        if 'large file' in req_lower or 'big file' in req_lower:
            return "find . -type f -size +100M"
        elif 'process' in req_lower and 'memory' in req_lower:
            return "ps aux --sort=-%mem | head -10"
        elif 'disk' in req_lower and ('space' in req_lower or 'usage' in req_lower):
            return "df -h"
        elif 'list' in req_lower and 'file' in req_lower:
            return "ls -lah"
        else:
            # Truncate huge inputs to prevent memory issues
            max_display = 100
            truncated = user_request[:max_display] + "..." if len(user_request) > max_display else user_request
            return f"# Could not parse: {truncated}"
    
    def _extract_command(self, llm_response: str) -> str:
        """Extract command from LLM response."""
        # Handle None or non-string
        if not llm_response or not isinstance(llm_response, str):
            return "# Could not extract command"
        
        # Remove markdown code blocks
        import re
        code_block = re.search(r'```(?:bash|sh)?\s*\n?(.*?)\n?```', llm_response, re.DOTALL)
        if code_block:
            return code_block.group(1).strip()
        
        # Remove common prefixes
        lines = llm_response.strip().split('\n')
        for line in lines:
            line = line.strip()
            if line and not line.startswith('#'):
                # Remove shell prompt prefix if present
                if line.startswith('$'):
                    line = line[1:].strip()
                if line:  # Only return if there's content after stripping
                    return line
        
        return llm_response.strip() if llm_response else "# Empty response"
    
    def _get_safety_level(self, command: str) -> int:
        """
        Get safety level (Claude pattern: tiered confirmations).
        
        Level 0: Safe (auto-execute with default yes)
        Level 1: Confirm once (standard operations)
        Level 2: Dangerous (double confirmation)
        """
        if not command:
            return 1
            
        LEVEL_0_SAFE = {'ls', 'pwd', 'echo', 'cat', 'head', 'tail', 'grep', 'find', 'df', 'du', 'ps', 'top'}
        LEVEL_2_DANGEROUS = {'rm', 'rmdir', 'dd', 'mkfs', 'fdisk', 'format', ':(){:|:&};:'}
        
        # Check for dangerous commands anywhere in the command string (handles chains)
        import re
        tokens = re.split(r'[;&|]', command)
        
        has_dangerous = False
        for token in tokens:
            token = token.strip()
            if not token:
                continue
            cmd = token.split()[0]
            if cmd in LEVEL_2_DANGEROUS:
                has_dangerous = True
                break
        
        if has_dangerous:
            return 2
        
        # Check if first command is safe (only if all commands are safe)
        first_cmd = command.split()[0] if command else ""
        if first_cmd in LEVEL_0_SAFE:
            return 0
        
        return 1  # Default: confirm once
    
    async def _execute_command(self, command: str) -> dict:
        """Execute shell command and return result."""
        from .tools.exec import BashCommandTool
        
        bash = BashCommandTool()
        result = await bash.execute(command=command)
        
        if result.success:
            return {
                'success': True,
                'output': result.data['stdout'],
                'error': result.data.get('stderr')
            }
        else:
            return {
                'success': False,
                'error': result.error or 'Command failed'
            }
    
    async def _handle_error(self, error: Exception, user_input: str):
        """
        Handle errors gracefully (Claude pattern: specific error handlers).
        Never crash, always suggest fix.
        """
        error_type = type(error).__name__
        
        # Specific handlers
        if isinstance(error, PermissionError):
            self.console.print("[red]❌ Permission denied[/red]")
            self.console.print("[yellow]💡 Try: sudo {user_input}[/yellow]")
        elif isinstance(error, FileNotFoundError):
            self.console.print("[red]❌ File or command not found[/red]")
            self.console.print("[yellow]💡 Check if the file exists or install the command[/yellow]")
        elif isinstance(error, TimeoutError):
            self.console.print("[red]❌ Operation timed out[/red]")
            self.console.print("[yellow]💡 Check network connection or increase timeout[/yellow]")
        else:
            # Generic fallback
            self.console.print(f"[red]❌ Error: {error_type}[/red]")
            self.console.print(f"[dim]{str(error)}[/dim]")
            self.console.print("[yellow]💡 Try rephrasing your request[/yellow]")
    
    def _show_help(self):
        """Show help message (Gemini: visual hierarchy)."""
        help_text = """
[bold cyan]Qwen CLI - AI-Powered Shell Assistant[/bold cyan]

[bold]Commands:[/bold]
  Just type what you want in natural language!
  
[bold]Examples:[/bold]
  • "list large files"
  • "find files modified today"
  • "show processes using most memory"
  
[bold]System commands:[/bold]
  • [cyan]help[/cyan]  - Show this help
  • [cyan]quit[/cyan]  - Exit shell
  • [cyan]/metrics[/cyan] - Show metrics
  • [cyan]/explain <cmd>[/cyan] - Explain a command

[bold]Safety:[/bold]
  ✓ Safe commands auto-execute (ls, pwd)
  ⚠️  Regular commands ask confirmation (cp, mv)
  🚨 Dangerous commands double-confirm (rm, dd)

[dim]Powered by Qwen + Constitutional AI[/dim]
"""
        self.console.print(help_text)


async def main():
    """Entry point for shell."""
    shell = InteractiveShell()
    await shell.run()


if __name__ == "__main__":
    asyncio.run(main())
