"""
planner/validation.py: Plan Validation and Monitoring.

Contains:
- PlanValidator: Validates execution plans before execution
- ExecutionEvent: Event for observability
- ExecutionMonitor: Observability layer (OpenTelemetry compatible)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    pass


class PlanValidator:
    """
    Validates execution plans before execution.
    Catches issues early to prevent runtime failures.

    Checks:
    1. No circular dependencies
    2. All dependencies exist
    3. At least one entry point
    4. Resource budget is reasonable
    5. Each stage is reachable
    6. Critical steps have checkpoints
    """

    @staticmethod
    def validate(plan: Any) -> Tuple[bool, List[str]]:
        """
        Validate plan for common issues.

        Args:
            plan: ExecutionPlan to validate

        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors: List[str] = []

        # Get SOPs from plan (handle both old and new format)
        sops = getattr(plan, 'sops', [])
        stages = getattr(plan, 'stages', [])

        # Build SOP map
        sop_map = {sop.id: sop for sop in sops if hasattr(sop, 'id')}

        # Check 1: No circular dependencies
        visited: Set[str] = set()
        rec_stack: Set[str] = set()

        def has_cycle(step_id: str) -> bool:
            visited.add(step_id)
            rec_stack.add(step_id)

            step = sop_map.get(step_id)
            if not step:
                return False

            for dep_id in getattr(step, 'dependencies', []):
                if dep_id not in visited:
                    if has_cycle(dep_id):
                        return True
                elif dep_id in rec_stack:
                    errors.append(f"Circular dependency detected involving step {step_id}")
                    return True

            rec_stack.remove(step_id)
            return False

        for sop in sops:
            sop_id = getattr(sop, 'id', None)
            if sop_id and sop_id not in visited:
                has_cycle(sop_id)

        # Check 2: All dependencies exist
        all_ids = {getattr(sop, 'id', None) for sop in sops}
        for sop in sops:
            sop_id = getattr(sop, 'id', None)
            for dep in getattr(sop, 'dependencies', []):
                if dep not in all_ids:
                    errors.append(f"Step {sop_id} depends on non-existent step {dep}")

        # Check 3: At least one step without dependencies (entry point)
        if sops:
            entry_points = [sop for sop in sops if not getattr(sop, 'dependencies', [])]
            if not entry_points:
                errors.append("No entry point found - all steps have dependencies")

        # Check 4: Resource budget is reasonable
        token_budget = getattr(plan, 'token_budget', 0)
        if token_budget > 200000:
            errors.append(f"Token budget ({token_budget}) exceeds recommended limit (200k)")

        # Check 5: Each stage is reachable
        if stages:
            for stage in stages:
                stage_name = getattr(stage, 'name', 'unknown')
                stage_steps = getattr(stage, 'steps', [])
                if not stage_steps:
                    errors.append(f"Empty stage detected: {stage_name}")

        # Check 6: Critical steps have checkpoints
        from .types import AgentPriority
        critical_steps = [
            s for s in sops
            if getattr(s, 'priority', None) == AgentPriority.CRITICAL
        ]
        critical_with_checkpoints = [
            s for s in critical_steps
            if getattr(s, 'checkpoint', None)
        ]
        if critical_steps and not critical_with_checkpoints:
            errors.append("Critical steps found but no checkpoints defined")

        return len(errors) == 0, errors

    @staticmethod
    def validate_quick(plan: Any) -> bool:
        """Quick validation - returns True if valid."""
        is_valid, _ = PlanValidator.validate(plan)
        return is_valid

    @staticmethod
    def get_warnings(plan: Any) -> List[str]:
        """Get non-critical warnings for a plan."""
        warnings: List[str] = []

        sops = getattr(plan, 'sops', [])

        # Warning: Low confidence steps
        low_confidence = [
            s for s in sops
            if getattr(s, 'confidence_score', 1.0) < 0.5
        ]
        if low_confidence:
            warnings.append(f"{len(low_confidence)} steps have low confidence (<50%)")

        # Warning: No retry strategy
        no_retry = [
            s for s in sops
            if getattr(s, 'retry_count', 0) == 0
        ]
        if len(no_retry) == len(sops) and sops:
            warnings.append("No steps have retry strategy configured")

        # Warning: High token budget
        token_budget = getattr(plan, 'token_budget', 0)
        if token_budget > 100000:
            warnings.append(f"High token budget: {token_budget:,} tokens")

        return warnings


# ============================================================================
# EXECUTION MONITORING (OpenTelemetry Compatible)
# ============================================================================

@dataclass
class ExecutionEvent:
    """Event emitted during plan execution for observability."""
    timestamp: str
    event_type: str  # started, completed, failed, checkpoint
    step_id: str
    agent_role: str
    correlation_id: str
    duration_ms: Optional[int] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        event_type: str,
        step_id: str,
        agent_role: str,
        correlation_id: str,
        **kwargs
    ) -> ExecutionEvent:
        """Factory method to create event with current timestamp."""
        return cls(
            timestamp=datetime.now().isoformat(),
            event_type=event_type,
            step_id=step_id,
            agent_role=agent_role,
            correlation_id=correlation_id,
            **kwargs
        )


class ExecutionMonitor:
    """
    Observability layer for plan execution.
    Emits events compatible with OpenTelemetry.

    Example:
        monitor = ExecutionMonitor()
        monitor.emit(ExecutionEvent.create("started", "step-1", "executor", "corr-123"))
        # ... execute step ...
        monitor.emit(ExecutionEvent.create("completed", "step-1", "executor", "corr-123", duration_ms=150))
        print(monitor.get_metrics())
    """

    def __init__(self, verbose: bool = False):
        self.events: List[ExecutionEvent] = []
        self.verbose = verbose

    def emit(self, event: ExecutionEvent) -> None:
        """Emit execution event."""
        self.events.append(event)
        if self.verbose:
            print(f"[{event.timestamp}] {event.event_type}: {event.step_id} ({event.agent_role})")

    def start_step(self, step_id: str, agent_role: str, correlation_id: str) -> None:
        """Convenience method to emit start event."""
        self.emit(ExecutionEvent.create("started", step_id, agent_role, correlation_id))

    def complete_step(self, step_id: str, agent_role: str, correlation_id: str, duration_ms: int) -> None:
        """Convenience method to emit completion event."""
        self.emit(ExecutionEvent.create(
            "completed", step_id, agent_role, correlation_id, duration_ms=duration_ms
        ))

    def fail_step(self, step_id: str, agent_role: str, correlation_id: str, error: str) -> None:
        """Convenience method to emit failure event."""
        self.emit(ExecutionEvent.create(
            "failed", step_id, agent_role, correlation_id, error=error
        ))

    def get_metrics(self) -> Dict[str, Any]:
        """Get execution metrics."""
        completed = [e for e in self.events if e.event_type == "completed"]
        failed = [e for e in self.events if e.event_type == "failed"]
        started = [e for e in self.events if e.event_type == "started"]

        durations = [e.duration_ms for e in completed if e.duration_ms is not None]

        return {
            "total_events": len(self.events),
            "started_steps": len(started),
            "completed_steps": len(completed),
            "failed_steps": len(failed),
            "success_rate": len(completed) / max(len(started), 1),
            "total_duration_ms": sum(durations),
            "avg_duration_ms": sum(durations) / max(len(durations), 1) if durations else 0,
        }

    def clear(self) -> None:
        """Clear all events."""
        self.events.clear()
