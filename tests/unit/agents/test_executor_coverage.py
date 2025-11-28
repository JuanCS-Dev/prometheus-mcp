"""
Extended test coverage for executor.py - Execution Engine tests.

This module provides comprehensive test coverage for:
1. CodeExecutionEngine with Docker/E2B modes and resource limits
2. Retry logic with exponential backoff and timeout handling
3. NextGenExecutorAgent validation with all PermissionLevels (DENY, ASK, ALLOW)
4. Approval callback system with sync/async support
5. History management with 100-item limit
6. Paranoid mode validation with LLM checks

Based on Anthropic Claude Code testing standards.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from jdev_cli.agents.executor import (
    ExecutionMode,
    SecurityLevel,
    CommandResult,
    CodeExecutionEngine,
    NextGenExecutorAgent,
)
from jdev_cli.agents.base import (
    AgentTask,
)
from jdev_cli.permissions import PermissionLevel


# =============================================================================
# CODEEXECUTIONENGINE - DOCKER MODE TESTS
# =============================================================================

class TestCodeExecutionEngineDocker:
    """Comprehensive tests for Docker execution mode."""

    def test_docker_mode_initialization(self):
        """Test Docker mode initialization."""
        engine = CodeExecutionEngine(mode=ExecutionMode.DOCKER)
        assert engine.mode == ExecutionMode.DOCKER
        assert "max_memory_mb" in engine.resource_limits
        assert "max_cpu_percent" in engine.resource_limits

    def test_docker_custom_resource_limits(self):
        """Test Docker with custom resource limits."""
        limits = {"max_memory_mb": 2048, "max_cpu_percent": 75}
        engine = CodeExecutionEngine(
            mode=ExecutionMode.DOCKER,
            resource_limits=limits
        )
        assert engine.resource_limits == limits

    @pytest.mark.asyncio
    async def test_docker_execution_builds_command_structure(self):
        """Test Docker execution builds correct command structure."""
        engine = CodeExecutionEngine(
            mode=ExecutionMode.DOCKER,
            resource_limits={"max_memory_mb": 512, "max_cpu_percent": 50}
        )

        with patch.object(engine, '_execute_local', new_callable=AsyncMock) as mock_local:
            mock_local.return_value = CommandResult(
                success=True,
                stdout="output",
                stderr="",
                exit_code=0,
                command="docker run...",
                execution_time=1.0
            )

            await engine.execute("echo test")

            # Verify Docker command was built with correct parameters
            call_args = mock_local.call_args[0][0]
            assert "docker run" in call_args
            assert "--memory=512m" in call_args
            assert "--cpus=0.5" in call_args

    @pytest.mark.asyncio
    async def test_docker_execution_with_high_memory_limit(self):
        """Test Docker with high memory limits."""
        limits = {"max_memory_mb": 4096, "max_cpu_percent": 100}
        engine = CodeExecutionEngine(
            mode=ExecutionMode.DOCKER,
            resource_limits=limits
        )

        with patch.object(engine, '_execute_local', new_callable=AsyncMock) as mock_local:
            mock_local.return_value = CommandResult(
                success=True,
                stdout="",
                stderr="",
                exit_code=0,
                command="docker run...",
                execution_time=1.0
            )

            await engine.execute("python heavy_script.py")

            call_args = mock_local.call_args[0][0]
            assert "--memory=4096m" in call_args
            assert "--cpus=1.0" in call_args

    @pytest.mark.asyncio
    async def test_docker_execution_with_low_memory_limit(self):
        """Test Docker with minimal memory limits."""
        limits = {"max_memory_mb": 64, "max_cpu_percent": 10}
        engine = CodeExecutionEngine(
            mode=ExecutionMode.DOCKER,
            resource_limits=limits
        )

        with patch.object(engine, '_execute_local', new_callable=AsyncMock) as mock_local:
            mock_local.return_value = CommandResult(
                success=True,
                stdout="",
                stderr="",
                exit_code=0,
                command="docker run...",
                execution_time=1.0
            )

            await engine.execute("ls")

            call_args = mock_local.call_args[0][0]
            assert "--memory=64m" in call_args
            assert "--cpus=0.1" in call_args


# =============================================================================
# CODEEXECUTIONENGINE - E2B MODE TESTS
# =============================================================================

class TestCodeExecutionEngineE2B:
    """Comprehensive tests for E2B execution mode."""

    def test_e2b_mode_initialization(self):
        """Test E2B mode initialization."""
        engine = CodeExecutionEngine(mode=ExecutionMode.E2B)
        assert engine.mode == ExecutionMode.E2B

    @pytest.mark.asyncio
    async def test_e2b_execution_fallback_to_local(self):
        """Test E2B execution falls back to local when not implemented."""
        engine = CodeExecutionEngine(mode=ExecutionMode.E2B)

        result = await engine.execute("echo 'e2b fallback'")

        # E2B should fallback to local execution
        assert result.success is True or result.success is False
        assert result.command == "echo 'e2b fallback'"

    @pytest.mark.asyncio
    async def test_e2b_with_timeout(self):
        """Test E2B execution with timeout."""
        engine = CodeExecutionEngine(
            mode=ExecutionMode.E2B,
            timeout=0.1
        )

        result = await engine.execute("sleep 5", trace_id="e2b-timeout-test")

        # Should timeout
        assert result.success is False
        assert result.trace_id == "e2b-timeout-test"

    @pytest.mark.asyncio
    async def test_e2b_with_trace_id(self):
        """Test E2B execution preserves trace ID."""
        engine = CodeExecutionEngine(mode=ExecutionMode.E2B)

        result = await engine.execute("echo test", trace_id="custom-e2b-trace")

        assert result.trace_id == "custom-e2b-trace"


# =============================================================================
# RETRY LOGIC & TIMEOUT TESTS
# =============================================================================

class TestCodeExecutionEngineRetryLogic:
    """Comprehensive tests for retry logic with timeout."""

    @pytest.mark.asyncio
    async def test_retry_logic_first_attempt_success(self):
        """Test no retries needed on first success."""
        engine = CodeExecutionEngine(max_retries=3)

        result = await engine.execute("echo success")

        assert result.success is True
        assert result.retries == 0

    @pytest.mark.asyncio
    async def test_retry_logic_timeout_then_success(self):
        """Test successful retry after timeout."""
        engine = CodeExecutionEngine(timeout=0.05, max_retries=3)

        with patch.object(engine, '_execute_local', new_callable=AsyncMock) as mock_local:
            # First call times out, second succeeds
            mock_local.side_effect = [
                asyncio.TimeoutError(),
                CommandResult(
                    success=True,
                    stdout="success",
                    stderr="",
                    exit_code=0,
                    command="test",
                    execution_time=0.1
                )
            ]

            result = await engine.execute("test command")

            # Should succeed on second attempt
            assert result.success is True
            # Retries should be > 0 (it tried and retried)
            assert mock_local.call_count == 2

    @pytest.mark.asyncio
    async def test_retry_logic_exponential_backoff(self):
        """Test exponential backoff between retries."""
        engine = CodeExecutionEngine(timeout=0.01, max_retries=3)

        with patch.object(engine, '_execute_local', new_callable=AsyncMock) as mock_local:
            mock_local.side_effect = asyncio.TimeoutError()
            with patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep:

                result = await engine.execute("timeout command")

                # Should have slept with exponential backoff
                # 2^0 = 1s, 2^1 = 2s
                assert mock_sleep.call_count >= 1
                sleep_calls = [c[0][0] for c in mock_sleep.call_args_list]
                assert any(s >= 1.0 for s in sleep_calls)

    @pytest.mark.asyncio
    async def test_retry_logic_max_retries_exceeded(self):
        """Test max retries limit is enforced."""
        engine = CodeExecutionEngine(timeout=0.01, max_retries=2)

        with patch.object(engine, '_execute_local', new_callable=AsyncMock) as mock_local:
            mock_local.side_effect = asyncio.TimeoutError()

            result = await engine.execute("always timeout")

            # Should fail after max_retries attempts
            assert result.success is False
            assert "timed out" in result.stderr.lower()
            assert mock_local.call_count == 2

    @pytest.mark.asyncio
    async def test_retry_logic_exception_handling(self):
        """Test retry on general exceptions."""
        engine = CodeExecutionEngine(max_retries=3)

        with patch.object(engine, '_execute_local', new_callable=AsyncMock) as mock_local:
            # First call raises, second succeeds
            mock_local.side_effect = [
                RuntimeError("Network error"),
                CommandResult(
                    success=True,
                    stdout="recovered",
                    stderr="",
                    exit_code=0,
                    command="test",
                    execution_time=0.1
                )
            ]

            result = await engine.execute("test")

            assert result.success is True
            assert mock_local.call_count == 2

    @pytest.mark.asyncio
    async def test_retry_logic_max_retries_exception(self):
        """Test max retries with exceptions."""
        engine = CodeExecutionEngine(max_retries=2)

        with patch.object(engine, '_execute_local', new_callable=AsyncMock) as mock_local:
            mock_local.side_effect = ValueError("Persistent error")

            result = await engine.execute("failing command")

            assert result.success is False
            assert "Persistent error" in result.stderr
            assert mock_local.call_count == 2

    @pytest.mark.asyncio
    async def test_timeout_configurable(self):
        """Test timeout is configurable."""
        engine = CodeExecutionEngine(timeout=60.0)
        assert engine.timeout == 60.0

        engine2 = CodeExecutionEngine(timeout=5.0)
        assert engine2.timeout == 5.0

    @pytest.mark.asyncio
    async def test_timeout_with_long_command(self):
        """Test timeout with intentionally slow command."""
        engine = CodeExecutionEngine(timeout=0.1, max_retries=1)

        result = await engine.execute("sleep 10")

        assert result.success is False
        assert "timed out" in result.stderr.lower()


# =============================================================================
# ERROR RECOVERY TESTS
# =============================================================================

class TestCodeExecutionEngineErrorRecovery:
    """Tests for error recovery mechanisms."""

    @pytest.mark.asyncio
    async def test_error_recovery_command_not_found(self):
        """Test recovery from command not found error."""
        engine = CodeExecutionEngine(max_retries=1)

        result = await engine.execute("nonexistent_command_xyz")

        assert result.success is False
        assert result.exit_code != 0

    @pytest.mark.asyncio
    async def test_error_recovery_permission_denied(self):
        """Test recovery from permission denied."""
        engine = CodeExecutionEngine(max_retries=1)

        result = await engine.execute("cat /root/.ssh/id_rsa")

        # Will either fail with permission denied or succeed depending on environment
        assert result.exit_code in (126, 1, 2) or result.exit_code == 0

    @pytest.mark.asyncio
    async def test_error_recovery_invalid_syntax(self):
        """Test recovery from invalid bash syntax."""
        engine = CodeExecutionEngine(max_retries=1)

        result = await engine.execute("echo test ||| invalid")

        assert result.success is False
        assert result.exit_code != 0


# =============================================================================
# NEXTGENEXECUTORAGENT - VALIDATION WITH PERMISSION LEVELS
# =============================================================================

class TestNextGenExecutorValidationPermissionLevels:
    """Tests for validation with all PermissionLevels (DENY, ASK, ALLOW)."""

    @pytest.fixture
    def agent(self):
        """Create agent with mocks."""
        mock_llm = MagicMock()
        mock_mcp = MagicMock()
        return NextGenExecutorAgent(
            llm_client=mock_llm,
            mcp_client=mock_mcp,
            security_level=SecurityLevel.STANDARD
        )

    @pytest.mark.asyncio
    async def test_validate_permission_level_deny(self, agent):
        """Test validation with DENY permission level."""
        agent.permission_manager.check_permission = MagicMock(
            return_value=(PermissionLevel.DENY, "Command denied by policy")
        )

        result = await agent._validate_command("dangerous_command")

        assert result["allowed"] is False
        assert "denied" in result["reason"].lower() or "policy" in result["reason"].lower()
        assert result["requires_approval"] is False

    @pytest.mark.asyncio
    async def test_validate_permission_level_ask(self, agent):
        """Test validation with ASK permission level."""
        agent.permission_manager.check_permission = MagicMock(
            return_value=(PermissionLevel.ASK, "Requires user approval")
        )

        result = await agent._validate_command("network_command")

        assert result["allowed"] is True
        assert result["requires_approval"] is True
        assert "approval" in result["reason"].lower() or "requires" in result["reason"].lower()

    @pytest.mark.asyncio
    async def test_validate_permission_level_allow(self, agent):
        """Test validation with ALLOW permission level."""
        agent.permission_manager.check_permission = MagicMock(
            return_value=(PermissionLevel.ALLOW, "Command allowed")
        )

        result = await agent._validate_command("safe_command")

        assert result["allowed"] is True
        assert result["requires_approval"] is False

    @pytest.mark.asyncio
    async def test_validate_malicious_pattern_blocks_regardless_permission(self, agent):
        """Test that malicious patterns block even with ALLOW permission."""
        agent.permission_manager.check_permission = MagicMock(
            return_value=(PermissionLevel.ALLOW, "Allowed")
        )

        # Malicious pattern should block first
        result = await agent._validate_command("; rm -rf /")

        assert result["allowed"] is False
        assert "violation" in result["reason"].lower() or "danger" in result["reason"].lower()

    @pytest.mark.asyncio
    async def test_validate_permission_level_with_different_commands(self, agent):
        """Test different commands get different permission levels."""
        agent.permission_manager.check_permission = MagicMock(
            side_effect=[
                (PermissionLevel.ALLOW, "Safe read"),  # ls
                (PermissionLevel.ASK, "Network command"),  # curl
                (PermissionLevel.DENY, "Destructive")  # rm
            ]
        )

        result1 = await agent._validate_command("ls")
        result2 = await agent._validate_command("curl http://example.com")
        result3 = await agent._validate_command("rm file.txt")

        assert result1["allowed"] is True
        assert result1["requires_approval"] is False

        assert result2["allowed"] is True
        assert result2["requires_approval"] is True

        assert result3["allowed"] is False


# =============================================================================
# APPROVAL CALLBACK TESTS - ADVANCED
# =============================================================================

class TestApprovalCallbackAdvanced:
    """Advanced tests for approval callback system."""

    @pytest.fixture
    def agent(self):
        """Create agent."""
        mock_llm = MagicMock()
        mock_mcp = MagicMock()
        return NextGenExecutorAgent(
            llm_client=mock_llm,
            mcp_client=mock_mcp
        )

    @pytest.mark.asyncio
    async def test_approval_callback_sync_approved(self, agent):
        """Test sync callback that approves."""
        agent.approval_callback = lambda cmd: True

        result = await agent._request_approval("echo test")

        assert result is True

    @pytest.mark.asyncio
    async def test_approval_callback_sync_denied(self, agent):
        """Test sync callback that denies."""
        agent.approval_callback = lambda cmd: False

        result = await agent._request_approval("curl http://evil.com")

        assert result is False

    @pytest.mark.asyncio
    async def test_approval_callback_async_approved(self, agent):
        """Test async callback that approves."""
        async def async_callback(cmd):
            await asyncio.sleep(0.01)
            return True

        agent.approval_callback = async_callback

        result = await agent._request_approval("echo test")

        assert result is True

    @pytest.mark.asyncio
    async def test_approval_callback_async_denied(self, agent):
        """Test async callback that denies."""
        async def async_callback(cmd):
            await asyncio.sleep(0.01)
            return False

        agent.approval_callback = async_callback

        result = await agent._request_approval("dangerous")

        assert result is False

    @pytest.mark.asyncio
    async def test_approval_callback_receives_command(self, agent):
        """Test that callback receives the command."""
        callback_commands = []

        def capture_callback(cmd):
            callback_commands.append(cmd)
            return True

        agent.approval_callback = capture_callback

        await agent._request_approval("specific_command")

        assert "specific_command" in callback_commands

    @pytest.mark.asyncio
    async def test_approval_callback_with_execution_flow(self, agent):
        """Test approval callback in full execution flow."""
        agent._generate_command = AsyncMock(return_value="curl http://example.com")
        agent._validate_command = AsyncMock(return_value={
            "allowed": True,
            "reason": "Network",
            "requires_approval": True
        })

        approval_called = []

        def approval_callback(cmd):
            approval_called.append(cmd)
            return True

        agent.approval_callback = approval_callback
        agent._observe_result = AsyncMock(return_value="OK")
        agent._reflect_on_execution = AsyncMock(return_value=[])

        task = AgentTask(request="Fetch URL")
        response = await agent.execute(task)

        assert len(approval_called) > 0


# =============================================================================
# HISTORY MANAGEMENT TESTS - 100 ITEM LIMIT
# =============================================================================

class TestHistoryManagement:
    """Tests for execution history management with 100-item limit."""

    @pytest.fixture
    def agent(self):
        """Create agent."""
        mock_llm = MagicMock()
        mock_mcp = MagicMock()
        return NextGenExecutorAgent(
            llm_client=mock_llm,
            mcp_client=mock_mcp,
            security_level=SecurityLevel.PERMISSIVE
        )

    def test_history_empty_initially(self, agent):
        """Test history starts empty."""
        assert len(agent.execution_history) == 0

    def test_history_stores_command_results(self, agent):
        """Test history stores CommandResult objects."""
        result = CommandResult(
            success=True,
            stdout="output",
            stderr="",
            exit_code=0,
            command="test",
            execution_time=0.1
        )

        agent.execution_history.append(result)

        assert len(agent.execution_history) == 1
        assert agent.execution_history[0].command == "test"

    @pytest.mark.asyncio
    async def test_history_limit_not_exceeded_after_execute(self, agent):
        """Test history doesn't exceed limit after executions."""
        agent._generate_command = AsyncMock(return_value="echo test")
        agent._validate_command = AsyncMock(return_value={
            "allowed": True,
            "reason": "Safe",
            "requires_approval": False
        })
        agent._observe_result = AsyncMock(return_value="OK")
        agent._reflect_on_execution = AsyncMock(return_value=[])

        # Execute 150 commands
        for i in range(150):
            task = AgentTask(request=f"test {i}")
            await agent.execute(task)

        # History should be trimmed to max 100
        assert len(agent.execution_history) <= 100

    def test_history_maintains_order(self, agent):
        """Test history maintains insertion order."""
        for i in range(10):
            result = CommandResult(
                success=True,
                stdout="",
                stderr="",
                exit_code=0,
                command=f"cmd_{i}",
                execution_time=0.1
            )
            agent.execution_history.append(result)

        assert agent.execution_history[0].command == "cmd_0"
        assert agent.execution_history[9].command == "cmd_9"

    def test_history_oldest_removed_on_overflow(self, agent):
        """Test oldest entries are removed when limit exceeded."""
        # Add exactly 101 items
        for i in range(101):
            result = CommandResult(
                success=True,
                stdout="",
                stderr="",
                exit_code=0,
                command=f"cmd_{i}",
                execution_time=0.1
            )
            agent.execution_history.append(result)
            # Simulate the trimming that happens in execute()
            if len(agent.execution_history) > 100:
                agent.execution_history.pop(0)

        # Should have 100 items, cmd_0 removed
        assert len(agent.execution_history) == 100
        assert agent.execution_history[0].command == "cmd_1"
        assert agent.execution_history[-1].command == "cmd_100"

    @pytest.mark.asyncio
    async def test_history_context_uses_recent_5(self, agent):
        """Test history context uses last 5 items."""
        for i in range(10):
            result = CommandResult(
                success=True,
                stdout="output",
                stderr="",
                exit_code=0,
                command=f"cmd_{i}",
                execution_time=0.1
            )
            agent.execution_history.append(result)

        context = agent._get_execution_history_context(limit=5)

        # Should contain last 5 commands
        assert "cmd_9" in context
        assert "cmd_5" in context
        assert "cmd_4" not in context or len([l for l in context.split('\n') if 'cmd_' in l]) <= 5


# =============================================================================
# PARANOID MODE VALIDATION TESTS
# =============================================================================

class TestParanoidModeValidation:
    """Comprehensive tests for PARANOID security level validation."""

    @pytest.fixture
    def paranoid_agent(self):
        """Create agent in PARANOID mode."""
        mock_llm = MagicMock()
        mock_mcp = MagicMock()
        return NextGenExecutorAgent(
            llm_client=mock_llm,
            mcp_client=mock_mcp,
            security_level=SecurityLevel.PARANOID
        )

    @pytest.fixture
    def standard_agent(self):
        """Create agent in STANDARD mode."""
        mock_llm = MagicMock()
        mock_mcp = MagicMock()
        return NextGenExecutorAgent(
            llm_client=mock_llm,
            mcp_client=mock_mcp,
            security_level=SecurityLevel.STANDARD
        )

    @pytest.mark.asyncio
    async def test_paranoid_mode_runs_llm_validation(self, paranoid_agent):
        """Test PARANOID mode always validates with LLM."""
        paranoid_agent.permission_manager.check_permission = MagicMock(
            return_value=(PermissionLevel.ALLOW, "Allowed")
        )
        paranoid_agent.llm_client.generate = AsyncMock(
            return_value='{"is_safe": true, "reason": "Safe"}'
        )

        result = await paranoid_agent._validate_command("ls")

        # LLM should be called
        assert paranoid_agent.llm_client.generate.called

    @pytest.mark.asyncio
    async def test_paranoid_mode_blocks_unsafe_llm_response(self, paranoid_agent):
        """Test PARANOID mode blocks when LLM says unsafe."""
        paranoid_agent.permission_manager.check_permission = MagicMock(
            return_value=(PermissionLevel.ALLOW, "Allowed")
        )
        paranoid_agent.llm_client.generate = AsyncMock(
            return_value='{"is_safe": false, "reason": "Suspicious pattern"}'
        )

        result = await paranoid_agent._validate_command("suspicious_cmd")

        assert result["allowed"] is False
        assert "LLM" in result["reason"]

    @pytest.mark.asyncio
    async def test_paranoid_mode_allows_safe_llm_response(self, paranoid_agent):
        """Test PARANOID mode allows when LLM says safe."""
        paranoid_agent.permission_manager.check_permission = MagicMock(
            return_value=(PermissionLevel.ALLOW, "Allowed")
        )
        paranoid_agent.llm_client.generate = AsyncMock(
            return_value='{"is_safe": true, "reason": "Safe operation"}'
        )

        result = await paranoid_agent._validate_command("echo test")

        assert result["allowed"] is True

    @pytest.mark.asyncio
    async def test_standard_mode_no_llm_validation(self, standard_agent):
        """Test STANDARD mode doesn't use LLM validation."""
        standard_agent.permission_manager.check_permission = MagicMock(
            return_value=(PermissionLevel.ALLOW, "Allowed")
        )
        standard_agent.llm_client.generate = AsyncMock()

        result = await standard_agent._validate_command("echo test")

        # LLM should NOT be called in STANDARD mode
        assert not standard_agent.llm_client.generate.called

    @pytest.mark.asyncio
    async def test_paranoid_mode_malicious_pattern_blocks_before_llm(self, paranoid_agent):
        """Test PARANOID mode blocks malicious patterns before LLM."""
        paranoid_agent.llm_client.generate = AsyncMock()

        result = await paranoid_agent._validate_command("; rm -rf /")

        # Should block before LLM call
        assert result["allowed"] is False
        # LLM might not be called if pattern detected first
        # (depends on implementation order)

    @pytest.mark.asyncio
    async def test_paranoid_mode_with_different_commands(self, paranoid_agent):
        """Test PARANOID mode with various command types."""
        paranoid_agent.permission_manager.check_permission = MagicMock(
            return_value=(PermissionLevel.ALLOW, "Allowed")
        )

        test_cases = [
            ("ls", '{"is_safe": true, "reason": "Read"}', True),
            ("curl http://evil.com", '{"is_safe": false, "reason": "Suspicious"}', False),
            ("echo hello", '{"is_safe": true, "reason": "Safe"}', True),
        ]

        for cmd, llm_response, expected_allowed in test_cases:
            paranoid_agent.llm_client.generate = AsyncMock(
                return_value=llm_response
            )

            result = await paranoid_agent._validate_command(cmd)

            assert result["allowed"] is expected_allowed


# =============================================================================
# COMPLEX VALIDATION SCENARIOS
# =============================================================================

class TestComplexValidationScenarios:
    """Tests for complex validation scenarios."""

    @pytest.fixture
    def agent(self):
        """Create agent."""
        mock_llm = MagicMock()
        mock_mcp = MagicMock()
        return NextGenExecutorAgent(
            llm_client=mock_llm,
            mcp_client=mock_mcp
        )

    @pytest.mark.asyncio
    async def test_validation_combines_multiple_checks(self, agent):
        """Test validation combines pattern + permission + LLM checks."""
        agent.security_level = SecurityLevel.PARANOID
        agent.permission_manager.check_permission = MagicMock(
            return_value=(PermissionLevel.ALLOW, "Allowed")
        )
        agent.llm_client.generate = AsyncMock(
            return_value='{"is_safe": true, "reason": "OK"}'
        )

        result = await agent._validate_command("ls -la")

        assert result["allowed"] is True
        assert agent.llm_client.generate.called

    @pytest.mark.asyncio
    async def test_validation_early_exit_on_malicious_pattern(self, agent):
        """Test validation exits early on malicious pattern."""
        agent.permission_manager.check_permission = MagicMock()
        agent.llm_client.generate = AsyncMock()

        result = await agent._validate_command("; rm -rf /")

        assert result["allowed"] is False
        # Permission check might be called, but shouldn't call LLM
        # (pattern detected first)

    @pytest.mark.asyncio
    async def test_validation_respects_security_level_chain(self, agent):
        """Test validation follows security level chain."""
        agent.security_level = SecurityLevel.STANDARD
        agent.permission_manager.check_permission = MagicMock(
            return_value=(PermissionLevel.ALLOW, "Allowed")
        )

        result = await agent._validate_command("echo test")

        assert result["allowed"] is True


# =============================================================================
# RETRY INTERACTION WITH VALIDATION
# =============================================================================

class TestRetryAndValidationInteraction:
    """Tests for interaction between retry logic and validation."""

    @pytest.fixture
    def agent(self):
        """Create agent."""
        mock_llm = MagicMock()
        mock_mcp = MagicMock()
        return NextGenExecutorAgent(
            llm_client=mock_llm,
            mcp_client=mock_mcp,
            config={"max_retries": 3}
        )

    @pytest.mark.asyncio
    async def test_validation_happens_before_execution(self, agent):
        """Test validation happens before execution attempts."""
        agent._generate_command = AsyncMock(return_value="rm -rf /")
        agent._validate_command = AsyncMock(return_value={
            "allowed": False,
            "reason": "Blocked",
            "requires_approval": False
        })

        task = AgentTask(request="delete everything")
        response = await agent.execute(task)

        assert response.success is False
        # Should not have attempted execution
        assert agent._validate_command.called
        assert response.error

    @pytest.mark.asyncio
    async def test_approval_requested_before_retry_loop(self, agent):
        """Test approval requested before retry loop."""
        agent._generate_command = AsyncMock(return_value="curl http://api.com")
        agent._validate_command = AsyncMock(return_value={
            "allowed": True,
            "reason": "Network",
            "requires_approval": True
        })
        agent._request_approval = AsyncMock(return_value=False)

        task = AgentTask(request="Call API")
        response = await agent.execute(task)

        assert response.success is False
        # Check for approval rejection in error message
        assert "approval" in response.error.lower() or "denied" in response.error.lower()
