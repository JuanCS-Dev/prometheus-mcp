"""Token tracking system with budget management and real-time monitoring."""

from typing import Dict, Optional, List
from dataclasses import dataclass
from datetime import datetime
import json


@dataclass
class TokenUsage:
    """Single token usage record."""
    timestamp: datetime
    input_tokens: int
    output_tokens: int
    total_tokens: int
    cost_estimate: float = 0.0
    context: str = ""


class TokenTracker:
    """Real-time token tracking with budget enforcement."""

    def __init__(self, budget: int = 1000000, cost_per_1k: float = 0.002):
        """
        Initialize tracker.
        
        Args:
            budget: Maximum tokens allowed
            cost_per_1k: Cost per 1000 tokens (default: Gemini Pro pricing)
        """
        self.budget = budget
        self.cost_per_1k = cost_per_1k
        self.history: List[TokenUsage] = []
        self.total_input = 0
        self.total_output = 0

    def track_tokens(self, input_tokens: int, output_tokens: int, context: str = "") -> None:
        """Record token usage."""
        if input_tokens < 0 or output_tokens < 0:
            raise ValueError("Token counts must be non-negative")

        total = input_tokens + output_tokens
        cost = (total / 1000) * self.cost_per_1k

        usage = TokenUsage(
            timestamp=datetime.now(),
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total,
            cost_estimate=cost,
            context=context
        )

        self.history.append(usage)
        self.total_input += input_tokens
        self.total_output += output_tokens

    def get_usage(self) -> Dict:
        """Get current usage statistics."""
        total = self.total_input + self.total_output
        return {
            "total_tokens": total,
            "input_tokens": self.total_input,
            "output_tokens": self.total_output,
            "budget": self.budget,
            "budget_remaining": self.budget - total,
            "budget_used_percent": (total / self.budget * 100) if self.budget > 0 else 0,
            "total_cost": sum(u.cost_estimate for u in self.history),
            "requests": len(self.history)
        }

    def is_over_budget(self) -> bool:
        """Check if budget exceeded."""
        return (self.total_input + self.total_output) > self.budget

    def get_warning_level(self) -> Optional[str]:
        """Get budget warning level."""
        usage_pct = (self.total_input + self.total_output) / self.budget * 100
        if usage_pct >= 90:
            return "critical"
        elif usage_pct >= 70:
            return "warning"
        return None

    def export_stats(self) -> str:
        """Export usage stats as JSON."""
        stats = self.get_usage()
        stats["history"] = [
            {
                "timestamp": u.timestamp.isoformat(),
                "input": u.input_tokens,
                "output": u.output_tokens,
                "total": u.total_tokens,
                "cost": u.cost_estimate,
                "context": u.context
            }
            for u in self.history[-20:]  # Last 20 requests
        ]
        return json.dumps(stats, indent=2)
