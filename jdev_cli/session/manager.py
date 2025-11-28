"""Session manager for persistence and resumption."""

import json
import uuid
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
from rich.console import Console

from .state import SessionState


console = Console()


class SessionManager:
    """Manage session persistence and resumption."""

    DEFAULT_SESSION_DIR = Path(".qwen/sessions")

    def __init__(self, session_dir: Optional[Path] = None):
        """Initialize session manager.
        
        Args:
            session_dir: Directory for session files (default: .qwen/sessions)
        """
        self.session_dir = session_dir or self.DEFAULT_SESSION_DIR
        try:
            self.session_dir.mkdir(parents=True, exist_ok=True)
        except (FileNotFoundError, OSError):
            # CWD may not exist, fallback to home directory
            self.session_dir = Path.home() / ".qwen_sessions"
            self.session_dir.mkdir(parents=True, exist_ok=True)

    def create_session(self, cwd: Optional[Path] = None) -> SessionState:
        """Create new session state.
        
        Args:
            cwd: Working directory (default: current directory)
            
        Returns:
            New SessionState instance
        """
        session_id = str(uuid.uuid4())[:8]
        return SessionState(
            session_id=session_id,
            cwd=cwd or Path.cwd()
        )

    def save_session(self, state: SessionState) -> Path:
        """Save session state to disk with atomic write protection.
        
        Args:
            state: SessionState to save
            
        Returns:
            Path to saved session file
        """
        session_file = self.session_dir / f"{state.session_id}.json"
        temp_file = self.session_dir / f"{state.session_id}.json.tmp"

        try:
            # Atomic write pattern: write to temp, then replace
            with open(temp_file, 'w') as f:
                json.dump(state.to_dict(), f, indent=2)

            # Atomic replace (safe on all platforms)
            import os
            os.replace(temp_file, session_file)

            console.print(f"[dim]Session saved:[/dim] {state.session_id}")
            return session_file

        except Exception as e:
            # Cleanup temp file on error
            if temp_file.exists():
                temp_file.unlink()
            console.print(f"[red]Failed to save session:[/red] {e}")
            raise

    def load_session(self, session_id: str) -> SessionState:
        """Load session state from disk.
        
        Args:
            session_id: Session ID to load
            
        Returns:
            Loaded SessionState
            
        Raises:
            FileNotFoundError: If session not found
        """
        session_file = self.session_dir / f"{session_id}.json"

        if not session_file.exists():
            raise FileNotFoundError(f"Session '{session_id}' not found")

        try:
            with open(session_file) as f:
                data = json.load(f)

            state = SessionState.from_dict(data)
            console.print(f"[dim]Session loaded:[/dim] {session_id}")
            return state

        except Exception as e:
            console.print(f"[red]Failed to load session:[/red] {e}")
            raise

    def list_sessions(self) -> List[Dict[str, Any]]:
        """List all saved sessions.
        
        Returns:
            List of session metadata dictionaries
        """
        if not self.session_dir.exists():
            return []

        sessions = []
        for session_file in sorted(self.session_dir.glob("*.json"), reverse=True):
            try:
                with open(session_file) as f:
                    data = json.load(f)

                sessions.append({
                    'id': data['session_id'],
                    'cwd': data['cwd'],
                    'created_at': data['created_at'],
                    'last_activity': data['last_activity'],
                    'messages': len(data.get('conversation', [])),
                    'files_read': len(data.get('files_read', [])),
                    'files_modified': len(data.get('files_modified', [])),
                    'tool_calls': data.get('tool_calls_count', 0),
                })
            except Exception as e:
                console.print(f"[yellow]Warning: Could not load {session_file.name}:[/yellow] {e}")
                continue

        return sessions

    def delete_session(self, session_id: str) -> bool:
        """Delete a session.
        
        Args:
            session_id: Session ID to delete
            
        Returns:
            True if deleted, False if not found
        """
        session_file = self.session_dir / f"{session_id}.json"

        if not session_file.exists():
            return False

        try:
            session_file.unlink()
            console.print(f"[dim]Session deleted:[/dim] {session_id}")
            return True
        except Exception as e:
            console.print(f"[red]Failed to delete session:[/red] {e}")
            raise

    def cleanup_old_sessions(self, days: int = 30) -> int:
        """Delete sessions older than specified days.
        
        Args:
            days: Delete sessions older than this many days
            
        Returns:
            Number of sessions deleted
        """
        if not self.session_dir.exists():
            return 0

        cutoff = datetime.now().timestamp() - (days * 24 * 60 * 60)
        deleted = 0

        for session_file in self.session_dir.glob("*.json"):
            try:
                if session_file.stat().st_mtime < cutoff:
                    session_file.unlink()
                    deleted += 1
            except Exception:
                continue

        if deleted > 0:
            console.print(f"[dim]Cleaned up {deleted} old sessions[/dim]")

        return deleted

    def get_latest_session(self) -> Optional[SessionState]:
        """Get the most recent session.
        
        Returns:
            Latest SessionState or None if no sessions exist
        """
        sessions = self.list_sessions()
        if not sessions:
            return None

        latest_id = sessions[0]['id']
        return self.load_session(latest_id)
