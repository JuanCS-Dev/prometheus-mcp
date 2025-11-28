"""Context and session management tools."""

import json
from pathlib import Path
from datetime import datetime
from typing import Optional

from .base import ToolResult, ToolCategory
from .validated import ValidatedTool


class GetContextTool(ValidatedTool):
    """Get current session context."""

    def __init__(self):
        super().__init__()
        self.category = ToolCategory.CONTEXT
        self.description = "Get current session context"
        self.parameters = {}

    async def _execute_validated(self, session_context=None) -> ToolResult:
        """Get context."""
        try:
            import os
            import subprocess

            # Get git branch if in repo
            try:
                result = subprocess.run(
                    ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                    capture_output=True,
                    text=True,
                    timeout=2
                )
                git_branch = result.stdout.strip() if result.returncode == 0 else None
            except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
                git_branch = None

            context = {
                "cwd": os.getcwd(),
                "git_branch": git_branch,
                "modified_files": list(session_context.modified_files) if session_context else [],
                "read_files": list(session_context.read_files) if session_context else [],
                "tool_calls": len(session_context.tool_calls) if session_context else 0
            }

            return ToolResult(
                success=True,
                data=context,
                metadata=context
            )
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class SaveSessionTool(ValidatedTool):
    """Save conversation session to file."""

    def __init__(self):
        super().__init__()
        self.category = ToolCategory.CONTEXT
        self.description = "Save conversation session to file"
        self.parameters = {
            "path": {
                "type": "string",
                "description": "Output file path",
                "required": True
            },
            "format": {
                "type": "string",
                "description": "Format: markdown or json",
                "required": False
            }
        }
    def get_validators(self):
        """Validate parameters."""
        return {}


    async def _execute_validated(self, path: str, format: str = "markdown", session_context=None) -> ToolResult:
        """Save session."""
        try:
            if not session_context:
                return ToolResult(success=False, error="No session context available")

            file_path = Path(path)

            if format == "json":
                # Save as JSON
                data = {
                    "timestamp": datetime.now().isoformat(),
                    "cwd": session_context.cwd,
                    "modified_files": list(session_context.modified_files),
                    "read_files": list(session_context.read_files),
                    "tool_calls": session_context.tool_calls
                }
                file_path.write_text(json.dumps(data, indent=2))
            else:
                # Save as Markdown
                content = "# QWEN-DEV-CLI Session\n\n"
                content += f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                content += f"**Working Directory:** `{session_context.cwd}`\n\n"

                if session_context.modified_files:
                    content += "## Modified Files\n\n"
                    for f in session_context.modified_files:
                        content += f"- `{f}`\n"
                    content += "\n"

                if session_context.read_files:
                    content += "## Read Files\n\n"
                    for f in session_context.read_files:
                        content += f"- `{f}`\n"
                    content += "\n"

                content += "## Tool Calls\n\n"
                content += f"Total: {len(session_context.tool_calls)}\n\n"

                for i, call in enumerate(session_context.tool_calls, 1):
                    content += f"### {i}. {call['tool']}\n\n"
                    content += f"```json\n{json.dumps(call['args'], indent=2)}\n```\n\n"
                    content += f"**Success:** {call['success']}\n\n"

                file_path.write_text(content)

            return ToolResult(
                success=True,
                data=f"Session saved to {path}",
                metadata={"path": str(file_path), "format": format}
            )
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class RestoreBackupTool(ValidatedTool):
    """Restore file from backup."""

    def __init__(self):
        super().__init__()
        self.category = ToolCategory.CONTEXT
        self.description = "Restore file from backup"
        self.parameters = {
            "file": {
                "type": "string",
                "description": "File to restore",
                "required": True
            },
            "backup_id": {
                "type": "string",
                "description": "Specific backup ID (or latest)",
                "required": False
            }
        }
    def get_validators(self):
        """Validate parameters."""
        return {}


    async def _execute_validated(self, file: str, backup_id: Optional[str] = None) -> ToolResult:
        """Restore from backup."""
        try:
            import shutil
            import glob

            backup_dir = Path(".qwen_backups")

            if not backup_dir.exists():
                return ToolResult(success=False, error="No backups directory found")

            # Find backups for this file
            file_name = Path(file).name
            pattern = str(backup_dir / f"{file_name}.*.bak")
            backups = sorted(glob.glob(pattern), reverse=True)

            if not backups:
                return ToolResult(success=False, error=f"No backups found for {file}")

            # Use latest backup
            backup_path = Path(backups[0])
            dest_path = Path(file)

            # Restore
            shutil.copy2(str(backup_path), str(dest_path))

            return ToolResult(
                success=True,
                data=f"Restored {file} from {backup_path.name}",
                metadata={
                    "file": str(dest_path),
                    "backup": str(backup_path)
                }
            )
        except Exception as e:
            return ToolResult(success=False, error=str(e))
