"""
PROMETHEUS Memory Module.

MIRIX-inspired 6-Type Memory System (arXiv:2507.07957):
1. Core Memory - Identity and persistent values
2. Episodic Memory - Past experiences ("what happened")
3. Semantic Memory - Factual knowledge ("what I know")
4. Procedural Memory - Learned skills ("how I do things")
5. Resource Memory - External resource cache
6. Knowledge Vault - Long-term consolidated knowledge
"""

from .memory_system import (
    MemorySystem,
    MemoryType,
    MemoryEntry,
    EpisodicMemory,
    SemanticMemory,
    ProceduralMemory,
)

__all__ = [
    "MemorySystem",
    "MemoryType",
    "MemoryEntry",
    "EpisodicMemory",
    "SemanticMemory",
    "ProceduralMemory",
]
