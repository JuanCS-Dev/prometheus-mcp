"""
Basic Tests for SofiaIntegratedAgent

This test suite covers:
- Initialization
- Basic counsel functionality
- Metrics tracking
- Session management
- Auto-detection
- BaseAgent interface
"""

import pytest
from jdev_cli.agents.sofia_agent import (
    SofiaIntegratedAgent,
    create_sofia_agent,
    CounselResponse,
    CounselMetrics,
)
from jdev_cli.agents.base import AgentTask, AgentRole


# ════════════════════════════════════════════════════════════════════════════════
# FIXTURES
# ════════════════════════════════════════════════════════════════════════════════


class MockLLMClient:
    """Mock LLM client for testing."""
    pass


class MockMCPClient:
    """Mock MCP client for testing."""
    pass


@pytest.fixture
def mock_llm():
    return MockLLMClient()


@pytest.fixture
def mock_mcp():
    return MockMCPClient()


@pytest.fixture
def sofia_agent(mock_llm, mock_mcp):
    """Create a Sofia agent for testing."""
    return create_sofia_agent(
        llm_client=mock_llm,
        mcp_client=mock_mcp,
        auto_detect=True,
        socratic_ratio=0.7,
    )


# ════════════════════════════════════════════════════════════════════════════════
# BASIC TESTS
# ════════════════════════════════════════════════════════════════════════════════


class TestInitialization:
    """Test Sofia agent initialization."""

    def test_create_sofia_agent(self, mock_llm, mock_mcp):
        """Test creating a Sofia agent."""
        sofia = create_sofia_agent(mock_llm, mock_mcp)

        assert sofia is not None
        assert sofia.role == AgentRole.COUNSELOR
        assert sofia.auto_detect is True
        assert sofia.get_sofia_state() == "LISTENING"

    def test_custom_config(self, mock_llm, mock_mcp):
        """Test Sofia with custom configuration."""
        sofia = SofiaIntegratedAgent(
            llm_client=mock_llm,
            mcp_client=mock_mcp,
            socratic_ratio=0.9,
            system2_threshold=0.8,
            auto_detect_ethical_dilemmas=False,
        )

        assert sofia.auto_detect is False
        assert sofia.sofia_core.config.socratic_ratio == 0.9
        assert sofia.sofia_core.config.system2_threshold == 0.8


class TestCounselProvision:
    """Test counsel provision functionality."""

    def test_provide_counsel_basic(self, sofia_agent):
        """Test basic counsel provision."""
        response = sofia_agent.provide_counsel(
            query="Should I refactor this code?",
            agent_id="test-agent"
        )

        assert isinstance(response, CounselResponse)
        assert response.counsel is not None
        assert len(response.counsel) > 0
        assert response.confidence >= 0.0
        assert response.confidence <= 1.0
        assert response.processing_time_ms >= 0.0

    @pytest.mark.asyncio
    async def test_provide_counsel_async(self, sofia_agent):
        """Test async counsel provision."""
        response = await sofia_agent.provide_counsel_async(
            query="Is it ethical to track users?",
            agent_id="async-test"
        )

        assert isinstance(response, CounselResponse)
        assert response.counsel is not None

    def test_counsel_with_context(self, sofia_agent):
        """Test counsel with additional context."""
        response = sofia_agent.provide_counsel(
            query="Should I delete user data?",
            context={"reason": "GDPR request"},
            agent_id="context-test"
        )

        assert response.counsel is not None


class TestMetricsTracking:
    """Test metrics tracking."""

    def test_metrics_creation(self, sofia_agent):
        """Test that metrics are created after first counsel."""
        agent_id = "metrics-test"

        # Before counsel - no metrics
        metrics = sofia_agent.get_metrics(agent_id)
        assert metrics is None

        # After counsel - metrics exist
        sofia_agent.provide_counsel("Test query", agent_id=agent_id)
        metrics = sofia_agent.get_metrics(agent_id)

        assert metrics is not None
        assert isinstance(metrics, CounselMetrics)
        assert metrics.total_counsels == 1

    def test_metrics_accumulation(self, sofia_agent):
        """Test that metrics accumulate correctly."""
        agent_id = "accumulation-test"

        # Provide multiple counsels
        for i in range(5):
            sofia_agent.provide_counsel(f"Query {i}", agent_id=agent_id)

        metrics = sofia_agent.get_metrics(agent_id)
        assert metrics.total_counsels == 5

    def test_metrics_export(self, sofia_agent):
        """Test exporting all metrics."""
        sofia_agent.provide_counsel("Q1", agent_id="agent1")
        sofia_agent.provide_counsel("Q2", agent_id="agent2")

        export = sofia_agent.export_metrics()

        assert isinstance(export, dict)
        assert "agent1" in export
        assert "agent2" in export
        assert export["agent1"]["total_counsels"] == 1


class TestSessionManagement:
    """Test session management."""

    def test_session_tracking(self, sofia_agent):
        """Test that sessions track counsel history."""
        session_id = "test-session-1"

        # Provide multiple counsels in same session
        sofia_agent.provide_counsel("Q1", session_id=session_id)
        sofia_agent.provide_counsel("Q2", session_id=session_id)

        history = sofia_agent.get_session_history(session_id)
        assert len(history) == 2

    def test_clear_session(self, sofia_agent):
        """Test clearing a session."""
        session_id = "test-session-2"

        sofia_agent.provide_counsel("Q1", session_id=session_id)
        sofia_agent.clear_session(session_id)

        history = sofia_agent.get_session_history(session_id)
        assert len(history) == 0


class TestAutoDetection:
    """Test auto-detection of ethical concerns."""

    def test_should_trigger_on_delete(self, sofia_agent):
        """Test auto-trigger on delete keyword."""
        should, reason = sofia_agent.should_trigger_counsel(
            "I want to delete user data"
        )

        assert should is True
        assert "delete" in reason.lower()

    def test_should_trigger_on_ethical(self, sofia_agent):
        """Test auto-trigger on ethical keywords."""
        should, reason = sofia_agent.should_trigger_counsel(
            "Is this ethical?"
        )

        assert should is True
        assert "ethical" in reason.lower()

    def test_no_trigger_on_normal(self, sofia_agent):
        """Test no trigger on normal content."""
        should, reason = sofia_agent.should_trigger_counsel(
            "Hello, how are you?"
        )

        assert should is False

    def test_auto_detect_disabled(self, mock_llm, mock_mcp):
        """Test that auto-detect can be disabled."""
        sofia = SofiaIntegratedAgent(
            llm_client=mock_llm,
            mcp_client=mock_mcp,
            auto_detect_ethical_dilemmas=False,
        )

        should, reason = sofia.should_trigger_counsel("delete user data")
        assert should is False
        assert "disabled" in reason.lower()


class TestBaseAgentInterface:
    """Test BaseAgent interface implementation."""

    @pytest.mark.asyncio
    async def test_execute(self, sofia_agent):
        """Test execute method."""
        task = AgentTask(
            task_id="task-1",
            request="Should I implement this feature?",
            context={"requesting_agent_id": "executor"},
            session_id="session-1",
            metadata={},
            history=[]
        )

        response = await sofia_agent.execute(task)

        assert response.success is True
        assert "counsel" in response.data
        assert response.reasoning is not None
        assert response.error is None

    @pytest.mark.asyncio
    async def test_execute_streaming(self, sofia_agent):
        """Test streaming execution."""
        task = AgentTask(
            task_id="task-2",
            request="Should I refactor?",
            context={},
            session_id="session-2",
            metadata={},
            history=[]
        )

        chunks = []
        final_response = None

        async for chunk, response in sofia_agent.execute_streaming(task):
            chunks.append(chunk)
            if response:
                final_response = response

        assert len(chunks) > 0
        assert final_response is not None
        assert final_response.success is True


class TestErrorHandling:
    """Test error handling."""

    def test_empty_query(self, sofia_agent):
        """Test handling of empty query."""
        # Sofia Core should handle this gracefully
        response = sofia_agent.provide_counsel("")
        assert response is not None

    def test_none_session_id(self, sofia_agent):
        """Test handling of None session_id."""
        response = sofia_agent.provide_counsel(
            "Test query",
            session_id=None
        )
        assert response is not None


class TestVirtueTracking:
    """Test virtue tracking in metrics."""

    def test_virtue_distribution(self, sofia_agent):
        """Test tracking of virtue distribution."""
        # Provide multiple counsels
        for i in range(3):
            sofia_agent.provide_counsel(f"Query {i}", agent_id="virtue-test")

        distribution = sofia_agent.get_virtue_distribution()

        assert isinstance(distribution, dict)
        # Sofia may not always express virtues explicitly,
        # so we just check the structure is correct


class TestCounselTypes:
    """Test different counsel types."""

    def test_counsel_type_recorded(self, sofia_agent):
        """Test that counsel type is recorded."""
        response = sofia_agent.provide_counsel(
            "I'm feeling anxious",
            agent_id="type-test"
        )

        assert response.counsel_type is not None
        # Likely SUPPORTING due to "anxious" keyword

    def test_thinking_mode_recorded(self, sofia_agent):
        """Test that thinking mode is recorded."""
        response = sofia_agent.provide_counsel(
            "Simple question",
            agent_id="mode-test"
        )

        assert response.thinking_mode in ["SYSTEM_1", "SYSTEM_2"]


# ════════════════════════════════════════════════════════════════════════════════
# RUN TESTS
# ════════════════════════════════════════════════════════════════════════════════


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
