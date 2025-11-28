"""
╔══════════════════════════════════════════════════════════════════════════════════╗
║                                                                                  ║
║                SOFIA CHAT MODE & PRE-EXECUTION COUNSEL TESTS                     ║
║                                                                                  ║
║  Tests for newly implemented features:                                          ║
║  1. SofiaChatMode - Continuous Socratic dialogue                                ║
║  2. Pre-Execution Counsel - Counsel before risky actions                        ║
║                                                                                  ║
║  Created: 2025-11-24                                                            ║
║  Author: Claude Code (Sonnet 4.5)                                               ║
║                                                                                  ║
╚══════════════════════════════════════════════════════════════════════════════════╝
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import Mock
from uuid import UUID

from jdev_cli.agents.sofia_agent import (
    SofiaChatMode,
    CounselResponse,
    create_sofia_agent,
)

from jdev_governance.sofia import (
    SofiaCounsel,
    CounselType,
    VirtueType,
    ThinkingMode,
    VirtueExpression,
    SocraticQuestion,
)


# ════════════════════════════════════════════════════════════════════════════════
# FIXTURES
# ════════════════════════════════════════════════════════════════════════════════


@pytest.fixture
def mock_llm_client():
    """Mock LLM client."""
    return Mock()


@pytest.fixture
def mock_mcp_client():
    """Mock MCP client."""
    return Mock()


@pytest.fixture
def mock_sofia_counsel():
    """Create a mock SofiaCounsel response from Sofia Core."""
    return SofiaCounsel(
        id=UUID("12345678-1234-5678-1234-567812345678"),
        timestamp=datetime.now(timezone.utc),
        user_query="Test query",  # Correct field name
        counsel_type=CounselType.EXPLORING,
        thinking_mode=ThinkingMode.SYSTEM_2,
        response="Let me ask you: what are your core values?",  # Correct field name
        questions_asked=[  # Correct field name
            SocraticQuestion(question_text="What values guide you?"),
            SocraticQuestion(question_text="Have you considered the consequences?"),
        ],
        virtues_expressed=[
            VirtueExpression(
                virtue=VirtueType.TAPEINOPHROSYNE,
                expression="Approaching this with humility",
            )
        ],
        confidence=0.75,
        processing_time_ms=150.0,
        community_suggested=False,
    )


@pytest.fixture
def sofia_agent(mock_llm_client, mock_mcp_client, mock_sofia_counsel, monkeypatch):
    """Create a Sofia agent with mocked core."""
    sofia = create_sofia_agent(mock_llm_client, mock_mcp_client)

    # Mock the respond method on sofia.sofia_core (SofiaCore uses 'respond', not 'provide_counsel')
    def mock_respond(*args, **kwargs):
        return mock_sofia_counsel

    monkeypatch.setattr(sofia.sofia_core, "respond", mock_respond)

    return sofia


# ════════════════════════════════════════════════════════════════════════════════
# CHAT MODE TESTS
# ════════════════════════════════════════════════════════════════════════════════


class TestSofiaChatMode:
    """Tests for SofiaChatMode continuous dialogue."""

    @pytest.mark.asyncio
    async def test_chat_mode_initialization(self, sofia_agent):
        """Test that chat mode initializes correctly."""
        chat = SofiaChatMode(sofia_agent)

        assert chat.sofia == sofia_agent
        assert chat.turn_count == 0
        assert chat.session_id is not None
        assert isinstance(chat.session_id, str)
        assert chat.started_at is not None

    @pytest.mark.asyncio
    async def test_send_message_async(self, sofia_agent):
        """Test sending a message in chat mode (async)."""
        chat = SofiaChatMode(sofia_agent)

        response = await chat.send_message("Should I refactor this code?")

        assert isinstance(response, CounselResponse)
        assert response.counsel is not None
        assert chat.turn_count == 1

    def test_send_message_sync(self, sofia_agent):
        """Test sending a message in chat mode (sync)."""
        chat = SofiaChatMode(sofia_agent)

        response = chat.send_message_sync("Should I refactor this code?")

        assert isinstance(response, CounselResponse)
        assert response.counsel is not None
        assert chat.turn_count == 1

    @pytest.mark.asyncio
    async def test_multi_turn_conversation(self, sofia_agent):
        """Test multiple turns of conversation maintain context."""
        chat = SofiaChatMode(sofia_agent)

        # Turn 1
        response1 = await chat.send_message("Should I delete user data?")
        assert chat.turn_count == 1
        assert response1.session_id == chat.session_id

        # Turn 2
        response2 = await chat.send_message("What if they requested it?")
        assert chat.turn_count == 2
        assert response2.session_id == chat.session_id

        # Turn 3
        response3 = await chat.send_message("How should I verify their identity?")
        assert chat.turn_count == 3
        assert response3.session_id == chat.session_id

        # All turns share the same session
        assert response1.session_id == response2.session_id == response3.session_id

    @pytest.mark.asyncio
    async def test_get_history(self, sofia_agent):
        """Test retrieving chat history."""
        chat = SofiaChatMode(sofia_agent)

        # Send multiple messages
        await chat.send_message("First question")
        await chat.send_message("Second question")
        await chat.send_message("Third question")

        history = chat.get_history()

        assert len(history) == 3
        assert all(isinstance(counsel, SofiaCounsel) for counsel in history)

    @pytest.mark.asyncio
    async def test_clear_session(self, sofia_agent):
        """Test clearing chat session starts fresh."""
        chat = SofiaChatMode(sofia_agent)

        # Send some messages
        await chat.send_message("First question")
        await chat.send_message("Second question")
        old_session_id = chat.session_id
        old_turn_count = chat.turn_count

        # Clear session
        chat.clear()

        # Verify reset
        assert chat.session_id != old_session_id
        assert chat.turn_count == 0
        assert len(chat.get_history()) == 0

    @pytest.mark.asyncio
    async def test_get_summary(self, sofia_agent):
        """Test getting session summary statistics."""
        chat = SofiaChatMode(sofia_agent)

        # Send messages
        await chat.send_message("Question 1")
        await chat.send_message("Question 2")

        summary = chat.get_summary()

        assert summary["session_id"] == chat.session_id
        assert summary["turn_count"] == 2
        assert "duration_seconds" in summary
        assert "total_questions_asked" in summary
        assert "avg_confidence" in summary
        assert "started_at" in summary

    @pytest.mark.asyncio
    async def test_export_transcript(self, sofia_agent):
        """Test exporting formatted chat transcript."""
        chat = SofiaChatMode(sofia_agent)

        # Send messages
        await chat.send_message("Should I implement feature X?")
        await chat.send_message("What are the risks?")

        transcript = chat.export_transcript()

        assert isinstance(transcript, str)
        assert chat.session_id in transcript
        assert "Turn 1" in transcript
        assert "Turn 2" in transcript
        assert "User Query:" in transcript  # Correct format
        assert "Sofia (" in transcript  # Includes counsel type

    @pytest.mark.asyncio
    async def test_chat_mode_passes_correct_context(self, sofia_agent, monkeypatch):
        """Test that chat mode passes correct context to counsel."""
        chat = SofiaChatMode(sofia_agent)

        # Track counsel calls
        counsel_calls = []

        # Store original method
        original_provide_counsel_async = sofia_agent.provide_counsel_async

        async def track_counsel(query, session_id=None, context=None, agent_id=None):
            counsel_calls.append({"query": query, "context": context})
            return await original_provide_counsel_async(query, session_id, context, agent_id)

        monkeypatch.setattr(sofia_agent, "provide_counsel_async", track_counsel)

        # Send message
        await chat.send_message("Test query")

        # Verify context
        assert len(counsel_calls) == 1
        assert counsel_calls[0]["context"]["mode"] == "chat"
        assert counsel_calls[0]["context"]["turn"] == 0

    @pytest.mark.asyncio
    async def test_chat_mode_session_continuity(self, sofia_agent):
        """Test that session history is maintained across turns."""
        chat = SofiaChatMode(sofia_agent)

        # First turn
        response1 = await chat.send_message("Should I do X?")

        # Check session history grows
        history1 = chat.get_history()
        assert len(history1) == 1

        # Second turn
        response2 = await chat.send_message("What about Y?")

        # History should have both
        history2 = chat.get_history()
        assert len(history2) == 2
        assert history2[0].id == history1[0].id  # First counsel preserved


# ════════════════════════════════════════════════════════════════════════════════
# PRE-EXECUTION COUNSEL TESTS
# ════════════════════════════════════════════════════════════════════════════════


class TestPreExecutionCounsel:
    """Tests for pre-execution counsel functionality."""

    @pytest.mark.asyncio
    async def test_pre_execution_counsel_basic(self, sofia_agent):
        """Test basic pre-execution counsel."""
        response = await sofia_agent.pre_execution_counsel(
            action_description="Delete all user data without backup",
            risk_level="HIGH",
            agent_id="executor-1",
        )

        assert isinstance(response, CounselResponse)
        assert response.counsel is not None
        assert "Delete all user data without backup" in response.original_query
        assert "HIGH" in response.original_query

    def test_pre_execution_counsel_sync(self, sofia_agent):
        """Test synchronous pre-execution counsel."""
        response = sofia_agent.pre_execution_counsel_sync(
            action_description="Execute SQL without sanitization",
            risk_level="CRITICAL",
            agent_id="executor-2",
        )

        assert isinstance(response, CounselResponse)
        assert response.counsel is not None

    @pytest.mark.asyncio
    async def test_pre_execution_counsel_passes_context(self, sofia_agent, monkeypatch):
        """Test that pre-execution counsel passes correct context."""
        counsel_calls = []

        # Store original method
        original_provide_counsel_async = sofia_agent.provide_counsel_async

        async def track_counsel(query, session_id=None, context=None, agent_id=None):
            counsel_calls.append({"context": context, "agent_id": agent_id})
            return await original_provide_counsel_async(query, session_id, context, agent_id)

        monkeypatch.setattr(sofia_agent, "provide_counsel_async", track_counsel)

        await sofia_agent.pre_execution_counsel(
            action_description="Risky action",
            risk_level="MEDIUM",
            agent_id="test-agent",
        )

        assert len(counsel_calls) == 1
        assert counsel_calls[0]["context"]["mode"] == "pre_execution"
        assert counsel_calls[0]["context"]["risk_level"] == "MEDIUM"
        assert counsel_calls[0]["context"]["action"] == "Risky action"
        assert counsel_calls[0]["agent_id"] == "test-agent"

    @pytest.mark.asyncio
    async def test_pre_execution_counsel_with_custom_context(self, sofia_agent):
        """Test pre-execution counsel with additional context."""
        custom_context = {
            "target": "production_database",
            "affected_users": 10000,
            "reversible": False,
        }

        response = await sofia_agent.pre_execution_counsel(
            action_description="Drop table",
            risk_level="CRITICAL",
            agent_id="executor-3",
            context=custom_context,
        )

        assert isinstance(response, CounselResponse)
        # Context should be merged with pre_execution defaults

    @pytest.mark.asyncio
    async def test_pre_execution_counsel_different_risk_levels(self, sofia_agent):
        """Test pre-execution counsel with different risk levels."""
        risk_levels = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]

        for risk_level in risk_levels:
            response = await sofia_agent.pre_execution_counsel(
                action_description=f"Action with {risk_level} risk",
                risk_level=risk_level,
                agent_id="executor-test",
            )

            assert isinstance(response, CounselResponse)
            assert risk_level in response.original_query

    @pytest.mark.asyncio
    async def test_pre_execution_counsel_metrics_tracking(self, sofia_agent):
        """Test that pre-execution counsel is tracked in metrics."""
        agent_id = "metrics-test-agent"

        # Provide counsel
        await sofia_agent.pre_execution_counsel(
            action_description="Test action",
            risk_level="HIGH",
            agent_id=agent_id,
        )

        # Check metrics
        metrics = sofia_agent.get_metrics(agent_id)
        assert metrics.total_counsels >= 1

    @pytest.mark.asyncio
    async def test_pre_execution_counsel_question_format(self, sofia_agent):
        """Test that pre-execution counsel formats question correctly."""
        action = "Deploy to production without tests"
        risk = "HIGH"

        response = await sofia_agent.pre_execution_counsel(
            action_description=action,
            risk_level=risk,
            agent_id="test",
        )

        # Query should contain key elements
        query = response.original_query
        assert risk.lower() in query.lower() or risk in query
        assert action in query
        assert any(
            keyword in query.lower()
            for keyword in ["consider", "wrong", "ethical", "implications"]
        )

    @pytest.mark.asyncio
    async def test_pre_execution_counsel_for_data_operations(self, sofia_agent):
        """Test pre-execution counsel for data deletion scenarios."""
        response = await sofia_agent.pre_execution_counsel(
            action_description="Delete user account data",
            risk_level="HIGH",
            agent_id="executor",
        )

        assert isinstance(response, CounselResponse)
        # Sofia should provide thoughtful counsel about data deletion

    @pytest.mark.asyncio
    async def test_pre_execution_counsel_for_security_operations(self, sofia_agent):
        """Test pre-execution counsel for security-sensitive operations."""
        response = await sofia_agent.pre_execution_counsel(
            action_description="Disable authentication temporarily",
            risk_level="CRITICAL",
            agent_id="executor",
        )

        assert isinstance(response, CounselResponse)
        # Sofia should provide counsel about security implications


# ════════════════════════════════════════════════════════════════════════════════
# INTEGRATION TESTS (Chat Mode + Pre-Execution)
# ════════════════════════════════════════════════════════════════════════════════


class TestChatAndPreExecutionIntegration:
    """Tests integrating chat mode with pre-execution counsel."""

    @pytest.mark.asyncio
    async def test_chat_then_pre_execution(self, sofia_agent):
        """Test using chat mode then pre-execution counsel."""
        # Start chat session
        chat = SofiaChatMode(sofia_agent)
        await chat.send_message("I'm planning a database migration")
        await chat.send_message("What should I consider?")

        # Now request pre-execution counsel
        response = await sofia_agent.pre_execution_counsel(
            action_description="Execute database migration",
            risk_level="HIGH",
            agent_id="migration-agent",
        )

        assert isinstance(response, CounselResponse)

    @pytest.mark.asyncio
    async def test_metrics_across_both_modes(self, sofia_agent):
        """Test that metrics track counsel across both modes."""
        agent_id = "mixed-mode-agent"

        # Chat mode counsel (won't be tracked without agent_id parameter)
        chat = SofiaChatMode(sofia_agent)
        await chat.send_message("Question 1")

        # Pre-execution counsel (will be tracked with agent_id)
        await sofia_agent.pre_execution_counsel(
            action_description="Action",
            risk_level="MEDIUM",
            agent_id=agent_id,
        )

        # Check metrics (only pre-execution tracked with agent_id)
        metrics = sofia_agent.get_metrics(agent_id)
        assert metrics.total_counsels == 1  # Only pre-execution counted


# ════════════════════════════════════════════════════════════════════════════════
# EDGE CASES & ERROR HANDLING
# ════════════════════════════════════════════════════════════════════════════════


class TestEdgeCases:
    """Test edge cases for new features."""

    @pytest.mark.asyncio
    async def test_chat_mode_empty_message(self, sofia_agent):
        """Test chat mode with empty message."""
        chat = SofiaChatMode(sofia_agent)

        response = await chat.send_message("")

        # Should still return response (Sofia Core handles it)
        assert isinstance(response, CounselResponse)

    @pytest.mark.asyncio
    async def test_pre_execution_empty_action(self, sofia_agent):
        """Test pre-execution counsel with empty action description."""
        response = await sofia_agent.pre_execution_counsel(
            action_description="",
            risk_level="HIGH",
            agent_id="test",
        )

        assert isinstance(response, CounselResponse)

    @pytest.mark.asyncio
    async def test_chat_mode_very_long_conversation(self, sofia_agent):
        """Test chat mode with many turns."""
        chat = SofiaChatMode(sofia_agent)

        # Send 20 messages
        for i in range(20):
            await chat.send_message(f"Question {i+1}")

        assert chat.turn_count == 20
        history = chat.get_history()
        assert len(history) == 20

    @pytest.mark.asyncio
    async def test_pre_execution_none_context(self, sofia_agent):
        """Test pre-execution counsel with None context."""
        response = await sofia_agent.pre_execution_counsel(
            action_description="Action",
            risk_level="HIGH",
            agent_id="test",
            context=None,
        )

        assert isinstance(response, CounselResponse)
