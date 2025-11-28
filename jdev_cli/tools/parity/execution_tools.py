"""
Execution Tools - BackgroundTask, BashOutput, KillShell
=======================================================

Background process management for Claude Code parity.

Contains:
- BackgroundTaskTool: Run shell commands in background
- BashOutputTool: Get output from background shells
- KillShellTool: Terminate background shells

Author: JuanCS Dev
Date: 2025-11-27
"""

from __future__ import annotations

import logging
import re
import shlex
import signal
import subprocess
import threading
from typing import Dict, List

from jdev_cli.tools.base import Tool, ToolCategory, ToolResult
from jdev_cli.tools._parity_utils import TaskTracker

logger = logging.getLogger(__name__)

# Shared task tracker instance
_task_tracker = TaskTracker()


# =============================================================================
# BACKGROUND TASK TOOL
# =============================================================================

class BackgroundTaskTool(Tool):
    """
    Run shell commands in the background.

    Claude Code parity: Implements /bashes functionality for background tasks.

    Security:
    - Commands are validated before execution
    - Uses shlex.split instead of shell=True
    - Blocked dangerous commands

    Example:
        result = await task.execute(action="start", command="pytest tests/")
        task_id = result.data["task_id"]
    """

    # Dangerous command patterns
    BLOCKED_PATTERNS = [
        r"rm\s+-rf\s+/",
        r":()\{.*\}",  # Fork bomb
        r"dd\s+.*of=/dev/",
        r"mkfs\.",
        r">\s*/dev/sd",
    ]

    def __init__(self):
        super().__init__()
        self.name = "background_task"
        self.category = ToolCategory.EXECUTION
        self.description = "Run shell commands in background"
        self.parameters = {
            "action": {
                "type": "string",
                "description": "Action: 'start', 'status', 'output', 'kill', 'list'",
                "required": True
            },
            "command": {
                "type": "string",
                "description": "Shell command to run (for 'start' action)",
                "required": False
            },
            "task_id": {
                "type": "string",
                "description": "Task ID (for 'status', 'output', 'kill' actions)",
                "required": False
            }
        }

    async def _execute_validated(self, **kwargs) -> ToolResult:
        """Execute background task action."""
        action = kwargs.get("action", "")
        command = kwargs.get("command", "")
        task_id = kwargs.get("task_id", "")

        if not action:
            return ToolResult(success=False, error="action is required")

        if action == "start":
            return await self._start_task(command)
        elif action == "list":
            return self._list_tasks()
        elif action == "status":
            return self._get_status(task_id)
        elif action == "output":
            return self._get_output(task_id)
        elif action == "kill":
            return self._kill_task(task_id)
        else:
            return ToolResult(
                success=False,
                error=f"Unknown action: {action}. Valid: start, list, status, output, kill"
            )

    async def _start_task(self, command: str) -> ToolResult:
        """Start a new background task."""
        if not command:
            return ToolResult(success=False, error="command is required for start")

        # Security: Check for dangerous patterns
        for pattern in self.BLOCKED_PATTERNS:
            if re.search(pattern, command, re.IGNORECASE):
                return ToolResult(
                    success=False,
                    error="Command blocked by security filter"
                )

        # Try to use input validator if available
        try:
            from jdev_cli.core.input_validator import validate_command
            validation = validate_command(command, allow_shell=False)
            if not validation.is_valid:
                return ToolResult(
                    success=False,
                    error=f"Command blocked: {', '.join(validation.errors)}"
                )
        except ImportError:
            logger.debug("Input validator not available, using basic checks")

        try:
            # Parse command safely
            args = shlex.split(command)
            if not args:
                return ToolResult(success=False, error="Empty command")

            # Start process
            process = subprocess.Popen(
                args,
                shell=False,  # SECURITY: Never use shell=True
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            # Create task entry
            task_id = _task_tracker.create_task(command, process, "running")

            # Start output collector thread
            collector = threading.Thread(
                target=self._collect_output,
                args=(task_id,),
                daemon=True
            )
            collector.start()

            return ToolResult(
                success=True,
                data={
                    "task_id": task_id,
                    "command": command[:100],
                    "status": "started",
                    "pid": process.pid
                },
                metadata={"action": "start"}
            )

        except FileNotFoundError:
            return ToolResult(success=False, error=f"Command not found: {args[0]}")
        except PermissionError:
            return ToolResult(success=False, error="Permission denied")
        except Exception as e:
            logger.error(f"Failed to start task: {e}")
            return ToolResult(success=False, error=str(e))

    def _collect_output(self, task_id: str) -> None:
        """Collect output from background process."""
        task = _task_tracker.get_task(task_id)
        if not task:
            return

        proc = task.get("process")
        if not proc:
            return

        try:
            stdout, stderr = proc.communicate()

            if stdout:
                for line in stdout.split("\n"):
                    if line:
                        _task_tracker.append_output(task_id, stdout=line)

            if stderr:
                for line in stderr.split("\n"):
                    if line:
                        _task_tracker.append_output(task_id, stderr=line)

            return_code = proc.returncode
            status = "completed" if return_code == 0 else "failed"
            _task_tracker.update_status(task_id, status, return_code)

        except Exception as e:
            logger.error(f"Output collection error for {task_id}: {e}")
            _task_tracker.update_status(task_id, "failed", -1)

    def _list_tasks(self) -> ToolResult:
        """List all background tasks."""
        tasks = _task_tracker.list_tasks()

        # Update status for running tasks
        for task in tasks:
            if task.get("status") == "running":
                proc = task.get("process")
                if proc and proc.poll() is not None:
                    _task_tracker.update_status(
                        task["id"],
                        "completed" if proc.returncode == 0 else "failed",
                        proc.returncode
                    )

        # Get fresh list after status updates
        tasks = _task_tracker.list_tasks()

        tasks_info = [
            {
                "id": t["id"],
                "command": t["command"][:50],
                "status": t["status"],
                "start_time": t.get("started_at")
            }
            for t in tasks
        ]

        return ToolResult(
            success=True,
            data={"tasks": tasks_info, "count": len(tasks_info)},
            metadata={"action": "list"}
        )

    def _get_status(self, task_id: str) -> ToolResult:
        """Get status of a specific task."""
        if not task_id:
            return ToolResult(success=False, error="task_id is required for status")

        task = _task_tracker.find_task(task_id)
        if not task:
            return ToolResult(success=False, error=f"Task not found: {task_id}")

        # Update status if process finished
        proc = task.get("process")
        if proc and task["status"] == "running" and proc.poll() is not None:
            _task_tracker.update_status(
                task["id"],
                "completed" if proc.returncode == 0 else "failed",
                proc.returncode
            )
            task = _task_tracker.get_task(task["id"])

        return ToolResult(
            success=True,
            data={
                "id": task["id"],
                "command": task["command"],
                "status": task["status"],
                "return_code": task.get("return_code"),
                "started_at": task.get("started_at"),
                "completed_at": task.get("completed_at")
            },
            metadata={"action": "status"}
        )

    def _get_output(self, task_id: str) -> ToolResult:
        """Get output from a task."""
        if not task_id:
            return ToolResult(success=False, error="task_id is required for output")

        task = _task_tracker.find_task(task_id)
        if not task:
            return ToolResult(success=False, error=f"Task not found: {task_id}")

        return ToolResult(
            success=True,
            data={
                "stdout": "\n".join(task.get("stdout", [])),
                "stderr": "\n".join(task.get("stderr", [])),
                "status": task["status"]
            },
            metadata={"action": "output", "task_id": task["id"]}
        )

    def _kill_task(self, task_id: str) -> ToolResult:
        """Kill a running task."""
        if not task_id:
            return ToolResult(success=False, error="task_id is required for kill")

        task = _task_tracker.find_task(task_id)
        if not task:
            return ToolResult(success=False, error=f"Task not found: {task_id}")

        proc = task.get("process")
        if proc and proc.poll() is None:
            try:
                proc.terminate()
                _task_tracker.update_status(task["id"], "killed")
            except Exception as e:
                return ToolResult(success=False, error=f"Failed to kill: {e}")

        return ToolResult(
            success=True,
            data={"task_id": task["id"], "status": "killed"},
            metadata={"action": "kill"}
        )


# =============================================================================
# BASH OUTPUT TOOL
# =============================================================================

class BashOutputTool(Tool):
    """
    Retrieve output from a running or completed background bash shell.

    Claude Code parity: Implements BashOutput tool for monitoring.

    Features:
    - Returns new output since last check
    - Shows stdout and stderr
    - Reports shell status
    - Supports regex filtering

    Example:
        result = await bash_output.execute(bash_id="task_1", filter="ERROR")
    """

    def __init__(self):
        super().__init__()
        self.name = "bash_output"
        self.category = ToolCategory.EXECUTION
        self.description = "Get output from a background shell"
        self.parameters = {
            "bash_id": {
                "type": "string",
                "description": "The ID of the background shell to retrieve output from",
                "required": True
            },
            "filter": {
                "type": "string",
                "description": "Optional regex to filter output lines",
                "required": False
            }
        }
        # Track read positions per shell
        self._read_positions: Dict[str, int] = {}

    async def _execute_validated(self, **kwargs) -> ToolResult:
        """Get output from background shell."""
        bash_id = kwargs.get("bash_id", "")
        filter_pattern = kwargs.get("filter")

        if not bash_id:
            return ToolResult(success=False, error="bash_id is required")

        # Find task
        task = _task_tracker.find_task(bash_id)
        if not task:
            return ToolResult(
                success=False,
                error=f"Shell not found: {bash_id}. Use background_task(action='list') to see shells."
            )

        # Normalize task_id
        task_id = task["id"]

        # Update status if process finished
        proc = task.get("process")
        if proc and task["status"] == "running" and proc.poll() is not None:
            _task_tracker.update_status(
                task_id,
                "completed" if proc.returncode == 0 else "failed",
                proc.returncode
            )
            task = _task_tracker.get_task(task_id)

        # Get stdout and stderr
        stdout_lines = task.get("stdout", [])
        stderr_lines = task.get("stderr", [])

        # Get last read position
        last_pos = self._read_positions.get(task_id, 0)

        # Get new output since last read
        all_output = stdout_lines + stderr_lines
        new_output = all_output[last_pos:]

        # Update read position
        self._read_positions[task_id] = len(all_output)

        # Apply filter if provided
        if filter_pattern and new_output:
            try:
                pattern = re.compile(filter_pattern)
                new_output = [line for line in new_output if pattern.search(line)]
            except re.error as e:
                return ToolResult(success=False, error=f"Invalid regex pattern: {e}")

        return ToolResult(
            success=True,
            data={
                "shell_id": task_id,
                "status": task["status"],
                "output": "\n".join(new_output),
                "lines_returned": len(new_output),
                "is_complete": task["status"] in ("completed", "failed", "killed"),
                "return_code": task.get("return_code")
            },
            metadata={
                "command": task.get("command", "")[:50],
                "filtered": bool(filter_pattern),
                "total_lines": len(all_output)
            }
        )


# =============================================================================
# KILL SHELL TOOL
# =============================================================================

class KillShellTool(Tool):
    """
    Kill a running background bash shell by its ID.

    Claude Code parity: Implements KillShell tool for termination.

    Example:
        result = await kill_shell.execute(shell_id="task_1")
    """

    def __init__(self):
        super().__init__()
        self.name = "kill_shell"
        self.category = ToolCategory.EXECUTION
        self.description = "Kill a running background shell"
        self.parameters = {
            "shell_id": {
                "type": "string",
                "description": "The ID of the background shell to kill",
                "required": True
            }
        }

    async def _execute_validated(self, **kwargs) -> ToolResult:
        """Kill background shell."""
        shell_id = kwargs.get("shell_id", "")

        if not shell_id:
            return ToolResult(success=False, error="shell_id is required")

        # Find task
        task = _task_tracker.find_task(shell_id)
        if not task:
            return ToolResult(
                success=False,
                error=f"Shell not found: {shell_id}. Use background_task(action='list') to see shells."
            )

        task_id = task["id"]

        # Check if already terminated
        if task["status"] in ("completed", "failed", "killed"):
            return ToolResult(
                success=True,
                data={
                    "shell_id": task_id,
                    "status": task["status"],
                    "message": f"Shell already {task['status']}"
                },
                metadata={"already_terminated": True}
            )

        # Kill the process
        proc = task.get("process")
        if proc:
            try:
                # Try graceful termination first
                proc.terminate()

                # Wait briefly for graceful shutdown
                try:
                    proc.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    # Force kill if not responding
                    proc.kill()
                    proc.wait(timeout=1)

                _task_tracker.update_status(task_id, "killed", -signal.SIGTERM)

                return ToolResult(
                    success=True,
                    data={
                        "shell_id": task_id,
                        "status": "killed",
                        "message": "Shell terminated successfully"
                    },
                    metadata={"command": task.get("command", "")[:50]}
                )

            except Exception as e:
                logger.error(f"Failed to kill shell {task_id}: {e}")
                return ToolResult(success=False, error=f"Failed to kill shell: {e}")

        return ToolResult(
            success=False,
            error="No process associated with shell"
        )


# =============================================================================
# REGISTRY HELPER
# =============================================================================

def get_execution_tools() -> List[Tool]:
    """Get all execution/background tools."""
    return [
        BackgroundTaskTool(),
        BashOutputTool(),
        KillShellTool(),
    ]


# For testing - allow clearing state
def clear_task_state() -> None:
    """Clear task tracker state (for testing)."""
    _task_tracker.clear_all()


__all__ = [
    "BackgroundTaskTool",
    "BashOutputTool",
    "KillShellTool",
    "get_execution_tools",
    "clear_task_state",
]
