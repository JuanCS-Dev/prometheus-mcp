"""Tests for hook execution context."""

from pathlib import Path
from datetime import datetime

from jdev_cli.hooks import HookContext


class TestHookContext:
    """Test suite for HookContext."""

    def test_context_creation(self):
        """Test basic context creation."""
        file_path = Path("src/utils/helper.py")
        ctx = HookContext(
            file_path=file_path,
            event_name="post_write",
            project_name="test-project"
        )

        assert ctx.file_path == file_path
        assert ctx.event_name == "post_write"
        assert ctx.project_name == "test-project"
        assert isinstance(ctx.timestamp, datetime)

    def test_file_property(self):
        """Test file property returns full path as string."""
        ctx = HookContext(Path("src/test.py"), "post_write")
        assert ctx.file == "src/test.py"

    def test_file_name_property(self):
        """Test file_name property returns name with extension."""
        ctx = HookContext(Path("src/utils/helper.py"), "post_write")
        assert ctx.file_name == "helper.py"

    def test_file_stem_property(self):
        """Test file_stem property returns name without extension."""
        ctx = HookContext(Path("src/utils/helper.py"), "post_write")
        assert ctx.file_stem == "helper"

    def test_file_extension_property(self):
        """Test file_extension property returns extension without dot."""
        ctx = HookContext(Path("src/utils/helper.py"), "post_write")
        assert ctx.file_extension == "py"

        ctx2 = HookContext(Path("README.md"), "post_write")
        assert ctx2.file_extension == "md"

    def test_dir_property(self):
        """Test dir property returns directory path."""
        ctx = HookContext(Path("src/utils/helper.py"), "post_write")
        assert ctx.dir == "src/utils"

    def test_relative_path_property(self):
        """Test relative_path property."""
        cwd = Path("/home/user/project")
        file_path = Path("/home/user/project/src/test.py")

        ctx = HookContext(
            file_path=file_path,
            event_name="post_write",
            cwd=cwd
        )

        assert ctx.relative_path == "src/test.py"

    def test_relative_path_outside_cwd(self):
        """Test relative_path when file is outside cwd."""
        cwd = Path("/home/user/project")
        file_path = Path("/tmp/test.py")

        ctx = HookContext(
            file_path=file_path,
            event_name="post_write",
            cwd=cwd
        )

        # Should return absolute path when not relative to cwd
        assert ctx.relative_path == str(file_path)

    def test_get_variables(self):
        """Test get_variables returns all substitution variables."""
        ctx = HookContext(
            file_path=Path("src/utils/helper.py"),
            event_name="post_write",
            project_name="my-project",
            metadata={"custom": "value"}
        )

        variables = ctx.get_variables()

        assert variables["file"] == "src/utils/helper.py"
        assert variables["file_name"] == "helper.py"
        assert variables["file_stem"] == "helper"
        assert variables["file_extension"] == "py"
        assert variables["dir"] == "src/utils"
        assert variables["project_name"] == "my-project"
        assert variables["event"] == "post_write"
        assert variables["custom"] == "value"

    def test_metadata_in_variables(self):
        """Test that metadata is included in variables."""
        ctx = HookContext(
            file_path=Path("test.py"),
            event_name="post_write",
            metadata={"branch": "main", "commit": "abc123"}
        )

        variables = ctx.get_variables()
        assert variables["branch"] == "main"
        assert variables["commit"] == "abc123"

    def test_empty_metadata(self):
        """Test context with empty metadata."""
        ctx = HookContext(Path("test.py"), "post_write")
        assert ctx.metadata == {}

        variables = ctx.get_variables()
        assert "file" in variables
        assert "event" in variables
