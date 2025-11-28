"""
AgentProtocol - Standardized Inter-Agent Communication
Pipeline de Diamante - Camada 2: GOVERNANCE GATE

Addresses: ISSUE-071, ISSUE-072, ISSUE-073 (Agent handoff and communication)

Implements standardized agent communication:
- ExecutionPlan schema (Planner → Executor)
- ContextBundle for propagation
- ReviewFeedback for corrections
- HandoffValidation

Design Philosophy:
- Explicit contracts between agents
- Strong typing for all messages
- Validation at boundaries
- Traceable communication
"""

from __future__ import annotations

import uuid
import time
from typing import Any, Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class MessagePriority(Enum):
    """Priority levels for messages."""
    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3


class MessageType(Enum):
    """Types of inter-agent messages."""
    REQUEST = "request"
    RESPONSE = "response"
    HANDOFF = "handoff"
    FEEDBACK = "feedback"
    BROADCAST = "broadcast"
    ACK = "acknowledgment"


class AgentRole(Enum):
    """Standard agent roles in the system."""
    PLANNER = "planner"
    EXECUTOR = "executor"
    REVIEWER = "reviewer"
    ARCHITECT = "architect"
    EXPLORER = "explorer"
    DEBUGGER = "debugger"
    DEVOPS = "devops"
    JUSTICA = "justica"
    SOFIA = "sofia"
    MAESTRO = "maestro"


class TaskStatus(Enum):
    """Status of a task in execution."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class StreamingChunkType(Enum):
    """
    Standard types for streaming chunks from agents.

    CRITICAL: All agents MUST use these types when yielding streaming chunks.
    This ensures compatibility with the UI rendering pipeline.

    Usage:
        yield StreamingChunk(type=StreamingChunkType.THINKING, data="token")
        yield StreamingChunk(type=StreamingChunkType.STATUS, data="Loading...")
        yield StreamingChunk(type=StreamingChunkType.RESULT, data=final_result)
    """
    THINKING = "thinking"      # LLM tokens being generated (display as-is)
    STATUS = "status"          # Status messages (display with newline)
    COMMAND = "command"        # Command to execute (syntax highlight)
    EXECUTING = "executing"    # Currently executing (show spinner)
    RESULT = "result"          # Final result (format appropriately)
    ERROR = "error"            # Error message (display in red)
    VERDICT = "verdict"        # Governance verdict (JusticaAgent)
    REASONING = "reasoning"    # Reasoning steps (collapse in UI)
    METRICS = "metrics"        # Performance metrics (table format)


@dataclass
class StreamingChunk:
    """
    Standardized streaming chunk for UI rendering.

    All agents SHOULD yield StreamingChunk instances instead of raw dicts.
    The AgentManager._normalize_streaming_chunk() handles legacy dict formats,
    but using StreamingChunk ensures type safety and IDE support.

    Examples:
        # Good - Type-safe
        yield StreamingChunk(type=StreamingChunkType.THINKING, data="Hello")

        # Legacy (still works but discouraged)
        yield {"type": "thinking", "data": "Hello"}

    Note:
        The 'content' key is DEPRECATED. Use 'data' for all chunk payloads.
    """
    type: StreamingChunkType
    data: Any
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to legacy dict format."""
        return {
            "type": self.type.value,
            "data": self.data,
            **({"metadata": self.metadata} if self.metadata else {})
        }

    def __str__(self) -> str:
        """String representation for display."""
        if self.type == StreamingChunkType.THINKING:
            return str(self.data)
        elif self.type == StreamingChunkType.STATUS:
            return f"{self.data}\n"
        elif self.type == StreamingChunkType.ERROR:
            return f"❌ {self.data}\n"
        elif self.type == StreamingChunkType.RESULT:
            if hasattr(self.data, 'to_markdown'):
                return self.data.to_markdown()
            elif hasattr(self.data, 'data'):
                return str(self.data.data)
            return str(self.data)
        else:
            return str(self.data)


@dataclass
class AgentIdentity:
    """Identity of an agent in the system."""
    agent_id: str
    role: AgentRole
    capabilities: Set[str] = field(default_factory=set)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def can_handle(self, capability: str) -> bool:
        """Check if agent can handle a capability."""
        return capability in self.capabilities


@dataclass
class MessageEnvelope:
    """Standard message envelope for all agent communication."""
    message_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: float = field(default_factory=time.time)
    message_type: MessageType = MessageType.REQUEST
    priority: MessagePriority = MessagePriority.NORMAL

    sender: Optional[AgentIdentity] = None
    receiver: Optional[AgentIdentity] = None

    correlation_id: Optional[str] = None  # Links related messages
    reply_to: Optional[str] = None  # For responses

    ttl: Optional[float] = None  # Time-to-live in seconds

    def is_expired(self) -> bool:
        """Check if message has expired."""
        if self.ttl is None:
            return False
        return time.time() - self.timestamp > self.ttl


@dataclass
class ExecutionStep:
    """A single step in an execution plan."""
    step_id: str
    description: str
    action: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)  # step_ids this depends on
    estimated_duration: Optional[float] = None
    rollback_action: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExecutionPlan:
    """
    Structured execution plan from Planner to Executor.

    This is the standard format for communicating work to be done.
    """
    plan_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: float = field(default_factory=time.time)
    created_by: Optional[AgentIdentity] = None

    title: str = ""
    description: str = ""
    goal: str = ""

    steps: List[ExecutionStep] = field(default_factory=list)
    context: Dict[str, Any] = field(default_factory=dict)

    # Validation requirements
    requires_approval: bool = False
    governance_checked: bool = False

    # Execution constraints
    max_duration: Optional[float] = None
    max_retries: int = 3

    def validate(self) -> Tuple[bool, List[str]]:
        """Validate plan structure."""
        errors = []

        if not self.title:
            errors.append("Plan must have a title")

        if not self.steps:
            errors.append("Plan must have at least one step")

        # Check for circular dependencies
        step_ids = {s.step_id for s in self.steps}
        for step in self.steps:
            for dep in step.dependencies:
                if dep not in step_ids:
                    errors.append(f"Step {step.step_id} depends on unknown step {dep}")

        return len(errors) == 0, errors

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "plan_id": self.plan_id,
            "created_at": self.created_at,
            "title": self.title,
            "description": self.description,
            "goal": self.goal,
            "steps": [
                {
                    "step_id": s.step_id,
                    "description": s.description,
                    "action": s.action,
                    "parameters": s.parameters,
                    "dependencies": s.dependencies,
                }
                for s in self.steps
            ],
            "context": self.context,
        }


@dataclass
class ContextBundle:
    """
    Context bundle for propagation between agents.

    Contains all context needed for an agent to understand and continue work.
    """
    bundle_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: float = field(default_factory=time.time)

    # File context
    working_directory: str = ""
    relevant_files: List[str] = field(default_factory=list)
    file_contents: Dict[str, str] = field(default_factory=dict)

    # Conversation context
    conversation_summary: str = ""
    recent_messages: List[Dict[str, str]] = field(default_factory=list)
    user_intent: str = ""

    # Execution context
    completed_steps: List[str] = field(default_factory=list)
    pending_steps: List[str] = field(default_factory=list)
    current_state: Dict[str, Any] = field(default_factory=dict)

    # Error context
    errors_encountered: List[Dict[str, Any]] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    # Custom context
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_file(self, path: str, content: Optional[str] = None) -> None:
        """Add a relevant file to context."""
        if path not in self.relevant_files:
            self.relevant_files.append(path)
        if content:
            self.file_contents[path] = content

    def add_error(self, error: str, context: Optional[Dict[str, Any]] = None) -> None:
        """Add an error to context."""
        self.errors_encountered.append({
            "error": error,
            "timestamp": time.time(),
            "context": context or {},
        })


@dataclass
class ReviewFeedback:
    """
    Feedback from Reviewer to Executor.

    Used to communicate corrections, suggestions, and approval status.
    """
    feedback_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: float = field(default_factory=time.time)
    reviewer: Optional[AgentIdentity] = None

    # Review result
    approved: bool = False
    requires_changes: bool = False
    blocking_issues: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)

    # Specific file feedback
    file_feedback: Dict[str, List[str]] = field(default_factory=dict)

    # Quality metrics
    code_quality_score: Optional[float] = None  # 0-100
    test_coverage: Optional[float] = None
    security_issues: List[str] = field(default_factory=list)

    # Re-execution guidance
    retry_steps: List[str] = field(default_factory=list)
    skip_steps: List[str] = field(default_factory=list)

    def add_blocking_issue(self, issue: str) -> None:
        """Add a blocking issue."""
        self.blocking_issues.append(issue)
        self.approved = False
        self.requires_changes = True

    def add_suggestion(self, suggestion: str) -> None:
        """Add a non-blocking suggestion."""
        self.suggestions.append(suggestion)


@dataclass
class HandoffRequest:
    """
    Request to hand off work to another agent.

    Used when one agent needs to delegate or transfer work.
    """
    handoff_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: float = field(default_factory=time.time)

    from_agent: Optional[AgentIdentity] = None
    to_role: AgentRole = AgentRole.EXECUTOR  # Role, not specific agent

    reason: str = ""
    plan: Optional[ExecutionPlan] = None
    context: Optional[ContextBundle] = None
    feedback: Optional[ReviewFeedback] = None

    # Handoff requirements
    required_capabilities: Set[str] = field(default_factory=set)
    deadline: Optional[float] = None

    def validate(self) -> Tuple[bool, List[str]]:
        """Validate handoff request."""
        errors = []

        if not self.reason:
            errors.append("Handoff must have a reason")

        if self.plan is None and self.context is None:
            errors.append("Handoff must include plan or context")

        return len(errors) == 0, errors


class ProtocolValidator:
    """Validates protocol messages and structures."""

    @staticmethod
    def validate_plan(plan: ExecutionPlan) -> Tuple[bool, List[str]]:
        """Validate execution plan."""
        return plan.validate()

    @staticmethod
    def validate_handoff(handoff: HandoffRequest) -> Tuple[bool, List[str]]:
        """Validate handoff request."""
        return handoff.validate()

    @staticmethod
    def validate_envelope(envelope: MessageEnvelope) -> Tuple[bool, List[str]]:
        """Validate message envelope."""
        errors = []

        if envelope.is_expired():
            errors.append("Message has expired")

        if envelope.sender is None:
            errors.append("Message must have a sender")

        return len(errors) == 0, errors


class AgentProtocol:
    """
    Manages standardized agent communication.

    Provides:
    - Message creation and validation
    - Plan construction helpers
    - Context bundling
    - Feedback formatting
    """

    def __init__(self, agent_identity: AgentIdentity):
        """
        Initialize protocol handler.

        Args:
            agent_identity: Identity of the owning agent
        """
        self.identity = agent_identity
        self.validator = ProtocolValidator()

    def create_plan(
        self,
        title: str,
        goal: str,
        steps: List[Dict[str, Any]],
        **kwargs
    ) -> ExecutionPlan:
        """
        Create a validated execution plan.

        Args:
            title: Plan title
            goal: Overall goal
            steps: List of step definitions

        Returns:
            ExecutionPlan ready for handoff
        """
        execution_steps = []
        for i, step in enumerate(steps):
            exec_step = ExecutionStep(
                step_id=step.get("id", f"step_{i+1}"),
                description=step.get("description", ""),
                action=step.get("action", ""),
                parameters=step.get("parameters", {}),
                dependencies=step.get("dependencies", []),
            )
            execution_steps.append(exec_step)

        plan = ExecutionPlan(
            created_by=self.identity,
            title=title,
            goal=goal,
            steps=execution_steps,
            **kwargs
        )

        # Validate
        is_valid, errors = plan.validate()
        if not is_valid:
            raise ValueError(f"Invalid plan: {errors}")

        return plan

    def create_context_bundle(
        self,
        working_directory: str,
        files: Optional[List[str]] = None,
        **kwargs
    ) -> ContextBundle:
        """
        Create a context bundle for handoff.

        Args:
            working_directory: Current working directory
            files: List of relevant file paths

        Returns:
            ContextBundle ready for handoff
        """
        bundle = ContextBundle(
            working_directory=working_directory,
            relevant_files=files or [],
            **kwargs
        )

        return bundle

    def create_feedback(
        self,
        approved: bool,
        **kwargs
    ) -> ReviewFeedback:
        """
        Create review feedback.

        Args:
            approved: Whether the review passed

        Returns:
            ReviewFeedback ready to send
        """
        return ReviewFeedback(
            reviewer=self.identity,
            approved=approved,
            **kwargs
        )

    def create_handoff(
        self,
        to_role: AgentRole,
        reason: str,
        plan: Optional[ExecutionPlan] = None,
        context: Optional[ContextBundle] = None,
    ) -> HandoffRequest:
        """
        Create a handoff request.

        Args:
            to_role: Target agent role
            reason: Reason for handoff
            plan: Execution plan (optional)
            context: Context bundle (optional)

        Returns:
            HandoffRequest ready to send
        """
        handoff = HandoffRequest(
            from_agent=self.identity,
            to_role=to_role,
            reason=reason,
            plan=plan,
            context=context,
        )

        # Validate
        is_valid, errors = handoff.validate()
        if not is_valid:
            raise ValueError(f"Invalid handoff: {errors}")

        return handoff

    def create_message(
        self,
        message_type: MessageType,
        receiver: Optional[AgentIdentity] = None,
        **kwargs
    ) -> MessageEnvelope:
        """
        Create a message envelope.

        Args:
            message_type: Type of message
            receiver: Target agent (optional)

        Returns:
            MessageEnvelope ready to send
        """
        return MessageEnvelope(
            message_type=message_type,
            sender=self.identity,
            receiver=receiver,
            **kwargs
        )


# Convenience factory functions

def create_planner_identity(agent_id: str = "planner") -> AgentIdentity:
    """Create a planner agent identity."""
    return AgentIdentity(
        agent_id=agent_id,
        role=AgentRole.PLANNER,
        capabilities={"plan", "analyze", "decompose"}
    )


def create_executor_identity(agent_id: str = "executor") -> AgentIdentity:
    """Create an executor agent identity."""
    return AgentIdentity(
        agent_id=agent_id,
        role=AgentRole.EXECUTOR,
        capabilities={"execute", "file_ops", "command"}
    )


def create_reviewer_identity(agent_id: str = "reviewer") -> AgentIdentity:
    """Create a reviewer agent identity."""
    return AgentIdentity(
        agent_id=agent_id,
        role=AgentRole.REVIEWER,
        capabilities={"review", "validate", "quality"}
    )


# Export all public symbols
__all__ = [
    'MessagePriority',
    'MessageType',
    'AgentRole',
    'TaskStatus',
    'StreamingChunkType',
    'StreamingChunk',
    'AgentIdentity',
    'MessageEnvelope',
    'ExecutionStep',
    'ExecutionPlan',
    'ContextBundle',
    'ReviewFeedback',
    'HandoffRequest',
    'ProtocolValidator',
    'AgentProtocol',
    'create_planner_identity',
    'create_executor_identity',
    'create_reviewer_identity',
]
