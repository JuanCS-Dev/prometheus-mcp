"""Hook events enumeration and definitions."""

from enum import Enum
from typing import List


class HookEvent(str, Enum):
    """Enumeration of hook events that can trigger automation.
    
    Hook events are fired at specific points in the tool execution lifecycle,
    allowing for post-action automation (formatting, testing, etc).
    """

    POST_WRITE = "post_write"
    POST_EDIT = "post_edit"
    POST_DELETE = "post_delete"
    PRE_COMMIT = "pre_commit"

    @classmethod
    def file_operations(cls) -> List['HookEvent']:
        """Get all file operation events (write, edit, delete)."""
        return [cls.POST_WRITE, cls.POST_EDIT, cls.POST_DELETE]

    @classmethod
    def git_operations(cls) -> List['HookEvent']:
        """Get all git operation events."""
        return [cls.PRE_COMMIT]

    def __str__(self) -> str:
        """String representation for logging."""
        return self.value


class HookPriority(int, Enum):
    """Hook execution priority levels.
    
    Higher priority hooks execute first. Used for ordering when
    multiple hooks are defined for the same event.
    """

    CRITICAL = 1000  # Must run first (security checks, validation)
    HIGH = 500       # Important (formatters, linters)
    NORMAL = 100     # Standard (tests, documentation)
    LOW = 10         # Optional (notifications, logging)

    def __lt__(self, other) -> bool:
        """Compare priorities (higher value = higher priority)."""
        if isinstance(other, HookPriority):
            return self.value < other.value
        return NotImplemented
