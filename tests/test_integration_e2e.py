"""
Week 2 End-to-End Integration Test

Validates full integration of:
- Workflow Visualizer
- Dashboard Auto-Update
- Preview System
- All components working together

Boris Cherny: End-to-end integration validation
"""

import pytest
from unittest.mock import Mock, AsyncMock
from jdev_cli.shell import InteractiveShell, SessionContext
from jdev_cli.tools.base import ToolResult
from jdev_cli.tui.components.workflow_visualizer import StepStatus
from jdev_cli.tui.components.dashboard import OperationStatus


class TestEndToEndIntegration:
    """End-to-end integration tests for Week 2 features."""

    @pytest.fixture
    def shell(self):
        """Create shell with all Week 2 dependencies."""
        shell = object.__new__(InteractiveShell)
        shell.console = Mock()
        shell.context = SessionContext()

        # Workflow Visualizer
        shell.workflow_viz = Mock()
        shell.workflow_viz.current_workflow = Mock()
        shell.workflow_viz.current_workflow.steps = []
        shell.workflow_viz.start_workflow = Mock()
        shell.workflow_viz.add_step = Mock()
        shell.workflow_viz.update_step_status = Mock()
        shell.workflow_viz.complete_workflow = Mock()
        shell.workflow_viz.render_workflow = Mock(return_value="[Workflow Viz]")

        # Dashboard
        shell.dashboard = Mock()
        shell.dashboard.add_operation = Mock()
        shell.dashboard.complete_operation = Mock()
        shell.dashboard.render = Mock(return_value="[Dashboard]")

        # Tool Registry
        shell.registry = Mock()

        # Conversation
        shell.conversation = Mock()
        shell.conversation.add_tool_result = Mock()

        return shell

    @pytest.mark.asyncio
    async def test_multi_tool_workflow_complete_integration(self, shell):
        """
        Test complete integration: 3 tools executing with:
        - Workflow steps tracking each tool
        - Dashboard operations for each tool
        - Preview enabled for file tools
        - All status updates working
        """
        # Setup: 3-tool chain (read -> edit -> write)
        tool_calls = [
            {"tool": "read_file", "args": {"path": "original.py"}},
            {"tool": "edit_file", "args": {"path": "original.py", "edits": []}},
            {"tool": "write_file", "args": {"path": "new.py", "content": "updated"}},
        ]

        # Mock tools
        mock_tool = AsyncMock()
        shell.registry.get = Mock(return_value=mock_tool)

        # Mock successful execution for all tools
        shell._execute_with_recovery = AsyncMock(return_value=ToolResult(
            success=True,
            data="Success",
            metadata={'path': 'file.py', 'lines': 10, 'tokens': 50, 'cost': 0.01}
        ))

        # Execute
        result = await shell._execute_tool_calls(tool_calls, turn=1)

        # === WORKFLOW VISUALIZER VALIDATION ===

        # Verify: Workflow started (3 tools)
        shell.workflow_viz.start_workflow.assert_called_once()

        # Verify: 3 workflow steps added
        assert shell.workflow_viz.add_step.call_count == 3

        # Verify: Each step went through status transitions
        # Each tool: PENDING -> RUNNING -> COMPLETED = 2 updates per tool
        assert shell.workflow_viz.update_step_status.call_count >= 6

        # Verify: Workflow completed
        shell.workflow_viz.complete_workflow.assert_called_once()

        # === DASHBOARD VALIDATION ===

        # Verify: 3 dashboard operations added
        assert shell.dashboard.add_operation.call_count == 3

        # Verify: All operations completed successfully
        assert shell.dashboard.complete_operation.call_count == 3

        # Verify: All marked as SUCCESS (not ERROR)
        success_calls = [
            call for call in shell.dashboard.complete_operation.call_args_list
            if call[0][1] == OperationStatus.SUCCESS
        ]
        assert len(success_calls) == 3

        # === PREVIEW SYSTEM VALIDATION ===

        # Verify: Console passed to file tools (edit_file and write_file)
        recovery_calls = shell._execute_with_recovery.call_args_list

        # Check edit_file call (index 1)
        edit_args = recovery_calls[1][0][2]
        assert 'console' in edit_args
        assert edit_args['console'] == shell.console
        assert 'preview' in edit_args
        assert edit_args['preview'] is True  # Default enabled

        # Check write_file call (index 2)
        write_args = recovery_calls[2][0][2]
        assert 'console' in write_args
        assert 'preview' in write_args

    @pytest.mark.asyncio
    async def test_failure_handling_across_all_systems(self, shell):
        """
        Test failure scenario propagates correctly through:
        - Workflow Visualizer (marks step as FAILED)
        - Dashboard (marks operation as ERROR)
        - Preview system (still works for other operations)
        """
        # Setup: 2 tools, second one fails
        tool_calls = [
            {"tool": "read_file", "args": {"path": "exists.py"}},
            {"tool": "read_file", "args": {"path": "nonexistent.py"}},
        ]

        mock_tool = AsyncMock()
        shell.registry.get = Mock(return_value=mock_tool)

        # Mock: First succeeds, second fails
        shell._execute_with_recovery = AsyncMock(side_effect=[
            ToolResult(success=True, data="OK", metadata={'path': 'f.py', 'lines': 10}),
            ToolResult(success=False, error="File not found"),
        ])

        # Execute
        await shell._execute_tool_calls(tool_calls, turn=1)

        # === WORKFLOW VALIDATION ===

        # Verify: Both steps added
        assert shell.workflow_viz.add_step.call_count == 2

        # Verify: Second step marked as FAILED
        failed_calls = [
            call for call in shell.workflow_viz.update_step_status.call_args_list
            if StepStatus.FAILED in call[0]
        ]
        assert len(failed_calls) >= 1

        # === DASHBOARD VALIDATION ===

        # Verify: First operation SUCCESS
        success_calls = [
            call for call in shell.dashboard.complete_operation.call_args_list
            if call[0][1] == OperationStatus.SUCCESS
        ]
        assert len(success_calls) == 1

        # Verify: Second operation ERROR
        error_calls = [
            call for call in shell.dashboard.complete_operation.call_args_list
            if call[0][1] == OperationStatus.ERROR
        ]
        assert len(error_calls) == 1

    @pytest.mark.asyncio
    async def test_preview_disabled_mode(self, shell):
        """
        Test that when preview is disabled:
        - Workflow and dashboard still work
        - Preview flag correctly passed as False
        """
        # Disable preview
        shell.context.preview_enabled = False

        tool_calls = [
            {"tool": "write_file", "args": {"path": "test.py", "content": "data"}},
        ]

        mock_tool = AsyncMock()
        shell.registry.get = Mock(return_value=mock_tool)

        shell._execute_with_recovery = AsyncMock(return_value=ToolResult(
            success=True,
            data="Written",
            metadata={}
        ))

        # Execute
        await shell._execute_tool_calls(tool_calls, turn=1)

        # Verify: preview=False passed
        args = shell._execute_with_recovery.call_args[0][2]
        assert args['preview'] is False

        # Verify: Workflow and dashboard still called
        assert shell.workflow_viz.add_step.called
        assert shell.dashboard.add_operation.called

    @pytest.mark.asyncio
    async def test_commands_integration(self, shell):
        """Test /workflow and /dash commands work."""
        # /workflow command
        should_exit, message = await shell._handle_system_command("/workflow")
        assert should_exit is False
        shell.workflow_viz.render_workflow.assert_called_once()

        # /dash command
        should_exit, message = await shell._handle_system_command("/dash")
        assert should_exit is False
        shell.dashboard.render.assert_called_once()

        # /preview toggle
        should_exit, message = await shell._handle_system_command("/preview")
        assert should_exit is False
        assert shell.context.preview_enabled is True

        should_exit, message = await shell._handle_system_command("/nopreview")
        assert should_exit is False
        assert shell.context.preview_enabled is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
