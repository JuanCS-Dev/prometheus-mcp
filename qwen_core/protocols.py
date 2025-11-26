"""
qwen_core.protocols: Interface Contracts.

Defines the protocols (structural typing) that external modules must implement.
Using Protocol instead of ABC allows:
- Duck typing with type safety
- No inheritance required
- Easier mocking in tests
- Clearer contracts

All protocols here define the MINIMUM interface required.
Implementations may add more methods.
"""

from __future__ import annotations

from typing import (
    Any,
    AsyncIterator,
    Dict,
    List,
    Optional,
    Protocol,
    runtime_checkable,
)

from qwen_core.types import AgentTask, AgentResponse, AgentCapability, AgentRole


# =============================================================================
# LLM CLIENT PROTOCOL
# =============================================================================

@runtime_checkable
class LLMClientProtocol(Protocol):
    """
    Protocol for LLM client implementations.

    Implementations must provide either generate() or stream().
    Both is preferred for flexibility.

    Example:
        class GeminiClient:
            async def generate(self, prompt: str, **kwargs) -> str:
                ...

            async def stream(self, prompt: str, **kwargs) -> AsyncIterator[str]:
                ...

        # Type checker accepts this:
        client: LLMClientProtocol = GeminiClient()
    """

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        **kwargs: Any,
    ) -> str:
        """Generate a complete response."""
        ...

    async def stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        """Stream response tokens."""
        ...


@runtime_checkable
class LLMClientWithChatProtocol(LLMClientProtocol, Protocol):
    """Extended protocol with chat-style streaming."""

    async def stream_chat(
        self,
        prompt: str,
        context: Optional[str] = None,
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        """Stream chat response with context."""
        ...


# =============================================================================
# MCP CLIENT PROTOCOL
# =============================================================================

@runtime_checkable
class MCPClientProtocol(Protocol):
    """
    Protocol for Model Context Protocol client.

    MCP provides tool execution and resource access.
    """

    async def call_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Execute a tool and return results."""
        ...

    async def list_tools(self) -> List[Dict[str, Any]]:
        """List available tools with schemas."""
        ...

    async def get_resource(
        self,
        uri: str,
    ) -> Dict[str, Any]:
        """Get a resource by URI."""
        ...


# =============================================================================
# AGENT PROTOCOL
# =============================================================================

@runtime_checkable
class AgentProtocol(Protocol):
    """
    Protocol for agent implementations.

    All agents must implement execute(). Streaming is optional.

    Properties:
        role: The agent's role (from AgentRole enum)
        capabilities: List of capabilities this agent has

    Methods:
        execute: Synchronous task execution
        execute_streaming: Optional streaming execution
    """

    @property
    def role(self) -> AgentRole:
        """The agent's role identifier."""
        ...

    @property
    def capabilities(self) -> List[AgentCapability]:
        """List of capabilities this agent has."""
        ...

    async def execute(self, task: AgentTask) -> AgentResponse:
        """
        Execute a task and return the response.

        This is the primary entry point for all agents.

        Args:
            task: The task specification

        Returns:
            AgentResponse with success/failure and data
        """
        ...


@runtime_checkable
class StreamingAgentProtocol(AgentProtocol, Protocol):
    """Extended protocol for agents that support streaming."""

    async def execute_streaming(
        self,
        task: AgentTask,
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        Execute task with streaming output.

        Yields dicts with format:
            {"type": "status"|"thinking"|"result", "data": ...}
        """
        ...


# =============================================================================
# TOOL PROTOCOL
# =============================================================================

@runtime_checkable
class ToolProtocol(Protocol):
    """
    Protocol for tool implementations.

    Tools are atomic operations that agents can invoke.
    """

    @property
    def name(self) -> str:
        """Unique tool identifier."""
        ...

    @property
    def description(self) -> str:
        """Human-readable description."""
        ...

    @property
    def required_capability(self) -> AgentCapability:
        """Capability required to use this tool."""
        ...

    async def execute(
        self,
        arguments: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Execute the tool with given arguments.

        Args:
            arguments: Tool-specific arguments

        Returns:
            Dict with 'success' bool and 'result' or 'error'
        """
        ...


@runtime_checkable
class ToolWithSchemaProtocol(ToolProtocol, Protocol):
    """Extended protocol for tools with JSON schema."""

    @property
    def parameters_schema(self) -> Dict[str, Any]:
        """JSON Schema for tool parameters."""
        ...


# =============================================================================
# GOVERNANCE PROTOCOL
# =============================================================================

@runtime_checkable
class GovernanceProtocol(Protocol):
    """
    Protocol for governance/audit systems.

    Governs agent actions for safety and compliance.
    """

    async def evaluate_action(
        self,
        agent_role: AgentRole,
        action: str,
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Evaluate if an action is permitted.

        Returns:
            {"allowed": bool, "reason": str, "violations": [...]}
        """
        ...

    def get_status_emoji(self) -> str:
        """Get current governance status as emoji."""
        ...


# =============================================================================
# SESSION PROTOCOL
# =============================================================================

@runtime_checkable
class SessionProtocol(Protocol):
    """Protocol for session management."""

    @property
    def session_id(self) -> str:
        """Current session identifier."""
        ...

    async def get_history(self) -> List[Dict[str, Any]]:
        """Get conversation history."""
        ...

    async def add_message(
        self,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Add message to history."""
        ...

    async def clear(self) -> None:
        """Clear session history."""
        ...
