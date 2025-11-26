"""
CustomCommandsManager - Slash Command System
=============================================

Extracted from Bridge GOD CLASS (Nov 2025 Refactoring).

Provides Claude Code-style custom slash commands:
- Load commands from .juancs/commands/*.md
- Execute commands with argument substitution
- Create/delete commands (project or global scope)
- Security: Path traversal prevention

Features:
- Project-local commands (.juancs/commands/)
- Global commands (~/.juancs/commands/)
- Argument substitution ($ARGUMENTS, {args}, $1, $2, etc.)
- Description extraction from markdown headers
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class CustomCommandsManager:
    """
    Manages custom slash commands with Claude Code parity.

    Commands are markdown files in .juancs/commands/ directory:
    - Filename (without .md) becomes the command name
    - File contents becomes the prompt template
    - First heading (#) becomes the description

    Usage:
        manager = CustomCommandsManager()
        commands = manager.load_commands()
        expanded = manager.execute_command("review", "main.py")
    """

    def __init__(
        self,
        project_dir: Optional[Path] = None,
        global_dir: Optional[Path] = None
    ):
        """
        Initialize CustomCommandsManager.

        Args:
            project_dir: Project commands directory. Defaults to ./.juancs/commands
            global_dir: Global commands directory. Defaults to ~/.juancs/commands
        """
        self._project_dir = project_dir
        self._global_dir = global_dir or (Path.home() / ".juancs" / "commands")
        self._commands: Dict[str, Dict[str, Any]] = {}
        self._loaded = False

    def _get_project_commands_dir(self) -> Path:
        """Get project-local commands directory."""
        if self._project_dir:
            return self._project_dir
        return Path.cwd() / ".juancs" / "commands"

    def _get_global_commands_dir(self) -> Path:
        """Get global commands directory."""
        return self._global_dir

    def _get_commands_dir(self) -> Path:
        """
        Get the active commands directory.

        Priority: project-local > global
        """
        project_dir = self._get_project_commands_dir()
        if project_dir.exists():
            return project_dir
        return self._get_global_commands_dir()

    def load_commands(self, force_reload: bool = False) -> Dict[str, Dict[str, Any]]:
        """
        Load custom commands from .juancs/commands/ directory.

        Commands are .md files where:
        - Filename (without .md) becomes the command name
        - File contents becomes the prompt template
        - First # heading becomes the description

        Args:
            force_reload: Force reload even if already loaded

        Returns:
            Dictionary of command_name -> {name, prompt, description, path, type}
        """
        if self._loaded and not force_reload:
            return self._commands

        self._commands = {}

        # Load from both project and global directories
        for scope, commands_dir in [
            ("project", self._get_project_commands_dir()),
            ("global", self._get_global_commands_dir())
        ]:
            if not commands_dir.exists():
                continue

            for md_file in commands_dir.glob("*.md"):
                command_name = md_file.stem

                # Skip if already loaded from project (project takes priority)
                if command_name in self._commands:
                    continue

                try:
                    content = md_file.read_text(encoding="utf-8")
                    description = self._extract_description(content)

                    self._commands[command_name] = {
                        "name": command_name,
                        "prompt": content,
                        "description": description or f"Custom command: {command_name}",
                        "path": str(md_file),
                        "type": scope
                    }

                except Exception as e:
                    logger.debug(f"Failed to load command {md_file}: {e}")
                    continue

        self._loaded = True
        return self._commands

    def _extract_description(self, content: str) -> str:
        """
        Extract description from command content.

        Looks for:
        - First markdown heading (# Description)
        - HTML comment (<!-- description -->)
        """
        lines = content.strip().split("\n")
        if not lines:
            return ""

        first_line = lines[0]

        if first_line.startswith("#"):
            # Markdown heading
            return first_line.lstrip("# ").strip()

        if first_line.startswith("<!--") and "-->" in first_line:
            # HTML comment
            return first_line.replace("<!--", "").replace("-->", "").strip()

        return ""

    def get_commands(self) -> Dict[str, Dict[str, Any]]:
        """Get all loaded custom commands."""
        return self.load_commands()

    def get_command(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific custom command by name.

        Args:
            name: Command name (without /)

        Returns:
            Command info dict or None if not found
        """
        commands = self.load_commands()
        return commands.get(name)

    def execute_command(self, name: str, args: str = "") -> Optional[str]:
        """
        Execute a custom command and return its expanded prompt.

        Supports argument substitution:
        - $ARGUMENTS: Full argument string
        - {args}: Full argument string
        - $1, $2, ...: Positional arguments

        Args:
            name: Command name (without /)
            args: Arguments to substitute in the prompt

        Returns:
            Expanded prompt string or None if command not found
        """
        command = self.get_command(name)
        if not command:
            return None

        prompt = command["prompt"]

        if args:
            # Full argument substitution
            prompt = prompt.replace("$ARGUMENTS", args)
            prompt = prompt.replace("{args}", args)

            # Positional argument substitution
            arg_parts = args.split()
            for i, arg in enumerate(arg_parts, 1):
                prompt = prompt.replace(f"${i}", arg)

        return prompt

    def _sanitize_command_name(self, name: str) -> str:
        """
        Sanitize command name to prevent path traversal and injection.

        Only allows alphanumeric, hyphens, and underscores.
        Max length: 50 characters.
        """
        sanitized = re.sub(r'[^a-zA-Z0-9_-]', '', name)
        if not sanitized:
            sanitized = "unnamed_command"
        return sanitized[:50]

    def create_command(
        self,
        name: str,
        prompt: str,
        description: str = "",
        scope: str = "project"
    ) -> Dict[str, Any]:
        """
        Create a new custom command.

        Args:
            name: Command name (without /)
            prompt: The prompt template
            description: Optional description
            scope: "project" or "global"

        Returns:
            Created command info

        Raises:
            ValueError: If command name contains path traversal
        """
        safe_name = self._sanitize_command_name(name)

        if scope == "project":
            commands_dir = self._get_project_commands_dir()
        else:
            commands_dir = self._get_global_commands_dir()

        commands_dir.mkdir(parents=True, exist_ok=True)

        command_file = commands_dir / f"{safe_name}.md"

        # Security: Verify path is within commands directory
        try:
            command_file.resolve().relative_to(commands_dir.resolve())
        except ValueError:
            raise ValueError(f"Invalid command name: path traversal detected")

        # Build content with optional description header
        content = prompt
        if description:
            content = f"# {description}\n\n{prompt}"

        command_file.write_text(content, encoding="utf-8")

        # Update cache
        self._commands[safe_name] = {
            "name": safe_name,
            "prompt": prompt,
            "description": description or f"Custom command: {safe_name}",
            "path": str(command_file),
            "type": scope
        }

        logger.info(f"Created command: {safe_name} ({scope})")
        return self._commands[safe_name]

    def delete_command(self, name: str) -> bool:
        """
        Delete a custom command.

        Args:
            name: Command name to delete

        Returns:
            True if deleted, False if not found or error
        """
        command = self.get_command(name)
        if not command:
            return False

        try:
            Path(command["path"]).unlink()
            if name in self._commands:
                del self._commands[name]
            logger.info(f"Deleted command: {name}")
            return True
        except Exception as e:
            logger.warning(f"Failed to delete command {name}: {e}")
            return False

    def refresh(self) -> Dict[str, Dict[str, Any]]:
        """Force reload of all custom commands."""
        self._loaded = False
        self._commands = {}
        return self.load_commands()

    def list_commands(self) -> List[Dict[str, Any]]:
        """
        List all commands in a structured format.

        Returns:
            List of command info dicts
        """
        commands = self.load_commands()
        return list(commands.values())

    def command_exists(self, name: str) -> bool:
        """Check if a command exists."""
        return self.get_command(name) is not None

    def get_command_names(self) -> List[str]:
        """Get list of all command names."""
        return list(self.load_commands().keys())

    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about loaded commands.

        Returns:
            Stats dictionary
        """
        commands = self.load_commands()
        project_count = sum(1 for c in commands.values() if c["type"] == "project")
        global_count = sum(1 for c in commands.values() if c["type"] == "global")

        return {
            "total_commands": len(commands),
            "project_commands": project_count,
            "global_commands": global_count,
            "project_dir": str(self._get_project_commands_dir()),
            "global_dir": str(self._get_global_commands_dir()),
            "loaded": self._loaded
        }
