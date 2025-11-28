"""
Command Router for JuanCS Dev-Code.

Routes slash commands to appropriate handlers.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from jdev_tui.app import QwenApp
    from jdev_tui.widgets.response_view import ResponseView


class CommandRouter:
    """
    Routes slash commands to appropriate handler modules.

    Lazy loads handlers to avoid circular imports.
    """

    def __init__(self, app: "QwenApp"):
        self.app = app
        self._basic = None
        self._agents = None
        self._claude_parity = None
        self._session = None
        self._operations = None

    @property
    def basic(self):
        """Lazy load basic commands handler."""
        if self._basic is None:
            from jdev_tui.handlers.basic import BasicCommandHandler
            self._basic = BasicCommandHandler(self.app)
        return self._basic

    @property
    def agents(self):
        """Lazy load agents handler."""
        if self._agents is None:
            from jdev_tui.handlers.agents import AgentCommandHandler
            self._agents = AgentCommandHandler(self.app)
        return self._agents

    @property
    def claude_parity(self):
        """Lazy load Claude parity handler."""
        if self._claude_parity is None:
            from jdev_tui.handlers.claude_parity import ClaudeParityHandler
            self._claude_parity = ClaudeParityHandler(self.app)
        return self._claude_parity

    @property
    def session(self):
        """Lazy load session handler."""
        if self._session is None:
            from jdev_tui.handlers.session import SessionCommandHandler
            self._session = SessionCommandHandler(self.app)
        return self._session

    @property
    def operations(self):
        """Lazy load operations handler."""
        if self._operations is None:
            from jdev_tui.handlers.operations import OperationsHandler
            self._operations = OperationsHandler(self.app)
        return self._operations

    async def dispatch(
        self,
        cmd: str,
        view: "ResponseView"
    ) -> bool:
        """
        Dispatch a command to the appropriate handler.

        Returns True if command was handled, False otherwise.
        """
        parts = cmd.split(maxsplit=1)
        command = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""

        # Basic commands
        if command in ("/help", "/clear", "/quit", "/exit", "/run", "/read",
                       "/agents", "/status", "/tools", "/palette", "/history",
                       "/context", "/context-clear"):
            await self.basic.handle(command, args, view)
            return True

        # Agent commands
        if command in ("/plan", "/execute", "/architect", "/review", "/explore",
                       "/refactor", "/test", "/security", "/docs", "/perf",
                       "/devops", "/justica", "/sofia", "/data"):
            await self.agents.handle(command, args, view)
            return True

        # Claude parity commands
        if command in ("/compact", "/cost", "/tokens", "/todos", "/todo",
                       "/model", "/init", "/hooks", "/mcp", "/router",
                       "/router-status", "/route", "/bashes", "/bg", "/kill",
                       "/notebook", "/task", "/subagents", "/ask", "/commands",
                       "/command-create", "/command-delete", "/plan-mode",
                       "/plan-status", "/plan-note", "/plan-exit", "/plan-approve"):
            await self.claude_parity.handle(command, args, view)
            return True

        # Session commands
        if command in ("/resume", "/save", "/sessions", "/checkpoint", "/rewind",
                       "/export", "/doctor", "/permissions", "/sandbox",
                       "/login", "/logout", "/auth", "/memory", "/remember"):
            await self.session.handle(command, args, view)
            return True

        # Operations commands
        if command in ("/pr", "/pr-draft", "/image", "/pdf", "/audit",
                       "/diff", "/backup", "/restore", "/undo", "/redo",
                       "/undo-stack", "/secrets", "/secrets-staged"):
            await self.operations.handle(command, args, view)
            return True

        # Check for custom command
        custom_cmd_name = command.lstrip("/")
        custom_prompt = self.app.bridge.execute_custom_command(custom_cmd_name, args)

        if custom_prompt:
            view.add_system_message(f"📜 *Running custom command: `/{custom_cmd_name}`*")
            await self.app._handle_chat(custom_prompt, view)
            return True

        # Unknown command
        view.add_error(f"Unknown command: {command}")
        view.add_system_message("Type `/help` for available commands.")
        return False
