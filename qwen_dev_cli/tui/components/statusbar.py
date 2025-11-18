"""
Status Bar - Elegant bottom status bar with contextual information.

Inspiration:
- VSCode Status Bar
- Sublime Text Status Bar
- Apple Touch Bar (conceptual)

Philosophy:
- Always visible (persistent context)
- Non-intrusive (subtle background)
- Information-dense (no clutter)
- Responsive (adapts to content)
- Elegant (Apple-style minimalism)

"Your word is a lamp to my feet and a light to my path." - Psalm 119:105

Created: 2025-11-18 21:44 UTC
"""

from typing import Optional, List, Dict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from rich.console import Console
from rich.table import Table
from rich.text import Text
from rich.align import Align
from rich.panel import Panel

from ..theme import COLORS
from ..styles import PRESET_STYLES


@dataclass
class StatusSegment:
    """
    A segment in the status bar.
    
    Attributes:
        text: Display text
        icon: Optional icon
        style: Rich style
        tooltip: Optional tooltip text
        priority: Display priority (higher = more important)
    """
    text: str
    icon: Optional[str] = None
    style: Optional[str] = None
    tooltip: Optional[str] = None
    priority: int = 0
    
    def render(self) -> Text:
        """Render segment as Text."""
        result = Text()
        
        if self.icon:
            result.append(f"{self.icon} ", style=self.style)
        
        result.append(self.text, style=self.style or PRESET_STYLES.SECONDARY)
        
        return result


class StatusBar:
    """
    Elegant status bar with three sections (left, center, right).
    
    Features:
    - Three-section layout (left/center/right)
    - Segment-based (composable)
    - Priority-based overflow handling
    - Responsive to terminal width
    - Subtle background (non-intrusive)
    - Auto-update support
    
    Examples:
        status = StatusBar()
        status.set_left("directory", "~/projects/qwen", icon="📁")
        status.set_right("git", "main", icon="🔀")
        console.print(status.render())
    """
    
    def __init__(
        self,
        show_background: bool = True,
        auto_hide: bool = False,
        auto_hide_delay: float = 3.0,
    ):
        """
        Initialize status bar.
        
        Args:
            show_background: Show subtle background
            auto_hide: Auto-hide when inactive
            auto_hide_delay: Delay before auto-hide (seconds)
        """
        self.show_background = show_background
        self.auto_hide = auto_hide
        self.auto_hide_delay = auto_hide_delay
        
        # Segments storage
        self.left_segments: Dict[str, StatusSegment] = {}
        self.center_segments: Dict[str, StatusSegment] = {}
        self.right_segments: Dict[str, StatusSegment] = {}
        
        # State
        self.last_update = datetime.now()
        self.visible = True
    
    def set_left(
        self,
        key: str,
        text: str,
        icon: Optional[str] = None,
        style: Optional[str] = None,
        priority: int = 0,
    ) -> None:
        """
        Set left section segment.
        
        Args:
            key: Segment identifier
            text: Display text
            icon: Optional icon
            style: Rich style
            priority: Display priority
        """
        self.left_segments[key] = StatusSegment(text, icon, style, priority=priority)
        self.last_update = datetime.now()
        self.visible = True
    
    def set_center(
        self,
        key: str,
        text: str,
        icon: Optional[str] = None,
        style: Optional[str] = None,
        priority: int = 0,
    ) -> None:
        """Set center section segment."""
        self.center_segments[key] = StatusSegment(text, icon, style, priority=priority)
        self.last_update = datetime.now()
        self.visible = True
    
    def set_right(
        self,
        key: str,
        text: str,
        icon: Optional[str] = None,
        style: Optional[str] = None,
        priority: int = 0,
    ) -> None:
        """Set right section segment."""
        self.right_segments[key] = StatusSegment(text, icon, style, priority=priority)
        self.last_update = datetime.now()
        self.visible = True
    
    def remove_left(self, key: str) -> None:
        """Remove left segment."""
        self.left_segments.pop(key, None)
    
    def remove_center(self, key: str) -> None:
        """Remove center segment."""
        self.center_segments.pop(key, None)
    
    def remove_right(self, key: str) -> None:
        """Remove right segment."""
        self.right_segments.pop(key, None)
    
    def clear(self) -> None:
        """Clear all segments."""
        self.left_segments.clear()
        self.center_segments.clear()
        self.right_segments.clear()
    
    def _build_section(self, segments: Dict[str, StatusSegment], max_width: Optional[int] = None) -> Text:
        """
        Build section text from segments.
        
        Args:
            segments: Segment dictionary
            max_width: Maximum width (for overflow handling)
            
        Returns:
            Combined Text object
        """
        if not segments:
            return Text()
        
        # Sort by priority (descending)
        sorted_segments = sorted(segments.values(), key=lambda s: s.priority, reverse=True)
        
        result = Text()
        for idx, segment in enumerate(sorted_segments):
            if idx > 0:
                result.append(" │ ", style=COLORS['border_muted'])
            
            result.append(segment.render())
        
        return result
    
    def render(self, width: Optional[int] = None) -> Panel:
        """
        Render status bar.
        
        Args:
            width: Terminal width (auto-detect if None)
            
        Returns:
            Rich Panel object
        """
        # Check auto-hide
        if self.auto_hide and not self.visible:
            return Panel(Text(), border_style="", height=0)
        
        # Build sections
        left_text = self._build_section(self.left_segments)
        center_text = self._build_section(self.center_segments)
        right_text = self._build_section(self.right_segments)
        
        # Create table for layout
        table = Table.grid(expand=True)
        table.add_column(justify="left", ratio=1)
        table.add_column(justify="center", ratio=1)
        table.add_column(justify="right", ratio=1)
        
        table.add_row(left_text, center_text, right_text)
        
        # Panel with subtle background
        background_style = COLORS['bg_subtle'] if self.show_background else ""
        
        return Panel(
            table,
            border_style=COLORS['border_muted'],
            style=background_style,
            padding=(0, 1),
            height=3,
        )
    
    def hide(self) -> None:
        """Hide status bar."""
        self.visible = False
    
    def show(self) -> None:
        """Show status bar."""
        self.visible = True


# =============================================================================
# PRE-CONFIGURED STATUS BARS
# =============================================================================

class DevelopmentStatusBar(StatusBar):
    """
    Pre-configured status bar for development environment.
    
    Shows:
    - Left: Current directory, file count
    - Center: Active context (files loaded)
    - Right: Git branch, time
    """
    
    def __init__(self):
        """Initialize development status bar."""
        super().__init__()
        self._setup_default()
    
    def _setup_default(self):
        """Setup default segments."""
        # Left: Directory
        self.set_left(
            "directory",
            str(Path.cwd().name),
            icon="📁",
            style=PRESET_STYLES.PATH,
            priority=10,
        )
        
        # Center: Context (placeholder)
        self.set_center(
            "context",
            "No files loaded",
            icon="📄",
            style=PRESET_STYLES.TERTIARY,
            priority=5,
        )
        
        # Right: Time
        self.set_right(
            "time",
            datetime.now().strftime("%H:%M"),
            icon="🕐",
            style=PRESET_STYLES.SECONDARY,
            priority=1,
        )
    
    def update_directory(self, path: str) -> None:
        """Update current directory display."""
        self.set_left(
            "directory",
            Path(path).name,
            icon="📁",
            style=PRESET_STYLES.PATH,
            priority=10,
        )
    
    def update_git_branch(self, branch: str, clean: bool = True) -> None:
        """Update git branch display."""
        icon = "🔀" if clean else "📝"
        style = PRESET_STYLES.SUCCESS if clean else PRESET_STYLES.WARNING
        
        self.set_right(
            "git",
            branch,
            icon=icon,
            style=style,
            priority=8,
        )
    
    def update_context_count(self, file_count: int, token_count: Optional[int] = None) -> None:
        """Update context files count."""
        if file_count == 0:
            text = "No files loaded"
            style = PRESET_STYLES.TERTIARY
        else:
            text = f"{file_count} file{'s' if file_count != 1 else ''}"
            if token_count:
                text += f" ({token_count} tokens)"
            style = PRESET_STYLES.INFO
        
        self.set_center(
            "context",
            text,
            icon="📄",
            style=style,
            priority=5,
        )
    
    def update_time(self) -> None:
        """Update time display."""
        self.set_right(
            "time",
            datetime.now().strftime("%H:%M"),
            icon="🕐",
            style=PRESET_STYLES.SECONDARY,
            priority=1,
        )


class MetricsStatusBar(StatusBar):
    """
    Pre-configured status bar for constitutional metrics.
    
    Shows:
    - Left: LEI (Live Engineering Index)
    - Center: HRI (Human Readability Index)
    - Right: Safety status
    """
    
    def __init__(self):
        """Initialize metrics status bar."""
        super().__init__()
        self._setup_default()
    
    def _setup_default(self):
        """Setup default segments."""
        self.update_lei(0.0)
        self.update_hri(100.0)
        self.update_safety("Safe")
    
    def update_lei(self, value: float) -> None:
        """
        Update LEI display.
        
        Args:
            value: LEI value (0.0-1.0)
        """
        # Color based on value
        if value < 0.2:
            style = PRESET_STYLES.SUCCESS
            icon = "✅"
        elif value < 0.5:
            style = PRESET_STYLES.WARNING
            icon = "⚠️"
        else:
            style = PRESET_STYLES.ERROR
            icon = "❌"
        
        self.set_left(
            "lei",
            f"LEI: {value:.2f}",
            icon=icon,
            style=style,
            priority=10,
        )
    
    def update_hri(self, value: float) -> None:
        """
        Update HRI display.
        
        Args:
            value: HRI percentage (0-100)
        """
        # Color based on value
        if value >= 80:
            style = PRESET_STYLES.SUCCESS
            icon = "📖"
        elif value >= 60:
            style = PRESET_STYLES.WARNING
            icon = "📕"
        else:
            style = PRESET_STYLES.ERROR
            icon = "📕"
        
        self.set_center(
            "hri",
            f"HRI: {value:.0f}%",
            icon=icon,
            style=style,
            priority=8,
        )
    
    def update_safety(self, status: str) -> None:
        """
        Update safety status.
        
        Args:
            status: Safety status (Safe, Warning, Danger)
        """
        status_config = {
            "Safe": {"icon": "🛡️", "style": PRESET_STYLES.SUCCESS},
            "Warning": {"icon": "⚠️", "style": PRESET_STYLES.WARNING},
            "Danger": {"icon": "🚨", "style": PRESET_STYLES.ERROR},
        }
        
        config = status_config.get(status, status_config["Safe"])
        
        self.set_right(
            "safety",
            status,
            icon=config["icon"],
            style=config["style"],
            priority=10,
        )


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def create_development_statusbar() -> DevelopmentStatusBar:
    """
    Create pre-configured development status bar.
    
    Returns:
        DevelopmentStatusBar instance
    """
    return DevelopmentStatusBar()


def create_metrics_statusbar() -> MetricsStatusBar:
    """
    Create pre-configured metrics status bar.
    
    Returns:
        MetricsStatusBar instance
    """
    return MetricsStatusBar()


# =============================================================================
# DEMO
# =============================================================================

if __name__ == "__main__":
    console = Console()
    
    # Development status bar
    console.print("[bold]Development Status Bar:[/bold]")
    dev_bar = create_development_statusbar()
    dev_bar.update_git_branch("main", clean=True)
    dev_bar.update_context_count(5, 2500)
    console.print(dev_bar.render())
    console.print()
    
    # Metrics status bar
    console.print("[bold]Metrics Status Bar:[/bold]")
    metrics_bar = create_metrics_statusbar()
    metrics_bar.update_lei(0.15)
    metrics_bar.update_hri(85.5)
    metrics_bar.update_safety("Safe")
    console.print(metrics_bar.render())
