"""Git operation tools."""

import subprocess
from typing import Optional

from .base import ToolResult, ToolCategory
from .validated import ValidatedTool


class GitStatusTool(ValidatedTool):
    """Get git repository status."""

    def __init__(self):
        super().__init__()
        self.category = ToolCategory.GIT
        self.description = "Get git repository status"
        self.parameters = {
            "path": {
                "type": "string",
                "description": "Repository path (default: current directory)",
                "required": False
            }
        }

    def get_validators(self):
        """Validate parameters."""
        return {}

    async def _execute_validated(self, path: str = ".") -> ToolResult:
        """Get git status."""
        try:
            # Get branch
            result = subprocess.run(
                ["git", "-C", path, "rev-parse", "--abbrev-ref", "HEAD"],
                capture_output=True,
                text=True,
                timeout=5
            )
            branch = result.stdout.strip() if result.returncode == 0 else "unknown"

            # Get status
            result = subprocess.run(
                ["git", "-C", path, "status", "--porcelain"],
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode != 0:
                return ToolResult(
                    success=False,
                    error="Not a git repository or git not available"
                )

            lines = result.stdout.split('\n') if result.stdout else []

            modified = []
            untracked = []
            staged = []

            for line in lines:
                if not line or not line.strip():
                    continue
                if len(line) < 3:
                    continue
                status = line[:2]
                filename = line[3:].strip()  # Strip whitespace

                if status[0] in ['M', 'A', 'D', 'R']:
                    staged.append(filename)
                if status[1] == 'M':
                    modified.append(filename)
                if status == '??':
                    untracked.append(filename)

            return ToolResult(
                success=True,
                data={
                    "branch": branch,
                    "modified": modified,
                    "untracked": untracked,
                    "staged": staged
                },
                metadata={
                    "branch": branch,
                    "total_changes": len(modified) + len(untracked) + len(staged)
                }
            )

        except Exception as e:
            return ToolResult(success=False, error=str(e))


class GitDiffTool(ValidatedTool):
    """Get git diff of changes."""

    def __init__(self):
        super().__init__()
        self.category = ToolCategory.GIT
        self.description = "Get diff of uncommitted changes"
        self.parameters = {
            "path": {
                "type": "string",
                "description": "Repository path (default: current directory)",
                "required": False
            },
            "file": {
                "type": "string",
                "description": "Specific file to diff",
                "required": False
            },
            "staged": {
                "type": "boolean",
                "description": "Show staged changes only",
                "required": False
            }
        }
    def get_validators(self):
        """Validate parameters."""
        return {}


    async def _execute_validated(self, path: str = ".", file: Optional[str] = None, staged: bool = False) -> ToolResult:
        """Get git diff."""
        try:
            cmd = ["git", "-C", path, "diff"]

            if staged:
                cmd.append("--staged")

            if file:
                cmd.append(file)

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode != 0:
                return ToolResult(
                    success=False,
                    error=result.stderr or "Git diff failed"
                )

            return ToolResult(
                success=True,
                data={"diff": result.stdout, "has_changes": bool(result.stdout.strip())},
                metadata={
                    "file": file or "all",
                    "staged": staged,
                    "has_changes": bool(result.stdout.strip())
                }
            )

        except Exception as e:
            return ToolResult(success=False, error=str(e))
