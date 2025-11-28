"""
Tests for Integration Coordinator.

Boris Cherny: "Tests or it didn't happen."
"""

import pytest
from typing import Any, Dict

from jdev_cli.core.integration_coordinator import Coordinator, SimpleEventBus
from jdev_cli.core.integration_types import (
    AgentResponse,
    Event,
    EventType,
    IntentType,
    ToolCategory,
    ToolDefinition,
)


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def event_bus():
    """Create event bus for testing."""
    return SimpleEventBus()


@pytest.fixture
def coordinator(event_bus, tmp_path):
    """Create coordinator for testing."""
    return Coordinator(cwd=str(tmp_path), event_bus=event_bus)


@pytest.fixture
def mock_context():
    """Create mock rich context (uses existing dataclass structure)."""
    from jdev_cli.intelligence.context_enhanced import (
        RichContext, GitStatus, WorkspaceInfo, TerminalInfo
    )
    from jdev_cli.intelligence.types import Context

    # Create base context
    base = Context(
        working_directory="/test/project",
        recent_files=["test.py", "main.py"],
        command_history=[],
        recent_errors=[]
    )

    # Add git status
    git = GitStatus(
        branch="main",
        staged_files=[],
        unstaged_files=[],
        untracked_files=[],
        has_remote=True,
        ahead=0,
        behind=0
    )

    # Add workspace info
    workspace = WorkspaceInfo(
        language="python",
        framework="pytest",
        dependencies={},
        has_tests=True,
        test_command="pytest"
    )

    # Add terminal info
    terminal = TerminalInfo(
        working_directory="/test/project",
        last_exit_code=0,
        shell="bash"
    )

    return RichContext(
        working_directory="/test/project",
        recent_files=["test.py", "main.py"],
        command_history=[],
        recent_errors=[],
        git_status=git,
        workspace=workspace,
        terminal=terminal
    )


class MockAgent:
    """Mock agent for testing."""

    async def invoke(self, request: str, context: Dict[str, Any]) -> AgentResponse:
        """Mock invoke that succeeds."""
        return {
            "success": True,
            "output": f"Processed: {request}",
            "metadata": {},
            "execution_time_ms": 10.0,
            "tokens_used": 100,
        }


class MockFailingAgent:
    """Mock agent that fails."""

    async def invoke(self, request: str, context: Dict[str, Any]) -> AgentResponse:
        """Mock invoke that fails."""
        raise RuntimeError("Agent failed intentionally")


def mock_tool_executor(param1: str) -> str:
    """Mock tool executor."""
    return f"Executed with {param1}"


def mock_failing_executor(param1: str) -> str:
    """Mock executor that fails."""
    raise ValueError("Executor failed intentionally")


# ============================================================================
# EVENT BUS TESTS
# ============================================================================

def test_event_bus_subscribe_publish(event_bus):
    """Test event bus subscription and publishing."""
    received_events = []

    def handler(event: Event):
        received_events.append(event)

    event_bus.subscribe(EventType.CONTEXT_UPDATED, handler)

    test_event = Event(
        type=EventType.CONTEXT_UPDATED,
        data={"test": "data"}
    )

    event_bus.publish(test_event)

    assert len(received_events) == 1
    assert received_events[0].type == EventType.CONTEXT_UPDATED
    assert received_events[0].data["test"] == "data"


def test_event_bus_multiple_handlers(event_bus):
    """Test multiple handlers for same event."""
    counter1 = {"count": 0}
    counter2 = {"count": 0}

    def handler1(event: Event):
        counter1["count"] += 1

    def handler2(event: Event):
        counter2["count"] += 1

    event_bus.subscribe(EventType.TOOL_STARTED, handler1)
    event_bus.subscribe(EventType.TOOL_STARTED, handler2)

    event_bus.publish(Event(type=EventType.TOOL_STARTED, data={}))

    assert counter1["count"] == 1
    assert counter2["count"] == 1


def test_event_bus_unsubscribe(event_bus):
    """Test unsubscribing from events."""
    received = []

    def handler(event: Event):
        received.append(event)

    event_bus.subscribe(EventType.AGENT_INVOKED, handler)
    event_bus.publish(Event(type=EventType.AGENT_INVOKED, data={}))

    assert len(received) == 1

    event_bus.unsubscribe(EventType.AGENT_INVOKED, handler)
    event_bus.publish(Event(type=EventType.AGENT_INVOKED, data={}))

    assert len(received) == 1  # No new event received


# ============================================================================
# COORDINATOR - AGENT REGISTRY TESTS
# ============================================================================

def test_coordinator_register_agent(coordinator):
    """Test registering an agent."""
    agent = MockAgent()
    coordinator.register_agent(IntentType.REVIEW, agent)

    assert IntentType.REVIEW in coordinator._agents
    assert coordinator._agents[IntentType.REVIEW] is agent


@pytest.mark.asyncio
async def test_coordinator_process_message_with_agent(coordinator):
    """Test message processing routed to agent."""
    agent = MockAgent()
    coordinator.register_agent(IntentType.REVIEW, agent)

    response = await coordinator.process_message("please review this code")

    assert "Processed: please review this code" in response


@pytest.mark.asyncio
async def test_coordinator_agent_invocation_events(coordinator, event_bus):
    """Test that agent invocation publishes events."""
    events = []

    def capture(event: Event):
        events.append(event)

    event_bus.subscribe(EventType.AGENT_INVOKED, capture)
    event_bus.subscribe(EventType.AGENT_COMPLETED, capture)

    agent = MockAgent()
    coordinator.register_agent(IntentType.TESTING, agent)

    await coordinator.process_message("run tests")

    # Should have invoked + completed events
    assert len(events) == 2
    assert events[0].type == EventType.AGENT_INVOKED
    assert events[1].type == EventType.AGENT_COMPLETED


@pytest.mark.asyncio
async def test_coordinator_agent_failure_event(coordinator, event_bus):
    """Test that agent failures publish failure events."""
    events = []

    def capture(event: Event):
        events.append(event)

    event_bus.subscribe(EventType.AGENT_FAILED, capture)

    failing_agent = MockFailingAgent()
    coordinator.register_agent(IntentType.SECURITY, failing_agent)

    response = await coordinator.process_message("find security vulnerabilities")

    assert "failed" in response.lower()
    assert len(events) == 1
    assert events[0].type == EventType.AGENT_FAILED


# ============================================================================
# COORDINATOR - TOOL REGISTRY TESTS
# ============================================================================

def test_coordinator_register_tool(coordinator):
    """Test registering a tool."""
    tool_def = ToolDefinition(
        name="test_tool",
        description="Test tool",
        category=ToolCategory.FILE,
        parameters={
            "type": "object",
            "properties": {
                "param1": {"type": "string"}
            }
        }
    )

    coordinator.register_tool(tool_def, mock_tool_executor)

    tools = coordinator.get_tools()
    assert len(tools) == 1
    assert tools[0].name == "test_tool"


def test_coordinator_get_tools_for_gemini(coordinator):
    """Test getting tools in Gemini format."""
    tool_def = ToolDefinition(
        name="read_file",
        description="Read a file",
        category=ToolCategory.FILE,
        parameters={
            "type": "object",
            "properties": {
                "path": {"type": "string"}
            }
        }
    )

    coordinator.register_tool(tool_def, mock_tool_executor)

    gemini_tools = coordinator.get_tools_for_gemini()

    assert len(gemini_tools) == 1
    assert gemini_tools[0]["name"] == "read_file"
    assert "parameters" in gemini_tools[0]


@pytest.mark.asyncio
async def test_coordinator_execute_tool_success(coordinator):
    """Test successful tool execution."""
    tool_def = ToolDefinition(
        name="test_tool",
        description="Test",
        category=ToolCategory.SHELL,
        parameters={"type": "object"}
    )

    coordinator.register_tool(tool_def, mock_tool_executor)

    result = await coordinator.execute_tool("test_tool", {"param1": "hello"})

    assert result.success is True
    assert "Executed with hello" in result.output
    assert result.execution_time_ms > 0


@pytest.mark.asyncio
async def test_coordinator_execute_tool_failure(coordinator):
    """Test tool execution failure."""
    tool_def = ToolDefinition(
        name="failing_tool",
        description="Fails",
        category=ToolCategory.SHELL,
        parameters={"type": "object"}
    )

    coordinator.register_tool(tool_def, mock_failing_executor)

    result = await coordinator.execute_tool("failing_tool", {"param1": "test"})

    assert result.success is False
    assert result.error is not None
    assert "Executor failed" in result.error


@pytest.mark.asyncio
async def test_coordinator_execute_nonexistent_tool(coordinator):
    """Test executing nonexistent tool raises error."""
    with pytest.raises(ValueError, match="Tool not found"):
        await coordinator.execute_tool("nonexistent", {})


@pytest.mark.asyncio
async def test_coordinator_tool_execution_events(coordinator, event_bus):
    """Test tool execution publishes events."""
    events = []

    def capture(event: Event):
        events.append(event)

    event_bus.subscribe(EventType.TOOL_STARTED, capture)
    event_bus.subscribe(EventType.TOOL_COMPLETED, capture)

    tool_def = ToolDefinition(
        name="test_tool",
        description="Test",
        category=ToolCategory.FILE,
        parameters={"type": "object"}
    )

    coordinator.register_tool(tool_def, mock_tool_executor)

    await coordinator.execute_tool("test_tool", {"param1": "test"})

    assert len(events) == 2
    assert events[0].type == EventType.TOOL_STARTED
    assert events[1].type == EventType.TOOL_COMPLETED


# ============================================================================
# COORDINATOR - INTENT DETECTION TESTS
# ============================================================================

@pytest.mark.parametrize("message,expected_intent", [
    ("please review this code", IntentType.REVIEW),
    ("analyze the architecture", IntentType.ARCHITECTURE),
    ("run tests on this module", IntentType.TESTING),
    ("check for security vulnerabilities", IntentType.SECURITY),
    ("optimize performance", IntentType.PERFORMANCE),
    ("refactor this function", IntentType.REFACTORING),
    ("create a plan", IntentType.PLANNING),
    ("explore the codebase", IntentType.EXPLORATION),
    ("write documentation", IntentType.DOCUMENTATION),
])
def test_coordinator_detect_intent(coordinator, message, expected_intent):
    """Test intent detection from various messages."""
    intent = coordinator.detect_intent(message)

    assert intent.type == expected_intent
    assert intent.confidence > 0


def test_coordinator_detect_intent_general(coordinator):
    """Test general intent for non-specific messages."""
    intent = coordinator.detect_intent("hello world")

    assert intent.type == IntentType.GENERAL
    assert intent.confidence == 1.0


def test_coordinator_detect_intent_confidence(coordinator):
    """Test confidence scores for intent detection."""
    # Message with multiple keywords should have higher confidence
    intent1 = coordinator.detect_intent("review and analyze")
    intent2 = coordinator.detect_intent("review")

    assert intent1.confidence >= intent2.confidence


# ============================================================================
# COORDINATOR - CONTEXT MANAGEMENT TESTS
# ============================================================================

def test_coordinator_get_context(coordinator):
    """Test getting context."""
    context = coordinator.get_context()

    assert context is not None
    assert hasattr(context, 'working_directory')
    assert str(coordinator.cwd) in context.working_directory


def test_coordinator_context_caching(coordinator):
    """Test that context is cached."""
    context1 = coordinator.get_context()
    context2 = coordinator.get_context()

    # Should be same instance (cached)
    assert context1 is context2


def test_coordinator_refresh_context(coordinator, event_bus):
    """Test force refresh of context."""
    events = []

    def capture(event: Event):
        events.append(event)

    event_bus.subscribe(EventType.CONTEXT_UPDATED, capture)

    context = coordinator.refresh_context()

    assert context is not None
    assert len(events) == 1
    assert events[0].type == EventType.CONTEXT_UPDATED


def test_coordinator_context_ttl(coordinator):
    """Test context TTL expiration."""
    context1 = coordinator.get_context()

    # Force cache to expire
    coordinator._context_cache_time = 0.0

    context2 = coordinator.get_context()

    # Should be different instances (re-built)
    assert context1 is not context2
