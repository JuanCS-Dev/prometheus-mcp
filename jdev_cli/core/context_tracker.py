"""
ContextTracker - Conversation Context Awareness
Pipeline de Diamante - Camada 1: INPUT FORTRESS

Addresses: ISSUE-025, ISSUE-026, ISSUE-027 (Context awareness)

Implements intelligent context tracking:
- File operation history
- "The other one" resolution
- Implicit file detection
- Workspace awareness
- Reference resolution

Design Philosophy:
- Users speak naturally, system understands
- Recent context is most relevant
- Ambiguity triggers clarification
- Fast lookups for common patterns
"""

from __future__ import annotations

import os
import re
import time
from typing import Any, Dict, List, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum
from collections import deque
import logging

logger = logging.getLogger(__name__)


class ContextType(Enum):
    """Types of context items."""
    FILE = "file"
    DIRECTORY = "directory"
    COMMAND = "command"
    ERROR = "error"
    VARIABLE = "variable"
    FUNCTION = "function"
    CLASS = "class"
    GIT_BRANCH = "git_branch"
    URL = "url"


class ReferenceType(Enum):
    """Types of natural language references."""
    EXPLICIT = "explicit"       # "file.py"
    DEMONSTRATIVE = "demonstrative"  # "this file", "that function"
    ANAPHORIC = "anaphoric"     # "it", "the other one"
    IMPLICIT = "implicit"       # "fix the bug" (which file?)


@dataclass
class ContextItem:
    """An item in the context history."""
    type: ContextType
    value: str
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)
    access_count: int = 0

    def touch(self) -> None:
        """Mark item as recently accessed."""
        self.access_count += 1
        self.timestamp = time.time()


@dataclass
class ResolvedReference:
    """A resolved reference with confidence."""
    value: str
    type: ContextType
    confidence: float  # 0.0 to 1.0
    reason: str
    alternatives: List[str] = field(default_factory=list)
    context_hint: Optional[str] = None
    related_to_previous: bool = False

    @property
    def resolved_path(self) -> Optional[str]:
        """Get resolved path if type is FILE or DIRECTORY."""
        if self.type in (ContextType.FILE, ContextType.DIRECTORY):
            return self.value
        return None


class ContextTracker:
    """
    Track conversation context for natural language understanding.

    Features:
    - Recent file history with recency weighting
    - Demonstrative reference resolution ("this", "that")
    - Anaphoric reference resolution ("it", "the other")
    - Implicit context detection
    - Workspace-aware file matching

    Usage:
        tracker = ContextTracker()

        # Record context
        tracker.record_file_access("src/main.py")
        tracker.record_file_access("src/utils.py")

        # Resolve references
        result = tracker.resolve("edit the first file")
        print(result.value)  # "src/main.py"

        result = tracker.resolve("the other one")
        print(result.value)  # "src/utils.py"
    """

    MAX_HISTORY = 50
    MAX_RECENT = 10
    DECAY_FACTOR = 0.9

    # Natural language patterns for reference detection
    DEMONSTRATIVE_PATTERNS = [
        (r'\b(this|that)\s+(file|folder|directory|function|class|module)\b', 0),
        (r'\b(the|this)\s+one\b', 0),
        (r'\b(current|active)\s+(file|folder|directory)\b', 0),
    ]

    ANAPHORIC_PATTERNS = [
        (r'\bthe\s+other\s+(one|file|folder)\b', 1),  # Second most recent
        (r'\bthe\s+(first|1st|original)\s+(one|file)\b', -1),  # First/oldest
        (r'\bthe\s+(second|2nd)\s+(one|file)\b', 1),
        (r'\bthe\s+(last|previous)\s+(one|file)\b', 0),  # Most recent
        (r'\bit\b', 0),  # Most recent of matching type
    ]

    IMPLICIT_PATTERNS = [
        (r'\b(fix|edit|update|change|modify)\s+(the\s+)?(bug|error|issue)\b', ContextType.FILE),
        (r'\b(run|execute)\s+(the\s+)?(test|tests)\b', ContextType.FILE),
        (r'\b(commit|push|pull)\b', ContextType.GIT_BRANCH),
    ]

    def __init__(
        self,
        working_directory: Optional[str] = None,
        max_history: int = MAX_HISTORY,
    ):
        """
        Initialize ContextTracker.

        Args:
            working_directory: Base working directory
            max_history: Maximum items to keep in history
        """
        self.working_directory = Path(working_directory or os.getcwd())
        self.max_history = max_history

        # Context storage by type
        self._history: Dict[ContextType, deque] = {
            ct: deque(maxlen=max_history) for ct in ContextType
        }

        # Recent items (across all types)
        self._recent: deque = deque(maxlen=self.MAX_RECENT)

        # Named references (explicit assignments)
        self._named: Dict[str, ContextItem] = {}

    def record(
        self,
        type: ContextType,
        value: str,
        metadata: Optional[Dict[str, Any]] = None,
        name: Optional[str] = None,
    ) -> ContextItem:
        """
        Record a context item.

        Args:
            type: Type of context item
            value: Value (file path, command, etc.)
            metadata: Additional metadata
            name: Optional name for later reference

        Returns:
            Created ContextItem
        """
        item = ContextItem(
            type=type,
            value=value,
            metadata=metadata or {},
        )

        # Add to type-specific history
        self._history[type].append(item)

        # Add to recent items
        self._recent.append(item)

        # Store named reference
        if name:
            self._named[name.lower()] = item

        logger.debug(f"Recorded context: {type.value}={value}")
        return item

    def record_file_access(
        self,
        path: str,
        operation: str = "access",
        **metadata
    ) -> ContextItem:
        """Record file access."""
        return self.record(
            ContextType.FILE,
            str(path),
            metadata={"operation": operation, **metadata}
        )

    def record_directory_access(
        self,
        path: str,
        **metadata
    ) -> ContextItem:
        """Record directory access."""
        return self.record(
            ContextType.DIRECTORY,
            str(path),
            metadata=metadata
        )

    def record_command(
        self,
        command: str,
        success: bool = True,
        **metadata
    ) -> ContextItem:
        """Record command execution."""
        return self.record(
            ContextType.COMMAND,
            command,
            metadata={"success": success, **metadata}
        )

    def record_error(
        self,
        error: str,
        file_path: Optional[str] = None,
        **metadata
    ) -> ContextItem:
        """Record an error."""
        meta = {"file_path": file_path, **metadata} if file_path else metadata
        return self.record(ContextType.ERROR, error, metadata=meta)

    def get_recent(
        self,
        type: Optional[ContextType] = None,
        limit: int = 5,
    ) -> List[ContextItem]:
        """
        Get recent context items.

        Args:
            type: Filter by type (None for all)
            limit: Maximum items to return

        Returns:
            List of recent items (newest first)
        """
        if type:
            items = list(self._history[type])
        else:
            items = list(self._recent)

        # Sort by timestamp (newest first)
        items.sort(key=lambda x: x.timestamp, reverse=True)

        return items[:limit]

    def get_most_recent(
        self,
        type: ContextType,
        offset: int = 0,
    ) -> Optional[ContextItem]:
        """
        Get most recent item of a type.

        Args:
            type: Context type
            offset: 0 = most recent, 1 = second most recent, etc.

        Returns:
            ContextItem if found
        """
        items = self.get_recent(type, limit=offset + 1)
        if len(items) > offset:
            return items[offset]
        return None

    def resolve(
        self,
        text: str,
        expected_type: Optional[ContextType] = None,
    ) -> Optional[ResolvedReference]:
        """
        Resolve natural language reference to context item.

        Args:
            text: User input text
            expected_type: Expected type of reference

        Returns:
            ResolvedReference if resolved
        """
        text_lower = text.lower()

        # Try named reference first
        if text_lower in self._named:
            item = self._named[text_lower]
            return ResolvedReference(
                value=item.value,
                type=item.type,
                confidence=1.0,
                reason="Named reference"
            )

        # Try demonstrative patterns ("this file", "that folder")
        for pattern, offset in self.DEMONSTRATIVE_PATTERNS:
            match = re.search(pattern, text_lower)
            if match:
                return self._resolve_demonstrative(match, offset, expected_type)

        # Try anaphoric patterns ("the other one", "it")
        for pattern, offset in self.ANAPHORIC_PATTERNS:
            match = re.search(pattern, text_lower)
            if match:
                return self._resolve_anaphoric(match, offset, expected_type)

        # Try implicit patterns ("fix the bug")
        for pattern, ctx_type in self.IMPLICIT_PATTERNS:
            if re.search(pattern, text_lower):
                return self._resolve_implicit(ctx_type, text)

        # Try file path detection
        file_ref = self._detect_file_reference(text)
        if file_ref:
            return file_ref

        return None

    def _resolve_demonstrative(
        self,
        match: re.Match,
        offset: int,
        expected_type: Optional[ContextType],
    ) -> Optional[ResolvedReference]:
        """Resolve demonstrative reference."""
        # Determine type from match
        match_text = match.group(0)
        ctx_type = expected_type

        if "file" in match_text:
            ctx_type = ContextType.FILE
        elif "folder" in match_text or "directory" in match_text:
            ctx_type = ContextType.DIRECTORY
        elif "function" in match_text:
            ctx_type = ContextType.FUNCTION
        elif "class" in match_text:
            ctx_type = ContextType.CLASS

        if ctx_type:
            item = self.get_most_recent(ctx_type, offset)
            if item:
                return ResolvedReference(
                    value=item.value,
                    type=item.type,
                    confidence=0.9,
                    reason=f"Demonstrative reference: '{match_text}'"
                )

        # Fallback to any recent item
        if self._recent:
            item = self._recent[-1]
            return ResolvedReference(
                value=item.value,
                type=item.type,
                confidence=0.7,
                reason="Most recent item"
            )

        return None

    def _resolve_anaphoric(
        self,
        match: re.Match,
        offset: int,
        expected_type: Optional[ContextType],
    ) -> Optional[ResolvedReference]:
        """Resolve anaphoric reference."""
        ctx_type = expected_type or ContextType.FILE

        # Handle "the other one" specially
        match_text = match.group(0)
        if "other" in match_text:
            # Get second most recent
            items = self.get_recent(ctx_type, limit=2)
            if len(items) >= 2:
                return ResolvedReference(
                    value=items[1].value,
                    type=items[1].type,
                    confidence=0.85,
                    reason="The other one (second most recent)",
                    alternatives=[items[0].value]
                )

        # Handle "first", "original"
        if "first" in match_text or "original" in match_text:
            items = self.get_recent(ctx_type, limit=10)
            if items:
                # Get oldest in recent history
                oldest = min(items, key=lambda x: x.timestamp)
                return ResolvedReference(
                    value=oldest.value,
                    type=oldest.type,
                    confidence=0.8,
                    reason="First/original reference"
                )

        # Default: most recent
        item = self.get_most_recent(ctx_type, offset)
        if item:
            return ResolvedReference(
                value=item.value,
                type=item.type,
                confidence=0.85,
                reason=f"Anaphoric reference: '{match_text}'"
            )

        return None

    def _resolve_implicit(
        self,
        ctx_type: ContextType,
        text: str,
    ) -> Optional[ResolvedReference]:
        """Resolve implicit reference."""
        # For errors, look for recent error with file
        if "bug" in text.lower() or "error" in text.lower():
            errors = self.get_recent(ContextType.ERROR, limit=5)
            for error in errors:
                file_path = error.metadata.get("file_path")
                if file_path:
                    return ResolvedReference(
                        value=file_path,
                        type=ContextType.FILE,
                        confidence=0.75,
                        reason="Implicit reference from recent error"
                    )

        # Default to most recent of expected type
        item = self.get_most_recent(ctx_type)
        if item:
            return ResolvedReference(
                value=item.value,
                type=item.type,
                confidence=0.6,
                reason="Implicit reference to recent context"
            )

        return None

    def _detect_file_reference(self, text: str) -> Optional[ResolvedReference]:
        """Detect file path references in text."""
        # Common file patterns
        patterns = [
            r'["\']([^"\']+\.[a-zA-Z0-9]+)["\']',  # Quoted paths
            r'\b(\S+\.[a-zA-Z0-9]{1,5})\b',  # File with extension
            r'\b((?:[\w-]+/)+[\w.-]+)\b',  # Path with slashes
        ]

        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                path = match.group(1)

                # Check if it's a real file
                full_path = self.working_directory / path
                if full_path.exists():
                    return ResolvedReference(
                        value=str(full_path),
                        type=ContextType.FILE,
                        confidence=0.95,
                        reason="Explicit file path found"
                    )

                # Check in recent files
                for item in self.get_recent(ContextType.FILE, limit=20):
                    if path in item.value or Path(item.value).name == path:
                        return ResolvedReference(
                            value=item.value,
                            type=ContextType.FILE,
                            confidence=0.8,
                            reason="Matched recent file"
                        )

        return None

    def suggest_clarification(
        self,
        text: str,
        expected_type: Optional[ContextType] = None,
    ) -> List[str]:
        """
        Suggest clarification options when reference is ambiguous.

        Args:
            text: User input
            expected_type: Expected context type

        Returns:
            List of clarification suggestions
        """
        ctx_type = expected_type or ContextType.FILE
        recent = self.get_recent(ctx_type, limit=5)

        if not recent:
            return ["No recent files found. Please specify a file path."]

        suggestions = ["Did you mean one of these?"]
        for i, item in enumerate(recent, 1):
            name = Path(item.value).name if ctx_type == ContextType.FILE else item.value
            suggestions.append(f"  {i}. {name}")

        return suggestions

    def clear(self, type: Optional[ContextType] = None) -> None:
        """Clear context history."""
        if type:
            self._history[type].clear()
        else:
            for history in self._history.values():
                history.clear()
            self._recent.clear()
            self._named.clear()

    # Vibe coder support methods
    _intents: List[str] = []
    _interactions: List[Tuple[str, str]] = []

    def record_intent(self, intent: str) -> None:
        """Record user's intent for tracking changes of mind."""
        if not hasattr(self, '_intents'):
            self._intents = []
        self._intents.append(intent)

    def get_current_intent(self) -> str:
        """Get the current (most recent) intent."""
        if hasattr(self, '_intents') and self._intents:
            return self._intents[-1]
        return ""

    def record_interaction(self, question: str, answer: str) -> None:
        """Record a Q&A interaction for context building."""
        if not hasattr(self, '_interactions'):
            self._interactions = []
        self._interactions.append((question, answer))

    def get_previous_topic(self) -> Optional[str]:
        """Get the topic from the previous interaction."""
        if hasattr(self, '_interactions') and self._interactions:
            return self._interactions[-1][1]
        return None


# Global instance
_default_tracker: Optional[ContextTracker] = None


def get_context_tracker() -> ContextTracker:
    """Get the default context tracker instance."""
    global _default_tracker
    if _default_tracker is None:
        _default_tracker = ContextTracker()
    return _default_tracker


# Convenience functions

def record_file(path: str, operation: str = "access") -> ContextItem:
    """Record file access."""
    return get_context_tracker().record_file_access(path, operation)


def resolve_reference(text: str) -> Optional[ResolvedReference]:
    """Resolve a natural language reference."""
    return get_context_tracker().resolve(text)


# Add resolve_reference as method to ContextTracker for test compatibility
ContextTracker.resolve_reference = lambda self, text, expected_type=None: self.resolve(text, expected_type)


def get_recent_files(limit: int = 5) -> List[str]:
    """Get recent file paths."""
    items = get_context_tracker().get_recent(ContextType.FILE, limit)
    return [item.value for item in items]


# Export all public symbols
__all__ = [
    'ContextType',
    'ReferenceType',
    'ContextItem',
    'ResolvedReference',
    'ContextTracker',
    'get_context_tracker',
    'record_file',
    'resolve_reference',
    'get_recent_files',
]
