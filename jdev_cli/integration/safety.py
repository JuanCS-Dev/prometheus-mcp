"""Safety validator for shell commands and tool executions.

Inspired by:
- Claude Code: Hook-based validation system
- GitHub Codex: Sandboxing and permission whitelisting
- Cursor AI: Security-first design
"""

import re
import os
from typing import Dict, Any, List, Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class SafetyValidator:
    """Validates tool calls and shell commands for safety.
    
    Implements multi-layer security:
    1. Dangerous pattern detection (Claude Code strategy)
    2. Permission whitelisting (Codex strategy)
    3. Path traversal prevention (Cursor strategy)
    4. Resource limit enforcement
    """

    # Dangerous shell patterns (Claude Code inspired)
    DANGEROUS_PATTERNS = [
        (r"rm\s+-rf\s+/", "Attempting to delete root directory"),
        (r"rm\s+-rf\s+\*", "Attempting to delete all files"),
        (r":(){ :|:& };:", "Fork bomb detected"),
        (r"dd\s+if=/dev/(zero|urandom)", "Attempting to fill disk"),
        (r"chmod\s+-R\s+777", "Attempting to set dangerous permissions"),
        (r"mkfs\.", "Attempting to format filesystem"),
        (r"shutdown|reboot|halt", "Attempting to shutdown system"),
        (r">\s*/dev/sda", "Attempting to overwrite disk"),
        (r"curl\s+.*\|\s*bash", "Piping remote code to bash"),
        (r"wget\s+.*\|\s*sh", "Piping remote code to shell"),
    ]

    # Dangerous tool operations
    DANGEROUS_OPERATIONS = {
        "delete_file": [
            (r"^/", "Cannot delete from root"),
            (r"\.\./", "Path traversal detected"),
        ],
        "write_file": [
            (r"^/etc/", "Cannot write to /etc"),
            (r"^/usr/", "Cannot write to /usr"),
            (r"^/bin/", "Cannot write to /bin"),
            (r"^/sbin/", "Cannot write to /sbin"),
        ],
        "bash_command": DANGEROUS_PATTERNS,
    }

    def __init__(
        self,
        enable_whitelist: bool = True,
        enable_blacklist: bool = True,
        max_file_size: int = 10 * 1024 * 1024,  # 10MB
        allowed_paths: Optional[List[str]] = None,
    ):
        """Initialize safety validator.
        
        Args:
            enable_whitelist: Enable permission whitelist
            enable_blacklist: Enable dangerous pattern blacklist
            max_file_size: Maximum file size for operations (bytes)
            allowed_paths: List of allowed path prefixes (None = current dir only)
        """
        self.enable_whitelist = enable_whitelist
        self.enable_blacklist = enable_blacklist
        self.max_file_size = max_file_size

        # Default to current working directory
        if allowed_paths is None:
            self.allowed_paths = [os.getcwd()]
        else:
            self.allowed_paths = [os.path.abspath(p) for p in allowed_paths]

        # Permission whitelist (can be extended by user)
        self.whitelisted_commands = {
            "git status", "git log", "git diff", "git show",
            "ls", "pwd", "cat", "grep", "find", "tree",
            "echo", "printf", "wc", "head", "tail",
        }

        logger.info(f"SafetyValidator initialized with {len(self.allowed_paths)} allowed paths")

    def is_safe(self, tool_call: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Check if a tool call is safe to execute.
        
        Args:
            tool_call: Tool call dictionary with 'tool', 'arguments'
            
        Returns:
            Tuple of (is_safe, reason_if_unsafe)
        """
        tool_name = tool_call.get("tool", "")
        arguments = tool_call.get("arguments", {})

        # Check blacklist patterns
        if self.enable_blacklist:
            is_safe, reason = self._check_blacklist(tool_name, arguments)
            if not is_safe:
                logger.warning(f"Blacklist violation: {reason}")
                return False, reason

        # Check whitelist for bash commands
        if self.enable_whitelist and tool_name == "bash_command":
            is_safe, reason = self._check_whitelist(arguments)
            if not is_safe:
                logger.warning(f"Whitelist violation: {reason}")
                return False, reason

        # Check path safety
        if "path" in arguments or "file" in arguments:
            path = arguments.get("path") or arguments.get("file")
            is_safe, reason = self._check_path_safety(path)
            if not is_safe:
                logger.warning(f"Path safety violation: {reason}")
                return False, reason

        # Check file size limits
        if tool_name in ["write_file", "read_file"]:
            path = arguments.get("path") or arguments.get("file")
            if path and os.path.exists(path):
                size = os.path.getsize(path)
                if size > self.max_file_size:
                    return False, f"File too large: {size} > {self.max_file_size}"

        return True, None

    def _check_blacklist(
        self,
        tool_name: str,
        arguments: Dict[str, Any]
    ) -> Tuple[bool, Optional[str]]:
        """Check against dangerous patterns."""
        patterns = self.DANGEROUS_OPERATIONS.get(tool_name, [])

        # For bash commands, check the actual command
        if tool_name == "bash_command":
            command = arguments.get("command", "")
            for pattern, reason in patterns:
                if re.search(pattern, command, re.IGNORECASE):
                    return False, f"Dangerous pattern detected: {reason}"

        # For file operations, check paths
        elif patterns:
            path = arguments.get("path") or arguments.get("file") or ""
            for pattern, reason in patterns:
                if re.search(pattern, path):
                    return False, f"Dangerous path pattern: {reason}"

        return True, None

    def _check_whitelist(self, arguments: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Check if bash command is whitelisted."""
        command = arguments.get("command", "").strip()

        # Extract base command (first word)
        base_cmd = command.split()[0] if command else ""

        # Check if any whitelisted command matches
        for allowed in self.whitelisted_commands:
            if command.startswith(allowed) or base_cmd == allowed.split()[0]:
                return True, None

        # Special case: Allow commands in current directory
        if command.startswith("./") or base_cmd.startswith("./"):
            return True, None

        return False, f"Command not whitelisted: {base_cmd}"

    def _check_path_safety(self, path: str) -> Tuple[bool, Optional[str]]:
        """Check if path is safe to access."""
        if not path:
            return True, None

        try:
            # Resolve absolute path
            abs_path = os.path.abspath(path)

            # Check against allowed paths
            for allowed in self.allowed_paths:
                if abs_path.startswith(allowed):
                    return True, None

            return False, f"Path outside allowed directories: {abs_path}"

        except Exception as e:
            return False, f"Invalid path: {str(e)}"

    def add_whitelisted_command(self, command: str):
        """Add a command to the whitelist."""
        self.whitelisted_commands.add(command)
        logger.info(f"Added to whitelist: {command}")

    def add_allowed_path(self, path: str):
        """Add a path to allowed paths."""
        abs_path = os.path.abspath(path)
        if abs_path not in self.allowed_paths:
            self.allowed_paths.append(abs_path)
            logger.info(f"Added allowed path: {abs_path}")

    def get_safety_report(self) -> Dict[str, Any]:
        """Get current safety configuration."""
        return {
            "whitelist_enabled": self.enable_whitelist,
            "blacklist_enabled": self.enable_blacklist,
            "max_file_size": self.max_file_size,
            "allowed_paths": self.allowed_paths,
            "whitelisted_commands": list(self.whitelisted_commands),
            "dangerous_patterns": len(self.DANGEROUS_PATTERNS),
        }


# Global instance (can be configured)
safety_validator = SafetyValidator()
