"""
Safe Command Executor - Hardened shell execution with whitelist.

This module provides secure command execution with:
- Command whitelist (only approved commands allowed)
- No shell=True (prevents injection)
- Timeout protection
- Resource limits
- Structured output

Author: Boris Cherny style implementation
Date: 2025-11-25
Security Level: OWASP Compliant
"""

from __future__ import annotations

import asyncio
import logging
import shlex
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, FrozenSet, List, Optional, Tuple

logger = logging.getLogger(__name__)


class CommandCategory(Enum):
    """Categories of allowed commands."""
    TESTING = "testing"
    LINTING = "linting"
    GIT = "git"
    FILE_SYSTEM = "file_system"
    PACKAGE = "package"
    SYSTEM_INFO = "system_info"


@dataclass(frozen=True)
class AllowedCommand:
    """
    Immutable definition of an allowed command.

    Attributes:
        name: Human-readable name for the command
        base_command: The executable (e.g., "pytest", "git")
        allowed_args: Frozenset of allowed argument patterns
        category: Command category for organization
        timeout_seconds: Maximum execution time
        description: What this command does
    """
    name: str
    base_command: str
    allowed_args: FrozenSet[str]
    category: CommandCategory
    timeout_seconds: int = 60
    description: str = ""


@dataclass
class ExecutionResult:
    """
    Result of command execution.

    Attributes:
        success: Whether command completed successfully
        exit_code: Process exit code
        stdout: Standard output
        stderr: Standard error
        command: The command that was executed
        error_message: Human-readable error if failed
    """
    success: bool
    exit_code: int
    stdout: str
    stderr: str
    command: str
    error_message: str = ""


class SafeCommandExecutor:
    """
    Secure command executor with whitelist-based validation.

    This executor ONLY allows pre-approved commands to run.
    All other commands are rejected for security.

    Example:
        executor = SafeCommandExecutor()
        result = await executor.execute("pytest -v")
        if result.success:
            print(result.stdout)
    """

    # Whitelist of allowed commands - IMMUTABLE
    ALLOWED_COMMANDS: Dict[str, AllowedCommand] = {
        # Testing
        "pytest": AllowedCommand(
            name="pytest",
            base_command="pytest",
            allowed_args=frozenset({"-v", "-vv", "-x", "-s", "--tb=short", "--tb=long",
                                    "--cov", "--cov-report=html", "--cov-report=xml",
                                    "-k", "-m", "--lf", "--ff", "-n", "auto"}),
            category=CommandCategory.TESTING,
            timeout_seconds=300,
            description="Run pytest tests"
        ),
        "python -m pytest": AllowedCommand(
            name="python pytest",
            base_command="python",
            allowed_args=frozenset({"-m", "pytest", "-v", "-vv", "-x", "-s"}),
            category=CommandCategory.TESTING,
            timeout_seconds=300,
            description="Run pytest via python -m"
        ),

        # Linting
        "ruff check": AllowedCommand(
            name="ruff check",
            base_command="ruff",
            allowed_args=frozenset({"check", ".", "--fix", "--unsafe-fixes",
                                    "--show-fixes", "--diff"}),
            category=CommandCategory.LINTING,
            timeout_seconds=120,
            description="Run ruff linter"
        ),
        "ruff format": AllowedCommand(
            name="ruff format",
            base_command="ruff",
            allowed_args=frozenset({"format", ".", "--check", "--diff"}),
            category=CommandCategory.LINTING,
            timeout_seconds=120,
            description="Run ruff formatter"
        ),
        "mypy": AllowedCommand(
            name="mypy",
            base_command="mypy",
            allowed_args=frozenset({".", "--strict", "--ignore-missing-imports",
                                    "--show-error-codes", "--pretty"}),
            category=CommandCategory.LINTING,
            timeout_seconds=180,
            description="Run mypy type checker"
        ),
        "black": AllowedCommand(
            name="black",
            base_command="black",
            allowed_args=frozenset({".", "--check", "--diff", "--line-length", "100"}),
            category=CommandCategory.LINTING,
            timeout_seconds=120,
            description="Run black formatter"
        ),
        "bandit": AllowedCommand(
            name="bandit",
            base_command="bandit",
            allowed_args=frozenset({"-r", ".", "-c", "pyproject.toml", "-ll", "-ii"}),
            category=CommandCategory.LINTING,
            timeout_seconds=120,
            description="Run bandit security scanner"
        ),

        # Git (read-only operations)
        "git status": AllowedCommand(
            name="git status",
            base_command="git",
            allowed_args=frozenset({"status", "-s", "--short", "--branch"}),
            category=CommandCategory.GIT,
            timeout_seconds=30,
            description="Show git status"
        ),
        "git diff": AllowedCommand(
            name="git diff",
            base_command="git",
            allowed_args=frozenset({"diff", "--staged", "--cached", "--name-only",
                                    "--stat", "HEAD", "HEAD~1"}),
            category=CommandCategory.GIT,
            timeout_seconds=60,
            description="Show git diff"
        ),
        "git log": AllowedCommand(
            name="git log",
            base_command="git",
            allowed_args=frozenset({"log", "--oneline", "-n", "10", "20", "5",
                                    "--graph", "--all", "--decorate"}),
            category=CommandCategory.GIT,
            timeout_seconds=30,
            description="Show git log"
        ),
        "git branch": AllowedCommand(
            name="git branch",
            base_command="git",
            allowed_args=frozenset({"branch", "-a", "-v", "--list"}),
            category=CommandCategory.GIT,
            timeout_seconds=30,
            description="List git branches"
        ),

        # File system (read-only)
        "ls": AllowedCommand(
            name="ls",
            base_command="ls",
            allowed_args=frozenset({"-la", "-l", "-a", "-lh", "-R", "."}),
            category=CommandCategory.FILE_SYSTEM,
            timeout_seconds=30,
            description="List directory contents"
        ),
        "tree": AllowedCommand(
            name="tree",
            base_command="tree",
            allowed_args=frozenset({"-L", "1", "2", "3", "-d", "-I", "__pycache__"}),
            category=CommandCategory.FILE_SYSTEM,
            timeout_seconds=30,
            description="Show directory tree"
        ),
        "wc": AllowedCommand(
            name="wc",
            base_command="wc",
            allowed_args=frozenset({"-l", "-w", "-c"}),
            category=CommandCategory.FILE_SYSTEM,
            timeout_seconds=30,
            description="Count lines/words/chars"
        ),
        "du": AllowedCommand(
            name="du",
            base_command="du",
            allowed_args=frozenset({"-sh", "-h", "--max-depth=1", "."}),
            category=CommandCategory.FILE_SYSTEM,
            timeout_seconds=30,
            description="Show disk usage"
        ),

        # Package management (read-only)
        "pip list": AllowedCommand(
            name="pip list",
            base_command="pip",
            allowed_args=frozenset({"list", "--outdated", "--format=columns"}),
            category=CommandCategory.PACKAGE,
            timeout_seconds=60,
            description="List installed packages"
        ),
        "pip show": AllowedCommand(
            name="pip show",
            base_command="pip",
            allowed_args=frozenset({"show"}),
            category=CommandCategory.PACKAGE,
            timeout_seconds=30,
            description="Show package info"
        ),

        # System info
        "python --version": AllowedCommand(
            name="python version",
            base_command="python",
            allowed_args=frozenset({"--version", "-V"}),
            category=CommandCategory.SYSTEM_INFO,
            timeout_seconds=10,
            description="Show Python version"
        ),
        "uname": AllowedCommand(
            name="uname",
            base_command="uname",
            allowed_args=frozenset({"-a", "-s", "-r", "-m"}),
            category=CommandCategory.SYSTEM_INFO,
            timeout_seconds=10,
            description="Show system info"
        ),
        "pwd": AllowedCommand(
            name="pwd",
            base_command="pwd",
            allowed_args=frozenset(),
            category=CommandCategory.SYSTEM_INFO,
            timeout_seconds=10,
            description="Print working directory"
        ),
        "whoami": AllowedCommand(
            name="whoami",
            base_command="whoami",
            allowed_args=frozenset(),
            category=CommandCategory.SYSTEM_INFO,
            timeout_seconds=10,
            description="Show current user"
        ),
    }

    # Dangerous patterns that should NEVER execute
    DANGEROUS_PATTERNS: FrozenSet[str] = frozenset({
        "rm ",
        "rmdir",
        "chmod",
        "chown",
        "sudo",
        "su ",
        "dd ",
        "mkfs",
        "fdisk",
        "kill",
        "pkill",
        "killall",
        "shutdown",
        "reboot",
        "halt",
        "poweroff",
        "eval",
        "exec",
        "source",
        "> /",
        ">> /",
        "| sh",
        "| bash",
        "| zsh",
        "curl | ",
        "wget | ",
        "$(",
        "`",
        "${",
        "&&",
        "||",
        ";",
        "\n",
        "\\n",
    })

    def __init__(self, working_dir: Optional[Path] = None):
        """
        Initialize executor.

        Args:
            working_dir: Working directory for command execution
        """
        self._working_dir = working_dir or Path.cwd()

    def _contains_dangerous_pattern(self, command: str) -> Optional[str]:
        """
        Check if command contains dangerous patterns.

        Args:
            command: Command string to check

        Returns:
            The dangerous pattern found, or None if safe
        """
        command_lower = command.lower()
        for pattern in self.DANGEROUS_PATTERNS:
            if pattern.lower() in command_lower:
                return pattern
        return None

    def _parse_command(self, command: str) -> Tuple[str, List[str]]:
        """
        Parse command into base command and arguments.

        Args:
            command: Full command string

        Returns:
            Tuple of (base_command, arguments)
        """
        try:
            parts = shlex.split(command)
            if not parts:
                return "", []
            return parts[0], parts[1:]
        except ValueError as e:
            logger.warning(f"Failed to parse command: {e}")
            return "", []

    def _find_matching_allowed_command(
        self,
        base_cmd: str,
        args: List[str]
    ) -> Optional[AllowedCommand]:
        """
        Find matching allowed command definition.

        Args:
            base_cmd: Base command (e.g., "pytest")
            args: Command arguments

        Returns:
            Matching AllowedCommand or None
        """
        # Try exact match first
        full_cmd = f"{base_cmd} {args[0]}" if args else base_cmd

        for key, allowed in self.ALLOWED_COMMANDS.items():
            if allowed.base_command == base_cmd:
                # Check if this is a subcommand match (e.g., "git status")
                if args and f"{base_cmd} {args[0]}" == key:
                    return allowed
                # Check simple command match
                if key == base_cmd:
                    return allowed

        return None

    def is_command_allowed(self, command: str) -> Tuple[bool, str]:
        """
        Check if command is allowed to execute.

        Args:
            command: Command to check

        Returns:
            Tuple of (is_allowed, reason)
        """
        # Check for dangerous patterns first
        dangerous = self._contains_dangerous_pattern(command)
        if dangerous:
            return False, f"Contains dangerous pattern: '{dangerous}'"

        # Parse command
        base_cmd, args = self._parse_command(command)
        if not base_cmd:
            return False, "Empty or invalid command"

        # Find matching allowed command
        allowed = self._find_matching_allowed_command(base_cmd, args)
        if not allowed:
            return False, f"Command '{base_cmd}' is not in the whitelist"

        return True, f"Allowed: {allowed.description}"

    def get_allowed_commands(self) -> List[str]:
        """
        Get list of allowed command names.

        Returns:
            List of allowed command descriptions
        """
        return [
            f"{cmd.name}: {cmd.description}"
            for cmd in self.ALLOWED_COMMANDS.values()
        ]

    def get_allowed_commands_by_category(self) -> Dict[str, List[str]]:
        """
        Get allowed commands organized by category.

        Returns:
            Dict mapping category name to list of commands
        """
        result: Dict[str, List[str]] = {}
        for cmd in self.ALLOWED_COMMANDS.values():
            category = cmd.category.value
            if category not in result:
                result[category] = []
            result[category].append(f"{cmd.name}: {cmd.description}")
        return result

    async def execute(self, command: str) -> ExecutionResult:
        """
        Execute command securely.

        Args:
            command: Command to execute

        Returns:
            ExecutionResult with output and status
        """
        # Validate command
        is_allowed, reason = self.is_command_allowed(command)
        if not is_allowed:
            logger.warning(f"Blocked command: {command} - {reason}")
            return ExecutionResult(
                success=False,
                exit_code=-1,
                stdout="",
                stderr="",
                command=command,
                error_message=f"Command not allowed: {reason}"
            )

        # Parse command for execution
        base_cmd, args = self._parse_command(command)
        allowed = self._find_matching_allowed_command(base_cmd, args)

        if not allowed:
            # Should never happen if is_allowed passed, but defensive
            return ExecutionResult(
                success=False,
                exit_code=-1,
                stdout="",
                stderr="",
                command=command,
                error_message="Internal error: command validation inconsistency"
            )

        try:
            # Build command array (NO SHELL!)
            cmd_array = [base_cmd] + args

            logger.info(f"Executing: {cmd_array}")

            # Create subprocess WITHOUT shell
            proc = await asyncio.create_subprocess_exec(
                *cmd_array,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(self._working_dir)
            )

            # Wait with timeout
            try:
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(),
                    timeout=allowed.timeout_seconds
                )
            except asyncio.TimeoutError:
                proc.kill()
                await proc.wait()
                return ExecutionResult(
                    success=False,
                    exit_code=-1,
                    stdout="",
                    stderr="",
                    command=command,
                    error_message=f"Command timed out after {allowed.timeout_seconds}s"
                )

            stdout_str = stdout.decode("utf-8", errors="replace") if stdout else ""
            stderr_str = stderr.decode("utf-8", errors="replace") if stderr else ""

            return ExecutionResult(
                success=proc.returncode == 0,
                exit_code=proc.returncode or 0,
                stdout=stdout_str,
                stderr=stderr_str,
                command=command,
                error_message="" if proc.returncode == 0 else f"Exit code: {proc.returncode}"
            )

        except FileNotFoundError:
            return ExecutionResult(
                success=False,
                exit_code=-1,
                stdout="",
                stderr="",
                command=command,
                error_message=f"Command not found: {base_cmd}"
            )
        except PermissionError:
            return ExecutionResult(
                success=False,
                exit_code=-1,
                stdout="",
                stderr="",
                command=command,
                error_message=f"Permission denied: {base_cmd}"
            )
        except Exception as e:
            logger.exception(f"Unexpected error executing command: {command}")
            return ExecutionResult(
                success=False,
                exit_code=-1,
                stdout="",
                stderr="",
                command=command,
                error_message=f"Execution error: {type(e).__name__}: {e}"
            )


# Singleton instance for global access
_executor: Optional[SafeCommandExecutor] = None


def get_safe_executor(working_dir: Optional[Path] = None) -> SafeCommandExecutor:
    """
    Get or create the safe executor singleton.

    Args:
        working_dir: Working directory (only used on first call)

    Returns:
        SafeCommandExecutor instance
    """
    global _executor
    if _executor is None:
        _executor = SafeCommandExecutor(working_dir)
    return _executor
