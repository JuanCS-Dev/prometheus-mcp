"""
Git Inspect Tools - Read-Only Git Operations
=============================================

Contains:
- GitStatusEnhancedTool: Detailed git status
- GitLogTool: Commit history
- GitDiffEnhancedTool: Diff with statistics

All tools in this module are read-only and safe.

Author: JuanCS Dev
Date: 2025-11-27
"""

from __future__ import annotations

import logging
import re
import subprocess
from typing import Dict, List

from jdev_cli.tools.base import Tool, ToolCategory, ToolResult

logger = logging.getLogger(__name__)


# =============================================================================
# GIT HELPER
# =============================================================================

async def run_git_command(*args: str, timeout: int = 30) -> ToolResult:
    """
    Run a git command safely.

    Args:
        *args: Git command arguments (without 'git')
        timeout: Command timeout in seconds

    Returns:
        ToolResult with stdout/stderr
    """
    try:
        result = subprocess.run(
            ["git", *args],
            capture_output=True,
            text=True,
            timeout=timeout
        )
        return ToolResult(
            success=result.returncode == 0,
            data=result.stdout,
            error=result.stderr if result.returncode != 0 else None
        )
    except subprocess.TimeoutExpired:
        return ToolResult(success=False, error=f"Git command timed out after {timeout}s")
    except FileNotFoundError:
        return ToolResult(success=False, error="Git is not installed or not in PATH")
    except Exception as e:
        logger.error(f"Git command failed: {e}")
        return ToolResult(success=False, error=str(e))


# =============================================================================
# GIT STATUS ENHANCED
# =============================================================================

class GitStatusEnhancedTool(Tool):
    """
    Enhanced git status with detailed information.

    Returns:
    - Current branch
    - Tracking branch status (ahead/behind)
    - Staged/unstaged/untracked files
    - Optional diff statistics

    Example:
        result = await status.execute(include_diff_stats=True)
        # result.data contains: branch, ahead, behind, staged, modified, etc.
    """

    def __init__(self):
        super().__init__()
        self.name = "git_status_enhanced"
        self.category = ToolCategory.GIT
        self.description = "Get detailed git status information"
        self.parameters = {
            "include_diff_stats": {
                "type": "boolean",
                "description": "Include diff statistics (default: False)",
                "required": False
            }
        }

    async def _execute_validated(self, **kwargs) -> ToolResult:
        """Get enhanced git status."""
        include_diff_stats = kwargs.get("include_diff_stats", False)

        try:
            # Get current branch
            branch_result = await run_git_command("rev-parse", "--abbrev-ref", "HEAD")
            current_branch = branch_result.data.strip() if branch_result.success else "unknown"

            # Get status (porcelain v2 for machine parsing)
            status_result = await run_git_command("status", "--porcelain=v2", "--branch")

            if not status_result.success:
                return ToolResult(success=False, error=status_result.error)

            # Parse status
            parsed = self._parse_status_v2(status_result.data)

            # Get tracking info (ahead/behind)
            ahead, behind = 0, 0
            tracking_result = await run_git_command(
                "rev-list", "--left-right", "--count", f"{current_branch}@{{u}}...HEAD"
            )
            if tracking_result.success:
                parts = tracking_result.data.strip().split()
                if len(parts) == 2:
                    behind, ahead = int(parts[0]), int(parts[1])

            # Get diff stats if requested
            diff_stats = None
            if include_diff_stats and (parsed["staged"] or parsed["modified"]):
                diff_result = await run_git_command("diff", "--stat", "--cached")
                if diff_result.success:
                    diff_stats = diff_result.data

            return ToolResult(
                success=True,
                data={
                    "branch": current_branch,
                    "ahead": ahead,
                    "behind": behind,
                    "is_clean": len(parsed["staged"]) == 0 and len(parsed["modified"]) == 0,
                    "staged": parsed["staged"],
                    "modified": parsed["modified"],
                    "untracked": parsed["untracked"],
                    "deleted": parsed["deleted"],
                    "renamed": parsed["renamed"],
                    "diff_stats": diff_stats,
                    "summary": self._format_summary(parsed, ahead, behind)
                },
                metadata={
                    "file_count": sum(len(v) for v in parsed.values()),
                    "branch": current_branch
                }
            )

        except Exception as e:
            logger.error(f"GitStatus error: {e}")
            return ToolResult(success=False, error=str(e))

    def _parse_status_v2(self, output: str) -> Dict[str, List[str]]:
        """Parse git status --porcelain=v2 output."""
        result = {
            "staged": [],
            "modified": [],
            "untracked": [],
            "deleted": [],
            "renamed": [],
        }

        for line in output.split("\n"):
            if not line:
                continue

            if line.startswith("# "):
                continue  # Header line

            if line.startswith("? "):
                # Untracked file
                result["untracked"].append(line[2:])

            elif line.startswith("1 ") or line.startswith("2 "):
                # Changed entry (1 = ordinary, 2 = rename/copy)
                parts = line.split("\t")
                if len(parts) >= 2:
                    status_part = parts[0].split()
                    xy = status_part[1] if len(status_part) > 1 else ".."
                    path = parts[-1]

                    # X = staged, Y = working tree
                    if xy[0] in "MARC":
                        result["staged"].append(path)
                    if xy[1] == "M":
                        result["modified"].append(path)
                    if xy[1] == "D" or xy[0] == "D":
                        result["deleted"].append(path)
                    if xy[0] == "R":
                        result["renamed"].append(path)

        return result

    def _format_summary(self, parsed: Dict, ahead: int, behind: int) -> str:
        """Format a human-readable summary."""
        parts = []

        if ahead:
            parts.append(f"ahead {ahead}")
        if behind:
            parts.append(f"behind {behind}")
        if parsed["staged"]:
            parts.append(f"{len(parsed['staged'])} staged")
        if parsed["modified"]:
            parts.append(f"{len(parsed['modified'])} modified")
        if parsed["untracked"]:
            parts.append(f"{len(parsed['untracked'])} untracked")
        if parsed["deleted"]:
            parts.append(f"{len(parsed['deleted'])} deleted")

        return ", ".join(parts) if parts else "clean"


# =============================================================================
# GIT LOG TOOL
# =============================================================================

class GitLogTool(Tool):
    """
    Get git commit history.

    Returns recent commits with hash, author, date, and message.

    Example:
        result = await log.execute(count=20, oneline=False)
    """

    def __init__(self):
        super().__init__()
        self.name = "git_log"
        self.category = ToolCategory.GIT
        self.description = "Get git commit history"
        self.parameters = {
            "count": {
                "type": "integer",
                "description": "Number of commits to show (default: 10, max: 100)",
                "required": False
            },
            "oneline": {
                "type": "boolean",
                "description": "One line per commit (default: True)",
                "required": False
            },
            "branch": {
                "type": "string",
                "description": "Branch to show history for (default: current)",
                "required": False
            }
        }

    async def _execute_validated(self, **kwargs) -> ToolResult:
        """Get git log."""
        count = kwargs.get("count", 10)
        oneline = kwargs.get("oneline", True)
        branch = kwargs.get("branch", "")

        # Validate count
        if not isinstance(count, int) or count < 1:
            count = 10
        count = min(count, 100)  # Hard limit

        try:
            args = ["log", f"-{count}"]

            if oneline:
                args.append("--oneline")
            else:
                args.extend(["--format=%H|%an|%ar|%s"])

            if branch:
                args.append(branch)

            result = await run_git_command(*args)

            if not result.success:
                return ToolResult(success=False, error=result.error)

            commits = []
            for line in result.data.strip().split("\n"):
                if not line:
                    continue

                if oneline:
                    parts = line.split(" ", 1)
                    commits.append({
                        "hash": parts[0],
                        "message": parts[1] if len(parts) > 1 else ""
                    })
                else:
                    parts = line.split("|")
                    if len(parts) >= 4:
                        commits.append({
                            "hash": parts[0][:7],
                            "author": parts[1],
                            "date": parts[2],
                            "message": parts[3]
                        })

            return ToolResult(
                success=True,
                data={"commits": commits},
                metadata={"count": len(commits), "branch": branch or "HEAD"}
            )

        except Exception as e:
            logger.error(f"GitLog error: {e}")
            return ToolResult(success=False, error=str(e))


# =============================================================================
# GIT DIFF ENHANCED
# =============================================================================

class GitDiffEnhancedTool(Tool):
    """
    Enhanced git diff with statistics.

    Shows changes between commits, branches, or working tree.

    Example:
        result = await diff.execute(target="main", stat_only=True)
    """

    def __init__(self):
        super().__init__()
        self.name = "git_diff_enhanced"
        self.category = ToolCategory.GIT
        self.description = "Get git diff with statistics"
        self.parameters = {
            "target": {
                "type": "string",
                "description": "Target to diff against (e.g., 'HEAD~1', 'main', 'staged')",
                "required": False
            },
            "stat_only": {
                "type": "boolean",
                "description": "Show only statistics (default: False)",
                "required": False
            },
            "file": {
                "type": "string",
                "description": "Specific file to diff",
                "required": False
            }
        }

    async def _execute_validated(self, **kwargs) -> ToolResult:
        """Get git diff."""
        target = kwargs.get("target", "")
        stat_only = kwargs.get("stat_only", False)
        file_path = kwargs.get("file", "")

        try:
            args = ["diff"]

            if target == "staged":
                args.append("--cached")
            elif target:
                args.append(target)

            if stat_only:
                args.append("--stat")

            if file_path:
                args.extend(["--", file_path])

            result = await run_git_command(*args)

            if not result.success:
                return ToolResult(success=False, error=result.error)

            # Get stats separately if not stat_only
            stats = {"files": 0, "insertions": 0, "deletions": 0}
            if not stat_only:
                stat_args = ["diff", "--stat"]
                if target == "staged":
                    stat_args.append("--cached")
                elif target:
                    stat_args.append(target)

                stat_result = await run_git_command(*stat_args)
                if stat_result.success:
                    stats = self._parse_diff_stats(stat_result.data)

            return ToolResult(
                success=True,
                data={
                    "diff": result.data[:10000] if not stat_only else None,
                    "stats": result.data if stat_only else None,
                    "files_changed": stats.get("files", 0),
                    "insertions": stats.get("insertions", 0),
                    "deletions": stats.get("deletions", 0),
                },
                metadata={"target": target or "working tree"}
            )

        except Exception as e:
            logger.error(f"GitDiff error: {e}")
            return ToolResult(success=False, error=str(e))

    def _parse_diff_stats(self, output: str) -> Dict[str, int]:
        """Parse diff --stat output."""
        # Last line format: "X files changed, Y insertions(+), Z deletions(-)"
        match = re.search(
            r'(\d+) files? changed(?:, (\d+) insertions?\(\+\))?(?:, (\d+) deletions?\(-\))?',
            output
        )

        if match:
            return {
                "files": int(match.group(1)),
                "insertions": int(match.group(2) or 0),
                "deletions": int(match.group(3) or 0),
            }

        return {"files": 0, "insertions": 0, "deletions": 0}


# =============================================================================
# REGISTRY HELPER
# =============================================================================

def get_git_inspect_tools() -> List[Tool]:
    """Get all read-only git tools."""
    return [
        GitStatusEnhancedTool(),
        GitLogTool(),
        GitDiffEnhancedTool(),
    ]


__all__ = [
    "GitStatusEnhancedTool",
    "GitLogTool",
    "GitDiffEnhancedTool",
    "get_git_inspect_tools",
    "run_git_command",
]
