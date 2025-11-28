"""
Git Integration Plugin.

SCALE & SUSTAIN Phase 2.1 - Plugin Architecture.

Provides Git VCS integration:
- /git status, /git diff, /git log commands
- Pre-commit hooks integration
- Branch management
- Commit message generation

Author: JuanCS Dev
Date: 2025-11-26
"""

import logging
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any, List

from plugins.core import (
    Plugin,
    PluginMetadata,
    PluginPriority,
    PluginContext,
)

logger = logging.getLogger(__name__)


class GitPlugin(Plugin):
    """
    Git integration plugin.

    Commands:
        /git status  - Show working tree status
        /git diff    - Show changes
        /git log     - Show recent commits
        /git branch  - List/manage branches
        /git commit  - Create commit with AI message

    Capabilities:
        - vcs: Version control system
        - git: Git-specific operations
    """

    def __init__(self):
        super().__init__()
        self._repo_root: Optional[Path] = None
        self._context: Optional[PluginContext] = None

    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="git",
            version="1.0.0",
            description="Git version control integration",
            author="JuanCS Dev",
            priority=PluginPriority.HIGH,
            dependencies=[],
            provides=["vcs", "git"],
        )

    async def activate(self, context: PluginContext) -> None:
        """Activate plugin and detect git repository."""
        self._context = context
        self._repo_root = self._find_repo_root()

        if self._repo_root:
            logger.info(f"Git plugin activated for repo: {self._repo_root}")
        else:
            logger.info("Git plugin activated (no repo detected)")

    async def deactivate(self) -> None:
        """Deactivate plugin."""
        self._context = None
        self._repo_root = None

    def _find_repo_root(self) -> Optional[Path]:
        """Find git repository root."""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--show-toplevel"],
                capture_output=True,
                text=True,
                check=True
            )
            return Path(result.stdout.strip())
        except subprocess.CalledProcessError:
            return None

    def on_command(self, command: str, args: str) -> Optional[Any]:
        """Handle git commands."""
        if not command.startswith("git"):
            return None

        # Parse subcommand
        parts = command.split()
        if len(parts) == 1:
            # Just /git - show status
            return self._run_git_command(["status", "--short"])

        subcommand = parts[1] if len(parts) > 1 else "status"
        extra_args = args.split() if args else []

        handlers = {
            "status": self._cmd_status,
            "diff": self._cmd_diff,
            "log": self._cmd_log,
            "branch": self._cmd_branch,
            "add": self._cmd_add,
            "commit": self._cmd_commit,
            "push": self._cmd_push,
            "pull": self._cmd_pull,
        }

        handler = handlers.get(subcommand)
        if handler:
            return handler(extra_args)

        # Pass through to git
        return self._run_git_command([subcommand] + extra_args)

    def _cmd_status(self, args: List[str]) -> Dict[str, Any]:
        """Handle /git status."""
        result = self._run_git_command(["status", "--short"] + args)
        return {
            "type": "git_status",
            "output": result.get("output", ""),
            "clean": not result.get("output", "").strip()
        }

    def _cmd_diff(self, args: List[str]) -> Dict[str, Any]:
        """Handle /git diff."""
        # Default to staged + unstaged
        if not args:
            staged = self._run_git_command(["diff", "--cached"])
            unstaged = self._run_git_command(["diff"])
            return {
                "type": "git_diff",
                "staged": staged.get("output", ""),
                "unstaged": unstaged.get("output", ""),
            }
        return self._run_git_command(["diff"] + args)

    def _cmd_log(self, args: List[str]) -> Dict[str, Any]:
        """Handle /git log."""
        default_args = ["--oneline", "-10"]
        return self._run_git_command(["log"] + (args or default_args))

    def _cmd_branch(self, args: List[str]) -> Dict[str, Any]:
        """Handle /git branch."""
        return self._run_git_command(["branch"] + args)

    def _cmd_add(self, args: List[str]) -> Dict[str, Any]:
        """Handle /git add."""
        if not args:
            args = ["."]  # Default to all
        return self._run_git_command(["add"] + args)

    def _cmd_commit(self, args: List[str]) -> Dict[str, Any]:
        """Handle /git commit."""
        if not args or "-m" not in args:
            # Generate commit message suggestion
            diff = self._run_git_command(["diff", "--cached", "--stat"])
            return {
                "type": "commit_prompt",
                "staged_changes": diff.get("output", ""),
                "suggestion": "Please provide a commit message with -m 'message'"
            }
        return self._run_git_command(["commit"] + args)

    def _cmd_push(self, args: List[str]) -> Dict[str, Any]:
        """Handle /git push."""
        return self._run_git_command(["push"] + args)

    def _cmd_pull(self, args: List[str]) -> Dict[str, Any]:
        """Handle /git pull."""
        return self._run_git_command(["pull"] + args)

    def _run_git_command(self, args: List[str]) -> Dict[str, Any]:
        """Run a git command and return result."""
        try:
            result = subprocess.run(
                ["git"] + args,
                capture_output=True,
                text=True,
                cwd=self._repo_root or Path.cwd(),
                timeout=30
            )

            return {
                "success": result.returncode == 0,
                "output": result.stdout,
                "error": result.stderr if result.returncode != 0 else None,
                "command": f"git {' '.join(args)}"
            }
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": "Command timed out",
                "command": f"git {' '.join(args)}"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "command": f"git {' '.join(args)}"
            }

    # ========== Tool Hooks ==========

    def on_tool_execute(
        self,
        tool_name: str,
        params: Dict[str, Any]
    ) -> Optional[Any]:
        """Intercept git-related tool calls."""
        # Could add pre-commit validation here
        if tool_name in ["write_file", "edit_file"]:
            # Track modified files for commit suggestions
            pass
        return None

    # ========== Utility Methods ==========

    def get_current_branch(self) -> Optional[str]:
        """Get current branch name."""
        result = self._run_git_command(["branch", "--show-current"])
        if result.get("success"):
            return result.get("output", "").strip()
        return None

    def get_uncommitted_changes(self) -> List[str]:
        """Get list of uncommitted files."""
        result = self._run_git_command(["status", "--porcelain"])
        if result.get("success"):
            return [
                line[3:] for line in result.get("output", "").splitlines()
                if line.strip()
            ]
        return []

    def is_clean(self) -> bool:
        """Check if working tree is clean."""
        return not self.get_uncommitted_changes()


__all__ = ['GitPlugin']
