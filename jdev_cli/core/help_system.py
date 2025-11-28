"""Minimal help system stub (consolidated from removed module)."""
from typing import List, Optional


class HelpSystem:
    """Minimal help system for CLI."""

    COMMANDS = {
        "help": "Show this help message",
        "exit": "Exit the CLI",
        "quit": "Exit the CLI",
        "clear": "Clear the screen",
        "status": "Show current status",
        "config": "Show or edit configuration",
    }

    def get_help(self, command: Optional[str] = None) -> str:
        """Get help text for a command or all commands."""
        if command:
            return self.COMMANDS.get(command, f"No help available for '{command}'")

        lines = ["Available commands:", ""]
        for cmd, desc in sorted(self.COMMANDS.items()):
            lines.append(f"  {cmd:15} {desc}")
        return "\n".join(lines)

    def search(self, query: str) -> List[str]:
        """Search commands matching query."""
        query_lower = query.lower()
        return [cmd for cmd in self.COMMANDS if query_lower in cmd.lower()]

    def suggest(self, partial: str) -> List[str]:
        """Suggest commands based on partial input."""
        return [cmd for cmd in self.COMMANDS if cmd.startswith(partial.lower())]


# Singleton instance
help_system = HelpSystem()
