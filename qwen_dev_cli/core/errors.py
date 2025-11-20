"""
Error hierarchy for qwen-dev-cli.

Following Boris Cherny's philosophy: explicit error types enable
better error handling and recovery. Every error should:
1. Have a clear hierarchy
2. Carry relevant context
3. Be recoverable when possible
4. Provide actionable error messages

Design principles:
- Specific exceptions over generic ones
- Immutable error context
- Rich error information for debugging
- Integration with recovery system
"""

from __future__ import annotations

from typing import Any, Dict, Optional
from pathlib import Path
from dataclasses import dataclass, field

from .types import ErrorCategory, FilePath


# ============================================================================
# BASE EXCEPTION
# ============================================================================

@dataclass(frozen=True)
class ErrorContext:
    """Immutable context for an error."""
    category: ErrorCategory
    file: Optional[FilePath] = None
    line: Optional[int] = None
    column: Optional[int] = None
    code_snippet: Optional[str] = None
    suggestions: tuple[str, ...] = field(default_factory=tuple)
    metadata: Dict[str, Any] = field(default_factory=dict)


class QwenError(Exception):
    """Base exception for all qwen-dev-cli errors.
    
    All custom exceptions should inherit from this base class.
    Provides structured error information and recovery hints.
    """
    
    def __init__(
        self,
        message: str,
        context: Optional[ErrorContext] = None,
        recoverable: bool = False,
        cause: Optional[Exception] = None,
    ):
        super().__init__(message)
        self.message = message
        self.context = context
        self.recoverable = recoverable
        self.cause = cause
    
    def __str__(self) -> str:
        """Human-readable error message."""
        parts = [self.message]
        
        if self.context:
            if self.context.file:
                parts.append(f"File: {self.context.file}")
            if self.context.line:
                location = f"Line: {self.context.line}"
                if self.context.column:
                    location += f", Column: {self.context.column}"
                parts.append(location)
            if self.context.code_snippet:
                parts.append(f"Code:\n{self.context.code_snippet}")
            if self.context.suggestions:
                parts.append("Suggestions:")
                parts.extend(f"  - {s}" for s in self.context.suggestions)
        
        if self.cause:
            parts.append(f"Caused by: {self.cause}")
        
        return "\n".join(parts)
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize error to dictionary."""
        result: Dict[str, Any] = {
            'type': self.__class__.__name__,
            'message': self.message,
            'recoverable': self.recoverable,
        }
        
        if self.context:
            result['context'] = {
                'category': self.context.category.value,
                'file': str(self.context.file) if self.context.file else None,
                'line': self.context.line,
                'column': self.context.column,
                'suggestions': list(self.context.suggestions),
                'metadata': self.context.metadata,
            }
        
        if self.cause:
            result['cause'] = str(self.cause)
        
        return result


# ============================================================================
# CODE EXECUTION ERRORS
# ============================================================================

class SyntaxError(QwenError):
    """Syntax error in Python code."""
    
    def __init__(
        self,
        message: str,
        file: Optional[FilePath] = None,
        line: Optional[int] = None,
        column: Optional[int] = None,
        code_snippet: Optional[str] = None,
    ):
        context = ErrorContext(
            category=ErrorCategory.SYNTAX,
            file=file,
            line=line,
            column=column,
            code_snippet=code_snippet,
            suggestions=(
                "Check for missing colons, parentheses, or quotes",
                "Verify indentation is consistent",
                "Run `python -m py_compile <file>` to validate syntax",
            ),
        )
        super().__init__(message, context, recoverable=True)


class ImportError(QwenError):
    """Module import error."""
    
    def __init__(
        self,
        message: str,
        module_name: str,
        file: Optional[FilePath] = None,
        line: Optional[int] = None,
    ):
        context = ErrorContext(
            category=ErrorCategory.IMPORT,
            file=file,
            line=line,
            metadata={'module': module_name},
            suggestions=(
                f"Install module: `pip install {module_name}`",
                "Check if module name is correct",
                "Verify virtual environment is activated",
            ),
        )
        super().__init__(message, context, recoverable=True)


class TypeError(QwenError):
    """Type error in code execution."""
    
    def __init__(
        self,
        message: str,
        expected_type: str,
        actual_type: str,
        file: Optional[FilePath] = None,
        line: Optional[int] = None,
    ):
        context = ErrorContext(
            category=ErrorCategory.TYPE,
            file=file,
            line=line,
            metadata={
                'expected': expected_type,
                'actual': actual_type,
            },
            suggestions=(
                f"Expected {expected_type}, got {actual_type}",
                "Check function signatures and type annotations",
                "Run `mypy` to catch type errors early",
            ),
        )
        super().__init__(message, context, recoverable=True)


class RuntimeError(QwenError):
    """Runtime error during execution."""
    
    def __init__(
        self,
        message: str,
        file: Optional[FilePath] = None,
        line: Optional[int] = None,
        cause: Optional[Exception] = None,
    ):
        context = ErrorContext(
            category=ErrorCategory.RUNTIME,
            file=file,
            line=line,
        )
        super().__init__(message, context, recoverable=False, cause=cause)


# ============================================================================
# FILE SYSTEM ERRORS
# ============================================================================

class FileNotFoundError(QwenError):
    """File or directory not found."""
    
    def __init__(self, path: FilePath):
        context = ErrorContext(
            category=ErrorCategory.PERMISSION,
            file=path,
            suggestions=(
                f"Check if file exists: `ls -la {path}`",
                "Verify path is correct and accessible",
                "Check file permissions",
            ),
        )
        super().__init__(f"File not found: {path}", context, recoverable=False)


class PermissionError(QwenError):
    """Permission denied for file operation."""
    
    def __init__(self, path: FilePath, operation: str):
        context = ErrorContext(
            category=ErrorCategory.PERMISSION,
            file=path,
            metadata={'operation': operation},
            suggestions=(
                f"Check file permissions: `ls -la {path}`",
                "Run with appropriate permissions",
                "Verify file is not locked by another process",
            ),
        )
        super().__init__(
            f"Permission denied: cannot {operation} {path}",
            context,
            recoverable=False,
        )


class FileAlreadyExistsError(QwenError):
    """File already exists and cannot be overwritten."""
    
    def __init__(self, path: FilePath):
        context = ErrorContext(
            category=ErrorCategory.PERMISSION,
            file=path,
            suggestions=(
                "Use a different filename",
                "Delete existing file if appropriate",
                "Use overwrite=True flag if supported",
            ),
        )
        super().__init__(f"File already exists: {path}", context, recoverable=True)


# ============================================================================
# NETWORK ERRORS
# ============================================================================

class NetworkError(QwenError):
    """Network-related error."""
    
    def __init__(
        self,
        message: str,
        url: Optional[str] = None,
        status_code: Optional[int] = None,
        cause: Optional[Exception] = None,
    ):
        metadata = {}
        if url:
            metadata['url'] = url
        if status_code:
            metadata['status_code'] = status_code
        
        context = ErrorContext(
            category=ErrorCategory.NETWORK,
            metadata=metadata,
            suggestions=(
                "Check network connection",
                "Verify API endpoint is correct",
                "Check if API key is valid",
                "Try again with exponential backoff",
            ),
        )
        super().__init__(message, context, recoverable=True, cause=cause)


class TimeoutError(QwenError):
    """Operation timed out."""
    
    def __init__(
        self,
        message: str,
        timeout_seconds: float,
        operation: str,
    ):
        context = ErrorContext(
            category=ErrorCategory.TIMEOUT,
            metadata={
                'timeout': timeout_seconds,
                'operation': operation,
            },
            suggestions=(
                f"Increase timeout (current: {timeout_seconds}s)",
                "Check if operation is hung",
                "Retry with exponential backoff",
            ),
        )
        super().__init__(message, context, recoverable=True)


class RateLimitError(QwenError):
    """API rate limit exceeded."""
    
    def __init__(
        self,
        provider: str,
        retry_after: Optional[int] = None,
    ):
        message = f"Rate limit exceeded for {provider}"
        if retry_after:
            message += f". Retry after {retry_after} seconds"
        
        metadata: Dict[str, Any] = {
            'provider': provider,
        }
        if retry_after is not None:
            metadata['retry_after'] = retry_after
        
        context = ErrorContext(
            category=ErrorCategory.NETWORK,
            metadata=metadata,
            suggestions=(
                f"Wait {retry_after} seconds before retrying" if retry_after else "Wait before retrying",
                "Reduce request rate",
                "Implement exponential backoff",
            ),
        )
        super().__init__(message, context=context, recoverable=True)


# ============================================================================
# RESOURCE ERRORS
# ============================================================================

class ResourceError(QwenError):
    """Resource constraint error."""
    
    def __init__(
        self,
        message: str,
        resource_type: str,
        limit: Optional[Any] = None,
        current: Optional[Any] = None,
    ):
        metadata = {'resource_type': resource_type}
        if limit is not None:
            metadata['limit'] = limit
        if current is not None:
            metadata['current'] = current
        
        suggestions = [
            f"Reduce {resource_type} usage",
            "Check resource limits and quotas",
        ]
        if limit and current:
            suggestions.insert(0, f"Current: {current}, Limit: {limit}")
        
        context = ErrorContext(
            category=ErrorCategory.RESOURCE,
            metadata=metadata,
            suggestions=tuple(suggestions),
        )
        super().__init__(message, context, recoverable=True)


class TokenLimitError(ResourceError):
    """Token limit exceeded."""
    
    def __init__(
        self,
        current_tokens: int,
        max_tokens: int,
        token_type: str = "context",
    ):
        super().__init__(
            f"{token_type.capitalize()} token limit exceeded: {current_tokens}/{max_tokens}",
            resource_type="tokens",
            limit=max_tokens,
            current=current_tokens,
        )


class MemoryLimitError(ResourceError):
    """Memory limit exceeded."""
    
    def __init__(
        self,
        current_mb: float,
        max_mb: float,
    ):
        super().__init__(
            f"Memory limit exceeded: {current_mb:.1f}MB / {max_mb:.1f}MB",
            resource_type="memory",
            limit=max_mb,
            current=current_mb,
        )


# ============================================================================
# VALIDATION ERRORS
# ============================================================================

class ValidationError(QwenError):
    """Input validation error."""
    
    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        value: Optional[Any] = None,
        constraint: Optional[str] = None,
    ):
        metadata = {}
        if field:
            metadata['field'] = field
        if value is not None:
            metadata['value'] = str(value)
        if constraint:
            metadata['constraint'] = constraint
        
        suggestions = ["Check input format and constraints"]
        if field:
            suggestions.append(f"Field '{field}' is invalid")
        if constraint:
            suggestions.append(f"Constraint: {constraint}")
        
        context = ErrorContext(
            category=ErrorCategory.UNKNOWN,
            metadata=metadata,
            suggestions=tuple(suggestions),
        )
        super().__init__(message, context, recoverable=True)


# ============================================================================
# CONFIGURATION ERRORS
# ============================================================================

class ConfigurationError(QwenError):
    """Configuration error."""
    
    def __init__(
        self,
        message: str,
        config_key: Optional[str] = None,
        config_file: Optional[FilePath] = None,
    ):
        metadata = {}
        if config_key:
            metadata['config_key'] = config_key
        
        suggestions = [
            "Check configuration file syntax",
            "Verify all required fields are set",
            "See documentation for valid configuration options",
        ]
        if config_key:
            suggestions.insert(0, f"Invalid configuration key: {config_key}")
        
        context = ErrorContext(
            category=ErrorCategory.UNKNOWN,
            file=config_file,
            metadata=metadata,
            suggestions=tuple(suggestions),
        )
        super().__init__(message, context, recoverable=True)


# ============================================================================
# LLM ERRORS
# ============================================================================

class LLMError(QwenError):
    """LLM-related error."""
    
    def __init__(
        self,
        message: str,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        cause: Optional[Exception] = None,
    ):
        metadata = {}
        if provider:
            metadata['provider'] = provider
        if model:
            metadata['model'] = model
        
        context = ErrorContext(
            category=ErrorCategory.NETWORK,
            metadata=metadata,
            suggestions=(
                "Check API key is valid",
                "Verify network connection",
                "Try a different provider",
                "Check provider status page",
            ),
        )
        super().__init__(message, context, recoverable=True, cause=cause)


class LLMValidationError(LLMError):
    """LLM backend not available."""
    
    def __init__(self, message: str):
        super().__init__(
            message,
            provider=None,
            model=None,
        )
        # Override suggestions
        if self.context:
            self.context = ErrorContext(
                category=self.context.category,
                metadata=self.context.metadata,
                suggestions=(
                    "Configure at least one LLM backend",
                    "Set HF_TOKEN, GEMINI_API_KEY, or NEBIUS_API_KEY",
                    "Check .env file configuration",
                    "See documentation for setup instructions",
                ),
            )


# ============================================================================
# TOOL ERRORS
# ============================================================================

class ToolError(QwenError):
    """Tool execution error."""
    
    def __init__(
        self,
        message: str,
        tool_name: str,
        arguments: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ):
        metadata = {'tool': tool_name}
        if arguments:
            metadata['arguments'] = arguments
        
        context = ErrorContext(
            category=ErrorCategory.RUNTIME,
            metadata=metadata,
            suggestions=(
                "Check tool arguments are correct",
                f"See documentation for tool '{tool_name}'",
                "Verify tool dependencies are installed",
            ),
        )
        super().__init__(message, context, recoverable=True, cause=cause)


class ToolNotFoundError(ToolError):
    """Tool not found in registry."""
    
    def __init__(self, tool_name: str):
        super().__init__(
            f"Tool not found: {tool_name}",
            tool_name=tool_name,
        )


# ============================================================================
# EXPORTS
# ============================================================================

__all__ = [
    # Base
    'QwenError', 'ErrorContext',
    
    # Code execution
    'SyntaxError', 'ImportError', 'TypeError', 'RuntimeError',
    
    # File system
    'FileNotFoundError', 'PermissionError', 'FileAlreadyExistsError',
    
    # Network
    'NetworkError', 'TimeoutError', 'RateLimitError',
    
    # Resources
    'ResourceError', 'TokenLimitError', 'MemoryLimitError',
    
    # Validation
    'ValidationError', 'ConfigurationError',
    
    # LLM
    'LLMError', 'LLMValidationError',
    
    # Tools
    'ToolError', 'ToolNotFoundError',
]
