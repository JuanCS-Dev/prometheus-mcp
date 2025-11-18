"""Type definitions for explanation engine.

Boris Cherny: Types first, implementation second.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional


class ExplanationLevel(Enum):
    """Detail level for explanations."""
    
    CONCISE = "concise"        # Expert: One-line
    BALANCED = "balanced"      # Intermediate: Brief with key points
    DETAILED = "detailed"      # Beginner: Full breakdown


@dataclass(frozen=True)
class CommandPart:
    """Single part of a command breakdown."""
    
    text: str
    explanation: str
    type: str  # 'command', 'flag', 'argument', 'operator'


@dataclass(frozen=True)
class CommandBreakdown:
    """Structured breakdown of a command."""
    
    parts: List[CommandPart]
    
    def format(self) -> str:
        """Format as human-readable text."""
        lines = []
        for part in self.parts:
            lines.append(f"  {part.text:<20} → {part.explanation}")
        return "\n".join(lines)


@dataclass(frozen=True)
class Explanation:
    """Immutable explanation object."""
    
    command: str
    summary: str
    breakdown: Optional[CommandBreakdown] = None
    examples: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    see_also: List[str] = field(default_factory=list)
    level: ExplanationLevel = ExplanationLevel.BALANCED
    
    def format(self) -> str:
        """Format explanation for display."""
        lines = [
            f"Command: {self.command}",
            f"\n{self.summary}",
        ]
        
        if self.breakdown and self.level != ExplanationLevel.CONCISE:
            lines.append(f"\nBreakdown:")
            lines.append(self.breakdown.format())
        
        if self.warnings:
            lines.append("\n⚠️  Warnings:")
            for warning in self.warnings:
                lines.append(f"  • {warning}")
        
        if self.examples and self.level == ExplanationLevel.DETAILED:
            lines.append("\n📚 Examples:")
            for example in self.examples:
                lines.append(f"  $ {example}")
        
        if self.see_also and self.level == ExplanationLevel.DETAILED:
            lines.append("\n🔗 See also:")
            for related in self.see_also:
                lines.append(f"  • {related}")
        
        return "\n".join(lines)
