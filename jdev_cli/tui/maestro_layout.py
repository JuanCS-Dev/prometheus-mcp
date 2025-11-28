"""Maestro Layout Manager - Unified 4-panel layout optimized for 30 FPS.

Implements differential rendering and state hashing for optimal performance.
"""

import hashlib
import time
from typing import Optional, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime

from rich.layout import Layout
from rich.panel import Panel
from rich.text import Text
from rich.table import Table
from rich.console import Console, RenderableType, Group


@dataclass
class LayoutState:
    """State for differential rendering."""

    header_data: Dict[str, Any] = field(default_factory=dict)
    conversation_data: list = field(default_factory=list)
    status_data: Dict[str, Any] = field(default_factory=dict)
    input_data: str = ""

    def compute_hash(self) -> str:
        """Compute hash of current state."""
        state_str = (
            str(self.header_data) +
            str(self.conversation_data) +
            str(self.status_data) +
            self.input_data
        )
        return hashlib.md5(state_str.encode()).hexdigest()


class MaestroLayout:
    """Layout manager with 4 panels optimized for 30 FPS rendering."""

    def __init__(self, console: Console):
        """Initialize MaestroLayout.

        Args:
            console: Rich Console instance
        """
        self.console = console

        # Layout structure
        self.layout = Layout()
        self._setup_layout()

        # State management for differential rendering
        self.state = LayoutState()
        self.last_hash: Optional[str] = None
        self.cached_panels: Dict[str, RenderableType] = {}

        # Performance tracking
        self.render_count = 0
        self.cache_hits = 0
        self.last_render_time = 0.0

    def _setup_layout(self):
        """Setup the 4-panel layout structure."""
        self.layout.split_column(
            Layout(name="header", size=4),  # Title + session info
            Layout(name="conversation", ratio=1),  # Message stream
            Layout(name="status", size=10),  # Progress + routing
            Layout(name="input", size=3)  # Prompt
        )

    def update_header(
        self,
        title: str = "MAESTRO v10.0",
        session_id: str = "",
        agent: str = "",
        timestamp: Optional[str] = None
    ):
        """Update header panel.

        Args:
            title: Main title
            session_id: Current session ID
            agent: Active agent name
            timestamp: Current timestamp
        """
        timestamp = timestamp or datetime.now().strftime("%H:%M:%S")

        header_data = {
            "title": title,
            "session_id": session_id,
            "agent": agent,
            "timestamp": timestamp
        }

        # Check if changed
        if header_data == self.state.header_data:
            self.cache_hits += 1
            return

        self.state.header_data = header_data

        # Render header
        table = Table.grid(expand=True)
        table.add_column(justify="left", ratio=1)
        table.add_column(justify="center", ratio=1)
        table.add_column(justify="right", ratio=1)

        # Left: Title
        left = Text(f"🤖 {title}", style="bold bright_cyan")

        # Center: Active agent
        center = Text(f"Agent: {agent}" if agent else "", style="bright_yellow")

        # Right: Session + Time
        right_parts = []
        if session_id:
            right_parts.append(f"Session: {session_id[:8]}")
        right_parts.append(timestamp)
        right = Text(" • ".join(right_parts), style="dim")

        table.add_row(left, center, right)

        panel = Panel(
            table,
            border_style="bright_cyan",
            padding=(0, 2)
        )

        self.cached_panels["header"] = panel
        self.layout["header"].update(panel)
        self.render_count += 1

    def update_conversation(self, messages: list):
        """Update conversation panel.

        Args:
            messages: List of message renderables
        """
        # Check if changed
        if messages == self.state.conversation_data:
            self.cache_hits += 1
            return

        self.state.conversation_data = messages.copy()

        # Render conversation
        if not messages:
            content = Text("No messages yet...", style="dim italic")
        else:
            # Stack messages vertically using Group (preserves renderables)
            content = Group(*messages)

        panel = Panel(
            content,
            title="[bold bright_blue]💬 Conversation[/bold bright_blue]",
            border_style="bright_blue",
            padding=(1, 2)
        )

        self.cached_panels["conversation"] = panel
        self.layout["conversation"].update(panel)
        self.render_count += 1

    def update_status(self, content: RenderableType):
        """Update status panel.

        Args:
            content: Renderable content (Panel, Progress, etc.)
        """
        # For complex renderables, always update
        # (hash comparison too expensive)
        self.layout["status"].update(content)
        self.render_count += 1

    def update_input(self, prompt: str = "maestro> "):
        """Update input panel.

        Args:
            prompt: Input prompt text
        """
        # Check if changed
        if prompt == self.state.input_data:
            self.cache_hits += 1
            return

        self.state.input_data = prompt

        # Render input
        text = Text(prompt, style="bright_green")

        panel = Panel(
            text,
            border_style="bright_green",
            padding=(0, 2)
        )

        self.cached_panels["input"] = panel
        self.layout["input"].update(panel)
        self.render_count += 1

    def render(self) -> Layout:
        """Render complete layout with differential rendering.

        Returns:
            Layout object ready for display
        """
        start_time = time.perf_counter()

        # Compute current state hash
        current_hash = self.state.compute_hash()

        # Skip re-render if nothing changed
        if current_hash == self.last_hash:
            self.cache_hits += 1
            return self.layout

        self.last_hash = current_hash

        # Track render time
        self.last_render_time = time.perf_counter() - start_time

        return self.layout

    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics.

        Returns:
            Dict with performance metrics
        """
        cache_hit_rate = (
            self.cache_hits / max(self.render_count, 1) * 100
            if self.render_count > 0
            else 0
        )

        return {
            "total_renders": self.render_count,
            "cache_hits": self.cache_hits,
            "cache_hit_rate": f"{cache_hit_rate:.1f}%",
            "last_render_ms": f"{self.last_render_time * 1000:.2f}ms",
            "target_fps": 30,
            "frame_budget_ms": 33.33
        }

    def reset_stats(self):
        """Reset performance statistics."""
        self.render_count = 0
        self.cache_hits = 0
        self.last_render_time = 0.0


class CyberpunkHeader:
    """Cyberpunk-styled header with neon effects."""

    @staticmethod
    def render(
        title: str = "NEUROSHELL v10.0",
        subtitle: str = "NEURAL INTERFACE ACTIVE",
        status: str = "ONLINE"
    ) -> Panel:
        """Render cyberpunk header.

        Args:
            title: Main title
            subtitle: Subtitle text
            status: Status indicator

        Returns:
            Rich Panel with cyberpunk styling
        """
        # ASCII art border
        border_top = "═" * 50
        border_bottom = "═" * 50

        # Create content
        content = Text()
        content.append(f"  {border_top}\n", style="bright_cyan")
        content.append("  ║ ", style="bright_cyan")
        content.append(title, style="bold bright_magenta")
        content.append(" ║\n", style="bright_cyan")
        content.append("  ║ ", style="bright_cyan")
        content.append(subtitle, style="bright_green")
        content.append(" " * (46 - len(subtitle)) + " ║\n", style="bright_cyan")
        content.append(f"  {border_bottom}", style="bright_cyan")

        # Status indicator
        status_color = "bright_green" if status == "ONLINE" else "bright_red"
        content.append("\n  [", style="dim")
        content.append(f"{status}", style=status_color)
        content.append("]", style="dim")

        return Panel(
            content,
            border_style="bright_cyan",
            padding=(0, 0)
        )
