"""
SessionManager - Session Persistence and Crash Recovery
Pipeline de Diamante - Camada 3: EXECUTION SANDBOX

Addresses: ISSUE-086, ISSUE-087, ISSUE-088 (Session persistence and recovery)

Implements comprehensive session management:
- Auto-save snapshots at configurable intervals
- Checksum verification for corruption detection
- Automatic recovery on startup
- Session history with search
- Conversation context persistence

Design Philosophy:
- Never lose user work
- Fast startup with lazy loading
- Corruption detection and recovery
- Privacy-aware (sensitive data handling)
"""

from __future__ import annotations

import os
import json
import time
import hashlib
import gzip
from typing import Any, Dict, List, Optional, TypeVar
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import threading
import logging

logger = logging.getLogger(__name__)

T = TypeVar('T')


class SessionState(Enum):
    """Session states."""
    NEW = "new"
    ACTIVE = "active"
    PAUSED = "paused"
    CRASHED = "crashed"
    COMPLETED = "completed"
    RECOVERED = "recovered"


@dataclass
class ConversationMessage:
    """A message in the conversation."""
    role: str  # "user", "assistant", "system", "tool"
    content: str
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ConversationMessage":
        """Deserialize from dictionary."""
        return cls(
            role=data["role"],
            content=data["content"],
            timestamp=data.get("timestamp", time.time()),
            metadata=data.get("metadata", {}),
        )


@dataclass
class SessionSnapshot:
    """A snapshot of session state."""
    session_id: str
    state: SessionState
    created_at: float
    updated_at: float
    checksum: str

    # Conversation state
    messages: List[ConversationMessage]
    context: Dict[str, Any]

    # Working state
    working_directory: str
    open_files: List[str]
    pending_operations: List[Dict[str, Any]]

    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "session_id": self.session_id,
            "state": self.state.value,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "checksum": self.checksum,
            "messages": [m.to_dict() for m in self.messages],
            "context": self.context,
            "working_directory": self.working_directory,
            "open_files": self.open_files,
            "pending_operations": self.pending_operations,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SessionSnapshot":
        """Deserialize from dictionary."""
        return cls(
            session_id=data["session_id"],
            state=SessionState(data["state"]),
            created_at=data["created_at"],
            updated_at=data["updated_at"],
            checksum=data["checksum"],
            messages=[ConversationMessage.from_dict(m) for m in data.get("messages", [])],
            context=data.get("context", {}),
            working_directory=data.get("working_directory", os.getcwd()),
            open_files=data.get("open_files", []),
            pending_operations=data.get("pending_operations", []),
            metadata=data.get("metadata", {}),
        )


@dataclass
class SessionInfo:
    """Summary information about a session."""
    session_id: str
    state: SessionState
    created_at: float
    updated_at: float
    message_count: int
    working_directory: str
    summary: str  # Brief description


class SessionManager:
    """
    Session persistence and crash recovery manager.

    Features:
    - Auto-save at configurable intervals
    - Checksum verification for corruption detection
    - Automatic crash recovery
    - Session history with search
    - Compression for storage efficiency

    Usage:
        manager = SessionManager()

        # Start or resume session
        session = manager.start_session()

        # Add messages
        manager.add_message("user", "Hello")
        manager.add_message("assistant", "Hi there!")

        # Save manually (also auto-saves)
        manager.save()

        # Later: resume session
        session = manager.resume_session(session_id)
    """

    SESSION_DIR = ".qwen_sessions"
    CURRENT_SESSION_FILE = "current_session.json"
    INDEX_FILE = "sessions_index.json"
    AUTO_SAVE_INTERVAL = 30  # seconds
    MAX_SESSIONS = 50  # Keep last N sessions
    COMPRESSION_THRESHOLD = 10 * 1024  # Compress if > 10KB

    def __init__(
        self,
        session_dir: Optional[str] = None,
        auto_save_interval: float = AUTO_SAVE_INTERVAL,
        enable_compression: bool = True,
        max_sessions: int = MAX_SESSIONS,
    ):
        """
        Initialize SessionManager.

        Args:
            session_dir: Directory for session storage
            auto_save_interval: Auto-save interval in seconds
            enable_compression: Enable gzip compression
            max_sessions: Maximum number of sessions to keep
        """
        self.session_dir = Path(session_dir or self.SESSION_DIR)
        self.auto_save_interval = auto_save_interval
        self.enable_compression = enable_compression
        self.max_sessions = max_sessions

        self._current_session: Optional[SessionSnapshot] = None
        self._dirty = False
        self._last_save = time.time()
        self._auto_save_thread: Optional[threading.Thread] = None
        self._stop_auto_save = threading.Event()

        # Ensure session directory exists
        self.session_dir.mkdir(parents=True, exist_ok=True)

    def _generate_session_id(self) -> str:
        """Generate unique session ID."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        random_suffix = hashlib.md5(str(time.time()).encode()).hexdigest()[:6]
        return f"session_{timestamp}_{random_suffix}"

    def _compute_checksum(self, data: Dict[str, Any]) -> str:
        """Compute checksum for data integrity verification."""
        # Exclude checksum field itself
        data_copy = {k: v for k, v in data.items() if k != "checksum"}
        content = json.dumps(data_copy, sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def _get_session_path(self, session_id: str) -> Path:
        """Get path for session file."""
        ext = ".json.gz" if self.enable_compression else ".json"
        return self.session_dir / f"{session_id}{ext}"

    def _save_session(self, snapshot: SessionSnapshot, path: Path) -> bool:
        """Save session snapshot to file."""
        try:
            data = snapshot.to_dict()
            data["checksum"] = self._compute_checksum(data)

            content = json.dumps(data, indent=2)

            if self.enable_compression and len(content) > self.COMPRESSION_THRESHOLD:
                path = path.with_suffix(".json.gz")
                with gzip.open(str(path), 'wt', encoding='utf-8') as f:
                    f.write(content)
            else:
                path = path.with_suffix(".json")
                path.write_text(content)

            return True

        except Exception as e:
            logger.error(f"Failed to save session: {e}")
            return False

    def _load_session(self, path: Path) -> Optional[SessionSnapshot]:
        """Load session snapshot from file."""
        try:
            # Try compressed first
            if path.with_suffix(".json.gz").exists():
                path = path.with_suffix(".json.gz")
                with gzip.open(str(path), 'rt', encoding='utf-8') as f:
                    content = f.read()
            elif path.with_suffix(".json").exists():
                path = path.with_suffix(".json")
                content = path.read_text()
            else:
                return None

            data = json.loads(content)

            # Verify checksum
            expected_checksum = data.get("checksum", "")
            actual_checksum = self._compute_checksum(data)

            if expected_checksum and expected_checksum != actual_checksum:
                logger.warning(f"Session checksum mismatch: {path}")
                # Still try to load, but mark as potentially corrupted
                data["metadata"]["checksum_mismatch"] = True

            return SessionSnapshot.from_dict(data)

        except Exception as e:
            logger.error(f"Failed to load session: {e}")
            return None

    def _update_index(self, session_info: SessionInfo) -> None:
        """Update session index file."""
        index_path = self.session_dir / self.INDEX_FILE
        index: Dict[str, Dict[str, Any]] = {}

        if index_path.exists():
            try:
                index = json.loads(index_path.read_text())
            except Exception:
                pass

        index[session_info.session_id] = {
            "state": session_info.state.value,
            "created_at": session_info.created_at,
            "updated_at": session_info.updated_at,
            "message_count": session_info.message_count,
            "working_directory": session_info.working_directory,
            "summary": session_info.summary,
        }

        # Prune old sessions
        if len(index) > self.max_sessions:
            sorted_sessions = sorted(
                index.items(),
                key=lambda x: x[1]["updated_at"],
                reverse=True
            )
            index = dict(sorted_sessions[:self.max_sessions])

            # Delete old session files
            for session_id, _ in sorted_sessions[self.max_sessions:]:
                for ext in [".json", ".json.gz"]:
                    path = self.session_dir / f"{session_id}{ext}"
                    if path.exists():
                        try:
                            path.unlink()
                        except Exception:
                            pass

        index_path.write_text(json.dumps(index, indent=2))

    def _auto_save_loop(self) -> None:
        """Background thread for auto-saving."""
        while not self._stop_auto_save.wait(self.auto_save_interval):
            if self._dirty and self._current_session:
                self.save()

    def _start_auto_save(self) -> None:
        """Start auto-save background thread."""
        if self._auto_save_thread is None or not self._auto_save_thread.is_alive():
            self._stop_auto_save.clear()
            self._auto_save_thread = threading.Thread(
                target=self._auto_save_loop,
                daemon=True
            )
            self._auto_save_thread.start()

    def _stop_auto_save_thread(self) -> None:
        """Stop auto-save background thread."""
        self._stop_auto_save.set()
        if self._auto_save_thread:
            self._auto_save_thread.join(timeout=1)

    def start_session(
        self,
        working_directory: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> SessionSnapshot:
        """
        Start a new session.

        Args:
            working_directory: Working directory for the session
            context: Initial context data

        Returns:
            New session snapshot
        """
        session_id = self._generate_session_id()
        now = time.time()

        self._current_session = SessionSnapshot(
            session_id=session_id,
            state=SessionState.ACTIVE,
            created_at=now,
            updated_at=now,
            checksum="",
            messages=[],
            context=context or {},
            working_directory=working_directory or os.getcwd(),
            open_files=[],
            pending_operations=[],
        )

        self._dirty = True
        self.save()

        # Start auto-save
        self._start_auto_save()

        logger.info(f"Started new session: {session_id}")
        return self._current_session

    def resume_session(self, session_id: str) -> Optional[SessionSnapshot]:
        """
        Resume an existing session.

        Args:
            session_id: Session ID to resume

        Returns:
            Session snapshot if found, None otherwise
        """
        path = self._get_session_path(session_id)
        session = self._load_session(path)

        if session:
            session.state = SessionState.RECOVERED
            session.updated_at = time.time()
            self._current_session = session
            self._dirty = True

            # Start auto-save
            self._start_auto_save()

            logger.info(f"Resumed session: {session_id}")
            return session

        return None

    def resume_latest(self) -> Optional[SessionSnapshot]:
        """Resume the most recent session."""
        sessions = self.list_sessions()
        if sessions:
            latest = max(sessions, key=lambda s: s.updated_at)
            return self.resume_session(latest.session_id)
        return None

    def check_for_crash_recovery(self) -> Optional[SessionSnapshot]:
        """
        Check for crashed session and offer recovery.

        Returns:
            Crashed session if found, None otherwise
        """
        # Check for current session marker
        current_path = self.session_dir / self.CURRENT_SESSION_FILE

        if current_path.exists():
            try:
                data = json.loads(current_path.read_text())
                session_id = data.get("session_id")

                if session_id:
                    path = self._get_session_path(session_id)
                    session = self._load_session(path)

                    if session and session.state == SessionState.ACTIVE:
                        session.state = SessionState.CRASHED
                        logger.warning(f"Found crashed session: {session_id}")
                        return session

            except Exception as e:
                logger.debug(f"No crash recovery needed: {e}")

        return None

    def add_message(
        self,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Add a message to the current session.

        Args:
            role: Message role (user, assistant, system, tool)
            content: Message content
            metadata: Additional metadata
        """
        if not self._current_session:
            raise RuntimeError("No active session")

        message = ConversationMessage(
            role=role,
            content=content,
            metadata=metadata or {},
        )

        self._current_session.messages.append(message)
        self._current_session.updated_at = time.time()
        self._dirty = True

    def update_context(self, key: str, value: Any) -> None:
        """Update session context."""
        if not self._current_session:
            raise RuntimeError("No active session")

        self._current_session.context[key] = value
        self._current_session.updated_at = time.time()
        self._dirty = True

    def add_pending_operation(self, operation: Dict[str, Any]) -> None:
        """Add a pending operation (for crash recovery)."""
        if not self._current_session:
            return

        self._current_session.pending_operations.append(operation)
        self._dirty = True

    def clear_pending_operations(self) -> List[Dict[str, Any]]:
        """Clear and return pending operations."""
        if not self._current_session:
            return []

        operations = self._current_session.pending_operations
        self._current_session.pending_operations = []
        self._dirty = True

        return operations

    def save(self) -> bool:
        """
        Save current session to disk.

        Returns:
            True if save was successful
        """
        if not self._current_session:
            return False

        self._current_session.updated_at = time.time()

        # Save session file
        path = self._get_session_path(self._current_session.session_id)
        if not self._save_session(self._current_session, path):
            return False

        # Update current session marker
        current_path = self.session_dir / self.CURRENT_SESSION_FILE
        current_data = {
            "session_id": self._current_session.session_id,
            "updated_at": self._current_session.updated_at,
        }
        current_path.write_text(json.dumps(current_data))

        # Update index
        summary = self._generate_summary()
        info = SessionInfo(
            session_id=self._current_session.session_id,
            state=self._current_session.state,
            created_at=self._current_session.created_at,
            updated_at=self._current_session.updated_at,
            message_count=len(self._current_session.messages),
            working_directory=self._current_session.working_directory,
            summary=summary,
        )
        self._update_index(info)

        self._dirty = False
        self._last_save = time.time()

        return True

    def _generate_summary(self) -> str:
        """Generate brief summary of session."""
        if not self._current_session:
            return ""

        messages = self._current_session.messages
        if not messages:
            return "Empty session"

        # Get first user message as summary
        for msg in messages:
            if msg.role == "user":
                content = msg.content.strip()
                if len(content) > 100:
                    return content[:97] + "..."
                return content

        return f"{len(messages)} messages"

    def end_session(self) -> None:
        """End the current session gracefully."""
        if self._current_session:
            self._current_session.state = SessionState.COMPLETED
            self._current_session.updated_at = time.time()
            self.save()

            # Remove current session marker
            current_path = self.session_dir / self.CURRENT_SESSION_FILE
            if current_path.exists():
                current_path.unlink()

            self._stop_auto_save_thread()
            self._current_session = None

    def list_sessions(self, limit: int = 20) -> List[SessionInfo]:
        """
        List recent sessions.

        Args:
            limit: Maximum number of sessions to return

        Returns:
            List of session info, newest first
        """
        index_path = self.session_dir / self.INDEX_FILE

        if not index_path.exists():
            return []

        try:
            index = json.loads(index_path.read_text())

            sessions = [
                SessionInfo(
                    session_id=sid,
                    state=SessionState(data["state"]),
                    created_at=data["created_at"],
                    updated_at=data["updated_at"],
                    message_count=data["message_count"],
                    working_directory=data["working_directory"],
                    summary=data["summary"],
                )
                for sid, data in index.items()
            ]

            # Sort by updated_at, newest first
            sessions.sort(key=lambda s: s.updated_at, reverse=True)

            return sessions[:limit]

        except Exception as e:
            logger.error(f"Failed to list sessions: {e}")
            return []

    def search_sessions(
        self,
        query: str,
        limit: int = 10,
    ) -> List[SessionInfo]:
        """
        Search sessions by content.

        Args:
            query: Search query
            limit: Maximum results

        Returns:
            Matching sessions
        """
        query_lower = query.lower()
        results = []

        for session_info in self.list_sessions(limit=100):
            # Check summary
            if query_lower in session_info.summary.lower():
                results.append(session_info)
                continue

            # Load full session and search messages
            path = self._get_session_path(session_info.session_id)
            session = self._load_session(path)

            if session:
                for msg in session.messages:
                    if query_lower in msg.content.lower():
                        results.append(session_info)
                        break

            if len(results) >= limit:
                break

        return results

    def get_messages(
        self,
        limit: Optional[int] = None,
        since: Optional[float] = None,
    ) -> List[ConversationMessage]:
        """
        Get messages from current session.

        Args:
            limit: Maximum number of messages (from end)
            since: Only messages after this timestamp

        Returns:
            List of messages
        """
        if not self._current_session:
            return []

        messages = self._current_session.messages

        if since:
            messages = [m for m in messages if m.timestamp >= since]

        if limit:
            messages = messages[-limit:]

        return messages

    @property
    def current_session(self) -> Optional[SessionSnapshot]:
        """Get current session."""
        return self._current_session

    @property
    def is_active(self) -> bool:
        """Check if there's an active session."""
        return self._current_session is not None


# Global instance
_default_manager: Optional[SessionManager] = None


def get_session_manager() -> SessionManager:
    """Get the default session manager instance."""
    global _default_manager
    if _default_manager is None:
        _default_manager = SessionManager()
    return _default_manager


# Convenience functions

def start_session(**kwargs) -> SessionSnapshot:
    """Start a new session."""
    return get_session_manager().start_session(**kwargs)


def resume_session(session_id: str) -> Optional[SessionSnapshot]:
    """Resume an existing session."""
    return get_session_manager().resume_session(session_id)


def add_message(role: str, content: str, **kwargs) -> None:
    """Add a message to the current session."""
    get_session_manager().add_message(role, content, **kwargs)


def save_session() -> bool:
    """Save the current session."""
    return get_session_manager().save()


def end_session() -> None:
    """End the current session."""
    get_session_manager().end_session()


# Export all public symbols
__all__ = [
    'SessionState',
    'ConversationMessage',
    'SessionSnapshot',
    'SessionInfo',
    'SessionManager',
    'get_session_manager',
    'start_session',
    'resume_session',
    'add_message',
    'save_session',
    'end_session',
]
