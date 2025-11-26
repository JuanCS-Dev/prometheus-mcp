"""
ERROR UTILITIES - Standardized error handling and logging.

This module provides consistent error logging across the codebase.
All error handlers should use these utilities for:
- Consistent message format
- Proper stack trace inclusion
- Type information
- Context preservation

Author: JuanCS Dev
Date: 2025-11-25
"""

import logging
import traceback
from typing import Any, Dict, Optional


def log_error(
    logger: logging.Logger,
    error: Exception,
    context: str = "",
    include_traceback: bool = True,
    **extra: Any
) -> str:
    """
    Log an error with full context and optional traceback.

    Args:
        logger: The logger instance to use
        error: The exception that occurred
        context: Description of what was being attempted
        include_traceback: Whether to include full stack trace
        **extra: Additional context to include in log

    Returns:
        Formatted error message string
    """
    error_type = type(error).__name__
    error_msg = str(error)[:500]  # Truncate very long messages

    # Build context string
    ctx_parts = [context] if context else []
    for key, value in extra.items():
        ctx_parts.append(f"{key}={value}")
    ctx_str = " | ".join(ctx_parts) if ctx_parts else "Unknown context"

    # Format message
    full_msg = f"[ERROR] {ctx_str}: {error_type}: {error_msg}"

    logger.error(full_msg, exc_info=include_traceback)

    return full_msg


def log_warning(
    logger: logging.Logger,
    error: Exception,
    context: str = "",
    **extra: Any
) -> str:
    """
    Log a warning with error context (no traceback).

    Use for recoverable errors or expected failures.
    """
    error_type = type(error).__name__
    error_msg = str(error)[:300]

    ctx_parts = [context] if context else []
    for key, value in extra.items():
        ctx_parts.append(f"{key}={value}")
    ctx_str = " | ".join(ctx_parts) if ctx_parts else "Unknown context"

    full_msg = f"[WARN] {ctx_str}: {error_type}: {error_msg}"

    logger.warning(full_msg)

    return full_msg


def log_retry(
    logger: logging.Logger,
    error: Exception,
    attempt: int,
    max_attempts: int,
    context: str = "",
    **extra: Any
) -> str:
    """
    Log a retry attempt with context.

    Uses WARNING level to ensure visibility in production.
    """
    error_type = type(error).__name__
    error_msg = str(error)[:200]

    full_msg = (
        f"[RETRY {attempt}/{max_attempts}] {context}: "
        f"{error_type}: {error_msg}"
    )

    # Use WARNING for first attempts, ERROR if near max
    if attempt >= max_attempts - 1:
        logger.error(full_msg)
    else:
        logger.warning(full_msg)

    return full_msg


def format_error_for_user(
    error: Exception,
    context: str = "",
    show_type: bool = True
) -> str:
    """
    Format error for user display (no internal details).

    Safe for showing to end users - hides stack traces
    but provides actionable information.
    """
    error_type = type(error).__name__
    error_msg = str(error)

    # Map common errors to user-friendly messages
    user_friendly = {
        "ConnectionError": "Could not connect to the service. Check your internet connection.",
        "TimeoutError": "Request timed out. The service may be slow or unavailable.",
        "AuthenticationError": "Authentication failed. Please check your API key.",
        "RateLimitError": "Rate limit exceeded. Please wait a moment and try again.",
        "FileNotFoundError": f"File not found: {error_msg}",
        "PermissionError": f"Permission denied: {error_msg}",
        "ValidationError": f"Invalid input: {error_msg}",
    }

    # Check for known error types
    for err_type, friendly_msg in user_friendly.items():
        if err_type in error_type:
            if context:
                return f"{context}: {friendly_msg}"
            return friendly_msg

    # Default: show error type and message
    if show_type:
        if context:
            return f"{context}: {error_type} - {error_msg}"
        return f"{error_type}: {error_msg}"
    else:
        if context:
            return f"{context}: {error_msg}"
        return error_msg


def create_error_result(
    error: Exception,
    context: str = "",
    include_type: bool = True
) -> Dict[str, Any]:
    """
    Create a standardized error result dictionary.

    Use for returning errors from tools/agents.
    """
    error_type = type(error).__name__
    error_msg = str(error)

    result = {
        "success": False,
        "error": format_error_for_user(error, context, include_type),
        "error_type": error_type,
    }

    if context:
        result["context"] = context

    return result


def is_retryable_error(error: Exception) -> bool:
    """
    Determine if an error is worth retrying.

    Returns True for transient errors like timeouts, connection issues.
    Returns False for permanent errors like auth failures, validation errors.
    """
    error_type = type(error).__name__
    error_msg = str(error).lower()

    # Non-retryable error types
    non_retryable_types = {
        "AuthenticationError",
        "AuthorizationError",
        "ValidationError",
        "ValueError",
        "TypeError",
        "KeyError",
        "AttributeError",
        "FileNotFoundError",
        "PermissionError",
        "InvalidAPIKeyError",
    }

    # Non-retryable message patterns
    non_retryable_patterns = [
        "invalid api key",
        "authentication failed",
        "unauthorized",
        "forbidden",
        "not found",
        "invalid",
        "malformed",
    ]

    # Check type
    if error_type in non_retryable_types:
        return False

    # Check message patterns
    for pattern in non_retryable_patterns:
        if pattern in error_msg:
            return False

    # Retryable by default (timeouts, connection errors, etc.)
    return True


class ErrorContext:
    """
    Context manager for standardized error handling.

    Usage:
        with ErrorContext(logger, "Processing file", filename=path) as ctx:
            # do work
            if something_wrong:
                ctx.warn("Minor issue detected")
        # Errors are automatically logged with context
    """

    def __init__(
        self,
        logger: logging.Logger,
        context: str,
        reraise: bool = True,
        **extra: Any
    ):
        self.logger = logger
        self.context = context
        self.extra = extra
        self.reraise = reraise
        self._warnings: list = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_val is not None:
            log_error(
                self.logger,
                exc_val,
                self.context,
                **self.extra
            )
            return not self.reraise  # Suppress if reraise=False
        return False

    def warn(self, message: str):
        """Log a warning within this context."""
        self._warnings.append(message)
        self.logger.warning(f"[{self.context}] {message}")
