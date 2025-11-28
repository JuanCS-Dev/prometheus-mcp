"""
🏛️ Justiça Integrated Agent - Constitutional Governance for Multi-Agent Systems

This module provides the integration layer between the jdev_cli agent framework
and the Justiça constitutional governance framework.

Architecture:
    - Wraps jdev_governance.justica.JusticaAgent as a BaseAgent
    - Provides pre-execution governance hooks for all agent operations
    - Enforces constitutional principles through trust-based verification
    - Exposes governance metrics for UI/monitoring

Usage:
    ```python
    from jdev_cli.agents.justica_agent import JusticaIntegratedAgent
    from jdev_governance.justica import EnforcementMode

    justica = JusticaIntegratedAgent(
        llm_client=llm_client,
        mcp_client=mcp_client,
        enforcement_mode=EnforcementMode.NORMATIVE,
        verbose_ui=True
    )

    # Pre-execution governance check
    verdict = await justica.evaluate_action(
        agent_id="executor",
        action_type="file_write",
        context={"path": "/etc/passwd"}
    )

    if verdict.approved:
        # Proceed with operation
        pass
    else:
        # Block or escalate to human
        print(verdict.reasoning)
    ```

Integration Points:
    - BaseAgent.execute(): Main execution with governance wrapping
    - Maestro orchestration: Pre-execution governance hooks
    - UI: Verbose governance panels (Rich formatting)
    - Audit: Transparent logging to jdev_cli logs

Enforcement Modes:
    - COERCIVE: Strict blocking (high security)
    - NORMATIVE: Balanced (default, per user choice)
    - ADAPTIVE: Learning from feedback

Author: Claude Code (Sonnet 4.5)
Version: 1.0.0
License: MIT
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, AsyncIterator
from uuid import uuid4

from pydantic import BaseModel, Field

# Base agent framework
from .base import (
    BaseAgent,
    AgentTask,
    AgentResponse,
    AgentRole,
    AgentCapability,
)

# Justiça framework (all imports validated in CERTIFICACAO_IMPORTS_PHASE1_2.md)
from jdev_governance.justica import (
    JusticaAgent,
    JusticaConfig,
    JusticaVerdict,
    EnforcementMode,
    Constitution,
    TrustLevel,
    AuditLogger,
    AuditLevel,
    AuditCategory,
    ConsoleBackend,
    FileBackend,
    create_default_constitution,
)

# --- Governance Metrics for UI/Monitoring ---

class GovernanceMetrics(BaseModel):
    """
    Governance metrics exposed for UI and monitoring.

    Used by Maestro UI to display governance panels with Rich formatting.
    """
    agent_id: str
    trust_score: float = Field(ge=0.0, le=1.0, description="Current trust score (0.0 - 1.0)")
    trust_level: TrustLevel
    total_evaluations: int = 0
    approved_count: int = 0
    blocked_count: int = 0
    escalated_count: int = 0
    violations: List[Dict[str, Any]] = Field(default_factory=list)
    last_evaluation: Optional[datetime] = None

    @property
    def approval_rate(self) -> float:
        """Calculate approval rate (0.0 - 1.0)."""
        if self.total_evaluations == 0:
            return 1.0
        return self.approved_count / self.total_evaluations

    @property
    def block_rate(self) -> float:
        """Calculate block rate (0.0 - 1.0)."""
        if self.total_evaluations == 0:
            return 0.0
        return self.blocked_count / self.total_evaluations


# --- Main Integrated Agent ---

class JusticaIntegratedAgent(BaseAgent):
    """
    Justiça Integrated Agent - Constitutional Governance Wrapper.

    This agent wraps the standalone Justiça framework as a BaseAgent,
    providing governance capabilities to the qwen-dev-cli multi-agent system.

    Key Responsibilities:
        - Pre-execution governance checks for all agents
        - Trust score management and temporal decay
        - Violation detection and enforcement
        - Transparent audit logging
        - Governance metrics for UI/monitoring

    Configuration:
        - enforcement_mode: COERCIVE, NORMATIVE (default), or ADAPTIVE
        - verbose_ui: Show detailed governance panels (default: True)
        - constitution: Custom or default 5-principle constitution
        - audit_backend: Console (default), File, or InMemory

    User Choices (from implementation plan):
        - Enforcement Mode: NORMATIVE (balanced)
        - UX: VERBOSE (visible to users)
    """

    def __init__(
        self,
        llm_client: Any,
        mcp_client: Any,
        enforcement_mode: EnforcementMode = EnforcementMode.NORMATIVE,
        verbose_ui: bool = True,
        constitution: Optional[Constitution] = None,
        audit_backend: Optional[str] = "console",
        system_prompt: Optional[str] = None,
    ) -> None:
        """
        Initialize Justiça Integrated Agent.

        Args:
            llm_client: LLM client for reasoning
            mcp_client: MCP client for tool execution
            enforcement_mode: Enforcement mode (default: NORMATIVE per user choice)
            verbose_ui: Show governance panels (default: True per user choice)
            constitution: Custom constitution (default: 5-principle default)
            audit_backend: Audit backend ("console", "file", "memory")
            system_prompt: Custom system prompt (optional)
        """
        # Initialize BaseAgent with GOVERNANCE role
        super().__init__(
            role=AgentRole.GOVERNANCE,
            capabilities=[
                AgentCapability.READ_ONLY,  # Can read files for analysis
                AgentCapability.FILE_EDIT,  # Can write audit logs
            ],
            llm_client=llm_client,
            mcp_client=mcp_client,
            system_prompt=system_prompt or self._create_system_prompt(),
        )

        # Configuration
        self.enforcement_mode = enforcement_mode
        self.verbose_ui = verbose_ui

        # Create Justiça core agent
        self.justica_config = JusticaConfig(
            agent_id="justica-integrated",
            enforcement_mode=enforcement_mode,
        )

        # Use provided constitution or create default
        self.constitution = constitution or create_default_constitution()

        # Initialize core Justiça agent
        self.justica_core = JusticaAgent(
            config=self.justica_config,
            constitution=self.constitution,
        )

        # Set up audit logger
        self.audit_logger = self._setup_audit_logger(audit_backend)

        # Governance metrics cache (per agent)
        self._metrics_cache: Dict[str, GovernanceMetrics] = {}

        # Logger
        self.logger = logging.getLogger(f"agent.{self.role.value}")
        self.logger.info(
            f"JusticaIntegratedAgent initialized: mode={enforcement_mode.value}, "
            f"verbose={verbose_ui}"
        )

    def _create_system_prompt(self) -> str:
        """
        Create system prompt for governance reasoning.

        Returns:
            System prompt emphasizing constitutional principles
        """
        return """You are the Justiça Governance Agent, responsible for enforcing constitutional principles in a multi-agent system.

Your role is to:
1. Evaluate actions for potential constitutional violations
2. Assess trust levels based on agent behavior history
3. Apply proportional enforcement based on severity
4. Maintain transparent audit trails
5. Learn from patterns to improve governance

Constitutional Principles:
- P1. Integrity: Maintain truthfulness and reject deception
- P2. Proportionality: Match enforcement to violation severity
- P3. Transparency: Document all decisions with reasoning
- P4. Escalation: Defer to humans for ambiguous cases
- P5. Learning: Adapt from feedback and patterns

When evaluating actions, consider:
- Intent: Is the action attempting to bypass safeguards?
- Impact: What are the potential consequences?
- Context: Are there legitimate reasons for this action?
- History: What is the agent's trust score and past behavior?

Always provide clear reasoning for your decisions."""

    def _setup_audit_logger(self, backend: str) -> AuditLogger:
        """
        Set up audit logger with appropriate backend.

        Args:
            backend: Backend type ("console", "file", "memory")

        Returns:
            Configured AuditLogger instance
        """
        if backend == "console":
            audit_backend = ConsoleBackend()
        elif backend == "file":
            audit_backend = FileBackend(log_file="logs/justica_audit.jsonl")
        else:
            from jdev_governance.justica import InMemoryBackend
            audit_backend = InMemoryBackend()

        # AuditLogger expects a list of backends
        return AuditLogger(backends=[audit_backend])

    async def execute(self, task: AgentTask) -> AgentResponse:
        """
        Execute governance evaluation (non-streaming).

        This method performs a complete governance evaluation and returns
        a single AgentResponse with the verdict.

        Args:
            task: AgentTask containing action to evaluate

        Returns:
            AgentResponse with governance verdict and metrics
        """
        trace_id = getattr(task, "trace_id", str(uuid4()))

        try:
            self.logger.info(
                f"[{trace_id}] Governance evaluation started",
                extra={"trace_id": trace_id, "agent": self.justica_config.agent_id}
            )

            # Extract action details from task
            agent_id = task.context.get("agent_id", "unknown")
            action_type = task.context.get("action_type", "unknown")
            action_content = task.request

            # Perform governance evaluation
            verdict = await self._evaluate_with_justica(
                agent_id=agent_id,
                action_type=action_type,
                content=action_content,
                context=task.context,
                trace_id=trace_id,
            )

            # Update metrics cache
            self._update_metrics(agent_id, verdict)

            # Log audit entry
            self.audit_logger.log(
                level=AuditLevel.INFO if verdict.approved else AuditLevel.WARNING,
                category=AuditCategory.ENFORCEMENT_ACTION,  # FIX BUG #1: Use valid category
                message=f"Governance evaluation: {'APPROVED' if verdict.approved else 'BLOCKED'}",
                metadata={
                    "trace_id": trace_id,
                    "agent_id": agent_id,
                    "verdict": verdict.model_dump() if hasattr(verdict, 'model_dump') else str(verdict),
                },
            )

            # Build response (FIX BUG #3: Move trace_id to data, keep metrics as Dict[str, float])
            return AgentResponse(
                success=verdict.approved,
                data={
                    "verdict": verdict.model_dump() if hasattr(verdict, 'model_dump') else {
                        "approved": verdict.approved,
                        "reasoning": verdict.reasoning,
                        "severity": self._get_verdict_severity(verdict),
                        "action_taken": self._get_verdict_action(verdict),
                    },
                    "metrics": self._metrics_cache.get(agent_id, {}).model_dump() if agent_id in self._metrics_cache else {},
                    "trace_id": trace_id,
                    "evaluation_time": datetime.utcnow().isoformat(),
                },
                reasoning=verdict.reasoning,
                error=None if verdict.approved else f"Blocked: {verdict.reasoning}",
                metrics={},  # Keep empty for now (could add numeric metrics later)
            )

        except Exception as e:
            self.logger.error(
                f"[{trace_id}] Governance evaluation failed: {e}",
                extra={"trace_id": trace_id, "error": str(e)},
                exc_info=True,
            )

            return AgentResponse(
                success=False,
                data={},
                reasoning="Governance evaluation failed due to internal error",
                error=str(e),
                metrics={"trace_id": trace_id},
            )

    async def execute_streaming(
        self,
        task: AgentTask,
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        Execute governance evaluation with streaming feedback.

        This method yields incremental updates during governance evaluation,
        allowing the UI to show real-time progress.

        Args:
            task: AgentTask containing action to evaluate

        Yields:
            Dict with streaming updates:
                - type: "status", "reasoning", "verdict", "metrics"
                - data: Type-specific data
        """
        trace_id = getattr(task, "trace_id", str(uuid4()))

        try:
            # Status: Starting evaluation
            yield {
                "type": "status",
                "data": {
                    "stage": "starting",
                    "message": "🏛️ Governance evaluation starting...",
                    "trace_id": trace_id,
                },
            }

            # Extract action details
            agent_id = task.context.get("agent_id", "unknown")
            action_type = task.context.get("action_type", "unknown")
            action_content = task.request

            # Status: Analyzing
            yield {
                "type": "status",
                "data": {
                    "stage": "analyzing",
                    "message": f"Analyzing {action_type} from {agent_id}...",
                },
            }

            # Perform evaluation (internal)
            verdict = await self._evaluate_with_justica(
                agent_id=agent_id,
                action_type=action_type,
                content=action_content,
                context=task.context,
                trace_id=trace_id,
            )

            # Stream reasoning chunks if verbose
            if self.verbose_ui and verdict.reasoning:
                reasoning_chunks = verdict.reasoning.split(". ")
                for chunk in reasoning_chunks:
                    if chunk.strip():
                        yield {
                            "type": "reasoning",
                            "data": {"chunk": chunk.strip() + ". "},
                        }
                        await asyncio.sleep(0.05)  # 50ms delay for smooth streaming

            # Update metrics
            self._update_metrics(agent_id, verdict)

            # Yield final verdict
            yield {
                "type": "verdict",
                "data": {
                    "approved": verdict.approved,
                    "reasoning": verdict.reasoning,
                    "severity": self._get_verdict_severity(verdict),
                    "action_taken": self._get_verdict_action(verdict),
                },
            }

            # Yield metrics if verbose
            if self.verbose_ui and agent_id in self._metrics_cache:
                yield {
                    "type": "metrics",
                    "data": self._metrics_cache[agent_id].model_dump(),
                }

            # Status: Complete
            yield {
                "type": "status",
                "data": {
                    "stage": "complete",
                    "message": f"✅ Governance evaluation complete: {'APPROVED' if verdict.approved else 'BLOCKED'}",
                    "trace_id": trace_id,
                },
            }

        except Exception as e:
            self.logger.error(
                f"[{trace_id}] Streaming governance evaluation failed: {e}",
                exc_info=True,
            )

            yield {
                "type": "error",
                "data": {
                    "error": str(e),
                    "trace_id": trace_id,
                },
            }

    async def _evaluate_with_justica(
        self,
        agent_id: str,
        action_type: str,
        content: str,
        context: Dict[str, Any],
        trace_id: str,
    ) -> JusticaVerdict:
        """
        Internal method to evaluate action with Justiça core.

        Args:
            agent_id: ID of agent requesting action
            action_type: Type of action (e.g., "file_write", "bash_exec")
            content: Action content/payload
            context: Additional context
            trace_id: Trace ID for logging

        Returns:
            JusticaVerdict with approval decision and reasoning
        """
        try:
            # Call Justiça core evaluation
            verdict = self.justica_core.evaluate_input(
                agent_id=agent_id,
                content=content,
                context={
                    **context,
                    "action_type": action_type,
                    "trace_id": trace_id,
                },
            )

            return verdict

        except Exception as e:
            self.logger.error(f"[{trace_id}] Justiça core evaluation failed: {e}")

            # Fallback verdict (fail-safe: block on error)
            # Note: JusticaVerdict doesn't have severity/violation_type/action_taken
            return JusticaVerdict(
                agent_id=agent_id,
                content_analyzed=content[:200],  # Truncate for safety
                approved=False,
                reasoning=f"Governance evaluation failed: {str(e)}. Defaulting to BLOCK for safety.",
                requires_human_review=True,
            )

    def _get_verdict_severity(self, verdict: JusticaVerdict) -> str:
        """Get severity from verdict with fallback."""
        # Check classification for severity
        if verdict.classification and hasattr(verdict.classification, 'severity'):
            return verdict.classification.severity.name
        # Fallback based on approval
        return "INFO" if verdict.approved else "MEDIUM"

    def _get_verdict_action(self, verdict: JusticaVerdict) -> str:
        """Get action from verdict with fallback."""
        if verdict.actions_taken:
            return verdict.actions_taken[0].action_type.name
        return "allow" if verdict.approved else "block"

    def _update_metrics(self, agent_id: str, verdict: JusticaVerdict) -> None:
        """
        Update governance metrics cache for an agent.

        Args:
            agent_id: Agent ID
            verdict: Verdict from evaluation
        """
        # Get or create metrics entry
        if agent_id not in self._metrics_cache:
            self._metrics_cache[agent_id] = GovernanceMetrics(
                agent_id=agent_id,
                trust_score=1.0,  # Start with full trust
                trust_level=TrustLevel.HIGH,
            )

        metrics = self._metrics_cache[agent_id]

        # Update counts
        metrics.total_evaluations += 1
        if verdict.approved:
            metrics.approved_count += 1
        else:
            metrics.blocked_count += 1

        if getattr(verdict, "requires_human_review", False):
            metrics.escalated_count += 1

        # Update trust score (get from Justiça core trust engine)
        trust_factor = self.justica_core.trust_engine.get_trust_factor(agent_id)
        trust_score = trust_factor.current_factor if trust_factor else 1.0
        metrics.trust_score = trust_score

        # Map trust score to trust level
        if trust_score >= 0.9:
            metrics.trust_level = TrustLevel.MAXIMUM
        elif trust_score >= 0.7:
            metrics.trust_level = TrustLevel.HIGH
        elif trust_score >= 0.5:
            metrics.trust_level = TrustLevel.MEDIUM
        elif trust_score >= 0.3:
            metrics.trust_level = TrustLevel.LOW
        else:
            metrics.trust_level = TrustLevel.SUSPENDED

        # Add violation if blocked
        if not verdict.approved:
            violation_type = "UNKNOWN"
            if verdict.classification and hasattr(verdict.classification, 'violation_type'):
                violation_type = verdict.classification.violation_type.name

            metrics.violations.append({
                "timestamp": datetime.utcnow().isoformat(),
                "type": violation_type,
                "severity": self._get_verdict_severity(verdict),
                "reasoning": verdict.reasoning,
            })

        # Update last evaluation timestamp
        metrics.last_evaluation = datetime.utcnow()

    # --- Public API Methods ---

    async def evaluate_action(
        self,
        agent_id: str,
        action_type: str,
        content: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> JusticaVerdict:
        """
        Public API: Evaluate an action for governance compliance.

        This is the main entry point for pre-execution governance checks.

        Args:
            agent_id: ID of agent requesting action
            action_type: Type of action (e.g., "file_write", "bash_exec")
            content: Action content/payload
            context: Additional context (optional)

        Returns:
            JusticaVerdict with approval decision

        Example:
            ```python
            verdict = await justica.evaluate_action(
                agent_id="executor",
                action_type="bash_exec",
                content="rm -rf /",
                context={"cwd": "/tmp"}
            )

            if verdict.approved:
                # Safe to proceed
                await executor.execute(...)
            else:
                # Block or escalate
                print(f"Blocked: {verdict.reasoning}")
            ```
        """
        trace_id = str(uuid4())
        return await self._evaluate_with_justica(
            agent_id=agent_id,
            action_type=action_type,
            content=content,
            context=context or {},
            trace_id=trace_id,
        )

    def get_metrics(self, agent_id: str) -> Optional[GovernanceMetrics]:
        """
        Get governance metrics for an agent.

        Args:
            agent_id: Agent ID

        Returns:
            GovernanceMetrics or None if agent not tracked
        """
        return self._metrics_cache.get(agent_id)

    def get_all_metrics(self) -> Dict[str, GovernanceMetrics]:
        """
        Get governance metrics for all tracked agents.

        Returns:
            Dict mapping agent_id to GovernanceMetrics
        """
        return self._metrics_cache.copy()

    def get_trust_score(self, agent_id: str) -> float:
        """
        Get current trust score for an agent.

        Args:
            agent_id: Agent ID

        Returns:
            Trust score (0.0 - 1.0), or 1.0 if agent not tracked
        """
        trust_factor = self.justica_core.trust_engine.get_trust_factor(agent_id)
        if trust_factor:
            return trust_factor.current_factor
        return 1.0  # Default if not tracked

    def reset_trust(self, agent_id: str) -> None:
        """
        Reset trust score for an agent to 1.0.

        This should only be used after human review/approval.

        Args:
            agent_id: Agent ID
        """
        # FIX BUG #4: Use correct TrustEngine API
        # Record multiple good actions to restore trust to 1.0
        trust_factor = self.justica_core.trust_engine.get_trust_factor(agent_id)
        if trust_factor:
            # Calculate how many good actions needed to restore to 1.0
            current = trust_factor.current_factor
            deficit = 1.0 - current

            # Record good actions (each adds ~0.01-0.05 depending on config)
            for _ in range(int(deficit * 50)):  # Conservative: 50 good actions max
                self.justica_core.trust_engine.record_good_action(
                    agent_id=agent_id,
                    description="Trust reset by human review",
                    context={"reset": True}
                )

            # Lift suspension if suspended
            is_suspended, _ = self.justica_core.trust_engine.check_suspension(agent_id)
            if is_suspended:
                self.justica_core.trust_engine.lift_suspension(
                    agent_id=agent_id,
                    reason="Trust reset by human review"
                )

        # Clear metrics cache
        if agent_id in self._metrics_cache:
            self._metrics_cache[agent_id].trust_score = 1.0
            self._metrics_cache[agent_id].trust_level = TrustLevel.HIGH
            self._metrics_cache[agent_id].violations.clear()
