"""
DevSquad: Multi-Agent Orchestration System.

This module coordinates the 5 specialist agents (Architect, Explorer, Planner,
Refactorer, Reviewer) to handle complex software development tasks through
agentic thinking and federation of specialists.

Architecture:
    DevSquad (orchestrator)
        ├── Phase 1: Architecture (Architect)
        ├── Phase 2: Exploration (Explorer)
        ├── Phase 3: Planning (Planner)
        ├── Phase 4: Execution (Refactorer)
        └── Phase 5: Review (Reviewer)

Philosophy (Boris Cherny):
    "The best architecture is the one where each component does ONE thing well."
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from ..agents.architect import ArchitectAgent
from ..agents.base import AgentResponse, AgentTask, TaskStatus
from ..agents.explorer import ExplorerAgent
from ..agents.planner import PlannerAgent
from ..agents.refactorer import RefactorerAgent
from ..agents.reviewer import ReviewerAgent
from .memory import MemoryManager


class WorkflowPhase(str, Enum):
    """5-phase workflow stages."""
    ARCHITECTURE = "architecture"
    EXPLORATION = "exploration"
    PLANNING = "planning"
    EXECUTION = "execution"
    REVIEW = "review"


class WorkflowStatus(str, Enum):
    """Workflow execution status."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    AWAITING_APPROVAL = "awaiting_approval"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class PhaseResult(BaseModel):
    """Result of a single workflow phase.
    
    Attributes:
        phase: Workflow phase identifier
        success: Whether phase succeeded
        agent_response: Underlying agent execution response
        started_at: Phase start timestamp
        completed_at: Phase completion timestamp
        duration_seconds: Execution duration
    """
    phase: WorkflowPhase
    success: bool
    agent_response: AgentResponse
    started_at: datetime
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None


class WorkflowResult(BaseModel):
    """Complete workflow execution result.
    
    Attributes:
        workflow_id: Unique workflow identifier
        request: Original user request
        status: Overall workflow status
        phases: Results from each phase
        artifacts: Generated artifacts (files, reports, etc.)
        total_duration_seconds: Total execution time
        metadata: Arbitrary metadata
    """
    workflow_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    request: str
    status: WorkflowStatus
    phases: List[PhaseResult] = Field(default_factory=list)
    artifacts: Dict[str, Any] = Field(default_factory=dict)
    total_duration_seconds: float = 0.0
    metadata: Dict[str, Any] = Field(default_factory=dict)


class DevSquad:
    """Multi-agent orchestration system.
    
    Coordinates 5 specialist agents to handle complex development tasks:
        1. Architect: Technical feasibility analysis
        2. Explorer: Intelligent context gathering
        3. Planner: Atomic execution plan generation
        4. Refactorer: Code execution with self-correction
        5. Reviewer: Quality validation and approval
    
    Workflow:
        User Request
            → Architect (approve/veto)
            → Explorer (gather context)
            → Planner (generate plan)
            → [HUMAN GATE] (approval required)
            → Refactorer (execute plan)
            → Reviewer (validate quality)
            → Done / Request Changes
    """
    
    def __init__(
        self,
        llm_client: Any,
        mcp_client: Any,
        require_human_approval: bool = True,
    ):
        """Initialize DevSquad orchestrator.
        
        Args:
            llm_client: LLM provider client (Gemini, Claude, etc.)
            mcp_client: MCP client for tool execution
            require_human_approval: Whether to require human approval before execution
        """
        self.llm_client = llm_client
        self.mcp_client = mcp_client
        self.require_human_approval = require_human_approval
        
        # Initialize specialist agents
        self.architect = ArchitectAgent(llm_client, mcp_client)
        self.explorer = ExplorerAgent(llm_client, mcp_client)
        self.planner = PlannerAgent(llm_client, mcp_client)
        self.refactorer = RefactorerAgent(llm_client, mcp_client)
        self.reviewer = ReviewerAgent(llm_client, mcp_client)
    
    async def execute_workflow(
        self,
        request: str,
        context: Optional[Dict[str, Any]] = None,
        approval_callback: Optional[Any] = None,
    ) -> WorkflowResult:
        """Execute complete 5-phase workflow.
        
        Args:
            request: User request description
            context: Optional context dictionary
            approval_callback: Optional callback for human approval
                              (must return bool or raise exception to cancel)
        
        Returns:
            WorkflowResult with phase results and artifacts
        """
        workflow_id = str(uuid.uuid4())
        session_id = f"squad_{workflow_id[:8]}"
        workflow_start = datetime.now()
        
        result = WorkflowResult(
            workflow_id=workflow_id,
            request=request,
            status=WorkflowStatus.IN_PROGRESS,
        )
        
        try:
            # Phase 1: Architecture Analysis
            arch_result = await self._phase_architecture(
                request, context or {}, session_id
            )
            result.phases.append(arch_result)
            
            if arch_result.success == False:
                result.status = WorkflowStatus.FAILED
                return self._finalize_workflow(result, workflow_start)
            
            # Check if architect vetoed
            arch_output = arch_result.agent_response.data
            if not arch_output.get("approved", False):
                result.status = WorkflowStatus.FAILED
                result.metadata["veto_reason"] = arch_output.get("reasoning", "Unknown")
                return self._finalize_workflow(result, workflow_start)
            
            # Phase 2: Context Exploration
            explore_result = await self._phase_exploration(
                request, arch_output, session_id
            )
            result.phases.append(explore_result)
            
            if explore_result.success == False:
                result.status = WorkflowStatus.FAILED
                return self._finalize_workflow(result, workflow_start)
            
            # Phase 3: Execution Planning
            plan_result = await self._phase_planning(
                request, explore_result.agent_response.data, session_id
            )
            result.phases.append(plan_result)
            
            if plan_result.success == False:
                result.status = WorkflowStatus.FAILED
                return self._finalize_workflow(result, workflow_start)
            
            # Human Gate: Approval Required
            if self.require_human_approval:
                result.status = WorkflowStatus.AWAITING_APPROVAL
                
                if approval_callback:
                    plan_output = plan_result.agent_response.data
                    approved = await self._request_approval(
                        approval_callback, plan_output.get("plan", {})
                    )
                    
                    if not approved:
                        result.status = WorkflowStatus.CANCELLED
                        result.metadata["cancellation_reason"] = "User rejected plan"
                        return self._finalize_workflow(result, workflow_start)
                else:
                    # No callback provided, pause here
                    result.metadata["awaiting_manual_approval"] = True
                    return self._finalize_workflow(result, workflow_start)
            
            result.status = WorkflowStatus.IN_PROGRESS
            
            # Phase 4: Code Execution
            exec_result = await self._phase_execution(
                plan_result.agent_response.data, session_id
            )
            result.phases.append(exec_result)
            
            if exec_result.success == False:
                result.status = WorkflowStatus.FAILED
                return self._finalize_workflow(result, workflow_start)
            
            # Phase 5: Quality Review
            review_result = await self._phase_review(
                exec_result.agent_response.data, session_id
            )
            result.phases.append(review_result)
            
            if review_result.success == False:
                result.status = WorkflowStatus.FAILED
                return self._finalize_workflow(result, workflow_start)
            
            # Check if reviewer approved
            review_output = review_result.agent_response.data
            if not review_output.get("report", {}).get("approved", False):
                result.status = WorkflowStatus.FAILED
                result.metadata["review_failed"] = True
                result.metadata["grade"] = review_output.get("report", {}).get("grade", "F")
            else:
                result.status = WorkflowStatus.COMPLETED
                result.artifacts = self._collect_artifacts(result.phases)
            
            return self._finalize_workflow(result, workflow_start)
        
        except Exception as e:
            result.status = WorkflowStatus.FAILED
            result.metadata["error"] = str(e)
            return self._finalize_workflow(result, workflow_start)
    
    async def _phase_architecture(
        self, request: str, context: Dict[str, Any], session_id: str
    ) -> PhaseResult:
        """Phase 1: Architecture analysis with Architect agent."""
        phase_start = datetime.now()
        
        task = AgentTask(
            request=request,
            context=context,
            session_id=session_id,
        )
        
        agent_response = await self.architect.execute(task)
        phase_end = datetime.now()
        
        return PhaseResult(
            phase=WorkflowPhase.ARCHITECTURE,
            success=agent_response.success,
            agent_response=agent_response,
            started_at=phase_start,
            completed_at=phase_end,
            duration_seconds=(phase_end - phase_start).total_seconds(),
        )
    
    async def _phase_exploration(
        self, request: str, arch_output: Dict[str, Any], session_id: str
    ) -> PhaseResult:
        """Phase 2: Context exploration with Explorer agent."""
        phase_start = datetime.now()
        
        # Pass architecture plan to explorer
        context = {
            "architecture": arch_output.get("architecture", {}),
            "project_type": arch_output.get("project_type"),
        }
        
        task = AgentTask(
            request=request,
            context=context,
            session_id=session_id,
        )
        
        agent_response = await self.explorer.execute(task)
        phase_end = datetime.now()
        
        return PhaseResult(
            phase=WorkflowPhase.EXPLORATION,
            success=agent_response.success,
            agent_response=agent_response,
            started_at=phase_start,
            completed_at=phase_end,
            duration_seconds=(phase_end - phase_start).total_seconds(),
        )
    
    async def _phase_planning(
        self, request: str, explore_output: Dict[str, Any], session_id: str
    ) -> PhaseResult:
        """Phase 3: Execution planning with Planner agent."""
        phase_start = datetime.now()
        
        # Pass explored context to planner
        context = {
            "context_map": explore_output.get("context", {}),
            "relevant_files": explore_output.get("files", []),
        }
        
        task = AgentTask(
            request=request,
            context=context,
            session_id=session_id,
        )
        
        agent_response = await self.planner.execute(task)
        phase_end = datetime.now()
        
        return PhaseResult(
            phase=WorkflowPhase.PLANNING,
            success=agent_response.success,
            agent_response=agent_response,
            started_at=phase_start,
            completed_at=phase_end,
            duration_seconds=(phase_end - phase_start).total_seconds(),
        )
    
    async def _phase_execution(
        self, plan_output: Dict[str, Any], session_id: str
    ) -> PhaseResult:
        """Phase 4: Code execution with Refactorer agent."""
        phase_start = datetime.now()
        
        # Extract execution plan
        plan = plan_output.get("plan", {})
        
        task = AgentTask(
            request="Execute the planned changes",
            context={"plan": plan},
            session_id=session_id,
        )
        
        agent_response = await self.refactorer.execute(task)
        phase_end = datetime.now()
        
        return PhaseResult(
            phase=WorkflowPhase.EXECUTION,
            success=agent_response.success,
            agent_response=agent_response,
            started_at=phase_start,
            completed_at=phase_end,
            duration_seconds=(phase_end - phase_start).total_seconds(),
        )
    
    async def _phase_review(
        self, exec_output: Dict[str, Any], session_id: str
    ) -> PhaseResult:
        """Phase 5: Quality review with Reviewer agent."""
        phase_start = datetime.now()
        
        # Extract changed files from execution
        changed_files = exec_output.get("modified_files", [])
        
        task = AgentTask(
            request="Review code changes for quality",
            context={"files": changed_files},
            session_id=session_id,
        )
        
        agent_response = await self.reviewer.execute(task)
        phase_end = datetime.now()
        
        return PhaseResult(
            phase=WorkflowPhase.REVIEW,
            success=agent_response.success,
            agent_response=agent_response,
            started_at=phase_start,
            completed_at=phase_end,
            duration_seconds=(phase_end - phase_start).total_seconds(),
        )
    
    async def _request_approval(
        self, callback: Any, plan: Dict[str, Any]
    ) -> bool:
        """Request human approval for execution plan.
        
        Args:
            callback: Approval callback function or coroutine
            plan: Execution plan dictionary
        
        Returns:
            True if approved, False if rejected
        """
        try:
            if callable(callback):
                result = callback(plan)
                if hasattr(result, '__await__'):
                    result = await result
                return bool(result)
            return False
        except Exception:
            return False  # Reject on error
    
    def _collect_artifacts(self, phases: List[PhaseResult]) -> Dict[str, Any]:
        """Collect artifacts from all phases.
        
        Args:
            phases: List of phase results
        
        Returns:
            Dictionary of artifacts by phase
        """
        artifacts = {}
        
        for phase_result in phases:
            phase_name = phase_result.phase.value
            artifacts[phase_name] = phase_result.agent_response.data
        
        return artifacts
    
    def _finalize_workflow(
        self, result: WorkflowResult, start_time: datetime
    ) -> WorkflowResult:
        """Finalize workflow result with timing.
        
        Args:
            result: Workflow result to finalize
            start_time: Workflow start timestamp
        
        Returns:
            Finalized workflow result
        """
        end_time = datetime.now()
        result.total_duration_seconds = (end_time - start_time).total_seconds()
        return result
    
    def get_phase_summary(self, workflow_result: WorkflowResult) -> str:
        """Generate human-readable phase summary.
        
        Args:
            workflow_result: Completed workflow result
        
        Returns:
            Formatted summary string
        """
        lines = [
            f"Workflow {workflow_result.workflow_id[:8]}",
            f"Status: {workflow_result.success.value}",
            f"Duration: {workflow_result.total_duration_seconds:.1f}s",
            "",
            "Phases:",
        ]
        
        for phase_result in workflow_result.phases:
            status_icon = "✅" if phase_result.success == True else "❌"
            lines.append(
                f"  {status_icon} {phase_result.phase.value.capitalize()}: "
                f"{phase_result.duration_seconds:.1f}s"
            )
        
        if workflow_result.success == WorkflowStatus.COMPLETED:
            lines.append("")
            lines.append("Artifacts: " + ", ".join(workflow_result.artifacts.keys()))
        
        return "\n".join(lines)
