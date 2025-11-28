"""
Tests for /sandbox slash command.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch

from jdev_cli.commands.sandbox import handle_sandbox
from jdev_cli.integration.sandbox import SandboxResult


@pytest.mark.asyncio
class TestSandboxCommand:
    """Test /sandbox command functionality."""

    async def test_empty_args(self):
        """Test command with no arguments shows help."""
        context = {'cwd': Path.cwd()}
        result = await handle_sandbox("", context)

        assert "Usage:" in result
        assert "/sandbox" in result

    @patch('jdev_cli.commands.sandbox.get_sandbox')
    async def test_sandbox_not_available(self, mock_get_sandbox):
        """Test when Docker is not available."""
        mock_sandbox = Mock()
        mock_sandbox.is_available.return_value = False
        mock_get_sandbox.return_value = mock_sandbox

        context = {'cwd': Path.cwd()}
        result = await handle_sandbox("echo test", context)

        assert "not available" in result.lower()

    @patch('jdev_cli.commands.sandbox.get_sandbox')
    async def test_successful_execution(self, mock_get_sandbox):
        """Test successful command execution."""
        mock_sandbox = Mock()
        mock_sandbox.is_available.return_value = True
        mock_sandbox.execute.return_value = SandboxResult(
            exit_code=0,
            stdout="Hello World",
            stderr="",
            duration_ms=123.45,
            container_id="abc123def456",
            success=True
        )
        mock_get_sandbox.return_value = mock_sandbox

        context = {'cwd': Path.cwd()}
        result = await handle_sandbox("echo 'Hello World'", context)

        assert "Success" in result
        assert "Hello World" in result
        assert "123ms" in result or "123.0ms" in result

    @patch('jdev_cli.commands.sandbox.get_sandbox')
    async def test_failed_execution(self, mock_get_sandbox):
        """Test failed command execution."""
        mock_sandbox = Mock()
        mock_sandbox.is_available.return_value = True
        mock_sandbox.execute.return_value = SandboxResult(
            exit_code=1,
            stdout="",
            stderr="Command failed",
            duration_ms=50.0,
            container_id="abc123",
            success=False
        )
        mock_get_sandbox.return_value = mock_sandbox

        context = {'cwd': Path.cwd()}
        result = await handle_sandbox("false", context)

        assert "Failed" in result
        assert "Command failed" in result

    @patch('jdev_cli.commands.sandbox.get_sandbox')
    async def test_timeout_flag(self, mock_get_sandbox):
        """Test --timeout flag parsing."""
        mock_sandbox = Mock()
        mock_sandbox.is_available.return_value = True
        mock_sandbox.execute.return_value = SandboxResult(
            exit_code=0,
            stdout="",
            stderr="",
            duration_ms=100.0,
            container_id="abc",
            success=True
        )
        mock_get_sandbox.return_value = mock_sandbox

        context = {'cwd': Path.cwd()}
        await handle_sandbox("echo test --timeout 60", context)

        # Verify timeout was passed correctly
        call_args = mock_sandbox.execute.call_args
        assert call_args.kwargs['timeout'] == 60

    @patch('jdev_cli.commands.sandbox.get_sandbox')
    async def test_readonly_flag(self, mock_get_sandbox):
        """Test --readonly flag parsing."""
        mock_sandbox = Mock()
        mock_sandbox.is_available.return_value = True
        mock_sandbox.execute.return_value = SandboxResult(
            exit_code=0,
            stdout="",
            stderr="",
            duration_ms=100.0,
            container_id="abc",
            success=True
        )
        mock_get_sandbox.return_value = mock_sandbox

        context = {'cwd': Path.cwd()}
        await handle_sandbox("cat file.txt --readonly", context)

        # Verify readonly was passed correctly
        call_args = mock_sandbox.execute.call_args
        assert call_args.kwargs['readonly'] is True

    @patch('jdev_cli.commands.sandbox.get_sandbox')
    async def test_context_cwd(self, mock_get_sandbox):
        """Test that cwd from context is used."""
        mock_sandbox = Mock()
        mock_sandbox.is_available.return_value = True
        mock_sandbox.execute.return_value = SandboxResult(
            exit_code=0,
            stdout="",
            stderr="",
            duration_ms=100.0,
            container_id="abc",
            success=True
        )
        mock_get_sandbox.return_value = mock_sandbox

        test_cwd = Path("/test/directory")
        context = {'cwd': test_cwd}
        await handle_sandbox("ls", context)

        # Verify cwd was passed correctly
        call_args = mock_sandbox.execute.call_args
        assert call_args.kwargs['cwd'] == test_cwd

    @patch('jdev_cli.commands.sandbox.get_sandbox')
    async def test_execution_exception(self, mock_get_sandbox):
        """Test handling of execution exceptions."""
        mock_sandbox = Mock()
        mock_sandbox.is_available.return_value = True
        mock_sandbox.execute.side_effect = Exception("Docker error")
        mock_get_sandbox.return_value = mock_sandbox

        context = {'cwd': Path.cwd()}
        result = await handle_sandbox("echo test", context)

        assert "Error" in result or "failed" in result.lower()

    @patch('jdev_cli.commands.sandbox.get_sandbox')
    @patch('jdev_cli.commands.sandbox.safety_validator')
    async def test_safety_validation_warning(self, mock_validator, mock_get_sandbox):
        """Test that dangerous commands show safety warning."""
        mock_sandbox = Mock()
        mock_sandbox.is_available.return_value = True
        mock_sandbox.execute.return_value = SandboxResult(
            exit_code=0,
            stdout="",
            stderr="",
            duration_ms=100.0,
            container_id="abc",
            success=True
        )
        mock_get_sandbox.return_value = mock_sandbox

        # Mock safety validator to flag command as unsafe
        mock_validator.is_safe.return_value = (False, "Dangerous pattern detected")

        context = {'cwd': Path.cwd()}
        result = await handle_sandbox("rm -rf /", context)

        # Should show warning but still execute in sandbox
        assert mock_validator.is_safe.called
        assert mock_sandbox.execute.called

    @patch('jdev_cli.commands.sandbox.get_sandbox')
    @patch('jdev_cli.commands.sandbox.safety_validator')
    async def test_safety_validation_safe_command(self, mock_validator, mock_get_sandbox):
        """Test that safe commands pass validation."""
        mock_sandbox = Mock()
        mock_sandbox.is_available.return_value = True
        mock_sandbox.execute.return_value = SandboxResult(
            exit_code=0,
            stdout="test output",
            stderr="",
            duration_ms=100.0,
            container_id="abc",
            success=True
        )
        mock_get_sandbox.return_value = mock_sandbox

        # Mock safety validator to approve command
        mock_validator.is_safe.return_value = (True, None)

        context = {'cwd': Path.cwd()}
        result = await handle_sandbox("echo safe command", context)

        # Should execute without warning
        assert mock_validator.is_safe.called
        assert mock_sandbox.execute.called
        assert "test output" in result


class TestSandboxCommandHelp:
    """Test help formatting."""

    @pytest.mark.asyncio
    async def test_help_format(self):
        """Test help message format."""
        context = {'cwd': Path.cwd()}
        result = await handle_sandbox("", context)

        assert "Usage:" in result
        assert "Examples:" in result
        assert "Flags:" in result
        assert "Features:" in result
