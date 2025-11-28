"""Context Auto-Compact - Automatic context management for Claude Code parity.

Claude Code parity: Implements automatic context compaction when approaching
token limits. Preserves important context while removing less relevant information.

Strategies:
1. Summarize old conversation turns
2. Remove verbose tool outputs
3. Prioritize recent and relevant context
4. Preserve code snippets and decisions

Author: Juan CS
Date: 2025-11-26
"""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# =============================================================================
# CONTEXT ENTRY TYPES
# =============================================================================

@dataclass
class ContextEntry:
    """A single context entry with metadata."""

    content: str
    entry_type: str  # "user", "assistant", "tool_result", "system", "code"
    timestamp: datetime = field(default_factory=datetime.now)
    token_count: int = 0
    priority: int = 5  # 1-10, higher = more important
    can_compact: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Calculate token count if not provided."""
        if self.token_count == 0:
            self.token_count = self._estimate_tokens(self.content)

    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count (rough approximation)."""
        # Rough estimate: ~4 chars per token for English
        return len(text) // 4

    @property
    def content_hash(self) -> str:
        """Get content hash for deduplication."""
        return hashlib.md5(self.content.encode()).hexdigest()[:8]


@dataclass
class CompactedContext:
    """Result of context compaction."""

    entries: List[ContextEntry]
    total_tokens: int
    removed_count: int
    summarized_count: int
    original_tokens: int

    @property
    def compression_ratio(self) -> float:
        """Get compression ratio."""
        if self.original_tokens == 0:
            return 1.0
        return self.total_tokens / self.original_tokens


# =============================================================================
# CONTEXT COMPACTOR
# =============================================================================

class ContextCompactor:
    """Automatic context compaction manager.

    Strategies:
    1. Priority-based retention (keep high-priority entries)
    2. Recency bias (keep recent entries)
    3. Summarization (compress old conversations)
    4. Deduplication (remove repeated content)
    5. Tool output truncation (shorten verbose outputs)

    Usage:
        compactor = ContextCompactor(max_tokens=100000)
        compactor.add_entry(content="...", entry_type="user")

        if compactor.should_compact():
            compacted = compactor.compact()
    """

    # Default token limits
    DEFAULT_MAX_TOKENS = 100000  # 100k context window
    COMPACT_THRESHOLD = 0.8  # Compact at 80% capacity
    TARGET_AFTER_COMPACT = 0.5  # Target 50% after compaction

    # Priority levels
    PRIORITY_CRITICAL = 10  # Never remove (system prompts, errors)
    PRIORITY_HIGH = 8  # Keep if possible (recent code, decisions)
    PRIORITY_NORMAL = 5  # Standard entries
    PRIORITY_LOW = 3  # Can be summarized
    PRIORITY_VERBOSE = 1  # Remove first (long tool outputs)

    def __init__(
        self,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        compact_threshold: float = COMPACT_THRESHOLD,
        target_ratio: float = TARGET_AFTER_COMPACT,
    ):
        """Initialize context compactor.

        Args:
            max_tokens: Maximum token limit
            compact_threshold: Ratio at which to trigger compaction
            target_ratio: Target ratio after compaction
        """
        self.max_tokens = max_tokens
        self.compact_threshold = compact_threshold
        self.target_ratio = target_ratio

        self._entries: List[ContextEntry] = []
        self._total_tokens = 0
        self._compaction_count = 0

    # =========================================================================
    # ENTRY MANAGEMENT
    # =========================================================================

    def add_entry(
        self,
        content: str,
        entry_type: str = "assistant",
        priority: Optional[int] = None,
        can_compact: bool = True,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ContextEntry:
        """Add a context entry.

        Args:
            content: Entry content
            entry_type: Type of entry
            priority: Priority level (auto-assigned if None)
            can_compact: Whether entry can be compacted
            metadata: Additional metadata

        Returns:
            The created ContextEntry
        """
        # Auto-assign priority based on type
        if priority is None:
            priority = self._auto_priority(content, entry_type)

        entry = ContextEntry(
            content=content,
            entry_type=entry_type,
            priority=priority,
            can_compact=can_compact,
            metadata=metadata or {},
        )

        self._entries.append(entry)
        self._total_tokens += entry.token_count

        # Check if compaction needed
        if self.should_compact():
            logger.info(f"Auto-compacting context: {self._total_tokens} tokens")
            self.compact()

        return entry

    def _auto_priority(self, content: str, entry_type: str) -> int:
        """Auto-assign priority based on content and type."""
        # System messages are critical
        if entry_type == "system":
            return self.PRIORITY_CRITICAL

        # Errors are high priority
        if entry_type == "error" or "error" in content.lower()[:100]:
            return self.PRIORITY_HIGH

        # Code is high priority
        if entry_type == "code" or "```" in content:
            return self.PRIORITY_HIGH

        # User messages are normal priority
        if entry_type == "user":
            return self.PRIORITY_NORMAL

        # Tool results can be verbose
        if entry_type == "tool_result":
            # Long outputs are lower priority
            if len(content) > 2000:
                return self.PRIORITY_VERBOSE
            return self.PRIORITY_LOW

        return self.PRIORITY_NORMAL

    # =========================================================================
    # COMPACTION
    # =========================================================================

    def should_compact(self) -> bool:
        """Check if compaction is needed."""
        return self._total_tokens >= (self.max_tokens * self.compact_threshold)

    def compact(self, target_tokens: Optional[int] = None) -> CompactedContext:
        """Compact the context to reduce token usage.

        Args:
            target_tokens: Target token count (default: max_tokens * target_ratio)

        Returns:
            CompactedContext with results
        """
        if target_tokens is None:
            target_tokens = int(self.max_tokens * self.target_ratio)

        original_tokens = self._total_tokens
        original_count = len(self._entries)

        # Apply compaction strategies in order
        self._deduplicate()
        self._truncate_verbose()
        self._summarize_old_conversations()
        self._remove_low_priority(target_tokens)

        self._compaction_count += 1

        # Recalculate total
        self._total_tokens = sum(e.token_count for e in self._entries)

        return CompactedContext(
            entries=self._entries.copy(),
            total_tokens=self._total_tokens,
            removed_count=original_count - len(self._entries),
            summarized_count=sum(1 for e in self._entries if e.metadata.get("summarized")),
            original_tokens=original_tokens,
        )

    def _deduplicate(self) -> None:
        """Remove duplicate entries."""
        seen_hashes = set()
        unique_entries = []

        for entry in self._entries:
            content_hash = entry.content_hash
            if content_hash not in seen_hashes:
                seen_hashes.add(content_hash)
                unique_entries.append(entry)

        removed = len(self._entries) - len(unique_entries)
        if removed > 0:
            logger.debug(f"Deduplication removed {removed} entries")

        self._entries = unique_entries

    def _truncate_verbose(self) -> None:
        """Truncate verbose tool outputs."""
        MAX_TOOL_OUTPUT = 1000  # Max chars for tool outputs

        for entry in self._entries:
            if entry.entry_type == "tool_result" and len(entry.content) > MAX_TOOL_OUTPUT:
                # Truncate with summary
                truncated = entry.content[:MAX_TOOL_OUTPUT]
                remaining = len(entry.content) - MAX_TOOL_OUTPUT

                entry.content = f"{truncated}\n... ({remaining} chars truncated)"
                entry.token_count = entry._estimate_tokens(entry.content)
                entry.metadata["truncated"] = True

    def _summarize_old_conversations(self) -> None:
        """Summarize old conversation turns."""
        if len(self._entries) < 10:
            return

        # Find consecutive user/assistant pairs older than recent 5
        old_entries = self._entries[:-5]
        new_entries = self._entries[-5:]

        # Group into conversation turns
        turns = []
        current_turn = []

        for entry in old_entries:
            if entry.entry_type in ("user", "assistant"):
                current_turn.append(entry)

                # End turn after assistant response
                if entry.entry_type == "assistant":
                    if len(current_turn) >= 2:
                        turns.append(current_turn)
                    current_turn = []
            else:
                # Non-conversation entries stay as-is
                if current_turn:
                    turns.append(current_turn)
                    current_turn = []
                turns.append([entry])

        # Summarize turns with multiple entries
        summarized_entries = []
        for turn in turns:
            if len(turn) >= 2 and all(e.can_compact for e in turn):
                summary = self._create_turn_summary(turn)
                summarized_entries.append(summary)
            else:
                summarized_entries.extend(turn)

        self._entries = summarized_entries + new_entries

    def _create_turn_summary(self, turn: List[ContextEntry]) -> ContextEntry:
        """Create a summary entry for a conversation turn."""
        user_content = ""
        assistant_content = ""

        for entry in turn:
            if entry.entry_type == "user":
                user_content = entry.content[:100]
            elif entry.entry_type == "assistant":
                assistant_content = entry.content[:200]

        summary = f"[Turn Summary] User: {user_content}... → Assistant: {assistant_content}..."

        return ContextEntry(
            content=summary,
            entry_type="summary",
            priority=self.PRIORITY_LOW,
            can_compact=True,
            metadata={"summarized": True, "original_entries": len(turn)},
        )

    def _remove_low_priority(self, target_tokens: int) -> None:
        """Remove low-priority entries to reach target."""
        if self._total_tokens <= target_tokens:
            return

        # Sort by priority (keep high priority) and recency (keep recent)
        scored_entries = []
        for i, entry in enumerate(self._entries):
            # Score = priority * 10 + recency_score
            recency_score = i / len(self._entries) * 5  # 0-5 based on position
            score = entry.priority * 10 + recency_score
            scored_entries.append((score, i, entry))

        # Sort by score (lowest first = remove first)
        scored_entries.sort(key=lambda x: x[0])

        # Remove until target reached
        current_tokens = self._total_tokens
        entries_to_keep = set(range(len(self._entries)))

        for score, idx, entry in scored_entries:
            if current_tokens <= target_tokens:
                break

            if entry.can_compact and entry.priority < self.PRIORITY_HIGH:
                entries_to_keep.discard(idx)
                current_tokens -= entry.token_count

        self._entries = [
            entry for i, entry in enumerate(self._entries)
            if i in entries_to_keep
        ]

    # =========================================================================
    # CONTEXT RETRIEVAL
    # =========================================================================

    def get_context(self, max_tokens: Optional[int] = None) -> str:
        """Get current context as string.

        Args:
            max_tokens: Maximum tokens to return

        Returns:
            Formatted context string
        """
        if max_tokens and self._total_tokens > max_tokens:
            self.compact(max_tokens)

        parts = []
        for entry in self._entries:
            if entry.entry_type == "system":
                parts.append(f"[System] {entry.content}")
            elif entry.entry_type == "user":
                parts.append(f"User: {entry.content}")
            elif entry.entry_type == "assistant":
                parts.append(f"Assistant: {entry.content}")
            elif entry.entry_type == "code":
                parts.append(f"```\n{entry.content}\n```")
            elif entry.entry_type == "summary":
                parts.append(entry.content)
            else:
                parts.append(entry.content)

        return "\n\n".join(parts)

    def get_recent_entries(self, count: int = 5) -> List[ContextEntry]:
        """Get recent context entries."""
        return self._entries[-count:]

    def clear(self) -> None:
        """Clear all context."""
        self._entries.clear()
        self._total_tokens = 0

    # =========================================================================
    # PROPERTIES
    # =========================================================================

    @property
    def total_tokens(self) -> int:
        """Get total token count."""
        return self._total_tokens

    @property
    def entry_count(self) -> int:
        """Get entry count."""
        return len(self._entries)

    @property
    def utilization(self) -> float:
        """Get context utilization ratio."""
        return self._total_tokens / self.max_tokens

    @property
    def compaction_count(self) -> int:
        """Get number of times context was compacted."""
        return self._compaction_count

    def get_stats(self) -> Dict[str, Any]:
        """Get context statistics."""
        type_counts = {}
        for entry in self._entries:
            type_counts[entry.entry_type] = type_counts.get(entry.entry_type, 0) + 1

        return {
            "total_tokens": self._total_tokens,
            "max_tokens": self.max_tokens,
            "utilization": f"{self.utilization:.1%}",
            "entry_count": len(self._entries),
            "compaction_count": self._compaction_count,
            "type_distribution": type_counts,
        }


# =============================================================================
# GLOBAL INSTANCE
# =============================================================================

_context_compactor: Optional[ContextCompactor] = None


def get_context_compactor(max_tokens: int = 100000) -> ContextCompactor:
    """Get or create the context compactor singleton."""
    global _context_compactor

    if _context_compactor is None:
        _context_compactor = ContextCompactor(max_tokens=max_tokens)

    return _context_compactor


def reset_context_compactor() -> None:
    """Reset the context compactor (for testing)."""
    global _context_compactor
    _context_compactor = None


# =============================================================================
# CONTEXT AUTO-COMPACT TOOL
# =============================================================================

class ContextCompactTool:
    """Tool to manually trigger context compaction.

    Claude Code parity: Allows explicit context management.
    """

    name = "context_compact"
    description = "Compact conversation context to free up token space"
    category = "context"

    def __init__(self):
        self.parameters = {
            "target_ratio": {
                "type": "number",
                "description": "Target utilization ratio after compaction (default: 0.5)",
                "required": False
            }
        }

    async def execute(self, target_ratio: float = 0.5) -> Dict[str, Any]:
        """Execute context compaction."""
        compactor = get_context_compactor()

        before_stats = compactor.get_stats()
        target_tokens = int(compactor.max_tokens * target_ratio)

        result = compactor.compact(target_tokens)

        return {
            "success": True,
            "before": {
                "tokens": before_stats["total_tokens"],
                "entries": before_stats["entry_count"],
            },
            "after": {
                "tokens": result.total_tokens,
                "entries": len(result.entries),
            },
            "compression_ratio": f"{result.compression_ratio:.1%}",
            "removed_entries": result.removed_count,
            "summarized_entries": result.summarized_count,
        }
