"""Memory System - JUAN.md/MEMORY.md persistent project memory.

Juan-Dev-Code memory system for project context.

The memory system provides:
1. Project-level memory (JUAN.md at project root)
2. User-level memory (~/.config/jdev-cli/MEMORY.md)
3. Session memory (temporary, in-memory)

Memory is automatically loaded at startup and updated during sessions.

Supports legacy CLAUDE.md for backwards compatibility.

Author: Juan CS
Date: 2025-11-26
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# =============================================================================
# MEMORY DATA STRUCTURES
# =============================================================================

@dataclass
class MemoryEntry:
    """A single memory entry with metadata."""

    content: str
    source: str  # "project", "user", "session"
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    tags: List[str] = field(default_factory=list)
    priority: int = 0  # Higher = more important

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "content": self.content,
            "source": self.source,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "tags": self.tags,
            "priority": self.priority,
        }


@dataclass
class ProjectMemory:
    """Memory loaded from CLAUDE.md at project root."""

    path: Path
    raw_content: str = ""
    sections: Dict[str, str] = field(default_factory=dict)
    instructions: List[str] = field(default_factory=list)
    preferences: Dict[str, str] = field(default_factory=dict)
    loaded_at: Optional[datetime] = None

    def is_loaded(self) -> bool:
        """Check if memory is loaded."""
        return self.loaded_at is not None


@dataclass
class UserMemory:
    """Memory loaded from user's MEMORY.md file."""

    path: Path
    raw_content: str = ""
    global_preferences: Dict[str, str] = field(default_factory=dict)
    project_overrides: Dict[str, Dict[str, str]] = field(default_factory=dict)
    loaded_at: Optional[datetime] = None


@dataclass
class SessionMemory:
    """In-memory session context (not persisted)."""

    entries: List[MemoryEntry] = field(default_factory=list)
    context_files: List[str] = field(default_factory=list)
    modified_files: List[str] = field(default_factory=list)
    key_decisions: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    session_start: datetime = field(default_factory=datetime.now)


# =============================================================================
# MEMORY MANAGER
# =============================================================================

class MemoryManager:
    """Manages persistent and session memory.

    Claude Code parity:
    - Reads CLAUDE.md from project root
    - Reads MEMORY.md from user config directory
    - Provides unified memory context for LLM

    Usage:
        manager = MemoryManager()
        manager.load()

        # Get context for LLM
        context = manager.get_context()

        # Add session memory
        manager.add_session_entry("User prefers TypeScript over JavaScript")
    """

    # Standard file names (Juan-Dev-Code convention)
    PROJECT_MEMORY_FILE = "JUAN.md"
    USER_MEMORY_FILE = "MEMORY.md"

    # Alternative names supported (includes CLAUDE.md for backwards compatibility)
    ALT_PROJECT_NAMES = [
        "JUAN.md",           # Primary (Juan-Dev-Code)
        ".juan/MEMORY.md",   # Hidden directory
        ".jdev/MEMORY.md",   # Alternative
        "CLAUDE.md",         # Backwards compatibility
        ".claude/MEMORY.md", # Claude Code legacy
        "MEMORY.md",         # Generic fallback
    ]

    def __init__(
        self,
        project_root: Optional[Path] = None,
        user_config_dir: Optional[Path] = None,
    ):
        """Initialize memory manager.

        Args:
            project_root: Project root directory (default: cwd)
            user_config_dir: User config directory (default: ~/.config/jdev-cli)
        """
        self._project_root = project_root or Path.cwd()
        self._user_config_dir = user_config_dir or Path.home() / ".config" / "jdev-cli"

        # Initialize memory stores
        self._project_memory = ProjectMemory(
            path=self._project_root / self.PROJECT_MEMORY_FILE
        )
        self._user_memory = UserMemory(
            path=self._user_config_dir / self.USER_MEMORY_FILE
        )
        self._session_memory = SessionMemory()

        self._loaded = False

    # =========================================================================
    # LOADING
    # =========================================================================

    def load(self) -> bool:
        """Load all memory sources.

        Returns:
            True if any memory was loaded successfully
        """
        project_loaded = self._load_project_memory()
        user_loaded = self._load_user_memory()

        self._loaded = project_loaded or user_loaded

        if self._loaded:
            logger.info(
                f"Memory loaded: project={project_loaded}, user={user_loaded}"
            )
        else:
            logger.debug("No memory files found")

        return self._loaded

    def _load_project_memory(self) -> bool:
        """Load project-level memory from JUAN.md (or CLAUDE.md for compatibility)."""
        # Try standard and alternative paths (JUAN.md first)
        for filename in self.ALT_PROJECT_NAMES:
            memory_path = self._project_root / filename

            if memory_path.exists() and memory_path.is_file():
                try:
                    content = memory_path.read_text(encoding="utf-8")
                    self._project_memory = ProjectMemory(
                        path=memory_path,
                        raw_content=content,
                        sections=self._parse_sections(content),
                        instructions=self._extract_instructions(content),
                        preferences=self._extract_preferences(content),
                        loaded_at=datetime.now(),
                    )
                    logger.info(f"Loaded project memory from {memory_path}")
                    return True
                except Exception as e:
                    logger.error(f"Failed to load project memory: {e}")

        return False

    def _load_user_memory(self) -> bool:
        """Load user-level memory from MEMORY.md."""
        memory_path = self._user_config_dir / self.USER_MEMORY_FILE

        if not memory_path.exists():
            return False

        try:
            content = memory_path.read_text(encoding="utf-8")
            self._user_memory = UserMemory(
                path=memory_path,
                raw_content=content,
                global_preferences=self._extract_preferences(content),
                loaded_at=datetime.now(),
            )
            logger.info(f"Loaded user memory from {memory_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to load user memory: {e}")
            return False

    # =========================================================================
    # PARSING
    # =========================================================================

    def _parse_sections(self, content: str) -> Dict[str, str]:
        """Parse markdown sections from content.

        Sections are identified by ## headers.
        """
        sections = {}
        current_section = "default"
        current_content: List[str] = []

        for line in content.split("\n"):
            if line.startswith("## "):
                # Save previous section
                if current_content:
                    sections[current_section] = "\n".join(current_content).strip()
                # Start new section
                current_section = line[3:].strip().lower()
                current_content = []
            else:
                current_content.append(line)

        # Save last section
        if current_content:
            sections[current_section] = "\n".join(current_content).strip()

        return sections

    def _extract_instructions(self, content: str) -> List[str]:
        """Extract instruction lines from content.

        Instructions are lines that:
        - Start with "- " (list items)
        - Are in sections like "instructions", "rules", "guidelines"
        """
        instructions = []
        sections = self._parse_sections(content)

        instruction_sections = ["instructions", "rules", "guidelines", "preferences", "default"]

        for section_name in instruction_sections:
            if section_name in sections:
                section_content = sections[section_name]
                for line in section_content.split("\n"):
                    line = line.strip()
                    if line.startswith("- "):
                        instructions.append(line[2:])
                    elif line.startswith("* "):
                        instructions.append(line[2:])

        return instructions

    def _extract_preferences(self, content: str) -> Dict[str, str]:
        """Extract key-value preferences from content.

        Preferences are in format:
        - key: value
        - **key**: value
        """
        import re

        preferences = {}

        # Match patterns like "- key: value" or "- **key**: value"
        pattern = re.compile(r'^[-*]\s+\*?\*?([^:*]+)\*?\*?:\s*(.+)$', re.MULTILINE)

        for match in pattern.finditer(content):
            key = match.group(1).strip().lower().replace(" ", "_")
            value = match.group(2).strip()
            preferences[key] = value

        return preferences

    # =========================================================================
    # CONTEXT BUILDING
    # =========================================================================

    def get_context(self, max_tokens: int = 2000) -> str:
        """Get unified memory context for LLM.

        Args:
            max_tokens: Approximate max tokens for context

        Returns:
            Formatted context string
        """
        parts = []

        # Project memory (highest priority)
        if self._project_memory.is_loaded():
            parts.append("## Project Memory (CLAUDE.md)")

            # Add instructions first
            if self._project_memory.instructions:
                parts.append("\n**Instructions:**")
                for instruction in self._project_memory.instructions[:10]:  # Limit
                    parts.append(f"- {instruction}")

            # Add preferences
            if self._project_memory.preferences:
                parts.append("\n**Preferences:**")
                for key, value in list(self._project_memory.preferences.items())[:5]:
                    parts.append(f"- {key}: {value}")

            # Add raw content if there's room
            remaining = max_tokens - len("\n".join(parts).split())
            if remaining > 200:
                raw = self._project_memory.raw_content[:remaining * 4]  # ~4 chars per token
                parts.append(f"\n**Full Context:**\n{raw}")

        # User memory (lower priority)
        if self._user_memory.loaded_at:
            parts.append("\n## User Preferences")
            for key, value in list(self._user_memory.global_preferences.items())[:5]:
                parts.append(f"- {key}: {value}")

        # Session memory (current session context)
        if self._session_memory.key_decisions:
            parts.append("\n## Session Decisions")
            for decision in self._session_memory.key_decisions[-5:]:
                parts.append(f"- {decision}")

        if self._session_memory.warnings:
            parts.append("\n## Session Warnings")
            for warning in self._session_memory.warnings[-3:]:
                parts.append(f"- {warning}")

        return "\n".join(parts)

    def get_instructions(self) -> List[str]:
        """Get all instructions from memory."""
        instructions = []

        if self._project_memory.is_loaded():
            instructions.extend(self._project_memory.instructions)

        return instructions

    def get_preference(self, key: str, default: str = "") -> str:
        """Get a specific preference.

        Args:
            key: Preference key
            default: Default value if not found

        Returns:
            Preference value
        """
        # Project preferences override user preferences
        if self._project_memory.is_loaded():
            if key in self._project_memory.preferences:
                return self._project_memory.preferences[key]

        if self._user_memory.loaded_at:
            if key in self._user_memory.global_preferences:
                return self._user_memory.global_preferences[key]

        return default

    # =========================================================================
    # SESSION MEMORY
    # =========================================================================

    def add_session_entry(self, content: str, tags: Optional[List[str]] = None) -> None:
        """Add entry to session memory.

        Args:
            content: Memory content
            tags: Optional tags for categorization
        """
        entry = MemoryEntry(
            content=content,
            source="session",
            tags=tags or [],
        )
        self._session_memory.entries.append(entry)

    def add_key_decision(self, decision: str) -> None:
        """Record a key decision made during the session."""
        self._session_memory.key_decisions.append(decision)

    def add_warning(self, warning: str) -> None:
        """Record a warning for future reference."""
        self._session_memory.warnings.append(warning)

    def track_context_file(self, path: str) -> None:
        """Track a file that has been read for context."""
        if path not in self._session_memory.context_files:
            self._session_memory.context_files.append(path)

    def track_modified_file(self, path: str) -> None:
        """Track a file that has been modified."""
        if path not in self._session_memory.modified_files:
            self._session_memory.modified_files.append(path)

    # =========================================================================
    # SAVING
    # =========================================================================

    def save_project_memory(self, content: str) -> bool:
        """Save content to project JUAN.md.

        Args:
            content: New content for JUAN.md

        Returns:
            True if saved successfully
        """
        try:
            path = self._project_root / self.PROJECT_MEMORY_FILE
            path.write_text(content, encoding="utf-8")

            # Reload
            self._load_project_memory()
            logger.info(f"Saved project memory to {path}")
            return True
        except Exception as e:
            logger.error(f"Failed to save project memory: {e}")
            return False

    def append_to_project_memory(self, content: str) -> bool:
        """Append content to project JUAN.md.

        Args:
            content: Content to append

        Returns:
            True if saved successfully
        """
        try:
            path = self._project_root / self.PROJECT_MEMORY_FILE

            # Read existing
            existing = ""
            if path.exists():
                existing = path.read_text(encoding="utf-8")

            # Append with timestamp
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
            new_content = f"{existing}\n\n## Added {timestamp}\n\n{content}"

            path.write_text(new_content.strip(), encoding="utf-8")

            # Reload
            self._load_project_memory()
            logger.info(f"Appended to project memory at {path}")
            return True
        except Exception as e:
            logger.error(f"Failed to append to project memory: {e}")
            return False

    # =========================================================================
    # PROPERTIES
    # =========================================================================

    @property
    def is_loaded(self) -> bool:
        """Check if any memory is loaded."""
        return self._loaded

    @property
    def project_memory(self) -> ProjectMemory:
        """Get project memory."""
        return self._project_memory

    @property
    def user_memory(self) -> UserMemory:
        """Get user memory."""
        return self._user_memory

    @property
    def session_memory(self) -> SessionMemory:
        """Get session memory."""
        return self._session_memory

    @property
    def has_project_memory(self) -> bool:
        """Check if project memory exists."""
        return self._project_memory.is_loaded()

    @property
    def has_user_memory(self) -> bool:
        """Check if user memory exists."""
        return self._user_memory.loaded_at is not None


# =============================================================================
# GLOBAL INSTANCE
# =============================================================================

_memory_manager: Optional[MemoryManager] = None


def get_memory_manager(
    project_root: Optional[Path] = None,
    auto_load: bool = True,
) -> MemoryManager:
    """Get or create the memory manager singleton.

    Args:
        project_root: Project root directory
        auto_load: Whether to auto-load memory

    Returns:
        MemoryManager instance
    """
    global _memory_manager

    if _memory_manager is None:
        _memory_manager = MemoryManager(project_root=project_root)
        if auto_load:
            _memory_manager.load()

    return _memory_manager


def reset_memory_manager() -> None:
    """Reset the memory manager (for testing)."""
    global _memory_manager
    _memory_manager = None


# =============================================================================
# MEMORY TOOLS
# =============================================================================

class MemoryReadTool:
    """Tool to read project/user memory.

    Read JUAN.md/MEMORY.md content (supports CLAUDE.md for compatibility).
    """

    name = "memory_read"
    description = "Read project JUAN.md or user MEMORY.md"
    category = "context"

    def __init__(self):
        self.parameters = {
            "source": {
                "type": "string",
                "description": "Memory source: 'project', 'user', or 'all' (default)",
                "required": False
            }
        }

    async def execute(self, source: str = "all") -> Dict[str, Any]:
        """Execute memory read."""
        manager = get_memory_manager()

        result: Dict[str, Any] = {"success": True}

        if source in ("project", "all"):
            if manager.has_project_memory:
                result["project"] = {
                    "path": str(manager.project_memory.path),
                    "content": manager.project_memory.raw_content,
                    "instructions": manager.project_memory.instructions,
                    "preferences": manager.project_memory.preferences,
                }
            else:
                result["project"] = None

        if source in ("user", "all"):
            if manager.has_user_memory:
                result["user"] = {
                    "path": str(manager.user_memory.path),
                    "preferences": manager.user_memory.global_preferences,
                }
            else:
                result["user"] = None

        return result


class MemoryWriteTool:
    """Tool to write to project memory.

    Write to JUAN.md (project memory file).
    """

    name = "memory_write"
    description = "Write to project JUAN.md"
    category = "context"

    def __init__(self):
        self.parameters = {
            "content": {
                "type": "string",
                "description": "Content to write",
                "required": True
            },
            "mode": {
                "type": "string",
                "description": "Write mode: 'replace' or 'append' (default)",
                "required": False
            }
        }

    async def execute(self, content: str, mode: str = "append") -> Dict[str, Any]:
        """Execute memory write."""
        manager = get_memory_manager()

        if mode == "replace":
            success = manager.save_project_memory(content)
        else:
            success = manager.append_to_project_memory(content)

        return {
            "success": success,
            "mode": mode,
            "path": str(manager.project_memory.path),
        }
