"""
Edge case testing for BaseAgent.

Tests cover:
    - Boundary conditions
    - Error propagation
    - State management edge cases
    - Capability edge cases
    - Concurrent operations
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from jdev_cli.agents.base import (
    AgentCapability,
    AgentRole,
    AgentTask,
    AgentResponse,
    BaseAgent,
    CapabilityViolationError,
)


class TestAgent(BaseAgent):
    """Test implementation."""

    async def execute(self, task: AgentTask) -> AgentResponse:
        return AgentResponse(success=True, reasoning="Test")


class TestAgentTaskEdgeCases:
    """Edge cases for AgentTask model."""

    def test_task_with_empty_context(self) -> None:
        """Test task with explicitly empty context."""
        task = AgentTask(request="Test", session_id="s1", context={})
        assert task.context == {}

    def test_task_with_nested_context(self) -> None:
        """Test task with deeply nested context."""
        task = AgentTask(
            request="Test",
            session_id="s1",
            context={
                "level1": {
                    "level2": {"level3": {"data": "deep"}},
                },
            },
        )
        assert task.context["level1"]["level2"]["level3"]["data"] == "deep"

    def test_task_with_large_context(self) -> None:
        """Test task with large context dictionary."""
        large_context = {f"key_{i}": f"value_{i}" for i in range(1000)}
        task = AgentTask(
            request="Test",
            session_id="s1",
            context=large_context,
        )
        assert len(task.context) == 1000

    def test_task_with_special_characters_in_request(self) -> None:
        """Test task with special characters."""
        special_chars = "Test with 'quotes' and \"double\" and \n newlines"
        task = AgentTask(request=special_chars, session_id="s1")
        assert task.request == special_chars

    def test_task_with_unicode_characters(self) -> None:
        """Test task with unicode characters."""
        unicode_request = "Adicionar autenticação JWT 🔐 com tokens 中文"
        task = AgentTask(request=unicode_request, session_id="s1")
        assert task.request == unicode_request

    def test_task_with_very_long_request(self) -> None:
        """Test task with very long request string."""
        long_request = "A" * 10000
        task = AgentTask(request=long_request, session_id="s1")
        assert len(task.request) == 10000

    def test_task_session_id_format(self) -> None:
        """Test various session ID formats."""
        formats = [
            "simple",
            "with-dashes",
            "with_underscores",
            "WITH-CAPS",
            "123-numeric",
            "uuid-abc-123-def-456",
        ]
        for session_id in formats:
            task = AgentTask(request="Test", session_id=session_id)
            assert task.session_id == session_id

    def test_task_metadata_types(self) -> None:
        """Test metadata with various types."""
        task = AgentTask(
            request="Test",
            session_id="s1",
            metadata={
                "string": "value",
                "int": 42,
                "float": 3.14,
                "bool": True,
                "list": [1, 2, 3],
                "dict": {"nested": "value"},
                "none": None,
            },
        )
        assert task.metadata["int"] == 42
        assert task.metadata["float"] == 3.14
        assert task.metadata["bool"] is True


class TestAgentResponseEdgeCases:
    """Edge cases for AgentResponse model."""

    def test_response_with_empty_data(self) -> None:
        """Test response with empty data dict."""
        response = AgentResponse(success=True, reasoning="Test", data={})
        assert response.data == {}

    def test_response_with_large_data(self) -> None:
        """Test response with large data payload."""
        large_data = {f"result_{i}": f"value_{i}" for i in range(1000)}
        response = AgentResponse(
            success=True,
            reasoning="Test",
            data=large_data,
        )
        assert len(response.data) == 1000

    def test_response_with_error_but_success_true(self) -> None:
        """Test response with error field set but success=True."""
        response = AgentResponse(
            success=True,
            reasoning="Test",
            error="This should be ignored",
        )
        # Pydantic allows this, validation is in business logic
        assert response.success is True
        assert response.error == "This should be ignored"

    def test_response_with_very_long_reasoning(self) -> None:
        """Test response with very long reasoning."""
        long_reasoning = "Because " * 1000
        response = AgentResponse(success=True, reasoning=long_reasoning)
        assert len(response.reasoning) > 5000

    def test_response_with_multiline_reasoning(self) -> None:
        """Test response with multiline reasoning."""
        multiline = """
        Step 1: Analyzed the request
        Step 2: Generated plan
        Step 3: Executed successfully
        """
        response = AgentResponse(success=True, reasoning=multiline)
        assert "\n" in response.reasoning


class TestBaseAgentCapabilityEdgeCases:
    """Edge cases for capability enforcement."""

    def test_agent_with_empty_capabilities(self) -> None:
        """Test agent with no capabilities."""
        agent = TestAgent(
            role=AgentRole.PLANNER,
            capabilities=[],  # No capabilities
            llm_client=MagicMock(),
            mcp_client=MagicMock(),
        )
        assert agent._can_use_tool("read_file") is False
        assert agent._can_use_tool("write_file") is False

    def test_agent_with_all_capabilities(self) -> None:
        """Test agent with all possible capabilities."""
        agent = TestAgent(
            role=AgentRole.REFACTORER,
            capabilities=list(AgentCapability),  # All capabilities
            llm_client=MagicMock(),
            mcp_client=MagicMock(),
        )
        assert agent._can_use_tool("read_file") is True
        assert agent._can_use_tool("write_file") is True
        assert agent._can_use_tool("bash_command") is True
        assert agent._can_use_tool("git_commit") is True

    def test_agent_with_duplicate_capabilities(self) -> None:
        """Test agent with duplicate capabilities in list."""
        agent = TestAgent(
            role=AgentRole.ARCHITECT,
            capabilities=[
                AgentCapability.READ_ONLY,
                AgentCapability.READ_ONLY,  # Duplicate
            ],
            llm_client=MagicMock(),
            mcp_client=MagicMock(),
        )
        assert agent._can_use_tool("read_file") is True

    def test_can_use_tool_with_unknown_tool(self) -> None:
        """Test capability check for unknown/unmapped tool."""
        agent = TestAgent(
            role=AgentRole.ARCHITECT,
            capabilities=[AgentCapability.READ_ONLY],
            llm_client=MagicMock(),
            mcp_client=MagicMock(),
        )
        assert agent._can_use_tool("nonexistent_tool") is False
        assert agent._can_use_tool("") is False

    def test_can_use_tool_case_sensitivity(self) -> None:
        """Test that tool names are case-sensitive."""
        agent = TestAgent(
            role=AgentRole.ARCHITECT,
            capabilities=[AgentCapability.READ_ONLY],
            llm_client=MagicMock(),
            mcp_client=MagicMock(),
        )
        assert agent._can_use_tool("read_file") is True
        assert agent._can_use_tool("READ_FILE") is False
        assert agent._can_use_tool("Read_File") is False


class TestBaseAgentStateEdgeCases:
    """Edge cases for agent state management."""

    def test_execution_count_increments_correctly(self) -> None:
        """Test that execution count increments on each LLM call."""
        agent = TestAgent(
            role=AgentRole.PLANNER,
            capabilities=[AgentCapability.DESIGN],
            llm_client=MagicMock(),
            mcp_client=MagicMock(),
        )
        assert agent.execution_count == 0

    @pytest.mark.asyncio
    async def test_execution_count_multiple_calls(self) -> None:
        """Test execution count with multiple LLM calls."""
        llm_client = MagicMock()
        llm_client.generate = AsyncMock(return_value="Response")

        agent = TestAgent(
            role=AgentRole.PLANNER,
            capabilities=[AgentCapability.DESIGN],
            llm_client=llm_client,
            mcp_client=MagicMock(),
        )

        await agent._call_llm("Prompt 1")
        assert agent.execution_count == 1

        await agent._call_llm("Prompt 2")
        assert agent.execution_count == 2

        await agent._call_llm("Prompt 3")
        assert agent.execution_count == 3

    def test_agent_with_empty_system_prompt(self) -> None:
        """Test agent with empty system prompt."""
        agent = TestAgent(
            role=AgentRole.ARCHITECT,
            capabilities=[AgentCapability.READ_ONLY],
            llm_client=MagicMock(),
            mcp_client=MagicMock(),
            system_prompt="",
        )
        assert agent.system_prompt == ""

    def test_agent_with_very_long_system_prompt(self) -> None:
        """Test agent with very long system prompt."""
        long_prompt = "You are an expert. " * 1000
        agent = TestAgent(
            role=AgentRole.ARCHITECT,
            capabilities=[AgentCapability.READ_ONLY],
            llm_client=MagicMock(),
            mcp_client=MagicMock(),
            system_prompt=long_prompt,
        )
        assert len(agent.system_prompt) > 10000


class TestBaseAgentLLMEdgeCases:
    """Edge cases for LLM integration."""

    @pytest.mark.asyncio
    async def test_call_llm_with_empty_prompt(self) -> None:
        """Test LLM call with empty prompt."""
        llm_client = MagicMock()
        llm_client.generate = AsyncMock(return_value="Response")

        agent = TestAgent(
            role=AgentRole.PLANNER,
            capabilities=[AgentCapability.DESIGN],
            llm_client=llm_client,
            mcp_client=MagicMock(),
        )

        response = await agent._call_llm("")
        assert response == "Response"

    @pytest.mark.asyncio
    async def test_call_llm_with_override_system_prompt(self) -> None:
        """Test LLM call with system prompt override."""
        llm_client = MagicMock()
        llm_client.generate = AsyncMock(return_value="Response")

        agent = TestAgent(
            role=AgentRole.PLANNER,
            capabilities=[AgentCapability.DESIGN],
            llm_client=llm_client,
            mcp_client=MagicMock(),
            system_prompt="Original prompt",
        )

        await agent._call_llm("Test", system_prompt="Override prompt")

        llm_client.generate.assert_called_once()
        call_kwargs = llm_client.generate.call_args.kwargs
        assert call_kwargs["system_prompt"] == "Override prompt"

    @pytest.mark.asyncio
    async def test_call_llm_with_extra_kwargs(self) -> None:
        """Test LLM call with additional kwargs."""
        llm_client = MagicMock()
        llm_client.generate = AsyncMock(return_value="Response")

        agent = TestAgent(
            role=AgentRole.PLANNER,
            capabilities=[AgentCapability.DESIGN],
            llm_client=llm_client,
            mcp_client=MagicMock(),
        )

        await agent._call_llm(
            "Test",
            temperature=0.7,
            max_tokens=1000,
            custom_param="value",
        )

        call_kwargs = llm_client.generate.call_args.kwargs
        assert call_kwargs["temperature"] == 0.7
        assert call_kwargs["max_tokens"] == 1000
        assert call_kwargs["custom_param"] == "value"

    @pytest.mark.asyncio
    async def test_call_llm_propagates_exceptions(self) -> None:
        """Test that LLM exceptions propagate correctly."""
        llm_client = MagicMock()
        llm_client.generate = AsyncMock(side_effect=Exception("LLM error"))

        agent = TestAgent(
            role=AgentRole.PLANNER,
            capabilities=[AgentCapability.DESIGN],
            llm_client=llm_client,
            mcp_client=MagicMock(),
        )

        with pytest.raises(Exception, match="LLM error"):
            await agent._call_llm("Test")


class TestBaseAgentMCPEdgeCases:
    """Edge cases for MCP tool execution."""

    @pytest.mark.asyncio
    async def test_execute_tool_with_empty_parameters(self) -> None:
        """Test tool execution with empty parameters."""
        mcp_client = MagicMock()
        mcp_client.call_tool = AsyncMock(return_value={"result": "success"})

        agent = TestAgent(
            role=AgentRole.EXPLORER,
            capabilities=[AgentCapability.READ_ONLY],
            llm_client=MagicMock(),
            mcp_client=mcp_client,
        )

        result = await agent._execute_tool("read_file", {})
        assert result["result"] == "success"

    @pytest.mark.asyncio
    async def test_execute_tool_with_complex_parameters(self) -> None:
        """Test tool execution with nested parameters."""
        mcp_client = MagicMock()
        mcp_client.call_tool = AsyncMock(return_value={"result": "success"})

        agent = TestAgent(
            role=AgentRole.REFACTORER,
            capabilities=[AgentCapability.FILE_EDIT],
            llm_client=MagicMock(),
            mcp_client=mcp_client,
        )

        params = {
            "path": "/test/file.py",
            "options": {
                "encoding": "utf-8",
                "backup": True,
                "permissions": 0o644,
            },
        }

        result = await agent._execute_tool("write_file", params)
        assert result["result"] == "success"

    @pytest.mark.asyncio
    async def test_execute_tool_propagates_mcp_exceptions(self) -> None:
        """Test that MCP exceptions propagate correctly."""
        mcp_client = MagicMock()
        mcp_client.call_tool = AsyncMock(side_effect=Exception("MCP error"))

        agent = TestAgent(
            role=AgentRole.EXPLORER,
            capabilities=[AgentCapability.READ_ONLY],
            llm_client=MagicMock(),
            mcp_client=mcp_client,
        )

        with pytest.raises(Exception, match="MCP error"):
            await agent._execute_tool("read_file", {"path": "test.py"})

    @pytest.mark.asyncio
    async def test_execute_tool_capability_error_contains_details(self) -> None:
        """Test that capability violation error has useful details."""
        agent = TestAgent(
            role=AgentRole.ARCHITECT,
            capabilities=[AgentCapability.READ_ONLY],
            llm_client=MagicMock(),
            mcp_client=MagicMock(),
        )

        with pytest.raises(CapabilityViolationError) as exc_info:
            await agent._execute_tool("write_file", {"path": "test.py"})

        error_msg = str(exc_info.value)
        assert "architect" in error_msg
        assert "write_file" in error_msg
        assert "READ_ONLY" in error_msg or "read_only" in error_msg


class TestBaseAgentReprAndStr:
    """Edge cases for string representation."""

    def test_repr_with_no_executions(self) -> None:
        """Test repr with zero executions."""
        agent = TestAgent(
            role=AgentRole.ARCHITECT,
            capabilities=[AgentCapability.READ_ONLY],
            llm_client=MagicMock(),
            mcp_client=MagicMock(),
        )
        assert "executions=0" in repr(agent)

    def test_repr_with_multiple_capabilities(self) -> None:
        """Test repr with multiple capabilities."""
        agent = TestAgent(
            role=AgentRole.REFACTORER,
            capabilities=[
                AgentCapability.READ_ONLY,
                AgentCapability.FILE_EDIT,
                AgentCapability.BASH_EXEC,
                AgentCapability.GIT_OPS,
            ],
            llm_client=MagicMock(),
            mcp_client=MagicMock(),
        )
        repr_str = repr(agent)
        assert "read_only" in repr_str
        assert "file_edit" in repr_str
        assert "bash_exec" in repr_str
        assert "git_ops" in repr_str

    def test_repr_includes_class_name(self) -> None:
        """Test that repr includes the class name."""
        agent = TestAgent(
            role=AgentRole.PLANNER,
            capabilities=[AgentCapability.DESIGN],
            llm_client=MagicMock(),
            mcp_client=MagicMock(),
        )
        assert "TestAgent" in repr(agent)
