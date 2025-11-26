"""
Basic Command Handler.

Handles: /help, /clear, /quit, /exit, /run, /read, /agents, /status,
         /tools, /palette, /history, /context, /context-clear
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from qwen_cli.constants import HELP_TOPICS

if TYPE_CHECKING:
    from qwen_cli.app import QwenApp
    from qwen_cli.widgets.response_view import ResponseView


class BasicCommandHandler:
    """Handler for basic system commands."""

    def __init__(self, app: "QwenApp"):
        self.app = app

    @property
    def bridge(self):
        return self.app.bridge

    async def handle(
        self,
        command: str,
        args: str,
        view: "ResponseView"
    ) -> None:
        """Route to specific handler method."""
        handlers = {
            "/help": self._handle_help,
            "/clear": self._handle_clear,
            "/quit": self._handle_quit,
            "/exit": self._handle_quit,
            "/run": self._handle_run,
            "/read": self._handle_read,
            "/agents": self._handle_agents,
            "/status": self._handle_status,
            "/tools": self._handle_tools,
            "/palette": self._handle_palette,
            "/history": self._handle_history,
            "/context": self._handle_context,
            "/context-clear": self._handle_context_clear,
        }

        handler = handlers.get(command)
        if handler:
            await handler(args, view)

    async def _handle_help(self, args: str, view: "ResponseView") -> None:
        """Handle /help command."""
        topic = args.lower().strip() if args else ""
        if topic in HELP_TOPICS:
            view.add_system_message(HELP_TOPICS[topic])
        else:
            # Fuzzy match topic
            matches = [k for k in HELP_TOPICS.keys() if k and topic in k]
            if matches:
                view.add_system_message(HELP_TOPICS[matches[0]])
            else:
                view.add_system_message(
                    f"❓ **Tópico não encontrado:** `{topic}`\n\n"
                    f"Tópicos disponíveis: `commands`, `agents`, `tools`, `keys`, `tips`\n\n"
                    f"Use `/help` para ver o menu principal."
                )

    async def _handle_clear(self, args: str, view: "ResponseView") -> None:
        """Handle /clear command."""
        view.clear_all()
        view.add_banner()

    async def _handle_quit(self, args: str, view: "ResponseView") -> None:
        """Handle /quit and /exit commands."""
        self.app.exit()

    async def _handle_run(self, args: str, view: "ResponseView") -> None:
        """Handle /run command."""
        if not args:
            view.add_error("Usage: /run <command>")
            return
        await self.app._execute_bash(args, view)

    async def _handle_read(self, args: str, view: "ResponseView") -> None:
        """Handle /read command."""
        if not args:
            view.add_error("Usage: /read <file>")
            return
        await self.app._read_file(args, view)

    async def _handle_agents(self, args: str, view: "ResponseView") -> None:
        """Handle /agents command."""
        agents_list = "\n".join([
            f"- **{name}**: {info.description}"
            for name, info in self.bridge.agents.AGENT_REGISTRY.items()
        ]) if hasattr(self.bridge.agents, 'AGENT_REGISTRY') else "13 agents available"
        view.add_system_message(f"## 🤖 Available Agents\n\n{agents_list}")

    async def _handle_status(self, args: str, view: "ResponseView") -> None:
        """Handle /status command."""
        status_msg = (
            f"## 📊 Status\n\n"
            f"- **LLM:** {'✅ Gemini connected' if self.bridge.is_connected else '❌ Not connected'}\n"
            f"- **Governance:** {self.bridge.governance.get_status_emoji()}\n"
            f"- **Agents:** {len(self.bridge.agents.available_agents)} available\n"
            f"- **Tools:** {self.bridge.tools.get_tool_count()} loaded\n"
            f"- **Context:** {len(self.bridge.history.context)} messages\n"
        )
        view.add_system_message(status_msg)

    async def _handle_tools(self, args: str, view: "ResponseView") -> None:
        """Handle /tools command."""
        view.add_system_message(self.bridge.get_tool_list())

    async def _handle_palette(self, args: str, view: "ResponseView") -> None:
        """Handle /palette command."""
        if args:
            results = self.bridge.palette.search(args)
            if results:
                lines = ["## 🔍 Command Search Results\n"]
                for r in results:
                    kb = f" `{r.get('keybinding', '')}`" if r.get('keybinding') else ""
                    lines.append(f"- **{r['command']}**{kb}: {r['description']}")
                view.add_system_message("\n".join(lines))
            else:
                view.add_system_message(f"No commands found for: `{args}`")
        else:
            # Show popular commands
            results = self.bridge.palette.search("", max_results=15)
            lines = ["## ⚡ Command Palette\n", "Type `/palette <query>` to search.\n"]
            for r in results:
                kb = f" `{r.get('keybinding', '')}`" if r.get('keybinding') else ""
                lines.append(f"- **{r['command']}**{kb}: {r['description']}")
            view.add_system_message("\n".join(lines))

    async def _handle_history(self, args: str, view: "ResponseView") -> None:
        """Handle /history command."""
        if args:
            results = self.bridge.history.search_history(args)
        else:
            results = self.bridge.history.get_recent(15)

        if results:
            lines = ["## 📜 Command History\n"]
            for i, cmd in enumerate(results, 1):
                lines.append(f"{i}. `{cmd}`")
            view.add_system_message("\n".join(lines))
        else:
            view.add_system_message("No history found.")

    async def _handle_context(self, args: str, view: "ResponseView") -> None:
        """Handle /context command."""
        context = self.bridge.history.get_context()
        if context:
            lines = [f"## 💬 Conversation Context ({len(context)} messages)\n"]
            for i, msg in enumerate(context[-10:], 1):
                role = "👤 User" if msg["role"] == "user" else "🤖 Assistant"
                content = msg["content"][:100] + "..." if len(msg["content"]) > 100 else msg["content"]
                lines.append(f"**{role}:** {content}\n")
            view.add_system_message("\n".join(lines))
        else:
            view.add_system_message("No conversation context yet. Start chatting!")

    async def _handle_context_clear(self, args: str, view: "ResponseView") -> None:
        """Handle /context-clear command."""
        self.bridge.history.clear_context()
        view.add_success("Conversation context cleared.")
