"""
Tests for preview system.

Boris Cherny: "Tests or it didn't happen."
"""

import pytest
import tempfile
from pathlib import Path

from jdev_cli.tools.preview_mixin import (
    PreviewMixin,
    PreviewableWriteTool,
    get_undo_manager,
    undo_last_operation
)


class TestPreviewMixin:
    """Test preview mixin functionality."""

    def test_preview_mixin_init(self):
        """Test mixin initialization."""
        mixin = PreviewMixin()
        assert mixin.enable_preview is True
        assert len(mixin._undo_stack) == 0

    def test_get_file_content_safe_existing(self):
        """Test reading existing file."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as tmp:
            tmp.write("test content")
            tmp.flush()

            try:
                mixin = PreviewMixin()
                content = mixin._get_file_content_safe(tmp.name)
                assert content == "test content"
            finally:
                Path(tmp.name).unlink()

    def test_get_file_content_safe_missing(self):
        """Test reading non-existent file returns empty string."""
        mixin = PreviewMixin()
        content = mixin._get_file_content_safe("/this/does/not/exist.txt")
        assert content == ""

    def test_backup_for_undo(self):
        """Test backup creation."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as tmp:
            tmp.write("original content")
            tmp.flush()

            try:
                mixin = PreviewMixin()
                mixin._backup_for_undo(tmp.name)

                assert mixin.can_undo()
                assert len(mixin._undo_stack) == 1

                path, content = mixin._undo_stack[0]
                assert path == tmp.name
                assert content == "original content"
            finally:
                Path(tmp.name).unlink()

    def test_undo_stack_limit(self):
        """Test undo stack is limited to 10 items."""
        mixin = PreviewMixin()

        # Add 15 items
        for i in range(15):
            mixin._undo_stack.append((f"/file{i}.txt", f"content{i}"))

        # Should keep only last 10
        assert len(mixin._undo_stack) == 10
        assert mixin._undo_stack[0] == ("/file5.txt", "content5")
        assert mixin._undo_stack[-1] == ("/file14.txt", "content14")

    def test_undo_last_success(self):
        """Test successful undo."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as tmp:
            tmp.write("original")
            tmp.flush()

            try:
                mixin = PreviewMixin()
                mixin._backup_for_undo(tmp.name)

                # Modify file
                Path(tmp.name).write_text("modified")

                # Undo
                result = mixin.undo_last()
                assert result is not None
                assert "Reverted" in result

                # Verify content restored
                assert Path(tmp.name).read_text() == "original"
            finally:
                Path(tmp.name).unlink()

    def test_undo_last_empty_stack(self):
        """Test undo with empty stack."""
        mixin = PreviewMixin()
        result = mixin.undo_last()
        assert result is None


class TestPreviewableWriteTool:
    """Test previewable write tool."""

    def test_write_without_preview(self):
        """Test write without preview (auto-confirm)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tool = PreviewableWriteTool()
            path = Path(tmpdir) / "test.txt"

            result = tool.execute(
                path=str(path),
                content="test content",
                preview=False  # Disable preview for test
            )

            assert result['success'] is True
            assert path.exists()
            assert path.read_text() == "test content"

    def test_write_new_file(self):
        """Test writing new file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tool = PreviewableWriteTool()
            path = Path(tmpdir) / "new.txt"

            result = tool.execute(
                path=str(path),
                content="new content",
                preview=False
            )

            assert result['success'] is True
            assert "Written" in result['message']
            assert path.exists()

    def test_write_creates_parent_dirs(self):
        """Test write creates parent directories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tool = PreviewableWriteTool()
            path = Path(tmpdir) / "deep" / "nested" / "file.txt"

            result = tool.execute(
                path=str(path),
                content="deep content",
                preview=False
            )

            assert result['success'] is True
            assert path.exists()
            assert path.read_text() == "deep content"

    def test_write_with_undo(self):
        """Test write enables undo."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tool = PreviewableWriteTool()
            path = Path(tmpdir) / "test.txt"

            # Create initial file
            path.write_text("original")

            # Modify with tool
            result = tool.execute(
                path=str(path),
                content="modified",
                preview=False
            )

            assert result['success'] is True
            assert result['can_undo'] is True

            # Verify can undo
            undo_result = tool.undo_last()
            assert undo_result is not None
            assert path.read_text() == "original"


class TestUndoManager:
    """Test global undo manager."""

    def test_get_undo_manager_singleton(self):
        """Test undo manager is singleton."""
        manager1 = get_undo_manager()
        manager2 = get_undo_manager()
        assert manager1 is manager2

    def test_undo_last_operation_global(self):
        """Test global undo operation."""
        manager = get_undo_manager()
        manager._undo_stack.clear()  # Reset

        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as tmp:
            tmp.write("test")
            tmp.flush()

            try:
                manager._backup_for_undo(tmp.name)
                Path(tmp.name).write_text("modified")

                result = undo_last_operation()
                assert result is not None
                assert "Reverted" in result
            finally:
                Path(tmp.name).unlink()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
