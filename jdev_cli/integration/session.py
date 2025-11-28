"""Session manager for persistent shell state.

Inspired by:
- Claude Code: Persistent Bash sessions with state
- GitHub Codex: PTY session management
- Cursor AI: Context preservation across interactions
"""

import os
import json
import time
from typing import Dict, Any, List, Optional
from pathlib import Path
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class Session:
    """Represents a single interactive session."""

    def __init__(self, session_id: str, cwd: Optional[str] = None):
        """Initialize session.
        
        Args:
            session_id: Unique session identifier
            cwd: Current working directory (defaults to os.getcwd())
        """
        self.session_id = session_id
        self.cwd = cwd or os.getcwd()
        self.env = dict(os.environ)
        self.history: List[Dict[str, Any]] = []
        self.context: Dict[str, Any] = {}
        self.created_at = datetime.now()
        self.last_activity = datetime.now()

        # Track files and operations
        self.read_files: set = set()
        self.modified_files: set = set()
        self.deleted_files: set = set()

        # Conversation state
        self.conversation_turns = 0
        self.tool_calls_count = 0
        self.errors_count = 0

        logger.info(f"Created session {session_id} in {self.cwd}")

    def add_history(
        self,
        action: str,
        details: Dict[str, Any],
        result: Any = None,
        success: bool = True
    ):
        """Add entry to session history.
        
        Args:
            action: Action type (tool_call, user_input, etc)
            details: Action details
            result: Action result
            success: Whether action succeeded
        """
        entry = {
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "details": details,
            "result": str(result) if result else None,
            "success": success,
        }
        self.history.append(entry)
        self.last_activity = datetime.now()

        # Update counters
        if action == "tool_call":
            self.tool_calls_count += 1
            if not success:
                self.errors_count += 1
        elif action == "user_input":
            self.conversation_turns += 1

    def track_file_operation(self, operation: str, path: str):
        """Track file operations for context."""
        abs_path = os.path.abspath(path)

        if operation == "read":
            self.read_files.add(abs_path)
        elif operation in ["write", "edit", "create"]:
            self.modified_files.add(abs_path)
        elif operation == "delete":
            self.deleted_files.add(abs_path)
            self.modified_files.discard(abs_path)

    def get_summary(self) -> Dict[str, Any]:
        """Get session summary."""
        duration = (datetime.now() - self.created_at).total_seconds()

        return {
            "session_id": self.session_id,
            "cwd": self.cwd,
            "duration_seconds": duration,
            "conversation_turns": self.conversation_turns,
            "tool_calls": self.tool_calls_count,
            "errors": self.errors_count,
            "files_read": len(self.read_files),
            "files_modified": len(self.modified_files),
            "files_deleted": len(self.deleted_files),
            "last_activity": self.last_activity.isoformat(),
        }

    def to_dict(self) -> Dict[str, Any]:
        """Serialize session to dictionary."""
        return {
            "session_id": self.session_id,
            "cwd": self.cwd,
            "env": self.env,
            "history": self.history[-50:],  # Last 50 entries
            "context": self.context,
            "created_at": self.created_at.isoformat(),
            "last_activity": self.last_activity.isoformat(),
            "read_files": list(self.read_files),
            "modified_files": list(self.modified_files),
            "deleted_files": list(self.deleted_files),
            "stats": self.get_summary(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Session":
        """Deserialize session from dictionary."""
        session = cls(
            session_id=data["session_id"],
            cwd=data.get("cwd")
        )
        session.env = data.get("env", dict(os.environ))
        session.history = data.get("history", [])
        session.context = data.get("context", {})
        session.read_files = set(data.get("read_files", []))
        session.modified_files = set(data.get("modified_files", []))
        session.deleted_files = set(data.get("deleted_files", []))

        # Parse timestamps
        if "created_at" in data:
            session.created_at = datetime.fromisoformat(data["created_at"])
        if "last_activity" in data:
            session.last_activity = datetime.fromisoformat(data["last_activity"])

        return session


class SessionManager:
    """Manages multiple interactive sessions.
    
    Features:
    - Persistent session state across restarts
    - Context preservation (Cursor strategy)
    - History tracking (Claude Code strategy)
    - Multi-session support (Codex strategy)
    """

    def __init__(self, storage_dir: Optional[Path] = None):
        """Initialize session manager.
        
        Args:
            storage_dir: Directory to store session data (default: ~/.qwen_sessions)
        """
        self.storage_dir = storage_dir or (Path.home() / ".qwen_sessions")
        self.storage_dir.mkdir(exist_ok=True)

        self.sessions: Dict[str, Session] = {}
        self.active_session_id: Optional[str] = None

        # Load existing sessions
        self._load_sessions()

        logger.info(f"SessionManager initialized with {len(self.sessions)} sessions")

    def create_session(self, session_id: Optional[str] = None) -> Session:
        """Create new session.
        
        Args:
            session_id: Optional session ID (generated if None)
            
        Returns:
            Created session
        """
        if session_id is None:
            session_id = f"session_{int(time.time())}"

        if session_id in self.sessions:
            logger.warning(f"Session {session_id} already exists, returning existing")
            return self.sessions[session_id]

        session = Session(session_id)
        self.sessions[session_id] = session
        self.active_session_id = session_id

        self._save_session(session)
        return session

    def get_session(self, session_id: str) -> Optional[Session]:
        """Get session by ID."""
        return self.sessions.get(session_id)

    def get_or_create_session(self, session_id: str) -> Session:
        """Get existing session or create new one."""
        if session_id in self.sessions:
            return self.sessions[session_id]
        return self.create_session(session_id)

    def get_active_session(self) -> Optional[Session]:
        """Get currently active session."""
        if self.active_session_id:
            return self.sessions.get(self.active_session_id)
        return None

    def set_active_session(self, session_id: str):
        """Set active session."""
        if session_id in self.sessions:
            self.active_session_id = session_id
            logger.info(f"Active session set to {session_id}")
        else:
            raise ValueError(f"Session {session_id} does not exist")

    def list_sessions(self) -> List[Dict[str, Any]]:
        """List all sessions with summaries."""
        return [
            session.get_summary()
            for session in self.sessions.values()
        ]

    def delete_session(self, session_id: str) -> bool:
        """Delete session and its data."""
        if session_id not in self.sessions:
            return False

        # Remove from memory
        del self.sessions[session_id]

        # Remove from disk
        session_file = self.storage_dir / f"{session_id}.json"
        if session_file.exists():
            session_file.unlink()

        # Update active session if deleted
        if self.active_session_id == session_id:
            self.active_session_id = None

        logger.info(f"Deleted session {session_id}")
        return True

    def save_all_sessions(self):
        """Save all sessions to disk."""
        for session in self.sessions.values():
            self._save_session(session)
        logger.info(f"Saved {len(self.sessions)} sessions")

    def _save_session(self, session: Session):
        """Save single session to disk."""
        session_file = self.storage_dir / f"{session.session_id}.json"
        try:
            with open(session_file, "w") as f:
                json.dump(session.to_dict(), f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save session {session.session_id}: {e}")

    def _load_sessions(self):
        """Load sessions from disk."""
        if not self.storage_dir.exists():
            return

        for session_file in self.storage_dir.glob("*.json"):
            try:
                with open(session_file) as f:
                    data = json.load(f)
                session = Session.from_dict(data)
                self.sessions[session.session_id] = session
                logger.debug(f"Loaded session {session.session_id}")
            except Exception as e:
                logger.error(f"Failed to load {session_file}: {e}")

    def cleanup_old_sessions(self, max_age_days: int = 30):
        """Remove sessions older than max_age_days."""
        cutoff = datetime.now().timestamp() - (max_age_days * 86400)

        to_delete = []
        for session_id, session in self.sessions.items():
            if session.last_activity.timestamp() < cutoff:
                to_delete.append(session_id)

        for session_id in to_delete:
            self.delete_session(session_id)

        if to_delete:
            logger.info(f"Cleaned up {len(to_delete)} old sessions")


# Global session manager instance
session_manager = SessionManager()
