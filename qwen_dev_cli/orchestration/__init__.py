"""
DEVSQUAD: Agent Orchestration & Coordination
Pipeline de Diamante - Camada 2: GOVERNANCE GATE

This module provides the orchestration layer that coordinates multiple
specialist agents to execute complex development workflows.

Components:
    - MemoryManager: Shared context and session state management
    - DevSquad: Multi-agent orchestrator (5-phase workflow)
    - WorkflowLibrary: Pre-defined workflow templates
    - DevSquadStateMachine: State machine for phase management

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
from qwen_dev_cli.orchestration.state_machine import (
    DevSquadStateMachine,
    Phase,
    PhaseResult,
    StateTransition,
)

__all__ = [
    "MemoryManager",
    "SharedContext",
    "DevSquad",
    "WorkflowPhase",
    "WorkflowStatus",
    "WorkflowResult",
    "DevSquadStateMachine",
    "Phase",
    "PhaseResult",
    "StateTransition",
]
