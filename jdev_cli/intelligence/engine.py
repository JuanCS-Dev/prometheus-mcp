"""Suggestion engine - core intelligence.

Boris Cherny principle: "Código é lido 10x mais que escrito"
Every function has a single, clear responsibility.
"""

import time
import logging
from typing import List, Optional

from .types import (
    Suggestion,
    Context,
    SuggestionPattern,
    SuggestionResult
)

logger = logging.getLogger(__name__)


class SuggestionEngine:
    """Engine for generating intelligent suggestions.
    
    Design: Registry pattern for extensibility + Strategy pattern for suggestions.
    Zero side effects - pure functions where possible.
    """

    def __init__(self) -> None:
        """Initialize empty engine."""
        self._patterns: List[SuggestionPattern] = []
        self._enabled: bool = True

    def register_pattern(self, pattern: SuggestionPattern) -> None:
        """Register a new suggestion pattern.
        
        Args:
            pattern: Pattern to register
            
        Note: Patterns are evaluated in order of priority (highest first)
        """
        # Insert maintaining priority order (binary search would be overkill for <100 patterns)
        insert_pos = 0
        for i, p in enumerate(self._patterns):
            if pattern.priority > p.priority:
                insert_pos = i
                break
            insert_pos = i + 1

        self._patterns.insert(insert_pos, pattern)
        logger.debug(f"Registered pattern '{pattern.name}' with priority {pattern.priority}")

    def unregister_pattern(self, name: str) -> bool:
        """Unregister a pattern by name.
        
        Returns:
            True if pattern was found and removed
        """
        initial_len = len(self._patterns)
        self._patterns = [p for p in self._patterns if p.name != name]
        removed = len(self._patterns) < initial_len

        if removed:
            logger.debug(f"Unregistered pattern '{name}'")
        return removed

    def generate_suggestions(
        self,
        context: Context,
        max_suggestions: int = 5
    ) -> SuggestionResult:
        """Generate suggestions for current context.
        
        Args:
            context: Current context
            max_suggestions: Maximum number of suggestions to return
            
        Returns:
            SuggestionResult with suggestions and metadata
            
        Boris Cherny: Clear error handling, no silent failures
        """
        start_time = time.perf_counter()
        suggestions: List[Suggestion] = []
        patterns_evaluated = 0

        if not self._enabled:
            logger.debug("Engine disabled, returning empty result")
            return SuggestionResult(
                suggestions=[],
                context=context,
                generation_time_ms=0.0,
                patterns_evaluated=0
            )

        for pattern in self._patterns:
            patterns_evaluated += 1

            try:
                if pattern.matches(context):
                    suggestion = pattern.suggestion_fn(context)
                    if suggestion is not None:
                        suggestions.append(suggestion)

                        if len(suggestions) >= max_suggestions:
                            break

            except Exception as e:
                logger.error(f"Pattern '{pattern.name}' failed: {e}", exc_info=True)
                # Continue with other patterns (fail gracefully)
                continue

        generation_time = (time.perf_counter() - start_time) * 1000

        return SuggestionResult(
            suggestions=suggestions,
            context=context,
            generation_time_ms=generation_time,
            patterns_evaluated=patterns_evaluated
        )

    def enable(self) -> None:
        """Enable suggestion generation."""
        self._enabled = True
        logger.debug("Engine enabled")

    def disable(self) -> None:
        """Disable suggestion generation."""
        self._enabled = False
        logger.debug("Engine disabled")

    @property
    def pattern_count(self) -> int:
        """Get number of registered patterns."""
        return len(self._patterns)

    @property
    def enabled_pattern_count(self) -> int:
        """Get number of enabled patterns."""
        return sum(1 for p in self._patterns if p.enabled)


# Global singleton for easy access
_engine: Optional[SuggestionEngine] = None


def get_engine() -> SuggestionEngine:
    """Get global suggestion engine (singleton pattern).
    
    Boris Cherny: Singletons are acceptable for stateful services
    that truly need global access.
    """
    global _engine
    if _engine is None:
        _engine = SuggestionEngine()
    return _engine
