"""
Context Pills - Closeable badges for active context files.

Inspiration:
- Browser tabs (Chrome, Safari)
- VSCode breadcrumbs
- Notion tags
- macOS Tags

Philosophy:
- Visual context (what's loaded)
- Quick removal (closeable)
- Color-coded (file types)
- Token-aware (show size)
- Elegant overflow (scroll indicators)

"In all your ways acknowledge him, and he will make straight your paths." 
- Proverbs 3:6

Created: 2025-11-18 21:44 UTC
"""

from typing import List, Optional, Dict, Callable
from dataclasses import dataclass
from pathlib import Path
from enum import Enum

from rich.console import Console
from rich.text import Text
from rich.table import Table
from rich.panel import Panel

from ..theme import COLORS
from ..styles import PRESET_STYLES


class PillType(Enum):
    """Context pill types (file types)."""
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"
    HTML = "html"
    CSS = "css"
    JSON = "json"
    MARKDOWN = "markdown"
    TEXT = "text"
    OTHER = "other"


# Pill styling by type
PILL_STYLES = {
    PillType.PYTHON: {
        "color": COLORS['accent_blue'],
        "icon": "🐍",
        "bg": "#1e3a8a",  # Dark blue
    },
    PillType.JAVASCRIPT: {
        "color": COLORS['accent_yellow'],
        "icon": "📜",
        "bg": "#78350f",  # Dark yellow
    },
    PillType.TYPESCRIPT: {
        "color": COLORS['accent_blue'],
        "icon": "🔷",
        "bg": "#164e63",  # Dark cyan
    },
    PillType.HTML: {
        "color": COLORS['accent_red'],
        "icon": "🌐",
        "bg": "#7f1d1d",  # Dark red
    },
    PillType.CSS: {
        "color": COLORS['accent_purple'],
        "icon": "🎨",
        "bg": "#581c87",  # Dark purple
    },
    PillType.JSON: {
        "color": COLORS['accent_green'],
        "icon": "📦",
        "bg": "#14532d",  # Dark green
    },
    PillType.MARKDOWN: {
        "color": COLORS['text_primary'],
        "icon": "📝",
        "bg": "#374151",  # Dark gray
    },
    PillType.TEXT: {
        "color": COLORS['text_secondary'],
        "icon": "📄",
        "bg": "#1f2937",  # Darker gray
    },
    PillType.OTHER: {
        "color": COLORS['text_tertiary'],
        "icon": "📁",
        "bg": "#111827",  # Almost black
    },
}


def detect_pill_type(path: Path) -> PillType:
    """
    Detect pill type from file extension.
    
    Args:
        path: File path
        
    Returns:
        PillType enum
    """
    ext = path.suffix.lower()
    
    type_map = {
        ".py": PillType.PYTHON,
        ".pyi": PillType.PYTHON,
        ".js": PillType.JAVASCRIPT,
        ".jsx": PillType.JAVASCRIPT,
        ".ts": PillType.TYPESCRIPT,
        ".tsx": PillType.TYPESCRIPT,
        ".html": PillType.HTML,
        ".htm": PillType.HTML,
        ".css": PillType.CSS,
        ".scss": PillType.CSS,
        ".json": PillType.JSON,
        ".md": PillType.MARKDOWN,
        ".markdown": PillType.MARKDOWN,
        ".txt": PillType.TEXT,
    }
    
    return type_map.get(ext, PillType.OTHER)


@dataclass
class ContextPill:
    """
    A pill representing a loaded file.
    
    Attributes:
        id: Unique identifier
        path: File path
        display_name: Short display name
        pill_type: PillType enum
        token_count: Token count (if known)
        closeable: Can be closed
        on_close: Callback when closed
    """
    id: str
    path: Path
    display_name: str
    pill_type: PillType
    token_count: Optional[int] = None
    closeable: bool = True
    on_close: Optional[Callable] = None
    
    @classmethod
    def from_path(cls, path: str, token_count: Optional[int] = None) -> 'ContextPill':
        """
        Create pill from file path.
        
        Args:
            path: File path
            token_count: Token count (if known)
            
        Returns:
            ContextPill instance
        """
        path_obj = Path(path)
        return cls(
            id=str(path_obj),
            path=path_obj,
            display_name=path_obj.name,
            pill_type=detect_pill_type(path_obj),
            token_count=token_count,
        )
    
    def render(self, selected: bool = False, show_close: bool = True) -> Text:
        """
        Render pill as Text.
        
        Args:
            selected: Is pill selected (highlighted)
            show_close: Show close button (×)
            
        Returns:
            Rich Text object
        """
        style = PILL_STYLES[self.pill_type]
        
        result = Text()
        
        # Icon
        result.append(f"{style['icon']} ", style=style['color'])
        
        # Display name
        name_style = PRESET_STYLES.EMPHASIS if selected else PRESET_STYLES.PRIMARY
        result.append(self.display_name, style=name_style)
        
        # Token count (if available)
        if self.token_count is not None:
            result.append(f" ({self.token_count}t)", style=PRESET_STYLES.TERTIARY)
        
        # Close button
        if self.closeable and show_close:
            close_style = PRESET_STYLES.ERROR if selected else PRESET_STYLES.TERTIARY
            result.append(" ×", style=close_style)
        
        return result
    
    def close(self) -> bool:
        """
        Close pill (trigger callback).
        
        Returns:
            True if closed successfully
        """
        if not self.closeable:
            return False
        
        if self.on_close:
            try:
                self.on_close(self)
                return True
            except Exception:
                return False
        
        return True


class PillContainer:
    """
    Container for managing multiple context pills.
    
    Features:
    - Add/remove pills
    - Selection support
    - Overflow handling (scroll indicators)
    - Total token count
    - Batch operations
    
    Examples:
        container = PillContainer()
        pill = ContextPill.from_path("src/main.py", token_count=150)
        container.add_pill(pill)
        console.print(container.render())
    """
    
    def __init__(self, max_display: int = 10):
        """
        Initialize pill container.
        
        Args:
            max_display: Maximum pills to display (overflow shows "...")
        """
        self.pills: Dict[str, ContextPill] = {}
        self.selected_id: Optional[str] = None
        self.max_display = max_display
    
    def add_pill(self, pill: ContextPill) -> None:
        """
        Add pill to container.
        
        Args:
            pill: ContextPill to add
        """
        self.pills[pill.id] = pill
        
        # Auto-select if first pill
        if len(self.pills) == 1:
            self.selected_id = pill.id
    
    def remove_pill(self, pill_id: str) -> bool:
        """
        Remove pill by ID.
        
        Args:
            pill_id: Pill identifier
            
        Returns:
            True if removed
        """
        if pill_id in self.pills:
            pill = self.pills[pill_id]
            
            # Trigger close callback
            if pill.on_close:
                pill.close()
            
            del self.pills[pill_id]
            
            # Update selection
            if self.selected_id == pill_id:
                self.selected_id = next(iter(self.pills), None)
            
            return True
        
        return False
    
    def clear_all(self) -> None:
        """Remove all pills."""
        for pill_id in list(self.pills.keys()):
            self.remove_pill(pill_id)
    
    def get_pill(self, pill_id: str) -> Optional[ContextPill]:
        """Get pill by ID."""
        return self.pills.get(pill_id)
    
    def select_pill(self, pill_id: str) -> bool:
        """
        Select pill by ID.
        
        Args:
            pill_id: Pill identifier
            
        Returns:
            True if selected
        """
        if pill_id in self.pills:
            self.selected_id = pill_id
            return True
        return False
    
    def select_next(self) -> None:
        """Select next pill (circular)."""
        if not self.pills:
            return
        
        pill_ids = list(self.pills.keys())
        if self.selected_id is None:
            self.selected_id = pill_ids[0]
        else:
            try:
                current_idx = pill_ids.index(self.selected_id)
                next_idx = (current_idx + 1) % len(pill_ids)
                self.selected_id = pill_ids[next_idx]
            except ValueError:
                self.selected_id = pill_ids[0]
    
    def select_previous(self) -> None:
        """Select previous pill (circular)."""
        if not self.pills:
            return
        
        pill_ids = list(self.pills.keys())
        if self.selected_id is None:
            self.selected_id = pill_ids[-1]
        else:
            try:
                current_idx = pill_ids.index(self.selected_id)
                prev_idx = (current_idx - 1) % len(pill_ids)
                self.selected_id = pill_ids[prev_idx]
            except ValueError:
                self.selected_id = pill_ids[-1]
    
    def remove_selected(self) -> bool:
        """Remove currently selected pill."""
        if self.selected_id:
            return self.remove_pill(self.selected_id)
        return False
    
    def get_total_tokens(self) -> int:
        """
        Get total token count across all pills.
        
        Returns:
            Total tokens
        """
        return sum(p.token_count or 0 for p in self.pills.values())
    
    def render(
        self,
        title: Optional[str] = None,
        show_stats: bool = True,
        show_overflow: bool = True,
    ) -> Panel:
        """
        Render pill container.
        
        Args:
            title: Panel title
            show_stats: Show statistics (count, tokens)
            show_overflow: Show overflow indicator
            
        Returns:
            Rich Panel object
        """
        if not self.pills:
            # Empty state
            content = Text()
            content.append("No files loaded", style=PRESET_STYLES.TERTIARY)
            content.append("\nAdd files to see them here", style=PRESET_STYLES.DIM)
            
            return Panel(
                content,
                title=title or "[bold]Context Files[/bold]",
                border_style=COLORS['border_muted'],
                padding=(1, 2),
            )
        
        # Build pills grid
        table = Table.grid(padding=(0, 1))
        table.add_column()
        
        # Display pills (with overflow handling)
        pills_list = list(self.pills.values())
        display_pills = pills_list[:self.max_display]
        overflow_count = len(pills_list) - self.max_display
        
        # Add each pill
        for pill in display_pills:
            selected = (pill.id == self.selected_id)
            pill_text = pill.render(selected=selected)
            
            # Add selection indicator
            if selected:
                indicator = Text("▶ ", style=PRESET_STYLES.SUCCESS)
                indicator.append(pill_text)
                table.add_row(indicator)
            else:
                table.add_row(Text("  ") + pill_text)
        
        # Show overflow indicator
        if show_overflow and overflow_count > 0:
            overflow_text = Text()
            overflow_text.append(f"  ... and {overflow_count} more", style=PRESET_STYLES.DIM)
            table.add_row(overflow_text)
        
        # Build subtitle with stats
        subtitle = None
        if show_stats:
            total_tokens = self.get_total_tokens()
            stats_text = Text()
            stats_text.append(f"{len(self.pills)} file{'s' if len(self.pills) != 1 else ''}", 
                            style=PRESET_STYLES.INFO)
            if total_tokens > 0:
                stats_text.append(f" • {total_tokens:,} tokens", style=PRESET_STYLES.SECONDARY)
            subtitle = stats_text
        
        return Panel(
            table,
            title=title or "[bold]📄 Context Files[/bold]",
            subtitle=subtitle,
            border_style=COLORS['accent_green'],
            padding=(1, 2),
        )


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def create_pill_from_file(
    path: str,
    token_count: Optional[int] = None,
    on_close: Optional[Callable] = None,
) -> ContextPill:
    """
    Quick helper to create pill from file path.
    
    Args:
        path: File path
        token_count: Token count (if known)
        on_close: Close callback
        
    Returns:
        ContextPill instance
    """
    pill = ContextPill.from_path(path, token_count=token_count)
    pill.on_close = on_close
    return pill


# =============================================================================
# DEMO
# =============================================================================

if __name__ == "__main__":
    console = Console()
    
    # Create container
    container = PillContainer(max_display=5)
    
    # Add some pills
    files = [
        ("src/main.py", 250),
        ("src/utils.py", 180),
        ("tests/test_main.py", 120),
        ("README.md", 50),
        ("config.json", 30),
        ("styles.css", 200),
        ("index.html", 100),
    ]
    
    for path, tokens in files:
        pill = create_pill_from_file(path, token_count=tokens)
        container.add_pill(pill)
    
    # Render
    console.print(container.render())
    console.print()
    
    # Select and show again
    container.select_next()
    container.select_next()
    console.print("[bold]After selecting 3rd pill:[/bold]")
    console.print(container.render())
