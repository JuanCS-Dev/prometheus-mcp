"""Command explanation engine.

Provides adaptive, context-aware explanations for commands.
"""

from .engine import ExplanationEngine, explain_command
from .types import Explanation, ExplanationLevel, CommandBreakdown

__all__ = [
    'ExplanationEngine',
    'explain_command',
    'Explanation',
    'ExplanationLevel',
    'CommandBreakdown'
]
