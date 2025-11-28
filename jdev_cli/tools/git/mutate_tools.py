"""
Git Mutate Tools - Write Operations with Safety
================================================

Contains:
- GitCommitTool: Create commits with HEREDOC support
- GitPRCreateTool: Create GitHub PRs via gh CLI

All tools in this module modify the repository and include safety checks.

Author: JuanCS Dev
Date: 2025-11-27
"""

from __future__ import annotations

import logging
import subprocess
from typing import Any, Dict, List

from jdev_cli.tools.base import Tool, ToolCategory, ToolResult
from jdev_cli.tools.git.safety import validate_commit_message
from jdev_cli.tools.git.inspect_tools import run_git_command

logger = logging.getLogger(__name__)


# =============================================================================
# GIT COMMIT TOOL
# =============================================================================

class GitCommitTool(Tool):
    """
    Create git commits with Claude Code conventions.

    Features:
    - Validates changes before commit
    - Adds Juan-Dev-Code signature
    - Respects safety protocols
    - Supports pre-commit hooks
    - Uses HEREDOC-style message passing for proper multi-line support

    Commit message format:
    ```
    <type>(<scope>): <description>

    <body>

    Generated with Juan-Dev-Code

    Co-Authored-By: Juan-Dev-Code <noreply@juancs.dev>
    ```

    Example:
        result = await commit.execute(
            message="feat(auth): add JWT token validation",
            files=["src/auth.py"],
            add_signature=True
        )
    """

    SIGNATURE = """

Generated with Juan-Dev-Code

Co-Authored-By: Juan-Dev-Code <noreply@juancs.dev>"""

    def __init__(self):
        super().__init__()
        self.name = "git_commit"
        self.category = ToolCategory.GIT
        self.description = "Create a git commit with Claude Code conventions"
        self.parameters = {
            "message": {
                "type": "string",
                "description": "Commit message (without signature)",
                "required": True
            },
            "files": {
                "type": "array",
                "description": "Files to stage (default: all modified)",
                "required": False
            },
            "amend": {
                "type": "boolean",
                "description": "Amend previous commit (requires explicit permission)",
                "required": False
            },
            "add_signature": {
                "type": "boolean",
                "description": "Add Juan-Dev-Code signature (default: True)",
                "required": False
            }
        }

    async def _execute_validated(self, **kwargs) -> ToolResult:
        """
        Create git commit with HEREDOC support for multi-line messages.

        Claude Code Parity: Uses subprocess stdin to pass commit messages,
        which is equivalent to HEREDOC pattern in shell:

        ```bash
        git commit -m "$(cat <<'EOF'
        Commit message here.

        Generated with Juan-Dev-Code

        Co-Authored-By: Juan-Dev-Code <noreply@juancs.dev>
        EOF
        )"
        ```
        """
        message = kwargs.get("message", "")
        files = kwargs.get("files", [])
        amend = kwargs.get("amend", False)
        add_signature = kwargs.get("add_signature", True)

        # Validate message
        if not message:
            return ToolResult(success=False, error="Commit message is required")

        is_valid, reason = validate_commit_message(message)
        if not is_valid:
            return ToolResult(success=False, error=reason)

        try:
            # Safety check for amend
            if amend:
                author_check = await self._check_authorship()
                if not author_check["safe_to_amend"]:
                    return ToolResult(
                        success=False,
                        error=f"Cannot amend: {author_check['reason']}"
                    )

            # Stage files
            stage_result = await self._stage_files(files)
            if not stage_result.success:
                return stage_result

            # Check if there are staged changes
            diff_result = await run_git_command("diff", "--cached", "--quiet")
            if diff_result.success:
                return ToolResult(
                    success=False,
                    error="No changes staged for commit"
                )

            # Build commit message
            full_message = self._build_commit_message(message, add_signature)

            # Use HEREDOC-style commit via stdin
            commit_result = await self._run_git_commit_heredoc(full_message, amend)

            if not commit_result.success:
                # Check if pre-commit hook modified files
                if commit_result.error and "pre-commit" in commit_result.error.lower():
                    return ToolResult(
                        success=False,
                        error="Pre-commit hook modified files. Review changes and retry.",
                        data={"hook_triggered": True}
                    )
                return ToolResult(success=False, error=commit_result.error)

            # Get commit hash
            hash_result = await run_git_command("rev-parse", "--short", "HEAD")
            commit_hash = hash_result.data.strip() if hash_result.success else "unknown"

            return ToolResult(
                success=True,
                data={
                    "commit": commit_hash,
                    "message": message[:100],
                    "amended": amend,
                    "files_committed": len(files) if files else "all staged",
                    "heredoc_used": True
                },
                metadata={"hash": commit_hash}
            )

        except Exception as e:
            logger.error(f"GitCommit error: {e}")
            return ToolResult(success=False, error=str(e))

    async def _stage_files(self, files: List[str]) -> ToolResult:
        """Stage files for commit."""
        if files:
            for file in files:
                # Validate file path (basic security check)
                if ".." in file or file.startswith("/"):
                    return ToolResult(success=False, error=f"Invalid file path: {file}")

                stage_result = await run_git_command("add", file)
                if not stage_result.success:
                    return ToolResult(
                        success=False,
                        error=f"Failed to stage {file}: {stage_result.error}"
                    )
        else:
            # Stage all modified files
            stage_result = await run_git_command("add", "-A")
            if not stage_result.success:
                return ToolResult(success=False, error=f"Failed to stage: {stage_result.error}")

        return ToolResult(success=True, data="Files staged")

    async def _run_git_commit_heredoc(self, message: str, amend: bool = False) -> ToolResult:
        """
        Run git commit with HEREDOC-style message passing.

        Uses subprocess stdin to pass multi-line commit messages properly,
        avoiding shell escaping issues. Equivalent to:

        ```bash
        git commit -F - <<'EOF'
        <message>
        EOF
        ```
        """
        try:
            args = ["git", "commit", "-F", "-"]  # Read message from stdin
            if amend:
                args.append("--amend")

            result = subprocess.run(
                args,
                input=message,  # Pass message via stdin (HEREDOC equivalent)
                capture_output=True,
                text=True,
                timeout=60
            )

            return ToolResult(
                success=result.returncode == 0,
                data=result.stdout,
                error=result.stderr if result.returncode != 0 else None
            )

        except subprocess.TimeoutExpired:
            return ToolResult(success=False, error="Git commit timed out")
        except Exception as e:
            return ToolResult(success=False, error=str(e))

    async def _check_authorship(self) -> Dict[str, Any]:
        """Check if safe to amend previous commit."""
        # Get last commit author
        result = await run_git_command("log", "-1", "--format=%an %ae")
        if not result.success:
            return {"safe_to_amend": False, "reason": "Could not check authorship"}

        author = result.data.strip()

        # Check if pushed
        status_result = await run_git_command("status", "-sb")
        if status_result.success and "ahead" not in status_result.data:
            return {"safe_to_amend": False, "reason": "Commit may already be pushed"}

        # Allow amend for Juan-Dev-Code-authored commits or unpushed commits
        if "claude" in author.lower() or "juan" in author.lower() or "noreply@" in author.lower():
            return {"safe_to_amend": True, "reason": "Tool-authored commit"}

        return {
            "safe_to_amend": True,
            "reason": f"Unpushed commit by {author}",
            "warning": "Amending another developer's commit"
        }

    def _build_commit_message(self, message: str, add_signature: bool) -> str:
        """Build full commit message with optional signature."""
        if not add_signature:
            return message

        return message + self.SIGNATURE


# =============================================================================
# PR CREATE TOOL
# =============================================================================

class GitPRCreateTool(Tool):
    """
    Create GitHub Pull Request using gh CLI.

    Claude Code parity: Create PRs with standard format.
    Requires: gh CLI installed and authenticated.

    Example:
        result = await pr.execute(
            title="feat: Add user authentication",
            body="## Summary\\n- Added JWT token support",
            base="main",
            draft=True
        )
    """

    SIGNATURE = "\n\nGenerated with Juan-Dev-Code"

    def __init__(self):
        super().__init__()
        self.name = "git_pr_create"
        self.category = ToolCategory.GIT
        self.description = "Create a GitHub Pull Request"
        self.parameters = {
            "title": {
                "type": "string",
                "description": "PR title",
                "required": True
            },
            "body": {
                "type": "string",
                "description": "PR description (markdown)",
                "required": False
            },
            "base": {
                "type": "string",
                "description": "Base branch (default: main)",
                "required": False
            },
            "draft": {
                "type": "boolean",
                "description": "Create as draft PR",
                "required": False
            }
        }

    async def _execute_validated(self, **kwargs) -> ToolResult:
        """Create PR using gh CLI."""
        title = kwargs.get("title", "")
        body = kwargs.get("body", "")
        base = kwargs.get("base", "main")
        draft = kwargs.get("draft", False)

        if not title:
            return ToolResult(success=False, error="PR title is required")

        if len(title) > 256:
            return ToolResult(success=False, error="PR title too long (max 256 chars)")

        # Check if gh is available
        gh_check = await self._check_gh_cli()
        if not gh_check.success:
            return gh_check

        try:
            # Build PR body with signature
            full_body = self._build_pr_body(body)

            # Use subprocess with stdin for body (HEREDOC equivalent)
            args = [
                "gh", "pr", "create",
                "--title", title,
                "--body-file", "-",  # Read body from stdin
                "--base", base,
            ]

            if draft:
                args.append("--draft")

            result = subprocess.run(
                args,
                input=full_body,
                capture_output=True,
                text=True,
                timeout=60
            )

            if result.returncode != 0:
                return ToolResult(success=False, error=result.stderr)

            # Extract PR URL
            pr_url = result.stdout.strip()

            return ToolResult(
                success=True,
                data={
                    "url": pr_url,
                    "title": title,
                    "base": base,
                    "draft": draft,
                },
                metadata={"created": True}
            )

        except subprocess.TimeoutExpired:
            return ToolResult(success=False, error="PR creation timed out")
        except Exception as e:
            logger.error(f"GitPRCreate error: {e}")
            return ToolResult(success=False, error=str(e))

    async def _check_gh_cli(self) -> ToolResult:
        """Check if gh CLI is available and authenticated."""
        try:
            result = subprocess.run(
                ["gh", "--version"],
                capture_output=True,
                timeout=10
            )
            if result.returncode != 0:
                return ToolResult(
                    success=False,
                    error="GitHub CLI (gh) not working properly"
                )

            # Check auth status
            auth_result = subprocess.run(
                ["gh", "auth", "status"],
                capture_output=True,
                timeout=10
            )
            if auth_result.returncode != 0:
                return ToolResult(
                    success=False,
                    error="GitHub CLI not authenticated. Run: gh auth login"
                )

            return ToolResult(success=True, data="gh CLI ready")

        except FileNotFoundError:
            return ToolResult(
                success=False,
                error="GitHub CLI (gh) not found. Install from: https://cli.github.com"
            )
        except Exception as e:
            return ToolResult(success=False, error=str(e))

    def _build_pr_body(self, body: str) -> str:
        """Build PR body with Juan-Dev-Code signature."""
        if not body:
            return f"## Summary\n\n_No description provided._\n{self.SIGNATURE}"

        return body + self.SIGNATURE


# =============================================================================
# REGISTRY HELPER
# =============================================================================

def get_git_mutate_tools() -> List[Tool]:
    """Get all write git tools."""
    return [
        GitCommitTool(),
        GitPRCreateTool(),
    ]


__all__ = [
    "GitCommitTool",
    "GitPRCreateTool",
    "get_git_mutate_tools",
]
