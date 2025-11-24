"""
╔══════════════════════════════════════════════════════════════════════════════════╗
║                                                                                  ║
║                        GOVERNANCE PIPELINE                                       ║
║                                                                                  ║
║  Orchestrator-Worker pattern for multi-agent governance                         ║
║                                                                                  ║
║  Based on Nov 2025 best practices:                                              ║
║  - Anthropic: "Orchestrator-worker where lead agent coordinates process         ║
║                while delegating to specialized subagents that operate in         ║
║                parallel" (90.2% performance improvement)                         ║
║  - Google: "Agent identities tied to Cloud IAM, Model Armor protection"        ║
║  - MCP: "Security & governance layer, single audit trail"                      ║
║                                                                                  ║
║  Architecture:                                                                   ║
║  ```                                                                             ║
║  User Request                                                                    ║
║      ↓                                                                           ║
║  Maestro (Orchestrator)                                                          ║
║      ↓                                                                           ║
║  Governance Pipeline                                                             ║
║      ├── Justiça (Governance) ──┐                                               ║
║      └── Sofia (Counsel)        ├──→ PARALLEL EXECUTION                         ║
║                                 ┘                                                ║
║      ↓                                                                           ║
║  Worker Agent (if approved)                                                      ║
║  ```                                                                             ║
║                                                                                  ║
╚══════════════════════════════════════════════════════════════════════════════════╝
"""

import asyncio
import uuid
import logging
from datetime import datetime, timezone
from typing import Tuple, Optional, Dict, Any

from qwen_dev_cli.agents.base import AgentTask, AgentResponse, BaseAgent
from qwen_dev_cli.agents.justica_agent import JusticaIntegratedAgent
from qwen_dev_cli.agents.sofia_agent import SofiaIntegratedAgent
from qwen_dev_cli.core.observability import get_tracer, trace_operation, get_status_code
from qwen_dev_cli.core.agent_identity import enforce_permission, AgentPermission

logger = logging.getLogger(__name__)
tracer = get_tracer()


def _detect_circular_references(obj: Any, visited: Optional[set] = None, max_depth: int = 100) -> bool:
    """
    Detect circular references in nested objects.

    🔒 SECURITY FIX (AIR GAP #22-23, #48-49): Prevents infinite loops

    Args:
        obj: Object to check
        visited: Set of visited object IDs
        max_depth: Maximum recursion depth

    Returns:
        bool: True if circular reference detected
    """
    if visited is None:
        visited = set()

    if max_depth <= 0:
        logger.warning("Max depth reached in circular reference detection")
        return True

    # Get object ID
    obj_id = id(obj)

    # Check if we've seen this object before
    if obj_id in visited:
        return True

    # Mark as visited
    visited.add(obj_id)

    # Check nested structures
    if isinstance(obj, dict):
        for key, value in obj.items():
            if _detect_circular_references(value, visited.copy(), max_depth - 1):
                return True
    elif isinstance(obj, (list, tuple)):
        for item in obj:
            if _detect_circular_references(item, visited.copy(), max_depth - 1):
                return True

    return False


class GovernancePipeline:
    """
    Governance pipeline using Orchestrator-Worker pattern.

    Principles (from research):
    1. **Narrow Permissions**: "read and route" only for orchestrator
    2. **Context Isolation**: Each agent has independent context window
    3. **Parallel Execution**: Governance checks run simultaneously
    4. **Observability**: OpenTelemetry traces with correlation IDs
    5. **Fail-Safe**: Block by default on error

    Example:
        >>> pipeline = GovernancePipeline(justica, sofia)
        >>> approved, reason, traces = await pipeline.pre_execution_check(
        ...     task, agent_id="executor", risk_level="HIGH"
        ... )
        >>> if approved:
        ...     response = await agent.execute(task)
    """

    def __init__(
        self,
        justica: JusticaIntegratedAgent,
        sofia: SofiaIntegratedAgent,
        enable_governance: bool = True,
        enable_counsel: bool = True,
        enable_observability: bool = True,
        fail_safe: bool = True
    ):
        """
        Initialize governance pipeline.

        Args:
            justica: Justiça governance agent
            sofia: Sofia counselor agent
            enable_governance: Enable Justiça checks
            enable_counsel: Enable Sofia counsel
            enable_observability: Enable OpenTelemetry tracing
            fail_safe: Block on error (recommended: True)

        Raises:
            TypeError: If justica or sofia have wrong type
            ValueError: If justica or sofia are None
        """
        # 🔒 INPUT VALIDATION (AIR GAP #12-15): Validate critical parameters
        if justica is None:
            raise ValueError("justica cannot be None")
        if sofia is None:
            raise ValueError("sofia cannot be None")

        # Type validation (duck typing - check for required methods)
        if not hasattr(justica, 'evaluate_action') and not hasattr(justica, 'execute'):
            raise TypeError(
                f"justica must have 'evaluate_action' or 'execute' method, "
                f"got {type(justica).__name__}"
            )

        if not hasattr(sofia, 'provide_counsel') and not hasattr(sofia, 'execute'):
            raise TypeError(
                f"sofia must have 'provide_counsel' or 'execute' method, "
                f"got {type(sofia).__name__}"
            )

        # Boolean validation
        if not isinstance(enable_governance, bool):
            raise TypeError(f"enable_governance must be bool, got {type(enable_governance).__name__}")
        if not isinstance(enable_counsel, bool):
            raise TypeError(f"enable_counsel must be bool, got {type(enable_counsel).__name__}")
        if not isinstance(enable_observability, bool):
            raise TypeError(f"enable_observability must be bool, got {type(enable_observability).__name__}")
        if not isinstance(fail_safe, bool):
            raise TypeError(f"fail_safe must be bool, got {type(fail_safe).__name__}")

        self.justica = justica
        self.sofia = sofia
        self.enable_governance = enable_governance
        self.enable_counsel = enable_counsel
        self.enable_observability = enable_observability
        self.fail_safe = fail_safe

        logger.info("✓ Governance Pipeline initialized")
        logger.info(f"  - Governance (Justiça): {enable_governance}")
        logger.info(f"  - Counsel (Sofia): {enable_counsel}")
        logger.info(f"  - Observability: {enable_observability}")
        logger.info(f"  - Fail-safe mode: {fail_safe}")

    async def pre_execution_check(
        self,
        task: AgentTask,
        agent_id: str,
        risk_level: str = "MEDIUM"
    ) -> Tuple[bool, Optional[str], Dict[str, Any]]:
        """
        Execute governance checks BEFORE agent action.

        Runs Justiça and Sofia in PARALLEL (Anthropic pattern: 90% faster).

        Args:
            task: The task to be executed
            agent_id: ID of agent requesting execution
            risk_level: Risk level (LOW, MEDIUM, HIGH, CRITICAL)

        Returns:
            Tuple of:
            - approved (bool): True if all checks pass
            - reason (Optional[str]): Blocking reason if not approved
            - traces (Dict): Observability traces

        Raises:
            TypeError: If parameters have wrong type
            ValueError: If parameters are None or invalid

        Example:
            >>> approved, reason, traces = await pipeline.pre_execution_check(
            ...     task, "executor", "HIGH"
            ... )
            >>> if not approved:
            ...     return error_response(reason)
        """
        # 🔒 INPUT VALIDATION (AIR GAP #24-28, #51-52): Validate all parameters
        if task is None:
            raise ValueError("task cannot be None")
        if not isinstance(task, AgentTask):
            raise TypeError(f"task must be AgentTask, got {type(task).__name__}")

        if agent_id is None:
            raise ValueError("agent_id cannot be None")
        if not isinstance(agent_id, str):
            raise TypeError(f"agent_id must be str, got {type(agent_id).__name__}")
        if not agent_id.strip():
            raise ValueError("agent_id cannot be empty")

        if risk_level is None:
            raise ValueError("risk_level cannot be None")
        if not isinstance(risk_level, str):
            raise TypeError(f"risk_level must be str, got {type(risk_level).__name__}")

        # Validate risk_level is one of the allowed values
        valid_risk_levels = {"LOW", "MEDIUM", "HIGH", "CRITICAL"}
        if risk_level not in valid_risk_levels:
            raise ValueError(f"risk_level must be one of {valid_risk_levels}, got '{risk_level}'")

        # 🔒 CIRCULAR REFERENCE CHECK (AIR GAP #22-23, #48-49)
        if _detect_circular_references(task.context):
            raise ValueError("Circular reference detected in task.context - potential infinite loop")

        correlation_id = str(uuid.uuid4())

        with trace_operation(
            "governance_pipeline.pre_execution_check",
            {
                "correlation_id": correlation_id,
                "agent_id": agent_id,
                "risk_level": risk_level
            }
        ) as span:

            traces = {
                "correlation_id": correlation_id,
                "started_at": datetime.now(timezone.utc).isoformat(),
                "agent_id": agent_id,
                "risk_level": risk_level,
                "governance_check": None,
                "counsel_check": None,
                "parallel_execution": True
            }

            try:
                # PARALLEL EXECUTION (Anthropic pattern)
                # Both checks run simultaneously with isolated contexts
                tasks_to_run = []

                if self.enable_governance:
                    tasks_to_run.append(self._run_governance_check(task, agent_id, correlation_id))

                if self.enable_counsel:
                    tasks_to_run.append(self._run_counsel_check(task, agent_id, risk_level, correlation_id))

                # Execute in parallel
                if tasks_to_run:
                    results = await asyncio.gather(*tasks_to_run, return_exceptions=True)

                    # Process governance result
                    if self.enable_governance:
                        gov_result = results[0]
                        if isinstance(gov_result, Exception):
                            if self.fail_safe:
                                traces["governance_check"] = {"error": str(gov_result), "blocked": True}
                                return False, f"Governance check failed: {str(gov_result)}", traces
                        else:
                            traces["governance_check"] = gov_result
                            if not gov_result["approved"]:
                                return False, gov_result["reason"], traces

                    # Process counsel result
                    if self.enable_counsel and len(results) > 1:
                        counsel_result = results[1] if len(results) > 1 else results[0]
                        if isinstance(counsel_result, Exception):
                            logger.warning(f"Counsel check failed: {counsel_result}")
                            # Counsel failures don't block (advisory only)
                        else:
                            traces["counsel_check"] = counsel_result

                traces["completed_at"] = datetime.now(timezone.utc).isoformat()
                traces["approved"] = True

                return True, None, traces

            except Exception as e:
                logger.exception(f"[{correlation_id}] Pipeline error: {e}")
                span.record_exception(e)

                # FAIL-SAFE: Block on unexpected error
                if self.fail_safe:
                    return False, f"Pipeline error (fail-safe): {str(e)}", traces

                # If not fail-safe, allow but log
                logger.error(f"Pipeline error but fail-safe disabled - allowing execution")
                return True, None, traces

    async def _run_governance_check(
        self,
        task: AgentTask,
        agent_id: str,
        correlation_id: str
    ) -> Dict[str, Any]:
        """
        Run Justiça governance check (isolated context).

        This runs in PARALLEL with counsel check.
        """
        with trace_operation(
            "governance.justica_check",
            {"agent": "justica", "correlation_id": correlation_id}
        ) as span:

            # Enforce permission (IAM pattern)
            try:
                enforce_permission("governance", AgentPermission.EVALUATE_GOVERNANCE)
            except PermissionError as e:
                logger.error(f"Permission denied: {e}")
                return {
                    "agent": "justica",
                    "approved": False,
                    "reason": str(e),
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }

            # Evaluate action
            verdict = await self.justica.evaluate_action(
                agent_id=agent_id,
                action_type="agent_task",  # Fixed: was action_description (AIR GAP!)
                content=task.request,
                context={
                    **task.context,
                    "correlation_id": correlation_id
                }
            )

            result = {
                "agent": "justica",
                "approved": verdict.approved,  # Fixed: was verdict.success (AIR GAP!)
                "reason": verdict.reasoning if not verdict.approved else None,
                "trust_score": getattr(verdict, "trust_score", 0.0),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

            if not verdict.approved:
                span.set_attribute("blocked", True)

            return result

    async def _run_counsel_check(
        self,
        task: AgentTask,
        agent_id: str,
        risk_level: str,
        correlation_id: str
    ) -> Dict[str, Any]:
        """
        Run Sofia counsel check (isolated context).

        This runs in PARALLEL with governance check.
        Only triggers for HIGH/CRITICAL risk or detected dilemmas.
        """
        with trace_operation(
            "governance.sofia_check",
            {"agent": "sofia", "correlation_id": correlation_id}
        ) as span:

            # Enforce permission (IAM pattern)
            try:
                enforce_permission("counselor", AgentPermission.PROVIDE_COUNSEL)
            except PermissionError as e:
                logger.error(f"Permission denied: {e}")
                return {
                    "agent": "sofia",
                    "triggered": False,
                    "reason": str(e),
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }

            # Check if counsel should trigger
            should_counsel, reason = self.sofia.should_trigger_counsel(task.request)

            result = {
                "agent": "sofia",
                "triggered": False,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

            # Only provide counsel for HIGH/CRITICAL risk OR detected dilemmas
            if should_counsel and risk_level in ["HIGH", "CRITICAL"]:
                counsel = await self.sofia.pre_execution_counsel(
                    action_description=task.request,
                    risk_level=risk_level,
                    agent_id=agent_id,
                    context={
                        **task.context,
                        "correlation_id": correlation_id
                    }
                )

                result["triggered"] = True
                result["counsel_type"] = counsel.counsel_type
                result["confidence"] = counsel.confidence
                result["requires_professional"] = counsel.requires_professional
                result["counsel_preview"] = counsel.counsel[:200]  # First 200 chars

                span.set_attribute("triggered", True)
                span.set_attribute("requires_professional", counsel.requires_professional)

                # ESCALATE if professional help required
                if counsel.requires_professional:
                    logger.warning(f"[{correlation_id}] Professional referral required")
                    # TODO: Implement escalation mechanism

            return result

    async def execute_with_governance(
        self,
        agent: BaseAgent,
        task: AgentTask,
        risk_level: str = "MEDIUM"
    ) -> AgentResponse:
        """
        Execute agent with complete governance pipeline.

        Flow:
        1. Pre-execution checks (parallel: Justiça + Sofia)
        2. Execute agent (if approved)
        3. Post-execution metrics (background task)

        Args:
            agent: The agent to execute
            task: Task to execute
            risk_level: Risk level for pre-execution counsel

        Returns:
            AgentResponse with execution result + governance metadata

        Example:
            >>> response = await pipeline.execute_with_governance(
            ...     executor_agent, task, risk_level="HIGH"
            ... )
            >>> if not response.success:
            ...     print(f"Blocked: {response.error}")
        """
        correlation_id = str(uuid.uuid4())

        with trace_operation(
            "execute_with_governance",
            {
                "correlation_id": correlation_id,
                "agent_id": agent.role.value,
                "risk_level": risk_level
            }
        ) as span:

            # PHASE 1: Pre-execution checks (PARALLEL)
            approved, reason, traces = await self.pre_execution_check(
                task=task,
                agent_id=agent.role.value,
                risk_level=risk_level
            )

            if not approved:
                logger.warning(f"[{correlation_id}] Action blocked: {reason}")
                span.set_attribute("blocked", True)

                return AgentResponse(
                    success=False,
                    reasoning="Governance pipeline blocked action",
                    error=reason,
                    data={
                        "governance_traces": traces,
                        "blocked_by": "governance_pipeline",
                        "correlation_id": correlation_id
                    }
                )

            # PHASE 2: Execute agent (context isolated)
            try:
                with trace_operation(f"agent.{agent.role.value}.execute"):
                    response = await agent.execute(task)

                # Add governance metadata to response
                if response.data is None:
                    response.data = {}
                response.data["governance_traces"] = traces
                response.data["correlation_id"] = correlation_id

                # PHASE 3: Post-execution metrics (background task, non-blocking)
                asyncio.create_task(
                    self._update_metrics_async(
                        agent_id=agent.role.value,
                        success=response.success,
                        correlation_id=correlation_id
                    )
                )

                return response

            except Exception as e:
                logger.exception(f"[{correlation_id}] Agent execution failed: {e}")
                span.record_exception(e)

                return AgentResponse(
                    success=False,
                    reasoning=f"Agent execution failed: {str(e)}",
                    error=str(e),
                    data={
                        "correlation_id": correlation_id,
                        "governance_traces": traces
                    }
                )

    async def _update_metrics_async(
        self,
        agent_id: str,
        success: bool,
        correlation_id: str
    ) -> None:
        """
        Update metrics in background (non-blocking).

        This runs as a background task to avoid blocking main execution.
        """
        try:
            # Update trust scores in Justiça
            if success:
                logger.debug(f"[{correlation_id}] Updating metrics for {agent_id} (success)")
            else:
                logger.debug(f"[{correlation_id}] Updating metrics for {agent_id} (failure)")

            # TODO: Implement actual metrics update
            # await self.justica.update_trust_score(agent_id, success)

        except Exception as e:
            logger.error(f"Failed to update metrics: {e}")
