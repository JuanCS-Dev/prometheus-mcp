"""
Tests for HistoryManager - Command and Session History Management.

Tests cover:
- Command history (add, search, recent)
- Conversation context
- Session persistence (save/load/list/delete)
- Checkpoint system (create/get/rewind)

Based on pytest patterns from Anthropic's Claude Code.
"""
import pytest
import json

from jdev_tui.core.history_manager import HistoryManager


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def temp_paths(tmp_path):
    """Create temporary paths for history and sessions."""
    return {
        "history_file": tmp_path / ".jdev_tui_history",
        "session_dir": tmp_path / ".juancs" / "sessions"
    }


@pytest.fixture
def history_manager(temp_paths):
    """Create HistoryManager with temp paths."""
    return HistoryManager(
        history_file=temp_paths["history_file"],
        session_dir=temp_paths["session_dir"]
    )


@pytest.fixture
def history_with_data(temp_paths):
    """Create HistoryManager with pre-existing data."""
    # Create history file with commands
    temp_paths["history_file"].write_text("git status\ngit add .\ngit commit -m test")

    # Create session directory with a session
    temp_paths["session_dir"].mkdir(parents=True, exist_ok=True)
    session_file = temp_paths["session_dir"] / "20250101_120000.json"
    session_file.write_text(json.dumps({
        "session_id": "20250101_120000",
        "timestamp": "2025-01-01T12:00:00",
        "context": [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"}
        ],
        "commands": ["git status"],
        "version": "1.0"
    }))

    return HistoryManager(
        history_file=temp_paths["history_file"],
        session_dir=temp_paths["session_dir"]
    )


# =============================================================================
# INITIALIZATION TESTS
# =============================================================================

class TestHistoryManagerInit:
    """Tests for HistoryManager initialization."""

    def test_init_defaults(self):
        """Test default initialization values."""
        manager = HistoryManager()
        assert manager.max_commands == 1000
        assert manager.max_context == 50

    def test_init_custom_limits(self, temp_paths):
        """Test custom limits."""
        manager = HistoryManager(
            max_commands=500,
            max_context=25,
            history_file=temp_paths["history_file"],
            session_dir=temp_paths["session_dir"]
        )
        assert manager.max_commands == 500
        assert manager.max_context == 25

    def test_init_custom_paths(self, temp_paths):
        """Test custom file paths."""
        manager = HistoryManager(
            history_file=temp_paths["history_file"],
            session_dir=temp_paths["session_dir"]
        )
        assert manager._history_file == temp_paths["history_file"]
        assert manager._session_dir == temp_paths["session_dir"]

    def test_init_empty_state(self, history_manager):
        """Test initial empty state."""
        assert history_manager.commands == []
        assert history_manager.context == []
        assert history_manager._checkpoints == []

    def test_init_loads_existing_history(self, history_with_data):
        """Test loading existing history file."""
        assert len(history_with_data.commands) == 3
        assert "git status" in history_with_data.commands


# =============================================================================
# COMMAND HISTORY TESTS
# =============================================================================

class TestCommandHistory:
    """Tests for command history functionality."""

    def test_add_command(self, history_manager):
        """Test adding commands."""
        history_manager.add_command("git status")
        assert history_manager.commands == ["git status"]

    def test_add_multiple_commands(self, history_manager):
        """Test adding multiple commands."""
        history_manager.add_command("git status")
        history_manager.add_command("git add .")
        history_manager.add_command("git commit -m test")
        assert len(history_manager.commands) == 3

    def test_add_skips_duplicate_last(self, history_manager):
        """Test duplicate of last command is skipped."""
        history_manager.add_command("git status")
        history_manager.add_command("git status")
        assert len(history_manager.commands) == 1

    def test_add_allows_non_consecutive_duplicate(self, history_manager):
        """Test non-consecutive duplicate is allowed."""
        history_manager.add_command("git status")
        history_manager.add_command("git add .")
        history_manager.add_command("git status")
        assert len(history_manager.commands) == 3

    def test_add_empty_command_ignored(self, history_manager):
        """Test empty command is ignored."""
        history_manager.add_command("")
        assert history_manager.commands == []

    def test_add_command_persists(self, temp_paths):
        """Test command is persisted to file."""
        manager = HistoryManager(
            history_file=temp_paths["history_file"],
            session_dir=temp_paths["session_dir"]
        )
        manager.add_command("test command")

        # Reload and verify
        manager2 = HistoryManager(
            history_file=temp_paths["history_file"],
            session_dir=temp_paths["session_dir"]
        )
        assert "test command" in manager2.commands

    def test_search_history_empty_query(self, history_with_data):
        """Test search with empty query returns recent."""
        results = history_with_data.search_history("")
        assert len(results) <= 10

    def test_search_history_matching(self, history_with_data):
        """Test search finds matching commands."""
        results = history_with_data.search_history("git")
        assert len(results) > 0
        assert all("git" in cmd.lower() for cmd in results)

    def test_search_history_case_insensitive(self, history_with_data):
        """Test search is case insensitive."""
        results = history_with_data.search_history("GIT")
        assert len(results) > 0

    def test_search_history_limit(self, history_manager):
        """Test search respects limit."""
        for i in range(20):
            history_manager.add_command(f"test command {i}")

        results = history_manager.search_history("test", limit=5)
        assert len(results) == 5

    def test_search_history_no_match(self, history_with_data):
        """Test search with no matches."""
        results = history_with_data.search_history("nonexistent")
        assert results == []

    def test_get_recent(self, history_with_data):
        """Test getting recent commands."""
        recent = history_with_data.get_recent(2)
        assert len(recent) == 2

    def test_get_recent_more_than_available(self, history_manager):
        """Test getting more recent than available."""
        history_manager.add_command("only one")
        recent = history_manager.get_recent(10)
        assert len(recent) == 1

    def test_clear_history(self, history_with_data):
        """Test clearing history."""
        history_with_data.clear_history()
        assert history_with_data.commands == []


# =============================================================================
# CONVERSATION CONTEXT TESTS
# =============================================================================

class TestConversationContext:
    """Tests for conversation context management."""

    def test_add_context(self, history_manager):
        """Test adding context message."""
        history_manager.add_context("user", "Hello")
        assert len(history_manager.context) == 1
        assert history_manager.context[0]["role"] == "user"
        assert history_manager.context[0]["content"] == "Hello"

    def test_add_multiple_context(self, history_manager):
        """Test adding multiple context messages."""
        history_manager.add_context("user", "Hello")
        history_manager.add_context("assistant", "Hi!")
        history_manager.add_context("user", "How are you?")
        assert len(history_manager.context) == 3

    def test_context_limit(self, temp_paths):
        """Test context respects max_context limit."""
        manager = HistoryManager(
            max_context=3,
            history_file=temp_paths["history_file"],
            session_dir=temp_paths["session_dir"]
        )

        for i in range(5):
            manager.add_context("user", f"Message {i}")

        assert len(manager.context) == 3
        # Should keep most recent
        assert manager.context[0]["content"] == "Message 2"

    def test_get_context_returns_copy(self, history_manager):
        """Test get_context returns a copy."""
        history_manager.add_context("user", "Test")
        context = history_manager.get_context()
        context.append({"role": "modified", "content": "bad"})

        # Original should not be modified
        assert len(history_manager.context) == 1

    def test_clear_context(self, history_manager):
        """Test clearing context."""
        history_manager.add_context("user", "Test")
        history_manager.clear_context()
        assert history_manager.context == []


# =============================================================================
# SESSION PERSISTENCE TESTS
# =============================================================================

class TestSessionPersistence:
    """Tests for session save/load/list functionality."""

    def test_save_session_auto_id(self, history_manager):
        """Test saving session with auto-generated ID."""
        history_manager.add_context("user", "Test")
        session_id = history_manager.save_session()

        assert session_id is not None
        assert len(session_id) > 0

    def test_save_session_custom_id(self, history_manager):
        """Test saving session with custom ID."""
        session_id = history_manager.save_session("my_session")
        assert session_id == "my_session"

    def test_save_session_creates_file(self, history_manager, temp_paths):
        """Test saving creates session file."""
        session_id = history_manager.save_session("test_session")
        session_file = temp_paths["session_dir"] / "test_session.json"
        assert session_file.exists()

    def test_save_session_content(self, history_manager, temp_paths):
        """Test saved session contains correct data."""
        history_manager.add_context("user", "Hello")
        history_manager.add_context("assistant", "Hi!")
        history_manager.add_command("git status")

        session_id = history_manager.save_session("test")

        session_file = temp_paths["session_dir"] / "test.json"
        data = json.loads(session_file.read_text())

        assert data["session_id"] == "test"
        assert len(data["context"]) == 2
        assert "timestamp" in data
        assert data["version"] == "1.0"

    def test_load_session_by_id(self, history_with_data):
        """Test loading session by ID."""
        result = history_with_data.load_session("20250101_120000")

        assert result["session_id"] == "20250101_120000"
        assert result["message_count"] == 2

    def test_load_session_restores_context(self, history_with_data):
        """Test loading restores context."""
        history_with_data.clear_context()
        history_with_data.load_session("20250101_120000")

        assert len(history_with_data.context) == 2
        assert history_with_data.context[0]["content"] == "Hello"

    def test_load_session_most_recent(self, history_manager, temp_paths):
        """Test loading most recent session when no ID."""
        # Create two sessions
        history_manager.add_context("user", "First")
        history_manager.save_session("older")

        history_manager.clear_context()
        history_manager.add_context("user", "Second")
        history_manager.save_session("newer")

        # Clear and load without ID
        history_manager.clear_context()
        result = history_manager.load_session()

        assert history_manager.context[0]["content"] == "Second"

    def test_load_session_not_found(self, history_manager):
        """Test loading non-existent session."""
        with pytest.raises(ValueError, match="No sessions found"):
            history_manager.load_session("nonexistent")

    def test_load_session_no_sessions(self, history_manager):
        """Test loading when no sessions exist."""
        with pytest.raises(ValueError, match="No sessions found"):
            history_manager.load_session()

    def test_list_sessions_empty(self, history_manager):
        """Test listing when no sessions."""
        sessions = history_manager.list_sessions()
        assert sessions == []

    def test_list_sessions(self, history_with_data):
        """Test listing sessions."""
        sessions = history_with_data.list_sessions()

        assert len(sessions) == 1
        assert sessions[0]["session_id"] == "20250101_120000"
        assert sessions[0]["message_count"] == 2

    def test_list_sessions_limit(self, history_manager):
        """Test listing respects limit."""
        for i in range(5):
            history_manager.save_session(f"session_{i}")

        sessions = history_manager.list_sessions(limit=3)
        assert len(sessions) == 3

    def test_list_sessions_sorted_by_time(self, history_manager, temp_paths):
        """Test sessions sorted by modification time."""
        import time

        history_manager.save_session("first")
        time.sleep(0.1)
        history_manager.save_session("second")

        sessions = history_manager.list_sessions()

        # Most recent first
        assert sessions[0]["session_id"] == "second"

    def test_delete_session(self, history_with_data, temp_paths):
        """Test deleting a session."""
        result = history_with_data.delete_session("20250101_120000")

        assert result is True
        session_file = temp_paths["session_dir"] / "20250101_120000.json"
        assert not session_file.exists()

    def test_delete_session_not_found(self, history_manager):
        """Test deleting non-existent session."""
        result = history_manager.delete_session("nonexistent")
        assert result is False


# =============================================================================
# CHECKPOINT TESTS
# =============================================================================

class TestCheckpoints:
    """Tests for checkpoint system."""

    def test_create_checkpoint(self, history_manager):
        """Test creating a checkpoint."""
        history_manager.add_context("user", "Test")
        checkpoint = history_manager.create_checkpoint()

        assert checkpoint["index"] == 0
        assert "label" in checkpoint
        assert "timestamp" in checkpoint
        assert checkpoint["message_count"] == 1

    def test_create_checkpoint_custom_label(self, history_manager):
        """Test creating checkpoint with custom label."""
        checkpoint = history_manager.create_checkpoint("My Checkpoint")
        assert checkpoint["label"] == "My Checkpoint"

    def test_create_multiple_checkpoints(self, history_manager):
        """Test creating multiple checkpoints."""
        cp1 = history_manager.create_checkpoint()
        cp2 = history_manager.create_checkpoint()
        cp3 = history_manager.create_checkpoint()

        assert cp1["index"] == 0
        assert cp2["index"] == 1
        assert cp3["index"] == 2

    def test_checkpoint_limit(self, history_manager):
        """Test checkpoint limit prevents memory leak."""
        for i in range(25):
            history_manager.create_checkpoint(f"CP {i}")

        checkpoints = history_manager.get_checkpoints()
        assert len(checkpoints) == 20  # MAX_CHECKPOINTS

    def test_checkpoint_reindexing(self, history_manager):
        """Test checkpoints are re-indexed when limit reached."""
        for i in range(25):
            history_manager.create_checkpoint(f"CP {i}")

        checkpoints = history_manager.get_checkpoints()
        # Indices should be 0-19
        assert checkpoints[0]["index"] == 0
        assert checkpoints[-1]["index"] == 19

    def test_get_checkpoints_empty(self, history_manager):
        """Test getting checkpoints when none exist."""
        checkpoints = history_manager.get_checkpoints()
        assert checkpoints == []

    def test_get_checkpoints(self, history_manager):
        """Test getting checkpoint list."""
        history_manager.create_checkpoint("First")
        history_manager.create_checkpoint("Second")

        checkpoints = history_manager.get_checkpoints()

        assert len(checkpoints) == 2
        assert checkpoints[0]["label"] == "First"
        assert checkpoints[1]["label"] == "Second"

    def test_rewind_to_checkpoint(self, history_manager):
        """Test rewinding to checkpoint."""
        history_manager.add_context("user", "Message 1")
        history_manager.create_checkpoint("Before change")

        history_manager.add_context("user", "Message 2")
        history_manager.add_context("user", "Message 3")

        result = history_manager.rewind_to_checkpoint(0)

        assert result["success"] is True
        assert len(history_manager.context) == 1
        assert history_manager.context[0]["content"] == "Message 1"

    def test_rewind_invalid_index(self, history_manager):
        """Test rewinding to invalid index."""
        history_manager.create_checkpoint()

        with pytest.raises(ValueError, match="Invalid checkpoint index"):
            history_manager.rewind_to_checkpoint(5)

    def test_rewind_no_checkpoints(self, history_manager):
        """Test rewinding when no checkpoints."""
        with pytest.raises(ValueError, match="No checkpoints available"):
            history_manager.rewind_to_checkpoint(0)

    def test_rewind_negative_index(self, history_manager):
        """Test rewinding to negative index."""
        history_manager.create_checkpoint()

        with pytest.raises(ValueError, match="Invalid checkpoint index"):
            history_manager.rewind_to_checkpoint(-1)

    def test_clear_checkpoints(self, history_manager):
        """Test clearing checkpoints."""
        history_manager.create_checkpoint()
        history_manager.create_checkpoint()
        history_manager.clear_checkpoints()

        assert history_manager.get_checkpoints() == []


# =============================================================================
# STATISTICS TESTS
# =============================================================================

class TestStatistics:
    """Tests for statistics functionality."""

    def test_get_stats(self, history_manager, temp_paths):
        """Test getting statistics."""
        history_manager.add_command("test")
        history_manager.add_context("user", "hello")
        history_manager.create_checkpoint()

        stats = history_manager.get_stats()

        assert stats["command_count"] == 1
        assert stats["context_count"] == 1
        assert stats["checkpoint_count"] == 1
        assert stats["max_commands"] == 1000
        assert stats["max_context"] == 50
        assert stats["max_checkpoints"] == 20

    def test_stats_paths(self, history_manager, temp_paths):
        """Test stats include paths."""
        stats = history_manager.get_stats()

        assert str(temp_paths["history_file"]) in stats["history_file"]
        assert str(temp_paths["session_dir"]) in stats["session_dir"]


# =============================================================================
# EDGE CASES
# =============================================================================

class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_unicode_in_commands(self, history_manager):
        """Test unicode characters in commands."""
        history_manager.add_command("echo '世界 🎉'")
        assert "世界" in history_manager.commands[0]

    def test_unicode_in_context(self, history_manager):
        """Test unicode in context."""
        history_manager.add_context("user", "Hello 世界!")
        assert "世界" in history_manager.context[0]["content"]

    def test_special_characters_in_session_content(self, history_manager):
        """Test special characters in session."""
        history_manager.add_context("user", 'Test "quotes" and <tags>')
        session_id = history_manager.save_session()

        history_manager.clear_context()
        history_manager.load_session(session_id)

        assert '"quotes"' in history_manager.context[0]["content"]

    def test_very_long_command(self, history_manager):
        """Test very long command."""
        long_cmd = "a" * 10000
        history_manager.add_command(long_cmd)
        assert len(history_manager.commands[0]) == 10000

    def test_very_long_context(self, history_manager):
        """Test very long context message."""
        long_msg = "b" * 50000
        history_manager.add_context("user", long_msg)
        assert len(history_manager.context[0]["content"]) == 50000

    def test_many_commands(self, temp_paths):
        """Test many commands respect limit."""
        manager = HistoryManager(
            max_commands=100,
            history_file=temp_paths["history_file"],
            session_dir=temp_paths["session_dir"]
        )

        for i in range(150):
            manager.add_command(f"command {i}")

        # Should not exceed limit when saved
        manager2 = HistoryManager(
            max_commands=100,
            history_file=temp_paths["history_file"],
            session_dir=temp_paths["session_dir"]
        )
        assert len(manager2.commands) <= 100

    def test_corrupted_history_file(self, temp_paths):
        """Test graceful handling of corrupted history."""
        temp_paths["history_file"].write_bytes(b"\x00\xff\xfe")

        # Should not crash
        manager = HistoryManager(
            history_file=temp_paths["history_file"],
            session_dir=temp_paths["session_dir"]
        )
        assert manager.commands == []

    def test_corrupted_session_file(self, temp_paths):
        """Test handling corrupted session in list."""
        temp_paths["session_dir"].mkdir(parents=True, exist_ok=True)
        corrupt_file = temp_paths["session_dir"] / "corrupt.json"
        corrupt_file.write_text("not valid json {{{")

        manager = HistoryManager(
            history_file=temp_paths["history_file"],
            session_dir=temp_paths["session_dir"]
        )

        # Should skip corrupt files
        sessions = manager.list_sessions()
        assert len(sessions) == 0


# =============================================================================
# INTEGRATION TESTS
# =============================================================================

class TestIntegration:
    """Integration tests for HistoryManager."""

    def test_full_session_lifecycle(self, history_manager):
        """Test complete session lifecycle."""
        # Build up conversation
        history_manager.add_command("git status")
        history_manager.add_context("user", "Check git status")
        history_manager.add_context("assistant", "Here's the status...")
        history_manager.create_checkpoint("After status")

        # More conversation
        history_manager.add_command("git add .")
        history_manager.add_context("user", "Stage changes")
        history_manager.add_context("assistant", "Changes staged")

        # Save session
        session_id = history_manager.save_session()

        # Clear everything
        history_manager.clear_context()
        history_manager.clear_history()
        history_manager.clear_checkpoints()

        # Reload session
        history_manager.load_session(session_id)

        # Verify restoration
        assert len(history_manager.context) == 4
        assert history_manager.context[0]["content"] == "Check git status"

    def test_checkpoint_workflow(self, history_manager):
        """Test typical checkpoint workflow."""
        # Initial state
        history_manager.add_context("user", "Start")
        cp1 = history_manager.create_checkpoint("Start")

        # Make changes
        history_manager.add_context("user", "Middle 1")
        history_manager.add_context("user", "Middle 2")
        cp2 = history_manager.create_checkpoint("Middle")

        # More changes
        history_manager.add_context("user", "End 1")
        history_manager.add_context("user", "End 2")

        # Verify current state
        assert len(history_manager.context) == 5

        # Rewind to middle
        history_manager.rewind_to_checkpoint(cp2["index"])
        assert len(history_manager.context) == 3

        # Rewind to start
        history_manager.rewind_to_checkpoint(cp1["index"])
        assert len(history_manager.context) == 1
