"""Slash Command Completer - Dropdown autocomplete for / commands."""

from typing import Optional
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.document import Document


class SlashCommandCompleter(Completer):
    """Autocomplete for slash commands with dropdown."""

    def __init__(self):
        """Initialize with available slash commands."""
        self.slash_commands = [
            # Basic commands
            ("/quit", "Exit MAESTRO"),
            ("/exit", "Exit MAESTRO"),
            ("/q", "Exit MAESTRO (short)"),
            ("/clear", "Clear screen"),
            ("/c", "Clear screen (short)"),
            ("/help", "Show help"),
            ("/h", "Show help (short)"),

            # Agent commands
            ("/agents", "List available agents"),
            ("/commands", "Fuzzy search commands"),

            # Permission management
            ("/permissions", "Show permission configuration"),
            ("/metrics", "Show execution metrics"),

            # Future commands (commented for visibility)
            # ("/history", "Show command history"),
            # ("/save", "Save session"),
            # ("/load", "Load session"),
        ]

    def get_completions(self, document: Document, complete_event):
        """Get completions for slash commands."""
        text = document.text_before_cursor
        word = document.get_word_before_cursor()

        # Only complete if starts with /
        if not text.startswith('/'):
            return

        # Get all matching commands
        for cmd, description in self.slash_commands:
            if cmd.startswith(text.lower()):
                yield Completion(
                    text=cmd,
                    start_position=-len(text),
                    display=cmd,
                    display_meta=description
                )


class CombinedCompleter(Completer):
    """Combines slash command completion with tool completion."""

    def __init__(self, tool_completer: Optional[Completer] = None):
        """Initialize with optional tool completer.

        Args:
            tool_completer: ContextAwareCompleter for tools
        """
        self.slash_completer = SlashCommandCompleter()
        self.tool_completer = tool_completer

    def get_completions(self, document: Document, complete_event):
        """Get completions from both slash and tool completers."""
        text = document.text_before_cursor

        # If starts with /, use slash completer
        if text.startswith('/'):
            yield from self.slash_completer.get_completions(document, complete_event)
        # Otherwise use tool completer if available
        elif self.tool_completer:
            yield from self.tool_completer.get_completions(document, complete_event)
