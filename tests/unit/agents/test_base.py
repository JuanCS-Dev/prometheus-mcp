"""
Tests for BaseAgent and related types.

Tests cover:
- AgentRole enum
- AgentCapability enum
- AgentTask model (including validation)
- AgentResponse model
- BaseAgent capability enforcement
- Tool permission checks

Based on Anthropic Claude Code testing standards.
"""
import pytest
import warnings
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

from jdev_cli.agents.base import (
    AgentRole,
    AgentCapability,
    TaskStatus,
    AgentTask,
    AgentResponse,
    TaskResult,
    BaseAgent,
    CapabilityViolationError,
)


# =============================================================================
# AGENTROLE ENUM TESTS
# =============================================================================

class TestAgentRole:
    """Tests for AgentRole enum."""

    def test_core_roles_exist(self):
        """Test core roles are defined."""
        assert AgentRole.ARCHITECT
        assert AgentRole.EXPLORER
        assert AgentRole.PLANNER
        assert AgentRole.REFACTORER
        assert AgentRole.REVIEWER

    def test_specialized_roles_exist(self):
        """Test specialized roles are defined."""
        assert AgentRole.SECURITY
        assert AgentRole.PERFORMANCE
        assert AgentRole.TESTING
        assert AgentRole.DOCUMENTATION
        assert AgentRole.DATABASE
        assert AgentRole.DEVOPS

    def test_governance_roles_exist(self):
        """Test governance roles are defined."""
        assert AgentRole.GOVERNANCE
        assert AgentRole.COUNSELOR

    def test_executor_role_exists(self):
        """Test executor role exists."""
        assert AgentRole.EXECUTOR

    def test_role_values_are_strings(self):
        """Test role values are lowercase strings."""
        assert AgentRole.ARCHITECT.value == "architect"
        assert AgentRole.GOVERNANCE.value == "governance"

    def test_all_roles_unique(self):
        """Test all role values are unique."""
        values = [r.value for r in AgentRole]
        assert len(values) == len(set(values))


# =============================================================================
# AGENTCAPABILITY ENUM TESTS
# =============================================================================

class TestAgentCapability:
    """Tests for AgentCapability enum."""

    def test_all_capabilities_defined(self):
        """Test all expected capabilities exist."""
        assert AgentCapability.READ_ONLY
        assert AgentCapability.FILE_EDIT
        assert AgentCapability.BASH_EXEC
        assert AgentCapability.GIT_OPS
        assert AgentCapability.DESIGN
        assert AgentCapability.DATABASE

    def test_capability_values(self):
        """Test capability string values."""
        assert AgentCapability.READ_ONLY.value == "read_only"
        assert AgentCapability.BASH_EXEC.value == "bash_exec"


# =============================================================================
# TASKSTATUS ENUM TESTS
# =============================================================================

class TestTaskStatus:
    """Tests for TaskStatus enum."""

    def test_all_statuses_defined(self):
        """Test all task statuses exist."""
        assert TaskStatus.PENDING
        assert TaskStatus.THINKING
        assert TaskStatus.ACTING
        assert TaskStatus.COMPLETED
        assert TaskStatus.FAILED
        assert TaskStatus.BLOCKED


# =============================================================================
# AGENTTASK MODEL TESTS
# =============================================================================

class TestAgentTask:
    """Tests for AgentTask Pydantic model."""

    def test_minimal_task(self):
        """Test creating task with minimal fields."""
        task = AgentTask(request="Test task")

        assert task.request == "Test task"
        assert task.task_id  # Should have auto-generated UUID
        assert task.context == {}
        assert task.session_id == "default"

    def test_full_task(self):
        """Test creating task with all fields."""
        task = AgentTask(
            task_id="custom-id",
            request="Full task",
            context={"key": "value"},
            session_id="session-123",
            metadata={"meta": "data"},
            history=[{"step": 1}]
        )

        assert task.task_id == "custom-id"
        assert task.request == "Full task"
        assert task.context["key"] == "value"
        assert task.session_id == "session-123"
        assert task.metadata["meta"] == "data"
        assert len(task.history) == 1

    def test_auto_generated_uuid(self):
        """Test task IDs are unique UUIDs."""
        task1 = AgentTask(request="Task 1")
        task2 = AgentTask(request="Task 2")

        assert task1.task_id != task2.task_id
        assert len(task1.task_id) == 36  # UUID format

    def test_deprecated_description_field(self):
        """Test deprecated 'description' field triggers warning."""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            task = AgentTask(description="Old style task")

            assert len(w) == 1
            assert "deprecated" in str(w[0].message).lower()
            assert task.request == "Old style task"

    def test_description_migrated_to_request(self):
        """Test description field is migrated to request."""
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            task = AgentTask(description="Legacy description")

            assert task.request == "Legacy description"

    def test_context_size_validation_small(self):
        """Test small context passes validation."""
        task = AgentTask(
            request="Task",
            context={"small": "context"}
        )

        assert task.context["small"] == "context"

    def test_context_too_many_keys_rejected(self):
        """Test context with too many keys is rejected."""
        large_context = {f"key_{i}": i for i in range(15000)}

        with pytest.raises(ValueError, match="maximum is 10000"):
            AgentTask(request="Task", context=large_context)

    def test_strict_mode_rejects_type_coercion(self):
        """Test strict mode prevents type coercion."""
        # Should not accept int where string expected
        with pytest.raises(Exception):  # ValidationError
            AgentTask(request=12345)  # type: ignore

    def test_empty_request_allowed(self):
        """Test empty request string is allowed."""
        task = AgentTask(request="")
        assert task.request == ""


# =============================================================================
# AGENTRESPONSE MODEL TESTS
# =============================================================================

class TestAgentResponse:
    """Tests for AgentResponse Pydantic model."""

    def test_success_response(self):
        """Test successful response creation."""
        response = AgentResponse(
            success=True,
            data={"result": "OK"},
            reasoning="Task completed successfully"
        )

        assert response.success is True
        assert response.data["result"] == "OK"
        assert response.reasoning == "Task completed successfully"
        assert response.error is None

    def test_error_response(self):
        """Test error response creation."""
        response = AgentResponse(
            success=False,
            error="Something went wrong"
        )

        assert response.success is False
        assert response.error == "Something went wrong"

    def test_auto_timestamp(self):
        """Test timestamp is auto-generated."""
        before = datetime.utcnow()
        response = AgentResponse(success=True)
        after = datetime.utcnow()

        assert before <= response.timestamp <= after

    def test_metrics_default_empty(self):
        """Test metrics defaults to empty dict."""
        response = AgentResponse(success=True)

        assert response.metrics == {}

    def test_metadata_alias(self):
        """Test metadata property returns metrics."""
        response = AgentResponse(
            success=True,
            metrics={"latency": 0.5}
        )

        assert response.metadata == response.metrics
        assert response.metadata["latency"] == 0.5

    def test_strict_mode_boolean(self):
        """Test strict mode enforces boolean for success."""
        # Should not accept string "true"
        with pytest.raises(Exception):  # ValidationError
            AgentResponse(success="true")  # type: ignore


# =============================================================================
# TASKRESULT MODEL TESTS
# =============================================================================

class TestTaskResult:
    """Tests for TaskResult model."""

    def test_basic_result(self):
        """Test basic task result creation."""
        result = TaskResult(
            task_id="task-123",
            status=TaskStatus.COMPLETED,
            output={"result": "done"}
        )

        assert result.task_id == "task-123"
        assert result.status == TaskStatus.COMPLETED
        assert result.output["result"] == "done"

    def test_failed_result(self):
        """Test failed task result."""
        result = TaskResult(
            task_id="task-456",
            status=TaskStatus.FAILED,
            metadata={"error": "timeout"}
        )

        assert result.status == TaskStatus.FAILED
        assert result.metadata["error"] == "timeout"


# =============================================================================
# BASEAGENT TESTS
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


class TestBaseAgent:
    """Tests for BaseAgent abstract class."""

    @pytest.fixture
    def mock_llm(self):
        """Create mock LLM client."""
        client = MagicMock()
        client.generate = AsyncMock(return_value="LLM response")
        return client

    @pytest.fixture
    def mock_mcp(self):
        """Create mock MCP client."""
        client = MagicMock()
        client.call_tool = AsyncMock(return_value={"success": True})
        return client

    @pytest.fixture
    def read_only_agent(self, mock_llm, mock_mcp):
        """Create agent with READ_ONLY capability."""
        return ConcreteAgent(
            role=AgentRole.EXPLORER,
            capabilities=[AgentCapability.READ_ONLY],
            llm_client=mock_llm,
            mcp_client=mock_mcp,
            system_prompt="Test prompt"
        )

    @pytest.fixture
    def full_agent(self, mock_llm, mock_mcp):
        """Create agent with all capabilities."""
        return ConcreteAgent(
            role=AgentRole.EXECUTOR,
            capabilities=list(AgentCapability),
            llm_client=mock_llm,
            mcp_client=mock_mcp,
            system_prompt="Full access"
        )

    def test_agent_initialization(self, read_only_agent):
        """Test agent initializes correctly."""
        assert read_only_agent.role == AgentRole.EXPLORER
        assert AgentCapability.READ_ONLY in read_only_agent.capabilities
        assert read_only_agent.system_prompt == "Test prompt"
        assert read_only_agent.execution_count == 0

    @pytest.mark.asyncio
    async def test_execute_returns_response(self, read_only_agent):
        """Test execute returns AgentResponse."""
        task = AgentTask(request="Test task")
        response = await read_only_agent.execute(task)

        assert isinstance(response, AgentResponse)
        assert response.success is True
        assert response.data["executed"] == "Test task"

    def test_can_use_tool_read_only(self, read_only_agent):
        """Test READ_ONLY agent can use read tools."""
        assert read_only_agent._can_use_tool("read_file") is True
        assert read_only_agent._can_use_tool("list_files") is True
        assert read_only_agent._can_use_tool("grep_search") is True

    def test_cannot_use_tool_write(self, read_only_agent):
        """Test READ_ONLY agent cannot use write tools."""
        assert read_only_agent._can_use_tool("write_file") is False
        assert read_only_agent._can_use_tool("delete_file") is False
        assert read_only_agent._can_use_tool("bash_command") is False

    def test_full_agent_all_tools(self, full_agent):
        """Test agent with all capabilities can use all tools."""
        assert full_agent._can_use_tool("read_file") is True
        assert full_agent._can_use_tool("write_file") is True
        assert full_agent._can_use_tool("bash_command") is True
        assert full_agent._can_use_tool("git_commit") is True
        assert full_agent._can_use_tool("db_query") is True

    def test_unknown_tool_blocked(self, read_only_agent):
        """Test unknown tools are blocked by default."""
        assert read_only_agent._can_use_tool("unknown_tool") is False
        assert read_only_agent._can_use_tool("hacker_tool") is False

    @pytest.mark.asyncio
    async def test_execute_tool_success(self, full_agent, mock_mcp):
        """Test successful tool execution."""
        result = await full_agent._execute_tool(
            "read_file",
            {"path": "test.py"}
        )

        assert result["success"] is True
        mock_mcp.call_tool.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_tool_blocked(self, read_only_agent):
        """Test blocked tool raises CapabilityViolationError."""
        with pytest.raises(CapabilityViolationError, match="SECURITY VIOLATION"):
            await read_only_agent._execute_tool(
                "bash_command",
                {"command": "rm -rf /"}
            )

    @pytest.mark.asyncio
    async def test_execute_tool_no_mcp(self, mock_llm):
        """Test tool execution with no MCP client."""
        agent = ConcreteAgent(
            role=AgentRole.EXECUTOR,
            capabilities=[AgentCapability.BASH_EXEC],
            llm_client=mock_llm,
            mcp_client=None,  # No MCP
            system_prompt="Test"
        )

        result = await agent._execute_tool(
            "bash_command",
            {"command": "ls"}
        )

        assert result["success"] is False
        assert "not initialized" in result["error"]

    @pytest.mark.asyncio
    async def test_call_llm(self, read_only_agent, mock_llm):
        """Test LLM call wrapper."""
        response = await read_only_agent._call_llm("Test prompt")

        assert response == "LLM response"
        assert read_only_agent.execution_count == 1
        mock_llm.generate.assert_called_once()

    @pytest.mark.asyncio
    async def test_call_llm_error_handling(self, mock_mcp):
        """Test LLM call error handling."""
        mock_llm = MagicMock()
        mock_llm.generate = AsyncMock(side_effect=Exception("API Error"))

        agent = ConcreteAgent(
            role=AgentRole.EXPLORER,
            capabilities=[AgentCapability.READ_ONLY],
            llm_client=mock_llm,
            mcp_client=mock_mcp,
            system_prompt="Test"
        )

        with pytest.raises(Exception, match="API Error"):
            await agent._call_llm("Test")

    @pytest.mark.asyncio
    async def test_run_streaming_fallback(self, read_only_agent):
        """Test run() method for non-streaming agent."""
        task = AgentTask(request="Stream test")

        results = []
        async for update in read_only_agent.run(task):
            results.append(update)

        assert len(results) == 2
        assert results[0]["type"] == "status"
        assert results[1]["type"] == "result"

    @pytest.mark.asyncio
    async def test_reason_method(self, read_only_agent, mock_llm):
        """Test internal reasoning method."""
        task = AgentTask(request="Analyze code")
        context = "Current file: main.py"

        result = await read_only_agent._reason(task, context)

        assert result == "LLM response"
        # Verify prompt includes task and context
        call_args = mock_llm.generate.call_args
        prompt = call_args.kwargs.get('prompt', call_args.args[0] if call_args.args else '')
        assert "Analyze code" in prompt
        assert "main.py" in prompt


# =============================================================================
# TOOL PERMISSION MAPPING TESTS
# =============================================================================

class TestToolPermissionMapping:
    """Tests for tool permission mapping in BaseAgent."""

    @pytest.fixture
    def agent_factory(self):
        """Factory for creating agents with specific capabilities."""
        def create(capabilities):
            mock_llm = MagicMock()
            mock_llm.generate = AsyncMock(return_value="OK")
            return ConcreteAgent(
                role=AgentRole.EXECUTOR,
                capabilities=capabilities,
                llm_client=mock_llm,
                mcp_client=MagicMock(),
                system_prompt="Test"
            )
        return create

    def test_read_tools_require_read_only(self, agent_factory):
        """Test read tools require READ_ONLY capability."""
        agent = agent_factory([AgentCapability.READ_ONLY])

        read_tools = ["read_file", "list_files", "grep_search", "ast_parse", "find_files"]
        for tool in read_tools:
            assert agent._can_use_tool(tool) is True, f"{tool} should be allowed"

    def test_write_tools_require_file_edit(self, agent_factory):
        """Test write tools require FILE_EDIT capability."""
        agent = agent_factory([AgentCapability.FILE_EDIT])

        write_tools = ["write_file", "edit_file", "delete_file", "create_directory"]
        for tool in write_tools:
            assert agent._can_use_tool(tool) is True, f"{tool} should be allowed"

    def test_bash_tools_require_bash_exec(self, agent_factory):
        """Test bash tools require BASH_EXEC capability."""
        agent = agent_factory([AgentCapability.BASH_EXEC])

        bash_tools = ["bash_command", "exec_command", "k8s_action", "docker_build", "argocd_sync"]
        for tool in bash_tools:
            assert agent._can_use_tool(tool) is True, f"{tool} should be allowed"

    def test_git_tools_require_git_ops(self, agent_factory):
        """Test git tools require GIT_OPS capability."""
        agent = agent_factory([AgentCapability.GIT_OPS])

        git_tools = ["git_diff", "git_commit", "git_push", "git_status"]
        for tool in git_tools:
            assert agent._can_use_tool(tool) is True, f"{tool} should be allowed"

    def test_db_tools_require_database(self, agent_factory):
        """Test database tools require DATABASE capability."""
        agent = agent_factory([AgentCapability.DATABASE])

        db_tools = ["db_query", "db_execute", "db_schema"]
        for tool in db_tools:
            assert agent._can_use_tool(tool) is True, f"{tool} should be allowed"


# =============================================================================
# SECURITY TESTS
# =============================================================================

class TestAgentSecurity:
    """Security-focused tests for agent system."""

    @pytest.fixture
    def restricted_agent(self):
        """Create agent with no capabilities."""
        mock_llm = MagicMock()
        mock_llm.generate = AsyncMock(return_value="OK")
        return ConcreteAgent(
            role=AgentRole.EXPLORER,
            capabilities=[],  # No capabilities
            llm_client=mock_llm,
            mcp_client=MagicMock(),
            system_prompt="Restricted"
        )

    def test_no_capabilities_blocks_all(self, restricted_agent):
        """Test agent with no capabilities cannot use any tools."""
        all_tools = [
            "read_file", "write_file", "bash_command",
            "git_commit", "db_query"
        ]

        for tool in all_tools:
            assert restricted_agent._can_use_tool(tool) is False

    @pytest.mark.asyncio
    async def test_capability_violation_logged(self, restricted_agent, caplog):
        """Test capability violations are logged as CRITICAL."""
        import logging
        caplog.set_level(logging.CRITICAL)

        with pytest.raises(CapabilityViolationError):
            await restricted_agent._execute_tool("bash_command", {"command": "ls"})

        assert "SECURITY VIOLATION" in caplog.text

    def test_context_bomb_prevention(self):
        """Test very large context is rejected."""
        # Create context that would exceed size limit
        # 10MB limit => need > 10,000,000 bytes
        with pytest.raises(ValueError):
            AgentTask(
                request="Test",
                context={f"key_{i}": "x" * 1000 for i in range(15000)}
            )


# =============================================================================
# EDGE CASES
# =============================================================================

class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_agent_role_from_string(self):
        """Test creating AgentRole from string."""
        role = AgentRole("architect")
        assert role == AgentRole.ARCHITECT

    def test_task_with_special_characters(self):
        """Test task with special characters in request."""
        task = AgentTask(
            request="Handle <script>alert('xss')</script> and SQL' OR '1'='1"
        )

        assert "<script>" in task.request
        assert "SQL'" in task.request

    def test_response_with_none_values(self):
        """Test response handles None values."""
        response = AgentResponse(
            success=True,
            data={"value": None},
            error=None
        )

        assert response.data["value"] is None
        assert response.error is None

    def test_task_history_immutability(self):
        """Test task history list is independent."""
        history = [{"step": 1}]
        task = AgentTask(request="Test", history=history)

        # Modify original list
        history.append({"step": 2})

        # Task history should be unchanged (Pydantic creates copy)
        assert len(task.history) == 1

    @pytest.mark.asyncio
    async def test_stream_llm_fallback(self):
        """Test _stream_llm fallback when no streaming available."""
        mock_llm = MagicMock(spec=[])  # Empty spec - no methods
        mock_llm.generate = AsyncMock(return_value="Fallback response")

        agent = ConcreteAgent(
            role=AgentRole.EXPLORER,
            capabilities=[AgentCapability.READ_ONLY],
            llm_client=mock_llm,
            mcp_client=MagicMock(),
            system_prompt="Test"
        )

        # _stream_llm checks hasattr for stream_chat and stream
        # MagicMock with spec=[] won't have those, so it should use _call_llm fallback
        # But we need to ensure _call_llm is called
        chunks = []
        async for chunk in agent._stream_llm("Test prompt"):
            chunks.append(chunk)

        # The fallback should yield the full response
        assert len(chunks) == 1
        assert chunks[0] == "Fallback response"

    @pytest.mark.asyncio
    async def test_stream_llm_with_stream_chat(self):
        """Test _stream_llm using stream_chat method."""
        async def mock_stream_chat(**kwargs):
            for token in ["Hello", " ", "World"]:
                yield token

        mock_llm = MagicMock()
        mock_llm.stream_chat = mock_stream_chat

        agent = ConcreteAgent(
            role=AgentRole.EXPLORER,
            capabilities=[AgentCapability.READ_ONLY],
            llm_client=mock_llm,
            mcp_client=MagicMock(),
            system_prompt="Test"
        )

        chunks = []
        async for chunk in agent._stream_llm("Test prompt"):
            chunks.append(chunk)

        assert chunks == ["Hello", " ", "World"]

    @pytest.mark.asyncio
    async def test_stream_llm_with_stream_method(self):
        """Test _stream_llm using stream method when stream_chat unavailable."""
        async def mock_stream(**kwargs):
            for token in ["Token1", "Token2"]:
                yield token

        mock_llm = MagicMock(spec=['stream'])  # Only stream, no stream_chat
        mock_llm.stream = mock_stream

        agent = ConcreteAgent(
            role=AgentRole.EXPLORER,
            capabilities=[AgentCapability.READ_ONLY],
            llm_client=mock_llm,
            mcp_client=MagicMock(),
            system_prompt="Test"
        )

        chunks = []
        async for chunk in agent._stream_llm("Test prompt"):
            chunks.append(chunk)

        assert chunks == ["Token1", "Token2"]

    @pytest.mark.asyncio
    async def test_stream_llm_error_handling(self):
        """Test _stream_llm error handling."""
        async def mock_stream_error(**kwargs):
            yield "First"
            raise Exception("Stream error")

        mock_llm = MagicMock()
        mock_llm.stream_chat = mock_stream_error

        agent = ConcreteAgent(
            role=AgentRole.EXPLORER,
            capabilities=[AgentCapability.READ_ONLY],
            llm_client=mock_llm,
            mcp_client=MagicMock(),
            system_prompt="Test"
        )

        with pytest.raises(Exception, match="Stream error"):
            async for chunk in agent._stream_llm("Test"):
                pass

    @pytest.mark.asyncio
    async def test_call_llm_with_stream_fallback(self):
        """Test _call_llm using stream method as fallback."""
        async def mock_stream(**kwargs):
            for token in ["A", "B", "C"]:
                yield token

        mock_llm = MagicMock(spec=['stream'])  # Only stream, no generate
        mock_llm.stream = mock_stream

        agent = ConcreteAgent(
            role=AgentRole.EXPLORER,
            capabilities=[AgentCapability.READ_ONLY],
            llm_client=mock_llm,
            mcp_client=MagicMock(),
            system_prompt="Test"
        )

        # _call_llm should use stream and join
        response = await agent._call_llm("Test prompt")

        assert response == "ABC"

    def test_deprecated_description_with_request_provided(self):
        """Test description ignored when request already provided."""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            # When both are provided, description is ignored
            task = AgentTask(request="New style", description="Old style")

            assert len(w) == 1
            assert task.request == "New style"  # request takes priority


# =============================================================================
# ADDITIONAL COVERAGE TESTS
# =============================================================================

class TestAdditionalCoverage:
    """Additional tests to improve coverage."""

    def test_capability_violation_error(self):
        """Test CapabilityViolationError exception."""
        error = CapabilityViolationError("SECURITY VIOLATION: explorer cannot use bash_command")

        assert "explorer" in str(error)
        assert "bash_command" in str(error)

    def test_task_result_with_all_fields(self):
        """Test TaskResult with all optional fields."""
        result = TaskResult(
            task_id="task-789",
            status=TaskStatus.THINKING,
            output={"partial": True},
            metadata={"progress": 50}
        )

        assert result.status == TaskStatus.THINKING
        assert result.metadata["progress"] == 50

    @pytest.mark.asyncio
    async def test_run_with_failed_execute(self):
        """Test run() when execute fails."""
        class FailingAgent(BaseAgent):
            async def execute(self, task: AgentTask) -> AgentResponse:
                raise ValueError("Execution failed")

        mock_llm = MagicMock()
        mock_llm.generate = AsyncMock(return_value="OK")

        agent = FailingAgent(
            role=AgentRole.EXECUTOR,
            capabilities=[AgentCapability.READ_ONLY],
            llm_client=mock_llm,
            mcp_client=MagicMock(),
            system_prompt="Test"
        )

        task = AgentTask(request="Fail task")
        results = []

        with pytest.raises(ValueError, match="Execution failed"):
            async for update in agent.run(task):
                results.append(update)

    def test_agent_response_data_with_nested(self):
        """Test AgentResponse with nested data."""
        response = AgentResponse(
            success=True,
            data={
                "result": "done",
                "details": {"count": 10},
                "suggestions": ["Suggestion 1", "Suggestion 2"]
            },
            reasoning="Completed"
        )

        assert response.data["details"]["count"] == 10
        assert len(response.data["suggestions"]) == 2

    def test_agent_task_with_context_files(self):
        """Test AgentTask with files in context."""
        task = AgentTask(
            request="Process files",
            context={"files": ["file1.py", "file2.py"]}
        )

        assert len(task.context["files"]) == 2
        assert "file1.py" in task.context["files"]
