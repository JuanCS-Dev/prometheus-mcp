"""Tests for PlannerAgent Context File Handling.

Tests that PlannerAgent gracefully handles missing context files like CLAUDE.md.

Compliance: Vértice Constitution v3.0
- P3: Fail gracefully with clear messages
- P1: Zero placeholders, complete tests
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from jdev_cli.agents.planner import PlannerAgent
from jdev_cli.agents.base import AgentTask


class TestCLAUDEmdOptional:
    """Tests for optional CLAUDE.md file handling."""

    @pytest.fixture
    def mock_llm(self):
        """Create mock LLM client."""
        llm = Mock()
        llm.generate = AsyncMock(return_value="Generated plan output")
        return llm

    @pytest.fixture
    def mock_mcp(self):
        """Create mock MCP client."""
        mcp = Mock()
        mcp.registry = Mock()
        mcp.registry.tools = {}
        return mcp

    @pytest.mark.asyncio
    async def test_load_team_standards_with_existing_claude_md(self, mock_llm, mock_mcp):
        """PlannerAgent should load CLAUDE.md when it exists."""
        agent = PlannerAgent(mock_llm, mock_mcp)

        # Mock successful file read
        mock_result = {
            "success": True,
            "content": "# Team Standards\n\n- Use Python 3.11+\n- Write tests\n"
        }

        with patch.object(agent, '_execute_tool', new_callable=AsyncMock) as mock_exec:
            mock_exec.return_value = mock_result

            result = await agent._load_team_standards()

            # Should return standards
            assert "claude_md" in result
            assert "Team Standards" in result["claude_md"]
            mock_exec.assert_called_once_with("read_file", {"path": "CLAUDE.md"})

    @pytest.mark.asyncio
    async def test_load_team_standards_without_claude_md_file_not_found(
        self, mock_llm, mock_mcp
    ):
        """PlannerAgent should handle FileNotFoundError gracefully."""
        agent = PlannerAgent(mock_llm, mock_mcp)

        with patch.object(agent, '_execute_tool', new_callable=AsyncMock) as mock_exec:
            mock_exec.side_effect = FileNotFoundError("CLAUDE.md not found")

            # Should not raise, returns empty dict
            result = await agent._load_team_standards()

            assert result == {}

    @pytest.mark.asyncio
    async def test_load_team_standards_without_claude_md_unsuccessful_read(
        self, mock_llm, mock_mcp
    ):
        """PlannerAgent should handle unsuccessful file read."""
        agent = PlannerAgent(mock_llm, mock_mcp)

        # Mock unsuccessful read
        mock_result = {"success": False, "error": "Permission denied"}

        with patch.object(agent, '_execute_tool', new_callable=AsyncMock) as mock_exec:
            mock_exec.return_value = mock_result

            result = await agent._load_team_standards()

            # Should return empty dict (fallback)
            assert result == {}

    @pytest.mark.asyncio
    async def test_load_team_standards_with_generic_exception(
        self, mock_llm, mock_mcp
    ):
        """PlannerAgent should handle generic exceptions gracefully."""
        agent = PlannerAgent(mock_llm, mock_mcp)

        with patch.object(agent, '_execute_tool', new_callable=AsyncMock) as mock_exec:
            mock_exec.side_effect = RuntimeError("Unexpected error")

            # Should not raise, logs warning and returns empty dict
            result = await agent._load_team_standards()

            assert result == {}

    @pytest.mark.asyncio
    async def test_load_team_standards_logs_info_on_success(
        self, mock_llm, mock_mcp, caplog
    ):
        """PlannerAgent should log info message when CLAUDE.md loaded."""
        agent = PlannerAgent(mock_llm, mock_mcp)

        mock_result = {"success": True, "content": "# Standards"}

        with patch.object(agent, '_execute_tool', new_callable=AsyncMock) as mock_exec:
            mock_exec.return_value = mock_result

            with caplog.at_level("INFO"):
                await agent._load_team_standards()

            # Check that info log was emitted
            assert any("Loaded team standards" in record.message for record in caplog.records)

    @pytest.mark.asyncio
    async def test_load_team_standards_logs_debug_on_file_not_found(
        self, mock_llm, mock_mcp, caplog
    ):
        """PlannerAgent should log debug message when CLAUDE.md not found."""
        agent = PlannerAgent(mock_llm, mock_mcp)

        with patch.object(agent, '_execute_tool', new_callable=AsyncMock) as mock_exec:
            mock_exec.side_effect = FileNotFoundError()

            with caplog.at_level("DEBUG"):
                await agent._load_team_standards()

            # Check that helpful debug message was logged
            assert any(
                "CLAUDE.md not found (optional)" in record.message
                for record in caplog.records
            )

    @pytest.mark.asyncio
    async def test_load_team_standards_logs_warning_on_error(
        self, mock_llm, mock_mcp, caplog
    ):
        """PlannerAgent should log warning on unexpected errors."""
        agent = PlannerAgent(mock_llm, mock_mcp)

        with patch.object(agent, '_execute_tool', new_callable=AsyncMock) as mock_exec:
            mock_exec.side_effect = PermissionError("Access denied")

            with caplog.at_level("WARNING"):
                await agent._load_team_standards()

            # Check that warning was logged
            assert any(
                "Failed to load CLAUDE.md" in record.message
                for record in caplog.records
            )


class TestPlannerWithoutContext:
    """Tests for PlannerAgent executing without context files."""

    @pytest.fixture
    def mock_llm_with_response(self):
        """Create mock LLM with realistic response."""
        llm = Mock()
        llm.generate = AsyncMock(return_value="""
        <think>
        Analyzing the task: Create a simple Python function.
        This requires creating a new file with function definition.
        </think>
        
        <action>
        Plan to create hello.py with a greeting function.
        Steps:
        1. Create file hello.py
        2. Write function definition
        3. Add docstring
        </action>
        """)
        return llm

    @pytest.fixture
    def mock_mcp_with_tools(self):
        """Create mock MCP with registered tools."""
        from jdev_cli.tools.base import ToolRegistry

        registry = ToolRegistry()

        # Mock read_file tool
        read_tool = Mock()
        read_tool.name = 'read_file'
        registry.register(read_tool)

        mcp = Mock()
        mcp.registry = registry
        return mcp

    @pytest.mark.asyncio
    async def test_planner_executes_without_claude_md(
        self, mock_llm_with_response, mock_mcp_with_tools
    ):
        """PlannerAgent should execute successfully without CLAUDE.md."""
        agent = PlannerAgent(mock_llm_with_response, mock_mcp_with_tools)

        # Mock _load_team_standards to simulate missing file
        with patch.object(agent, '_load_team_standards', new_callable=AsyncMock) as mock_load:
            mock_load.return_value = {}  # No CLAUDE.md

            # Create simple task
            task = AgentTask(
                request="Create a simple hello world function",
                context={"project_root": "/tmp/test"}
            )

            # Should not raise, executes with default standards
            response = await agent.execute(task)

            # Agent should still work
            assert response is not None
            mock_load.assert_called_once()

    @pytest.mark.asyncio
    async def test_planner_uses_defaults_when_no_standards(
        self, mock_llm_with_response, mock_mcp_with_tools
    ):
        """PlannerAgent should use default behavior without standards."""
        agent = PlannerAgent(mock_llm_with_response, mock_mcp_with_tools)

        with patch.object(agent, '_load_team_standards', new_callable=AsyncMock) as mock_load:
            mock_load.return_value = {}

            task = AgentTask(
                request="Plan a refactoring task",
                context={}
            )

            # Execute without errors
            response = await agent.execute(task)

            # Should still generate a plan (using LLM defaults)
            assert response is not None


class TestContextFileDocumentation:
    """Tests for context file documentation and error messages."""

    @pytest.mark.asyncio
    async def test_error_message_mentions_creating_claude_md(self, caplog):
        """Error messages should suggest creating CLAUDE.md."""
        from jdev_cli.tools.base import ToolRegistry
        from jdev_cli.core.mcp_client import MCPClient

        llm = Mock()
        llm.generate = AsyncMock(return_value="output")

        registry = ToolRegistry()
        mcp = MCPClient(registry)

        agent = PlannerAgent(llm, mcp)

        with patch.object(agent, '_execute_tool', new_callable=AsyncMock) as mock_exec:
            mock_exec.side_effect = FileNotFoundError()

            with caplog.at_level("DEBUG"):
                await agent._load_team_standards()

            # Error message should be helpful
            messages = [record.message for record in caplog.records]
            assert any("Create CLAUDE.md" in msg for msg in messages)


# Metadata for pytest
pytestmark = pytest.mark.unit
