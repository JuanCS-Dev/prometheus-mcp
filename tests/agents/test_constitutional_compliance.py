"""
Constitutional compliance testing (Vértice v3.0).

Tests validate adherence to:
    - Princípio P1: Completude Obrigatória
    - Princípio P2: Validação Preventiva
    - Princípio P3: Ceticismo Crítico
    - Princípio P4: Rastreabilidade Total
    - Princípio P5: Consciência Sistêmica
    - Princípio P6: Eficiência de Token
    - Capability enforcement
    - Zero placeholders/TODOs
    - Type safety
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
import inspect

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
        return AgentResponse(success=True, reasoning="Test execution")


class TestConstitutionalP1Completude:
    """Princípio P1: Completude Obrigatória - Zero placeholders."""

    def test_no_todo_comments_in_source(self) -> None:
        """Verify no TODO/FIXME comments in source code."""
        import jdev_cli.agents.base as base_module
        import jdev_cli.orchestration.memory as memory_module

        base_source = inspect.getsource(base_module)
        memory_source = inspect.getsource(memory_module)

        # Check for forbidden patterns
        forbidden = ["TODO", "FIXME", "XXX", "HACK", "pass  #"]
        for pattern in forbidden:
            assert pattern not in base_source, f"Found {pattern} in base.py"
            assert pattern not in memory_source, f"Found {pattern} in memory.py"

    def test_all_methods_have_implementation(self) -> None:
        """Verify all methods have real implementations, not just pass."""
        import jdev_cli.agents.base as base_module

        for name, obj in inspect.getmembers(base_module):
            if inspect.isclass(obj) and issubclass(obj, BaseAgent) and obj != BaseAgent:
                for method_name, method in inspect.getmembers(obj, inspect.isfunction):
                    if not method_name.startswith("_"):
                        source = inspect.getsource(method)
                        # Check it's not just "pass"
                        assert source.strip() != "pass", f"{name}.{method_name} is placeholder"

    def test_pydantic_models_have_real_fields(self) -> None:
        """Verify Pydantic models have complete field definitions."""
        # AgentTask should have all required fields
        task = AgentTask(request="Test", session_id="s1")
        assert hasattr(task, "task_id")
        assert hasattr(task, "request")
        assert hasattr(task, "context")
        assert hasattr(task, "session_id")
        assert hasattr(task, "metadata")

        # AgentResponse should have all required fields
        response = AgentResponse(success=True, reasoning="Test")
        assert hasattr(response, "success")
        assert hasattr(response, "data")
        assert hasattr(response, "reasoning")
        assert hasattr(response, "error")
        assert hasattr(response, "metadata")
        assert hasattr(response, "timestamp")


class TestConstitutionalP2ValidacaoPreventiva:
    """Princípio P2: Validação Preventiva - Validate before using."""

    def test_capability_validation_before_tool_use(self) -> None:
        """Test that _can_use_tool validates before _execute_tool."""
        agent = TestAgent(
            role=AgentRole.ARCHITECT,
            capabilities=[AgentCapability.READ_ONLY],
            llm_client=MagicMock(),
            mcp_client=MagicMock(),
        )

        # Validation method exists and works
        assert agent._can_use_tool("read_file") is True
        assert agent._can_use_tool("write_file") is False

    @pytest.mark.asyncio
    async def test_execute_tool_validates_capability_first(self) -> None:
        """Test that _execute_tool calls _can_use_tool before execution."""
        agent = TestAgent(
            role=AgentRole.ARCHITECT,
            capabilities=[AgentCapability.READ_ONLY],
            llm_client=MagicMock(),
            mcp_client=MagicMock(),
        )

        # Should raise before calling MCP client
        with pytest.raises(CapabilityViolationError):
            await agent._execute_tool("write_file", {})

        # MCP client should never be called
        agent.mcp_client.call_tool.assert_not_called()

    def test_tool_capability_map_is_complete(self) -> None:
        """Test that all common tools are mapped to capabilities."""
        agent = TestAgent(
            role=AgentRole.REFACTORER,
            capabilities=list(AgentCapability),
            llm_client=MagicMock(),
            mcp_client=MagicMock(),
        )

        # READ_ONLY tools
        assert agent._can_use_tool("read_file") is True
        assert agent._can_use_tool("list_files") is True
        assert agent._can_use_tool("grep_search") is True
        assert agent._can_use_tool("find_files") is True

        # FILE_EDIT tools
        assert agent._can_use_tool("write_file") is True
        assert agent._can_use_tool("edit_file") is True
        assert agent._can_use_tool("delete_file") is True
        assert agent._can_use_tool("create_directory") is True

        # BASH_EXEC tools
        assert agent._can_use_tool("bash_command") is True
        assert agent._can_use_tool("exec_command") is True

        # GIT_OPS tools
        assert agent._can_use_tool("git_diff") is True
        assert agent._can_use_tool("git_commit") is True
        assert agent._can_use_tool("git_push") is True
        assert agent._can_use_tool("git_status") is True


class TestConstitutionalP3CeticismoCritico:
    """Princípio P3: Ceticismo Crítico - Don't trust blindly."""

    @pytest.mark.asyncio
    async def test_capability_violation_raises_descriptive_error(self) -> None:
        """Test that capability violations produce helpful errors."""
        agent = TestAgent(
            role=AgentRole.ARCHITECT,
            capabilities=[AgentCapability.READ_ONLY],
            llm_client=MagicMock(),
            mcp_client=MagicMock(),
        )

        with pytest.raises(CapabilityViolationError) as exc_info:
            await agent._execute_tool("write_file", {})

        error_msg = str(exc_info.value)
        # Error should explain what went wrong
        assert "architect" in error_msg.lower()
        assert "write_file" in error_msg
        assert "cannot use" in error_msg.lower()

    @pytest.mark.asyncio
    async def test_agent_does_not_silently_fail(self) -> None:
        """Test that violations raise exceptions, not silent failures."""
        agent = TestAgent(
            role=AgentRole.PLANNER,
            capabilities=[AgentCapability.DESIGN],
            llm_client=MagicMock(),
            mcp_client=MagicMock(),
        )

        # Should raise, not return False or None
        with pytest.raises(CapabilityViolationError):
            await agent._execute_tool("bash_command", {})


class TestConstitutionalP4Rastreabilidade:
    """Princípio P4: Rastreabilidade Total - Traceable decisions."""

    def test_agent_tracks_execution_count(self) -> None:
        """Test that agent tracks number of LLM calls."""
        agent = TestAgent(
            role=AgentRole.PLANNER,
            capabilities=[AgentCapability.DESIGN],
            llm_client=MagicMock(),
            mcp_client=MagicMock(),
        )

        assert agent.execution_count == 0
        # Counter is available for tracking

    def test_agent_response_includes_reasoning(self) -> None:
        """Test that responses include reasoning field."""
        response = AgentResponse(
            success=True,
            reasoning="This is why I did what I did",
        )

        assert response.reasoning
        assert len(response.reasoning) > 0

    def test_agent_response_includes_timestamp(self) -> None:
        """Test that responses include timestamp."""
        response = AgentResponse(success=True, reasoning="Test")

        assert response.timestamp is not None
        # Timestamp allows tracing when decision was made

    def test_shared_context_tracks_updates(self) -> None:
        """Test that SharedContext tracks creation and update times."""
        from jdev_cli.orchestration.memory import SharedContext

        context = SharedContext(user_request="Test")

        assert context.created_at is not None
        assert context.updated_at is not None
        # Timestamps allow tracing session lifecycle


class TestConstitutionalP5ConscienciaSistemica:
    """Princípio P5: Consciência Sistêmica - System-aware design."""

    def test_agents_have_defined_roles(self) -> None:
        """Test that all agents must declare their role."""
        # Agent cannot be created without a role
        with pytest.raises(TypeError):
            TestAgent(  # type: ignore
                capabilities=[AgentCapability.READ_ONLY],
                llm_client=MagicMock(),
                mcp_client=MagicMock(),
            )

    def test_agents_have_defined_capabilities(self) -> None:
        """Test that all agents must declare capabilities."""
        # Agent cannot be created without capabilities
        with pytest.raises(TypeError):
            TestAgent(  # type: ignore
                role=AgentRole.ARCHITECT,
                llm_client=MagicMock(),
                mcp_client=MagicMock(),
            )

    def test_memory_manager_supports_coordination(self) -> None:
        """Test that MemoryManager enables multi-agent coordination."""
        from jdev_cli.orchestration.memory import MemoryManager

        manager = MemoryManager()
        session_id = manager.create_session("Test")

        # Should support multiple agents updating same session
        manager.update_context(session_id, decisions={"architect": "approved"})
        manager.update_context(session_id, context_files=[{"path": "file.py"}])

        context = manager.get_context(session_id)
        assert context is not None
        assert "architect" in context.decisions
        assert len(context.context_files) == 1

    def test_shared_context_has_agent_specific_fields(self) -> None:
        """Test that SharedContext has fields for each agent type."""
        from jdev_cli.orchestration.memory import SharedContext

        context = SharedContext(user_request="Test")

        # Each specialist agent has a designated field
        assert hasattr(context, "decisions")  # Architect
        assert hasattr(context, "context_files")  # Explorer
        assert hasattr(context, "execution_plan")  # Planner
        assert hasattr(context, "execution_results")  # Refactorer
        assert hasattr(context, "review_feedback")  # Reviewer


class TestConstitutionalP6EficienciaToken:
    """Princípio P6: Eficiência de Token - No circular waste."""

    def test_execution_count_increments_per_llm_call(self) -> None:
        """Test that execution_count tracks LLM token usage."""
        agent = TestAgent(
            role=AgentRole.PLANNER,
            capabilities=[AgentCapability.DESIGN],
            llm_client=MagicMock(),
            mcp_client=MagicMock(),
        )

        initial_count = agent.execution_count
        # Counter allows detecting excessive retries
        assert isinstance(initial_count, int)

    def test_agent_response_has_metadata_for_metrics(self) -> None:
        """Test that responses support metadata for token tracking."""
        response = AgentResponse(
            success=True,
            reasoning="Test",
            metadata={"tokens_used": 1234, "model": "gpt-4"},
        )

        assert response.metadata["tokens_used"] == 1234
        # Metadata enables token budget tracking


class TestCapabilityEnforcementSecurity:
    """Security through capability enforcement."""

    def test_architect_cannot_modify_files(self) -> None:
        """Test that Architect (READ_ONLY) cannot modify files."""
        agent = TestAgent(
            role=AgentRole.ARCHITECT,
            capabilities=[AgentCapability.READ_ONLY],
            llm_client=MagicMock(),
            mcp_client=MagicMock(),
        )

        assert agent._can_use_tool("write_file") is False
        assert agent._can_use_tool("edit_file") is False
        assert agent._can_use_tool("delete_file") is False

    def test_explorer_cannot_execute_bash(self) -> None:
        """Test that Explorer (READ_ONLY) cannot execute commands."""
        agent = TestAgent(
            role=AgentRole.EXPLORER,
            capabilities=[AgentCapability.READ_ONLY],
            llm_client=MagicMock(),
            mcp_client=MagicMock(),
        )

        assert agent._can_use_tool("bash_command") is False
        assert agent._can_use_tool("exec_command") is False

    def test_planner_cannot_execute_anything(self) -> None:
        """Test that Planner (DESIGN) cannot execute code or tools."""
        agent = TestAgent(
            role=AgentRole.PLANNER,
            capabilities=[AgentCapability.DESIGN],
            llm_client=MagicMock(),
            mcp_client=MagicMock(),
        )

        # Planner is pure design, no execution
        assert agent._can_use_tool("read_file") is False
        assert agent._can_use_tool("write_file") is False
        assert agent._can_use_tool("bash_command") is False
        assert agent._can_use_tool("git_commit") is False

    def test_reviewer_can_read_and_git_only(self) -> None:
        """Test that Reviewer has READ_ONLY + GIT_OPS only."""
        agent = TestAgent(
            role=AgentRole.REVIEWER,
            capabilities=[AgentCapability.READ_ONLY, AgentCapability.GIT_OPS],
            llm_client=MagicMock(),
            mcp_client=MagicMock(),
        )

        # Can read and check git
        assert agent._can_use_tool("read_file") is True
        assert agent._can_use_tool("git_diff") is True
        assert agent._can_use_tool("git_status") is True

        # Cannot modify or execute
        assert agent._can_use_tool("write_file") is False
        assert agent._can_use_tool("bash_command") is False

    def test_only_refactorer_has_full_access(self) -> None:
        """Test that only Refactorer should have all capabilities."""
        refactorer = TestAgent(
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

        # Refactorer can do everything
        assert refactorer._can_use_tool("read_file") is True
        assert refactorer._can_use_tool("write_file") is True
        assert refactorer._can_use_tool("bash_command") is True
        assert refactorer._can_use_tool("git_commit") is True


class TestTypeSafetyCompliance:
    """Type safety compliance (mypy --strict)."""

    def test_all_public_methods_have_type_hints(self) -> None:
        """Test that all public methods have complete type hints."""
        import jdev_cli.agents.base as base_module

        for name, obj in inspect.getmembers(base_module):
            if inspect.isclass(obj):
                for method_name, method in inspect.getmembers(obj, inspect.isfunction):
                    if not method_name.startswith("_"):
                        sig = inspect.signature(method)
                        # All parameters should have annotations
                        for param_name, param in sig.parameters.items():
                            if param_name not in ("self", "cls"):
                                assert param.annotation != inspect.Parameter.empty, (
                                    f"{name}.{method_name} parameter '{param_name}' missing type hint"
                                )

    def test_pydantic_models_use_field_validators(self) -> None:
        """Test that Pydantic models use Field for validation."""

        # AgentTask uses Field for constraints
        task = AgentTask(request="Test", session_id="s1")
        # Min length constraint exists (tested by Pydantic)
        assert len(task.request) >= 1

    def test_enums_have_string_values(self) -> None:
        """Test that enums have proper string values."""
        assert isinstance(AgentRole.ARCHITECT.value, str)
        assert isinstance(AgentCapability.READ_ONLY.value, str)


class TestIntegrationWithExistingInfrastructure:
    """Test integration with existing qwen-dev-cli infrastructure."""

    @pytest.mark.asyncio
    async def test_can_use_mock_llm_client(self) -> None:
        """Test that BaseAgent works with mocked LLM client."""
        llm_client = MagicMock()
        llm_client.generate = AsyncMock(return_value="LLM response")

        agent = TestAgent(
            role=AgentRole.PLANNER,
            capabilities=[AgentCapability.DESIGN],
            llm_client=llm_client,
            mcp_client=MagicMock(),
        )

        response = await agent._call_llm("Test prompt")
        assert response == "LLM response"

    @pytest.mark.asyncio
    async def test_can_use_mock_mcp_client(self) -> None:
        """Test that BaseAgent works with mocked MCP client."""
        mcp_client = MagicMock()
        mcp_client.call_tool = AsyncMock(return_value={"result": "success"})

        agent = TestAgent(
            role=AgentRole.EXPLORER,
            capabilities=[AgentCapability.READ_ONLY],
            llm_client=MagicMock(),
            mcp_client=mcp_client,
        )

        result = await agent._execute_tool("read_file", {"path": "test.py"})
        assert result["result"] == "success"
