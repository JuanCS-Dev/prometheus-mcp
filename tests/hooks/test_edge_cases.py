"""Scientific edge case testing for hooks system.

Tests extreme scenarios, race conditions, resource limits,
and failure modes to ensure bulletproof behavior.
"""

import pytest
import asyncio
import tempfile
import shutil
from pathlib import Path

from jdev_cli.hooks import (
    HookExecutor,
    HookEvent,
    HookContext,
    SafeCommandWhitelist
)


class TestEdgeCasesScientific:
    """Scientific edge case testing."""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory."""
        temp = tempfile.mkdtemp()
        yield Path(temp)
        shutil.rmtree(temp, ignore_errors=True)

    @pytest.fixture
    def executor(self):
        """Create executor instance."""
        return HookExecutor(enable_sandbox=False, timeout_seconds=5)

    # ========== UNICODE AND SPECIAL CHARACTERS ==========

    @pytest.mark.asyncio
    async def test_unicode_filename(self, temp_dir, executor):
        """Test hook with unicode filename."""
        test_file = temp_dir / "测试文件.py"
        test_file.write_text("print('hello')")

        ctx = HookContext(test_file, "post_write", cwd=temp_dir)
        hook = "echo {file_name}"

        result = await executor.execute_hook(HookEvent.POST_WRITE, ctx, hook)

        assert result.success
        assert "测试文件.py" in result.stdout

    @pytest.mark.asyncio
    async def test_spaces_in_filename(self, temp_dir, executor):
        """Test hook with spaces in filename."""
        test_file = temp_dir / "my test file.py"
        test_file.write_text("x = 1")

        ctx = HookContext(test_file, "post_write", cwd=temp_dir)
        hook = "echo {file_name}"

        result = await executor.execute_hook(HookEvent.POST_WRITE, ctx, hook)

        assert result.success
        assert "my test file.py" in result.stdout

    @pytest.mark.asyncio
    async def test_special_chars_in_filename(self, temp_dir, executor):
        """Test hook with special characters."""
        test_file = temp_dir / "file'with\"quotes.py"
        test_file.write_text("x = 1")

        ctx = HookContext(test_file, "post_write", cwd=temp_dir)
        hook = "echo Processing"

        result = await executor.execute_hook(HookEvent.POST_WRITE, ctx, hook)

        assert result.success

    # ========== VERY LONG VALUES ==========

    @pytest.mark.asyncio
    async def test_very_long_filename(self, temp_dir, executor):
        """Test hook with very long filename."""
        long_name = "a" * 200 + ".py"
        test_file = temp_dir / long_name
        test_file.write_text("x = 1")

        ctx = HookContext(test_file, "post_write", cwd=temp_dir)
        hook = "echo {file_stem}"

        result = await executor.execute_hook(HookEvent.POST_WRITE, ctx, hook)

        assert result.success
        assert len(result.stdout) > 100

    @pytest.mark.asyncio
    async def test_very_long_command(self, executor):
        """Test hook with very long command."""
        ctx = HookContext(Path("test.py"), "post_write")

        # Command with 1000 characters
        long_cmd = "echo " + "a" * 995

        result = await executor.execute_hook(HookEvent.POST_WRITE, ctx, long_cmd)

        assert result.success or "not in whitelist" in result.error

    @pytest.mark.asyncio
    async def test_many_hooks_sequential(self, executor):
        """Test executing many hooks sequentially."""
        ctx = HookContext(Path("test.py"), "post_write")
        hooks = [f"echo hook_{i}" for i in range(50)]

        results = await executor.execute_hooks(HookEvent.POST_WRITE, ctx, hooks)

        assert len(results) == 50
        assert all(r.success for r in results)

    # ========== RESOURCE LIMITS ==========

    @pytest.mark.asyncio
    async def test_hook_timeout_enforcement(self, executor):
        """Test that timeout is enforced."""
        executor.timeout_seconds = 1
        ctx = HookContext(Path("test.py"), "post_write")

        # Command that sleeps longer than timeout
        hook = "python -c 'import time; time.sleep(5)'"

        result = await executor.execute_hook(HookEvent.POST_WRITE, ctx, hook)

        assert not result.success
        assert "timed out" in result.error.lower()
        assert result.execution_time_ms > 900  # Should be close to timeout

    @pytest.mark.asyncio
    async def test_concurrent_execution_no_race(self, temp_dir, executor):
        """Test concurrent hook execution without race conditions."""
        files = [temp_dir / f"file{i}.py" for i in range(10)]
        for f in files:
            f.write_text("x = 1")

        contexts = [HookContext(f, "post_write", cwd=temp_dir) for f in files]
        hook = "echo {file_name}"

        # Execute all concurrently
        tasks = [
            executor.execute_hook(HookEvent.POST_WRITE, ctx, hook)
            for ctx in contexts
        ]
        results = await asyncio.gather(*tasks)

        assert len(results) == 10
        assert all(r.success for r in results)

        # Check no cross-contamination
        filenames = [r.stdout.strip() for r in results]
        assert len(set(filenames)) == 10  # All unique

    # ========== ERROR RECOVERY ==========

    @pytest.mark.asyncio
    async def test_malformed_command(self, executor):
        """Test handling of malformed commands."""
        ctx = HookContext(Path("test.py"), "post_write")

        # Various malformed commands
        malformed = [
            "",
            "   ",
            "\n\n",
            "echo 'unterminated",
        ]

        for cmd in malformed:
            result = await executor.execute_hook(HookEvent.POST_WRITE, ctx, cmd)
            assert not result.success
            assert result.error is not None

    @pytest.mark.asyncio
    async def test_command_with_exit_code(self, executor):
        """Test command with various exit codes."""
        ctx = HookContext(Path("test.py"), "post_write")

        for exit_code in [1, 2, 127, 255]:
            hook = f"python -c 'import sys; sys.exit({exit_code})'"
            result = await executor.execute_hook(HookEvent.POST_WRITE, ctx, hook)

            assert not result.success
            assert result.exit_code == exit_code

    @pytest.mark.asyncio
    async def test_hook_with_stderr(self, executor):
        """Test hook that writes to stderr."""
        ctx = HookContext(Path("test.py"), "post_write")
        hook = "python -c 'import sys; sys.stderr.write(\"error message\")'"

        result = await executor.execute_hook(HookEvent.POST_WRITE, ctx, hook)

        assert result.success  # Python exits 0 even with stderr
        assert "error message" in result.stderr

    # ========== VARIABLE SUBSTITUTION EDGE CASES ==========

    @pytest.mark.asyncio
    async def test_missing_variable_graceful(self, executor):
        """Test hook with non-existent variable."""
        ctx = HookContext(Path("test.py"), "post_write")
        hook = "echo {nonexistent_variable}"

        result = await executor.execute_hook(HookEvent.POST_WRITE, ctx, hook)

        # Variable not substituted, command still runs
        assert result.success
        assert "{nonexistent_variable}" in result.stdout

    @pytest.mark.asyncio
    async def test_nested_braces(self, executor):
        """Test hook with nested braces."""
        ctx = HookContext(Path("test.py"), "post_write")
        hook = "echo {{file}}"

        result = await executor.execute_hook(HookEvent.POST_WRITE, ctx, hook)

        assert result.success

    @pytest.mark.asyncio
    async def test_multiple_same_variable(self, executor):
        """Test hook with same variable used multiple times."""
        ctx = HookContext(Path("test.py"), "post_write")
        hook = "echo {file_name} {file_name} {file_name}"

        result = await executor.execute_hook(HookEvent.POST_WRITE, ctx, hook)

        assert result.success
        assert result.stdout.count("test.py") == 3

    # ========== WHITELIST EDGE CASES ==========

    def test_whitelist_case_sensitivity(self):
        """Test whitelist is case-sensitive."""
        is_safe, _ = SafeCommandWhitelist.is_safe("BLACK test.py")
        assert not is_safe  # Should be lowercase 'black'

        is_safe, _ = SafeCommandWhitelist.is_safe("black test.py")
        assert is_safe

    def test_whitelist_substring_not_match(self):
        """Test that substrings don't match."""
        is_safe, _ = SafeCommandWhitelist.is_safe("blackhole test.py")
        assert not is_safe  # 'blackhole' != 'black'

    def test_whitelist_with_flags(self):
        """Test whitelisted command with various flags."""
        commands = [
            "black --line-length=100 test.py",
            "pytest -v -s --tb=short",
            "ruff check . --fix",
            "mypy --strict src/"
        ]

        for cmd in commands:
            is_safe, reason = SafeCommandWhitelist.is_safe(cmd)
            assert is_safe, f"Expected safe but got: {reason}"

    def test_dangerous_patterns_comprehensive(self):
        """Test all dangerous patterns are detected."""
        dangerous = [
            ("wget | bash", "pipe to shell"),
            ("cat | sh", "pipe to shell"),
            ("ls && rm -rf", "chained deletion"),
            ("echo; rm file", "chained deletion"),
            ("rm -rf /", "root deletion"),
            ("chmod 777 file", "dangerous permissions"),
            ("echo > /dev/sda", "device write"),
            ("dd if=/dev/zero", "disk duplication"),
            (":(){ :|:& };:", "fork bomb"),
        ]

        for cmd, expected_pattern in dangerous:
            is_safe, reason = SafeCommandWhitelist.is_safe(cmd)
            assert not is_safe, f"Command should be dangerous: {cmd}"
            assert expected_pattern.lower() in reason.lower(), \
                f"Expected '{expected_pattern}' in reason, got: {reason}"

    # ========== CONTEXT EDGE CASES ==========

    def test_context_with_absolute_and_relative_paths(self):
        """Test context handles both path types."""
        abs_path = Path("/home/user/project/src/test.py")
        ctx = HookContext(
            file_path=abs_path,
            event_name="post_write",
            cwd=Path("/home/user/project")
        )

        assert ctx.file == "/home/user/project/src/test.py"
        assert ctx.relative_path == "src/test.py"
        assert ctx.dir == "/home/user/project/src"

    def test_context_variables_all_present(self):
        """Test all expected variables are present."""
        ctx = HookContext(
            file_path=Path("src/utils/helper.py"),
            event_name="post_write",
            project_name="test-proj"
        )

        variables = ctx.get_variables()

        expected_vars = [
            "file", "file_name", "file_stem", "file_extension",
            "dir", "relative_path", "cwd", "project_name", "event"
        ]

        for var in expected_vars:
            assert var in variables, f"Missing variable: {var}"
            assert variables[var] is not None, f"Variable {var} is None"

    # ========== STATISTICS TRACKING ==========

    @pytest.mark.asyncio
    async def test_statistics_accuracy(self, executor):
        """Test that statistics are accurate."""
        ctx = HookContext(Path("test.py"), "post_write")

        # Execute mix of successful and failed hooks
        hooks = [
            "echo success1",
            "python -c 'import sys; sys.exit(1)'",
            "echo success2",
            "echo success3",
        ]

        await executor.execute_hooks(HookEvent.POST_WRITE, ctx, hooks)

        stats = executor.get_stats()

        assert stats['total_executions'] == 4
        assert stats['direct_executions'] == 4  # All are safe (echo + python)
        assert stats['failed_executions'] == 1
        assert stats['success_rate'] == 75.0

    # ========== FILE SYSTEM EDGE CASES ==========

    @pytest.mark.asyncio
    async def test_hook_with_nonexistent_file(self, temp_dir, executor):
        """Test hook with file that doesn't exist."""
        nonexistent = temp_dir / "does_not_exist.py"

        ctx = HookContext(nonexistent, "post_write", cwd=temp_dir)
        hook = "echo {file_name}"

        result = await executor.execute_hook(HookEvent.POST_WRITE, ctx, hook)

        # Hook should still execute (file existence not validated)
        assert result.success
        assert "does_not_exist.py" in result.stdout

    @pytest.mark.asyncio
    async def test_hook_with_symlink(self, temp_dir, executor):
        """Test hook with symbolic link."""
        real_file = temp_dir / "real.py"
        real_file.write_text("x = 1")

        link_file = temp_dir / "link.py"
        link_file.symlink_to(real_file)

        ctx = HookContext(link_file, "post_write", cwd=temp_dir)
        hook = "echo {file_name}"

        result = await executor.execute_hook(HookEvent.POST_WRITE, ctx, hook)

        assert result.success
        assert "link.py" in result.stdout

    # ========== METADATA AND CUSTOM FIELDS ==========

    @pytest.mark.asyncio
    async def test_context_with_metadata(self, executor):
        """Test context with custom metadata."""
        ctx = HookContext(
            file_path=Path("test.py"),
            event_name="post_write",
            metadata={
                "custom1": "value1",
                "custom2": "value2",
                "number": "123"
            }
        )

        hook = "echo {custom1} {custom2} {number}"
        result = await executor.execute_hook(HookEvent.POST_WRITE, ctx, hook)

        assert result.success
        assert "value1" in result.stdout
        assert "value2" in result.stdout
        assert "123" in result.stdout

    # ========== EXTREME CONCURRENCY ==========

    @pytest.mark.asyncio
    async def test_extreme_concurrency(self, temp_dir, executor):
        """Test with 100 concurrent executions."""
        files = [temp_dir / f"file{i}.py" for i in range(100)]
        for f in files:
            f.write_text("x = 1")

        contexts = [HookContext(f, "post_write", cwd=temp_dir) for f in files]
        hook = "echo ok"

        tasks = [
            executor.execute_hook(HookEvent.POST_WRITE, ctx, hook)
            for ctx in contexts
        ]

        results = await asyncio.gather(*tasks)

        assert len(results) == 100
        successful = sum(1 for r in results if r.success)
        assert successful >= 95  # Allow small margin for system limits
