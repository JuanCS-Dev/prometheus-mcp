"""
MAESTRO v10.0 - Shell UI Component

Complete shell UI matching the concept image with 30 FPS rendering,
triple-panel streaming, and glassmorphism cyberpunk styling.

Based on November 2025 research:
- Rich 14.1.0 Live display with 30 FPS
- Async differential rendering
- Group renderables for flicker-free updates
"""

import asyncio
from typing import Optional, Dict, Any
from datetime import datetime

from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from rich.text import Text
from rich.table import Table
from rich.live import Live
from rich.style import Style
from rich.box import ROUNDED

from ..theme import COLORS
from .maestro_data_structures import AgentState, AgentStatus, MetricsData
from .agent_stream_panel import AgentStreamPanel
from .file_operations_panel import FileOperationsPanel
from .command_palette_bar import CommandPaletteBar
from .metrics_dashboard import MetricsDashboard


class MaestroShellUI:
    """
    Complete MAESTRO shell UI matching the concept image.

    Features:
    - 30 FPS rendering with Rich Live
    - Triple-panel agent streaming
    - Real-time file operations
    - Command palette
    - Metrics dashboard
    - Glassmorphism cyberpunk styling
    """

    def __init__(self, console: Optional[Console] = None):
        """
        Initialize MAESTRO shell UI.

        Args:
            console: Rich Console instance (creates new if None)
        """
        self.console = console or Console()

        # Agent states (can be extended)
        self.agents: Dict[str, AgentState] = {
            'executor': AgentState(
                name="CODE EXECUTOR",
                icon="⚡",
                status=AgentStatus.IDLE
            ),
            'planner': AgentState(
                name="PLANNER",
                icon="🎯",
                status=AgentStatus.IDLE
            ),
        }

        # File operations tracker
        self.file_ops = FileOperationsPanel()

        # Command palette
        self.command_palette = CommandPaletteBar()

        # Metrics
        self.metrics = MetricsData()

        # Layout
        self.layout = Layout()
        self._setup_layout()

        # Live display (will be initialized on start)
        self.live: Optional[Live] = None

        # Performance tracking
        self.frame_count = 0
        self.start_time = 0.0

        # Throttle refresh to 30 FPS (33.3ms minimum interval)
        self._last_refresh = 0.0
        self._min_refresh_interval = 0.033  # 33ms = 30 FPS

    def _setup_layout(self):
        """Setup the 4-layer layout structure"""
        self.layout.split_column(
            Layout(name="header", size=4),          # Title + live status
            Layout(name="agents", ratio=1),         # Triple-panel streaming
            Layout(name="command_bar", size=4),     # Command palette
            Layout(name="metrics", size=3)          # Metrics dashboard
        )

    def _render_header(self) -> Panel:
        """
        Render top header with live status and metrics.

        Returns:
            Rich Panel for header
        """
        # Build header table (3 columns)
        table = Table.grid(expand=True)
        table.add_column(justify="left", ratio=1)
        table.add_column(justify="center", ratio=1)
        table.add_column(justify="right", ratio=1)

        # Left: Logo + Title
        left = Text()
        left.append("🎵 ", style=f"bold {COLORS['neon_cyan']}")
        left.append("MAESTRO", style=f"bold {COLORS['neon_cyan']}")
        left.append(" v10.0", style=f"dim {COLORS['text_secondary']}")

        # Center: Live indicator + stats
        center = Text()
        center.append("[", style=COLORS['text_tertiary'])
        center.append("● LIVE", style=f"bold blink {COLORS['maestro_live']}")
        center.append("]", style=COLORS['text_tertiary'])

        # Active agents count
        active_count = sum(
            1 for agent in self.agents.values()
            if agent.status in [AgentStatus.EXECUTING, AgentStatus.THINKING]
        )
        center.append(f" {len(self.agents)} agents", style=COLORS['text_secondary'])
        if active_count > 0:
            center.append(f" ({active_count} active)", style=COLORS['neon_cyan'])

        # Token efficiency
        if self.metrics.tokens_saved > 0:
            center.append(" | Efficiency: ", style=COLORS['text_secondary'])
            center.append(f"{self.metrics.tokens_saved:.0f}%↓", style=f"bold {COLORS['neon_green']}")

        # Latency
        if self.metrics.latency_ms > 0:
            center.append(" | ", style=COLORS['text_secondary'])
            center.append(f"{self.metrics.latency_ms}ms", style=f"bold {COLORS['neon_cyan']}")

        # Right: Timestamp
        right = Text(datetime.now().strftime("%H:%M:%S"), style=COLORS['text_tertiary'])

        table.add_row(left, center, right)

        return Panel(
            table,
            border_style=COLORS['neon_cyan'],
            box=ROUNDED,
            padding=(0, 2),
            style=Style(bgcolor=COLORS['bg_deep'])
        )

    def _render_agents_panel(self) -> Layout:
        """
        Render 3-column agent streams.

        Returns:
            Layout with agent panels
        """
        agent_layout = Layout()

        # Determine number of columns based on active agents
        active_agents = list(self.agents.keys())[:2]  # Max 2 agent columns + files

        if len(active_agents) >= 2:
            # Triple panel: executor | planner | files
            agent_layout.split_row(
                Layout(name="agent1"),
                Layout(name="agent2"),
                Layout(name="files")
            )

            # Render executor
            executor_panel = AgentStreamPanel(
                self.agents['executor'],
                COLORS['neon_cyan']
            )
            agent_layout["agent1"].update(executor_panel.render())

            # Render planner
            planner_panel = AgentStreamPanel(
                self.agents['planner'],
                COLORS['neon_purple']
            )
            agent_layout["agent2"].update(planner_panel.render())

            # Render files
            agent_layout["files"].update(self.file_ops.render())

        else:
            # Dual panel: single agent | files
            agent_layout.split_row(
                Layout(name="agent1"),
                Layout(name="files")
            )

            # Render first active agent
            first_agent = active_agents[0] if active_agents else 'executor'
            agent_state = self.agents[first_agent]

            # Choose color based on agent
            if first_agent == 'executor':
                color = COLORS['neon_cyan']
            elif first_agent == 'planner':
                color = COLORS['neon_purple']
            else:
                color = COLORS['neon_blue']

            panel = AgentStreamPanel(agent_state, color)
            agent_layout["agent1"].update(panel.render())

            # Render files
            agent_layout["files"].update(self.file_ops.render())

        return agent_layout

    def _render_command_bar(self) -> Panel:
        """
        Render command palette bar.

        Returns:
            Rich Panel for command bar
        """
        return self.command_palette.render()

    def _render_metrics(self) -> Panel:
        """
        Render metrics dashboard.

        Returns:
            Rich Panel for metrics
        """
        dashboard = MetricsDashboard(self.metrics)
        content = dashboard.render(compact=True)

        return Panel(
            content,
            border_style=COLORS['border_muted'],
            box=ROUNDED,
            padding=(0, 2),
            style=Style(bgcolor=COLORS['bg_deep'])
        )

    def refresh_display(self, force: bool = False):
        """
        Refresh the entire display with throttling.

        Args:
            force: Force refresh even if within throttle interval
        """
        import time

        current_time = time.time()
        elapsed = current_time - self._last_refresh

        # Throttle: only refresh if enough time passed OR forced
        if not force and elapsed < self._min_refresh_interval:
            return  # Skip this refresh to stay within 30 FPS budget

        # Perform refresh
        self.layout["header"].update(self._render_header())
        self.layout["agents"].update(self._render_agents_panel())
        self.layout["command_bar"].update(self._render_command_bar())
        self.layout["metrics"].update(self._render_metrics())

        self.frame_count += 1
        self._last_refresh = current_time

    async def start(self):
        """Start the live display @ 30 FPS"""
        self.live = Live(
            self.layout,
            console=self.console,
            refresh_per_second=30,  # 30 FPS!
            screen=False,  # Stay in normal buffer (not alternate screen)
            transient=False
        )

        self.live.start()
        self.refresh_display()
        self.start_time = asyncio.get_event_loop().time()

    def stop(self):
        """Stop the live display and ensure thread cleanup"""
        if self.live:
            try:
                self.live.stop()
            except Exception as e:
                # Ignore errors during stop (Live might already be stopped)
                pass
            finally:
                self.live = None

    # ========================================================================
    # HIGH-LEVEL API FOR AGENTS
    # ========================================================================

    async def update_agent_stream(
        self,
        agent_name: str,
        text: str,
        advance_spinner: bool = True
    ):
        """
        Update agent stream with new text.

        Args:
            agent_name: Name of agent ('executor', 'planner', etc.)
            text: Text to add to stream
            advance_spinner: Whether to advance spinner animation
        """
        if agent_name not in self.agents:
            return

        agent = self.agents[agent_name]

        # Set status to executing if not already
        if agent.status == AgentStatus.IDLE:
            agent.status = AgentStatus.EXECUTING

        # Add content
        agent.add_content(text)

        # Advance spinner
        if advance_spinner:
            agent.spinner_frame += 1

        # Refresh display
        self.refresh_display()

    async def update_executor_stream(self, text: str):
        """Shortcut: Update executor agent stream"""
        await self.update_agent_stream('executor', text)

    async def update_planner_stream(self, text: str):
        """Shortcut: Update planner agent stream"""
        await self.update_agent_stream('planner', text)

    def update_agent_progress(self, agent_name: str, progress: float):
        """
        Update agent progress bar.

        Args:
            agent_name: Name of agent
            progress: Progress percentage (0.0 to 100.0)
        """
        if agent_name in self.agents:
            self.agents[agent_name].progress = progress
            self.refresh_display()

    def update_executor_progress(self, progress: float):
        """Shortcut: Update executor progress"""
        self.update_agent_progress('executor', progress)

    def mark_agent_done(self, agent_name: str):
        """
        Mark agent as done.

        Args:
            agent_name: Name of agent
        """
        if agent_name in self.agents:
            self.agents[agent_name].status = AgentStatus.DONE
            self.agents[agent_name].progress = 100.0
            self.refresh_display()

    def mark_agent_error(self, agent_name: str, error_message: str):
        """
        Mark agent as error.

        Args:
            agent_name: Name of agent
            error_message: Error message to display
        """
        if agent_name in self.agents:
            self.agents[agent_name].set_error(error_message)
            self.refresh_display()

    def clear_agent_content(self, agent_name: str):
        """
        Clear agent content.

        Args:
            agent_name: Name of agent
        """
        if agent_name in self.agents:
            self.agents[agent_name].clear_content()
            self.agents[agent_name].progress = 0.0
            self.agents[agent_name].status = AgentStatus.IDLE
            self.refresh_display()

    def add_file_operation(
        self,
        path: str,
        status: str,
        added: int = 0,
        removed: int = 0
    ):
        """
        Add file operation to tracker.

        Args:
            path: File path
            status: Status string ("analyzing", "modified", "saved", "creating")
            added: Lines added
            removed: Lines removed
        """
        from .file_operations_panel import create_file_operation_from_event

        op = create_file_operation_from_event(path, status, added, removed)
        self.file_ops.add_operation(op)
        self.refresh_display()

    def update_metrics(self, **kwargs):
        """
        Update metrics.

        Args:
            **kwargs: Metric fields to update (success_rate, tokens_used, etc.)
        """
        for key, value in kwargs.items():
            if hasattr(self.metrics, key):
                setattr(self.metrics, key, value)
        self.refresh_display()

    def get_fps(self) -> float:
        """
        Calculate current FPS.

        Returns:
            Frames per second
        """
        if self.start_time == 0.0:
            return 0.0

        elapsed = asyncio.get_event_loop().time() - self.start_time
        if elapsed == 0:
            return 0.0

        return self.frame_count / elapsed

    def add_agent(self, name: str, display_name: str, icon: str):
        """
        Add custom agent to UI.

        Args:
            name: Agent key name
            display_name: Display name
            icon: Emoji icon
        """
        self.agents[name] = AgentState(
            name=display_name,
            icon=icon,
            status=AgentStatus.IDLE
        )


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def create_maestro_ui(console: Optional[Console] = None) -> MaestroShellUI:
    """
    Create MAESTRO UI with default configuration.

    Args:
        console: Optional Console instance

    Returns:
        Configured MaestroShellUI
    """
    return MaestroShellUI(console)
