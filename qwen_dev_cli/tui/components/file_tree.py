"""
import logging
logger = logging.getLogger(__name__)
Collapsible File Tree - VSCode/Cursor-style sidebar.

Inspiration:
- VSCode Explorer
- Cursor file tree
- macOS Finder sidebar
- IntelliJ Project view

Philosophy:
- Visual hierarchy (indent levels)
- Expand/collapse (interactive)
- Git status indicators
- Icon support
- Smart filtering
- Keyboard navigation

"The Lord is my light and my salvation—whom shall I fear?"
- Psalm 27:1

Created: 2025-11-19 00:45 UTC
"""

from typing import List, Optional, Dict, Set, Callable
from dataclasses import dataclass, field
from pathlib import Path
from enum import Enum
import os

from rich.console import Console
from rich.text import Text
from rich.tree import Tree
from rich.panel import Panel

from ..theme import COLORS
from ..styles import PRESET_STYLES


class FileType(Enum):
    """File type classification."""
    DIRECTORY = "directory"
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"
    HTML = "html"
    CSS = "css"
    JSON = "json"
    YAML = "yaml"
    MARKDOWN = "markdown"
    IMAGE = "image"
    TEXT = "text"
    BINARY = "binary"
    UNKNOWN = "unknown"


class GitStatus(Enum):
    """Git file status."""
    UNTRACKED = "untracked"
    MODIFIED = "modified"
    ADDED = "added"
    DELETED = "deleted"
    RENAMED = "renamed"
    CLEAN = "clean"


@dataclass
class FileNode:
    """Represents a file or directory in the tree."""
    name: str
    path: Path
    type: FileType
    is_dir: bool
    children: List['FileNode'] = field(default_factory=list)
    expanded: bool = False
    git_status: Optional[GitStatus] = None
    size: Optional[int] = None
    depth: int = 0
    
    def __post_init__(self, is_directory=None):
        # Allow is_directory as alias for is_dir
        if is_directory is not None:
            self.is_dir = is_directory
        """Initialize computed fields."""
        if self.is_dir and not self.children:
            # Lazy loading - children will be loaded when expanded
            self.children = []
    
    def toggle_expand(self):
        """Toggle expand/collapse state."""
        if self.is_dir:
            self.expanded = not self.expanded
    
    def add_child(self, node: 'FileNode'):
        """Add child node."""
        if self.is_dir:
            self.children.append(node)
            self.children.sort(key=lambda n: (not n.is_dir, n.name.lower()))
    
    def get_icon(self) -> str:
        """Get icon for file/directory."""
        if self.is_dir:
            return "📂" if self.expanded else "📁"
        
        icons = {
            FileType.PYTHON: "🐍",
            FileType.JAVASCRIPT: "📜",
            FileType.TYPESCRIPT: "📘",
            FileType.HTML: "🌐",
            FileType.CSS: "🎨",
            FileType.JSON: "📋",
            FileType.YAML: "⚙️",
            FileType.MARKDOWN: "📝",
            FileType.IMAGE: "🖼️",
            FileType.TEXT: "📄",
            FileType.BINARY: "📦",
            FileType.UNKNOWN: "❓"
        }
        
        return icons.get(self.type, "📄")
    
    def get_git_indicator(self) -> Optional[str]:
        """Get git status indicator."""
        if self.git_status is None or self.git_status == GitStatus.CLEAN:
            return None
        
        indicators = {
            GitStatus.UNTRACKED: "?",
            GitStatus.MODIFIED: "M",
            GitStatus.ADDED: "A",
            GitStatus.DELETED: "D",
            GitStatus.RENAMED: "R"
        }
        
        return indicators.get(self.git_status, "")


def detect_file_type(path: Path) -> FileType:
    """Detect file type from path."""
    if path.is_dir():
        return FileType.DIRECTORY
    
    suffix = path.suffix.lower()
    
    type_map = {
        '.py': FileType.PYTHON,
        '.js': FileType.JAVASCRIPT,
        '.jsx': FileType.JAVASCRIPT,
        '.ts': FileType.TYPESCRIPT,
        '.tsx': FileType.TYPESCRIPT,
        '.html': FileType.HTML,
        '.htm': FileType.HTML,
        '.css': FileType.CSS,
        '.scss': FileType.CSS,
        '.json': FileType.JSON,
        '.yaml': FileType.YAML,
        '.yml': FileType.YAML,
        '.md': FileType.MARKDOWN,
        '.png': FileType.IMAGE,
        '.jpg': FileType.IMAGE,
        '.jpeg': FileType.IMAGE,
        '.gif': FileType.IMAGE,
        '.svg': FileType.IMAGE,
        '.txt': FileType.TEXT,
        '.log': FileType.TEXT
    }
    
    return type_map.get(suffix, FileType.UNKNOWN)


class FileTree:
    """
    Interactive collapsible file tree.
    
    Features:
    - Expand/collapse directories
    - Git status indicators
    - File type icons
    - Smart filtering
    - Keyboard navigation
    - Click to open/close
    """
    
    def __init__(
        self,
        root_path: Path,
        console: Console,
        max_depth: int = 5,
        show_hidden: bool = False,
        git_aware: bool = True
    ):
        self.root_path = root_path
        self.console = console
        self.max_depth = max_depth
        self.show_hidden = show_hidden
        self.git_aware = git_aware
        
        self.root_node: Optional[FileNode] = None
        self.selected_node: Optional[FileNode] = None
        self.expanded_paths: Set[str] = set()
        self.git_status_cache: Dict[str, GitStatus] = {}
        
        # Filters
        self.ignore_patterns = {
            '__pycache__', '.git', '.venv', 'venv', 'node_modules',
            '.pytest_cache', '.mypy_cache', 'dist', 'build', '.eggs'
        }
    
    def build_tree(self) -> FileNode:
        """Build file tree from root path."""
        self.root_node = self._build_node(self.root_path, depth=0)
        
        if self.git_aware:
            self._load_git_status()
        
        return self.root_node
    
    def _build_node(self, path: Path, depth: int) -> FileNode:
        """Build node recursively."""
        is_dir = path.is_dir()
        file_type = detect_file_type(path)
        
        node = FileNode(
            name=path.name or str(path),
            path=path,
            type=file_type,
            is_dir=is_dir,
            depth=depth,
            expanded=str(path) in self.expanded_paths
        )
        
        # Build children for directories
        if is_dir and depth < self.max_depth:
            try:
                for child_path in sorted(path.iterdir()):
                    # Skip hidden files
                    if not self.show_hidden and child_path.name.startswith('.'):
                        continue
                    
                    # Skip ignored patterns
                    if child_path.name in self.ignore_patterns:
                        continue
                    
                    child_node = self._build_node(child_path, depth + 1)
                    node.add_child(child_node)
            except PermissionError as e:
                logger.debug(f"Permission denied for {node.path}: {e}")
        
        return node
    
    def _load_git_status(self):
        """Load git status for files."""
        # Git status detection deferred - requires gitpython dependency
        # For now, just placeholder
        pass
    
    def toggle_node(self, node: FileNode):
        """Toggle expand/collapse for node."""
        node.toggle_expand()
        
        if node.expanded:
            self.expanded_paths.add(str(node.path))
        else:
            self.expanded_paths.discard(str(node.path))
    
    def render(self) -> Panel:
        """Render file tree as Rich panel."""
        if not self.root_node:
            self.build_tree()
        
        tree = self._render_node_tree(self.root_node)
        
        panel = Panel(
            tree,
            title=f"📁 {self.root_path.name}",
            title_align="left",
            border_style=COLORS['primary'],
            box=PRESET_STYLES['rounded'],
            padding=(1, 1)
        )
        
        return panel
    
    def _render_node_tree(self, node: FileNode) -> Tree:
        """Render node as Rich Tree."""
        # Create label
        label = self._create_node_label(node)
        
        # Create tree
        tree = Tree(label)
        
        # Add children if expanded
        if node.is_dir and node.expanded:
            for child in node.children:
                child_tree = self._render_node_tree(child)
                tree.add(child_tree)
        
        return tree
    
    def _create_node_label(self, node: FileNode) -> Text:
        """Create label for node."""
        label = Text()
        
        # Icon
        icon = node.get_icon()
        label.append(f"{icon} ", style=COLORS['secondary'])
        
        # Name
        name_style = f"bold {COLORS['primary']}" if node.is_dir else COLORS['secondary']
        if node == self.selected_node:
            name_style = f"bold {COLORS['accent']}"
        
        label.append(node.name, style=name_style)
        
        # Git status indicator
        git_indicator = node.get_git_indicator()
        if git_indicator:
            git_color = self._get_git_color(node.git_status)
            label.append(f" [{git_indicator}]", style=f"bold {git_color}")
        
        # Size for files
        if not node.is_dir and node.size:
            size_str = self._format_size(node.size)
            label.append(f" ({size_str})", style=f"dim {COLORS['muted']}")
        
        return label
    
    def _get_git_color(self, status: Optional[GitStatus]) -> str:
        """Get color for git status."""
        colors = {
            GitStatus.UNTRACKED: COLORS['info'],
            GitStatus.MODIFIED: COLORS['warning'],
            GitStatus.ADDED: COLORS['success'],
            GitStatus.DELETED: COLORS['error'],
            GitStatus.RENAMED: COLORS['accent']
        }
        return colors.get(status, COLORS['muted'])
    
    def _format_size(self, size: int) -> str:
        """Format file size."""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f}{unit}"
            size /= 1024.0
        return f"{size:.1f}TB"
    
    def find_node(self, path: Path) -> Optional[FileNode]:
        """Find node by path."""
        if not self.root_node:
            return None
        
        return self._find_node_recursive(self.root_node, path)
    
    def _find_node_recursive(self, node: FileNode, path: Path) -> Optional[FileNode]:
        """Find node recursively."""
        if node.path == path:
            return node
        
        for child in node.children:
            result = self._find_node_recursive(child, path)
            if result:
                return result
        
        return None
    
    def refresh(self):
        """Refresh file tree."""
        self.root_node = None
        self.build_tree()


def create_file_tree(
    root_path: str,
    console: Console,
    max_depth: int = 3,
    show_hidden: bool = False
) -> FileTree:
    """Create configured file tree."""
    return FileTree(
        root_path=Path(root_path),
        console=console,
        max_depth=max_depth,
        show_hidden=show_hidden
    )
