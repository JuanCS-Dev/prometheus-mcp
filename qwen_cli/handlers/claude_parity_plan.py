"""
Claude Parity Plan Command Handler.

Handles custom commands and plan mode:
/commands, /command-create, /command-delete,
/plan-mode, /plan-status, /plan-note, /plan-exit, /plan-approve
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from qwen_cli.app import QwenApp
    from qwen_cli.widgets.response_view import ResponseView


class ClaudeParityPlanHandler:
    """Handler for plan-related Claude parity commands."""

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
            "/commands": self._handle_commands,
            "/command-create": self._handle_command_create,
            "/command-delete": self._handle_command_delete,
            "/plan-mode": self._handle_plan_mode,
            "/plan-status": self._handle_plan_status,
            "/plan-note": self._handle_plan_note,
            "/plan-exit": self._handle_plan_exit,
            "/plan-approve": self._handle_plan_approve,
        }

        handler = handlers.get(command)
        if handler:
            await handler(args, view)

    async def _handle_commands(self, args: str, view: "ResponseView") -> None:
        if args == "refresh":
            try:
                commands = self.bridge.refresh_custom_commands()
                view.add_system_message(f"✅ Reloaded {len(commands)} custom commands")
            except Exception as e:
                view.add_error(f"Refresh error: {e}")
        else:
            try:
                commands = self.bridge.get_custom_commands()
                if commands:
                    lines = ["## 📜 Custom Commands\n"]
                    for name, cmd in commands.items():
                        scope = "🏠" if cmd["type"] == "project" else "🌍"
                        lines.append(f"{scope} **/{name}** - {cmd['description']}")
                    lines.append("\n**Usage:**")
                    lines.append("- `/commands refresh` - Reload commands")
                    lines.append("- `/command-create <name>` - Create new command")
                    lines.append("- `/command-delete <name>` - Delete command")
                    view.add_system_message("\n".join(lines))
                else:
                    view.add_system_message(
                        "## 📜 Custom Commands\n\n"
                        "No custom commands found.\n\n"
                        "**Create commands in:**\n"
                        "- `.juancs/commands/<name>.md` (project)\n"
                        "- `~/.juancs/commands/<name>.md` (global)\n\n"
                        "**Example:**\n"
                        "Create `.juancs/commands/review-pr.md`:\n"
                        "```markdown\n"
                        "# Review a pull request\n"
                        "Review PR $1 focusing on code quality and security.\n"
                        "```\n"
                        "Then use: `/review-pr 123`"
                    )
            except Exception as e:
                view.add_error(f"Commands error: {e}")

    async def _handle_command_create(self, args: str, view: "ResponseView") -> None:
        if not args:
            view.add_system_message(
                "## 📜 Create Custom Command\n\n"
                "**Usage:** `/command-create <name> <prompt>`\n\n"
                "**Variables:**\n"
                "- `$ARGUMENTS` or `{args}` - All arguments\n"
                "- `$1`, `$2`, etc. - Positional arguments\n\n"
                "**Example:**\n"
                "`/command-create fix-bugs Find and fix bugs in $ARGUMENTS`"
            )
        else:
            parts = args.split(maxsplit=1)
            name = parts[0]
            prompt = parts[1] if len(parts) > 1 else f"Execute {name} command"

            try:
                cmd = self.bridge.create_custom_command(name, prompt)
                view.add_system_message(
                    f"## ✅ Command Created\n\n"
                    f"**Name:** `/{name}`\n"
                    f"**Path:** `{cmd['path']}`\n\n"
                    f"Now you can use `/{name} <args>` to run this command."
                )
            except Exception as e:
                view.add_error(f"Create failed: {e}")

    async def _handle_command_delete(self, args: str, view: "ResponseView") -> None:
        if not args:
            view.add_error("Usage: `/command-delete <name>`")
        else:
            try:
                if self.bridge.delete_custom_command(args):
                    view.add_system_message(f"✅ Command `/{args}` deleted")
                else:
                    view.add_error(f"Command not found: {args}")
            except Exception as e:
                view.add_error(f"Delete failed: {e}")

    async def _handle_plan_mode(self, args: str, view: "ResponseView") -> None:
        try:
            result = self.bridge.enter_plan_mode(args)
            if result.get("success"):
                view.add_system_message(
                    f"## 📋 Plan Mode Activated\n\n"
                    f"**Task:** {result.get('task', 'No task specified')}\n"
                    f"**Plan file:** `{result.get('plan_file')}`\n\n"
                    f"⚠️ **Restrictions:** {result.get('restrictions')}\n\n"
                    f"**Commands:**\n"
                    f"- `/plan-note <note>` - Add exploration note\n"
                    f"- `/plan-status` - Check plan status\n"
                    f"- `/plan-exit` - Exit without approval\n"
                    f"- `/plan-approve` - Approve and exit"
                )
            else:
                view.add_error(result.get("error", "Failed to enter plan mode"))
        except Exception as e:
            view.add_error(f"Plan mode failed: {e}")

    async def _handle_plan_status(self, args: str, view: "ResponseView") -> None:
        try:
            state = self.bridge.get_plan_mode_state()
            if state.get("active"):
                view.add_system_message(
                    f"## 📋 Plan Mode Status\n\n"
                    f"**Active:** ✅ Yes\n"
                    f"**Task:** {state.get('task', 'N/A')}\n"
                    f"**Plan file:** `{state.get('plan_file')}`\n"
                    f"**Started:** {state.get('started_at')}\n"
                    f"**Notes:** {len(state.get('exploration_log', []))} entries"
                )
            else:
                view.add_system_message(
                    "## 📋 Plan Mode Status\n\n"
                    "**Active:** ❌ No\n\n"
                    "Use `/plan-mode <task>` to enter plan mode."
                )
        except Exception as e:
            view.add_error(f"Status check failed: {e}")

    async def _handle_plan_note(self, args: str, view: "ResponseView") -> None:
        if not args:
            view.add_error("Usage: `/plan-note <note>`")
        else:
            try:
                if self.bridge.add_plan_note(args):
                    view.add_system_message(f"✅ Note added: {args[:50]}...")
                else:
                    view.add_error("Not in plan mode. Use `/plan-mode` first.")
            except Exception as e:
                view.add_error(f"Failed to add note: {e}")

    async def _handle_plan_exit(self, args: str, view: "ResponseView") -> None:
        try:
            result = self.bridge.exit_plan_mode(approved=False)
            if result.get("success"):
                view.add_system_message(
                    f"## 📋 Plan Mode Exited\n\n"
                    f"**Approved:** ❌ No\n"
                    f"**Plan file:** `{result.get('plan_file')}`\n"
                    f"**Notes collected:** {result.get('exploration_count', 0)}"
                )
            else:
                view.add_error(result.get("error", "Not in plan mode"))
        except Exception as e:
            view.add_error(f"Exit failed: {e}")

    async def _handle_plan_approve(self, args: str, view: "ResponseView") -> None:
        try:
            result = self.bridge.exit_plan_mode(approved=True)
            if result.get("success"):
                view.add_system_message(
                    f"## ✅ Plan Approved!\n\n"
                    f"**Plan file:** `{result.get('plan_file')}`\n"
                    f"**Notes collected:** {result.get('exploration_count', 0)}\n\n"
                    f"Write operations are now enabled. Ready to implement!"
                )
            else:
                view.add_error(result.get("error", "Not in plan mode"))
        except Exception as e:
            view.add_error(f"Approval failed: {e}")
