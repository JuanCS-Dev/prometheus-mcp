"""Command palette with fuzzy search and command discovery."""

from typing import List, Dict, Callable, Optional
from dataclasses import dataclass
from enum import Enum
import re


class CommandCategory(Enum):
    """Command categories."""
    AGENT = "agent"
    SYSTEM = "system"
    HELP = "help"
    UI = "ui"
    TOOL = "tool"
    EDIT = "edit"
    CONTEXT = "context"
    SESSION = "session"
    TIMELINE = "timeline"
    ACCESSIBILITY = "accessibility"


@dataclass
class Command:
    """Command definition."""
    id: str
    label: str
    description: str
    category: str
    keybinding: Optional[str] = None
    handler: Optional[Callable] = None
    priority: int = 0


class CommandPalette:
    """Fuzzy command search and execution."""

    def __init__(self, context_manager=None):
        """Initialize palette with registered commands."""
        self.commands: List[Command] = []
        self.recent_commands: List[str] = []
        self.max_recent = 10
        self.context_manager = context_manager
        self._register_default_commands()

    def _register_default_commands(self):
        """Register built-in commands."""
        defaults = [
            Command("token.show", "Show Token Usage", "Display current token statistics", "Tools", "Ctrl+T"),
            Command("token.export", "Export Token Stats", "Save token usage to file", "Tools"),
            Command("preview.accept", "Accept Changes", "Apply preview changes", "Edit", "Ctrl+Enter"),
            Command("preview.reject", "Reject Changes", "Discard preview changes", "Edit", "Ctrl+Backspace"),
            Command("preview.undo", "Undo Preview", "Undo last preview change", "Edit", "Ctrl+Z"),
            Command("preview.redo", "Redo Preview", "Redo last undone change", "Edit", "Ctrl+Shift+Z"),
            Command("timeline.play", "Play Timeline", "Replay session timeline", "Timeline"),
            Command("timeline.export", "Export Timeline", "Save timeline to file", "Timeline"),
            Command("timeline.jump", "Jump to Event", "Navigate to specific event", "Timeline"),
            Command("context.show", "Show Context", "Display current context size", "Context"),
            Command("context.clear", "Clear Context", "Reset conversation context", "Context"),
            Command("help.shortcuts", "Show Keyboard Shortcuts", "Display all keybindings", "Help", "Ctrl+?"),
            Command("help.commands", "Show All Commands", "List available commands", "Help"),
            Command("accessibility.toggle", "Toggle High Contrast", "Enable/disable high contrast mode", "Accessibility"),
            Command("session.save", "Save Session", "Export current session", "Session"),
            Command("session.load", "Load Session", "Import saved session", "Session"),
        ]
        self.commands.extend(defaults)

    def register_command(self, command: Command):
        """Add custom command."""
        self.commands.append(command)

    def get_suggestions(self, query: str, max_results: int = 10) -> List[Dict]:
        """
        Fuzzy search commands.
        
        Args:
            query: Search string
            max_results: Maximum results to return
            
        Returns:
            Sorted list of matching commands
        """
        if not query:
            # Return recent + high priority, or first N commands
            recent = [c for c in self.commands if c.id in self.recent_commands[:5]]
            remaining = max_results - len(recent)

            if remaining > 0:
                high_priority = sorted(
                    [c for c in self.commands if c.id not in self.recent_commands],
                    key=lambda x: x.priority,
                    reverse=True
                )[:remaining]
                return [self._command_to_dict(c) for c in recent + high_priority]
            return [self._command_to_dict(c) for c in recent]

        # Fuzzy match with scoring
        results = []
        query_lower = query.lower()

        for cmd in self.commands:
            score = self._fuzzy_score(query_lower, cmd)
            if score > 0:
                results.append((score, cmd))

        # Sort by score descending, recent commands get boost
        results.sort(key=lambda x: (
            x[0] + (10 if x[1].id in self.recent_commands else 0),
            x[1].priority
        ), reverse=True)

        return [self._command_to_dict(c) for _, c in results[:max_results]]

    def _fuzzy_score(self, query: str, cmd: Command) -> int:
        """Calculate fuzzy match score."""
        score = 0
        label_lower = cmd.label.lower()
        desc_lower = cmd.description.lower()

        # Exact match
        if query == label_lower:
            return 1000

        # Starts with
        if label_lower.startswith(query):
            score += 500
        elif desc_lower.startswith(query):
            score += 300

        # Contains
        if query in label_lower:
            score += 200
        elif query in desc_lower:
            score += 100

        # Word boundary match
        if re.search(r'\b' + re.escape(query), label_lower):
            score += 150

        # Character sequence match (fuzzy)
        if self._has_char_sequence(query, label_lower):
            score += 50

        return score

    def _has_char_sequence(self, query: str, text: str) -> bool:
        """Check if query characters appear in order in text."""
        idx = 0
        for char in query:
            idx = text.find(char, idx)
            if idx == -1:
                return False
            idx += 1
        return True

    def _command_to_dict(self, cmd: Command) -> Dict:
        """Convert command to dictionary."""
        return {
            "id": cmd.id,
            "command": cmd.label,
            "description": cmd.description,
            "category": cmd.category,
            "keybinding": cmd.keybinding,
            "priority": cmd.priority
        }

    def execute(self, command_id: str):
        """Execute command by ID."""
        cmd = next((c for c in self.commands if c.id == command_id), None)
        if not cmd:
            raise ValueError(f"Command not found: {command_id}")

        # Track recent
        if command_id in self.recent_commands:
            self.recent_commands.remove(command_id)
        self.recent_commands.insert(0, command_id)
        if len(self.recent_commands) > self.max_recent:
            self.recent_commands.pop()

        # Execute handler
        if cmd.handler:
            return cmd.handler()
        return {"status": "no_handler", "message": f"Command {cmd.label} has no handler"}
