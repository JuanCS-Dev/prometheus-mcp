"""Tests for hook events enumeration."""

from jdev_cli.hooks import HookEvent, HookPriority


class TestHookEvent:
    """Test suite for HookEvent enum."""

    def test_event_values(self):
        """Test that all events have correct string values."""
        assert HookEvent.POST_WRITE.value == "post_write"
        assert HookEvent.POST_EDIT.value == "post_edit"
        assert HookEvent.POST_DELETE.value == "post_delete"
        assert HookEvent.PRE_COMMIT.value == "pre_commit"

    def test_file_operations(self):
        """Test file_operations class method."""
        file_ops = HookEvent.file_operations()
        assert len(file_ops) == 3
        assert HookEvent.POST_WRITE in file_ops
        assert HookEvent.POST_EDIT in file_ops
        assert HookEvent.POST_DELETE in file_ops
        assert HookEvent.PRE_COMMIT not in file_ops

    def test_git_operations(self):
        """Test git_operations class method."""
        git_ops = HookEvent.git_operations()
        assert len(git_ops) == 1
        assert HookEvent.PRE_COMMIT in git_ops

    def test_string_representation(self):
        """Test __str__ returns correct value."""
        assert str(HookEvent.POST_WRITE) == "post_write"
        assert str(HookEvent.PRE_COMMIT) == "pre_commit"


class TestHookPriority:
    """Test suite for HookPriority enum."""

    def test_priority_values(self):
        """Test priority numeric values."""
        assert HookPriority.CRITICAL.value == 1000
        assert HookPriority.HIGH.value == 500
        assert HookPriority.NORMAL.value == 100
        assert HookPriority.LOW.value == 10

    def test_priority_comparison(self):
        """Test priority comparison (higher value = higher priority)."""
        assert HookPriority.CRITICAL > HookPriority.HIGH
        assert HookPriority.HIGH > HookPriority.NORMAL
        assert HookPriority.NORMAL > HookPriority.LOW

        # Ensure sorting works correctly
        priorities = [
            HookPriority.LOW,
            HookPriority.CRITICAL,
            HookPriority.NORMAL,
            HookPriority.HIGH
        ]
        sorted_priorities = sorted(priorities, reverse=True)
        assert sorted_priorities == [
            HookPriority.CRITICAL,
            HookPriority.HIGH,
            HookPriority.NORMAL,
            HookPriority.LOW
        ]
