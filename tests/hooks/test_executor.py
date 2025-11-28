"""Tests for hook executor."""

import pytest
from pathlib import Path
from unittest.mock import Mock

from jdev_cli.hooks import (
    HookExecutor,
    HookEvent,
    HookContext,
    HookResult
)


class TestHookExecutor:
    """Test suite for HookExecutor."""

    def test_executor_initialization(self):
        """Test executor initializes with correct defaults."""
        executor = HookExecutor()

        assert executor.timeout_seconds == 30
        assert executor.enable_sandbox is True
        assert executor._execution_count == 0
        assert executor._direct_count == 0
        assert executor._sandbox_count == 0
        assert executor._failed_count == 0

    def test_executor_with_custom_timeout(self):
        """Test executor with custom timeout."""
        executor = HookExecutor(timeout_seconds=60)
        assert executor.timeout_seconds == 60

    def test_executor_with_sandbox_disabled(self):
        """Test executor with sandbox disabled."""
        executor = HookExecutor(enable_sandbox=False)
        assert executor.enable_sandbox is False

    def test_substitute_variables(self):
        """Test variable substitution in commands."""
        executor = HookExecutor()
        ctx = HookContext(
            file_path=Path("src/test.py"),
            event_name="post_write",
            project_name="myproject"
        )

        command = executor._substitute_variables("black {file}", ctx)
        assert command == "black src/test.py"

        command = executor._substitute_variables(
            "pytest tests/test_{file_stem}.py", ctx
        )
        assert command == "pytest tests/test_test.py"

        command = executor._substitute_variables(
            "echo {project_name}/{file_name}", ctx
        )
        assert command == "echo myproject/test.py"

    def test_substitute_multiple_variables(self):
        """Test substitution of multiple variables in one command."""
        executor = HookExecutor()
        ctx = HookContext(
            file_path=Path("src/utils/helper.py"),
            event_name="post_edit"
        )

        command = executor._substitute_variables(
            "cp {file} {dir}/backup_{file_name}", ctx
        )
        assert command == "cp src/utils/helper.py src/utils/backup_helper.py"

    @pytest.mark.asyncio
    async def test_execute_direct_success(self):
        """Test direct execution of safe command (success)."""
        executor = HookExecutor()

        result = await executor._execute_direct("echo hello", Path.cwd())

        assert result.success
        assert result.exit_code == 0
        assert "hello" in result.stdout
        assert not result.executed_in_sandbox

    @pytest.mark.asyncio
    async def test_execute_direct_failure(self):
        """Test direct execution of command that fails."""
        executor = HookExecutor()

        result = await executor._execute_direct(
            "python -c 'import sys; sys.exit(1)'",
            Path.cwd()
        )

        assert not result.success
        assert result.exit_code == 1
        assert not result.executed_in_sandbox

    @pytest.mark.asyncio
    async def test_execute_direct_timeout(self):
        """Test direct execution timeout."""
        executor = HookExecutor(timeout_seconds=1)

        result = await executor._execute_direct(
            "python -c 'import time; time.sleep(10)'",
            Path.cwd()
        )

        assert not result.success
        assert "timed out" in result.error.lower()

    @pytest.mark.asyncio
    async def test_execute_safe_command_direct(self):
        """Test safe command executes directly (not sandboxed)."""
        executor = HookExecutor()
        ctx = HookContext(Path("test.py"), "post_write")

        result = await executor.execute_hook(
            HookEvent.POST_WRITE,
            ctx,
            "echo {file}"
        )

        assert result.success
        assert not result.executed_in_sandbox
        assert executor._direct_count == 1
        assert executor._sandbox_count == 0

    @pytest.mark.asyncio
    async def test_execute_dangerous_command_rejected_no_sandbox(self):
        """Test dangerous command rejected when sandbox disabled."""
        executor = HookExecutor(enable_sandbox=False)
        ctx = HookContext(Path("test.py"), "post_write")

        result = await executor.execute_hook(
            HookEvent.POST_WRITE,
            ctx,
            "unknown_command {file}"
        )

        assert not result.success
        assert "not whitelisted" in result.error
        assert "sandbox disabled" in result.error
        assert executor._failed_count == 1

    @pytest.mark.asyncio
    async def test_execute_dangerous_command_sandboxed(self):
        """Test dangerous command executes in sandbox."""
        mock_sandbox = Mock()
        mock_sandbox.execute_sandboxed = Mock(return_value={
            'success': True,
            'output': 'test output',
            'exit_code': 0
        })

        executor = HookExecutor(
            sandbox_executor=mock_sandbox,
            enable_sandbox=True
        )
        ctx = HookContext(Path("test.py"), "post_write")

        result = await executor.execute_hook(
            HookEvent.POST_WRITE,
            ctx,
            "dangerous_command {file}"
        )

        assert result.success
        assert result.executed_in_sandbox
        assert executor._sandbox_count == 1
        mock_sandbox.execute_sandboxed.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_hooks_multiple(self):
        """Test executing multiple hooks."""
        executor = HookExecutor()
        ctx = HookContext(Path("test.py"), "post_write")

        hooks = [
            "echo first",
            "echo second",
            "echo third"
        ]

        results = await executor.execute_hooks(
            HookEvent.POST_WRITE,
            ctx,
            hooks
        )

        assert len(results) == 3
        assert all(r.success for r in results)
        assert executor._execution_count == 3

    @pytest.mark.asyncio
    async def test_execute_hooks_empty_list(self):
        """Test executing empty hooks list."""
        executor = HookExecutor()
        ctx = HookContext(Path("test.py"), "post_write")

        results = await executor.execute_hooks(
            HookEvent.POST_WRITE,
            ctx,
            []
        )

        assert results == []
        assert executor._execution_count == 0

    @pytest.mark.asyncio
    async def test_execute_hooks_with_failure(self):
        """Test executing hooks where one fails."""
        executor = HookExecutor()
        ctx = HookContext(Path("test.py"), "post_write")

        hooks = [
            "echo success",
            "python -c 'import sys; sys.exit(1)'",
            "echo after_failure"
        ]

        results = await executor.execute_hooks(
            HookEvent.POST_WRITE,
            ctx,
            hooks
        )

        assert len(results) == 3
        assert results[0].success
        assert not results[1].success
        assert results[2].success
        assert executor._failed_count == 1

    def test_get_stats_initial(self):
        """Test get_stats returns correct initial values."""
        executor = HookExecutor()
        stats = executor.get_stats()

        assert stats['total_executions'] == 0
        assert stats['direct_executions'] == 0
        assert stats['sandboxed_executions'] == 0
        assert stats['failed_executions'] == 0
        assert stats['success_rate'] == 0

    @pytest.mark.asyncio
    async def test_get_stats_after_executions(self):
        """Test get_stats after some executions."""
        executor = HookExecutor()
        ctx = HookContext(Path("test.py"), "post_write")

        await executor.execute_hook(HookEvent.POST_WRITE, ctx, "echo success")
        await executor.execute_hook(HookEvent.POST_WRITE, ctx, "echo success2")
        await executor.execute_hook(
            HookEvent.POST_WRITE,
            ctx,
            "python -c 'import sys; sys.exit(1)'"
        )

        stats = executor.get_stats()

        assert stats['total_executions'] == 3
        assert stats['direct_executions'] == 3
        assert stats['failed_executions'] == 1
        assert stats['success_rate'] == pytest.approx(66.67, rel=0.1)

    @pytest.mark.asyncio
    async def test_execution_time_recorded(self):
        """Test that execution time is recorded in results."""
        executor = HookExecutor()
        ctx = HookContext(Path("test.py"), "post_write")

        result = await executor.execute_hook(
            HookEvent.POST_WRITE,
            ctx,
            "echo test"
        )

        assert result.execution_time_ms > 0
        assert result.execution_time_ms < 5000  # Should be fast

    @pytest.mark.asyncio
    async def test_hook_with_invalid_command(self):
        """Test hook with command that doesn't exist."""
        executor = HookExecutor(enable_sandbox=False)
        ctx = HookContext(Path("test.py"), "post_write")

        result = await executor.execute_hook(
            HookEvent.POST_WRITE,
            ctx,
            "nonexistent_command_xyz"
        )

        assert not result.success
        assert result.error is not None


class TestHookResult:
    """Test suite for HookResult dataclass."""

    def test_result_creation_success(self):
        """Test creating successful result."""
        result = HookResult(
            success=True,
            command="black test.py",
            stdout="reformatted test.py",
            exit_code=0,
            execution_time_ms=150.5
        )

        assert result.success
        assert result.command == "black test.py"
        assert result.stdout == "reformatted test.py"
        assert result.exit_code == 0
        assert result.execution_time_ms == 150.5
        assert not result.executed_in_sandbox
        assert result.error is None

    def test_result_creation_failure(self):
        """Test creating failed result."""
        result = HookResult(
            success=False,
            command="dangerous_command",
            error="Command not whitelisted",
            execution_time_ms=5.0
        )

        assert not result.success
        assert result.error == "Command not whitelisted"
        assert result.command == "dangerous_command"
