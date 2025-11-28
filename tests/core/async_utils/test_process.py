"""
Tests for async process operations.

SCALE & SUSTAIN Phase 3.1 validation.
"""

import pytest

from jdev_core.async_utils import (
    run_command,
    run_shell,
    run_many,
    ProcessResult,
)


class TestProcessResult:
    """Test ProcessResult dataclass."""

    def test_process_result_success(self):
        """Test successful process result."""
        result = ProcessResult(
            returncode=0,
            stdout="output",
            stderr="",
            command="echo test"
        )

        assert result.success is True
        assert result.output == "output"

    def test_process_result_failure(self):
        """Test failed process result."""
        result = ProcessResult(
            returncode=1,
            stdout="",
            stderr="error message",
            command="false"
        )

        assert result.success is False
        assert "error message" in result.output

    def test_process_result_combined_output(self):
        """Test combined stdout and stderr."""
        result = ProcessResult(
            returncode=0,
            stdout="stdout line",
            stderr="stderr line",
            command="test"
        )

        assert "stdout line" in result.output
        assert "stderr line" in result.output


class TestRunCommand:
    """Test run_command function."""

    @pytest.mark.asyncio
    async def test_run_simple_command(self):
        """Test running a simple command."""
        result = await run_command("echo hello")

        assert result.success is True
        assert result.stdout == "hello"

    @pytest.mark.asyncio
    async def test_run_command_with_args(self):
        """Test running command with arguments."""
        result = await run_command(["echo", "arg1", "arg2"])

        assert result.success is True
        assert "arg1" in result.stdout
        assert "arg2" in result.stdout

    @pytest.mark.asyncio
    async def test_run_command_failure(self):
        """Test running a failing command."""
        result = await run_command("false")

        assert result.success is False
        assert result.returncode != 0

    @pytest.mark.asyncio
    async def test_run_command_with_cwd(self, tmp_path):
        """Test running command in specific directory."""
        result = await run_command("pwd", cwd=str(tmp_path))

        assert result.success is True
        assert str(tmp_path) in result.stdout

    @pytest.mark.asyncio
    async def test_run_command_timeout(self):
        """Test command timeout."""
        result = await run_command("sleep 10", timeout=0.1)

        assert result.success is False
        assert "timed out" in result.stderr.lower()

    @pytest.mark.asyncio
    async def test_run_command_with_env(self):
        """Test running command with custom environment."""
        import os
        env = {**os.environ, "TEST_VAR": "test_value"}
        result = await run_command("echo $TEST_VAR", shell=True, env=env)

        assert result.success is True
        assert "test_value" in result.stdout


class TestRunShell:
    """Test run_shell function."""

    @pytest.mark.asyncio
    async def test_run_shell_script(self):
        """Test running a shell script."""
        script = "echo 'line1' && echo 'line2'"
        result = await run_shell(script)

        assert result.success is True
        assert "line1" in result.stdout
        assert "line2" in result.stdout

    @pytest.mark.asyncio
    async def test_run_shell_with_pipes(self):
        """Test shell script with pipes."""
        script = "echo 'hello world' | tr 'a-z' 'A-Z'"
        result = await run_shell(script)

        assert result.success is True
        assert "HELLO WORLD" in result.stdout


class TestRunMany:
    """Test run_many function."""

    @pytest.mark.asyncio
    async def test_run_many_concurrent(self):
        """Test running multiple commands concurrently."""
        commands = [
            "echo cmd1",
            "echo cmd2",
            "echo cmd3",
        ]

        results = await run_many(commands)

        assert len(results) == 3
        assert all(r.success for r in results)
        assert "cmd1" in results[0].stdout
        assert "cmd2" in results[1].stdout
        assert "cmd3" in results[2].stdout

    @pytest.mark.asyncio
    async def test_run_many_fail_fast(self):
        """Test run_many with fail_fast option."""
        commands = [
            "echo first",
            "false",  # This will fail
            "echo third",
        ]

        results = await run_many(commands, fail_fast=True)

        # Should stop after the failure
        assert len(results) == 2
        assert results[0].success is True
        assert results[1].success is False

    @pytest.mark.asyncio
    async def test_run_many_all_succeed(self):
        """Test run_many when all commands succeed."""
        commands = [
            ["echo", "a"],
            ["echo", "b"],
        ]

        results = await run_many(commands)

        assert all(r.success for r in results)
