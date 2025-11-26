"""
Session Command Handler.

Handles: /resume, /save, /sessions, /checkpoint, /rewind, /export,
         /doctor, /permissions, /sandbox, /login, /logout, /auth,
         /memory, /remember
"""

from __future__ import annotations

import os
import subprocess
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from qwen_cli.app import QwenApp
    from qwen_cli.widgets.response_view import ResponseView


class SessionCommandHandler:
    """Handler for session and auth commands."""

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
            "/resume": self._handle_resume,
            "/save": self._handle_save,
            "/sessions": self._handle_sessions,
            "/checkpoint": self._handle_checkpoint,
            "/rewind": self._handle_rewind,
            "/export": self._handle_export,
            "/doctor": self._handle_doctor,
            "/permissions": self._handle_permissions,
            "/sandbox": self._handle_sandbox,
            "/login": self._handle_login,
            "/logout": self._handle_logout,
            "/auth": self._handle_auth,
            "/memory": self._handle_memory,
            "/remember": self._handle_remember,
        }

        handler = handlers.get(command)
        if handler:
            await handler(args, view)

    async def _handle_resume(self, args: str, view: "ResponseView") -> None:
        session_id = args if args else None
        try:
            result = self.bridge.resume_session(session_id)
            view.add_system_message(
                f"## 🔄 Session Resumed\n\n"
                f"**Session:** {result.get('session_id', 'latest')}\n"
                f"**Timestamp:** {result.get('timestamp', 'unknown')}\n"
                f"**Messages:** {result.get('message_count', 0)}\n"
                f"**Context:** Restored ✓"
            )
        except Exception as e:
            view.add_system_message(
                f"## 🔄 Resume Session\n\n"
                f"No previous session found: {e}\n\n"
                f"Use `/sessions` to list available sessions."
            )

    async def _handle_save(self, args: str, view: "ResponseView") -> None:
        session_id = args if args else None
        try:
            saved_id = self.bridge.save_session(session_id)
            view.add_system_message(
                f"## 💾 Session Saved\n\n"
                f"**Session ID:** `{saved_id}`\n"
                f"**Location:** `~/.juancs/sessions/{saved_id}.json`\n\n"
                f"Use `/resume {saved_id}` to restore later."
            )
        except Exception as e:
            view.add_error(f"Save failed: {e}")

    async def _handle_sessions(self, args: str, view: "ResponseView") -> None:
        try:
            sessions = self.bridge.list_sessions(10)
            if sessions:
                lines = ["## 📚 Available Sessions\n"]
                for s in sessions:
                    lines.append(f"- `{s['session_id']}` ({s['message_count']} msgs) - {s.get('timestamp', '?')[:16]}")
                lines.append("\nUse `/resume <session_id>` to restore.")
                view.add_system_message("\n".join(lines))
            else:
                view.add_system_message(
                    "## 📚 Sessions\n\n"
                    "No saved sessions found.\n\n"
                    "Use `/save` to save current session."
                )
        except Exception as e:
            view.add_error(f"List sessions failed: {e}")

    async def _handle_checkpoint(self, args: str, view: "ResponseView") -> None:
        label = args if args else None
        try:
            cp = self.bridge.create_checkpoint(label)
            view.add_system_message(
                f"## 📌 Checkpoint Created\n\n"
                f"**Index:** {cp['index']}\n"
                f"**Label:** {cp['label']}\n"
                f"**Messages:** {cp['message_count']}\n\n"
                f"Use `/rewind {cp['index']}` to return to this point."
            )
        except Exception as e:
            view.add_error(f"Checkpoint failed: {e}")

    async def _handle_rewind(self, args: str, view: "ResponseView") -> None:
        try:
            checkpoints = self.bridge.get_checkpoints()
            if args and args.isdigit():
                idx = int(args)
                result = self.bridge.rewind_to(idx)
                view.add_system_message(
                    f"## ⏪ Rewound\n\n"
                    f"**Checkpoint:** {result.get('rewound_to', idx)}\n"
                    f"**Messages:** {result.get('message_count', '?')}\n"
                    f"**Status:** Conversation state restored ✓"
                )
            elif checkpoints:
                lines = ["## ⏪ Available Checkpoints\n"]
                for cp in checkpoints[-10:]:
                    lines.append(f"- `{cp['index']}`: {cp['label']} ({cp['message_count']} msgs)")
                lines.append("\nUse `/rewind <index>` to restore.")
                view.add_system_message("\n".join(lines))
            else:
                view.add_system_message(
                    "## ⏪ Checkpoints\n\n"
                    "No checkpoints available.\n\n"
                    "Use `/checkpoint [label]` to create one."
                )
        except Exception as e:
            view.add_system_message(f"## ⏪ Rewind\n\nError: {e}")

    async def _handle_export(self, args: str, view: "ResponseView") -> None:
        try:
            filepath = self.bridge.export_conversation(args or "conversation.md")
            view.add_system_message(f"✅ Conversation exported to: **{filepath}**")
        except Exception as e:
            view.add_error(f"Export failed: {e}")

    async def _handle_doctor(self, args: str, view: "ResponseView") -> None:
        try:
            health = self.bridge.check_health()
            lines = ["## 🏥 Health Check\n"]
            for check, status in health.items():
                icon = "✅" if status.get('ok') else "❌"
                lines.append(f"{icon} **{check}:** {status.get('message', 'OK')}")
            view.add_system_message("\n".join(lines))
        except Exception as e:
            view.add_system_message(f"## 🏥 Health Check\n\n❌ Check failed: {e}")

    async def _handle_permissions(self, args: str, view: "ResponseView") -> None:
        try:
            perms = self.bridge.get_permissions()
            lines = ["## 🔐 Permissions\n"]
            for perm, value in perms.items():
                icon = "✅" if value else "❌"
                lines.append(f"{icon} **{perm}**")
            view.add_system_message("\n".join(lines))
        except Exception as e:
            view.add_system_message(f"## 🔐 Permissions\n\nNot available: {e}")

    async def _handle_sandbox(self, args: str, view: "ResponseView") -> None:
        try:
            if args == "off":
                self.bridge.set_sandbox(False)
                view.add_system_message("🔓 Sandbox **disabled**")
            else:
                self.bridge.set_sandbox(True)
                view.add_system_message("🔒 Sandbox **enabled** - commands run in isolation")
        except Exception as e:
            view.add_error(f"Sandbox toggle failed: {e}")

    async def _handle_login(self, args: str, view: "ResponseView") -> None:
        if not args:
            status = self.bridge.get_auth_status()
            lines = ["## 🔐 Authentication Status\n"]
            for provider, info in status.get("providers", {}).items():
                if info["logged_in"]:
                    sources = ", ".join(info["sources"])
                    lines.append(f"✅ **{provider}**: logged in ({sources})")
                else:
                    lines.append(f"⬚ **{provider}**: not configured")
            lines.append("\n**Usage:**")
            lines.append("- `/login <provider> <api_key>` - Login globally")
            lines.append("- `/login <provider> <api_key> project` - Login for this project only")
            lines.append("\n**Providers:** gemini, openai, anthropic, nebius, groq")
            view.add_system_message("\n".join(lines))
        else:
            parts = args.split(maxsplit=2)
            provider = parts[0]
            api_key = parts[1] if len(parts) > 1 else None
            scope = parts[2] if len(parts) > 2 else "global"

            result = self.bridge.login(provider, api_key, scope)
            if result.get("success"):
                view.add_system_message(
                    f"## ✅ Logged in to {provider}\n\n"
                    f"**Scope:** {result.get('scope', 'global')}\n"
                    f"**File:** `{result.get('file', 'environment')}`"
                )
            else:
                view.add_error(result.get("error", "Login failed"))

    async def _handle_logout(self, args: str, view: "ResponseView") -> None:
        if not args:
            result = self.bridge.logout()
        else:
            result = self.bridge.logout(provider=args)

        if result.get("success"):
            removed = result.get("removed", [])
            if removed:
                view.add_system_message(
                    f"## 🔓 Logged Out\n\n"
                    f"**Removed:** {', '.join(removed)}"
                )
            else:
                view.add_system_message("No credentials found to remove.")
        else:
            view.add_error(result.get("error", "Logout failed"))

    async def _handle_auth(self, args: str, view: "ResponseView") -> None:
        status = self.bridge.get_auth_status()
        lines = ["## 🔐 Authentication Status\n"]

        for provider, info in status.get("providers", {}).items():
            if info["logged_in"]:
                sources = ", ".join(info["sources"])
                lines.append(f"✅ **{provider}**: `{info['env_var']}` ({sources})")
            else:
                lines.append(f"⬚ **{provider}**: not configured")

        lines.append(f"\n**Global config:** `{status.get('global_file')}`")
        lines.append(f"**Project config:** `{status.get('project_file')}`")
        view.add_system_message("\n".join(lines))

    async def _handle_memory(self, args: str, view: "ResponseView") -> None:
        if not args:
            project_mem = self.bridge.read_memory(scope="project")
            global_mem = self.bridge.read_memory(scope="global")

            lines = ["## 🧠 Memory\n"]

            if project_mem.get("exists"):
                lines.append(f"### Project Memory (`{project_mem.get('file')}`)")
                lines.append(f"*{project_mem.get('lines', 0)} lines, {project_mem.get('size', 0)} bytes*\n")
                content = project_mem.get("content", "")[:500]
                if content:
                    lines.append(f"```\n{content}\n```")
            else:
                lines.append("*No project memory (MEMORY.md not found)*\n")

            if global_mem.get("exists"):
                lines.append(f"\n### Global Memory (`{global_mem.get('file')}`)")
                lines.append(f"*{global_mem.get('lines', 0)} lines*")
            else:
                lines.append("\n*No global memory*")

            lines.append("\n**Commands:**")
            lines.append("- `/remember <note>` - Add note to memory")
            lines.append("- `/memory edit` - Open memory file in editor")
            view.add_system_message("\n".join(lines))

        elif args == "edit":
            mem_file = self.bridge._get_memory_file(scope="project")
            editor = os.environ.get("EDITOR", "nano")

            if not mem_file.exists():
                self.bridge.write_memory(
                    "# Project Memory\n\nAdd persistent notes and context here.\n",
                    scope="project"
                )

            try:
                subprocess.run([editor, str(mem_file)])
                view.add_system_message(f"Memory file edited: `{mem_file}`")
            except Exception as e:
                view.add_error(f"Could not open editor: {e}")

        elif args == "clear":
            mem_file = self.bridge._get_memory_file(scope="project")
            if mem_file.exists():
                mem_file.unlink()
                view.add_system_message("Project memory cleared.")
            else:
                view.add_system_message("No memory file to clear.")

    async def _handle_remember(self, args: str, view: "ResponseView") -> None:
        if not args:
            view.add_error("Usage: `/remember <note>` or `/remember preferences: <note>`")
        else:
            category = "general"
            note = args

            if ":" in args and args.split(":")[0].strip() in ["preferences", "patterns", "todos", "context"]:
                category, note = args.split(":", 1)
                category = category.strip()
                note = note.strip()

            result = self.bridge.add_memory_note(note, category=category)
            if result.get("success"):
                view.add_system_message(
                    f"📝 Note added to **{category}** in `{result.get('file')}`"
                )
            else:
                view.add_error(result.get("error", "Failed to add note"))
