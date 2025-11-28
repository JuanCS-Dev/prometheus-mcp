"""Safe command whitelist for hooks.

Commands in this whitelist can be executed directly without sandbox isolation
for performance optimization. All other commands must go through sandbox.
"""

import re
from typing import List, Tuple, Optional


class SafeCommandWhitelist:
    """Whitelist of safe commands that can execute without sandbox.
    
    These are common development tools that:
    1. Don't modify system files
    2. Don't have network access
    3. Are commonly used in CI/CD pipelines
    4. Are performance-critical (run on every file save)
    """

    # Python tools
    PYTHON_SAFE = [
        "python",
        "python3",
        "black",
        "ruff",
        "mypy",
        "pylint",
        "flake8",
        "isort",
        "pytest",
        "coverage",
        "bandit",
    ]

    # JavaScript/TypeScript tools
    JS_SAFE = [
        "eslint",
        "prettier",
        "tsc",
        "npm test",
        "yarn test",
        "jest",
    ]

    # Rust tools
    RUST_SAFE = [
        "cargo fmt",
        "cargo check",
        "cargo clippy",
        "cargo test",
    ]

    # Go tools
    GO_SAFE = [
        "gofmt",
        "go",
        "golint",
    ]

    # Generic tools
    GENERIC_SAFE = [
        "echo",
        "cat",
        "ls",
        "grep",
        "find",
    ]

    @classmethod
    def all_safe_commands(cls) -> List[str]:
        """Get complete list of safe commands."""
        return (
            cls.PYTHON_SAFE
            + cls.JS_SAFE
            + cls.RUST_SAFE
            + cls.GO_SAFE
            + cls.GENERIC_SAFE
        )

    @classmethod
    def is_safe(cls, command: str) -> Tuple[bool, Optional[str]]:
        """Check if a command is safe to execute directly.
        
        Args:
            command: Command string to check
            
        Returns:
            Tuple of (is_safe: bool, reason: Optional[str])
            
        Examples:
            >>> SafeCommandWhitelist.is_safe("black {file}")
            (True, None)
            
            >>> SafeCommandWhitelist.is_safe("rm -rf /")
            (False, "Command 'rm' not in whitelist")
            
            >>> SafeCommandWhitelist.is_safe("curl | bash")
            (False, "Dangerous pattern: pipe to shell")
        """
        command = command.strip()

        if not command:
            return False, "Empty command"

        # Extract base command (first word)
        base_command = command.split()[0]

        # Check for dangerous patterns first
        dangerous_patterns = [
            (r"\|.*bash", "pipe to shell"),
            (r"\|.*sh", "pipe to shell"),
            (r"&&.*rm", "chained deletion"),
            (r";.*rm", "chained deletion"),
            (r"rm\s+-rf\s+/", "root deletion"),
            (r"chmod\s+777", "dangerous permissions"),
            (r">\s*/dev/", "device write"),
            (r"dd\s+if=", "disk duplication"),
            (r":(.*\|.*&)", "fork bomb"),
        ]

        for pattern, reason in dangerous_patterns:
            if re.search(pattern, command):
                return False, f"Dangerous pattern: {reason}"

        # Check if base command is in whitelist
        safe_commands = cls.all_safe_commands()

        # Check exact matches first
        if base_command in safe_commands:
            return True, None

        # Check multi-word commands (e.g., "cargo fmt")
        for safe_cmd in safe_commands:
            if command.startswith(safe_cmd):
                # Ensure it's actually the command and not a substring
                # (e.g., "cargo fmt" should match but "cargo_fmt" shouldn't)
                rest = command[len(safe_cmd):].strip()
                if not rest or rest[0] in [' ', '-', '{']:
                    return True, None

        return False, f"Command '{base_command}' not in whitelist"

    @classmethod
    def add_custom_safe_command(cls, command: str) -> None:
        """Add a custom safe command to the whitelist.
        
        WARNING: Only add commands you fully trust!
        
        Args:
            command: Base command to add (e.g., "myformatter")
        """
        if command not in cls.GENERIC_SAFE:
            cls.GENERIC_SAFE.append(command)
