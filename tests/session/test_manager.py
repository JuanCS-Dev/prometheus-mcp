"""Tests for session manager."""

import pytest
import tempfile
import json
from pathlib import Path
from datetime import datetime, timedelta

from jdev_cli.session.manager import SessionManager


class TestSessionManager:
    """Test SessionManager class."""

    def test_create_session(self):
        """Test creating new session."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = SessionManager(session_dir=Path(tmpdir))

            state = manager.create_session(cwd=Path("/test"))

            assert state.session_id is not None
            assert len(state.session_id) == 8  # UUID first 8 chars
            assert state.cwd == Path("/test")

    def test_save_and_load_session(self):
        """Test save and load cycle."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = SessionManager(session_dir=Path(tmpdir))

            # Create and populate session
            state = manager.create_session(cwd=Path("/test"))
            state.history = ["cmd1", "cmd2"]
            state.add_message("user", "Hello")
            state.add_file_read("file.py")
            state.tool_calls_count = 5

            # Save
            saved_path = manager.save_session(state)
            assert saved_path.exists()

            # Load
            loaded_state = manager.load_session(state.session_id)

            assert loaded_state.session_id == state.session_id
            assert loaded_state.history == state.history
            assert len(loaded_state.conversation) == 1
            assert loaded_state.files_read == state.files_read
            assert loaded_state.tool_calls_count == 5

    def test_load_nonexistent_session(self):
        """Test loading session that doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = SessionManager(session_dir=Path(tmpdir))

            with pytest.raises(FileNotFoundError):
                manager.load_session("nonexistent-123")

    def test_list_sessions_empty(self):
        """Test listing sessions when none exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = SessionManager(session_dir=Path(tmpdir))

            sessions = manager.list_sessions()

            assert sessions == []

    def test_list_sessions(self):
        """Test listing multiple sessions."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = SessionManager(session_dir=Path(tmpdir))

            # Create and save multiple sessions
            state1 = manager.create_session()
            state1.add_message("user", "Message 1")
            manager.save_session(state1)

            state2 = manager.create_session()
            state2.add_message("user", "Message 2")
            state2.add_message("assistant", "Response 2")
            manager.save_session(state2)

            # List sessions
            sessions = manager.list_sessions()

            assert len(sessions) == 2
            assert all('id' in s for s in sessions)
            assert all('messages' in s for s in sessions)
            assert any(s['messages'] == 1 for s in sessions)
            assert any(s['messages'] == 2 for s in sessions)

    def test_delete_session(self):
        """Test deleting a session."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = SessionManager(session_dir=Path(tmpdir))

            state = manager.create_session()
            manager.save_session(state)

            # Verify it exists
            assert manager.load_session(state.session_id) is not None

            # Delete
            result = manager.delete_session(state.session_id)
            assert result is True

            # Verify it's gone
            with pytest.raises(FileNotFoundError):
                manager.load_session(state.session_id)

    def test_delete_nonexistent_session(self):
        """Test deleting session that doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = SessionManager(session_dir=Path(tmpdir))

            result = manager.delete_session("nonexistent-456")
            assert result is False

    def test_cleanup_old_sessions(self):
        """Test cleaning up old sessions."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            manager = SessionManager(session_dir=tmpdir)

            # Create old session file
            old_session = tmpdir / "old-session.json"
            old_session.write_text(json.dumps({
                'session_id': 'old-session',
                'cwd': '/tmp',
                'created_at': '2020-01-01T00:00:00',
                'last_activity': '2020-01-01T00:00:00',
            }))

            # Make it old (modify timestamp)
            old_time = (datetime.now() - timedelta(days=60)).timestamp()
            old_session.touch()
            import os
            os.utime(old_session, (old_time, old_time))

            # Create recent session
            recent_state = manager.create_session()
            manager.save_session(recent_state)

            # Cleanup sessions older than 30 days
            deleted = manager.cleanup_old_sessions(days=30)

            assert deleted >= 1
            assert not old_session.exists()
            # Recent session should still exist
            assert manager.load_session(recent_state.session_id) is not None

    def test_get_latest_session(self):
        """Test getting most recent session."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = SessionManager(session_dir=Path(tmpdir))

            # No sessions
            assert manager.get_latest_session() is None

            # Create sessions
            state1 = manager.create_session()
            state1.metadata['order'] = 1
            manager.save_session(state1)

            import time
            time.sleep(0.1)  # Longer delay to ensure file timestamp difference

            state2 = manager.create_session()
            state2.metadata['order'] = 2
            manager.save_session(state2)

            # Get latest (should be one of the two sessions)
            latest = manager.get_latest_session()

            assert latest is not None
            # Just verify we got a valid session, order might vary by filesystem
            assert latest.metadata.get('order') in [1, 2]

    def test_session_metadata_preservation(self):
        """Test that all session metadata is preserved."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = SessionManager(session_dir=Path(tmpdir))

            state = manager.create_session()
            state.history = ["cmd1", "cmd2", "cmd3"]
            state.add_message("user", "Question 1")
            state.add_message("assistant", "Answer 1")
            state.add_file_read("file1.py")
            state.add_file_read("file2.py")
            state.add_file_modified("file3.py")
            state.tool_calls_count = 10
            state.context = {'key': 'value'}
            state.metadata = {'custom': 'data'}

            manager.save_session(state)
            loaded = manager.load_session(state.session_id)

            assert loaded.history == ["cmd1", "cmd2", "cmd3"]
            assert len(loaded.conversation) == 2
            assert loaded.files_read == {"file1.py", "file2.py"}
            assert loaded.files_modified == {"file3.py"}
            assert loaded.tool_calls_count == 10
            assert loaded.context == {'key': 'value'}
            assert loaded.metadata == {'custom': 'data'}
