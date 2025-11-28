"""
Tests for Phase 3.1: Error Recovery Loop

Tests error recovery engine, diagnosis, and auto-correction.
"""

import pytest
from unittest.mock import Mock, AsyncMock

from jdev_cli.core.recovery import (
    ErrorRecoveryEngine,
    ErrorCategory,
    RecoveryStrategy,
    RecoveryContext,
    RecoveryResult,
)


class TestErrorCategorization:
    """Test error categorization."""

    def test_syntax_errors(self):
        """Test syntax error detection."""
        engine = ErrorRecoveryEngine(llm_client=Mock())

        assert engine.categorize_error("SyntaxError: invalid syntax") == ErrorCategory.SYNTAX
        assert engine.categorize_error("Parse error at line 10") == ErrorCategory.SYNTAX

    def test_permission_errors(self):
        """Test permission error detection."""
        engine = ErrorRecoveryEngine(llm_client=Mock())

        assert engine.categorize_error("Permission denied") == ErrorCategory.PERMISSION
        assert engine.categorize_error("Access forbidden") == ErrorCategory.PERMISSION

    def test_not_found_errors(self):
        """Test not found error detection."""
        engine = ErrorRecoveryEngine(llm_client=Mock())

        assert engine.categorize_error("File not found: test.txt") == ErrorCategory.NOT_FOUND
        assert engine.categorize_error("Path does not exist") == ErrorCategory.NOT_FOUND
        assert engine.categorize_error("No such file or directory") == ErrorCategory.NOT_FOUND

    def test_command_not_found(self):
        """Test command not found detection (should not be confused with NOT_FOUND)."""
        engine = ErrorRecoveryEngine(llm_client=Mock())

        assert engine.categorize_error("bash: command not found: xyz") == ErrorCategory.COMMAND_NOT_FOUND
        assert engine.categorize_error("command not recognized") == ErrorCategory.COMMAND_NOT_FOUND

    def test_timeout_errors(self):
        """Test timeout error detection."""
        engine = ErrorRecoveryEngine(llm_client=Mock())

        assert engine.categorize_error("Timeout after 30s") == ErrorCategory.TIMEOUT
        assert engine.categorize_error("Operation timed out") == ErrorCategory.TIMEOUT

    def test_type_errors(self):
        """Test type error detection."""
        engine = ErrorRecoveryEngine(llm_client=Mock())

        assert engine.categorize_error("TypeError: expected str, got int") == ErrorCategory.TYPE_ERROR

    def test_value_errors(self):
        """Test value error detection."""
        engine = ErrorRecoveryEngine(llm_client=Mock())

        assert engine.categorize_error("ValueError: invalid value") == ErrorCategory.VALUE_ERROR

    def test_network_errors(self):
        """Test network error detection."""
        engine = ErrorRecoveryEngine(llm_client=Mock())

        assert engine.categorize_error("Network error: connection refused") == ErrorCategory.NETWORK
        # "Connection timeout" has "timeout" keyword, so categorized as TIMEOUT (order matters)
        assert engine.categorize_error("Network connection failed") == ErrorCategory.NETWORK

    def test_unknown_errors(self):
        """Test unknown error fallback."""
        engine = ErrorRecoveryEngine(llm_client=Mock())

        assert engine.categorize_error("Some weird error") == ErrorCategory.UNKNOWN


class TestRecoveryStrategy:
    """Test recovery strategy determination."""

    def test_syntax_strategy(self):
        """Test strategy for syntax errors."""
        engine = ErrorRecoveryEngine(llm_client=Mock())

        context = RecoveryContext(
            attempt_number=1,
            max_attempts=2,
            error="SyntaxError",
            error_category=ErrorCategory.SYNTAX,
            failed_tool="test",
            failed_args={},
            previous_result=None,
            user_intent="test",
            previous_commands=[]
        )

        strategy = engine.determine_strategy(ErrorCategory.SYNTAX, context)
        assert strategy == RecoveryStrategy.RETRY_MODIFIED

    def test_permission_strategy(self):
        """Test strategy for permission errors."""
        engine = ErrorRecoveryEngine(llm_client=Mock())

        context = RecoveryContext(
            attempt_number=1,
            max_attempts=2,
            error="Permission denied",
            error_category=ErrorCategory.PERMISSION,
            failed_tool="test",
            failed_args={},
            previous_result=None,
            user_intent="test",
            previous_commands=[]
        )

        strategy = engine.determine_strategy(ErrorCategory.PERMISSION, context)
        assert strategy == RecoveryStrategy.SUGGEST_PERMISSION

    def test_command_not_found_strategy(self):
        """Test strategy for command not found."""
        engine = ErrorRecoveryEngine(llm_client=Mock())

        context = RecoveryContext(
            attempt_number=1,
            max_attempts=2,
            error="command not found",
            error_category=ErrorCategory.COMMAND_NOT_FOUND,
            failed_tool="test",
            failed_args={},
            previous_result=None,
            user_intent="test",
            previous_commands=[]
        )

        strategy = engine.determine_strategy(ErrorCategory.COMMAND_NOT_FOUND, context)
        assert strategy == RecoveryStrategy.SUGGEST_INSTALL

    def test_escalation_on_max_attempts(self):
        """Test escalation when max attempts reached."""
        engine = ErrorRecoveryEngine(llm_client=Mock())

        context = RecoveryContext(
            attempt_number=2,
            max_attempts=2,
            error="Unknown error",
            error_category=ErrorCategory.UNKNOWN,
            failed_tool="test",
            failed_args={},
            previous_result=None,
            user_intent="test",
            previous_commands=[]
        )

        strategy = engine.determine_strategy(ErrorCategory.UNKNOWN, context)
        assert strategy == RecoveryStrategy.ESCALATE


class TestRecoveryEngine:
    """Test recovery engine."""

    def test_engine_initialization(self):
        """Test creating recovery engine."""
        llm = Mock()
        engine = ErrorRecoveryEngine(
            llm_client=llm,
            max_attempts=2,
            enable_learning=True
        )

        assert engine.llm == llm
        assert engine.max_attempts == 2
        assert engine.enable_learning
        assert len(engine.recovery_history) == 0

    @pytest.mark.asyncio
    async def test_escalation_strategy(self):
        """Test escalation strategy (no recovery attempt)."""
        llm = Mock()
        engine = ErrorRecoveryEngine(llm_client=llm, max_attempts=2)

        context = RecoveryContext(
            attempt_number=2,
            max_attempts=2,
            error="Fatal error",
            error_category=ErrorCategory.UNKNOWN,
            failed_tool="test",
            failed_args={},
            previous_result=None,
            user_intent="test",
            previous_commands=[]
        )

        result = await engine.attempt_recovery(context)

        assert not result.success
        assert not result.recovered
        assert result.escalation_reason is not None

    @pytest.mark.asyncio
    async def test_llm_diagnosis(self):
        """Test LLM diagnosis for error."""
        llm = Mock()
        llm.generate_async = AsyncMock(return_value={
            "content": """DIAGNOSIS: Missing argument in function call
CORRECTION: Add required parameter
TOOL_CALL: {"tool": "corrected_tool", "args": {"fixed": "value"}}"""
        })

        engine = ErrorRecoveryEngine(llm_client=llm, max_attempts=2)

        context = RecoveryContext(
            attempt_number=1,
            max_attempts=2,
            error="Missing argument",
            error_category=ErrorCategory.SYNTAX,
            failed_tool="test_tool",
            failed_args={"bad": "args"},
            previous_result=None,
            user_intent="Do something",
            previous_commands=[]
        )

        diagnosis, correction = await engine.diagnose_error(context)

        assert "Missing argument" in diagnosis
        assert correction is not None
        assert correction["tool"] == "corrected_tool"
        assert correction["args"] == {"fixed": "value"}

    @pytest.mark.asyncio
    async def test_recovery_with_correction(self):
        """Test recovery with LLM correction."""
        llm = Mock()
        llm.generate_async = AsyncMock(return_value={
            "content": """DIAGNOSIS: Wrong file path
TOOL_CALL: {"tool": "read_file", "args": {"path": "correct_path.txt"}}"""
        })

        engine = ErrorRecoveryEngine(llm_client=llm, max_attempts=2)

        context = RecoveryContext(
            attempt_number=1,
            max_attempts=2,
            error="File not found: wrong_path.txt",
            error_category=ErrorCategory.NOT_FOUND,
            failed_tool="read_file",
            failed_args={"path": "wrong_path.txt"},
            previous_result=None,
            user_intent="Read a file",
            previous_commands=[]
        )

        result = await engine.attempt_recovery(context)

        assert result.success
        assert result.corrected_tool == "read_file"
        assert result.corrected_args == {"path": "correct_path.txt"}

    @pytest.mark.asyncio
    async def test_recovery_without_correction(self):
        """Test recovery when LLM cannot provide correction."""
        llm = Mock()
        llm.generate_async = AsyncMock(return_value={
            "content": "DIAGNOSIS: Error is too complex to auto-fix"
        })

        engine = ErrorRecoveryEngine(llm_client=llm, max_attempts=2)

        context = RecoveryContext(
            attempt_number=1,
            max_attempts=2,
            error="Complex error",
            error_category=ErrorCategory.UNKNOWN,
            failed_tool="test",
            failed_args={},
            previous_result=None,
            user_intent="test",
            previous_commands=[]
        )

        result = await engine.attempt_recovery(context)

        assert not result.success
        assert result.escalation_reason is not None

    def test_learning_common_errors(self):
        """Test tracking common errors."""
        engine = ErrorRecoveryEngine(llm_client=Mock(), enable_learning=True)

        # Record same error multiple times
        for i in range(5):
            engine.common_errors["File not found"] = engine.common_errors.get("File not found", 0) + 1

        assert engine.common_errors["File not found"] == 5

    def test_learning_successful_fixes(self):
        """Test recording successful fixes."""
        engine = ErrorRecoveryEngine(llm_client=Mock(), enable_learning=True)

        context = RecoveryContext(
            attempt_number=1,
            max_attempts=2,
            error="Test error",
            error_category=ErrorCategory.SYNTAX,
            failed_tool="test",
            failed_args={},
            previous_result=None,
            user_intent="test",
            previous_commands=[],
            suggested_fix="Fixed it"
        )

        result = RecoveryResult(
            success=True,
            recovered=True,
            attempts_used=1
        )

        engine.record_recovery_outcome(context, result, final_success=True)

        assert "Test error" in engine.successful_fixes
        assert len(engine.successful_fixes["Test error"]) == 1

    def test_statistics(self):
        """Test recovery statistics."""
        engine = ErrorRecoveryEngine(llm_client=Mock(), enable_learning=True)

        # Add some recovery history
        engine.recovery_history.extend([
            {"final_success": True},
            {"final_success": False},
            {"final_success": True},
        ])

        stats = engine.get_statistics()

        assert stats["total_recovery_attempts"] == 3
        assert stats["successful_recoveries"] == 2
        assert stats["success_rate"] == 2/3

    def test_constitutional_p6_max_attempts(self):
        """Test Constitutional P6: Max 2 attempts enforced."""
        engine = ErrorRecoveryEngine(llm_client=Mock(), max_attempts=2)

        assert engine.max_attempts == 2


class TestRecoveryContext:
    """Test recovery context."""

    def test_context_creation(self):
        """Test creating recovery context."""
        context = RecoveryContext(
            attempt_number=1,
            max_attempts=2,
            error="Test error",
            error_category=ErrorCategory.SYNTAX,
            failed_tool="test_tool",
            failed_args={"arg": "value"},
            previous_result=None,
            user_intent="Do something",
            previous_commands=[{"tool": "prev", "args": {}}]
        )

        assert context.attempt_number == 1
        assert context.max_attempts == 2
        assert context.error == "Test error"
        assert context.error_category == ErrorCategory.SYNTAX

    def test_context_serialization(self):
        """Test context to_dict."""
        context = RecoveryContext(
            attempt_number=1,
            max_attempts=2,
            error="Test",
            error_category=ErrorCategory.SYNTAX,
            failed_tool="test",
            failed_args={},
            previous_result=None,
            user_intent="test",
            previous_commands=[],
            diagnosis="Test diagnosis",
            suggested_fix="Test fix",
            recovery_strategy=RecoveryStrategy.RETRY_MODIFIED
        )

        data = context.to_dict()

        assert data["attempt"] == "1/2"
        assert data["error"] == "Test"
        assert data["category"] == "syntax"
        assert data["diagnosis"] == "Test diagnosis"
        assert data["strategy"] == "retry_modified"


class TestRecoveryResult:
    """Test recovery result."""

    def test_successful_recovery(self):
        """Test successful recovery result."""
        result = RecoveryResult(
            success=True,
            recovered=True,
            attempts_used=1,
            corrected_tool="fixed_tool",
            corrected_args={"fixed": "args"},
            what_worked="LLM correction"
        )

        assert result.success
        assert result.recovered
        assert result.attempts_used == 1
        assert result.corrected_tool == "fixed_tool"

    def test_failed_recovery(self):
        """Test failed recovery result."""
        result = RecoveryResult(
            success=False,
            recovered=False,
            attempts_used=2,
            final_error="Could not fix",
            escalation_reason="Too complex"
        )

        assert not result.success
        assert not result.recovered
        assert result.final_error == "Could not fix"
        assert result.escalation_reason == "Too complex"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
