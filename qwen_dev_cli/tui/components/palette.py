"""
Command Palette - Cmd+K style command launcher with fuzzy search.

Inspiration:
- VSCode Command Palette (Cmd+K)
- Sublime Text Command Palette
- Apple Spotlight
- GitHub Command Palette

Philosophy:
- Instant feedback (< 50ms)
- Fuzzy search (forgiving)
- Keyboard-first (accessible)
- Categories with icons
- Recent commands (smart)
- Elegant animations

"If any of you lacks wisdom, let him ask God, who gives generously to all."
- James 1:5

Created: 2025-11-18 21:44 UTC
"""

import re
from typing import List, Optional, Callable, Dict, Set
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.align import Align

from ..theme import COLORS
from ..styles import PRESET_STYLES
from ..wisdom import get_random_verse


class CommandCategory(Enum):
    """Command categories."""
    FILE = "file"
    EDIT = "edit"
    SEARCH = "search"
    GIT = "git"
    TOOLS = "tools"
    VIEW = "view"
    HELP = "help"
    SYSTEM = "system"


# Category icons and colors
CATEGORY_CONFIG = {
    CommandCategory.FILE: {"icon": "📄", "color": COLORS['accent_blue']},
    CommandCategory.EDIT: {"icon": "✏️", "color": COLORS['accent_green']},
    CommandCategory.SEARCH: {"icon": "🔍", "color": COLORS['accent_yellow']},
    CommandCategory.GIT: {"icon": "🔀", "color": COLORS['accent_purple']},
    CommandCategory.TOOLS: {"icon": "🔧", "color": COLORS['accent_blue']},
    CommandCategory.VIEW: {"icon": "👁️", "color": COLORS['text_secondary']},
    CommandCategory.HELP: {"icon": "❓", "color": COLORS['accent_yellow']},
    CommandCategory.SYSTEM: {"icon": "⚙️", "color": COLORS['text_secondary']},
}


@dataclass
class Command:
    """
    name: str
    description: str
    category: str
    id: str = ""
    shortcut: str = ""
    icon: str = ""
    
    def __post_init__(self):
        if not self.id:
            self.id = self.name.lower().replace(" ", "_")
    
    Attributes:
        id: Unique command identifier
        title: Display title
        description: Short description
        category: Command category
        keywords: Additional search keywords
        keybinding: Keyboard shortcut (if any)
        action: Function to execute
        enabled: Is command enabled
    """
    id: str
    title: str
    description: str
    category: CommandCategory
    keywords: List[str] = field(default_factory=list)
    keybinding: Optional[str] = None
    action: Optional[Callable] = None
    enabled: bool = True
    last_used: Optional[datetime] = None
    use_count: int = 0
    
    @property
    def search_text(self) -> str:
        """Get combined text for searching."""
        parts = [
            self.title.lower(),
            self.description.lower(),
            self.category.value.lower(),
        ] + [k.lower() for k in self.keywords]
        return " ".join(parts)
    
    @property
    def display_title(self) -> Text:
        """Get formatted title with category icon."""
        config = CATEGORY_CONFIG[self.category]
        text = Text()
        text.append(f"{config['icon']} ", style=config['color'])
        text.append(self.title, style=PRESET_STYLES.EMPHASIS)
        
        if self.keybinding:
            text.append(f"  [{self.keybinding}]", style=PRESET_STYLES.TERTIARY)
        
        return text
    
    def mark_used(self):
        """Mark command as used (for recency tracking)."""
        self.last_used = datetime.now()
        self.use_count += 1


class FuzzyMatcher:
    """
    Fuzzy string matching for command search.
    
    Algorithm:
    - Sequential character matching
    - Case-insensitive
    - Score based on:
      1. Match position (earlier = better)
      2. Consecutive matches (bonus)
      3. Start of word matches (bonus)
      
    Examples:
        matcher = FuzzyMatcher()
        score = matcher.score("file open", "fo")  # High score
        score = matcher.score("file open", "fop")  # Very high score
    """
    
    def __init__(self):
        """Initialize matcher."""
        pass
    
    def score(self, text: str, query: str) -> float:
        """
        Calculate fuzzy match score.
        
        Args:
            text: Text to search in
            query: Search query
            
        Returns:
            Score (0.0 = no match, 1.0 = perfect match)
        """
        if not query:
            return 1.0
        
        text = text.lower()
        query = query.lower()
        
        # Quick exact match check
        if query in text:
            # Bonus for exact substring
            position_score = 1.0 - (text.index(query) / len(text))
            return 0.8 + (0.2 * position_score)
        
        # Fuzzy matching
        text_idx = 0
        query_idx = 0
        matches = []
        
        while query_idx < len(query) and text_idx < len(text):
            if text[text_idx] == query[query_idx]:
                matches.append(text_idx)
                query_idx += 1
            text_idx += 1
        
        # Not all query characters found
        if query_idx < len(query):
            return 0.0
        
        # Calculate score based on match positions
        if not matches:
            return 0.0
        
        # Base score: how much of query matched
        base_score = len(matches) / len(text)
        
        # Position bonus: earlier matches better
        position_score = 1.0 - (matches[0] / len(text))
        
        # Consecutive bonus: adjacent matches better
        consecutive_count = 0
        for i in range(1, len(matches)):
            if matches[i] == matches[i-1] + 1:
                consecutive_count += 1
        consecutive_score = consecutive_count / max(len(matches) - 1, 1)
        
        # Word start bonus: matches at word boundaries
        word_start_count = 0
        words = text.split()
        word_positions = []
        pos = 0
        for word in words:
            word_positions.append(pos)
            pos += len(word) + 1
        
        for match_pos in matches:
            if match_pos in word_positions:
                word_start_count += 1
        word_start_score = word_start_count / len(matches)
        
        # Weighted combination
        final_score = (
            base_score * 0.3 +
            position_score * 0.2 +
            consecutive_score * 0.3 +
            word_start_score * 0.2
        )
        
        return min(final_score, 1.0)
    
    def matches(self, text: str, query: str, threshold: float = 0.3) -> bool:
        """
        Check if text matches query.
        
        Args:
            text: Text to search in
            query: Search query
            threshold: Minimum score to consider a match
            
        Returns:
            True if matches
        """
        return self.score(text, query) >= threshold


class CommandPalette:
    """
    Command palette with fuzzy search and keyboard navigation.
    
    Examples:
        palette = CommandPalette()
        palette.add_command(Command(
            id="file.open",
            title="Open File",
            description="Open a file in the editor",
            category=CommandCategory.FILE,
            keybinding="Ctrl+O"
        ))
        
        # Search
        results = palette.search("open")
        
        # Execute
        palette.execute_command("file.open")
    """
    
    def __init__(self):
        """Initialize command palette."""
        self.commands: Dict[str, Command] = {}
        self.matcher = FuzzyMatcher()
        self.recent_limit = 5
    
    def add_command(self, command: Command) -> None:
        """
        Add command to palette.
        
        Args:
            command: Command to add
        """
        self.commands[command.id] = command
    
    def add_commands(self, commands: List[Command]) -> None:
        """
        Add multiple commands.
        
        Args:
            commands: List of commands to add
        """
        for cmd in commands:
            self.add_command(cmd)
    
    def get_command(self, command_id: str) -> Optional[Command]:
        """
        Get command by ID.
        
        Args:
            command_id: Command identifier
            
        Returns:
            Command if found, None otherwise
        """
        return self.commands.get(command_id)
    
    def search(
        self,
        query: str,
        limit: int = 10,
        category: Optional[CommandCategory] = None,
        include_recent: bool = True,
    ) -> List[Command]:
        """
        Search commands with fuzzy matching.
        
        Args:
            query: Search query
            limit: Maximum results
            category: Filter by category
            include_recent: Include recent commands at top
            
        Returns:
            List of matching commands (sorted by relevance)
        """
        if not query.strip():
            # No query: show recent or all
            if include_recent:
                return self.get_recent_commands(limit)
            else:
                return list(self.commands.values())[:limit]
        
        # Filter by category if specified
        candidates = self.commands.values()
        if category:
            candidates = [c for c in candidates if c.category == category]
        
        # Score all commands
        scored = []
        for cmd in candidates:
            if not cmd.enabled:
                continue
            
            score = self.matcher.score(cmd.search_text, query)
            if score > 0.0:
                scored.append((score, cmd))
        
        # Sort by score (descending)
        scored.sort(key=lambda x: x[0], reverse=True)
        
        # Boost recent commands
        if include_recent:
            recent_ids = {cmd.id for cmd in self.get_recent_commands()}
            boosted = []
            for score, cmd in scored:
                if cmd.id in recent_ids:
                    score *= 1.2  # 20% boost for recent commands
                boosted.append((score, cmd))
            scored = boosted
            scored.sort(key=lambda x: x[0], reverse=True)
        
        # Return top results
        return [cmd for score, cmd in scored[:limit]]
    
    def get_recent_commands(self, limit: int = 5) -> List[Command]:
        """
        Get recently used commands.
        
        Args:
            limit: Maximum number of commands
            
        Returns:
            List of recent commands (sorted by recency)
        """
        recent = [cmd for cmd in self.commands.values() if cmd.last_used]
        recent.sort(key=lambda c: c.last_used, reverse=True)
        return recent[:limit]
    
    def get_popular_commands(self, limit: int = 5) -> List[Command]:
        """
        Get most used commands.
        
        Args:
            limit: Maximum number of commands
            
        Returns:
            List of popular commands (sorted by use count)
        """
        popular = [cmd for cmd in self.commands.values() if cmd.use_count > 0]
        popular.sort(key=lambda c: c.use_count, reverse=True)
        return popular[:limit]
    
    def execute_command(self, command_id: str) -> bool:
        """
        Execute command by ID.
        
        Args:
            command_id: Command identifier
            
        Returns:
            True if executed successfully
        """
        cmd = self.get_command(command_id)
        if not cmd or not cmd.enabled:
            return False
        
        # Mark as used
        cmd.mark_used()
        
        # Execute action
        if cmd.action:
            try:
                cmd.action()
                return True
            except Exception:
                return False
        
        return True
    
    def render_search_results(
        self,
        query: str,
        selected_index: int = 0,
        limit: int = 8,
    ) -> Panel:
        """
        Render search results as panel.
        
        Args:
            query: Current search query
            selected_index: Currently selected result index
            limit: Maximum results to show
            
        Returns:
            Rich Panel with results
        """
        results = self.search(query, limit=limit)
        
        if not results:
            # No results
            content = Text()
            content.append("No commands found", style=PRESET_STYLES.TERTIARY)
            
            # Show biblical verse for encouragement
            verse = get_random_verse(60)
            content.append(f"\n\n{verse}", style=PRESET_STYLES.DIM)
            
            return Panel(
                Align.center(content),
                title="[bold]Command Palette[/bold]",
                subtitle=f"[dim]{query}[/dim]" if query else None,
                border_style=COLORS['border_muted'],
                padding=(1, 2),
            )
        
        # Build results table
        table = Table.grid(padding=(0, 1))
        table.add_column("", style=PRESET_STYLES.TERTIARY, width=2)  # Selection indicator
        table.add_column("Command", style=PRESET_STYLES.PRIMARY)
        table.add_column("Description", style=PRESET_STYLES.SECONDARY)
        
        for idx, cmd in enumerate(results):
            # Selection indicator
            indicator = "▶" if idx == selected_index else " "
            
            # Command title with highlighting
            title = cmd.display_title
            
            # Description
            desc = Text(cmd.description, style=PRESET_STYLES.TERTIARY)
            
            # Add row with highlighting if selected
            if idx == selected_index:
                table.add_row(
                    Text(indicator, style=PRESET_STYLES.SUCCESS),
                    title,
                    desc,
                    style=PRESET_STYLES.HIGHLIGHT,
                )
            else:
                table.add_row(indicator, title, desc)
        
        # Query display
        query_text = Text()
        query_text.append("Search: ", style=PRESET_STYLES.SECONDARY)
        query_text.append(query or "(type to search)", style=PRESET_STYLES.EMPHASIS if query else PRESET_STYLES.DIM)
        
        return Panel(
            table,
            title="[bold]⌘ Command Palette[/bold]",
            subtitle=query_text,
            border_style=COLORS['accent_blue'],
            padding=(1, 2),
        )


# =============================================================================
# DEFAULT COMMANDS
# =============================================================================

DEFAULT_COMMANDS = [
    # File commands
    Command(
        id="file.open",
        title="Open File",
        description="Open a file in the editor",
        category=CommandCategory.FILE,
        keywords=["read", "load"],
        keybinding="Ctrl+O",
    ),
    Command(
        id="file.save",
        title="Save File",
        description="Save current file",
        category=CommandCategory.FILE,
        keywords=["write"],
        keybinding="Ctrl+S",
    ),
    Command(
        id="file.tree",
        title="Show File Tree",
        description="Display directory tree",
        category=CommandCategory.FILE,
        keywords=["directory", "folder", "ls"],
    ),
    
    # Search commands
    Command(
        id="search.files",
        title="Search Files",
        description="Search for files by name",
        category=CommandCategory.SEARCH,
        keywords=["find", "locate"],
        keybinding="Ctrl+P",
    ),
    Command(
        id="search.content",
        title="Search in Files",
        description="Search text in file contents",
        category=CommandCategory.SEARCH,
        keywords=["grep", "find", "text"],
        keybinding="Ctrl+Shift+F",
    ),
    
    # Git commands
    Command(
        id="git.status",
        title="Git Status",
        description="Show git repository status",
        category=CommandCategory.GIT,
        keywords=["vcs", "version"],
    ),
    Command(
        id="git.diff",
        title="Git Diff",
        description="Show changes in working directory",
        category=CommandCategory.GIT,
        keywords=["changes", "modifications"],
    ),
    Command(
        id="git.commit",
        title="Git Commit",
        description="Commit staged changes",
        category=CommandCategory.GIT,
        keywords=["save", "checkpoint"],
    ),
    
    # Tools
    Command(
        id="tools.terminal",
        title="Open Terminal",
        description="Open integrated terminal",
        category=CommandCategory.TOOLS,
        keywords=["shell", "bash"],
        keybinding="Ctrl+`",
    ),
    
    # View
    Command(
        id="view.metrics",
        title="Show Metrics",
        description="Display LEI, HRI, and CPI metrics",
        category=CommandCategory.VIEW,
        keywords=["constitutional", "lei", "hri", "stats"],
    ),
    
    # Help
    Command(
        id="help.commands",
        title="Show All Commands",
        description="List all available commands",
        category=CommandCategory.HELP,
        keywords=["list", "palette"],
        keybinding="Ctrl+Shift+P",
    ),
]


def create_default_palette() -> CommandPalette:
    """
    Create palette with default commands.
    
    Returns:
        CommandPalette with default commands
    """
    palette = CommandPalette()
    palette.add_commands(DEFAULT_COMMANDS)
    return palette


# =============================================================================
# QUICK DEMO
# =============================================================================

if __name__ == "__main__":
    console = Console()
    palette = create_default_palette()
    
    # Demo searches
    queries = ["", "open", "git", "search", "xyz"]
    
    for query in queries:
        console.print(palette.render_search_results(query, selected_index=0))
        console.print()
