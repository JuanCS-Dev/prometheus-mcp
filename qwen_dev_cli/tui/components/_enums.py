"""
TUI Component Enums - Centralized enum definitions.
"""

from enum import Enum


class MessageRole(Enum):
    """Message role types."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class ProgressStyle(Enum):
    """Progress bar styles."""
    BAR = "bar"
    SPINNER = "spinner"
    DOTS = "dots"
    MINIMAL = "minimal"
