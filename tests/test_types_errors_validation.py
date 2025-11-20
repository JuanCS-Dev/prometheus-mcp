"""
Comprehensive tests for types, errors, and validation modules.

Boris Cherny philosophy: "Tests or it didn't happen."

Test coverage:
- Type definitions and guards
- Error hierarchy and serialization
- Validation rules and composition
- Edge cases and error conditions
"""

import pytest
from pathlib import Path
from typing import Any
import tempfile
import os

from qwen_dev_cli.core.types import (
    MessageRole,
    ErrorCategory,
    WorkflowState,
    is_message,
    is_message_list,
    is_file_path,
)

from qwen_dev_cli.core.errors import (
    QwenError,
    ErrorContext,
    SyntaxError,
    ImportError,
    TypeError,
    FileNotFoundError,
    PermissionError,
    NetworkError,
    TimeoutError,
    RateLimitError,
    TokenLimitError,
    ValidationError as ErrorValidationError,
    LLMError,
    LLMValidationError,
    ToolError,
)

from qwen_dev_cli.core.validation import (
    ValidationResultImpl,
    Required,
    TypeCheck,
    Range,
    Pattern,
    Length,
    OneOf,
    And,
    Or,
    Optional as OptionalValidator,
    Custom,
    validate_message,
    validate_message_list,
    validate_tool_definition,
)


# ============================================================================
# TYPE TESTS
# ============================================================================

class TestTypes:
    """Test type definitions and guards."""
    
    def test_message_role_enum(self):
        """Test MessageRole enum."""
        assert MessageRole.SYSTEM == "system"
        assert MessageRole.USER == "user"
        assert MessageRole.ASSISTANT == "assistant"
        assert MessageRole.TOOL == "tool"
    
    def test_error_category_enum(self):
        """Test ErrorCategory enum."""
        assert ErrorCategory.SYNTAX == "syntax"
        assert ErrorCategory.RUNTIME == "runtime"
        assert ErrorCategory.NETWORK == "network"
    
    def test_workflow_state_enum(self):
        """Test WorkflowState enum."""
        assert WorkflowState.PENDING == "pending"
        assert WorkflowState.RUNNING == "running"
        assert WorkflowState.SUCCESS == "success"
        assert WorkflowState.FAILED == "failed"
    
    def test_is_message_valid(self):
        """Test is_message with valid message."""
        msg = {"role": "user", "content": "Hello"}
        assert is_message(msg)
    
    def test_is_message_invalid(self):
        """Test is_message with invalid messages."""
        assert not is_message({})
        assert not is_message({"role": "user"})  # Missing content
        assert not is_message({"content": "test"})  # Missing role
        assert not is_message("not a dict")
        assert not is_message(None)
    
    def test_is_message_list_valid(self):
        """Test is_message_list with valid list."""
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there"}
        ]
        assert is_message_list(messages)
    
    def test_is_message_list_invalid(self):
        """Test is_message_list with invalid lists."""
        assert not is_message_list([{"role": "user"}])  # Invalid message
        assert not is_message_list("not a list")
        assert not is_message_list([1, 2, 3])
    
    def test_is_file_path(self):
        """Test is_file_path guard."""
        assert is_file_path("/path/to/file")
        assert is_file_path(Path("/path/to/file"))
        assert not is_file_path(123)
        assert not is_file_path(None)


# ============================================================================
# ERROR TESTS
# ============================================================================

class TestErrors:
    """Test error hierarchy."""
    
    def test_error_context_immutable(self):
        """Test ErrorContext is immutable."""
        context = ErrorContext(category=ErrorCategory.SYNTAX, file="test.py")
        with pytest.raises(Exception):  # Should raise FrozenInstanceError
            context.file = "other.py"  # type: ignore
    
    def test_qwen_error_basic(self):
        """Test basic QwenError creation."""
        error = QwenError("Something went wrong")
        assert error.message == "Something went wrong"
        assert error.context is None
        assert not error.recoverable
    
    def test_qwen_error_with_context(self):
        """Test QwenError with context."""
        context = ErrorContext(
            category=ErrorCategory.SYNTAX,
            file="test.py",
            line=10,
            suggestions=("Fix syntax", "Check indentation")
        )
        error = QwenError("Syntax issue", context=context, recoverable=True)
        assert error.context == context
        assert error.recoverable
    
    def test_qwen_error_serialization(self):
        """Test error serialization to dict."""
        context = ErrorContext(category=ErrorCategory.RUNTIME, file="script.py")
        error = QwenError("Runtime error", context=context)
        data = error.to_dict()
        
        assert data['type'] == 'QwenError'
        assert data['message'] == 'Runtime error'
        assert 'context' in data
        assert data['context']['category'] == 'runtime'
    
    def test_syntax_error(self):
        """Test SyntaxError."""
        error = SyntaxError(
            "Missing colon",
            file="test.py",
            line=10,
            column=5,
            code_snippet="if x == 5\n    print('hi')"
        )
        assert error.recoverable
        assert error.context is not None
        assert error.context.category == ErrorCategory.SYNTAX
        assert len(error.context.suggestions) > 0
    
    def test_import_error(self):
        """Test ImportError."""
        error = ImportError("Module not found", module_name="numpy", file="script.py")
        assert error.recoverable
        assert error.context is not None
        assert error.context.metadata['module'] == 'numpy'
        assert any('pip install' in s for s in error.context.suggestions)
    
    def test_type_error(self):
        """Test TypeError."""
        error = TypeError(
            "Type mismatch",
            expected_type="str",
            actual_type="int",
            file="test.py",
            line=5
        )
        assert error.recoverable
        assert error.context is not None
        assert error.context.metadata['expected'] == 'str'
        assert error.context.metadata['actual'] == 'int'
    
    def test_file_not_found_error(self):
        """Test FileNotFoundError."""
        error = FileNotFoundError("/path/to/missing")
        assert not error.recoverable
        assert error.context is not None
        assert "missing" in str(error.context.file)
    
    def test_permission_error(self):
        """Test PermissionError."""
        error = PermissionError("/protected/file", "write")
        assert not error.recoverable
        assert error.context is not None
        assert error.context.metadata['operation'] == 'write'
    
    def test_network_error(self):
        """Test NetworkError."""
        error = NetworkError(
            "Connection failed",
            url="https://api.example.com",
            status_code=500
        )
        assert error.recoverable
        assert error.context is not None
        assert error.context.metadata['url'] == 'https://api.example.com'
        assert error.context.metadata['status_code'] == 500
    
    def test_timeout_error(self):
        """Test TimeoutError."""
        error = TimeoutError("Operation timed out", timeout_seconds=30.0, operation="API call")
        assert error.recoverable
        assert error.context is not None
        assert error.context.metadata['timeout'] == 30.0
    
    def test_rate_limit_error(self):
        """Test RateLimitError."""
        error = RateLimitError(provider="OpenAI", retry_after=60)
        assert error.recoverable
        assert "60 seconds" in error.message
    
    def test_token_limit_error(self):
        """Test TokenLimitError."""
        error = TokenLimitError(current_tokens=5000, max_tokens=4096)
        assert error.recoverable
        assert error.context is not None
        assert error.context.metadata['current'] == 5000
        assert error.context.metadata['limit'] == 4096
    
    def test_llm_error(self):
        """Test LLMError."""
        error = LLMError("API failed", provider="OpenAI", model="gpt-4")
        assert error.recoverable
        assert error.context is not None
        assert error.context.metadata['provider'] == 'OpenAI'
        assert error.context.metadata['model'] == 'gpt-4'
    
    def test_llm_validation_error(self):
        """Test LLMValidationError."""
        error = LLMValidationError("No backend available")
        assert error.recoverable
        assert any('HF_TOKEN' in s for s in error.context.suggestions)
    
    def test_tool_error(self):
        """Test ToolError."""
        error = ToolError(
            "Tool execution failed",
            tool_name="read_file",
            arguments={"path": "/test"}
        )
        assert error.recoverable
        assert error.context is not None
        assert error.context.metadata['tool'] == 'read_file'


# ============================================================================
# VALIDATION TESTS
# ============================================================================

class TestValidation:
    """Test validation system."""
    
    def test_validation_result_success(self):
        """Test successful validation result."""
        result = ValidationResultImpl.success()
        assert result.valid
        assert len(result.errors) == 0
    
    def test_validation_result_failure(self):
        """Test failed validation result."""
        result = ValidationResultImpl.failure(["Error 1", "Error 2"])
        assert not result.valid
        assert len(result.errors) == 2
    
    def test_validation_result_merge(self):
        """Test merging validation results."""
        r1 = ValidationResultImpl.success(warnings=["Warning 1"])
        r2 = ValidationResultImpl.failure(["Error 1"])
        
        merged = r1.merge(r2)
        assert not merged.valid
        assert len(merged.errors) == 1
        assert len(merged.warnings) == 1
    
    def test_required_validator(self):
        """Test Required validator."""
        validator = Required("username")
        
        assert validator.validate("test").valid
        assert not validator.validate(None).valid
        assert not validator.validate("").valid
    
    def test_type_check_validator(self):
        """Test TypeCheck validator."""
        validator = TypeCheck(str, "name")
        
        assert validator.validate("hello").valid
        assert not validator.validate(123).valid
        assert not validator.validate(None).valid
    
    def test_range_validator(self):
        """Test Range validator."""
        validator = Range(min_value=0, max_value=100, field_name="score")
        
        assert validator.validate(50).valid
        assert validator.validate(0).valid
        assert validator.validate(100).valid
        assert not validator.validate(-1).valid
        assert not validator.validate(101).valid
    
    def test_pattern_validator(self):
        """Test Pattern validator."""
        validator = Pattern(r'^[a-z]+$', "username", "lowercase letters")
        
        assert validator.validate("hello").valid
        assert not validator.validate("Hello123").valid
        assert not validator.validate("").valid
    
    def test_length_validator(self):
        """Test Length validator."""
        validator = Length(min_length=3, max_length=10, field_name="password")
        
        assert validator.validate("12345").valid
        assert validator.validate("123").valid
        assert validator.validate("1234567890").valid
        assert not validator.validate("12").valid
        assert not validator.validate("12345678901").valid
    
    def test_one_of_validator(self):
        """Test OneOf validator."""
        validator = OneOf(["admin", "user", "guest"], "role")
        
        assert validator.validate("admin").valid
        assert validator.validate("user").valid
        assert not validator.validate("superuser").valid
    
    def test_and_validator(self):
        """Test And (composite) validator."""
        validator = And(
            Required("field"),
            TypeCheck(str, "field"),
            Length(min_length=3, field_name="field")
        )
        
        assert validator.validate("hello").valid
        assert not validator.validate("ab").valid
        assert not validator.validate(None).valid
    
    def test_or_validator(self):
        """Test Or (composite) validator."""
        validator = Or(
            TypeCheck(str, "value"),
            TypeCheck(int, "value")
        )
        
        assert validator.validate("hello").valid
        assert validator.validate(123).valid
        assert not validator.validate([]).valid
    
    def test_optional_validator(self):
        """Test Optional validator."""
        validator = OptionalValidator(TypeCheck(str, "name"))
        
        assert validator.validate(None).valid
        assert validator.validate("hello").valid
        assert not validator.validate(123).valid
    
    def test_custom_validator(self):
        """Test Custom validator."""
        validator = Custom(
            func=lambda x: x > 0,
            error_message="Value must be positive"
        )
        
        assert validator.validate(5).valid
        assert not validator.validate(0).valid
        assert not validator.validate(-1).valid
    
    def test_validate_message_valid(self):
        """Test validate_message with valid message."""
        msg = {"role": "user", "content": "Hello"}
        result = validate_message(msg)
        assert result.valid
    
    def test_validate_message_invalid_role(self):
        """Test validate_message with invalid role."""
        msg = {"role": "invalid", "content": "Hello"}
        result = validate_message(msg)
        assert not result.valid
        assert any("Invalid role" in err for err in result.errors)
    
    def test_validate_message_missing_content(self):
        """Test validate_message with missing content."""
        msg = {"role": "user"}
        result = validate_message(msg)
        assert not result.valid
        assert any("content" in err for err in result.errors)
    
    def test_validate_message_list_valid(self):
        """Test validate_message_list with valid list."""
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi"}
        ]
        result = validate_message_list(messages)
        assert result.valid
    
    def test_validate_message_list_empty(self):
        """Test validate_message_list with empty list."""
        result = validate_message_list([])
        assert not result.valid
        assert any("empty" in err for err in result.errors)
    
    def test_validate_message_list_invalid_message(self):
        """Test validate_message_list with invalid message."""
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "invalid"}  # Invalid
        ]
        result = validate_message_list(messages)
        assert not result.valid
    
    def test_validate_tool_definition_valid(self):
        """Test validate_tool_definition with valid tool."""
        tool = {
            "name": "read_file",
            "description": "Read a file",
            "parameters": {"path": {"type": "string"}}
        }
        result = validate_tool_definition(tool)
        assert result.valid
    
    def test_validate_tool_definition_missing_fields(self):
        """Test validate_tool_definition with missing fields."""
        tool = {"name": "test"}  # Missing description and parameters
        result = validate_tool_definition(tool)
        assert not result.valid
        assert len(result.errors) >= 2


# ============================================================================
# FILE SYSTEM VALIDATION TESTS
# ============================================================================

class TestFileSystemValidation:
    """Test file system validators."""
    
    def test_path_exists_valid(self):
        """Test PathExists with existing path."""
        with tempfile.NamedTemporaryFile() as tmp:
            from qwen_dev_cli.core.validation import PathExists
            validator = PathExists()
            result = validator.validate(tmp.name)
            assert result.valid
    
    def test_path_exists_invalid(self):
        """Test PathExists with non-existent path."""
        from qwen_dev_cli.core.validation import PathExists
        validator = PathExists()
        result = validator.validate("/this/path/does/not/exist")
        assert not result.valid
    
    def test_file_exists_valid(self):
        """Test FileExists with existing file."""
        with tempfile.NamedTemporaryFile() as tmp:
            from qwen_dev_cli.core.validation import FileExists
            validator = FileExists()
            result = validator.validate(tmp.name)
            assert result.valid
    
    def test_file_exists_directory(self):
        """Test FileExists with directory (should fail)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            from qwen_dev_cli.core.validation import FileExists
            validator = FileExists()
            result = validator.validate(tmpdir)
            assert not result.valid
            assert any("not a file" in err for err in result.errors)
    
    def test_directory_exists_valid(self):
        """Test DirectoryExists with existing directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            from qwen_dev_cli.core.validation import DirectoryExists
            validator = DirectoryExists()
            result = validator.validate(tmpdir)
            assert result.valid
    
    def test_readable_file_valid(self):
        """Test ReadableFile with readable file."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as tmp:
            tmp.write("test content")
            tmp.flush()
            
            try:
                from qwen_dev_cli.core.validation import ReadableFile
                validator = ReadableFile()
                result = validator.validate(tmp.name)
                assert result.valid
            finally:
                os.unlink(tmp.name)


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

class TestIntegration:
    """Test integration between types, errors, and validation."""
    
    def test_error_with_validation_context(self):
        """Test creating error from validation failure."""
        validator = And(
            Required("username"),
            Length(min_length=3, field_name="username")
        )
        result = validator.validate("ab")
        
        assert not result.valid
        
        # Create error from validation result
        error = ErrorValidationError(
            result.errors[0],
            field="username",
            value="ab"
        )
        assert error.recoverable
    
    def test_workflow_with_errors(self):
        """Test workflow state transitions with errors."""
        # Simulate workflow execution
        state = WorkflowState.PENDING
        assert state == WorkflowState.PENDING
        
        # Simulate error
        error = TimeoutError("Step timed out", timeout_seconds=30.0, operation="step1")
        assert error.recoverable
        
        # Would transition to FAILED state
        state = WorkflowState.FAILED
        assert state == WorkflowState.FAILED


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
