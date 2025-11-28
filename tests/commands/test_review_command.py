"""
Tests for /review slash command.
"""

import pytest
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, patch

from jdev_cli.commands.review import handle_review


@pytest.mark.asyncio
class TestReviewCommand:
    """Test /review command functionality."""

    async def test_no_session(self):
        """Test when no active session exists."""
        context = {}
        result = await handle_review("", context)

        assert "No active session" in result

    async def test_basic_review(self):
        """Test basic review output."""
        session = Mock()
        session.session_id = "test-session-123"
        session.created_at = datetime.now()
        session.modified_files = {"file1.py", "file2.py"}
        session.read_files = {"file3.py"}
        session.tool_calls_count = 5

        context = {'session': session, 'cwd': Path.cwd()}
        result = await handle_review("", context)

        assert "Session Review" in result
        assert "test-ses" in result  # Truncated session ID
        assert "Files Modified (2)" in result
        assert "file1.py" in result
        assert "file2.py" in result
        assert "Files Read (1)" in result
        assert "file3.py" in result
        assert "Tool Calls" in result
        assert "5" in result

    async def test_empty_session(self):
        """Test review with empty session."""
        session = Mock()
        session.session_id = "empty-session"
        session.created_at = datetime.now()
        session.modified_files = set()
        session.read_files = set()
        session.tool_calls_count = 0

        context = {'session': session}
        result = await handle_review("", context)

        assert "Session Review" in result
        assert "Tool Calls" in result
        assert "0" in result

    async def test_many_read_files(self):
        """Test review with many read files (should truncate)."""
        session = Mock()
        session.session_id = "test-session"
        session.created_at = datetime.now()
        session.modified_files = set()
        session.read_files = {f"file{i}.py" for i in range(20)}
        session.tool_calls_count = 0

        context = {'session': session}
        result = await handle_review("", context)

        assert "Files Read (20)" in result
        assert "... and" in result  # Truncation message

    @patch('jdev_cli.commands.review.subprocess.run')
    async def test_stats_flag(self, mock_run):
        """Test --stats flag."""
        # Mock git diff --numstat
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "10\t5\tfile1.py\n3\t2\tfile2.py\n"
        mock_run.return_value = mock_result

        session = Mock()
        session.session_id = "test-session"
        session.created_at = datetime.now()
        session.modified_files = {"file1.py", "file2.py"}
        session.read_files = set()
        session.tool_calls_count = 0

        context = {'session': session}
        result = await handle_review("--stats", context)

        assert "Statistics" in result
        assert "Lines Added" in result
        assert "Lines Removed" in result

    @patch('jdev_cli.commands.review._export_review')
    async def test_export_flag(self, mock_export):
        """Test --export flag."""
        mock_export.return_value = Path("/tmp/review.txt")

        session = Mock()
        session.session_id = "test-session"
        session.created_at = datetime.now()
        session.modified_files = set()
        session.read_files = set()
        session.tool_calls_count = 0

        context = {'session': session}
        result = await handle_review("--export", context)

        assert "exported" in result.lower()
        mock_export.assert_called_once()

    @patch('jdev_cli.commands.review.subprocess.run')
    async def test_git_status(self, mock_run):
        """Test git status integration."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = " M file1.py\nA  file2.py\n"
        mock_run.return_value = mock_result

        session = Mock()
        session.session_id = "test-session"
        session.created_at = datetime.now()
        session.modified_files = {"file1.py"}
        session.read_files = set()
        session.tool_calls_count = 0

        context = {'session': session, 'cwd': Path.cwd()}
        result = await handle_review("", context)

        assert "Git Status" in result


class TestReviewHelpers:
    """Test helper functions."""

    def test_session_duration(self):
        """Test duration calculation in header."""
        # This would test _format_session_header if it was exported
        # For now, we test it indirectly through handle_review
        pass

    def test_file_type_analysis(self):
        """Test file type analysis."""
        from jdev_cli.commands.review import _analyze_file_types

        files = {"file1.py", "file2.py", "test.js", "data.json"}
        types = _analyze_file_types(files)

        assert types[".py"] == 2
        assert types[".js"] == 1
        assert types[".json"] == 1
