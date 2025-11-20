"""
Week 2 Integration Tests: Workflow Visualizer + Preview Integration

Tests:
- Workflow steps added during tool execution
- Preview system for file operations
- /preview and /nopreview commands
- Dashboard auto-update

Boris Cherny: Type-safe integration testing
"""

import pytest
import asyncio
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from qwen_dev_cli.shell import InteractiveShell, SessionContext
from qwen_dev_cli.tools.base import ToolResult
from qwen_dev_cli.tui.components.workflow_visualizer import StepStatus

# Note: StepStatus values are PENDING, RUNNING, COMPLETED, FAILED, SKIPPED, BLOCKED


class TestWorkflowIntegration:
    """Test workflow visualizer integration in tool execution."""
    
    @pytest.fixture
    def shell(self):
        """Create shell instance with minimal dependencies."""
        # Create shell without running full __init__
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
        shell.dashboard = Mock()
        return shell
    
    @pytest.mark.asyncio
    async def test_workflow_steps_added_for_multiple_tools(self, shell):
        """Test that workflow steps are added for each tool in sequence."""
        # Setup: Mock tool calls
        tool_calls = [
            {"tool": "read_file", "args": {"path": "test.py"}},
            {"tool": "write_file", "args": {"path": "test.py", "content": "new"}},
        ]
        
        # Mock tools
        mock_tool = AsyncMock()
        mock_tool.execute = AsyncMock(return_value=ToolResult(
            success=True,
            data="Success"
        ))
        shell.registry.get = Mock(return_value=mock_tool)
        
        # Mock conversation tracking
        shell.conversation.add_tool_result = Mock()
        
        # Mock _execute_with_recovery (with proper metadata for read_file)
        shell._execute_with_recovery = AsyncMock(return_value=ToolResult(
            success=True,
            data="Success",
            metadata={'path': 'test.py', 'lines': 10}
        ))
        
        # Execute
        result = await shell._execute_tool_calls(tool_calls, turn=1)
        
        # Verify: Workflow.start_workflow should have been called (2 tools)
        shell.workflow_viz.start_workflow.assert_called_once()
        
        # Verify: add_step called for each tool
        assert shell.workflow_viz.add_step.call_count == 2
        
        # Verify: update_step_status called (IN_PROGRESS + COMPLETED for each)
        assert shell.workflow_viz.update_step_status.call_count >= 2
    
    @pytest.mark.asyncio
    async def test_workflow_step_marked_failed_on_error(self, shell):
        """Test that workflow step is marked as FAILED when tool fails."""
        # Setup: Mock failing tool
        tool_calls = [
            {"tool": "read_file", "args": {"path": "nonexistent.py"}},
        ]
        
        mock_tool = AsyncMock()
        shell.registry.get = Mock(return_value=mock_tool)
        
        # Mock conversation
        shell.conversation.add_tool_result = Mock()
        
        # Mock recovery (should fail)
        shell._execute_with_recovery = AsyncMock(return_value=ToolResult(
            success=False,
            error="File not found"
        ))
        
        # Execute
        result = await shell._execute_tool_calls(tool_calls, turn=1)
        
        # Verify: Step added
        shell.workflow_viz.add_step.assert_called_once()
        
        # Verify: Step marked as FAILED (called with StepStatus.FAILED)
        failed_calls = [
            call for call in shell.workflow_viz.update_step_status.call_args_list
            if StepStatus.FAILED in call[0]
        ]
        assert len(failed_calls) >= 1
    
    @pytest.mark.asyncio
    async def test_console_passed_to_file_tools(self, shell):
        """Test that console object is passed to file tools for preview."""
        # Setup: Mock write_file tool call
        tool_calls = [
            {"tool": "write_file", "args": {"path": "test.py", "content": "data"}},
        ]
        
        mock_tool = AsyncMock()
        shell.registry.get = Mock(return_value=mock_tool)
        
        # Mock conversation
        shell.conversation.add_tool_result = Mock()
        
        # Mock recovery - track args passed
        shell._execute_with_recovery = AsyncMock(return_value=ToolResult(
            success=True,
            data="Written"
        ))
        
        # Execute
        await shell._execute_tool_calls(tool_calls, turn=1)
        
        # Verify: _execute_with_recovery was called
        assert shell._execute_with_recovery.called
        
        # Verify: Args dict contains console and preview
        call_args = shell._execute_with_recovery.call_args[0]  # positional args
        args_dict = call_args[2]  # 3rd positional arg is args dict
        
        assert 'console' in args_dict, "console not passed to tool"
        assert args_dict['console'] == shell.console
        assert 'preview' in args_dict, "preview not passed to tool"
        assert args_dict['preview'] is True


class TestPreviewCommands:
    """Test /preview and /nopreview commands."""
    
    @pytest.fixture
    def shell(self):
        """Create shell with minimal dependencies."""
        shell = object.__new__(InteractiveShell)
        shell.console = Mock()
        shell.context = SessionContext()
        shell.registry = Mock()
        shell.conversation = Mock()
        shell.conversation.add_tool_result = Mock()
        shell._execute_with_recovery = AsyncMock()
        shell.workflow_viz = Mock()
        shell.dashboard = Mock()  # Add dashboard
        return shell
    
    @pytest.mark.asyncio
    async def test_preview_command_enables_preview(self, shell):
        """Test that /preview command enables preview."""
        # Initially should be True (default)
        assert shell.context.preview_enabled is True
        
        # Disable it
        shell.context.preview_enabled = False
        
        # Execute /preview
        should_exit, message = await shell._handle_system_command("/preview")
        
        # Verify
        assert should_exit is False
        assert shell.context.preview_enabled is True
        assert "enabled" in message.lower()
    
    @pytest.mark.asyncio
    async def test_nopreview_command_disables_preview(self, shell):
        """Test that /nopreview command disables preview."""
        # Initially should be True
        assert shell.context.preview_enabled is True
        
        # Execute /nopreview
        should_exit, message = await shell._handle_system_command("/nopreview")
        
        # Verify
        assert should_exit is False
        assert shell.context.preview_enabled is False
        assert "disabled" in message.lower()
    
    @pytest.mark.asyncio
    async def test_preview_setting_persists_across_commands(self, shell):
        """Test that preview setting persists in session context."""
        # Disable preview
        await shell._handle_system_command("/nopreview")
        assert shell.context.preview_enabled is False
        
        # Simulate tool execution
        tool_calls = [
            {"tool": "write_file", "args": {"path": "test.py", "content": "x"}},
        ]
        
        mock_tool = AsyncMock()
        shell.registry.get = Mock(return_value=mock_tool)
        shell.conversation = Mock()
        shell.conversation.add_tool_result = Mock()
        shell._execute_with_recovery = AsyncMock(return_value=ToolResult(
            success=True, data="OK"
        ))
        
        await shell._execute_tool_calls(tool_calls, turn=1)
        
        # Verify: preview=False was passed
        call_args = shell._execute_with_recovery.call_args[0][2]
        assert call_args['preview'] is False


class TestSessionContext:
    """Test SessionContext initialization."""
    
    def test_session_context_has_preview_enabled_by_default(self):
        """Test that SessionContext initializes with preview_enabled=True."""
        context = SessionContext()
        
        assert hasattr(context, 'preview_enabled')
        assert context.preview_enabled is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
