"""
Input validation and sanitization for qwen-dev-cli.

Boris Cherny philosophy: "Validate early, fail fast, provide clear feedback."

Design principles:
- Explicit validation rules
- Composable validators
- Rich error messages
- Type-safe validation results
- Zero runtime overhead for valid inputs
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, TypeVar, Union
from pathlib import Path
import re
from dataclasses import dataclass



T = TypeVar('T')


# ============================================================================
# VALIDATION RESULT
# ============================================================================

@dataclass
class ValidationResultImpl:
    """Implementation of ValidationResult protocol."""
    valid: bool
    errors: List[str]
    warnings: List[str]

    @classmethod
    def success(cls, warnings: Optional[List[str]] = None) -> ValidationResultImpl:
        """Create a successful validation result."""
        return cls(valid=True, errors=[], warnings=warnings or [])

    @classmethod
    def failure(cls, errors: List[str], warnings: Optional[List[str]] = None) -> ValidationResultImpl:
        """Create a failed validation result."""
        return cls(valid=False, errors=errors, warnings=warnings or [])

    def add_error(self, error: str) -> None:
        """Add an error to the result."""
        self.errors.append(error)
        self.valid = False

    def add_warning(self, warning: str) -> None:
        """Add a warning to the result."""
        self.warnings.append(warning)

    def merge(self, other: ValidationResultImpl) -> ValidationResultImpl:
        """Merge with another validation result."""
        return ValidationResultImpl(
            valid=self.valid and other.valid,
            errors=self.errors + other.errors,
            warnings=self.warnings + other.warnings,
        )


# ============================================================================
# VALIDATOR BASE CLASS
# ============================================================================

class Validator:
    """Base class for validators."""

    def validate(self, value: Any) -> ValidationResultImpl:
        """Validate a value. Must be overridden by subclasses."""
        raise NotImplementedError(f"{self.__class__.__name__}.validate() not implemented")

    def __call__(self, value: Any) -> ValidationResultImpl:
        """Allow validator to be called directly."""
        return self.validate(value)


# ============================================================================
# BASIC VALIDATORS
# ============================================================================

class Required(Validator):
    """Validate that a value is present."""

    def __init__(self, field_name: str):
        self.field_name = field_name

    def validate(self, value: Any) -> ValidationResultImpl:
        if value is None or value == "":
            return ValidationResultImpl.failure([f"{self.field_name} is required"])
        return ValidationResultImpl.success()


class TypeCheck(Validator):
    """Validate that a value is of a specific type."""

    def __init__(self, expected_type: type, field_name: str):
        self.expected_type = expected_type
        self.field_name = field_name

    def validate(self, value: Any) -> ValidationResultImpl:
        if not isinstance(value, self.expected_type):
            actual_type = type(value).__name__
            expected_name = self.expected_type.__name__
            return ValidationResultImpl.failure([
                f"{self.field_name} must be {expected_name}, got {actual_type}"
            ])
        return ValidationResultImpl.success()


class Range(Validator):
    """Validate that a numeric value is within a range."""

    def __init__(
        self,
        min_value: Optional[Union[int, float]] = None,
        max_value: Optional[Union[int, float]] = None,
        field_name: str = "value",
    ):
        self.min_value = min_value
        self.max_value = max_value
        self.field_name = field_name

    def validate(self, value: Any) -> ValidationResultImpl:
        if not isinstance(value, (int, float)):
            return ValidationResultImpl.failure([f"{self.field_name} must be a number"])

        if self.min_value is not None and value < self.min_value:
            return ValidationResultImpl.failure([
                f"{self.field_name} must be >= {self.min_value}, got {value}"
            ])

        if self.max_value is not None and value > self.max_value:
            return ValidationResultImpl.failure([
                f"{self.field_name} must be <= {self.max_value}, got {value}"
            ])

        return ValidationResultImpl.success()


class Pattern(Validator):
    """Validate that a string matches a regex pattern."""

    def __init__(self, pattern: str, field_name: str, description: str = "pattern"):
        self.pattern = re.compile(pattern)
        self.field_name = field_name
        self.description = description

    def validate(self, value: Any) -> ValidationResultImpl:
        if not isinstance(value, str):
            return ValidationResultImpl.failure([f"{self.field_name} must be a string"])

        if not self.pattern.match(value):
            return ValidationResultImpl.failure([
                f"{self.field_name} does not match {self.description}"
            ])

        return ValidationResultImpl.success()


class Length(Validator):
    """Validate string or list length."""

    def __init__(
        self,
        min_length: Optional[int] = None,
        max_length: Optional[int] = None,
        field_name: str = "value",
    ):
        self.min_length = min_length
        self.max_length = max_length
        self.field_name = field_name

    def validate(self, value: Any) -> ValidationResultImpl:
        if not hasattr(value, '__len__'):
            return ValidationResultImpl.failure([f"{self.field_name} must have a length"])

        length = len(value)

        if self.min_length is not None and length < self.min_length:
            return ValidationResultImpl.failure([
                f"{self.field_name} must have at least {self.min_length} items, got {length}"
            ])

        if self.max_length is not None and length > self.max_length:
            return ValidationResultImpl.failure([
                f"{self.field_name} must have at most {self.max_length} items, got {length}"
            ])

        return ValidationResultImpl.success()


class OneOf(Validator):
    """Validate that a value is one of allowed values."""

    def __init__(self, allowed: List[Any], field_name: str):
        self.allowed = allowed
        self.field_name = field_name

    def validate(self, value: Any) -> ValidationResultImpl:
        if value not in self.allowed:
            allowed_str = ', '.join(str(v) for v in self.allowed)
            return ValidationResultImpl.failure([
                f"{self.field_name} must be one of: {allowed_str}, got {value}"
            ])
        return ValidationResultImpl.success()


# ============================================================================
# FILE SYSTEM VALIDATORS
# ============================================================================

class PathExists(Validator):
    """Validate that a path exists."""

    def __init__(self, field_name: str = "path"):
        self.field_name = field_name

    def validate(self, value: Any) -> ValidationResultImpl:
        try:
            path = Path(value)
            if not path.exists():
                return ValidationResultImpl.failure([f"{self.field_name} does not exist: {value}"])
            return ValidationResultImpl.success()
        except (TypeError, ValueError) as e:
            return ValidationResultImpl.failure([f"Invalid path: {e}"])


class FileExists(Validator):
    """Validate that a file exists and is a file."""

    def __init__(self, field_name: str = "file"):
        self.field_name = field_name

    def validate(self, value: Any) -> ValidationResultImpl:
        try:
            path = Path(value)
            if not path.exists():
                return ValidationResultImpl.failure([f"{self.field_name} does not exist: {value}"])
            if not path.is_file():
                return ValidationResultImpl.failure([f"{self.field_name} is not a file: {value}"])
            return ValidationResultImpl.success()
        except (TypeError, ValueError) as e:
            return ValidationResultImpl.failure([f"Invalid file path: {e}"])


class DirectoryExists(Validator):
    """Validate that a directory exists."""

    def __init__(self, field_name: str = "directory"):
        self.field_name = field_name

    def validate(self, value: Any) -> ValidationResultImpl:
        try:
            path = Path(value)
            if not path.exists():
                return ValidationResultImpl.failure([f"{self.field_name} does not exist: {value}"])
            if not path.is_dir():
                return ValidationResultImpl.failure([f"{self.field_name} is not a directory: {value}"])
            return ValidationResultImpl.success()
        except (TypeError, ValueError) as e:
            return ValidationResultImpl.failure([f"Invalid directory path: {e}"])


class ReadableFile(Validator):
    """Validate that a file is readable."""

    def __init__(self, field_name: str = "file"):
        self.field_name = field_name

    def validate(self, value: Any) -> ValidationResultImpl:
        result = FileExists(self.field_name).validate(value)
        if not result.valid:
            return result

        try:
            path = Path(value)
            with open(path, 'r') as f:
                f.read(1)  # Try to read 1 byte
            return ValidationResultImpl.success()
        except PermissionError:
            return ValidationResultImpl.failure([f"{self.field_name} is not readable: {value}"])
        except Exception as e:
            return ValidationResultImpl.failure([f"Cannot read {self.field_name}: {e}"])


# ============================================================================
# COMPOSITE VALIDATORS
# ============================================================================

class And(Validator):
    """Combine multiple validators with AND logic."""

    def __init__(self, *validators: Validator):
        self.validators = validators

    def validate(self, value: Any) -> ValidationResultImpl:
        result = ValidationResultImpl.success()
        for validator in self.validators:
            result = result.merge(validator.validate(value))
            if not result.valid:
                break  # Short-circuit on first failure
        return result


class Or(Validator):
    """Combine multiple validators with OR logic."""

    def __init__(self, *validators: Validator):
        self.validators = validators

    def validate(self, value: Any) -> ValidationResultImpl:
        all_errors: List[str] = []

        for validator in self.validators:
            result = validator.validate(value)
            if result.valid:
                return result  # Short-circuit on first success
            all_errors.extend(result.errors)

        return ValidationResultImpl.failure(all_errors)


class Optional(Validator):
    """Make a validator optional (None is valid)."""

    def __init__(self, validator: Validator):
        self.validator = validator

    def validate(self, value: Any) -> ValidationResultImpl:
        if value is None:
            return ValidationResultImpl.success()
        return self.validator.validate(value)


# ============================================================================
# CUSTOM VALIDATOR
# ============================================================================

class Custom(Validator):
    """Custom validator using a function."""

    def __init__(
        self,
        func: Callable[[Any], bool],
        error_message: str,
    ):
        self.func = func
        self.error_message = error_message

    def validate(self, value: Any) -> ValidationResultImpl:
        try:
            if self.func(value):
                return ValidationResultImpl.success()
            return ValidationResultImpl.failure([self.error_message])
        except Exception as e:
            return ValidationResultImpl.failure([f"Validation error: {e}"])


# ============================================================================
# HIGH-LEVEL VALIDATION FUNCTIONS
# ============================================================================

def validate_message(message: Dict[str, Any]) -> ValidationResultImpl:
    """Validate a message structure."""
    result = ValidationResultImpl.success()

    # Check required fields
    if 'role' not in message:
        result.add_error("Message missing 'role' field")
    elif message['role'] not in ['system', 'user', 'assistant', 'tool']:
        result.add_error(f"Invalid role: {message['role']}")

    if 'content' not in message:
        result.add_error("Message missing 'content' field")
    elif not isinstance(message['content'], str):
        result.add_error("Message content must be a string")

    return result


def validate_message_list(messages: List[Any]) -> ValidationResultImpl:
    """Validate a list of messages."""
    if not isinstance(messages, list):
        return ValidationResultImpl.failure(["messages must be a list"])

    if len(messages) == 0:
        return ValidationResultImpl.failure(["messages list cannot be empty"])

    result = ValidationResultImpl.success()
    for i, msg in enumerate(messages):
        if not isinstance(msg, dict):
            result.add_error(f"Message {i} must be a dictionary")
            continue

        msg_result = validate_message(msg)
        if not msg_result.valid:
            for error in msg_result.errors:
                result.add_error(f"Message {i}: {error}")

    return result


def validate_tool_definition(tool: Dict[str, Any]) -> ValidationResultImpl:
    """Validate a tool definition."""
    result = ValidationResultImpl.success()

    if 'name' not in tool:
        result.add_error("Tool missing 'name' field")
    elif not isinstance(tool['name'], str):
        result.add_error("Tool name must be a string")

    if 'description' not in tool:
        result.add_error("Tool missing 'description' field")

    if 'parameters' not in tool:
        result.add_error("Tool missing 'parameters' field")
    elif not isinstance(tool['parameters'], dict):
        result.add_error("Tool parameters must be a dictionary")

    return result


def validate_file_path(path: Any, must_exist: bool = False) -> ValidationResultImpl:
    """Validate a file path."""
    try:
        p = Path(path)

        if must_exist and not p.exists():
            return ValidationResultImpl.failure([f"Path does not exist: {path}"])

        return ValidationResultImpl.success()
    except (TypeError, ValueError) as e:
        return ValidationResultImpl.failure([f"Invalid path: {e}"])


# ============================================================================
# EXPORTS
# ============================================================================

__all__ = [
    # Result
    'ValidationResultImpl',

    # Base
    'Validator',

    # Basic validators
    'Required', 'TypeCheck', 'Range', 'Pattern', 'Length', 'OneOf',

    # File system validators
    'PathExists', 'FileExists', 'DirectoryExists', 'ReadableFile',

    # Composite validators
    'And', 'Or', 'Optional', 'Custom',

    # High-level functions
    'validate_message', 'validate_message_list',
    'validate_tool_definition', 'validate_file_path',
]
