"""Tests for session state."""

from datetime import datetime
from pathlib import Path

from jdev_cli.session.state import SessionState


class TestSessionState:
    """Test SessionState dataclass."""

    def test_default_initialization(self):
        """Test session state with defaults."""
        state = SessionState(session_id="test-123", cwd=Path("/tmp"))

        assert state.session_id == "test-123"
        assert state.cwd == Path("/tmp")
        assert state.history == []
        assert state.conversation == []
        assert state.context == {}
        assert state.files_read == set()
        assert state.files_modified == set()
        assert state.tool_calls_count == 0
        assert isinstance(state.created_at, datetime)
        assert isinstance(state.last_activity, datetime)

    def test_to_dict(self):
        """Test converting state to dictionary."""
        state = SessionState(session_id="test-456", cwd=Path("/home/user"))
        state.history = ["command1", "command2"]
        state.files_read = {"file1.py", "file2.py"}

        data = state.to_dict()

        assert data['session_id'] == "test-456"
        assert data['cwd'] == "/home/user"
        assert data['history'] == ["command1", "command2"]
        assert set(data['files_read']) == {"file1.py", "file2.py"}
        assert isinstance(data['created_at'], str)

    def test_from_dict(self):
        """Test creating state from dictionary."""
        data = {
            'session_id': 'test-789',
            'cwd': '/tmp/test',
            'history': ['cmd1', 'cmd2'],
            'conversation': [],
            'context': {},
            'files_read': ['file1.py'],
            'files_modified': [],
            'tool_calls_count': 5,
            'created_at': '2025-01-01T12:00:00',
            'last_activity': '2025-01-01T12:30:00',
            'metadata': {},
        }

        state = SessionState.from_dict(data)

        assert state.session_id == 'test-789'
        assert state.cwd == Path('/tmp/test')
        assert state.history == ['cmd1', 'cmd2']
        assert state.files_read == {'file1.py'}
        assert state.tool_calls_count == 5

    def test_add_message(self):
        """Test adding messages to conversation."""
        state = SessionState(session_id="test", cwd=Path("/tmp"))

        state.add_message("user", "Hello")
        state.add_message("assistant", "Hi there!")

        assert len(state.conversation) == 2
        assert state.conversation[0]['role'] == "user"
        assert state.conversation[0]['content'] == "Hello"
        assert state.conversation[1]['role'] == "assistant"
        assert 'timestamp' in state.conversation[0]

    def test_add_file_read(self):
        """Test tracking files read."""
        state = SessionState(session_id="test", cwd=Path("/tmp"))

        state.add_file_read("src/main.py")
        state.add_file_read("tests/test_main.py")
        state.add_file_read("src/main.py")  # Duplicate

        assert len(state.files_read) == 2
        assert "src/main.py" in state.files_read
        assert "tests/test_main.py" in state.files_read

    def test_add_file_modified(self):
        """Test tracking files modified."""
        state = SessionState(session_id="test", cwd=Path("/tmp"))

        state.add_file_modified("src/utils.py")

        assert "src/utils.py" in state.files_modified

    def test_increment_tool_calls(self):
        """Test incrementing tool call counter."""
        state = SessionState(session_id="test", cwd=Path("/tmp"))

        assert state.tool_calls_count == 0

        state.increment_tool_calls()
        assert state.tool_calls_count == 1

        state.increment_tool_calls()
        state.increment_tool_calls()
        assert state.tool_calls_count == 3

    def test_update_activity(self):
        """Test activity timestamp updates."""
        state = SessionState(session_id="test", cwd=Path("/tmp"))

        original_activity = state.last_activity

        # Small delay to ensure timestamp changes
        import time
        time.sleep(0.01)

        state.update_activity()

        assert state.last_activity > original_activity

    def test_roundtrip_serialization(self):
        """Test to_dict -> from_dict roundtrip."""
        original = SessionState(session_id="roundtrip", cwd=Path("/test"))
        original.history = ["cmd1", "cmd2"]
        original.add_message("user", "test message")
        original.add_file_read("file.py")
        original.tool_calls_count = 10

        data = original.to_dict()
        restored = SessionState.from_dict(data)

        assert restored.session_id == original.session_id
        assert restored.cwd == original.cwd
        assert restored.history == original.history
        assert len(restored.conversation) == len(original.conversation)
        assert restored.files_read == original.files_read
        assert restored.tool_calls_count == original.tool_calls_count
