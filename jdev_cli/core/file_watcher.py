"""Real-time file system monitoring (Claude pattern).

Boris Cherny: Event-driven, incremental updates only.
"""

import os
import time
import hashlib
from pathlib import Path
from typing import Dict, Set, Optional, Callable
from collections import deque
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class FileEvent:
    """File system event."""

    path: str
    event_type: str  # 'created', 'modified', 'deleted'
    timestamp: float
    file_hash: Optional[str] = None


class FileWatcher:
    """File system watcher with incremental updates (Claude pattern).
    
    Uses polling for simplicity (watchdog adds dependency).
    Updates every 1s, only processes changed files.
    """

    def __init__(
        self,
        root_path: str = ".",
        watch_extensions: Set[str] = None
    ):
        self.root_path = Path(root_path)
        self._watch_extensions = watch_extensions or {'.py', '.js', '.ts', '.go', '.rs'}
        self._file_hashes: Dict[str, str] = {}
        self._recent_events: deque = deque(maxlen=100)
        self._callbacks: list[Callable] = []
        self._running = False

    def add_callback(self, callback: Callable[[FileEvent], None]) -> None:
        """Register callback for file events."""
        self._callbacks.append(callback)

    def start(self):
        """Start watching (sync, for simplicity)."""
        self._running = True
        self._initial_scan()

    def stop(self):
        """Stop watching."""
        self._running = False

    def _initial_scan(self):
        """Initial scan to establish baseline."""
        for file_path in self._get_watched_files():
            file_hash = self._hash_file(file_path)
            self._file_hashes[str(file_path)] = file_hash

    def check_updates(self):
        """Check for file updates (call periodically)."""
        if not self._running:
            return

        current_files = set(str(p) for p in self._get_watched_files())
        tracked_files = set(self._file_hashes.keys())

        # Detect new files
        for file_path in current_files - tracked_files:
            event = FileEvent(
                path=file_path,
                event_type='created',
                timestamp=time.time(),
                file_hash=self._hash_file(file_path)
            )
            self._handle_event(event)
            self._file_hashes[file_path] = event.file_hash

        # Detect deleted files
        for file_path in tracked_files - current_files:
            event = FileEvent(
                path=file_path,
                event_type='deleted',
                timestamp=time.time()
            )
            self._handle_event(event)
            del self._file_hashes[file_path]

        # Detect modified files
        for file_path in current_files & tracked_files:
            new_hash = self._hash_file(file_path)
            if new_hash != self._file_hashes[file_path]:
                event = FileEvent(
                    path=file_path,
                    event_type='modified',
                    timestamp=time.time(),
                    file_hash=new_hash
                )
                self._handle_event(event)
                self._file_hashes[file_path] = new_hash

    def _get_watched_files(self):
        """Get all files to watch."""
        for root, dirs, files in os.walk(self.root_path):
            # Skip hidden dirs and common excludes
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['node_modules', '__pycache__', 'venv']]

            for file in files:
                file_path = Path(root) / file
                if file_path.suffix in self._watch_extensions:
                    yield file_path

    def _hash_file(self, file_path: str) -> str:
        """Fast file hash (first 8KB only for speed)."""
        try:
            with open(file_path, 'rb') as f:
                # Only hash first 8KB for speed
                content = f.read(8192)
                return hashlib.md5(content).hexdigest()
        except (IOError, OSError):
            return ""

    def _handle_event(self, event: FileEvent):
        """Handle file event."""
        self._recent_events.append(event)

        for callback in self._callbacks:
            try:
                callback(event)
            except Exception as e:
                logger.error(f"Callback failed: {e}")

    @property
    def recent_events(self) -> list[FileEvent]:
        """Get recent events (last 100)."""
        return list(self._recent_events)

    @property
    def tracked_files(self) -> int:
        """Get number of tracked files."""
        return len(self._file_hashes)


class RecentFilesTracker:
    """Track recently modified files (Cursor pattern).
    
    LRU cache of recent files with recency scoring.
    """

    def __init__(self, maxsize: int = 50):
        self._files: deque = deque(maxlen=maxsize)
        self._timestamps: Dict[str, float] = {}

    def add(self, file_path: str) -> None:
        """Add file to recent list."""
        # Remove if exists (to update position)
        if file_path in self._files:
            self._files.remove(file_path)

        self._files.append(file_path)
        self._timestamps[file_path] = time.time()

    def get_recent(self, count: int = 10) -> list[str]:
        """Get N most recent files."""
        return list(reversed(self._files))[:count]

    def get_score(self, file_path: str) -> float:
        """Get recency score (0-1, 1 = most recent)."""
        if file_path not in self._timestamps:
            return 0.0

        age = time.time() - self._timestamps[file_path]
        # Exponential decay: score = e^(-age/300)
        # Half-life of 5 minutes
        return 2 ** (-age / 300)
