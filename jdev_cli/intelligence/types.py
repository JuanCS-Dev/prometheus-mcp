"""Type definitions for intelligence layer.

Following Boris Cherny's principle: "If it doesn't have types, it's not production."
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List, Dict, Any, Callable
from datetime import datetime


class SuggestionType(Enum):
    """Types of suggestions the system can provide."""

    COMMAND_COMPLETION = "command_completion"
    NEXT_STEP = "next_step"
    ERROR_PREVENTION = "error_prevention"
    WORKFLOW_OPTIMIZATION = "workflow_optimization"
    CONTEXT_AWARE = "context_aware"


class SuggestionConfidence(Enum):
    """Confidence levels for suggestions."""

    HIGH = "high"      # 80-100% confidence
    MEDIUM = "medium"  # 50-79% confidence
    LOW = "low"        # 20-49% confidence


@dataclass(frozen=True)
class Suggestion:
    """Immutable suggestion object.
    
    Following functional programming principles: immutable data structures
    prevent a whole class of bugs.
    """

    type: SuggestionType
    content: str
    confidence: SuggestionConfidence
    reasoning: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)

    def __str__(self) -> str:
        """Human-readable representation."""
        icon = {
            SuggestionConfidence.HIGH: "🎯",
            SuggestionConfidence.MEDIUM: "💡",
            SuggestionConfidence.LOW: "💭"
        }[self.confidence]

        return f"{icon} {self.content}"


@dataclass(frozen=True)
class Context:
    """Context information for suggestion generation.
    
    Immutable to prevent temporal coupling bugs.
    """

    current_command: Optional[str] = None
    command_history: List[str] = field(default_factory=list)
    recent_errors: List[str] = field(default_factory=list)
    working_directory: str = "."
    git_branch: Optional[str] = None
    recent_files: List[str] = field(default_factory=list)
    environment: Dict[str, str] = field(default_factory=dict)

    def with_command(self, command: str) -> 'Context':
        """Return new Context with updated command (immutable update)."""
        return Context(
            current_command=command,
            command_history=self.command_history,
            recent_errors=self.recent_errors,
            working_directory=self.working_directory,
            git_branch=self.git_branch,
            recent_files=self.recent_files,
            environment=self.environment
        )


@dataclass
class SuggestionPattern:
    """Pattern for matching and suggesting commands."""

    name: str
    pattern: str
    suggestion_fn: Callable[[Context], Optional[Suggestion]]
    priority: int = 50
    enabled: bool = True

    def matches(self, context: Context) -> bool:
        """Check if pattern matches current context."""
        if not self.enabled:
            return False

        # Empty pattern means "always evaluate" (pattern checks context internally)
        if not self.pattern:
            return True

        # Non-empty pattern requires current_command
        if context.current_command:
            return self.pattern in context.current_command
        return False


@dataclass
class SuggestionResult:
    """Result of suggestion generation."""

    suggestions: List[Suggestion]
    context: Context
    generation_time_ms: float
    patterns_evaluated: int

    @property
    def best_suggestion(self) -> Optional[Suggestion]:
        """Get highest confidence suggestion."""
        if not self.suggestions:
            return None

        confidence_order = {
            SuggestionConfidence.HIGH: 3,
            SuggestionConfidence.MEDIUM: 2,
            SuggestionConfidence.LOW: 1
        }

        return max(
            self.suggestions,
            key=lambda s: confidence_order[s.confidence]
        )
