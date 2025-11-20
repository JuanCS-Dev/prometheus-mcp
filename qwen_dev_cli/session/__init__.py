"""Session management and persistence for qwen-dev-cli.

This module provides session state management with:
- Complete conversation history
- Context preservation
- File tracking (read/modified)
- Tool call statistics
- Resume capability
"""

from .manager import SessionManager
from .state import SessionState

__all__ = [
    'SessionManager',
    'SessionState',
]
