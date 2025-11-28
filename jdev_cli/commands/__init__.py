"""
Slash commands for qwen-dev-cli.

Slash commands provide quick access to common operations.
"""

from typing import Dict, Any, Callable, Optional, List
from dataclasses import dataclass


@dataclass
class SlashCommand:
    """Slash command definition."""

    name: str
    description: str
    usage: str
    handler: Callable
    aliases: Optional[List[str]] = None
    requires_session: bool = False

    def __post_init__(self):
        if self.aliases is None:
            self.aliases = []


class SlashCommandRegistry:
    """Registry for slash commands."""

    def __init__(self):
        self._commands: Dict[str, SlashCommand] = {}
        self._aliases: Dict[str, str] = {}

    def register(self, command: SlashCommand):
        """Register a slash command."""
        self._commands[command.name] = command

        for alias in command.aliases:
            self._aliases[alias] = command.name

    def get(self, name: str) -> Optional[SlashCommand]:
        """Get command by name or alias."""
        # Check aliases first
        if name in self._aliases:
            name = self._aliases[name]

        return self._commands.get(name)

    def list(self) -> List[SlashCommand]:
        """List all commands."""
        return list(self._commands.values())

    def exists(self, name: str) -> bool:
        """Check if command exists."""
        return name in self._commands or name in self._aliases


# Global registry
slash_registry = SlashCommandRegistry()
