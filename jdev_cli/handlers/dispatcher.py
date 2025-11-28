"""
CommandDispatcher - Command Pattern Implementation.

SCALE & SUSTAIN Phase 1.2 - CC Reduction.

This dispatcher reduces shell_main.py CC from 112 to ~15 by:
1. Using dictionary-based routing (O(1) lookup)
2. Delegating to specialized handlers
3. Eliminating 35+ elif branches

Author: JuanCS Dev
Date: 2025-11-26
"""

from dataclasses import dataclass
from typing import Any, Callable, Coroutine, Dict, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from jdev_cli.shell_main import InteractiveShell


@dataclass
class CommandResult:
    """Result of command execution."""
    should_exit: bool = False
    message: Optional[str] = None
    success: bool = True

    @classmethod
    def exit(cls) -> 'CommandResult':
        """Create exit result."""
        return cls(should_exit=True)

    @classmethod
    def ok(cls, message: Optional[str] = None) -> 'CommandResult':
        """Create success result."""
        return cls(message=message)

    @classmethod
    def error(cls, message: str) -> 'CommandResult':
        """Create error result."""
        return cls(message=message, success=False)

    @classmethod
    def unknown(cls, cmd: str) -> 'CommandResult':
        """Create unknown command result."""
        return cls(message=f"Unknown command: {cmd}", success=False)


# Type alias for command handler
CommandHandler = Callable[['InteractiveShell', str], Coroutine[Any, Any, CommandResult]]


class CommandDispatcher:
    """
    Dispatch commands to appropriate handlers.

    Reduces cyclomatic complexity by replacing if/elif chains
    with dictionary-based dispatch.
    """

    def __init__(self, shell: 'InteractiveShell'):
        """
        Initialize dispatcher with shell reference.

        Args:
            shell: The InteractiveShell instance.
        """
        self.shell = shell
        self._handlers: Dict[str, CommandHandler] = {}
        self._prefix_handlers: Dict[str, CommandHandler] = {}

        # Import and register handlers
        self._register_handlers()

    def _register_handlers(self) -> None:
        """Register all command handlers."""
        from .basic_handler import BasicHandler
        from .lsp_handler import LSPHandler
        from .history_handler import HistoryHandler
        from .workflow_handler import WorkflowHandler
        from .index_handler import IndexHandler
        from .refactor_handler import RefactorHandler

        # Create handler instances
        basic = BasicHandler(self.shell)
        lsp = LSPHandler(self.shell)
        history = HistoryHandler(self.shell)
        workflow = WorkflowHandler(self.shell)
        index = IndexHandler(self.shell)
        refactor = RefactorHandler(self.shell)

        # Register exact match handlers
        self._handlers = {
            # Basic commands
            "/exit": basic.handle_exit,
            "/quit": basic.handle_exit,
            "/help": basic.handle_help,
            "/tools": basic.handle_tools,
            "/clear": basic.handle_clear,
            "/context": basic.handle_context,
            "/context optimize": basic.handle_context_optimize,
            "/metrics": basic.handle_metrics,
            "/cache": basic.handle_cache,
            "/tokens": basic.handle_tokens,
            "/preview": basic.handle_preview_on,
            "/nopreview": basic.handle_preview_off,
            "/dash": basic.handle_dashboard,
            "/dashboard": basic.handle_dashboard,

            # History commands
            "/history": history.handle_history,
            "/stats": history.handle_stats,
            "/sessions": history.handle_sessions,

            # Workflow commands
            "/workflow": workflow.handle_workflow_status,
            "/workflow list": workflow.handle_workflow_list,

            # Index commands
            "/index": index.handle_index,

            # LSP commands
            "/lsp": lsp.handle_lsp_start,
        }

        # Register prefix match handlers (order matters - longer prefixes first)
        self._prefix_handlers = {
            # LSP commands (most specific first)
            "/lsp signature ": lsp.handle_signature,
            "/lsp complete ": lsp.handle_complete,
            "/lsp hover ": lsp.handle_hover,
            "/lsp goto ": lsp.handle_goto,
            "/lsp refs ": lsp.handle_refs,
            "/lsp diag ": lsp.handle_diag,

            # Refactor commands
            "/refactor rename ": refactor.handle_rename,
            "/refactor imports ": refactor.handle_imports,

            # Workflow commands
            "/workflow run ": workflow.handle_workflow_run,

            # Other commands
            "/squad ": workflow.handle_squad,
            "/find ": index.handle_find,
            "/explain ": basic.handle_explain,
            "/suggest ": index.handle_suggest,
        }

    async def dispatch(self, cmd: str) -> CommandResult:
        """
        Dispatch command to appropriate handler.

        Args:
            cmd: The command string.

        Returns:
            CommandResult with execution status.
        """
        cmd = cmd.strip()

        # Try exact match first
        if cmd in self._handlers:
            handler = self._handlers[cmd]
            return await handler(cmd)

        # Try prefix match (check longer prefixes first)
        for prefix, handler in sorted(
            self._prefix_handlers.items(),
            key=lambda x: len(x[0]),
            reverse=True
        ):
            if cmd.startswith(prefix):
                return await handler(cmd)

        # Unknown command
        return CommandResult.unknown(cmd)

    def register_handler(self, cmd: str, handler: CommandHandler) -> None:
        """
        Register a new command handler.

        Args:
            cmd: Command string (exact match).
            handler: Async handler function.
        """
        self._handlers[cmd] = handler

    def register_prefix_handler(self, prefix: str, handler: CommandHandler) -> None:
        """
        Register a prefix-based handler.

        Args:
            prefix: Command prefix to match.
            handler: Async handler function.
        """
        self._prefix_handlers[prefix] = handler

    def get_all_commands(self) -> list[str]:
        """Get list of all registered commands."""
        return list(self._handlers.keys()) + [
            f"{p}..." for p in self._prefix_handlers.keys()
        ]
