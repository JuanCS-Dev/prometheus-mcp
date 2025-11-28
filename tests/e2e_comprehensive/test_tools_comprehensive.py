"""
Comprehensive E2E Tests: All Tools - NO MOCKS
==============================================

Tests every tool with real file operations, real git commands, real searches.
Edge cases, error conditions, boundary values.

Author: JuanCS Dev
Date: 2025-11-27
"""

import pytest
from pathlib import Path
import subprocess


class TestFileOperationsComprehensive:
    """Comprehensive file operations testing."""

    @pytest.mark.asyncio
    async def test_write_file_basic(self, temp_project):
        """Test basic file writing."""
        from jdev_cli.tools.file_ops import WriteFileTool

        tool = WriteFileTool()
        result = await tool._execute_validated(
            path=str(temp_project / "test.py"),
            content="print('hello')"
        )

        assert result.success
        assert (temp_project / "test.py").exists()
        assert (temp_project / "test.py").read_text() == "print('hello')"

    @pytest.mark.asyncio
    async def test_write_file_nested_dirs(self, temp_project):
        """Test writing to nested directories."""
        from jdev_cli.tools.file_ops import WriteFileTool

        tool = WriteFileTool()
        result = await tool._execute_validated(
            path=str(temp_project / "a" / "b" / "c" / "deep.py"),
            content="# deep nested file",
            create_dirs=True
        )

        assert result.success
        assert (temp_project / "a" / "b" / "c" / "deep.py").exists()

    @pytest.mark.asyncio
    async def test_write_file_large_content(self, temp_project):
        """Test writing large files (10MB)."""
        from jdev_cli.tools.file_ops import WriteFileTool

        tool = WriteFileTool()
        large_content = "x" * (10 * 1024 * 1024)  # 10MB

        result = await tool._execute_validated(
            path=str(temp_project / "large.txt"),
            content=large_content
        )

        assert result.success
        assert (temp_project / "large.txt").stat().st_size == 10 * 1024 * 1024

    @pytest.mark.asyncio
    async def test_write_file_unicode(self, temp_project):
        """Test writing unicode content."""
        from jdev_cli.tools.file_ops import WriteFileTool

        tool = WriteFileTool()
        unicode_content = "Hello 世界 🌍 Привет مرحبا"

        result = await tool._execute_validated(
            path=str(temp_project / "unicode.txt"),
            content=unicode_content
        )

        assert result.success
        assert (temp_project / "unicode.txt").read_text() == unicode_content

    @pytest.mark.asyncio
    async def test_write_file_special_chars(self, temp_project):
        """Test writing files with special characters in name."""
        from jdev_cli.tools.file_ops import WriteFileTool

        tool = WriteFileTool()
        # Note: some chars not allowed in filenames
        result = await tool._execute_validated(
            path=str(temp_project / "file-with_special.chars.txt"),
            content="test"
        )

        assert result.success

    @pytest.mark.asyncio
    async def test_read_file_basic(self, temp_project):
        """Test basic file reading."""
        from jdev_cli.tools.file_ops import ReadFileTool

        test_file = temp_project / "read.py"
        test_file.write_text("def foo():\n    pass")

        tool = ReadFileTool()
        result = await tool._execute_validated(path=str(test_file))

        assert result.success
        assert "def foo():" in result.data["content"]
        assert result.data["lines"] == 2

    @pytest.mark.asyncio
    async def test_read_file_line_range(self, temp_project):
        """Test reading specific line ranges."""
        from jdev_cli.tools.file_ops import ReadFileTool

        test_file = temp_project / "lines.txt"
        test_file.write_text("line1\nline2\nline3\nline4\nline5")

        tool = ReadFileTool()
        result = await tool._execute_validated(
            path=str(test_file),
            line_range=(2, 4)
        )

        assert result.success
        assert "line2" in result.data["content"]
        assert "line4" in result.data["content"]
        assert "line1" not in result.data["content"]

    @pytest.mark.asyncio
    async def test_read_file_empty(self, temp_project):
        """Test reading empty file."""
        from jdev_cli.tools.file_ops import ReadFileTool

        test_file = temp_project / "empty.txt"
        test_file.write_text("")

        tool = ReadFileTool()
        result = await tool._execute_validated(path=str(test_file))

        assert result.success
        assert result.data["content"] == ""

    @pytest.mark.asyncio
    async def test_read_file_nonexistent(self, temp_project):
        """Test reading non-existent file."""
        from jdev_cli.tools.file_ops import ReadFileTool

        tool = ReadFileTool()
        result = await tool._execute_validated(
            path=str(temp_project / "nonexistent.txt")
        )

        assert not result.success
        assert "not found" in result.error.lower()

    @pytest.mark.asyncio
    async def test_edit_file_single_replacement(self, temp_project):
        """Test single edit replacement."""
        from jdev_cli.tools.file_ops import EditFileTool

        test_file = temp_project / "edit.py"
        test_file.write_text("def old_name():\n    pass")

        tool = EditFileTool()
        result = await tool._execute_validated(
            path=str(test_file),
            edits=[{"search": "old_name", "replace": "new_name"}],
            preview=False,
            create_backup=False
        )

        assert result.success
        content = test_file.read_text()
        assert "new_name" in content
        assert "old_name" not in content

    @pytest.mark.asyncio
    async def test_edit_file_multiple_edits(self, temp_project):
        """Test multiple edits in sequence."""
        from jdev_cli.tools.file_ops import EditFileTool

        test_file = temp_project / "multi.py"
        test_file.write_text("a = 1\nb = 2\nc = 3")

        tool = EditFileTool()
        result = await tool._execute_validated(
            path=str(test_file),
            edits=[
                {"search": "a = 1", "replace": "a = 10"},
                {"search": "b = 2", "replace": "b = 20"},
            ],
            preview=False,
            create_backup=False
        )

        assert result.success
        content = test_file.read_text()
        assert "a = 10" in content
        assert "b = 20" in content

    @pytest.mark.asyncio
    async def test_edit_file_replace_all(self, temp_project):
        """Test replace_all flag."""
        from jdev_cli.tools.file_ops import EditFileTool

        test_file = temp_project / "replaceall.py"
        test_file.write_text("foo\nfoo\nfoo")

        tool = EditFileTool()
        result = await tool._execute_validated(
            path=str(test_file),
            edits=[{"search": "foo", "replace": "bar"}],
            replace_all=True,
            preview=False,
            create_backup=False
        )

        assert result.success
        content = test_file.read_text()
        assert content == "bar\nbar\nbar"

    @pytest.mark.asyncio
    async def test_edit_file_search_not_found(self, temp_project):
        """Test edit when search string not found."""
        from jdev_cli.tools.file_ops import EditFileTool

        test_file = temp_project / "notfound.py"
        test_file.write_text("hello world")

        tool = EditFileTool()
        result = await tool._execute_validated(
            path=str(test_file),
            edits=[{"search": "nonexistent", "replace": "something"}],
            preview=False,
            create_backup=False
        )

        assert not result.success
        assert "not found" in result.error.lower()

    @pytest.mark.asyncio
    async def test_edit_file_creates_backup(self, temp_project):
        """Test backup creation."""
        from jdev_cli.tools.file_ops import EditFileTool

        test_file = temp_project / "backup.py"
        original = "original content"
        test_file.write_text(original)

        tool = EditFileTool()
        result = await tool._execute_validated(
            path=str(test_file),
            edits=[{"search": "original", "replace": "modified"}],
            preview=False,
            create_backup=True
        )

        assert result.success
        # Check backup was created
        backup_dir = Path(".qwen_backups")
        assert backup_dir.exists()
        backups = list(backup_dir.glob("backup.py.*.bak"))
        assert len(backups) > 0

    @pytest.mark.asyncio
    async def test_list_directory_basic(self, temp_project):
        """Test basic directory listing."""
        from jdev_cli.tools.file_ops import ListDirectoryTool

        # Create some files
        (temp_project / "file1.py").write_text("")
        (temp_project / "file2.py").write_text("")
        (temp_project / "subdir").mkdir()

        tool = ListDirectoryTool()
        result = await tool._execute_validated(path=str(temp_project))

        assert result.success
        assert result.metadata["file_count"] == 2
        assert result.metadata["dir_count"] == 1

    @pytest.mark.asyncio
    async def test_list_directory_recursive(self, temp_project):
        """Test recursive directory listing."""
        from jdev_cli.tools.file_ops import ListDirectoryTool

        (temp_project / "a" / "b").mkdir(parents=True)
        (temp_project / "a" / "file1.py").write_text("")
        (temp_project / "a" / "b" / "file2.py").write_text("")

        tool = ListDirectoryTool()
        result = await tool._execute_validated(
            path=str(temp_project / "a"),
            recursive=True
        )

        assert result.success
        assert result.metadata["file_count"] >= 2

    @pytest.mark.asyncio
    async def test_list_directory_pattern(self, temp_project):
        """Test directory listing with pattern."""
        from jdev_cli.tools.file_ops import ListDirectoryTool

        (temp_project / "test.py").write_text("")
        (temp_project / "test.txt").write_text("")
        (temp_project / "data.json").write_text("")

        tool = ListDirectoryTool()
        result = await tool._execute_validated(
            path=str(temp_project),
            pattern="*.py"
        )

        assert result.success
        assert result.metadata["file_count"] == 1

    @pytest.mark.asyncio
    async def test_delete_file_to_trash(self, temp_project):
        """Test file deletion to trash."""
        from jdev_cli.tools.file_ops import DeleteFileTool

        test_file = temp_project / "delete_me.txt"
        test_file.write_text("delete this")

        tool = DeleteFileTool()
        result = await tool._execute_validated(
            path=str(test_file),
            permanent=False
        )

        assert result.success
        assert not test_file.exists()
        # Check file in trash
        trash_dir = Path(".trash")
        assert trash_dir.exists()

    @pytest.mark.asyncio
    async def test_delete_file_permanent(self, temp_project):
        """Test permanent file deletion."""
        from jdev_cli.tools.file_ops import DeleteFileTool

        test_file = temp_project / "permanent_delete.txt"
        test_file.write_text("gone forever")

        tool = DeleteFileTool()
        result = await tool._execute_validated(
            path=str(test_file),
            permanent=True
        )

        assert result.success
        assert not test_file.exists()


class TestSearchOperationsComprehensive:
    """Comprehensive search operations testing."""

    @pytest.mark.asyncio
    async def test_search_basic_pattern(self, sample_python_project):
        """Test basic pattern search."""
        from jdev_cli.tools.search import SearchFilesTool

        tool = SearchFilesTool()
        result = await tool._execute_validated(
            pattern="def ",
            path=str(sample_python_project)
        )

        assert result.success
        matches = result.data.get("matches", [])
        assert len(matches) > 0

    @pytest.mark.asyncio
    async def test_search_case_insensitive(self, temp_project):
        """Test case-insensitive search."""
        from jdev_cli.tools.search import SearchFilesTool

        (temp_project / "test.txt").write_text("Hello\nHELLO\nhello")

        tool = SearchFilesTool()
        result = await tool._execute_validated(
            pattern="hello",
            path=str(temp_project),
            ignore_case=True
        )

        assert result.success
        matches = result.data.get("matches", [])
        assert len(matches) == 3

    @pytest.mark.asyncio
    async def test_search_case_sensitive(self, temp_project):
        """Test case-sensitive search."""
        from jdev_cli.tools.search import SearchFilesTool

        (temp_project / "test.txt").write_text("Hello\nHELLO\nhello")

        tool = SearchFilesTool()
        result = await tool._execute_validated(
            pattern="hello",
            path=str(temp_project),
            ignore_case=False
        )

        assert result.success
        matches = result.data.get("matches", [])
        assert len(matches) == 1

    @pytest.mark.asyncio
    async def test_search_with_file_pattern(self, temp_project):
        """Test search with file pattern filter."""
        from jdev_cli.tools.search import SearchFilesTool

        (temp_project / "test.py").write_text("def foo(): pass")
        (temp_project / "test.txt").write_text("def foo(): pass")

        tool = SearchFilesTool()
        result = await tool._execute_validated(
            pattern="def foo",
            path=str(temp_project),
            file_pattern="*.py"
        )

        assert result.success
        matches = result.data.get("matches", [])
        assert len(matches) == 1
        assert matches[0]["file"].endswith(".py")

    @pytest.mark.asyncio
    async def test_search_regex_pattern(self, temp_project):
        """Test regex pattern search."""
        from jdev_cli.tools.search import SearchFilesTool

        (temp_project / "code.py").write_text("def func1():\n    pass\ndef func2():\n    pass")

        tool = SearchFilesTool()
        result = await tool._execute_validated(
            pattern=r"def func",
            path=str(temp_project)
        )

        assert result.success
        matches = result.data.get("matches", [])
        assert len(matches) >= 2  # At least 2 matches

    @pytest.mark.asyncio
    async def test_search_max_results(self, temp_project):
        """Test max results limit."""
        from jdev_cli.tools.search import SearchFilesTool

        content = "\n".join([f"line {i}" for i in range(100)])
        (temp_project / "many.txt").write_text(content)

        tool = SearchFilesTool()
        result = await tool._execute_validated(
            pattern="line",
            path=str(temp_project),
            max_results=10
        )

        assert result.success
        matches = result.data.get("matches", [])
        assert len(matches) <= 10

    @pytest.mark.asyncio
    async def test_search_no_matches(self, temp_project):
        """Test search with no matches."""
        from jdev_cli.tools.search import SearchFilesTool

        (temp_project / "test.txt").write_text("hello world")

        tool = SearchFilesTool()
        result = await tool._execute_validated(
            pattern="nonexistent_pattern_xyz",
            path=str(temp_project)
        )

        assert result.success
        matches = result.data.get("matches", [])
        assert len(matches) == 0

    @pytest.mark.asyncio
    async def test_directory_tree_basic(self, temp_project):
        """Test basic directory tree."""
        from jdev_cli.tools.search import GetDirectoryTreeTool

        (temp_project / "a").mkdir()
        (temp_project / "b").mkdir()
        (temp_project / "a" / "file.py").write_text("")

        tool = GetDirectoryTreeTool()
        result = await tool._execute_validated(path=str(temp_project))

        assert result.success
        assert "a/" in result.data
        assert "b/" in result.data

    @pytest.mark.asyncio
    async def test_directory_tree_max_depth(self, temp_project):
        """Test directory tree with depth limit."""
        from jdev_cli.tools.search import GetDirectoryTreeTool

        (temp_project / "a" / "b" / "c" / "d").mkdir(parents=True)

        tool = GetDirectoryTreeTool()
        result = await tool._execute_validated(
            path=str(temp_project),
            max_depth=2
        )

        assert result.success
        # Should not include deep nested dirs


class TestGitOperationsComprehensive:
    """Comprehensive git operations testing."""

    @pytest.mark.asyncio
    async def test_git_status_clean_repo(self, temp_project):
        """Test git status on clean repo."""
        from jdev_cli.tools.git_ops import GitStatusTool

        # Initialize git repo
        subprocess.run(["git", "init"], cwd=temp_project, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=temp_project)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=temp_project)

        tool = GitStatusTool()
        result = await tool._execute_validated(path=str(temp_project))

        assert result.success
        assert "branch" in result.data

    @pytest.mark.asyncio
    async def test_git_status_with_changes(self, temp_project):
        """Test git status with modifications."""
        from jdev_cli.tools.git_ops import GitStatusTool

        # Setup git
        subprocess.run(["git", "init"], cwd=temp_project, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=temp_project)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=temp_project)

        # Create and commit a file
        test_file = temp_project / "test.py"
        test_file.write_text("original")
        subprocess.run(["git", "add", "."], cwd=temp_project)
        subprocess.run(["git", "commit", "-m", "initial"], cwd=temp_project)

        # Modify it
        test_file.write_text("modified")

        tool = GitStatusTool()
        result = await tool._execute_validated(path=str(temp_project))

        assert result.success
        assert len(result.data["modified"]) > 0

    @pytest.mark.asyncio
    async def test_git_status_untracked_files(self, temp_project):
        """Test git status with untracked files."""
        from jdev_cli.tools.git_ops import GitStatusTool

        subprocess.run(["git", "init"], cwd=temp_project, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=temp_project)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=temp_project)

        (temp_project / "untracked.py").write_text("new file")

        tool = GitStatusTool()
        result = await tool._execute_validated(path=str(temp_project))

        assert result.success
        assert len(result.data["untracked"]) > 0

    @pytest.mark.asyncio
    async def test_git_diff_no_changes(self, temp_project):
        """Test git diff with no changes."""
        from jdev_cli.tools.git_ops import GitDiffTool

        subprocess.run(["git", "init"], cwd=temp_project, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=temp_project)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=temp_project)

        tool = GitDiffTool()
        result = await tool._execute_validated(path=str(temp_project))

        assert result.success
        assert not result.data["has_changes"]

    @pytest.mark.asyncio
    async def test_git_diff_with_changes(self, temp_project):
        """Test git diff with modifications."""
        from jdev_cli.tools.git_ops import GitDiffTool

        subprocess.run(["git", "init"], cwd=temp_project, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=temp_project)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=temp_project)

        test_file = temp_project / "test.py"
        test_file.write_text("original")
        subprocess.run(["git", "add", "."], cwd=temp_project)
        subprocess.run(["git", "commit", "-m", "initial"], cwd=temp_project)

        test_file.write_text("modified content")

        tool = GitDiffTool()
        result = await tool._execute_validated(path=str(temp_project))

        assert result.success
        assert result.data["has_changes"]
        assert "modified" in result.data["diff"]

    @pytest.mark.asyncio
    async def test_git_diff_staged(self, temp_project):
        """Test git diff for staged changes."""
        from jdev_cli.tools.git_ops import GitDiffTool

        subprocess.run(["git", "init"], cwd=temp_project, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=temp_project)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=temp_project)

        test_file = temp_project / "test.py"
        test_file.write_text("original")
        subprocess.run(["git", "add", "."], cwd=temp_project)
        subprocess.run(["git", "commit", "-m", "initial"], cwd=temp_project)

        test_file.write_text("staged content")
        subprocess.run(["git", "add", "test.py"], cwd=temp_project)

        tool = GitDiffTool()
        result = await tool._execute_validated(
            path=str(temp_project),
            staged=True
        )

        assert result.success
        assert result.data["has_changes"]

    @pytest.mark.asyncio
    async def test_git_diff_specific_file(self, temp_project):
        """Test git diff for specific file."""
        from jdev_cli.tools.git_ops import GitDiffTool

        subprocess.run(["git", "init"], cwd=temp_project, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=temp_project)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=temp_project)

        file1 = temp_project / "file1.py"
        file2 = temp_project / "file2.py"
        file1.write_text("content1")
        file2.write_text("content2")
        subprocess.run(["git", "add", "."], cwd=temp_project)
        subprocess.run(["git", "commit", "-m", "initial"], cwd=temp_project)

        file1.write_text("modified1")
        file2.write_text("modified2")

        tool = GitDiffTool()
        result = await tool._execute_validated(
            path=str(temp_project),
            file="file1.py"
        )

        assert result.success
        assert "file1.py" in result.data["diff"]
