"""
Response View Widget.

Smooth 60fps Response Viewport for streaming AI responses.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from textual.containers import VerticalScroll
from textual.reactive import reactive
from textual.widgets import Static

from rich.syntax import Syntax
from rich.panel import Panel
from rich.markdown import Markdown
from rich.text import Text

from jdev_tui.constants import BANNER
from jdev_tui.widgets.selectable import SelectableStatic
from jdev_tui.core.output_formatter import OutputFormatter, Colors, Icons
from jdev_tui.components.streaming_adapter import StreamingResponseWidget

if TYPE_CHECKING:
    pass


class ResponseView(VerticalScroll):
    """
    Smooth 60fps Response Viewport.

    Handles:
    - User messages
    - AI streaming responses
    - Code blocks with syntax highlighting
    - Action indicators
    """

    DEFAULT_CSS = """
    ResponseView {
        height: 1fr;
        border: round $primary;
        background: $background;
        padding: 1 2;
        scrollbar-size: 0 0;
    }

    .user-message {
        margin-bottom: 1;
        color: $foreground;
    }

    .ai-response {
        margin-bottom: 1;
        color: $foreground;
    }

    .code-block {
        margin: 1 0;
    }

    .action {
        color: $secondary;
    }

    .success {
        color: $success;
    }

    .error {
        color: $error;
    }

    .system-message {
        margin: 1 0;
        color: $foreground;
    }

    .tool-result {
        margin: 1 0;
    }

    .banner {
        text-align: center;
        width: 100%;
        color: $primary;
    }
    """

    is_thinking: reactive[bool] = reactive(False)

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.current_response = ""
        self._response_widget: Static | StreamingResponseWidget | None = None
        self._thinking_widget: Static | None = None
        self._use_streaming_markdown: bool = True

    def add_banner(self) -> None:
        """Add startup banner."""
        widget = Static(BANNER, classes="banner")
        self.mount(widget)

    def add_user_message(self, message: str) -> None:
        """Add user message with prompt icon."""
        content = Text()
        content.append("❯ ", style=f"bold {Colors.PRIMARY}")
        content.append(message)

        widget = SelectableStatic(content, classes="user-message")
        self.mount(widget)
        self.scroll_end(animate=True)

    def add_system_message(self, message: str) -> None:
        """Add system/help message (markdown)."""
        widget = SelectableStatic(Markdown(message), classes="system-message")
        self.mount(widget)
        self.scroll_end(animate=True)

    def start_thinking(self) -> None:
        """Show thinking indicator with orange accent."""
        self.is_thinking = True
        self._thinking_widget = Static(
            f"[bold {Colors.ACTION}]{Icons.THINKING}[/] [italic {Colors.MUTED}]Thinking...[/]",
            id="thinking-indicator"
        )
        self.mount(self._thinking_widget)
        self.scroll_end(animate=True)

    def end_thinking(self) -> None:
        """Remove thinking indicator and finalize response."""
        self.is_thinking = False
        if self._thinking_widget:
            self._thinking_widget.remove()
            self._thinking_widget = None

        # Wrap completed response in Panel
        if self.current_response and self._response_widget:
            if self._use_streaming_markdown and isinstance(self._response_widget, StreamingResponseWidget):
                self._response_widget.finalize_sync()
            else:
                formatted_panel = OutputFormatter.format_response(
                    self.current_response,
                    title="Response",
                    border_style=Colors.PRIMARY
                )
                self._response_widget.update(formatted_panel)

        # Reset for next response
        self.current_response = ""
        self._response_widget = None

    def append_chunk(self, chunk: str) -> None:
        """Append streaming chunk. Optimized for 60fps."""
        self.current_response += chunk

        if self._response_widget:
            if self._use_streaming_markdown and isinstance(self._response_widget, StreamingResponseWidget):
                self._response_widget.append_chunk(chunk)
            else:
                self._response_widget.update(self.current_response)
        else:
            # Create new widget (first chunk)
            if self._thinking_widget:
                self._thinking_widget.remove()
                self._thinking_widget = None

            if self._use_streaming_markdown:
                self._response_widget = StreamingResponseWidget(
                    classes="ai-response",
                    enable_markdown=True
                )
            else:
                self._response_widget = SelectableStatic(
                    self.current_response,
                    classes="ai-response"
                )
            self.mount(self._response_widget)

            if self._use_streaming_markdown and isinstance(self._response_widget, StreamingResponseWidget):
                self._response_widget.append_chunk(chunk)

        # Throttled scroll (max 20fps = 50ms) to prevent layout thrashing
        import time
        current_time = time.time()
        if not hasattr(self, '_last_scroll_time'):
            self._last_scroll_time = 0
            
        if current_time - self._last_scroll_time >= 0.05:
            self.scroll_end(animate=False)
            self._last_scroll_time = current_time

    def add_code_block(
        self,
        code: str,
        language: str = "text",
        title: str | None = None
    ) -> None:
        """Add syntax-highlighted code block in a panel."""
        syntax = Syntax(
            code.strip(),
            language,
            theme="dracula",
            line_numbers=True,
            word_wrap=True,
            background_color="#1e1e2e"
        )

        panel_title = f"{Icons.FILE} {title}" if title else f"{Icons.FILE} {language.upper()}"
        panel = Panel(
            syntax,
            title=f"[{Colors.PRIMARY}]{panel_title}[/]",
            title_align="left",
            border_style=Colors.PRIMARY
        )

        widget = SelectableStatic(panel, classes="code-block")
        self.mount(widget)
        self.scroll_end(animate=True)

    def add_action(self, action: str) -> None:
        """Add action indicator with orange accent."""
        widget = SelectableStatic(
            f"[bold {Colors.ACTION}]{Icons.EXECUTING}[/] [{Colors.MUTED}]{action}[/]",
            classes="action"
        )
        self.mount(widget)
        self.scroll_end(animate=True)

    def add_success(self, message: str) -> None:
        """Add success message with checkmark."""
        widget = SelectableStatic(
            f"[bold {Colors.SUCCESS}]{Icons.SUCCESS}[/] [{Colors.SUCCESS}]{message}[/]",
            classes="success"
        )
        self.mount(widget)
        self.scroll_end(animate=True)

    def add_error(self, message: str) -> None:
        """Add error message with X."""
        widget = SelectableStatic(
            f"[bold {Colors.ERROR}]{Icons.ERROR}[/] [{Colors.ERROR}]{message}[/]",
            classes="error"
        )
        self.mount(widget)
        self.scroll_end(animate=True)

    def add_tool_result(
        self,
        tool_name: str,
        success: bool,
        data: str | None = None,
        error: str | None = None
    ) -> None:
        """Add tool execution result with Panel formatting."""
        panel = OutputFormatter.format_tool_result(tool_name, success, data, error)
        widget = SelectableStatic(panel, classes="tool-result")
        self.mount(widget)
        self.scroll_end(animate=True)

    def add_response_panel(self, text: str, title: str = "Response") -> None:
        """Add a formatted response panel."""
        panel = OutputFormatter.format_response(text, title)
        widget = SelectableStatic(panel, classes="ai-response")
        self.mount(widget)
        self.scroll_end(animate=True)

    def clear_all(self) -> None:
        """Clear all content."""
        self.current_response = ""
        self._response_widget = None
        self._thinking_widget = None

        for child in list(self.children):
            child.remove()
