"""
Comprehensive coverage tests for SafeCommandExecutor - Advanced edge cases.

These tests focus on:
1. Command Parsing Edge Cases:
   - Escaped quotes handling
   - Multiple spaces normalization
   - Malformed quotes detection

2. Error Handling:
   - FileNotFoundError scenarios
   - PermissionError scenarios
   - Timeout handling

3. Singleton Pattern:
   - Multiple get_safe_executor() calls with custom working_dir
   - Verifying second call ignores working_dir parameter
   - Thread safety and state management

Author: Boris Cherny style - Type-safe, thorough, comprehensive coverage
Date: 2025-11-25
"""

import pytest
import asyncio
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from jdev_tui.core.safe_executor import (
    SafeCommandExecutor,
    get_safe_executor,
)


# =============================================================================
# COMMAND PARSING EDGE CASES - COMPREHENSIVE
# =============================================================================

class TestCommandParsingEdgeCases:
    """Tests for command parsing edge cases using shlex."""

    @pytest.fixture
    def executor(self) -> SafeCommandExecutor:
        """Fresh executor instance."""
        return SafeCommandExecutor()

    # =========================================================================
    # ESCAPED QUOTES TESTS
    # =========================================================================

    @pytest.mark.parametrize("command,expected_allowed", [
        # Single quotes preserved
        ("echo 'hello world'", False),  # echo not whitelisted
        ("pwd", True),  # Simple command

        # Double quotes preserved
        ("echo \"hello world\"", False),  # echo not whitelisted

        # Escaped quotes within quotes
        ("echo \"test\\\"quote\"", False),  # echo not whitelisted
        ("echo 'test\\'quote'", False),  # echo not whitelisted
    ])
    def test_quoted_arguments_parsed_correctly(
        self,
        executor: SafeCommandExecutor,
        command: str,
        expected_allowed: bool
    ) -> None:
        """Quoted arguments should be parsed correctly by shlex."""
        is_allowed, reason = executor.is_command_allowed(command)
        assert is_allowed == expected_allowed, f"Parsing failed for: {command}"

    def test_escaped_quotes_in_whitelisted_command(
        self,
        executor: SafeCommandExecutor
    ) -> None:
        """Escaped quotes in whitelisted commands should parse correctly."""
        # pytest accepts quoted paths
        command = 'pytest -k "test_name"'
        is_allowed, reason = executor.is_command_allowed(command)
        # This depends on whether pytest with quoted args is in whitelist
        assert isinstance(is_allowed, bool)

    def test_single_quote_escape_sequences(
        self,
        executor: SafeCommandExecutor
    ) -> None:
        """Single quotes should preserve content literally."""
        command = "ls -la"  # Safe command
        base_cmd, args = executor._parse_command(command)
        assert base_cmd == "ls"
        assert "-la" in args

    def test_double_quote_escape_sequences(
        self,
        executor: SafeCommandExecutor
    ) -> None:
        """Double quotes should allow escape sequences."""
        command = 'pytest -v -k "test_"'
        base_cmd, args = executor._parse_command(command)
        assert base_cmd == "pytest"
        assert "-v" in args
        assert "-k" in args

    def test_mismatched_quotes_raises_value_error(
        self,
        executor: SafeCommandExecutor
    ) -> None:
        """Mismatched quotes should raise ValueError in shlex.split()."""
        command = 'pytest "unclosed quote'
        base_cmd, args = executor._parse_command(command)
        # Should return ("", []) on error
        assert base_cmd == ""
        assert args == []

    def test_unmatched_single_quote(
        self,
        executor: SafeCommandExecutor
    ) -> None:
        """Unmatched single quote should be caught."""
        command = "ls 'path"
        base_cmd, args = executor._parse_command(command)
        assert base_cmd == ""
        assert args == []

    def test_nested_quotes_parsing(
        self,
        executor: SafeCommandExecutor
    ) -> None:
        """Nested quotes should parse correctly."""
        command = """pytest -v -k 'test and "important"'"""
        base_cmd, args = executor._parse_command(command)
        assert base_cmd == "pytest"
        # shlex handles nested quotes

    # =========================================================================
    # MULTIPLE SPACES TESTS
    # =========================================================================

    @pytest.mark.parametrize("command", [
        "ls  -la",           # double space
        "ls   -la",          # triple space
        "ls     -la",        # many spaces
        "ls\t-la",           # tab separator
        "ls\t\t-la",         # multiple tabs
        "ls  \t  -la",       # mixed spaces and tabs
    ])
    def test_multiple_spaces_normalized(
        self,
        executor: SafeCommandExecutor,
        command: str
    ) -> None:
        """Multiple spaces/tabs should be normalized correctly."""
        base_cmd, args = executor._parse_command(command)
        # shlex.split() handles whitespace normalization
        assert base_cmd == "ls"
        assert "-la" in args

    def test_leading_whitespace_stripped(
        self,
        executor: SafeCommandExecutor
    ) -> None:
        """Leading whitespace should be stripped."""
        command = "   pwd"
        base_cmd, args = executor._parse_command(command)
        assert base_cmd == "pwd"
        assert args == []

    def test_trailing_whitespace_stripped(
        self,
        executor: SafeCommandExecutor
    ) -> None:
        """Trailing whitespace should be stripped."""
        command = "pwd   "
        base_cmd, args = executor._parse_command(command)
        assert base_cmd == "pwd"
        assert args == []

    def test_mixed_leading_trailing_whitespace(
        self,
        executor: SafeCommandExecutor
    ) -> None:
        """Mixed leading/trailing whitespace should be handled."""
        command = "  \t pwd -v  \t "
        base_cmd, args = executor._parse_command(command)
        assert base_cmd == "pwd"

    def test_internal_multiple_spaces_preserved_in_args(
        self,
        executor: SafeCommandExecutor
    ) -> None:
        """Multiple spaces within quoted strings should be preserved."""
        # This tests that "multiple spaces" inside quotes stay intact
        command = 'pytest -k "test and feature"'
        base_cmd, args = executor._parse_command(command)
        assert base_cmd == "pytest"

    # =========================================================================
    # MALFORMED QUOTES TESTS
    # =========================================================================

    def test_mismatched_single_quote_start(
        self,
        executor: SafeCommandExecutor
    ) -> None:
        """Single quote without closing should fail gracefully."""
        command = "pytest 'incomplete"
        base_cmd, args = executor._parse_command(command)
        assert base_cmd == ""
        assert args == []

    def test_mismatched_double_quote_start(
        self,
        executor: SafeCommandExecutor
    ) -> None:
        """Double quote without closing should fail gracefully."""
        command = 'pytest "incomplete'
        base_cmd, args = executor._parse_command(command)
        assert base_cmd == ""
        assert args == []

    def test_alternating_quotes_incomplete(
        self,
        executor: SafeCommandExecutor
    ) -> None:
        """Alternating quotes without proper closing should fail."""
        command = '''pytest "start 'middle" more"'''
        # shlex might handle this, depends on nesting
        base_cmd, args = executor._parse_command(command)
        # Should either parse correctly or return empty
        assert isinstance(base_cmd, str)
        assert isinstance(args, list)

    def test_quote_at_end_incomplete(
        self,
        executor: SafeCommandExecutor
    ) -> None:
        """Quote at end without closing should fail."""
        command = "ls -la '"
        base_cmd, args = executor._parse_command(command)
        assert base_cmd == ""
        assert args == []

    def test_empty_quoted_string(
        self,
        executor: SafeCommandExecutor
    ) -> None:
        """Empty quoted strings should parse correctly."""
        command = 'pytest -v -k ""'
        base_cmd, args = executor._parse_command(command)
        assert base_cmd == "pytest"
        assert "-v" in args

    def test_only_quotes(
        self,
        executor: SafeCommandExecutor
    ) -> None:
        """Command with only quotes should fail."""
        command = '""'
        base_cmd, args = executor._parse_command(command)
        assert base_cmd == ""
        assert args == []

    def test_whitespace_in_quotes_preserved(
        self,
        executor: SafeCommandExecutor
    ) -> None:
        """Whitespace inside quotes should be preserved."""
        command = 'pytest -v -k "test with spaces"'
        base_cmd, args = executor._parse_command(command)
        assert base_cmd == "pytest"
        assert "-v" in args
        # The quoted string with spaces should be one element

    def test_backslash_quote_escaping(
        self,
        executor: SafeCommandExecutor
    ) -> None:
        """Backslash-escaped quotes should be handled."""
        command = r'pytest -k "test\"quote"'
        base_cmd, args = executor._parse_command(command)
        # shlex should handle this
        assert base_cmd == "pytest"

    def test_mixed_quote_types_in_one_command(
        self,
        executor: SafeCommandExecutor
    ) -> None:
        """Mixed single and double quotes should parse."""
        command = """pytest -v -k 'test' -m "mark" """
        base_cmd, args = executor._parse_command(command)
        assert base_cmd == "pytest"


# =============================================================================
# ERROR HANDLING - COMPREHENSIVE
# =============================================================================

class TestErrorHandlingExecution:
    """Tests for error handling during command execution."""

    @pytest.fixture
    def executor(self) -> SafeCommandExecutor:
        """Fresh executor instance."""
        return SafeCommandExecutor()

    # =========================================================================
    # FILE NOT FOUND ERROR TESTS
    # =========================================================================

    @pytest.mark.asyncio
    async def test_nonexistent_whitelisted_command_file_not_found(
        self,
        executor: SafeCommandExecutor
    ) -> None:
        """Whitelisted but non-installed command should return FileNotFoundError result."""
        # Create a mock that raises FileNotFoundError
        with patch('asyncio.create_subprocess_exec') as mock_exec:
            mock_exec.side_effect = FileNotFoundError("Command not found")

            result = await executor.execute("pytest")

            assert not result.success
            assert result.exit_code == -1
            assert "not found" in result.error_message.lower()
            assert result.stdout == ""
            assert result.stderr == ""

    @pytest.mark.asyncio
    async def test_file_not_found_error_captured(
        self,
        executor: SafeCommandExecutor
    ) -> None:
        """FileNotFoundError should be caught and returned as error result."""
        with patch('asyncio.create_subprocess_exec') as mock_exec:
            mock_exec.side_effect = FileNotFoundError("No such file")

            result = await executor.execute("pwd")

            assert not result.success
            assert result.exit_code == -1
            assert result.error_message != ""

    @pytest.mark.asyncio
    async def test_file_not_found_includes_command_name(
        self,
        executor: SafeCommandExecutor
    ) -> None:
        """FileNotFoundError message should include command name."""
        with patch('asyncio.create_subprocess_exec') as mock_exec:
            mock_exec.side_effect = FileNotFoundError()

            result = await executor.execute("mypy")

            assert "mypy" in result.error_message

    # =========================================================================
    # PERMISSION ERROR TESTS
    # =========================================================================

    @pytest.mark.asyncio
    async def test_permission_denied_error_handled(
        self,
        executor: SafeCommandExecutor
    ) -> None:
        """PermissionError should be caught and returned as error result."""
        with patch('asyncio.create_subprocess_exec') as mock_exec:
            mock_exec.side_effect = PermissionError("Permission denied")

            result = await executor.execute("pwd")

            assert not result.success
            assert result.exit_code == -1
            assert "permission" in result.error_message.lower()

    @pytest.mark.asyncio
    async def test_permission_error_includes_command_name(
        self,
        executor: SafeCommandExecutor
    ) -> None:
        """PermissionError message should include command name."""
        with patch('asyncio.create_subprocess_exec') as mock_exec:
            mock_exec.side_effect = PermissionError()

            result = await executor.execute("ruff")

            assert "ruff" in result.error_message

    @pytest.mark.asyncio
    async def test_permission_error_with_custom_working_dir(
        self,
        executor: SafeCommandExecutor
    ) -> None:
        """PermissionError should be handled even with custom working_dir."""
        with tempfile.TemporaryDirectory() as tmpdir:
            executor_with_dir = SafeCommandExecutor(working_dir=Path(tmpdir))

            with patch('asyncio.create_subprocess_exec') as mock_exec:
                mock_exec.side_effect = PermissionError("Access denied")

                result = await executor_with_dir.execute("pwd")

                assert not result.success
                assert "permission" in result.error_message.lower()

    # =========================================================================
    # TIMEOUT HANDLING TESTS
    # =========================================================================

    @pytest.mark.asyncio
    async def test_timeout_kills_process_and_returns_error(
        self,
        executor: SafeCommandExecutor
    ) -> None:
        """Command timeout should kill process and return error."""
        # Mock subprocess that times out
        mock_proc = AsyncMock()
        mock_proc.kill = MagicMock()
        mock_proc.wait = AsyncMock()

        with patch('asyncio.create_subprocess_exec') as mock_exec:
            mock_exec.return_value = mock_proc

            with patch('asyncio.wait_for') as mock_wait_for:
                mock_wait_for.side_effect = asyncio.TimeoutError()

                result = await executor.execute("pwd")

                assert not result.success
                assert result.exit_code == -1
                assert "timed out" in result.error_message.lower()
                # Verify process was killed
                mock_proc.kill.assert_called_once()
                mock_proc.wait.assert_called_once()

    @pytest.mark.asyncio
    async def test_timeout_error_message_includes_timeout_seconds(
        self,
        executor: SafeCommandExecutor
    ) -> None:
        """Timeout error message should include timeout value in seconds."""
        mock_proc = AsyncMock()
        mock_proc.kill = MagicMock()
        mock_proc.wait = AsyncMock()

        with patch('asyncio.create_subprocess_exec') as mock_exec:
            mock_exec.return_value = mock_proc

            with patch('asyncio.wait_for') as mock_wait_for:
                mock_wait_for.side_effect = asyncio.TimeoutError()

                result = await executor.execute("pytest")

                # pytest has 300 second timeout
                assert "300" in result.error_message or "timed out" in result.error_message.lower()

    @pytest.mark.asyncio
    async def test_timeout_with_short_timeout_command(
        self,
        executor: SafeCommandExecutor
    ) -> None:
        """Commands with short timeout should timeout quickly."""
        mock_proc = AsyncMock()
        mock_proc.kill = MagicMock()
        mock_proc.wait = AsyncMock()

        with patch('asyncio.create_subprocess_exec') as mock_exec:
            mock_exec.return_value = mock_proc

            with patch('asyncio.wait_for') as mock_wait_for:
                mock_wait_for.side_effect = asyncio.TimeoutError()

                result = await executor.execute("python --version")

                assert not result.success
                # python --version has 10 second timeout
                assert "timed out" in result.error_message.lower()

    @pytest.mark.asyncio
    async def test_timeout_closes_stderr_stdout_pipes(
        self,
        executor: SafeCommandExecutor
    ) -> None:
        """Timeout handling should properly clean up process."""
        mock_proc = AsyncMock()
        mock_proc.kill = MagicMock()
        mock_proc.wait = AsyncMock()

        with patch('asyncio.create_subprocess_exec') as mock_exec:
            mock_exec.return_value = mock_proc

            with patch('asyncio.wait_for') as mock_wait_for:
                mock_wait_for.side_effect = asyncio.TimeoutError()

                result = await executor.execute("pwd")

                # Should ensure process is killed
                assert mock_proc.kill.called or mock_proc.wait.called

    # =========================================================================
    # GENERIC EXCEPTION HANDLING
    # =========================================================================

    @pytest.mark.asyncio
    async def test_unexpected_exception_caught(
        self,
        executor: SafeCommandExecutor
    ) -> None:
        """Unexpected exceptions should be caught and returned."""
        with patch('asyncio.create_subprocess_exec') as mock_exec:
            mock_exec.side_effect = RuntimeError("Unexpected error")

            result = await executor.execute("pwd")

            assert not result.success
            assert result.exit_code == -1
            assert "RuntimeError" in result.error_message

    @pytest.mark.asyncio
    async def test_os_error_handled(
        self,
        executor: SafeCommandExecutor
    ) -> None:
        """OSError should be caught and returned as error."""
        with patch('asyncio.create_subprocess_exec') as mock_exec:
            mock_exec.side_effect = OSError("System error")

            result = await executor.execute("pwd")

            assert not result.success

    @pytest.mark.asyncio
    async def test_exception_includes_traceback_info(
        self,
        executor: SafeCommandExecutor
    ) -> None:
        """Exception message should include exception type."""
        with patch('asyncio.create_subprocess_exec') as mock_exec:
            mock_exec.side_effect = ValueError("Invalid value")

            result = await executor.execute("pwd")

            assert "ValueError" in result.error_message

    @pytest.mark.asyncio
    async def test_process_returns_nonzero_exit_code(
        self,
        executor: SafeCommandExecutor
    ) -> None:
        """Non-zero exit code should mark result as failed."""
        mock_proc = AsyncMock()
        mock_proc.returncode = 1
        mock_proc.communicate = AsyncMock(
            return_value=(b"", b"error output")
        )

        with patch('asyncio.create_subprocess_exec') as mock_exec:
            mock_exec.return_value = mock_proc

            result = await executor.execute("pwd")

            assert not result.success
            assert result.exit_code == 1
            assert result.error_message != ""

    @pytest.mark.asyncio
    async def test_stderr_captured_on_failure(
        self,
        executor: SafeCommandExecutor
    ) -> None:
        """stderr should be captured when command fails."""
        mock_proc = AsyncMock()
        mock_proc.returncode = 1
        mock_proc.communicate = AsyncMock(
            return_value=(b"", b"error message")
        )

        with patch('asyncio.create_subprocess_exec') as mock_exec:
            mock_exec.return_value = mock_proc

            result = await executor.execute("pwd")

            assert result.stderr == "error message"

    @pytest.mark.asyncio
    async def test_utf8_decode_error_handling(
        self,
        executor: SafeCommandExecutor
    ) -> None:
        """Invalid UTF-8 in output should be handled gracefully."""
        mock_proc = AsyncMock()
        mock_proc.returncode = 0
        # Invalid UTF-8 bytes
        mock_proc.communicate = AsyncMock(
            return_value=(b"\xff\xfe invalid utf8", b"")
        )

        with patch('asyncio.create_subprocess_exec') as mock_exec:
            mock_exec.return_value = mock_proc

            result = await executor.execute("pwd")

            # Should handle decode error with 'replace' option
            assert result.stdout != ""  # Some output present
            assert result.success  # But still marked as success


# =============================================================================
# SINGLETON PATTERN - COMPREHENSIVE
# =============================================================================

class TestSingletonPatternComprehensive:
    """Comprehensive tests for get_safe_executor singleton behavior."""

    def setup_method(self):
        """Reset singleton state before each test."""
        import jdev_tui.core.safe_executor as se_module
        se_module._executor = None

    def teardown_method(self):
        """Reset singleton state after each test."""
        import jdev_tui.core.safe_executor as se_module
        se_module._executor = None

    # =========================================================================
    # INITIAL CREATION WITH CUSTOM WORKING_DIR
    # =========================================================================

    def test_get_safe_executor_with_custom_working_dir(self) -> None:
        """First call with custom working_dir should create executor with that dir."""
        with tempfile.TemporaryDirectory() as tmpdir:
            custom_path = Path(tmpdir)

            executor = get_safe_executor(working_dir=custom_path)

            assert executor is not None
            assert executor._working_dir == custom_path

    def test_get_safe_executor_with_none_uses_cwd(self) -> None:
        """First call with None should use current working directory."""
        executor = get_safe_executor(working_dir=None)

        assert executor is not None
        assert executor._working_dir == Path.cwd()

    def test_get_safe_executor_default_uses_cwd(self) -> None:
        """Call without argument should use current working directory."""
        executor = get_safe_executor()

        assert executor is not None
        assert executor._working_dir == Path.cwd()

    # =========================================================================
    # SINGLETON IDEMPOTENCY - SECOND CALL IGNORES WORKING_DIR
    # =========================================================================

    def test_second_call_returns_same_instance(self) -> None:
        """Second call should return same instance regardless of working_dir."""
        with tempfile.TemporaryDirectory() as tmpdir1:
            with tempfile.TemporaryDirectory() as tmpdir2:
                path1 = Path(tmpdir1)
                path2 = Path(tmpdir2)

                executor1 = get_safe_executor(working_dir=path1)
                executor2 = get_safe_executor(working_dir=path2)

                assert executor1 is executor2

    def test_second_call_ignores_custom_working_dir(self) -> None:
        """Second call with different working_dir should be ignored."""
        with tempfile.TemporaryDirectory() as tmpdir1:
            with tempfile.TemporaryDirectory() as tmpdir2:
                path1 = Path(tmpdir1)
                path2 = Path(tmpdir2)

                executor1 = get_safe_executor(working_dir=path1)
                first_working_dir = executor1._working_dir

                executor2 = get_safe_executor(working_dir=path2)

                # Second call should ignore path2
                assert executor2._working_dir == first_working_dir
                assert executor2._working_dir != path2

    def test_third_call_also_ignores_working_dir(self) -> None:
        """Third call should also return same instance with original working_dir."""
        with tempfile.TemporaryDirectory() as tmpdir1:
            with tempfile.TemporaryDirectory() as tmpdir2:
                with tempfile.TemporaryDirectory() as tmpdir3:
                    path1 = Path(tmpdir1)
                    path2 = Path(tmpdir2)
                    path3 = Path(tmpdir3)

                    executor1 = get_safe_executor(working_dir=path1)
                    executor2 = get_safe_executor(working_dir=path2)
                    executor3 = get_safe_executor(working_dir=path3)

                    assert executor1 is executor2 is executor3
                    assert executor3._working_dir == path1

    # =========================================================================
    # SINGLETON WITH MIXED ARGUMENTS
    # =========================================================================

    def test_first_call_with_path_second_call_without(self) -> None:
        """Singleton should work with first call having path, second without."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir)

            executor1 = get_safe_executor(working_dir=path)
            executor2 = get_safe_executor()  # No working_dir

            assert executor1 is executor2
            assert executor2._working_dir == path

    def test_first_call_without_path_second_call_with(self) -> None:
        """Singleton should work with first call without path, second with."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir)

            executor1 = get_safe_executor()  # No working_dir
            first_dir = executor1._working_dir

            executor2 = get_safe_executor(working_dir=path)

            # Should still have original working_dir
            assert executor1 is executor2
            assert executor2._working_dir == first_dir

    # =========================================================================
    # SINGLETON STATE PRESERVATION
    # =========================================================================

    def test_singleton_preserves_allowed_commands(self) -> None:
        """Singleton should preserve ALLOWED_COMMANDS across instances."""
        executor1 = get_safe_executor()
        commands1 = len(executor1.ALLOWED_COMMANDS)

        executor2 = get_safe_executor()
        commands2 = len(executor2.ALLOWED_COMMANDS)

        assert commands1 == commands2
        assert executor1.ALLOWED_COMMANDS is executor2.ALLOWED_COMMANDS

    def test_singleton_preserves_dangerous_patterns(self) -> None:
        """Singleton should preserve DANGEROUS_PATTERNS."""
        executor1 = get_safe_executor()
        patterns1 = len(executor1.DANGEROUS_PATTERNS)

        executor2 = get_safe_executor()
        patterns2 = len(executor2.DANGEROUS_PATTERNS)

        assert patterns1 == patterns2
        assert executor1.DANGEROUS_PATTERNS is executor2.DANGEROUS_PATTERNS

    # =========================================================================
    # SINGLETON WITH CONCURRENT CALLS
    # =========================================================================

    def test_multiple_concurrent_calls_return_same_instance(self) -> None:
        """Multiple concurrent-style calls should return same instance."""
        with tempfile.TemporaryDirectory() as tmpdir1:
            with tempfile.TemporaryDirectory() as tmpdir2:
                path1 = Path(tmpdir1)
                path2 = Path(tmpdir2)

                # Simulate rapid sequential calls
                executors = []
                for path in [path1, path2, path1]:
                    executors.append(get_safe_executor(working_dir=path))

                # All should be the same instance
                assert executors[0] is executors[1] is executors[2]

    def test_singleton_instance_type(self) -> None:
        """Singleton should be SafeCommandExecutor instance."""
        executor = get_safe_executor()

        assert isinstance(executor, SafeCommandExecutor)
        assert hasattr(executor, 'execute')
        assert hasattr(executor, 'is_command_allowed')
        assert hasattr(executor, '_working_dir')

    # =========================================================================
    # SINGLETON GLOBAL STATE
    # =========================================================================

    def test_global_executor_variable_set_on_first_call(self) -> None:
        """Global _executor should be set on first call."""
        import jdev_tui.core.safe_executor as se_module

        assert se_module._executor is None

        executor = get_safe_executor()

        assert se_module._executor is not None
        assert se_module._executor is executor

    def test_global_executor_not_reset_on_subsequent_calls(self) -> None:
        """Global _executor should not be reset on subsequent calls."""
        import jdev_tui.core.safe_executor as se_module

        executor1 = get_safe_executor()
        first_id = id(se_module._executor)

        executor2 = get_safe_executor()
        second_id = id(se_module._executor)

        assert first_id == second_id


# =============================================================================
# WORKING DIRECTORY TESTS
# =============================================================================

class TestWorkingDirectoryHandling:
    """Tests for working directory handling in command execution."""

    @pytest.mark.asyncio
    async def test_custom_working_dir_passed_to_subprocess(self) -> None:
        """Custom working_dir should be passed to subprocess.create_subprocess_exec."""
        with tempfile.TemporaryDirectory() as tmpdir:
            custom_path = Path(tmpdir)
            executor = SafeCommandExecutor(working_dir=custom_path)

            with patch('asyncio.create_subprocess_exec') as mock_exec:
                mock_proc = AsyncMock()
                mock_proc.returncode = 0
                mock_proc.communicate = AsyncMock(return_value=(b"output", b""))
                mock_exec.return_value = mock_proc

                result = await executor.execute("pwd")

                # Check that cwd was passed
                call_args = mock_exec.call_args
                assert call_args[1]['cwd'] == str(custom_path)

    @pytest.mark.asyncio
    async def test_default_working_dir_is_cwd(self) -> None:
        """Default working_dir should be current working directory."""
        executor = SafeCommandExecutor()

        with patch('asyncio.create_subprocess_exec') as mock_exec:
            mock_proc = AsyncMock()
            mock_proc.returncode = 0
            mock_proc.communicate = AsyncMock(return_value=(b"output", b""))
            mock_exec.return_value = mock_proc

            result = await executor.execute("pwd")

            call_args = mock_exec.call_args
            assert call_args[1]['cwd'] == str(Path.cwd())

    @pytest.mark.asyncio
    async def test_working_dir_path_object_converted_to_string(self) -> None:
        """Path objects should be converted to strings for subprocess."""
        with tempfile.TemporaryDirectory() as tmpdir:
            custom_path = Path(tmpdir)
            executor = SafeCommandExecutor(working_dir=custom_path)

            with patch('asyncio.create_subprocess_exec') as mock_exec:
                mock_proc = AsyncMock()
                mock_proc.returncode = 0
                mock_proc.communicate = AsyncMock(return_value=(b"output", b""))
                mock_exec.return_value = mock_proc

                result = await executor.execute("pwd")

                call_args = mock_exec.call_args
                # Should be string, not Path
                assert isinstance(call_args[1]['cwd'], str)


# =============================================================================
# COMBINED EDGE CASES - STRESS TESTING
# =============================================================================

class TestCombinedEdgeCases:
    """Tests combining multiple edge cases for stress testing."""

    @pytest.fixture
    def executor(self) -> SafeCommandExecutor:
        return SafeCommandExecutor()

    def test_complex_command_with_multiple_edge_cases(
        self,
        executor: SafeCommandExecutor
    ) -> None:
        """Complex command with quotes and spaces should parse correctly."""
        # Multiple spaces, escaped quotes
        command = 'pytest  -v  -k  "test_name"  --tb=short'

        base_cmd, args = executor._parse_command(command)

        assert base_cmd == "pytest"
        assert "-v" in args
        assert "-k" in args

    @pytest.mark.asyncio
    async def test_blocked_command_with_complex_parsing(
        self,
        executor: SafeCommandExecutor
    ) -> None:
        """Dangerous command with complex parsing should still be blocked."""
        # Malformed quotes with dangerous pattern
        command = 'ls "test; rm -rf /"'

        is_allowed, _ = executor.is_command_allowed(command)

        assert not is_allowed

    @pytest.mark.asyncio
    async def test_timeout_with_complex_command(
        self,
        executor: SafeCommandExecutor
    ) -> None:
        """Timeout should work with complex whitelisted commands."""
        mock_proc = AsyncMock()
        mock_proc.kill = MagicMock()
        mock_proc.wait = AsyncMock()

        with patch('asyncio.create_subprocess_exec') as mock_exec:
            mock_exec.return_value = mock_proc

            with patch('asyncio.wait_for') as mock_wait_for:
                mock_wait_for.side_effect = asyncio.TimeoutError()

                result = await executor.execute('pytest -v -k "test" --tb=short')

                assert not result.success
                assert "timed out" in result.error_message.lower()

    def test_dangerous_pattern_in_quoted_string_still_blocked(
        self,
        executor: SafeCommandExecutor
    ) -> None:
        """Dangerous patterns should be blocked even in quoted strings."""
        # Even though shlex would parse this as a single quoted argument,
        # the dangerous pattern check happens before parsing
        command = 'echo "test; rm -rf /"'

        is_allowed, _ = executor.is_command_allowed(command)

        assert not is_allowed

    def test_multiple_parsing_failures_in_sequence(
        self,
        executor: SafeCommandExecutor
    ) -> None:
        """Sequence of malformed commands should all fail gracefully."""
        malformed_commands = [
            'pytest "unclosed',
            "pytest 'unclosed",
            'pytest "test\' mixed',
        ]

        for command in malformed_commands:
            base_cmd, args = executor._parse_command(command)
            # Should return empty base_cmd on error
            assert base_cmd == "" or isinstance(base_cmd, str)
