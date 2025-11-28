"""Tests for session validation."""

import pytest
from jdev_cli.session.state import SessionState


class TestSessionValidation:
    """Test session state validation."""

    def test_from_dict_missing_session_id(self):
        """Test validation catches missing session_id."""
        data = {
            'cwd': '/tmp',
            'created_at': '2025-01-01T00:00:00',
            'last_activity': '2025-01-01T00:00:00',
        }

        with pytest.raises(ValueError) as exc:
            SessionState.from_dict(data)

        assert 'Missing required fields' in str(exc.value)
        assert 'session_id' in str(exc.value)

    def test_from_dict_missing_cwd(self):
        """Test validation catches missing cwd."""
        data = {
            'session_id': 'test-123',
            'created_at': '2025-01-01T00:00:00',
            'last_activity': '2025-01-01T00:00:00',
        }

        with pytest.raises(ValueError) as exc:
            SessionState.from_dict(data)

        assert 'Missing required fields' in str(exc.value)
        assert 'cwd' in str(exc.value)

    def test_from_dict_missing_timestamps(self):
        """Test validation catches missing timestamps."""
        data = {
            'session_id': 'test-123',
            'cwd': '/tmp',
        }

        with pytest.raises(ValueError) as exc:
            SessionState.from_dict(data)

        assert 'Missing required fields' in str(exc.value)
        assert 'created_at' in str(exc.value) or 'last_activity' in str(exc.value)

    def test_from_dict_invalid_timestamp_format(self):
        """Test validation catches invalid timestamp format."""
        data = {
            'session_id': 'test-123',
            'cwd': '/tmp',
            'created_at': 'not-a-timestamp',
            'last_activity': '2025-01-01T00:00:00',
        }

        with pytest.raises(ValueError) as exc:
            SessionState.from_dict(data)

        assert 'Invalid session data format' in str(exc.value)

    def test_from_dict_all_fields_valid(self):
        """Test validation passes with all required fields."""
        data = {
            'session_id': 'test-123',
            'cwd': '/tmp',
            'created_at': '2025-01-01T00:00:00',
            'last_activity': '2025-01-01T00:00:00',
        }

        # Should not raise
        state = SessionState.from_dict(data)
        assert state.session_id == 'test-123'

    def test_from_dict_with_optional_fields(self):
        """Test optional fields are handled correctly."""
        data = {
            'session_id': 'test-123',
            'cwd': '/tmp',
            'created_at': '2025-01-01T00:00:00',
            'last_activity': '2025-01-01T00:00:00',
            'history': ['cmd1', 'cmd2'],
            'files_read': ['file1.py'],
            'tool_calls_count': 5,
        }

        state = SessionState.from_dict(data)
        assert state.history == ['cmd1', 'cmd2']
        assert state.files_read == {'file1.py'}
        assert state.tool_calls_count == 5

    def test_from_dict_missing_optional_fields_use_defaults(self):
        """Test missing optional fields use defaults."""
        data = {
            'session_id': 'test-123',
            'cwd': '/tmp',
            'created_at': '2025-01-01T00:00:00',
            'last_activity': '2025-01-01T00:00:00',
        }

        state = SessionState.from_dict(data)
        assert state.history == []
        assert state.conversation == []
        assert state.context == {}
        assert state.files_read == set()
        assert state.files_modified == set()
        assert state.tool_calls_count == 0
        assert state.metadata == {}
