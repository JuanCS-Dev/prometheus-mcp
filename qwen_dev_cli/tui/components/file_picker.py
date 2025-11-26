"""File Picker Completer - @ trigger for file search with autocomplete.

Constitutional compliance: P1 (Completeness), P2 (Validation), P6 (Efficiency)

This module implements Claude Code-style @ mentions for file selection:
- Type @ to trigger file picker dropdown
- Fuzzy search across project files
- Recent files prioritized
- Git-aware (respects .gitignore)
"""

import os
import fnmatch
import logging
from pathlib import Path
from typing import List, Optional, Set, Iterator, Tuple
from dataclasses import dataclass, field
from enum import Enum

from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.document import Document

logger = logging.getLogger(__name__)


class FileType(Enum):
    """File type classification for icons."""
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"
    RUST = "rust"
    GO = "go"
    MARKDOWN = "markdown"
    JSON = "json"
    YAML = "yaml"
    TOML = "toml"
    HTML = "html"
    CSS = "css"
    SQL = "sql"
    SHELL = "shell"
    DOCKERFILE = "dockerfile"
    DIRECTORY = "directory"
    CONFIG = "config"
    TEXT = "text"
    UNKNOWN = "unknown"


# File extension to type mapping
EXTENSION_MAP = {
    '.py': FileType.PYTHON,
    '.pyx': FileType.PYTHON,
    '.pyi': FileType.PYTHON,
    '.js': FileType.JAVASCRIPT,
    '.jsx': FileType.JAVASCRIPT,
    '.mjs': FileType.JAVASCRIPT,
    '.ts': FileType.TYPESCRIPT,
    '.tsx': FileType.TYPESCRIPT,
    '.rs': FileType.RUST,
    '.go': FileType.GO,
    '.md': FileType.MARKDOWN,
    '.mdx': FileType.MARKDOWN,
    '.json': FileType.JSON,
    '.yaml': FileType.YAML,
    '.yml': FileType.YAML,
    '.toml': FileType.TOML,
    '.html': FileType.HTML,
    '.htm': FileType.HTML,
    '.css': FileType.CSS,
    '.scss': FileType.CSS,
    '.sass': FileType.CSS,
    '.sql': FileType.SQL,
    '.sh': FileType.SHELL,
    '.bash': FileType.SHELL,
    '.zsh': FileType.SHELL,
    '.fish': FileType.SHELL,
    '.txt': FileType.TEXT,
    '.rst': FileType.TEXT,
    '.cfg': FileType.CONFIG,
    '.ini': FileType.CONFIG,
    '.conf': FileType.CONFIG,
    '.env': FileType.CONFIG,
}

# Special filenames
SPECIAL_FILES = {
    'Dockerfile': FileType.DOCKERFILE,
    'docker-compose.yml': FileType.DOCKERFILE,
    'docker-compose.yaml': FileType.DOCKERFILE,
    'Makefile': FileType.SHELL,
    'CMakeLists.txt': FileType.CONFIG,
    'requirements.txt': FileType.CONFIG,
    'pyproject.toml': FileType.TOML,
    'package.json': FileType.JSON,
    'tsconfig.json': FileType.JSON,
    'Cargo.toml': FileType.TOML,
    'go.mod': FileType.GO,
    '.gitignore': FileType.CONFIG,
    '.dockerignore': FileType.CONFIG,
}

# File type icons (NerdFont compatible)
FILE_ICONS = {
    FileType.PYTHON: '🐍',
    FileType.JAVASCRIPT: '📜',
    FileType.TYPESCRIPT: '💠',
    FileType.RUST: '🦀',
    FileType.GO: '🔵',
    FileType.MARKDOWN: '📝',
    FileType.JSON: '📋',
    FileType.YAML: '⚙️',
    FileType.TOML: '⚙️',
    FileType.HTML: '🌐',
    FileType.CSS: '🎨',
    FileType.SQL: '🗃️',
    FileType.SHELL: '💻',
    FileType.DOCKERFILE: '🐳',
    FileType.DIRECTORY: '📁',
    FileType.CONFIG: '⚙️',
    FileType.TEXT: '📄',
    FileType.UNKNOWN: '📄',
}


@dataclass
class FileEntry:
    """Represents a file in the picker."""
    path: Path
    relative_path: str
    name: str
    file_type: FileType
    score: float = 0.0
    is_recent: bool = False
    git_status: Optional[str] = None

    def get_icon(self) -> str:
        """Get icon for file type."""
        return FILE_ICONS.get(self.file_type, '📄')

    def get_display(self) -> str:
        """Get display string with icon."""
        icon = self.get_icon()
        recent_marker = "★ " if self.is_recent else ""
        return f"{icon} {recent_marker}{self.name}"

    def get_description(self) -> str:
        """Get description (parent path)."""
        parent = str(Path(self.relative_path).parent)
        return parent if parent != '.' else ''


class GitIgnoreParser:
    """Parse and apply .gitignore patterns."""

    def __init__(self, root_path: Path):
        self.root_path = root_path
        self.patterns: List[Tuple[str, bool]] = []  # (pattern, is_negation)
        self._load_gitignore()

    def _load_gitignore(self):
        """Load .gitignore patterns from root."""
        gitignore_path = self.root_path / '.gitignore'
        if not gitignore_path.exists():
            return

        try:
            with open(gitignore_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    # Skip comments and empty lines
                    if not line or line.startswith('#'):
                        continue

                    # Handle negation
                    is_negation = line.startswith('!')
                    if is_negation:
                        line = line[1:]

                    self.patterns.append((line, is_negation))
        except Exception as e:
            logger.debug(f"Failed to parse .gitignore: {e}")

    def is_ignored(self, path: Path) -> bool:
        """Check if path should be ignored."""
        try:
            rel_path = path.relative_to(self.root_path)
            path_str = str(rel_path)
        except ValueError:
            return False

        ignored = False
        for pattern, is_negation in self.patterns:
            # Normalize pattern
            if pattern.endswith('/'):
                # Directory pattern
                if path.is_dir() and fnmatch.fnmatch(path_str + '/', pattern):
                    ignored = not is_negation
                elif fnmatch.fnmatch(path_str, pattern.rstrip('/')):
                    ignored = not is_negation
            else:
                if fnmatch.fnmatch(path_str, pattern) or fnmatch.fnmatch(path.name, pattern):
                    ignored = not is_negation

        return ignored


class FileScanner:
    """Scans and indexes project files efficiently."""

    # Always ignore these patterns
    DEFAULT_IGNORE = {
        '__pycache__', '.git', '.svn', '.hg', 'node_modules',
        '.venv', 'venv', 'env', '.env', '.tox', '.mypy_cache',
        '.pytest_cache', '.coverage', 'htmlcov', 'dist', 'build',
        '*.egg-info', '.eggs', '.idea', '.vscode', '*.pyc', '*.pyo',
        '.DS_Store', 'Thumbs.db', '*.swp', '*.swo', '*~',
        '.archive', '.backup', '.bak', 'backup', 'backups',
    }

    def __init__(
        self,
        root_path: Path,
        max_depth: int = 10,
        max_files: int = 5000,
        respect_gitignore: bool = True
    ):
        self.root_path = root_path.resolve()
        self.max_depth = max_depth
        self.max_files = max_files
        self.gitignore = GitIgnoreParser(root_path) if respect_gitignore else None
        self._file_cache: List[FileEntry] = []
        self._cache_valid = False

    def _should_ignore(self, path: Path) -> bool:
        """Check if path should be ignored."""
        name = path.name

        # Check default ignore patterns
        for pattern in self.DEFAULT_IGNORE:
            if fnmatch.fnmatch(name, pattern):
                return True

        # Check .gitignore
        if self.gitignore and self.gitignore.is_ignored(path):
            return True

        return False

    def _get_file_type(self, path: Path) -> FileType:
        """Determine file type from path."""
        name = path.name

        # Check special files first
        if name in SPECIAL_FILES:
            return SPECIAL_FILES[name]

        # Check extension
        suffix = path.suffix.lower()
        if suffix in EXTENSION_MAP:
            return EXTENSION_MAP[suffix]

        return FileType.UNKNOWN

    def scan(self, force: bool = False) -> List[FileEntry]:
        """Scan directory tree and return file entries."""
        if self._cache_valid and not force:
            return self._file_cache

        self._file_cache = []
        file_count = 0

        def _scan_dir(dir_path: Path, depth: int = 0):
            nonlocal file_count

            if depth > self.max_depth or file_count >= self.max_files:
                return

            try:
                entries = sorted(dir_path.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
            except PermissionError:
                return
            except OSError as e:
                logger.debug(f"Cannot scan {dir_path}: {e}")
                return

            for entry in entries:
                if file_count >= self.max_files:
                    break

                if self._should_ignore(entry):
                    continue

                if entry.is_dir():
                    _scan_dir(entry, depth + 1)
                elif entry.is_file():
                    try:
                        rel_path = entry.relative_to(self.root_path)
                        file_entry = FileEntry(
                            path=entry,
                            relative_path=str(rel_path),
                            name=entry.name,
                            file_type=self._get_file_type(entry)
                        )
                        self._file_cache.append(file_entry)
                        file_count += 1
                    except ValueError:
                        continue

        _scan_dir(self.root_path)
        self._cache_valid = True

        logger.debug(f"Scanned {file_count} files in {self.root_path}")
        return self._file_cache

    def invalidate_cache(self):
        """Invalidate the file cache."""
        self._cache_valid = False
        self._file_cache = []


class FuzzyFileMatcher:
    """Fuzzy matching for file names and paths."""

    @staticmethod
    def score(query: str, target: str, is_path: bool = False) -> float:
        """
        Calculate fuzzy match score.

        Scoring factors:
        - Exact match: 100
        - Prefix match: 90 * ratio
        - Substring match: 70 * ratio
        - Fuzzy character match: 50 * ratio
        - Path component bonus: +10 if matches directory name
        """
        if not query:
            return 0.0

        query_lower = query.lower()
        target_lower = target.lower()

        # Exact match
        if query_lower == target_lower:
            return 100.0

        # For paths, also check filename
        if is_path:
            filename = Path(target).name.lower()
            if query_lower == filename:
                return 95.0

        # Prefix match
        if target_lower.startswith(query_lower):
            return 90.0 * (len(query) / len(target))

        # For paths, check if prefix matches filename
        if is_path:
            filename = Path(target).name.lower()
            if filename.startswith(query_lower):
                return 85.0 * (len(query) / len(filename))

        # Substring match
        if query_lower in target_lower:
            # Bonus for word boundary match
            idx = target_lower.index(query_lower)
            boundary_bonus = 5.0 if idx == 0 or target_lower[idx-1] in '/_.-' else 0.0
            return 70.0 * (len(query) / len(target)) + boundary_bonus

        # Path component match (for file paths)
        if is_path and '/' in target:
            components = target_lower.split('/')
            for i, comp in enumerate(components):
                if query_lower in comp:
                    # Higher score for filename (last component)
                    weight = 1.2 if i == len(components) - 1 else 1.0
                    return 60.0 * (len(query) / len(comp)) * weight

        # Fuzzy character match
        score = 0.0
        query_idx = 0
        consecutive_bonus = 0.0
        last_match_idx = -2

        for i, char in enumerate(target_lower):
            if query_idx < len(query_lower) and char == query_lower[query_idx]:
                score += 1.0
                # Bonus for consecutive matches
                if i == last_match_idx + 1:
                    consecutive_bonus += 0.5
                last_match_idx = i
                query_idx += 1

        if query_idx == len(query_lower):
            # All characters matched
            base_score = 50.0 * (score / len(target))
            return base_score + consecutive_bonus

        return 0.0

    @staticmethod
    def matches(query: str, target: str, threshold: float = 30.0) -> bool:
        """Check if query fuzzy-matches target above threshold."""
        return FuzzyFileMatcher.score(query, target) >= threshold


class FilePickerCompleter(Completer):
    """
    Completer for @ file mentions.

    Triggers on @ character and provides fuzzy file search.
    Recent files are prioritized and marked with ★.
    """

    def __init__(
        self,
        root_path: Optional[Path] = None,
        recent_files: Optional[List[str]] = None,
        max_results: int = 15
    ):
        self.root_path = (root_path or Path.cwd()).resolve()
        self.recent_files: Set[str] = set(recent_files or [])
        self.max_results = max_results
        self.scanner = FileScanner(self.root_path)
        self._last_query = ""
        self._last_results: List[FileEntry] = []

    def update_recent_files(self, files: List[str]):
        """Update list of recent files."""
        self.recent_files = set(files)

    def add_recent_file(self, file_path: str):
        """Add a file to recent files."""
        self.recent_files.add(file_path)

    def refresh_files(self):
        """Refresh file index."""
        self.scanner.invalidate_cache()
        self.scanner.scan(force=True)

    def _find_at_position(self, text: str) -> Optional[int]:
        """Find the position of @ that triggers completion."""
        # Find last @ that's either at start or after whitespace
        for i in range(len(text) - 1, -1, -1):
            if text[i] == '@':
                # Check if it's a valid trigger position
                if i == 0 or text[i-1].isspace():
                    return i
        return None

    def _search_files(self, query: str) -> List[FileEntry]:
        """Search files matching query."""
        files = self.scanner.scan()

        # Mark recent files
        for f in files:
            f.is_recent = f.relative_path in self.recent_files or str(f.path) in self.recent_files

        if not query:
            # No query - show recent files first, then alphabetically
            recent = [f for f in files if f.is_recent]
            recent.sort(key=lambda f: f.name.lower())

            others = [f for f in files if not f.is_recent]
            others.sort(key=lambda f: f.name.lower())

            return (recent + others)[:self.max_results]

        # Score all files
        scored: List[Tuple[float, FileEntry]] = []
        for f in files:
            # Try matching against relative path and filename
            path_score = FuzzyFileMatcher.score(query, f.relative_path, is_path=True)
            name_score = FuzzyFileMatcher.score(query, f.name, is_path=False)

            best_score = max(path_score, name_score)

            if best_score > 0:
                # Boost recent files
                if f.is_recent:
                    best_score *= 1.3
                f.score = best_score
                scored.append((best_score, f))

        # Sort by score descending
        scored.sort(key=lambda x: x[0], reverse=True)

        return [f for _, f in scored[:self.max_results]]

    def get_completions(self, document: Document, complete_event) -> Iterator[Completion]:
        """Get file completions for @ mentions."""
        text = document.text_before_cursor

        # Find @ trigger position
        at_pos = self._find_at_position(text)
        if at_pos is None:
            return

        # Extract query after @
        query = text[at_pos + 1:]

        # Search files
        results = self._search_files(query)

        # Calculate replacement position (from @ onwards)
        start_position = -(len(query) + 1)  # +1 for @

        for file_entry in results:
            # Use relative path as completion text
            completion_text = f"@{file_entry.relative_path}"

            yield Completion(
                text=completion_text,
                start_position=start_position,
                display=file_entry.get_display(),
                display_meta=file_entry.get_description(),
                style='class:file-completion',
                selected_style='class:file-completion-selected'
            )


class UnifiedCompleter(Completer):
    """
    Unified completer combining:
    - Slash commands (/)
    - File picker (@)
    - Tool completions

    This replaces CombinedCompleter with @ support.
    """

    def __init__(
        self,
        slash_completer: Optional[Completer] = None,
        file_picker: Optional[FilePickerCompleter] = None,
        tool_completer: Optional[Completer] = None
    ):
        self.slash_completer = slash_completer
        self.file_picker = file_picker or FilePickerCompleter()
        self.tool_completer = tool_completer

    def get_completions(self, document: Document, complete_event) -> Iterator[Completion]:
        """Route to appropriate completer based on input."""
        text = document.text_before_cursor

        # Check for slash commands first (highest priority)
        if text.startswith('/'):
            if self.slash_completer:
                yield from self.slash_completer.get_completions(document, complete_event)
            return

        # Check for @ file picker
        # Find @ that's either at start or after whitespace
        has_at_trigger = False
        for i in range(len(text) - 1, -1, -1):
            if text[i] == '@' and (i == 0 or text[i-1].isspace()):
                has_at_trigger = True
                break

        if has_at_trigger:
            yield from self.file_picker.get_completions(document, complete_event)
            return

        # Fall back to tool completer
        if self.tool_completer:
            yield from self.tool_completer.get_completions(document, complete_event)


# Factory function for easy creation
def create_file_picker(
    root_path: Optional[Path] = None,
    recent_files: Optional[List[str]] = None
) -> FilePickerCompleter:
    """Create a configured file picker completer."""
    return FilePickerCompleter(
        root_path=root_path,
        recent_files=recent_files
    )


def create_unified_completer(
    root_path: Optional[Path] = None,
    slash_completer: Optional[Completer] = None,
    tool_completer: Optional[Completer] = None,
    recent_files: Optional[List[str]] = None
) -> UnifiedCompleter:
    """Create a unified completer with all features."""
    from .slash_completer import SlashCommandCompleter

    return UnifiedCompleter(
        slash_completer=slash_completer or SlashCommandCompleter(),
        file_picker=FilePickerCompleter(root_path=root_path, recent_files=recent_files),
        tool_completer=tool_completer
    )


__all__ = [
    'FilePickerCompleter',
    'UnifiedCompleter',
    'FileScanner',
    'FuzzyFileMatcher',
    'FileEntry',
    'FileType',
    'create_file_picker',
    'create_unified_completer',
]
