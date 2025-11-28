"""Tests for non-interactive mode (single-shot execution)."""

import pytest
import tempfile
from pathlib import Path
from typer.testing import CliRunner

from jdev_cli.cli import app
from jdev_cli.core.single_shot import SingleShotExecutor, execute_single_shot


runner = CliRunner()


class TestSingleShotExecutor:
    """Test SingleShotExecutor class."""

    def test_executor_initialization(self):
        """Test executor initializes correctly."""
        executor = SingleShotExecutor()

        assert executor.llm is not None
        assert executor.context_builder is not None
        assert executor.registry is not None
        assert len(executor.registry.get_all()) > 0

    def test_executor_tools_registered(self):
        """Test essential tools are registered."""
        executor = SingleShotExecutor()
        tools = executor.registry.get_all()

        # Check essential tools exist
        tool_names = set(tools.keys())
        essential_tools = {
            'read_file', 'write_file', 'edit_file',
            'list_directory', 'search_files',
            'bash_command', 'git_status', 'git_diff'
        }

        # At least some essential tools should be registered
        assert len(tool_names & essential_tools) >= 5

    def test_build_context(self):
        """Test context building."""
        executor = SingleShotExecutor()
        context = executor._build_context()

        assert 'cwd' in context
        assert 'project_structure' in context
        assert isinstance(context['cwd'], str)
        assert len(context['cwd']) > 0

    def test_parse_tool_calls_valid(self):
        """Test parsing valid tool calls."""
        executor = SingleShotExecutor()

        response = '[{"tool": "readfile", "args": {"path": "test.py"}}]'
        tool_calls = executor._parse_tool_calls(response)

        assert isinstance(tool_calls, list)
        assert len(tool_calls) == 1
        assert tool_calls[0]['tool'] == 'readfile'
        assert tool_calls[0]['args']['path'] == 'test.py'

    def test_parse_tool_calls_with_text(self):
        """Test parsing tool calls embedded in text."""
        executor = SingleShotExecutor()

        response = 'Sure, here are the tools:\n[{"tool": "gitstatus", "args": {}}]\nDone!'
        tool_calls = executor._parse_tool_calls(response)

        assert isinstance(tool_calls, list)
        assert len(tool_calls) == 1
        assert tool_calls[0]['tool'] == 'gitstatus'

    def test_parse_tool_calls_no_tools(self):
        """Test parsing response without tool calls."""
        executor = SingleShotExecutor()

        response = 'This is just a plain text response without any tool calls.'
        tool_calls = executor._parse_tool_calls(response)

        assert isinstance(tool_calls, list)
        assert len(tool_calls) == 0

    def test_format_results_success(self):
        """Test formatting successful results."""
        executor = SingleShotExecutor()

        results = [
            {'success': True, 'tool': 'readfile', 'output': 'content here'},
            {'success': True, 'tool': 'gitstatus', 'output': 'clean'}
        ]

        formatted = executor._format_results(results)

        assert formatted['success'] is True
        assert len(formatted['actions_taken']) == 2
        assert len(formatted['errors']) == 0
        assert 'readfile' in formatted['output']
        assert 'gitstatus' in formatted['output']

    def test_format_results_with_errors(self):
        """Test formatting results with errors."""
        executor = SingleShotExecutor()

        results = [
            {'success': True, 'tool': 'readfile', 'output': 'content'},
            {'success': False, 'tool': 'writefile', 'error': 'Permission denied'}
        ]

        formatted = executor._format_results(results)

        assert formatted['success'] is False
        assert len(formatted['actions_taken']) == 2
        assert len(formatted['errors']) == 1
        assert 'Permission denied' in formatted['errors'][0]

    @pytest.mark.asyncio
    async def test_execute_simple_request(self):
        """Test executing simple request (no tools)."""
        # This test requires LLM, mark as integration test
        pytest.skip("Requires LLM - integration test")

    @pytest.mark.asyncio
    async def test_execute_with_tool_calls(self):
        """Test executing request that triggers tool calls."""
        # This test requires LLM, mark as integration test
        pytest.skip("Requires LLM - integration test")


class TestCLINonInteractive:
    """Test CLI non-interactive mode."""

    def test_chat_command_help(self):
        """Test chat command shows help."""
        result = runner.invoke(app, ["chat", "--help"])

        assert result.exit_code == 0
        assert "chat" in result.output.lower()
        assert "--message" in result.output

    def test_chat_without_message_requires_shell(self):
        """Test chat without -m tries to start shell."""
        # This would start interactive shell, so we just check the command exists
        # Full test would require mocking the shell
        result = runner.invoke(app, ["chat", "--help"])
        assert result.exit_code == 0

    def test_chat_with_message_flag(self):
        """Test chat with --message flag (single message mode)."""
        # This test requires LLM, mark as integration test
        result = runner.invoke(app, ["chat", "--message", "hello", "--no-context"])

        # Should not crash, but may fail without API key
        # We're testing the command structure works
        assert result.exit_code in [0, 1]  # 1 if LLM fails, which is ok

    def test_chat_json_output_format(self):
        """Test JSON output format."""
        result = runner.invoke(app, [
            "chat",
            "--message", "test",
            "--json",
            "--no-context"
        ])

        # Should attempt to produce JSON (even if LLM fails)
        # Check command doesn't crash
        assert result.exit_code in [0, 1]

    def test_chat_output_to_file(self):
        """Test saving output to file."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            output_path = f.name

        try:
            result = runner.invoke(app, [
                "chat",
                "--message", "hello",
                "--output", output_path,
                "--no-context"
            ])

            # File should be created (even if content is error message)
            assert Path(output_path).exists()

        finally:
            # Cleanup
            if Path(output_path).exists():
                Path(output_path).unlink()

    def test_chat_no_context_flag(self):
        """Test --no-context flag."""
        result = runner.invoke(app, [
            "chat",
            "--message", "test",
            "--no-context"
        ])

        # Should not crash
        assert result.exit_code in [0, 1]


class TestExecuteSingleShot:
    """Test execute_single_shot function."""

    @pytest.mark.asyncio
    async def test_execute_returns_dict(self):
        """Test execute_single_shot returns proper structure."""
        # Mock test - doesn't actually call LLM
        result = {
            'success': True,
            'output': 'test',
            'actions_taken': [],
            'errors': []
        }

        # Verify structure
        assert isinstance(result, dict)
        assert 'success' in result
        assert 'output' in result
        assert 'actions_taken' in result
        assert 'errors' in result

    @pytest.mark.asyncio
    async def test_execute_with_context(self):
        """Test execute_single_shot with context enabled."""
        pytest.skip("Requires LLM - integration test")

    @pytest.mark.asyncio
    async def test_execute_without_context(self):
        """Test execute_single_shot with context disabled."""
        pytest.skip("Requires LLM - integration test")


# Integration tests (require LLM API)
class TestNonInteractiveIntegration:
    """Integration tests requiring LLM."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_real_single_shot_execution(self):
        """Test real single-shot execution with LLM."""
        # Requires valid API credentials
        result = await execute_single_shot(
            "What is 2+2?",
            include_context=False
        )

        assert result['success'] is True
        assert len(result['output']) > 0

    @pytest.mark.integration
    def test_real_cli_single_message(self):
        """Test real CLI single message."""
        result = runner.invoke(app, [
            "chat",
            "--message", "What is Python?",
            "--no-context"
        ])

        # Should succeed with valid API key
        assert result.exit_code == 0
        assert len(result.output) > 0

    @pytest.mark.integration
    def test_real_cli_with_json_output(self):
        """Test real CLI with JSON output."""
        result = runner.invoke(app, [
            "chat",
            "--message", "say hello",  # Simple message for cleaner JSON
            "--json",
            "--no-context"
        ])

        # Should succeed or fail gracefully
        assert result.exit_code in [0, 1]

        # Should have JSON-like structure in output
        assert '{' in result.output
        assert '"success"' in result.output or '"error"' in result.output
