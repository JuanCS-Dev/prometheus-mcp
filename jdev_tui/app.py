"""
JuanCS Dev-Code - The Minimal Masterpiece
==========================================

A beautiful, 60fps TUI inspired by:
- Gemini CLI's visual design
- Claude Code's simplicity
- Textual's power

Philosophy: "Perfection is achieved not when there is nothing more to add,
            but when there is nothing left to take away." - Antoine de Saint-Exupéry

Soli Deo Gloria
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import ClassVar

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal
from textual.reactive import reactive
from textual.widgets import Footer, Header, Input
from textual import on, events

# Local imports
from jdev_tui.constants import HELP_TEXT
from jdev_tui.widgets import AutocompleteDropdown, ResponseView, StatusBar
from jdev_tui.handlers import CommandRouter
from jdev_tui.themes import THEME_LIGHT, THEME_DARK, ThemeManager


# =============================================================================
# MAIN APPLICATION
# =============================================================================

class QwenApp(App):
    """
    JuanCS Dev-Code - The Minimal Masterpiece.

    A beautiful, fast, minimal TUI for AI-powered development.
    60fps rendering, security-first design, extensible core.
    """

    TITLE = "JuanCS Dev-Code"
    SUB_TITLE = "The Developer's Ally"

    # =========================================================================
    # PALETA DE CORES COESA - JuanCS Dev-Code Theme
    # =========================================================================
    # Primary: Cyan (#00d4aa) - Main accent, user prompts, panels
    # Secondary: Magenta (#ff79c6) - Highlights, agent indicators
    # Success: Green (#50fa7b) - Success messages, confirmations
    # Warning: Yellow (#f1fa8c) - Warnings, caution
    # Error: Red (#ff5555) - Errors, failures
    # Muted: Gray (#6272a4) - Dim text, hints
    # Surface: Dark (#1e1e2e) - Background
    # =========================================================================

    LAYERS = ["base", "autocomplete"]

    CSS = """
    Screen {
        background: $background;
        layers: base autocomplete;
    }

    Header {
        background: $surface;
        color: $foreground;
    }

    Footer {
        background: $surface;
    }

    #main {
        height: 1fr;
        padding: 1 2;
        layer: base;
    }

    /* Input area - uses theme colors */
    #input-area {
        height: 3;
        border: round $primary;
        background: $surface;
        padding: 0 1;
    }

    #prompt-icon {
        width: 3;
        padding: 1 0;
        color: $primary;
        text-style: bold;
    }

    #prompt {
        background: transparent;
        border: none;
        color: $foreground;
    }

    #prompt:focus {
        border: none;
    }

    /* ResponseView styling */
    ResponseView {
        scrollbar-size: 0 0;
        background: $background;
        color: $foreground;
    }

    VerticalScroll {
        scrollbar-size: 0 0;
    }

    /* Autocomplete dropdown - uses theme colors */
    #autocomplete {
        layer: autocomplete;
        dock: bottom;
        offset: 0 -4;
        margin: 0 3;
        background: $surface;
        border: round $primary;
        padding: 0 1;
        max-height: 18;
        display: none;
        color: $foreground;
    }

    #autocomplete.visible {
        display: block;
    }
    """

    BINDINGS: ClassVar[list[Binding]] = [
        Binding("ctrl+c", "quit", "Exit", show=True),
        Binding("ctrl+l", "clear", "Clear", show=True),
        Binding("ctrl+p", "show_help", "Help", show=True),
        Binding("ctrl+t", "toggle_theme", "Theme", show=True),
        Binding("escape", "cancel", "Cancel", show=False),
        # Scroll bindings for ResponseView (PageUp/PageDown always work)
        Binding("pageup", "scroll_up_page", "Page Up", show=False),
        Binding("pagedown", "scroll_down_page", "Page Down", show=False),
        Binding("ctrl+home", "scroll_home", "Top", show=False),
        Binding("ctrl+end", "scroll_end", "Bottom", show=False),
        # Ctrl+Arrow for fine scroll (Up/Down reserved for history)
        Binding("ctrl+up", "scroll_up", "Scroll Up", show=False),
        Binding("ctrl+down", "scroll_down", "Scroll Down", show=False),
    ]

    # State
    is_processing: reactive[bool] = reactive(False)

    def __init__(self) -> None:
        super().__init__()
        self.history: list[str] = []
        self.history_index = -1

        # Integration bridge (lazy loaded)
        self._bridge = None

        # Command router (lazy loaded)
        self._router = None

        # Pending media for AI
        self._pending_image = None
        self._pending_pdf = None

    @property
    def bridge(self):
        """Lazy load the integration bridge."""
        if self._bridge is None:
            from jdev_tui.core.bridge import get_bridge
            self._bridge = get_bridge()
        return self._bridge

    @property
    def router(self) -> CommandRouter:
        """Lazy load the command router."""
        if self._router is None:
            self._router = CommandRouter(self)
        return self._router

    def compose(self) -> ComposeResult:
        """Compose the UI - Gemini CLI style."""
        yield Header(show_clock=True)

        with Container(id="main"):
            # Response area (scrollable viewport)
            yield ResponseView(id="response")

            # Input area
            with Horizontal(id="input-area"):
                from textual.widgets import Static
                yield Static("❯", id="prompt-icon")
                yield Input(
                    placeholder="Type your command or ask anything...",
                    id="prompt"
                )

        # Autocomplete dropdown (overlay above input)
        yield AutocompleteDropdown(id="autocomplete")

        yield StatusBar()
        yield Footer()

    def on_mount(self) -> None:
        """Called when app is mounted - show banner and init bridge."""
        # Register themes
        self.register_theme(THEME_LIGHT)
        self.register_theme(THEME_DARK)

        # Load saved theme preference
        saved_theme = ThemeManager.get_theme_preference()
        self.theme = saved_theme

        response = self.query_one("#response", ResponseView)
        response.add_banner()

        # Initialize bridge and update status
        status = self.query_one(StatusBar)
        try:
            status.llm_connected = self.bridge.is_connected
            status.agent_count = len(self.bridge.agents.available_agents)
            status.tool_count = self.bridge.tools.get_tool_count()
            status.governance_status = self.bridge.governance.get_status_emoji()

            if self.bridge.is_connected:
                tool_msg = f" {status.tool_count} tools loaded." if status.tool_count > 0 else ""
                response.add_system_message(
                    f"✅ **Gemini connected!**{tool_msg} Type `/help` for commands or just chat."
                )
            else:
                response.add_system_message(
                    "⚠️ **No LLM configured.** Set `GEMINI_API_KEY` for full functionality.\n\n"
                    "Type `/help` for available commands."
                )
        except Exception as e:
            response.add_system_message(
                f"⚠️ Bridge init: {e}\n\nType `/help` for commands."
            )

        # Focus input
        self.query_one("#prompt", Input).focus()

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle user input submission."""
        user_input = event.value.strip()
        if not user_input:
            return

        # Hide autocomplete on submit
        autocomplete = self.query_one("#autocomplete", AutocompleteDropdown)
        autocomplete.hide()

        # Clear input field
        prompt = self.query_one("#prompt", Input)
        prompt.value = ""

        # Add to history
        self.history.append(user_input)
        self.history_index = len(self.history)

        # Get response view
        response = self.query_one("#response", ResponseView)

        # Show user message
        response.add_user_message(user_input)

        # Update status
        status = self.query_one(StatusBar)
        status.mode = "PROCESSING"

        try:
            # Handle commands vs chat
            if user_input.startswith("/"):
                await self.router.dispatch(user_input, response)
            else:
                await self._handle_chat(user_input, response)
        finally:
            status.mode = "READY"

    @on(Input.Changed, "#prompt")
    def on_input_changed(self, event: Input.Changed) -> None:
        """Handle input changes for autocomplete."""
        text = event.value

        autocomplete = self.query_one("#autocomplete", AutocompleteDropdown)

        if not text:
            autocomplete.hide()
            return

        # Check for @ file picker trigger
        has_at_trigger = False
        for i in range(len(text) - 1, -1, -1):
            if text[i] == '@' and (i == 0 or text[i-1].isspace()):
                has_at_trigger = True
                break

        # Show autocomplete for slash commands, @ file picker, or 2+ chars
        if not text.startswith("/") and not has_at_trigger and len(text) < 2:
            autocomplete.hide()
            return

        # Get completions from bridge
        try:
            completions = self.bridge.autocomplete.get_completions(text, max_results=15)
            autocomplete.show_completions(completions)
        except Exception:
            autocomplete.hide()

    async def on_key(self, event: events.Key) -> None:
        """Handle special keys for autocomplete navigation."""
        autocomplete = self.query_one("#autocomplete", AutocompleteDropdown)
        prompt = self.query_one("#prompt", Input)

        # Only handle when autocomplete is visible and prompt focused
        if not autocomplete.has_class("visible"):
            # Handle history navigation when autocomplete hidden
            if event.key == "up" and self.history:
                event.prevent_default()
                if self.history_index > 0:
                    self.history_index -= 1
                    prompt.value = self.history[self.history_index]
                    prompt.cursor_position = len(prompt.value)
            elif event.key == "down" and self.history:
                event.prevent_default()
                if self.history_index < len(self.history) - 1:
                    self.history_index += 1
                    prompt.value = self.history[self.history_index]
                    prompt.cursor_position = len(prompt.value)
            return

        if event.key == "up":
            event.prevent_default()
            autocomplete.move_selection(-1)

        elif event.key == "down":
            event.prevent_default()
            autocomplete.move_selection(1)

        elif event.key == "tab" or event.key == "enter":
            selected = autocomplete.get_selected()
            if selected:
                event.prevent_default()
                prompt.value = selected + " "
                prompt.cursor_position = len(prompt.value)
                autocomplete.hide()

        elif event.key == "escape":
            event.prevent_default()
            autocomplete.hide()

    async def _handle_chat(
        self,
        message: str,
        view: ResponseView
    ) -> None:
        """Handle natural language chat via Gemini streaming."""
        self.is_processing = True
        view.start_thinking()

        status = self.query_one(StatusBar)
        status.mode = "THINKING"

        try:
            async for chunk in self.bridge.chat(message):
                view.append_chunk(chunk)
                await asyncio.sleep(0)  # Yield for UI

            view.add_success("✓ Response complete")
            status.governance_status = self.bridge.governance.get_status_emoji()

        except Exception as e:
            view.add_error(f"Chat error: {e}")
            status.errors += 1
        finally:
            self.is_processing = False
            status.mode = "READY"
            view.end_thinking()

    async def _execute_bash(
        self,
        command: str,
        view: ResponseView
    ) -> None:
        """Execute bash command SECURELY via whitelist."""
        from jdev_tui.core.safe_executor import get_safe_executor

        executor = get_safe_executor()

        # Check if command is allowed BEFORE execution
        is_allowed, reason = executor.is_command_allowed(command)

        if not is_allowed:
            view.add_error(f"🚫 Command blocked: {reason}")
            view.add_action("Allowed commands:")

            allowed_by_cat = executor.get_allowed_commands_by_category()
            for category, commands in allowed_by_cat.items():
                view.add_action(f"  [{category}]")
                for cmd in commands[:3]:
                    view.add_action(f"    • {cmd}")
            return

        view.add_action(f"🔒 Executing (whitelisted): {command}")

        result = await executor.execute(command)

        if result.success:
            if result.stdout:
                view.add_code_block(result.stdout, language="bash", title=command)
            view.add_success(f"✓ Command completed (exit code: {result.exit_code})")
        else:
            error_msg = result.error_message or result.stderr or "Unknown error"
            view.add_error(f"Command failed: {error_msg}")
            if result.stderr:
                view.add_code_block(result.stderr, language="text", title="stderr")

    async def _read_file(
        self,
        path_str: str,
        view: ResponseView
    ) -> None:
        """Read and display file with syntax highlighting."""
        path = Path(path_str).expanduser()

        view.add_action(f"Reading: {path}")

        if not path.exists():
            view.add_error(f"File not found: {path}")
            return

        if not path.is_file():
            view.add_error(f"Not a file: {path}")
            return

        try:
            content = path.read_text()
            language = self._detect_language(path.suffix)

            view.add_code_block(
                content,
                language=language,
                title=str(path.name)
            )
            view.add_success(f"Read {len(content):,} characters")

        except Exception as e:
            view.add_error(f"Read error: {e}")

    def _detect_language(self, suffix: str) -> str:
        """Detect language from file extension."""
        lang_map = {
            ".py": "python",
            ".js": "javascript",
            ".ts": "typescript",
            ".jsx": "javascript",
            ".tsx": "typescript",
            ".json": "json",
            ".yaml": "yaml",
            ".yml": "yaml",
            ".md": "markdown",
            ".sh": "bash",
            ".bash": "bash",
            ".zsh": "bash",
            ".html": "html",
            ".css": "css",
            ".sql": "sql",
            ".rs": "rust",
            ".go": "go",
            ".java": "java",
            ".c": "c",
            ".cpp": "cpp",
            ".h": "c",
            ".hpp": "cpp",
            ".rb": "ruby",
            ".php": "php",
            ".swift": "swift",
            ".kt": "kotlin",
            ".toml": "toml",
            ".ini": "ini",
            ".xml": "xml",
        }
        return lang_map.get(suffix.lower(), "text")

    # Actions
    def action_quit(self) -> None:
        """Exit the application."""
        self.exit()

    def action_clear(self) -> None:
        """Clear the response view."""
        response = self.query_one("#response", ResponseView)
        response.clear_all()
        response.add_banner()

    def action_show_help(self) -> None:
        """Show help."""
        response = self.query_one("#response", ResponseView)
        response.add_system_message(HELP_TEXT)

    def action_cancel(self) -> None:
        """Cancel current operation."""
        if self.is_processing:
            self.is_processing = False
            response = self.query_one("#response", ResponseView)
            response.end_thinking()
            response.add_error("Operation cancelled")

    def action_toggle_theme(self) -> None:
        """Toggle between light and dark themes."""
        new_theme = ThemeManager.toggle_theme(self.theme)
        self.theme = new_theme

        # Show feedback
        response = self.query_one("#response", ResponseView)
        theme_name = "Claude Light ☀️" if new_theme == "claude-light" else "Matrix Dark 🌙"
        response.add_system_message(f"Theme switched to **{theme_name}**")

    # =========================================================================
    # SCROLL ACTIONS - Allow scrolling ResponseView with keyboard
    # =========================================================================

    def action_scroll_up(self) -> None:
        """Scroll ResponseView up by one line."""
        response = self.query_one("#response", ResponseView)
        response.scroll_up(animate=False)

    def action_scroll_down(self) -> None:
        """Scroll ResponseView down by one line."""
        response = self.query_one("#response", ResponseView)
        response.scroll_down(animate=False)

    def action_scroll_up_page(self) -> None:
        """Scroll ResponseView up by one page."""
        response = self.query_one("#response", ResponseView)
        response.scroll_page_up(animate=False)

    def action_scroll_down_page(self) -> None:
        """Scroll ResponseView down by one page."""
        response = self.query_one("#response", ResponseView)
        response.scroll_page_down(animate=False)

    def action_scroll_home(self) -> None:
        """Scroll ResponseView to top."""
        response = self.query_one("#response", ResponseView)
        response.scroll_home(animate=False)

    def action_scroll_end(self) -> None:
        """Scroll ResponseView to bottom."""
        response = self.query_one("#response", ResponseView)
        response.scroll_end(animate=False)


# =============================================================================
# ENTRY POINT
# =============================================================================

def main() -> None:
    """Run the QWEN CLI application."""
    app = QwenApp()
    # mouse=True enables scroll wheel in ResponseView
    # Use Shift+Click to select text for copy/paste in most terminals
    app.run(mouse=True)


if __name__ == "__main__":
    main()
