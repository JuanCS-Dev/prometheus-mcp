"""
Integration Layer - Type Definitions.

Boris Cherny: "The type system is documentation that can't lie."

This module defines the contracts between:
- Shell ↔ Agents
- Shell ↔ Tools  
- Shell ↔ Intelligence
- Shell ↔ TUI

All integrations flow through these types.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Protocol, TypedDict
from uuid import uuid4


# ============================================================================
# INTENT SYSTEM
# ============================================================================

class IntentType(str, Enum):
    """Categorized user intent (mapped to agents)."""

    # Agent-mapped intents
    ARCHITECTURE = "architecture"  # → ArchitectAgent
    EXPLORATION = "exploration"    # → ExplorerAgent
    PLANNING = "planning"          # → PlannerAgent
    REFACTORING = "refactoring"    # → RefactorerAgent
    REVIEW = "review"              # → ReviewerAgent
    SECURITY = "security"          # → SecurityAgent
    PERFORMANCE = "performance"    # → PerformanceAgent
    TESTING = "testing"            # → TestingAgent
    DOCUMENTATION = "documentation"  # → DocumentationAgent

    # Direct actions (no agent)
    FILE_OPERATION = "file_operation"
    GIT_OPERATION = "git_operation"
    SHELL_COMMAND = "shell_command"
    SEARCH = "search"

    # Conversational
    QUESTION = "question"
    GENERAL = "general"


@dataclass(frozen=True)
class Intent:
    """Detected user intent with confidence."""

    type: IntentType
    confidence: float  # 0.0 - 1.0
    keywords: List[str] = field(default_factory=list)
    context_hints: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate confidence range."""
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"Confidence must be [0.0, 1.0], got {self.confidence}")


# ============================================================================
# AGENT INTEGRATION
# ============================================================================

class AgentResponse(TypedDict):
    """Standard agent response format."""

    success: bool
    output: str
    metadata: Dict[str, Any]
    execution_time_ms: float
    tokens_used: Optional[int]


class AgentInvoker(Protocol):
    """Protocol for agent invocation.
    
    Any class implementing this can be called by the integration layer.
    """

    async def invoke(
        self,
        request: str,
        context: Dict[str, Any]
    ) -> AgentResponse:
        """Invoke agent with request and context.
        
        Args:
            request: User's request string
            context: Rich context dictionary
            
        Returns:
            AgentResponse with results
        """
        ...


# ============================================================================
# TOOL INTEGRATION
# ============================================================================

class ToolCategory(str, Enum):
    """Tool categorization for organization."""

    FILE = "file"
    GIT = "git"
    SHELL = "shell"
    SEARCH = "search"
    CONTEXT = "context"
    TERMINAL = "terminal"


@dataclass(frozen=True)
class ToolDefinition:
    """Gemini-compatible tool definition.
    
    Maps our internal tools to Gemini function calling schema.
    """

    name: str
    description: str
    category: ToolCategory
    parameters: Dict[str, Any]  # JSON Schema format
    requires_confirmation: bool = False
    destructive: bool = False

    def to_gemini_schema(self) -> Dict[str, Any]:
        """Convert to Gemini function declaration format."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters
        }


@dataclass
class ToolExecutionResult:
    """Result of tool execution."""

    success: bool
    output: str
    error: Optional[str] = None
    execution_time_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


# ============================================================================
# CONTEXT INTEGRATION
# ============================================================================

# NOTE: We use the existing RichContext from intelligence/context_enhanced.py
# This provides compatibility with existing infrastructure while maintaining
# our integration layer abstraction.

def context_to_prompt_string(context: Any) -> str:
    """Format context as string for system prompt injection.
    
    Args:
        context: RichContext from intelligence.context_enhanced
        
    Returns:
        Formatted string for system prompt
    """
    lines = [
        "# Current Context",
        ""
    ]

    # Working directory
    if hasattr(context, 'working_directory'):
        lines.append(f"**Working Directory:** `{context.working_directory}`")

    # Git status
    if hasattr(context, 'git_status') and context.git_status:
        git = context.git_status
        lines.append("")
        lines.append("## Git Status")

        if git.branch:
            lines.append(f"**Branch:** `{git.branch}`")

        if git.ahead > 0 or git.behind > 0:
            lines.append(f"**Sync:** ↑{git.ahead} ↓{git.behind}")

        if git.staged_files:
            lines.append(f"**Staged:** {len(git.staged_files)} files")
        if git.unstaged_files:
            lines.append(f"**Unstaged:** {len(git.unstaged_files)} files")

    # Workspace
    if hasattr(context, 'workspace') and context.workspace:
        ws = context.workspace
        lines.append("")
        lines.append("## Project Info")

        if ws.language:
            lines.append(f"**Language:** {ws.language}")
        if ws.framework:
            lines.append(f"**Framework:** {ws.framework}")
        if ws.has_tests and ws.test_command:
            lines.append(f"**Tests:** `{ws.test_command}`")

    # Recent files
    if hasattr(context, 'recent_files') and context.recent_files:
        lines.append("")
        lines.append("## Recent Files")
        for f in context.recent_files[:5]:
            lines.append(f"- `{f}`")

    return "\n".join(lines)


# ============================================================================
# EVENT SYSTEM
# ============================================================================

class EventType(str, Enum):
    """Event types for pub/sub system."""

    # Context events
    CONTEXT_UPDATED = "context_updated"
    DIRECTORY_CHANGED = "directory_changed"

    # Tool events
    TOOL_STARTED = "tool_started"
    TOOL_COMPLETED = "tool_completed"
    TOOL_FAILED = "tool_failed"

    # Agent events
    AGENT_INVOKED = "agent_invoked"
    AGENT_COMPLETED = "agent_completed"
    AGENT_FAILED = "agent_failed"

    # LLM events
    LLM_STREAM_START = "llm_stream_start"
    LLM_STREAM_CHUNK = "llm_stream_chunk"
    LLM_STREAM_END = "llm_stream_end"

    # Session events
    SESSION_START = "session_start"
    SESSION_END = "session_end"


@dataclass
class Event:
    """Generic event for pub/sub."""

    type: EventType
    data: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.now)
    event_id: str = field(default_factory=lambda: str(uuid4()))


EventHandler = Callable[[Event], None]


class EventBus(Protocol):
    """Protocol for event bus implementation."""

    def subscribe(self, event_type: EventType, handler: EventHandler) -> None:
        """Subscribe to event type."""
        ...

    def publish(self, event: Event) -> None:
        """Publish event to subscribers."""
        ...

    def unsubscribe(self, event_type: EventType, handler: EventHandler) -> None:
        """Unsubscribe from event type."""
        ...


# ============================================================================
# TUI INTEGRATION
# ============================================================================

@dataclass
class ToastConfig:
    """Configuration for toast notification."""

    message: str
    level: str = "info"  # info, success, warning, error
    duration_ms: int = 3000
    icon: Optional[str] = None


@dataclass
class ProgressConfig:
    """Configuration for progress bar."""

    title: str
    total: Optional[int] = None  # None = indeterminate
    current: int = 0
    description: Optional[str] = None


# ============================================================================
# INTEGRATION COORDINATOR
# ============================================================================

class IntegrationCoordinator(Protocol):
    """Central coordinator for all integrations.
    
    This is the main interface that the shell interacts with.
    All component communication flows through here.
    """

    async def process_message(
        self,
        message: str,
        context: RichContext
    ) -> str:
        """Process user message with full integration pipeline.
        
        Flow:
        1. Detect intent
        2. Build/refresh context
        3. Route to agent OR direct tool execution
        4. Publish events for TUI updates
        5. Return formatted response
        """
        ...

    def get_context(self) -> RichContext:
        """Get current rich context."""
        ...

    def refresh_context(self) -> RichContext:
        """Force context refresh (after cd, git ops, etc)."""
        ...

    def get_tools(self) -> List[ToolDefinition]:
        """Get all registered tools for function calling."""
        ...

    async def execute_tool(
        self,
        tool_name: str,
        parameters: Dict[str, Any]
    ) -> ToolExecutionResult:
        """Execute a tool by name."""
        ...
