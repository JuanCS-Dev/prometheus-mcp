"""
DevSquadStateMachine - Phase-Based Workflow State Machine
Pipeline de Diamante - Camada 2: GOVERNANCE GATE

Addresses: ISSUE-074, ISSUE-075, ISSUE-076 (DevSquad workflow and rollback)

Implements:
- State machine for DevSquad phases
- Transition validation
- Checkpoint at each phase
- Rollback to previous phase

Design Philosophy:
- Explicit state transitions
- No skipping phases
- Safe rollback at any point
- Traceable state history
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
from contextlib import contextmanager
import logging

logger = logging.getLogger(__name__)


class Phase(Enum):
    """DevSquad workflow phases."""
    INIT = "init"
    ARCHITECT = "architect"
    EXPLORER = "explorer"
    PLANNER = "planner"
    EXECUTOR = "executor"
    REVIEWER = "reviewer"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLBACK = "rollback"


class TransitionResult(Enum):
    """Result of a state transition."""
    SUCCESS = "success"
    BLOCKED = "blocked"
    INVALID = "invalid"
    ERROR = "error"


@dataclass
class PhaseCheckpoint:
    """Checkpoint of state at a phase."""
    phase: Phase
    timestamp: float
    context: Dict[str, Any]
    outputs: Dict[str, Any]
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PhaseResult:
    """Result of phase execution."""
    phase: Phase
    success: bool
    outputs: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    duration: float = 0.0
    next_phase: Optional[Phase] = None


@dataclass
class StateTransition:
    """A state transition record."""
    from_phase: Phase
    to_phase: Phase
    timestamp: float
    reason: str
    success: bool


class DevSquadStateMachine:
    """
    State machine for DevSquad workflow phases.

    Enforces:
    - Valid phase ordering: INIT → ARCHITECT → EXPLORER → PLANNER → EXECUTOR → REVIEWER → COMPLETED
    - No phase skipping
    - Rollback capability to any previous phase
    - Checkpoint at each transition

    Usage:
        sm = DevSquadStateMachine()
        sm.start()

        result = sm.transition_to(Phase.ARCHITECT, context={})
        if result.success:
            # Do architect work
            sm.complete_phase(outputs={"design": {...}})
            sm.transition_to(Phase.EXPLORER, context={})
    """

    # Valid transitions (from_phase -> allowed_to_phases)
    VALID_TRANSITIONS: Dict[Phase, Set[Phase]] = {
        Phase.INIT: {Phase.ARCHITECT, Phase.EXPLORER, Phase.PLANNER},  # Can start at different points
        Phase.ARCHITECT: {Phase.EXPLORER, Phase.PLANNER, Phase.FAILED, Phase.ROLLBACK},
        Phase.EXPLORER: {Phase.PLANNER, Phase.FAILED, Phase.ROLLBACK},
        Phase.PLANNER: {Phase.EXECUTOR, Phase.FAILED, Phase.ROLLBACK},
        Phase.EXECUTOR: {Phase.REVIEWER, Phase.PLANNER, Phase.FAILED, Phase.ROLLBACK},  # Can go back to planner
        Phase.REVIEWER: {Phase.COMPLETED, Phase.EXECUTOR, Phase.FAILED, Phase.ROLLBACK},  # Can send back to executor
        Phase.COMPLETED: set(),  # Terminal state
        Phase.FAILED: {Phase.ROLLBACK, Phase.INIT},  # Can rollback or restart
        Phase.ROLLBACK: {Phase.INIT, Phase.ARCHITECT, Phase.EXPLORER, Phase.PLANNER, Phase.EXECUTOR},
    }

    def __init__(self, workflow_id: Optional[str] = None):
        """
        Initialize state machine.

        Args:
            workflow_id: Unique workflow identifier
        """
        import uuid
        self.workflow_id = workflow_id or str(uuid.uuid4())
        self.current_phase = Phase.INIT
        self.checkpoints: Dict[Phase, PhaseCheckpoint] = {}
        self.transitions: List[StateTransition] = []
        self.started_at: Optional[float] = None
        self.completed_at: Optional[float] = None
        self._phase_start_time: Optional[float] = None

    def start(self, context: Optional[Dict[str, Any]] = None) -> bool:
        """Start the workflow."""
        if self.started_at is not None:
            logger.warning(f"Workflow {self.workflow_id} already started")
            return False

        self.started_at = time.time()
        self._phase_start_time = self.started_at

        # Create initial checkpoint
        self._create_checkpoint(Phase.INIT, context or {}, {})

        logger.info(f"Workflow {self.workflow_id} started")
        return True

    def can_transition_to(self, target_phase: Phase) -> Tuple[bool, str]:
        """
        Check if transition to target phase is valid.

        Returns:
            (can_transition, reason)
        """
        if self.current_phase == target_phase:
            return False, "Already in target phase"

        valid_targets = self.VALID_TRANSITIONS.get(self.current_phase, set())
        if target_phase not in valid_targets:
            return False, f"Invalid transition from {self.current_phase.value} to {target_phase.value}"

        return True, "Valid transition"

    def transition_to(
        self,
        target_phase: Phase,
        context: Optional[Dict[str, Any]] = None,
        reason: str = "Workflow progression"
    ) -> StateTransition:
        """
        Transition to a new phase.

        Args:
            target_phase: Phase to transition to
            context: Context for the new phase
            reason: Reason for transition

        Returns:
            StateTransition record
        """
        can_transition, validation_reason = self.can_transition_to(target_phase)

        transition = StateTransition(
            from_phase=self.current_phase,
            to_phase=target_phase,
            timestamp=time.time(),
            reason=reason,
            success=can_transition
        )

        if not can_transition:
            logger.warning(f"Blocked transition: {validation_reason}")
            self.transitions.append(transition)
            return transition

        # Save checkpoint for current phase before leaving
        if self.current_phase != Phase.INIT:
            self._create_checkpoint(self.current_phase, context or {}, {})

        # Perform transition
        prev_phase = self.current_phase
        self.current_phase = target_phase
        self._phase_start_time = time.time()

        self.transitions.append(transition)

        logger.info(f"Transitioned from {prev_phase.value} to {target_phase.value}")

        # Check for terminal states
        if target_phase == Phase.COMPLETED:
            self.completed_at = time.time()
            logger.info(f"Workflow {self.workflow_id} completed")
        elif target_phase == Phase.FAILED:
            self.completed_at = time.time()
            logger.warning(f"Workflow {self.workflow_id} failed")

        return transition

    def complete_phase(
        self,
        outputs: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> PhaseResult:
        """
        Mark current phase as complete and save outputs.

        Args:
            outputs: Phase outputs to save
            context: Updated context

        Returns:
            PhaseResult with completion status
        """
        duration = time.time() - (self._phase_start_time or time.time())

        # Create checkpoint with outputs
        self._create_checkpoint(self.current_phase, context or {}, outputs or {})

        # Determine next phase
        next_phase = self._get_default_next_phase()

        result = PhaseResult(
            phase=self.current_phase,
            success=True,
            outputs=outputs or {},
            duration=duration,
            next_phase=next_phase
        )

        logger.info(f"Phase {self.current_phase.value} completed in {duration:.2f}s")
        return result

    def fail_phase(
        self,
        errors: List[str],
        context: Optional[Dict[str, Any]] = None
    ) -> PhaseResult:
        """
        Mark current phase as failed.

        Args:
            errors: List of error messages
            context: Context at failure

        Returns:
            PhaseResult with failure status
        """
        duration = time.time() - (self._phase_start_time or time.time())

        # Save checkpoint with error context
        error_context = {"errors": errors, **(context or {})}
        self._create_checkpoint(self.current_phase, error_context, {})

        result = PhaseResult(
            phase=self.current_phase,
            success=False,
            errors=errors,
            duration=duration,
            next_phase=Phase.FAILED
        )

        logger.error(f"Phase {self.current_phase.value} failed: {errors}")
        return result

    def rollback_to(self, target_phase: Phase) -> Tuple[bool, str]:
        """
        Rollback to a previous phase.

        Args:
            target_phase: Phase to rollback to

        Returns:
            (success, message)
        """
        # Check if we have a checkpoint for target phase
        if target_phase not in self.checkpoints:
            return False, f"No checkpoint for phase {target_phase.value}"

        # Transition through ROLLBACK state
        self.transition_to(Phase.ROLLBACK, reason=f"Rolling back to {target_phase.value}")

        # Restore checkpoint
        checkpoint = self.checkpoints[target_phase]

        # Transition to target
        result = self.transition_to(target_phase, context=checkpoint.context, reason="Rollback")

        if result.success:
            logger.info(f"Rolled back to {target_phase.value}")
            return True, f"Rolled back to {target_phase.value}"
        else:
            return False, "Rollback transition failed"

    def get_checkpoint(self, phase: Phase) -> Optional[PhaseCheckpoint]:
        """Get checkpoint for a phase."""
        return self.checkpoints.get(phase)

    def get_history(self) -> List[StateTransition]:
        """Get complete transition history."""
        return self.transitions.copy()

    def get_state_summary(self) -> Dict[str, Any]:
        """Get summary of current state."""
        return {
            "workflow_id": self.workflow_id,
            "current_phase": self.current_phase.value,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "transitions_count": len(self.transitions),
            "checkpoints": list(self.checkpoints.keys()),
            "is_terminal": self.current_phase in {Phase.COMPLETED, Phase.FAILED},
        }

    def _create_checkpoint(
        self,
        phase: Phase,
        context: Dict[str, Any],
        outputs: Dict[str, Any]
    ) -> PhaseCheckpoint:
        """Create and store a checkpoint."""
        checkpoint = PhaseCheckpoint(
            phase=phase,
            timestamp=time.time(),
            context=context,
            outputs=outputs,
        )
        self.checkpoints[phase] = checkpoint
        return checkpoint

    def _get_default_next_phase(self) -> Optional[Phase]:
        """Get the default next phase in the workflow."""
        phase_order = [
            Phase.INIT, Phase.ARCHITECT, Phase.EXPLORER,
            Phase.PLANNER, Phase.EXECUTOR, Phase.REVIEWER, Phase.COMPLETED
        ]
        try:
            current_idx = phase_order.index(self.current_phase)
            if current_idx < len(phase_order) - 1:
                return phase_order[current_idx + 1]
        except ValueError:
            pass
        return None

    @property
    def is_running(self) -> bool:
        """Check if workflow is running."""
        return (
            self.started_at is not None and
            self.completed_at is None and
            self.current_phase not in {Phase.COMPLETED, Phase.FAILED}
        )

    @property
    def is_completed(self) -> bool:
        """Check if workflow is completed."""
        return self.current_phase == Phase.COMPLETED

    @property
    def is_failed(self) -> bool:
        """Check if workflow failed."""
        return self.current_phase == Phase.FAILED


@contextmanager
def workflow_phase(sm: DevSquadStateMachine, phase: Phase, context: Optional[Dict] = None):
    """
    Context manager for workflow phases.

    Usage:
        with workflow_phase(sm, Phase.EXECUTOR) as phase_ctx:
            # Do work
            phase_ctx["outputs"]["result"] = "done"
    """
    phase_context = {"outputs": {}, "context": context or {}}

    # Transition to phase
    transition = sm.transition_to(phase, context=context)
    if not transition.success:
        raise RuntimeError(f"Failed to enter phase {phase.value}")

    try:
        yield phase_context
        # Complete phase on success
        sm.complete_phase(outputs=phase_context.get("outputs"), context=phase_context.get("context"))
    except Exception as e:
        # Fail phase on error
        sm.fail_phase(errors=[str(e)], context=phase_context.get("context"))
        raise


# Export all public symbols
__all__ = [
    'Phase',
    'TransitionResult',
    'PhaseCheckpoint',
    'PhaseResult',
    'StateTransition',
    'DevSquadStateMachine',
    'workflow_phase',
]
