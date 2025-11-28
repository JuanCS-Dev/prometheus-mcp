"""Tests for Shell squad and workflow commands."""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from jdev_cli.shell import InteractiveShell
from jdev_cli.orchestration.squad import WorkflowResult, WorkflowStatus

@pytest.fixture
def mock_squad_class():
    with patch("jdev_cli.shell.DevSquad") as mock_class:
        squad_instance = MagicMock()
        result = WorkflowResult(
            request="test",
            status=WorkflowStatus.COMPLETED
        )
        squad_instance.execute_workflow = AsyncMock(return_value=result)
        squad_instance.get_phase_summary.return_value = "Workflow Completed Successfully"
        mock_class.return_value = squad_instance
        yield mock_class

@pytest.mark.asyncio
async def test_shell_squad_command(mock_squad_class):
    """Test /squad command in shell."""
    # Mock MCPClient to avoid real init
    with patch("jdev_cli.shell.MCPClient"):
        shell = InteractiveShell()
    shell.console = MagicMock()

    # Test /squad command
    await shell._handle_system_command("/squad Create a new feature")

    # Verify output
    shell.console.print.assert_called()
    calls = [str(call) for call in shell.console.print.mock_calls]
    assert any("DevSquad Mission" in c for c in calls)
    assert any("Create a new feature" in c for c in calls)

    # Verify execution
    shell.squad.execute_workflow.assert_called_once()
    assert any("Workflow Completed Successfully" in c for c in calls)

@pytest.mark.asyncio
async def test_shell_workflow_list_command():
    """Test /workflow list command in shell."""
    # Mock MCPClient and DevSquad
    with patch("jdev_cli.shell.MCPClient"), patch("jdev_cli.shell.DevSquad"):
        shell = InteractiveShell()
    shell.console = MagicMock()

    # Test /workflow list
    await shell._handle_system_command("/workflow list")

    # Verify output
    shell.console.print.assert_called()
    # Check if any call argument is a Table with correct title
    from rich.table import Table
    found = False
    for args, _ in shell.console.print.call_args_list:
        if args and isinstance(args[0], Table):
            if "Available Workflows" in args[0].title:
                found = True
                break
    assert found, "Table with title 'Available Workflows' not found in print calls"

@pytest.mark.asyncio
async def test_shell_workflow_run_command(mock_squad_class):
    """Test /workflow run command in shell."""
    # Mock MCPClient
    with patch("jdev_cli.shell.MCPClient"):
        shell = InteractiveShell()
    shell.console = MagicMock()

    # Test /workflow run
    await shell._handle_system_command("/workflow run setup-fastapi")

    # Verify output
    shell.console.print.assert_called()
    calls = [str(call) for call in shell.console.print.mock_calls]
    assert any("Starting Workflow" in c for c in calls)
    assert any("setup-fastapi" in c for c in calls)
    assert any("Execution Plan" in c for c in calls)

    # Verify execution
    shell.squad.execute_workflow.assert_called_once()
    assert any("Workflow Completed Successfully" in c for c in calls)
