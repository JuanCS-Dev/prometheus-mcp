"""
Week 2 Day 2 Integration Tests: Dashboard Auto-Update

Tests:
- Dashboard operations added during tool execution
- Dashboard updated on success/failure
- /dash command shows current state

Boris Cherny: Type-safe dashboard integration testing
"""

import pytest
from unittest.mock import Mock, AsyncMock
from jdev_cli.shell import InteractiveShell, SessionContext
from jdev_cli.tools.base import ToolResult
from jdev_cli.tui.components.dashboard import OperationStatus


class TestDashboardIntegration:
    """Test dashboard auto-update during tool execution."""

    @pytest.fixture
    def shell(self):
        """Create shell with minimal dependencies."""
        shell = object.__new__(InteractiveShell)
        shell.console = Mock()
        shell.context = SessionContext()
        shell.workflow_viz = Mock()
        shell.workflow_viz.current_workflow = Mock()
        shell.workflow_viz.current_workflow.steps = []
        shell.workflow_viz.start_workflow = Mock()
        shell.workflow_viz.add_step = Mock()
        shell.workflow_viz.update_step_status = Mock()
        shell.workflow_viz.complete_workflow = Mock()
        shell.registry = Mock()
        shell.conversation = Mock()
        shell.conversation.add_tool_result = Mock()
        shell.dashboard = Mock()
        shell.dashboard.add_operation = Mock()
        shell.dashboard.complete_operation = Mock()
        return shell

    @pytest.mark.asyncio
    async def test_dashboard_operation_added_for_each_tool(self, shell):
        """Test that dashboard.add_operation is called for each tool."""
        # Setup: Mock tool calls
        tool_calls = [
            {"tool": "read_file", "args": {"path": "test.py"}},
            {"tool": "write_file", "args": {"path": "test.py", "content": "data"}},
        ]

        # Mock tools
        mock_tool = AsyncMock()
        shell.registry.get = Mock(return_value=mock_tool)

        # Mock recovery (success) with proper metadata for read_file
        shell._execute_with_recovery = AsyncMock(return_value=ToolResult(
            success=True,
            data="Success",
            metadata={'tokens': 100, 'cost': 0.01, 'path': 'test.py', 'lines': 10}
        ))

        # Execute
        await shell._execute_tool_calls(tool_calls, turn=1)

        # Verify: Dashboard.add_operation called for each tool
        assert shell.dashboard.add_operation.call_count == 2

        # Verify: Operations have correct type
        calls = shell.dashboard.add_operation.call_args_list
        assert calls[0][0][0].type == "read_file"
        assert calls[1][0][0].type == "write_file"

    @pytest.mark.asyncio
    async def test_dashboard_updated_on_success(self, shell):
        """Test that dashboard.complete_operation is called with SUCCESS."""
        # Setup
        tool_calls = [
            {"tool": "read_file", "args": {"path": "test.py"}},
        ]

        mock_tool = AsyncMock()
        shell.registry.get = Mock(return_value=mock_tool)

        # Mock successful execution with metadata
        shell._execute_with_recovery = AsyncMock(return_value=ToolResult(
            success=True,
            data="Success",
            metadata={'tokens': 150, 'cost': 0.02, 'path': 'test.py', 'lines': 10}
        ))

        # Execute
        await shell._execute_tool_calls(tool_calls, turn=1)

        # Verify: complete_operation called with SUCCESS
        shell.dashboard.complete_operation.assert_called_once()
        call_args = shell.dashboard.complete_operation.call_args

        # First arg is op_id, second is status
        assert call_args[0][1] == OperationStatus.SUCCESS
        # Check kwargs for tokens and cost
        assert call_args[1]['tokens_used'] == 150
        assert call_args[1]['cost'] == 0.02

    @pytest.mark.asyncio
    async def test_dashboard_updated_on_failure(self, shell):
        """Test that dashboard.complete_operation is called with ERROR."""
        # Setup
        tool_calls = [
            {"tool": "read_file", "args": {"path": "nonexistent.py"}},
        ]

        mock_tool = AsyncMock()
        shell.registry.get = Mock(return_value=mock_tool)

        # Mock failed execution
        shell._execute_with_recovery = AsyncMock(return_value=ToolResult(
            success=False,
            error="File not found"
        ))

        # Execute
        await shell._execute_tool_calls(tool_calls, turn=1)

        # Verify: complete_operation called with ERROR
        shell.dashboard.complete_operation.assert_called_once()
        call_args = shell.dashboard.complete_operation.call_args
        assert call_args[0][1] == OperationStatus.ERROR

    @pytest.mark.asyncio
    async def test_dashboard_updated_on_recovery_failure(self, shell):
        """Test dashboard update when recovery fails completely."""
        # Setup
        tool_calls = [
            {"tool": "read_file", "args": {"path": "test.py"}},
        ]

        mock_tool = AsyncMock()
        shell.registry.get = Mock(return_value=mock_tool)

        # Mock recovery failure (returns None)
        shell._execute_with_recovery = AsyncMock(return_value=None)

        # Execute
        await shell._execute_tool_calls(tool_calls, turn=1)

        # Verify: complete_operation called with ERROR
        shell.dashboard.complete_operation.assert_called_once()
        call_args = shell.dashboard.complete_operation.call_args
        assert call_args[0][1] == OperationStatus.ERROR

    @pytest.mark.asyncio
    async def test_dashboard_operations_have_unique_ids(self, shell):
        """Test that each operation gets a unique ID."""
        # Setup: Multiple tool calls
        tool_calls = [
            {"tool": "read_file", "args": {"path": "a.py"}},
            {"tool": "read_file", "args": {"path": "b.py"}},
            {"tool": "read_file", "args": {"path": "c.py"}},
        ]

        mock_tool = AsyncMock()
        shell.registry.get = Mock(return_value=mock_tool)

        shell._execute_with_recovery = AsyncMock(return_value=ToolResult(
            success=True,
            data="OK",
            metadata={'path': 'file.py', 'lines': 10}
        ))

        # Execute
        await shell._execute_tool_calls(tool_calls, turn=1)

        # Verify: 3 operations added
        assert shell.dashboard.add_operation.call_count == 3

        # Verify: All operation IDs are unique
        added_ops = [call[0][0] for call in shell.dashboard.add_operation.call_args_list]
        op_ids = [op.id for op in added_ops]

        assert len(op_ids) == len(set(op_ids)), "Operation IDs should be unique"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
