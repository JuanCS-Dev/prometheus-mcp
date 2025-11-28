"""Agent Routing Display - Shows which agent is handling the request.

Cyberpunk-styled panel with agent selection confidence and ETA.
"""

from rich.panel import Panel
from rich.table import Table
from rich.text import Text


class AgentRoutingDisplay:
    """Display agent selection with confidence and ETA."""

    # Agent emojis for visual impact
    AGENT_EMOJIS = {
        'executor': '💻',
        'planner': '⚡',
        'reviewer': '🔍',
        'refactorer': '🔧',
        'explorer': '🗺️',
        'architect': '🏗️',
        'security': '🛡️',
        'performance': '⚡',
        'testing': '🧪',
        'documentation': '📚'
    }

    # Agent colors (cyberpunk theme)
    AGENT_COLORS = {
        'executor': 'bright_white',
        'planner': 'bright_yellow',
        'reviewer': 'bright_cyan',
        'refactorer': 'bright_magenta',
        'explorer': 'bright_green',
        'architect': 'bright_blue',
        'security': 'bright_red',
        'performance': 'yellow',
        'testing': 'green',
        'documentation': 'cyan'
    }

    def __init__(self):
        """Initialize AgentRoutingDisplay."""
        pass

    def render(
        self,
        agent_name: str,
        confidence: float = 1.0,
        eta: str = "calculating...",
        metadata: dict = None
    ) -> Panel:
        """Render agent routing panel.

        Args:
            agent_name: Name of the selected agent
            confidence: Confidence score (0.0-1.0)
            eta: Estimated time to completion
            metadata: Additional metadata to display

        Returns:
            Rich Panel with routing information
        """
        metadata = metadata or {}

        # Get agent styling
        emoji = self.AGENT_EMOJIS.get(agent_name, '🤖')
        color = self.AGENT_COLORS.get(agent_name, 'white')

        # Create table for structured display
        table = Table.grid(padding=(0, 2))
        table.add_column(style="dim", justify="right", width=12)
        table.add_column(style=color)

        # Agent name with emoji
        agent_display = f"{emoji} {agent_name.title()} Agent"
        table.add_row("Agent:", Text(agent_display, style=f"bold {color}"))

        # Confidence bar
        confidence_pct = int(confidence * 100)
        confidence_bar = self._create_confidence_bar(confidence)
        table.add_row("Confidence:", confidence_bar)

        # ETA
        table.add_row("ETA:", Text(eta, style="bright_white"))

        # Additional metadata
        if metadata:
            for key, value in metadata.items():
                table.add_row(f"{key}:", str(value))

        # Create panel with neon border
        panel = Panel(
            table,
            title="[bold cyan]⚡ AGENT ROUTING ⚡[/bold cyan]",
            border_style="bright_cyan",
            padding=(0, 1)
        )

        return panel

    def _create_confidence_bar(self, confidence: float) -> Text:
        """Create a visual confidence bar.

        Args:
            confidence: Confidence score (0.0-1.0)

        Returns:
            Text with visual bar representation
        """
        bar_length = 20
        filled = int(confidence * bar_length)
        empty = bar_length - filled

        # Color based on confidence
        if confidence >= 0.9:
            color = "bright_green"
        elif confidence >= 0.7:
            color = "bright_yellow"
        else:
            color = "bright_red"

        # Create bar
        bar = "█" * filled + "░" * empty
        percentage = f"{int(confidence * 100)}%"

        return Text(f"{bar} {percentage}", style=color)

    def render_compact(self, agent_name: str) -> Text:
        """Render compact single-line routing info.

        Args:
            agent_name: Name of the selected agent

        Returns:
            Text with compact routing info
        """
        emoji = self.AGENT_EMOJIS.get(agent_name, '🤖')
        color = self.AGENT_COLORS.get(agent_name, 'white')

        return Text(f"{emoji} [{color}]{agent_name}[/{color}]", style="dim")
