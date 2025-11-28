"""
MAESTRO v10.0 - Agent Stream Panel Component

Individual agent streaming panel with glassmorphism effects,
animated spinners, and cursor animation.
"""

from rich.panel import Panel
from rich.text import Text
from rich.style import Style
from rich.box import ROUNDED

from ..theme import COLORS
from .maestro_data_structures import AgentState, AgentStatus


class AgentStreamPanel:
    """
    Individual agent stream panel with 30 FPS rendering.

    Features:
    - Animated spinner during execution
    - Pulsing cursor animation
    - Progress bar visualization
    - Status indicators
    - Glassmorphism card styling
    """

    # Spinner frames (Braille spinner)
    SPINNER_FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]

    # Cursor animation frames (smooth pulsing)
    CURSOR_FRAMES = ["▋", "▌", "▍", "▎", "▏", " ", "▏", "▎", "▍", "▌"]

    def __init__(self, agent_state: AgentState, color: str):
        """
        Initialize agent stream panel.

        Args:
            agent_state: Agent state dataclass
            color: Hex color for this agent (e.g., COLORS['neon_cyan'])
        """
        self.state = agent_state
        self.color = color
        self.cursor_index = 0

    def render(self, show_cursor: bool = True, max_display_lines: int = 100) -> Panel:
        """
        Render agent panel with current state.

        Args:
            show_cursor: Whether to show animated cursor
            max_display_lines: Maximum lines to display in panel (increased to 100 for better streaming)

        Returns:
            Rich Panel ready for rendering
        """
        # Build header with status indicator
        header = self._build_header()

        # Build content area
        content = self._build_content(show_cursor, max_display_lines)

        # Build panel with glassmorphism styling
        return Panel(
            content,
            title=header,
            border_style=self.color,
            box=ROUNDED,
            padding=(1, 2),
            style=Style(bgcolor=COLORS['bg_card'])
        )

    def _build_header(self) -> Text:
        """
        Build panel header with icon, name, and status.

        Returns:
            Formatted Text object for header
        """
        header = Text()

        # Icon + Name
        header.append(f"{self.state.icon} ", style=f"bold {self.color}")
        header.append(self.state.name.upper(), style=f"bold {self.color}")

        # Status indicator
        if self.state.status == AgentStatus.EXECUTING:
            # Animated spinner
            spinner = self.SPINNER_FRAMES[
                self.state.spinner_frame % len(self.SPINNER_FRAMES)
            ]
            header.append(f" {spinner}", style=self.color)

        elif self.state.status == AgentStatus.THINKING:
            header.append(" 🤔", style=self.color)

        elif self.state.status == AgentStatus.DONE:
            header.append(" ✓", style=f"bold {COLORS['neon_green']}")

        elif self.state.status == AgentStatus.ERROR:
            header.append(" ✗", style=f"bold {COLORS['neon_red']}")

        return header

    def _build_content(
        self,
        show_cursor: bool,
        max_display_lines: int
    ) -> Text:
        """
        Build content area with streaming text.

        Args:
            show_cursor: Whether to show animated cursor
            max_display_lines: Maximum lines to display

        Returns:
            Formatted Text object for content
        """
        content = Text()

        # Get recent content lines (tail)
        display_lines = (
            self.state.content[-max_display_lines:]
            if len(self.state.content) > max_display_lines
            else self.state.content
        )

        # Display content
        for line in display_lines:
            # Use primary text color for executor, keep neon for others
            text_color = (
                COLORS['text_primary']
                if self.color == COLORS['neon_cyan']
                else self.color
            )
            content.append(line + "\n", style=text_color)

        # Add animated cursor if executing
        if show_cursor and self.state.status == AgentStatus.EXECUTING:
            cursor = self.CURSOR_FRAMES[self.cursor_index]
            content.append(cursor, style=f"bold {self.color}")
            self.cursor_index = (self.cursor_index + 1) % len(self.CURSOR_FRAMES)

        # Add progress bar if applicable
        if self.state.progress > 0:
            progress_bar = self._build_progress_bar()
            content.append(f"\n\n{progress_bar}", style=f"bold {self.color}")

        # Add completion indicator
        if self.state.status == AgentStatus.DONE:
            content.append("\n\n✓ ", style=f"bold {COLORS['neon_green']}")
            content.append("Complete", style=COLORS['neon_green'])

        # Add error message if present
        if self.state.status == AgentStatus.ERROR and self.state.error_message:
            content.append("\n\n✗ ", style=f"bold {COLORS['neon_red']}")
            content.append("Error: ", style=f"bold {COLORS['neon_red']}")
            content.append(self.state.error_message, style=COLORS['neon_red'])

        return content

    def _build_progress_bar(self, width: int = 30) -> str:
        """
        Build ASCII progress bar.

        Args:
            width: Width of progress bar in characters

        Returns:
            Progress bar string
        """
        filled = int(width * self.state.progress / 100)
        bar = "█" * filled + "░" * (width - filled)
        return f"{bar} {self.state.progress:.0f}%"

    def advance_spinner(self):
        """Advance spinner animation frame"""
        self.state.spinner_frame += 1

    def reset_cursor(self):
        """Reset cursor animation to start"""
        self.cursor_index = 0


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def create_executor_panel(state: AgentState) -> AgentStreamPanel:
    """
    Create executor agent panel with cyan neon styling.

    Args:
        state: Agent state

    Returns:
        Configured AgentStreamPanel
    """
    return AgentStreamPanel(state, COLORS['neon_cyan'])


def create_planner_panel(state: AgentState) -> AgentStreamPanel:
    """
    Create planner agent panel with purple neon styling.

    Args:
        state: Agent state

    Returns:
        Configured AgentStreamPanel
    """
    return AgentStreamPanel(state, COLORS['neon_purple'])


def create_reviewer_panel(state: AgentState) -> AgentStreamPanel:
    """
    Create reviewer agent panel with green neon styling.

    Args:
        state: Agent state

    Returns:
        Configured AgentStreamPanel
    """
    return AgentStreamPanel(state, COLORS['neon_green'])


def create_refactorer_panel(state: AgentState) -> AgentStreamPanel:
    """
    Create refactorer agent panel with yellow neon styling.

    Args:
        state: Agent state

    Returns:
        Configured AgentStreamPanel
    """
    return AgentStreamPanel(state, COLORS['neon_yellow'])


def create_explorer_panel(state: AgentState) -> AgentStreamPanel:
    """
    Create explorer agent panel with blue neon styling.

    Args:
        state: Agent state

    Returns:
        Configured AgentStreamPanel
    """
    return AgentStreamPanel(state, COLORS['neon_blue'])
