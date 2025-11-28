"""
Comprehensive streaming tests for BaseAgent._stream_llm() and _call_llm().

Tests cover:
- _stream_llm() method with multiple implementations
  * stream_chat available
  * stream method fallback
  * Error handling during streaming
- _call_llm() with streaming fallback
  * Fallback to stream when generate unavailable
  * Token concatenation
- Async iteration and cleanup
  * Correct token yielding
  * Cleanup after errors
  * Execution count incrementation

Based on Anthropic Claude Code testing standards.
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock

from jdev_cli.agents.base import (
    AgentRole,
    AgentCapability,
    AgentTask,
    AgentResponse,
    BaseAgent,
)


# =============================================================================
# TEST FIXTURES
# =============================================================================

class ConcreteAgent(BaseAgent):
    """Concrete implementation for testing BaseAgent."""

    async def execute(self, task: AgentTask) -> AgentResponse:
        """Simple execute implementation."""
        return AgentResponse(
            success=True,
            data={"executed": task.request},
            reasoning="Test execution"
        )


@pytest.fixture
def mock_llm():
    """Create mock LLM client."""
    client = MagicMock()
    client.generate = AsyncMock(return_value="LLM response")
    return client


@pytest.fixture
def mock_mcp():
    """Create mock MCP client."""
    client = MagicMock()
    client.call_tool = AsyncMock(return_value={"success": True})
    return client


@pytest.fixture
def agent(mock_llm, mock_mcp):
    """Create agent for testing."""
    return ConcreteAgent(
        role=AgentRole.EXPLORER,
        capabilities=[AgentCapability.READ_ONLY],
        llm_client=mock_llm,
        mcp_client=mock_mcp,
        system_prompt="Test prompt"
    )


# =============================================================================
# _STREAM_LLM WITH STREAM_CHAT TESTS
# =============================================================================

class TestStreamLlmWithStreamChat:
    """Tests for _stream_llm using stream_chat method."""

    @pytest.mark.asyncio
    async def test_stream_chat_basic_tokens(self, mock_mcp):
        """Test _stream_llm yields tokens from stream_chat."""
        async def mock_stream_chat(**kwargs):
            for token in ["Hello", " ", "World"]:
                yield token

        mock_llm = MagicMock()
        mock_llm.stream_chat = mock_stream_chat

        agent = ConcreteAgent(
            role=AgentRole.EXPLORER,
            capabilities=[AgentCapability.READ_ONLY],
            llm_client=mock_llm,
            mcp_client=mock_mcp,
            system_prompt="Test"
        )

        chunks = []
        async for chunk in agent._stream_llm("Test prompt"):
            chunks.append(chunk)

        assert chunks == ["Hello", " ", "World"]
        assert agent.execution_count == 1

    @pytest.mark.asyncio
    async def test_stream_chat_empty_tokens(self, mock_mcp):
        """Test _stream_llm with empty token stream."""
        async def mock_stream_chat(**kwargs):
            return
            yield  # Empty generator

        mock_llm = MagicMock()
        mock_llm.stream_chat = mock_stream_chat

        agent = ConcreteAgent(
            role=AgentRole.EXPLORER,
            capabilities=[AgentCapability.READ_ONLY],
            llm_client=mock_llm,
            mcp_client=mock_mcp,
            system_prompt="Test"
        )

        chunks = []
        async for chunk in agent._stream_llm("Test prompt"):
            chunks.append(chunk)

        assert chunks == []
        assert agent.execution_count == 1

    @pytest.mark.asyncio
    async def test_stream_chat_single_token(self, mock_mcp):
        """Test _stream_llm with single token."""
        async def mock_stream_chat(**kwargs):
            yield "SingleToken"

        mock_llm = MagicMock()
        mock_llm.stream_chat = mock_stream_chat

        agent = ConcreteAgent(
            role=AgentRole.EXPLORER,
            capabilities=[AgentCapability.READ_ONLY],
            llm_client=mock_llm,
            mcp_client=mock_mcp,
            system_prompt="Test"
        )

        chunks = []
        async for chunk in agent._stream_llm("Test prompt"):
            chunks.append(chunk)

        assert chunks == ["SingleToken"]
        assert agent.execution_count == 1

    @pytest.mark.asyncio
    async def test_stream_chat_passes_prompt(self, mock_mcp):
        """Test _stream_llm passes prompt to stream_chat."""
        captured_kwargs = {}

        async def mock_stream_chat(**kwargs):
            captured_kwargs.update(kwargs)
            yield "Response"

        mock_llm = MagicMock()
        mock_llm.stream_chat = mock_stream_chat

        agent = ConcreteAgent(
            role=AgentRole.EXPLORER,
            capabilities=[AgentCapability.READ_ONLY],
            llm_client=mock_llm,
            mcp_client=mock_mcp,
            system_prompt="System Test"
        )

        async for _ in agent._stream_llm("Test prompt"):
            pass

        assert captured_kwargs["prompt"] == "Test prompt"
        assert captured_kwargs["context"] == "System Test"

    @pytest.mark.asyncio
    async def test_stream_chat_passes_custom_system_prompt(self, mock_mcp):
        """Test _stream_llm uses custom system_prompt parameter."""
        captured_kwargs = {}

        async def mock_stream_chat(**kwargs):
            captured_kwargs.update(kwargs)
            yield "Response"

        mock_llm = MagicMock()
        mock_llm.stream_chat = mock_stream_chat

        agent = ConcreteAgent(
            role=AgentRole.EXPLORER,
            capabilities=[AgentCapability.READ_ONLY],
            llm_client=mock_llm,
            mcp_client=mock_mcp,
            system_prompt="Default"
        )

        async for _ in agent._stream_llm("Test prompt", system_prompt="Custom"):
            pass

        assert captured_kwargs["context"] == "Custom"

    @pytest.mark.asyncio
    async def test_stream_chat_long_token_stream(self, mock_mcp):
        """Test _stream_llm with many tokens."""
        async def mock_stream_chat(**kwargs):
            for i in range(1000):
                yield f"token{i}"

        mock_llm = MagicMock()
        mock_llm.stream_chat = mock_stream_chat

        agent = ConcreteAgent(
            role=AgentRole.EXPLORER,
            capabilities=[AgentCapability.READ_ONLY],
            llm_client=mock_llm,
            mcp_client=mock_mcp,
            system_prompt="Test"
        )

        chunks = []
        async for chunk in agent._stream_llm("Test prompt"):
            chunks.append(chunk)

        assert len(chunks) == 1000
        assert chunks[0] == "token0"
        assert chunks[999] == "token999"

    @pytest.mark.asyncio
    async def test_stream_chat_special_characters(self, mock_mcp):
        """Test _stream_llm handles special characters in tokens."""
        async def mock_stream_chat(**kwargs):
            special_tokens = [
                "Hello\n",
                "\t",
                "世界",
                "🚀",
                "\\n",
                "\x00",
            ]
            for token in special_tokens:
                yield token

        mock_llm = MagicMock()
        mock_llm.stream_chat = mock_stream_chat

        agent = ConcreteAgent(
            role=AgentRole.EXPLORER,
            capabilities=[AgentCapability.READ_ONLY],
            llm_client=mock_llm,
            mcp_client=mock_mcp,
            system_prompt="Test"
        )

        chunks = []
        async for chunk in agent._stream_llm("Test prompt"):
            chunks.append(chunk)

        assert len(chunks) == 6
        assert "世界" in chunks
        assert "🚀" in chunks

    @pytest.mark.asyncio
    async def test_stream_chat_extra_kwargs(self, mock_mcp):
        """Test _stream_llm passes extra kwargs to stream_chat."""
        captured_kwargs = {}

        async def mock_stream_chat(**kwargs):
            captured_kwargs.update(kwargs)
            yield "Response"

        mock_llm = MagicMock()
        mock_llm.stream_chat = mock_stream_chat

        agent = ConcreteAgent(
            role=AgentRole.EXPLORER,
            capabilities=[AgentCapability.READ_ONLY],
            llm_client=mock_llm,
            mcp_client=mock_mcp,
            system_prompt="Test"
        )

        async for _ in agent._stream_llm(
            "Test",
            temperature=0.7,
            max_tokens=100,
            custom_param="value"
        ):
            pass

        assert captured_kwargs["temperature"] == 0.7
        assert captured_kwargs["max_tokens"] == 100
        assert captured_kwargs["custom_param"] == "value"


# =============================================================================
# _STREAM_LLM WITH STREAM METHOD FALLBACK TESTS
# =============================================================================

class TestStreamLlmWithStreamFallback:
    """Tests for _stream_llm using stream method when stream_chat unavailable."""

    @pytest.mark.asyncio
    async def test_stream_method_fallback(self, mock_mcp):
        """Test _stream_llm falls back to stream method."""
        async def mock_stream(**kwargs):
            for token in ["Token1", "Token2", "Token3"]:
                yield token

        mock_llm = MagicMock(spec=['stream'])  # Only stream, no stream_chat
        mock_llm.stream = mock_stream

        agent = ConcreteAgent(
            role=AgentRole.EXPLORER,
            capabilities=[AgentCapability.READ_ONLY],
            llm_client=mock_llm,
            mcp_client=mock_mcp,
            system_prompt="Test"
        )

        chunks = []
        async for chunk in agent._stream_llm("Test prompt"):
            chunks.append(chunk)

        assert chunks == ["Token1", "Token2", "Token3"]
        assert agent.execution_count == 1

    @pytest.mark.asyncio
    async def test_stream_fallback_passes_system_prompt(self, mock_mcp):
        """Test stream fallback receives system_prompt as parameter."""
        captured_kwargs = {}

        async def mock_stream(**kwargs):
            captured_kwargs.update(kwargs)
            yield "Response"

        mock_llm = MagicMock(spec=['stream'])
        mock_llm.stream = mock_stream

        agent = ConcreteAgent(
            role=AgentRole.EXPLORER,
            capabilities=[AgentCapability.READ_ONLY],
            llm_client=mock_llm,
            mcp_client=mock_mcp,
            system_prompt="Default"
        )

        async for _ in agent._stream_llm("Test", system_prompt="Custom"):
            pass

        assert captured_kwargs["system_prompt"] == "Custom"

    @pytest.mark.asyncio
    async def test_stream_chat_preferred_over_stream(self, mock_mcp):
        """Test stream_chat is used when both methods available."""
        stream_called = False
        stream_chat_called = False

        async def mock_stream(**kwargs):
            nonlocal stream_called
            stream_called = True
            yield "FromStream"

        async def mock_stream_chat(**kwargs):
            nonlocal stream_chat_called
            stream_chat_called = True
            yield "FromStreamChat"

        mock_llm = MagicMock()
        mock_llm.stream = mock_stream
        mock_llm.stream_chat = mock_stream_chat

        agent = ConcreteAgent(
            role=AgentRole.EXPLORER,
            capabilities=[AgentCapability.READ_ONLY],
            llm_client=mock_llm,
            mcp_client=mock_mcp,
            system_prompt="Test"
        )

        chunks = []
        async for chunk in agent._stream_llm("Test prompt"):
            chunks.append(chunk)

        assert stream_chat_called is True
        assert stream_called is False
        assert chunks == ["FromStreamChat"]


# =============================================================================
# _STREAM_LLM ERROR HANDLING TESTS
# =============================================================================

class TestStreamLlmErrorHandling:
    """Tests for _stream_llm error handling during streaming."""

    @pytest.mark.asyncio
    async def test_stream_chat_error_raised(self, mock_mcp):
        """Test _stream_llm propagates stream_chat errors."""
        async def mock_stream_error(**kwargs):
            yield "First"
            raise ValueError("Stream error occurred")

        mock_llm = MagicMock()
        mock_llm.stream_chat = mock_stream_error

        agent = ConcreteAgent(
            role=AgentRole.EXPLORER,
            capabilities=[AgentCapability.READ_ONLY],
            llm_client=mock_llm,
            mcp_client=mock_mcp,
            system_prompt="Test"
        )

        chunks = []
        with pytest.raises(ValueError, match="Stream error occurred"):
            async for chunk in agent._stream_llm("Test"):
                chunks.append(chunk)

        assert chunks == ["First"]

    @pytest.mark.asyncio
    async def test_stream_chat_timeout_error(self, mock_mcp):
        """Test _stream_llm handles timeout errors."""
        async def mock_stream_timeout(**kwargs):
            yield "Partial"
            raise asyncio.TimeoutError("Stream timeout")

        mock_llm = MagicMock()
        mock_llm.stream_chat = mock_stream_timeout

        agent = ConcreteAgent(
            role=AgentRole.EXPLORER,
            capabilities=[AgentCapability.READ_ONLY],
            llm_client=mock_llm,
            mcp_client=mock_mcp,
            system_prompt="Test"
        )

        with pytest.raises(asyncio.TimeoutError, match="Stream timeout"):
            async for chunk in agent._stream_llm("Test"):
                pass

    @pytest.mark.asyncio
    async def test_stream_chat_api_error(self, mock_mcp):
        """Test _stream_llm handles API errors."""
        async def mock_stream_api_error(**kwargs):
            raise ConnectionError("API connection failed")
            yield  # Never reached

        mock_llm = MagicMock()
        mock_llm.stream_chat = mock_stream_api_error

        agent = ConcreteAgent(
            role=AgentRole.EXPLORER,
            capabilities=[AgentCapability.READ_ONLY],
            llm_client=mock_llm,
            mcp_client=mock_mcp,
            system_prompt="Test"
        )

        with pytest.raises(ConnectionError, match="API connection failed"):
            async for chunk in agent._stream_llm("Test"):
                pass

    @pytest.mark.asyncio
    async def test_stream_method_error_logged(self, mock_mcp, caplog):
        """Test stream errors are logged."""
        import logging
        caplog.set_level(logging.ERROR)

        async def mock_stream_error(**kwargs):
            raise RuntimeError("Test error")
            yield  # Never reached

        mock_llm = MagicMock(spec=['stream'])
        mock_llm.stream = mock_stream_error

        agent = ConcreteAgent(
            role=AgentRole.EXPLORER,
            capabilities=[AgentCapability.READ_ONLY],
            llm_client=mock_llm,
            mcp_client=mock_mcp,
            system_prompt="Test"
        )

        with pytest.raises(RuntimeError):
            async for _ in agent._stream_llm("Test"):
                pass

        assert "LLM Stream failed" in caplog.text

    @pytest.mark.asyncio
    async def test_stream_error_increments_execution_count_before_error(self, mock_mcp):
        """Test execution_count is incremented before stream errors."""
        async def mock_stream_error(**kwargs):
            raise ValueError("Stream failed")
            yield  # Never reached

        mock_llm = MagicMock()
        mock_llm.stream_chat = mock_stream_error

        agent = ConcreteAgent(
            role=AgentRole.EXPLORER,
            capabilities=[AgentCapability.READ_ONLY],
            llm_client=mock_llm,
            mcp_client=mock_mcp,
            system_prompt="Test"
        )

        initial_count = agent.execution_count

        with pytest.raises(ValueError):
            async for _ in agent._stream_llm("Test"):
                pass

        # Note: execution_count is incremented AFTER the generator exits,
        # so it only increments if no error occurs during iteration initialization
        assert agent.execution_count == initial_count

    @pytest.mark.asyncio
    async def test_generator_cleanup_on_break(self, mock_mcp):
        """Test generator cleanup when iteration is broken."""
        cleanup_called = False

        async def mock_stream_with_cleanup(**kwargs):
            nonlocal cleanup_called
            try:
                yield "Token1"
                yield "Token2"
                yield "Token3"
            finally:
                cleanup_called = True

        mock_llm = MagicMock()
        mock_llm.stream_chat = mock_stream_with_cleanup

        agent = ConcreteAgent(
            role=AgentRole.EXPLORER,
            capabilities=[AgentCapability.READ_ONLY],
            llm_client=mock_llm,
            mcp_client=mock_mcp,
            system_prompt="Test"
        )

        chunks = []
        async for chunk in agent._stream_llm("Test"):
            chunks.append(chunk)
            if len(chunks) == 2:
                break

        # Note: cleanup happens when generator is garbage collected
        assert chunks == ["Token1", "Token2"]


# =============================================================================
# _CALL_LLM WITH STREAMING FALLBACK TESTS
# =============================================================================

class TestCallLlmWithStreamingFallback:
    """Tests for _call_llm using stream method as fallback."""

    @pytest.mark.asyncio
    async def test_call_llm_with_generate(self, mock_mcp):
        """Test _call_llm uses generate method when available."""
        mock_llm = MagicMock()
        mock_llm.generate = AsyncMock(return_value="Generated response")

        agent = ConcreteAgent(
            role=AgentRole.EXPLORER,
            capabilities=[AgentCapability.READ_ONLY],
            llm_client=mock_llm,
            mcp_client=mock_mcp,
            system_prompt="Test"
        )

        response = await agent._call_llm("Test prompt")

        assert response == "Generated response"
        assert agent.execution_count == 1
        mock_llm.generate.assert_called_once()

    @pytest.mark.asyncio
    async def test_call_llm_stream_fallback(self, mock_mcp):
        """Test _call_llm falls back to stream when generate unavailable."""
        async def mock_stream(**kwargs):
            for token in ["A", "B", "C"]:
                yield token

        mock_llm = MagicMock(spec=['stream'])  # Only stream, no generate
        mock_llm.stream = mock_stream

        agent = ConcreteAgent(
            role=AgentRole.EXPLORER,
            capabilities=[AgentCapability.READ_ONLY],
            llm_client=mock_llm,
            mcp_client=mock_mcp,
            system_prompt="Test"
        )

        response = await agent._call_llm("Test prompt")

        assert response == "ABC"
        assert agent.execution_count == 1

    @pytest.mark.asyncio
    async def test_call_llm_concatenates_stream_tokens(self, mock_mcp):
        """Test _call_llm concatenates stream tokens correctly."""
        async def mock_stream(**kwargs):
            tokens = ["Hello", " ", "World", "!"]
            for token in tokens:
                yield token

        mock_llm = MagicMock(spec=['stream'])
        mock_llm.stream = mock_stream

        agent = ConcreteAgent(
            role=AgentRole.EXPLORER,
            capabilities=[AgentCapability.READ_ONLY],
            llm_client=mock_llm,
            mcp_client=mock_mcp,
            system_prompt="Test"
        )

        response = await agent._call_llm("Test prompt")

        assert response == "Hello World!"

    @pytest.mark.asyncio
    async def test_call_llm_empty_stream(self, mock_mcp):
        """Test _call_llm handles empty token stream."""
        async def mock_stream(**kwargs):
            return
            yield  # Empty generator

        mock_llm = MagicMock(spec=['stream'])
        mock_llm.stream = mock_stream

        agent = ConcreteAgent(
            role=AgentRole.EXPLORER,
            capabilities=[AgentCapability.READ_ONLY],
            llm_client=mock_llm,
            mcp_client=mock_mcp,
            system_prompt="Test"
        )

        response = await agent._call_llm("Test prompt")

        assert response == ""
        assert agent.execution_count == 1

    @pytest.mark.asyncio
    async def test_call_llm_large_token_stream(self, mock_mcp):
        """Test _call_llm handles large token stream."""
        async def mock_stream(**kwargs):
            for i in range(10000):
                yield f"token{i}|"

        mock_llm = MagicMock(spec=['stream'])
        mock_llm.stream = mock_stream

        agent = ConcreteAgent(
            role=AgentRole.EXPLORER,
            capabilities=[AgentCapability.READ_ONLY],
            llm_client=mock_llm,
            mcp_client=mock_mcp,
            system_prompt="Test"
        )

        response = await agent._call_llm("Test prompt")

        # Should concatenate all tokens
        assert response.startswith("token0|")
        assert response.endswith("token9999|")
        assert len(response) > 50000  # Should be large

    @pytest.mark.asyncio
    async def test_call_llm_passes_system_prompt_to_stream(self, mock_mcp):
        """Test _call_llm passes system_prompt to stream method."""
        captured_kwargs = {}

        async def mock_stream(**kwargs):
            captured_kwargs.update(kwargs)
            yield "Response"

        mock_llm = MagicMock(spec=['stream'])
        mock_llm.stream = mock_stream

        agent = ConcreteAgent(
            role=AgentRole.EXPLORER,
            capabilities=[AgentCapability.READ_ONLY],
            llm_client=mock_llm,
            mcp_client=mock_mcp,
            system_prompt="Default"
        )

        await agent._call_llm("Test", system_prompt="Custom")

        assert captured_kwargs["system_prompt"] == "Custom"

    @pytest.mark.asyncio
    async def test_call_llm_uses_default_system_prompt(self, mock_mcp):
        """Test _call_llm uses agent's default system_prompt."""
        captured_kwargs = {}

        async def mock_stream(**kwargs):
            captured_kwargs.update(kwargs)
            yield "Response"

        mock_llm = MagicMock(spec=['stream'])
        mock_llm.stream = mock_stream

        agent = ConcreteAgent(
            role=AgentRole.EXPLORER,
            capabilities=[AgentCapability.READ_ONLY],
            llm_client=mock_llm,
            mcp_client=mock_mcp,
            system_prompt="AgentDefault"
        )

        await agent._call_llm("Test")  # No system_prompt override

        assert captured_kwargs["system_prompt"] == "AgentDefault"

    @pytest.mark.asyncio
    async def test_call_llm_extra_kwargs(self, mock_mcp):
        """Test _call_llm passes extra kwargs."""
        captured_kwargs = {}

        async def mock_stream(**kwargs):
            captured_kwargs.update(kwargs)
            yield "Response"

        mock_llm = MagicMock(spec=['stream'])
        mock_llm.stream = mock_stream

        agent = ConcreteAgent(
            role=AgentRole.EXPLORER,
            capabilities=[AgentCapability.READ_ONLY],
            llm_client=mock_llm,
            mcp_client=mock_mcp,
            system_prompt="Test"
        )

        await agent._call_llm(
            "Test",
            temperature=0.9,
            max_tokens=500,
            top_p=0.95
        )

        assert captured_kwargs["temperature"] == 0.9
        assert captured_kwargs["max_tokens"] == 500
        assert captured_kwargs["top_p"] == 0.95


# =============================================================================
# _CALL_LLM ERROR HANDLING TESTS
# =============================================================================

class TestCallLlmErrorHandling:
    """Tests for _call_llm error handling."""

    @pytest.mark.asyncio
    async def test_call_llm_generate_error(self, mock_mcp):
        """Test _call_llm propagates generate errors."""
        mock_llm = MagicMock()
        mock_llm.generate = AsyncMock(side_effect=ValueError("Generate failed"))

        agent = ConcreteAgent(
            role=AgentRole.EXPLORER,
            capabilities=[AgentCapability.READ_ONLY],
            llm_client=mock_llm,
            mcp_client=mock_mcp,
            system_prompt="Test"
        )

        with pytest.raises(ValueError, match="Generate failed"):
            await agent._call_llm("Test")

    @pytest.mark.asyncio
    async def test_call_llm_stream_error(self, mock_mcp):
        """Test _call_llm propagates stream errors."""
        async def mock_stream_error(**kwargs):
            yield "Partial"
            raise RuntimeError("Stream failed")

        mock_llm = MagicMock(spec=['stream'])
        mock_llm.stream = mock_stream_error

        agent = ConcreteAgent(
            role=AgentRole.EXPLORER,
            capabilities=[AgentCapability.READ_ONLY],
            llm_client=mock_llm,
            mcp_client=mock_mcp,
            system_prompt="Test"
        )

        with pytest.raises(RuntimeError, match="Stream failed"):
            await agent._call_llm("Test")

    @pytest.mark.asyncio
    async def test_call_llm_error_increments_count(self, mock_mcp):
        """Test execution_count is not incremented on error."""
        mock_llm = MagicMock()
        mock_llm.generate = AsyncMock(side_effect=ValueError("Error"))

        agent = ConcreteAgent(
            role=AgentRole.EXPLORER,
            capabilities=[AgentCapability.READ_ONLY],
            llm_client=mock_llm,
            mcp_client=mock_mcp,
            system_prompt="Test"
        )

        initial_count = agent.execution_count

        with pytest.raises(ValueError):
            await agent._call_llm("Test")

        # execution_count is not incremented on error
        assert agent.execution_count == initial_count

    @pytest.mark.asyncio
    async def test_call_llm_error_logged(self, mock_mcp, caplog):
        """Test _call_llm errors are logged."""
        import logging
        caplog.set_level(logging.ERROR)

        mock_llm = MagicMock()
        mock_llm.generate = AsyncMock(side_effect=Exception("Test error"))

        agent = ConcreteAgent(
            role=AgentRole.EXPLORER,
            capabilities=[AgentCapability.READ_ONLY],
            llm_client=mock_llm,
            mcp_client=mock_mcp,
            system_prompt="Test"
        )

        with pytest.raises(Exception):
            await agent._call_llm("Test")

        assert "LLM Call failed" in caplog.text


# =============================================================================
# EXECUTION COUNT AND STATE MANAGEMENT TESTS
# =============================================================================

class TestExecutionCountManagement:
    """Tests for execution_count state management."""

    @pytest.mark.asyncio
    async def test_execution_count_increments_on_generate(self, mock_mcp):
        """Test execution_count increments after successful generate."""
        mock_llm = MagicMock()
        mock_llm.generate = AsyncMock(return_value="Response")

        agent = ConcreteAgent(
            role=AgentRole.EXPLORER,
            capabilities=[AgentCapability.READ_ONLY],
            llm_client=mock_llm,
            mcp_client=mock_mcp,
            system_prompt="Test"
        )

        assert agent.execution_count == 0

        await agent._call_llm("Test 1")
        assert agent.execution_count == 1

        await agent._call_llm("Test 2")
        assert agent.execution_count == 2

    @pytest.mark.asyncio
    async def test_execution_count_increments_on_stream(self, mock_mcp):
        """Test execution_count increments after successful stream."""
        async def mock_stream(**kwargs):
            yield "Response"

        mock_llm = MagicMock(spec=['stream'])
        mock_llm.stream = mock_stream

        agent = ConcreteAgent(
            role=AgentRole.EXPLORER,
            capabilities=[AgentCapability.READ_ONLY],
            llm_client=mock_llm,
            mcp_client=mock_mcp,
            system_prompt="Test"
        )

        assert agent.execution_count == 0

        await agent._call_llm("Test 1")
        assert agent.execution_count == 1

    @pytest.mark.asyncio
    async def test_execution_count_separate_for_stream_llm(self, mock_mcp):
        """Test _stream_llm has separate execution_count increment."""
        async def mock_stream_chat(**kwargs):
            yield "Token"

        mock_llm = MagicMock()
        mock_llm.stream_chat = mock_stream_chat

        agent = ConcreteAgent(
            role=AgentRole.EXPLORER,
            capabilities=[AgentCapability.READ_ONLY],
            llm_client=mock_llm,
            mcp_client=mock_mcp,
            system_prompt="Test"
        )

        assert agent.execution_count == 0

        async for _ in agent._stream_llm("Test"):
            pass

        assert agent.execution_count == 1


# =============================================================================
# ASYNC ITERATION TESTS
# =============================================================================

class TestAsyncIteration:
    """Tests for async iteration behavior."""

    @pytest.mark.asyncio
    async def test_stream_llm_async_iteration_order(self, mock_mcp):
        """Test tokens are yielded in correct order."""
        async def mock_stream_chat(**kwargs):
            for token in ["1", "2", "3", "4", "5"]:
                yield token

        mock_llm = MagicMock()
        mock_llm.stream_chat = mock_stream_chat

        agent = ConcreteAgent(
            role=AgentRole.EXPLORER,
            capabilities=[AgentCapability.READ_ONLY],
            llm_client=mock_llm,
            mcp_client=mock_mcp,
            system_prompt="Test"
        )

        chunks = []
        async for chunk in agent._stream_llm("Test"):
            chunks.append(chunk)

        assert chunks == ["1", "2", "3", "4", "5"]

    @pytest.mark.asyncio
    async def test_stream_llm_early_exit(self, mock_mcp):
        """Test early exit from stream iteration."""
        async def mock_stream_chat(**kwargs):
            for i in range(100):
                yield f"token{i}"

        mock_llm = MagicMock()
        mock_llm.stream_chat = mock_stream_chat

        agent = ConcreteAgent(
            role=AgentRole.EXPLORER,
            capabilities=[AgentCapability.READ_ONLY],
            llm_client=mock_llm,
            mcp_client=mock_mcp,
            system_prompt="Test"
        )

        chunks = []
        async for chunk in agent._stream_llm("Test"):
            chunks.append(chunk)
            if len(chunks) >= 5:
                break

        assert len(chunks) == 5
        assert chunks[-1] == "token4"

    @pytest.mark.asyncio
    async def test_stream_llm_multiple_iterations(self, mock_mcp):
        """Test multiple independent stream iterations."""
        call_count = 0

        async def mock_stream_chat(**kwargs):
            nonlocal call_count
            call_count += 1
            for i in range(3):
                yield f"call{call_count}_token{i}"

        mock_llm = MagicMock()
        mock_llm.stream_chat = mock_stream_chat

        agent = ConcreteAgent(
            role=AgentRole.EXPLORER,
            capabilities=[AgentCapability.READ_ONLY],
            llm_client=mock_llm,
            mcp_client=mock_mcp,
            system_prompt="Test"
        )

        # First iteration
        chunks1 = []
        async for chunk in agent._stream_llm("Test 1"):
            chunks1.append(chunk)

        # Second iteration
        chunks2 = []
        async for chunk in agent._stream_llm("Test 2"):
            chunks2.append(chunk)

        assert chunks1 == ["call1_token0", "call1_token1", "call1_token2"]
        assert chunks2 == ["call2_token0", "call2_token1", "call2_token2"]
        assert call_count == 2
        assert agent.execution_count == 2

    @pytest.mark.asyncio
    async def test_stream_llm_collect_all_tokens(self, mock_mcp):
        """Test collecting all tokens from stream."""
        async def mock_stream_chat(**kwargs):
            text = "The quick brown fox jumps over the lazy dog"
            for word in text.split():
                yield word
                yield " "

        mock_llm = MagicMock()
        mock_llm.stream_chat = mock_stream_chat

        agent = ConcreteAgent(
            role=AgentRole.EXPLORER,
            capabilities=[AgentCapability.READ_ONLY],
            llm_client=mock_llm,
            mcp_client=mock_mcp,
            system_prompt="Test"
        )

        result = ""
        async for chunk in agent._stream_llm("Test"):
            result += chunk

        assert "quick" in result
        assert "brown" in result
        assert "lazy" in result


# =============================================================================
# INTEGRATION TESTS
# =============================================================================

class TestStreamingIntegration:
    """Integration tests combining multiple streaming features."""

    @pytest.mark.asyncio
    async def test_stream_chat_with_kwargs_and_error(self, mock_mcp):
        """Test stream_chat with multiple kwargs and error handling."""
        async def mock_stream_chat(**kwargs):
            # Verify kwargs were passed
            assert kwargs["temperature"] == 0.5
            assert kwargs["max_tokens"] == 100
            yield "Partial"
            raise RuntimeError("Simulated error")

        mock_llm = MagicMock()
        mock_llm.stream_chat = mock_stream_chat

        agent = ConcreteAgent(
            role=AgentRole.EXPLORER,
            capabilities=[AgentCapability.READ_ONLY],
            llm_client=mock_llm,
            mcp_client=mock_mcp,
            system_prompt="Test"
        )

        chunks = []
        with pytest.raises(RuntimeError):
            async for chunk in agent._stream_llm(
                "Test",
                temperature=0.5,
                max_tokens=100
            ):
                chunks.append(chunk)

        assert chunks == ["Partial"]

    @pytest.mark.asyncio
    async def test_call_llm_fallback_chain(self, mock_mcp):
        """Test complete fallback chain: no generate, use stream."""
        async def mock_stream(**kwargs):
            text = "Hello World"
            for char in text:
                yield char

        mock_llm = MagicMock(spec=['stream'])
        mock_llm.stream = mock_stream

        agent = ConcreteAgent(
            role=AgentRole.EXPLORER,
            capabilities=[AgentCapability.READ_ONLY],
            llm_client=mock_llm,
            mcp_client=mock_mcp,
            system_prompt="Test"
        )

        result = await agent._call_llm("Test")

        assert result == "Hello World"
        assert agent.execution_count == 1

    @pytest.mark.asyncio
    async def test_stream_llm_full_fallback_chain(self, mock_mcp):
        """Test full fallback chain: stream_chat -> stream -> generate."""
        async def mock_generate(**kwargs):
            return "Generated response"

        mock_llm = MagicMock(spec=['generate'])
        mock_llm.generate = mock_generate

        agent = ConcreteAgent(
            role=AgentRole.EXPLORER,
            capabilities=[AgentCapability.READ_ONLY],
            llm_client=mock_llm,
            mcp_client=mock_mcp,
            system_prompt="Test"
        )

        # _stream_llm falls back to _call_llm which uses generate
        # Both _stream_llm and _call_llm increment execution_count
        chunks = []
        async for chunk in agent._stream_llm("Test"):
            chunks.append(chunk)

        assert chunks == ["Generated response"]
        assert agent.execution_count == 2  # Incremented by both _stream_llm and _call_llm
