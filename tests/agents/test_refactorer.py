"""
Tests for RefactorerAgent - The Code Surgeon.

Validates step execution, self-correction, validation.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from jdev_cli.agents.refactorer import RefactorerAgent
from jdev_cli.agents.base import AgentTask, AgentCapability, AgentRole


class TestRefactorerBasic:
    """Basic functionality tests for Refactorer."""

    def test_refactorer_initialization(self) -> None:
        """Test Refactorer initializes with full capabilities."""
        llm_client = MagicMock()
        mcp_client = MagicMock()

        refactorer = RefactorerAgent(llm_client, mcp_client)

        assert refactorer.role == AgentRole.REFACTORER
        assert AgentCapability.READ_ONLY in refactorer.capabilities
        assert AgentCapability.FILE_EDIT in refactorer.capabilities
        assert AgentCapability.BASH_EXEC in refactorer.capabilities
        assert AgentCapability.GIT_OPS in refactorer.capabilities
        assert len(refactorer.capabilities) == 4

    @pytest.mark.asyncio
    async def test_refactorer_executes_create_directory(self) -> None:
        """Test Refactorer executes create_directory step."""
        mcp_client = MagicMock()
        mcp_client.call_tool = AsyncMock(return_value={"result": "OK"})

        refactorer = RefactorerAgent(MagicMock(), mcp_client)
        task = AgentTask(
            request="Execute step",
            session_id="test",
            context={
                "step": {
                    "id": 1,
                    "action": "create_directory",
                    "params": {"path": "app/new_folder"},
                    "risk": "LOW"
                }
            }
        )

        response = await refactorer.execute(task)

        assert response.success is True
        assert response.data["step_id"] == 1
        assert response.data["status"] == "SUCCESS"
        assert response.data["attempts"] == 1

    @pytest.mark.asyncio
    async def test_refactorer_executes_create_file(self) -> None:
        """Test Refactorer executes create_file step."""
        mcp_client = MagicMock()
        mcp_client.call_tool = AsyncMock(return_value={"result": "OK"})

        refactorer = RefactorerAgent(MagicMock(), mcp_client)
        task = AgentTask(
            request="Create file",
            session_id="test",
            context={
                "step": {
                    "id": 2,
                    "action": "create_file",
                    "params": {"path": "test.py", "content": "print('hello')"},
                    "risk": "LOW"
                }
            }
        )

        response = await refactorer.execute(task)

        assert response.success is True
        assert "test.py" in response.reasoning or "test.py" in str(response.data)

    @pytest.mark.asyncio
    async def test_refactorer_validates_step_structure(self) -> None:
        """Test Refactorer rejects invalid step structure."""
        refactorer = RefactorerAgent(MagicMock(), MagicMock())
        task = AgentTask(
            request="Execute",
            session_id="test",
            context={
                "step": {"invalid": "structure"}  # Missing id, action
            }
        )

        response = await refactorer.execute(task)

        assert response.success is False
        assert "invalid" in response.reasoning.lower()

    @pytest.mark.asyncio
    async def test_refactorer_handles_missing_step(self) -> None:
        """Test Refactorer handles missing step in context."""
        refactorer = RefactorerAgent(MagicMock(), MagicMock())
        task = AgentTask(request="Execute", session_id="test")  # No context

        response = await refactorer.execute(task)

        assert response.success is False
        assert "no step" in response.reasoning.lower()

    @pytest.mark.asyncio
    async def test_refactorer_retries_on_failure(self) -> None:
        """Test Refactorer retries up to 3 times."""
        mcp_client = MagicMock()
        # Fail twice on execution, succeed on third + validation + test counting
        mcp_client.call_tool = AsyncMock(
            side_effect=[
                Exception("First fail"),  # Attempt 1 fails
                Exception("Second fail"),  # Attempt 2 fails
                {"result": "OK"},  # Attempt 3 succeeds (create_file)
                {"result": "OK"},  # Validation succeeds
                {"result": "5"},   # Test count
            ]
        )

        llm_client = MagicMock()
        llm_client.generate = AsyncMock(return_value="Try alternative approach")

        refactorer = RefactorerAgent(llm_client, mcp_client)
        task = AgentTask(
            request="Execute",
            session_id="test",
            context={
                "step": {
                    "id": 1,
                    "action": "create_file",
                    "params": {"path": "test.py"},
                    "risk": "LOW"
                }
            }
        )

        response = await refactorer.execute(task)

        # Should succeed on third attempt
        assert response.success is True
        assert response.data["attempts"] == 3

    @pytest.mark.asyncio
    async def test_refactorer_fails_after_max_attempts(self) -> None:
        """Test Refactorer fails after 3 failed attempts."""
        mcp_client = MagicMock()
        mcp_client.call_tool = AsyncMock(side_effect=Exception("Always fails"))

        llm_client = MagicMock()
        llm_client.generate = AsyncMock(return_value="Correction hint")

        refactorer = RefactorerAgent(llm_client, mcp_client)
        task = AgentTask(
            request="Execute",
            session_id="test",
            context={
                "step": {
                    "id": 1,
                    "action": "create_file",
                    "params": {"path": "test.py"},
                    "risk": "LOW"
                }
            }
        )

        response = await refactorer.execute(task)

        assert response.success is False
        assert response.data["status"] == "FAILED"
        assert response.data["attempts"] == 3
        assert response.data["requires_human"] is True

    @pytest.mark.asyncio
    async def test_refactorer_runs_tests_after_code_change(self) -> None:
        """Test Refactorer runs tests after editing files."""
        mcp_client = MagicMock()
        # Mock successful file creation and test run
        mcp_client.call_tool = AsyncMock(
            side_effect=[
                {"result": "File created"},  # create_file
                {"result": "OK"},  # validation
                {"result": "10"},  # test count
            ]
        )

        refactorer = RefactorerAgent(MagicMock(), mcp_client)
        task = AgentTask(
            request="Create",
            session_id="test",
            context={
                "step": {
                    "id": 1,
                    "action": "create_file",
                    "params": {"path": "app/new.py", "content": "code"},
                    "risk": "LOW"
                }
            }
        )

        response = await refactorer.execute(task)

        assert response.success is True
        # Should have run tests
        assert response.data["tests_run"] is not None

    @pytest.mark.asyncio
    async def test_refactorer_creates_backup_before_delete(self) -> None:
        """Test Refactorer creates backup before deleting files."""
        mcp_client = MagicMock()
        mcp_client.call_tool = AsyncMock(return_value={"result": "OK"})

        refactorer = RefactorerAgent(MagicMock(), mcp_client)
        task = AgentTask(
            request="Delete",
            session_id="test",
            context={
                "step": {
                    "id": 1,
                    "action": "delete_file",
                    "params": {"path": "old.py"},
                    "risk": "HIGH"
                }
            }
        )

        response = await refactorer.execute(task)

        assert response.success is True
        # Check that backup was mentioned
        assert "backup" in response.reasoning.lower() or "backup" in str(response.data)

    @pytest.mark.asyncio
    async def test_refactorer_execution_count_increments(self) -> None:
        """Test Refactorer tracks execution count."""
        mcp_client = MagicMock()
        mcp_client.call_tool = AsyncMock(return_value={"result": "OK"})

        refactorer = RefactorerAgent(MagicMock(), mcp_client)
        initial_count = refactorer.execution_count

        task = AgentTask(
            request="Execute",
            session_id="test",
            context={
                "step": {
                    "id": 1,
                    "action": "bash_command",
                    "params": {"command": "echo test"},
                    "risk": "LOW"
                }
            }
        )

        await refactorer.execute(task)

        assert refactorer.execution_count == initial_count + 1

    def test_refactorer_can_use_all_tools(self) -> None:
        """Test Refactorer can use all tool types."""
        refactorer = RefactorerAgent(MagicMock(), MagicMock())

        # Should have access to all tools
        assert refactorer._can_use_tool("read_file") is True
        assert refactorer._can_use_tool("write_file") is True
        assert refactorer._can_use_tool("edit_file") is True
        assert refactorer._can_use_tool("bash_command") is True
        assert refactorer._can_use_tool("git_commit") is True

    @pytest.mark.asyncio
    async def test_refactorer_executes_bash_command(self) -> None:
        """Test Refactorer executes bash commands."""
        mcp_client = MagicMock()
        mcp_client.call_tool = AsyncMock(return_value={"result": "Command executed"})

        refactorer = RefactorerAgent(MagicMock(), mcp_client)
        task = AgentTask(
            request="Run command",
            session_id="test",
            context={
                "step": {
                    "id": 1,
                    "action": "bash_command",
                    "params": {"command": "ls -la"},
                    "risk": "LOW"
                }
            }
        )

        response = await refactorer.execute(task)

        assert response.success is True
        assert "ls" in response.reasoning or "ls" in str(response.data)

    @pytest.mark.asyncio
    async def test_refactorer_validates_execution(self) -> None:
        """Test Refactorer validates each operation."""
        mcp_client = MagicMock()
        # First call: create file, second call: validation
        mcp_client.call_tool = AsyncMock(
            side_effect=[
                {"result": "File created"},
                {"result": "OK"}  # Validation passes
            ]
        )

        refactorer = RefactorerAgent(MagicMock(), mcp_client)
        task = AgentTask(
            request="Create",
            session_id="test",
            context={
                "step": {
                    "id": 1,
                    "action": "create_file",
                    "params": {"path": "test.py", "content": "code"},
                    "risk": "LOW"
                }
            }
        )

        response = await refactorer.execute(task)

        assert response.success is True
        # Validation should be in execution log
        execution_log = response.data.get("execution_log", [])
        assert any("validation" in log.lower() for log in execution_log)

    @pytest.mark.asyncio
    async def test_refactorer_handles_exception(self) -> None:
        """Test Refactorer handles exceptions gracefully."""
        mcp_client = MagicMock()
        mcp_client.call_tool = AsyncMock(side_effect=Exception("Critical error"))

        llm_client = MagicMock()
        llm_client.generate = AsyncMock(return_value="Suggestion")

        refactorer = RefactorerAgent(llm_client, mcp_client)
        task = AgentTask(
            request="Execute",
            session_id="test",
            context={
                "step": {
                    "id": 1,
                    "action": "create_file",
                    "params": {"path": "test.py"},
                    "risk": "LOW"
                }
            }
        )

        response = await refactorer.execute(task)

        assert response.success is False
        assert response.error is not None
