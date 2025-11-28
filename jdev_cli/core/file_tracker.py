"""
MAESTRO v10.0 - File Operation Tracker

Automatic tracking of file operations for real-time UI visualization.
Integrates with agents to capture read/write/analyze operations.
"""

import asyncio
from typing import Optional, Callable, Dict, Any
from pathlib import Path
import time


class FileOperationTracker:
    """
    Track file operations for real-time UI visualization.

    Monitors:
    - File reads (analyzing)
    - File writes (modified)
    - File saves (saved)
    - File creates (creating)
    - Diffs (lines added/removed)

    Usage:
        tracker = FileOperationTracker()

        # Register UI callback
        tracker.set_callback(ui.add_file_operation)

        # Track operations
        await tracker.track_read("src/agent.py")
        await tracker.track_write("src/agent.py", lines_added=127, lines_removed=43)
        await tracker.track_save("src/agent.py")
    """

    def __init__(self):
        """Initialize file operation tracker"""
        self.callback: Optional[Callable] = None
        self.operations: Dict[str, Dict[str, Any]] = {}
        self.diff_cache: Dict[str, tuple] = {}  # path -> (lines_added, lines_removed)

    def set_callback(self, callback: Callable):
        """
        Set callback for file operation events.

        Args:
            callback: Function to call with (path, status, lines_added, lines_removed)
        """
        self.callback = callback

    async def track_read(self, path: str | Path):
        """
        Track file read operation.

        Args:
            path: File path
        """
        path_str = str(path)

        # Store operation
        self.operations[path_str] = {
            "status": "analyzing",
            "timestamp": time.time()
        }

        # Emit event
        if self.callback:
            self.callback(path_str, "analyzing", 0, 0)

        # Small delay for visual feedback
        await asyncio.sleep(0.05)

    async def track_write(
        self,
        path: str | Path,
        lines_added: int = 0,
        lines_removed: int = 0
    ):
        """
        Track file write operation.

        Args:
            path: File path
            lines_added: Number of lines added
            lines_removed: Number of lines removed
        """
        path_str = str(path)

        # Cache diff info
        self.diff_cache[path_str] = (lines_added, lines_removed)

        # Store operation
        self.operations[path_str] = {
            "status": "modified",
            "lines_added": lines_added,
            "lines_removed": lines_removed,
            "timestamp": time.time()
        }

        # Emit event
        if self.callback:
            self.callback(path_str, "modified", lines_added, lines_removed)

        # Small delay for visual feedback
        await asyncio.sleep(0.05)

    async def track_save(self, path: str | Path):
        """
        Track file save operation.

        Args:
            path: File path
        """
        path_str = str(path)

        # Get cached diff if available
        lines_added, lines_removed = self.diff_cache.get(path_str, (0, 0))

        # Store operation
        self.operations[path_str] = {
            "status": "saved",
            "lines_added": lines_added,
            "lines_removed": lines_removed,
            "timestamp": time.time()
        }

        # Emit event
        if self.callback:
            self.callback(path_str, "saved", lines_added, lines_removed)

        # Clear cache after save
        self.diff_cache.pop(path_str, None)

        # Small delay for visual feedback
        await asyncio.sleep(0.05)

    async def track_create(self, path: str | Path):
        """
        Track file creation operation.

        Args:
            path: File path
        """
        path_str = str(path)

        # Store operation
        self.operations[path_str] = {
            "status": "creating",
            "timestamp": time.time()
        }

        # Emit event
        if self.callback:
            self.callback(path_str, "creating", 0, 0)

        # Small delay for visual feedback
        await asyncio.sleep(0.05)

    async def track_error(self, path: str | Path, error: str):
        """
        Track file operation error.

        Args:
            path: File path
            error: Error message
        """
        path_str = str(path)

        # Store operation
        self.operations[path_str] = {
            "status": "error",
            "error": error,
            "timestamp": time.time()
        }

        # Emit event
        if self.callback:
            self.callback(path_str, "error", 0, 0)

        # Small delay for visual feedback
        await asyncio.sleep(0.05)

    def calculate_diff(self, old_content: str, new_content: str) -> tuple[int, int]:
        """
        Calculate diff between old and new content.

        Args:
            old_content: Original file content
            new_content: New file content

        Returns:
            Tuple of (lines_added, lines_removed)
        """
        old_lines = old_content.splitlines()
        new_lines = new_content.splitlines()

        # Simple diff: count line changes
        old_set = set(old_lines)
        new_set = set(new_lines)

        lines_added = len(new_set - old_set)
        lines_removed = len(old_set - new_set)

        return (lines_added, lines_removed)

    async def track_edit(
        self,
        path: str | Path,
        old_content: str,
        new_content: str
    ):
        """
        Track file edit with automatic diff calculation.

        Args:
            path: File path
            old_content: Original content
            new_content: New content
        """
        # Calculate diff
        lines_added, lines_removed = self.calculate_diff(old_content, new_content)

        # Track as write
        await self.track_write(path, lines_added, lines_removed)

    def clear(self):
        """Clear all tracked operations"""
        self.operations.clear()
        self.diff_cache.clear()

    def get_operation_status(self, path: str | Path) -> Optional[str]:
        """
        Get current status of file.

        Args:
            path: File path

        Returns:
            Status string or None if not tracked
        """
        path_str = str(path)
        op = self.operations.get(path_str)
        return op["status"] if op else None


# ============================================================================
# SINGLETON INSTANCE (optional, for convenience)
# ============================================================================

_global_tracker: Optional[FileOperationTracker] = None


def get_global_tracker() -> FileOperationTracker:
    """
    Get global file operation tracker instance.

    Returns:
        Global FileOperationTracker
    """
    global _global_tracker
    if _global_tracker is None:
        _global_tracker = FileOperationTracker()
    return _global_tracker


def set_global_callback(callback: Callable):
    """
    Set callback for global tracker.

    Args:
        callback: Callback function
    """
    tracker = get_global_tracker()
    tracker.set_callback(callback)


# ============================================================================
# CONTEXT MANAGER FOR AUTOMATIC TRACKING
# ============================================================================

class TrackedFileOperation:
    """
    Context manager for automatic file operation tracking.

    Usage:
        async with TrackedFileOperation(tracker, "src/agent.py", "read"):
            content = read_file("src/agent.py")
    """

    def __init__(
        self,
        tracker: FileOperationTracker,
        path: str | Path,
        operation: str
    ):
        """
        Initialize tracked operation.

        Args:
            tracker: FileOperationTracker instance
            path: File path
            operation: Operation type ("read", "write", "create", "save")
        """
        self.tracker = tracker
        self.path = path
        self.operation = operation
        self.old_content: Optional[str] = None

    async def __aenter__(self):
        """Enter context: track operation start"""
        if self.operation == "read":
            await self.tracker.track_read(self.path)
        elif self.operation == "create":
            await self.tracker.track_create(self.path)

        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit context: track operation completion"""
        if exc_type is not None:
            # Error occurred
            await self.tracker.track_error(self.path, str(exc_val))
            return False

        # Success
        if self.operation in ["write", "save"]:
            await self.tracker.track_save(self.path)

        return True

    def set_content(self, old_content: str, new_content: str):
        """
        Set content for diff calculation.

        Args:
            old_content: Original content
            new_content: New content
        """
        self.old_content = old_content

        # Calculate and cache diff
        lines_added, lines_removed = self.tracker.calculate_diff(
            old_content,
            new_content
        )
        self.tracker.diff_cache[str(self.path)] = (lines_added, lines_removed)
