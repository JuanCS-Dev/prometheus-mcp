"""Streaming Response Display - Real-time LLM token streaming @ 30 FPS.

Implements smooth token-by-token display with intelligent truncation and batching.
"""

import time
from typing import AsyncIterator, Optional
from collections import deque

from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.live import Live


class StreamingResponseDisplay:
    """Stream LLM responses with 30 FPS rendering and intelligent truncation."""

    def __init__(
        self,
        console: Console,
        target_fps: int = 30,
        max_lines: int = 20,
        show_cursor: bool = True
    ):
        """Initialize StreamingResponseDisplay.

        Args:
            console: Rich Console instance
            target_fps: Target frames per second (default: 30)
            max_lines: Maximum lines before truncation (default: 20)
            show_cursor: Show typing cursor animation (default: True)
        """
        self.console = console
        self.target_fps = target_fps
        self.frame_budget = 1.0 / target_fps  # 33.33ms for 30 FPS
        self.max_lines = max_lines
        self.show_cursor = show_cursor

        # Batching state
        self.token_buffer: deque[str] = deque()
        self.full_content = ""
        self.is_truncated = False

        # Cursor animation frames
        self.cursor_frames = ["▋", "▌", "▍", "▎", "▏", " ", "▏", "▎", "▍", "▌"]
        self.cursor_index = 0

    async def stream(
        self,
        token_iterator: AsyncIterator[str],
        role: str = "assistant",
        style: str = "bright_magenta"
    ):
        """Stream tokens with 30 FPS rendering.

        Args:
            token_iterator: Async iterator of tokens
            role: Message role (for styling)
            style: Text style color

        Note:
            Complete content is available in self.full_content after streaming
        """
        self.full_content = ""
        self.token_buffer.clear()
        self.is_truncated = False

        last_update = time.time()

        # Stream tokens with batching
        async for token in token_iterator:
            self.token_buffer.append(token)
            self.full_content += token

            # Update display at target FPS
            now = time.time()
            if (now - last_update) >= self.frame_budget:
                # Flush buffer and update display
                yield self._render_current_state(style)
                last_update = now

        # Final update without cursor
        self.show_cursor = False
        yield self._render_current_state(style)

    def _render_current_state(self, style: str) -> Panel:
        """Render current state with cursor animation.

        Args:
            style: Text style color

        Returns:
            Rich Panel with current content
        """
        # Get display content (possibly truncated)
        display_content = self._get_display_content()

        # Add cursor if enabled
        if self.show_cursor:
            cursor = self.cursor_frames[self.cursor_index]
            self.cursor_index = (self.cursor_index + 1) % len(self.cursor_frames)
            display_content += cursor

        # Create text object
        text = Text(display_content, style=style)

        # Add truncation hint if needed
        if self.is_truncated:
            text.append("\n\n", style="dim")
            text.append("... [content truncated] ...", style="dim italic")
            text.append("\n", style="dim")
            text.append("💡 Use ", style="dim")
            text.append("/expand", style="bold bright_cyan")
            text.append(" to see full output", style="dim")

        # Create panel
        panel = Panel(
            text,
            title="[bold bright_magenta]🤖 AI Response[/bold bright_magenta]",
            border_style="bright_magenta",
            padding=(1, 2)
        )

        return panel

    def _get_display_content(self) -> str:
        """Get content for display with intelligent truncation.

        Returns:
            Content string (possibly truncated)
        """
        lines = self.full_content.split('\n')

        # Check if truncation needed
        if len(lines) > self.max_lines:
            self.is_truncated = True

            # Smart truncation: show first 15 lines + last 5 lines
            keep_start = self.max_lines - 5
            displayed_lines = lines[:keep_start] + ["", "...", ""] + lines[-5:]

            return '\n'.join(displayed_lines)

        self.is_truncated = False
        return self.full_content

    async def stream_with_live(
        self,
        token_iterator: AsyncIterator[str],
        role: str = "assistant",
        style: str = "bright_magenta"
    ) -> str:
        """Stream with Live context manager (auto-refreshing).

        Args:
            token_iterator: Async iterator of tokens
            role: Message role
            style: Text style color

        Returns:
            Complete content string
        """
        self.full_content = ""
        self.token_buffer.clear()
        self.is_truncated = False

        # Use Live for auto-refresh
        with Live(
            self._render_current_state(style),
            console=self.console,
            refresh_per_second=self.target_fps,
            transient=False
        ) as live:
            async for token in token_iterator:
                self.full_content += token

                # Update display
                live.update(self._render_current_state(style))

            # Final update without cursor
            self.show_cursor = False
            live.update(self._render_current_state(style))

        return self.full_content


class TokenBatcher:
    """Batches tokens for efficient 30 FPS rendering."""

    def __init__(self, target_fps: int = 30, batch_size: int = 3):
        """Initialize TokenBatcher.

        Args:
            target_fps: Target frames per second
            batch_size: Number of tokens per batch
        """
        self.target_fps = target_fps
        self.frame_budget = 1.0 / target_fps
        self.batch_size = batch_size

        self.buffer: list[str] = []
        self.last_flush = time.time()

    async def add_token(self, token: str) -> Optional[str]:
        """Add token to batch.

        Args:
            token: Token to add

        Returns:
            Batched string if ready to flush, None otherwise
        """
        self.buffer.append(token)

        # Flush if batch full or frame budget exceeded
        now = time.time()
        if len(self.buffer) >= self.batch_size or (now - self.last_flush) >= self.frame_budget:
            batched = ''.join(self.buffer)
            self.buffer.clear()
            self.last_flush = now
            return batched

        return None

    def flush(self) -> str:
        """Flush remaining tokens.

        Returns:
            Remaining batched string
        """
        batched = ''.join(self.buffer)
        self.buffer.clear()
        return batched
