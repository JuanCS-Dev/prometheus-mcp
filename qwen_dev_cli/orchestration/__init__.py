"""
DEVSQUAD: Agent Orchestration & Coordination

This module provides the orchestration layer that coordinates multiple
specialist agents to execute complex development workflows.

Components:
    - MemoryManager: Shared context and session state management
    - DevSquad: Multi-agent orchestrator (5-phase workflow)
    - WorkflowLibrary: Pre-defined workflow templates

Philosophy (Boris Cherny):
    "Coordination is harder than implementation."
    - Explicit state management
    - Type-safe agent communication
    - Atomic operations
    - Production-grade reliability
"""

from qwen_dev_cli.orchestration.memory import (
    MemoryManager,
    SharedContext,
)
from qwen_dev_cli.orchestration.squad import (
    DevSquad,
    WorkflowPhase,
    WorkflowStatus,
    WorkflowResult,
)

__all__ = [
    "MemoryManager",
    "SharedContext",
    "DevSquad",
    "WorkflowPhase",
    "WorkflowStatus",
    "WorkflowResult",
]
