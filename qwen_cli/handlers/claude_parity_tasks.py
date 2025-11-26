"""
Claude Parity Tasks Command Handler.

Handles background tasks and subagent commands:
/bashes, /bg, /kill, /notebook, /task, /subagents, /ask
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from qwen_cli.app import QwenApp
    from qwen_cli.widgets.response_view import ResponseView


class ClaudeParityTasksHandler:
    """Handler for task-related Claude parity commands."""

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
            "/bashes": self._handle_bashes,
            "/bg": self._handle_bg,
            "/kill": self._handle_kill,
            "/notebook": self._handle_notebook,
            "/task": self._handle_task,
            "/subagents": self._handle_subagents,
            "/ask": self._handle_ask,
        }

        handler = handlers.get(command)
        if handler:
            await handler(args, view)

    async def _handle_bashes(self, args: str, view: "ResponseView") -> None:
        try:
            from qwen_dev_cli.tools.claude_parity_tools import BackgroundTaskTool

            tool = BackgroundTaskTool()
            result = await tool._execute_validated(action="list")

            if result.success:
                tasks = result.data.get("tasks", [])
                if tasks:
                    lines = ["## 🔄 Background Tasks\n"]
                    for t in tasks:
                        status_icon = "🟢" if t["status"] == "running" else "✅" if t["status"] == "completed" else "❌"
                        lines.append(f"{status_icon} `{t['id']}` - {t['command']} ({t['status']})")
                    view.add_system_message("\n".join(lines))
                else:
                    view.add_system_message("## 🔄 Background Tasks\n\nNo background tasks running.")
            else:
                view.add_error(f"Failed: {result.error}")
        except Exception as e:
            view.add_error(f"Background tasks error: {e}")

    async def _handle_bg(self, args: str, view: "ResponseView") -> None:
        if not args:
            view.add_error("Usage: `/bg <command>` - Run command in background")
        else:
            try:
                from qwen_dev_cli.tools.claude_parity_tools import BackgroundTaskTool

                tool = BackgroundTaskTool()
                result = await tool._execute_validated(action="start", command=args)

                if result.success:
                    task_id = result.data.get("task_id")
                    view.add_system_message(
                        f"## 🚀 Background Task Started\n\n"
                        f"**Task ID:** `{task_id}`\n"
                        f"**Command:** `{args}`\n\n"
                        f"Use `/bashes` to check status, `/kill {task_id}` to stop."
                    )
                else:
                    view.add_error(f"Failed to start: {result.error}")
            except Exception as e:
                view.add_error(f"Background task error: {e}")

    async def _handle_kill(self, args: str, view: "ResponseView") -> None:
        if not args:
            view.add_error("Usage: `/kill <task_id>` - Kill a background task")
        else:
            try:
                from qwen_dev_cli.tools.claude_parity_tools import BackgroundTaskTool

                tool = BackgroundTaskTool()
                result = await tool._execute_validated(action="kill", task_id=args)

                if result.success:
                    view.add_system_message(f"✅ Task `{args}` killed.")
                else:
                    view.add_error(f"Failed: {result.error}")
            except Exception as e:
                view.add_error(f"Kill error: {e}")

    async def _handle_notebook(self, args: str, view: "ResponseView") -> None:
        if not args:
            view.add_error("Usage: `/notebook <path.ipynb>` - Read Jupyter notebook")
        else:
            try:
                from qwen_dev_cli.tools.claude_parity_tools import NotebookReadTool

                tool = NotebookReadTool()
                result = await tool._execute_validated(file_path=args)

                if result.success:
                    data = result.data
                    lines = [
                        f"## 📓 Notebook: {args}\n",
                        f"**Kernel:** {data.get('kernel', 'Unknown')}",
                        f"**Language:** {data.get('language', 'unknown')}",
                        f"**Cells:** {data.get('total_cells', 0)}\n",
                    ]

                    for cell in data.get("cells", [])[:10]:
                        cell_type = cell.get("type", "unknown")
                        icon = "📝" if cell_type == "code" else "📄"
                        source = cell.get("source", "")[:200]
                        if len(cell.get("source", "")) > 200:
                            source += "..."

                        lines.append(f"\n### {icon} Cell {cell.get('index')} ({cell_type})")
                        lines.append(f"```\n{source}\n```")

                        if cell.get("outputs"):
                            lines.append(f"*Outputs: {len(cell['outputs'])} items*")

                    if data.get("total_cells", 0) > 10:
                        lines.append(f"\n*... and {data['total_cells'] - 10} more cells*")

                    view.add_system_message("\n".join(lines))
                else:
                    view.add_error(f"Failed: {result.error}")
            except Exception as e:
                view.add_error(f"Notebook error: {e}")

    async def _handle_task(self, args: str, view: "ResponseView") -> None:
        if not args:
            view.add_system_message(
                "## 🤖 Task Tool - Launch Subagents\n\n"
                "**Usage:** `/task <type> <prompt>`\n\n"
                "**Agent Types:**\n"
                "- `explore` - Fast codebase exploration\n"
                "- `plan` - Task planning and breakdown\n"
                "- `general-purpose` - Complex multi-step tasks\n"
                "- `code-reviewer` - Review code quality\n"
                "- `test-runner` - Execute tests\n"
                "- `security` - Security analysis\n"
                "- `documentation` - Generate docs\n"
                "- `refactor` - Code refactoring\n\n"
                "**Examples:**\n"
                "- `/task explore Find all API endpoints`\n"
                "- `/task plan Implement user authentication`\n"
                "- `/task code-reviewer Review the auth module`"
            )
        else:
            try:
                from qwen_dev_cli.tools.claude_parity_tools import TaskTool

                parts = args.split(maxsplit=1)
                subagent_type = parts[0] if parts else "general-purpose"
                prompt = parts[1] if len(parts) > 1 else args

                tool = TaskTool()
                result = await tool._execute_validated(
                    prompt=prompt,
                    subagent_type=subagent_type,
                    description=f"Task: {prompt[:30]}"
                )

                if result.success:
                    data = result.data
                    view.add_system_message(
                        f"## 🤖 Subagent Launched\n\n"
                        f"**ID:** `{data['subagent_id']}`\n"
                        f"**Type:** {data['type']}\n"
                        f"**Description:** {data['description']}\n\n"
                        f"**Result:**\n"
                        f"```json\n{json.dumps(data['result'], indent=2)}\n```\n\n"
                        f"Use `/subagents` to see all running subagents."
                    )
                else:
                    view.add_error(f"Task failed: {result.error}")
            except Exception as e:
                view.add_error(f"Task error: {e}")

    async def _handle_subagents(self, args: str, view: "ResponseView") -> None:
        try:
            from qwen_dev_cli.tools.claude_parity_tools import TaskTool

            subagents = TaskTool.list_subagents()
            if subagents:
                lines = ["## 🤖 Running Subagents\n"]
                for s in subagents:
                    status_icon = "🟢" if s["status"] == "running" else "✅" if s["status"] == "completed" else "❌"
                    lines.append(
                        f"{status_icon} `{s['id']}` - **{s['type']}** ({s['status']})\n"
                        f"   {s['description']} | {s['prompts_count']} prompt(s)"
                    )
                view.add_system_message("\n".join(lines))
            else:
                view.add_system_message(
                    "## 🤖 Subagents\n\n"
                    "No subagents running.\n\n"
                    "Use `/task <type> <prompt>` to launch one."
                )
        except Exception as e:
            view.add_error(f"Subagents error: {e}")

    async def _handle_ask(self, args: str, view: "ResponseView") -> None:
        if not args:
            view.add_system_message(
                "## ❓ Ask User Question\n\n"
                "This command is used by the AI to ask clarifying questions.\n\n"
                "The AI can use this tool to:\n"
                "- Gather user preferences\n"
                "- Clarify requirements\n"
                "- Get decisions on implementation choices"
            )
        else:
            try:
                from qwen_dev_cli.tools.claude_parity_tools import AskUserQuestionTool
                pending = AskUserQuestionTool.get_pending_questions()
                if pending:
                    lines = ["## ❓ Pending Questions\n"]
                    for q in pending:
                        lines.append(f"**Question ID:** `{q['id']}`")
                        for question in q["questions"]:
                            lines.append(f"\n**{question['header']}:** {question['question']}")
                            for i, opt in enumerate(question["options"], 1):
                                label = opt.get("label", opt) if isinstance(opt, dict) else opt
                                lines.append(f"  {i}. {label}")
                    view.add_system_message("\n".join(lines))
                else:
                    view.add_system_message("No pending questions.")
            except Exception as e:
                view.add_error(f"Ask error: {e}")
