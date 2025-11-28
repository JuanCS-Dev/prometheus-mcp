"""
Consolidated Context Manager - Week 4 Day 1
Wraps ContextAwarenessEngine with ContextOptimizer API.
Boris Cherny Implementation.
"""

from typing import Dict
from jdev_cli.tui.components.context_awareness import (
    ContextAwarenessEngine,
    OptimizationMetrics
)


class ConsolidatedContextManager:
    """
    Unified context manager combining best of both worlds.
    Wraps ContextAwarenessEngine and provides ContextOptimizer API.
    """

    def __init__(self, max_tokens: int = 100_000):
        """Initialize with consolidated features."""
        self.engine = ContextAwarenessEngine(max_context_tokens=max_tokens)

    def get_optimization_stats(self) -> Dict:
        """Get stats (delegates to engine)."""
        return {
            'total_items': len(self.engine.items),
            'total_tokens': self.engine.window.total_tokens,
            'max_tokens': self.engine.max_context_tokens,
            'usage_percent': self.engine.window.utilization * 100,
            'pinned_items': len(self.engine.window.user_pinned),
            'optimizations_performed': self.engine.optimizations_performed,
            'total_tokens_freed': self.engine.total_tokens_freed
        }

    def get_optimization_recommendations(self) -> list:
        """Get recommendations."""
        recs = []
        usage = self.engine.window.utilization * 100

        if usage >= 90:
            recs.append("CRITICAL: Context >90% full - immediate optimization needed")
        elif usage >= 80:
            recs.append("WARNING: Context >80% full - consider optimizing")

        return recs

    def auto_optimize(self, target_usage: float = 0.7):
        """Auto-optimize (delegates to engine's optimize_context)."""
        # Use existing optimize_context method
        result = self.engine.optimize_context(target_utilization=target_usage)

        # Convert to OptimizationMetrics format
        return OptimizationMetrics(
            items_before=len(self.engine.items) + result.get('removed', 0),
            items_after=len(self.engine.items),
            tokens_before=self.engine.window.total_tokens + result.get('tokens_freed', 0),
            tokens_after=self.engine.window.total_tokens,
            items_removed=result.get('removed', 0),
            tokens_freed=result.get('tokens_freed', 0),
            duration_ms=result.get('duration_ms', 0)
        )

    # Delegate rendering methods
    def render_token_usage_realtime(self):
        """Delegate to engine."""
        return self.engine.render_token_usage_realtime()

    def update_tokens(self, input_tokens: int, output_tokens: int, cost: float = 0.0):
        """Delegate to engine."""
        return self.engine.update_tokens(input_tokens, output_tokens, cost)
