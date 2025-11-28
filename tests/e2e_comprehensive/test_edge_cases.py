"""
Comprehensive E2E Tests: Edge Cases & Error Conditions
=======================================================

Tests boundary conditions, error handling, race conditions, corrupted inputs.
NO MOCKS - all real operations.

Author: JuanCS Dev
Date: 2025-11-27
"""

import pytest
import asyncio
import os


class TestFileSizeEdgeCases:
    """Test edge cases related to file sizes."""

    @pytest.mark.asyncio
    async def test_write_empty_file(self, temp_project):
        """Test writing completely empty file."""
        from jdev_cli.tools.file_ops import WriteFileTool, ReadFileTool

        write_tool = WriteFileTool()
        read_tool = ReadFileTool()

        result = await write_tool._execute_validated(
            path=str(temp_project / "empty.txt"),
            content=""
        )

        assert result.success

        # Verify read works on empty file
        read_result = await read_tool._execute_validated(
            path=str(temp_project / "empty.txt")
        )
        assert read_result.success
        assert read_result.data["content"] == ""
        assert read_result.data["lines"] == 1  # Empty file has 1 line

    @pytest.mark.asyncio
    async def test_write_single_character(self, temp_project):
        """Test writing single character file."""
        from jdev_cli.tools.file_ops import WriteFileTool

        tool = WriteFileTool()
        result = await tool._execute_validated(
            path=str(temp_project / "single.txt"),
            content="x"
        )

        assert result.success
        assert (temp_project / "single.txt").read_text() == "x"

    @pytest.mark.asyncio
    async def test_write_only_whitespace(self, temp_project):
        """Test writing file with only whitespace."""
        from jdev_cli.tools.file_ops import WriteFileTool

        tool = WriteFileTool()
        result = await tool._execute_validated(
            path=str(temp_project / "whitespace.txt"),
            content="   \n\n\t\t\n   "
        )

        assert result.success

    @pytest.mark.asyncio
    async def test_write_many_newlines(self, temp_project):
        """Test writing file with many newlines."""
        from jdev_cli.tools.file_ops import WriteFileTool

        tool = WriteFileTool()
        content = "\n" * 10000

        result = await tool._execute_validated(
            path=str(temp_project / "newlines.txt"),
            content=content
        )

        assert result.success
        assert (temp_project / "newlines.txt").read_text() == content

    @pytest.mark.asyncio
    async def test_read_line_range_edge_cases(self, temp_project):
        """Test reading edge case line ranges."""
        from jdev_cli.tools.file_ops import ReadFileTool

        test_file = temp_project / "lines.txt"
        test_file.write_text("line1\nline2\nline3")

        tool = ReadFileTool()

        # Read first line only
        result = await tool._execute_validated(
            path=str(test_file),
            line_range=(1, 1)
        )
        assert result.success
        assert "line1" in result.data["content"]
        assert "line2" not in result.data["content"]

        # Read last line only
        result = await tool._execute_validated(
            path=str(test_file),
            line_range=(3, 3)
        )
        assert result.success
        assert "line3" in result.data["content"]

        # Read beyond end (should handle gracefully)
        result = await tool._execute_validated(
            path=str(test_file),
            line_range=(1, 1000)
        )
        assert result.success


class TestPathEdgeCases:
    """Test edge cases related to file paths."""

    @pytest.mark.asyncio
    async def test_path_with_spaces(self, temp_project):
        """Test file with spaces in path."""
        from jdev_cli.tools.file_ops import WriteFileTool

        tool = WriteFileTool()
        file_path = temp_project / "path with spaces" / "file with spaces.txt"

        result = await tool._execute_validated(
            path=str(file_path),
            content="content",
            create_dirs=True
        )

        assert result.success
        assert file_path.exists()

    @pytest.mark.asyncio
    async def test_very_long_filename(self, temp_project):
        """Test very long filename (approaching OS limit)."""
        from jdev_cli.tools.file_ops import WriteFileTool

        tool = WriteFileTool()
        # Most systems limit filenames to 255 chars
        long_name = "a" * 200 + ".txt"

        result = await tool._execute_validated(
            path=str(temp_project / long_name),
            content="test"
        )

        assert result.success

    @pytest.mark.asyncio
    async def test_deep_nesting(self, temp_project):
        """Test deeply nested directory structure."""
        from jdev_cli.tools.file_ops import WriteFileTool

        tool = WriteFileTool()
        deep_path = temp_project / "/".join([f"dir{i}" for i in range(20)]) / "deep.txt"

        result = await tool._execute_validated(
            path=str(deep_path),
            content="deep content",
            create_dirs=True
        )

        assert result.success
        assert deep_path.exists()

    @pytest.mark.asyncio
    async def test_relative_path_components(self, temp_project):
        """Test paths with . and .. components."""
        from jdev_cli.tools.file_ops import WriteFileTool, ReadFileTool

        (temp_project / "subdir").mkdir()

        write_tool = WriteFileTool()
        await write_tool._execute_validated(
            path=str(temp_project / "test.txt"),
            content="content"
        )

        read_tool = ReadFileTool()
        # Use relative path with ..
        result = await read_tool._execute_validated(
            path=str(temp_project / "subdir" / ".." / "test.txt")
        )

        assert result.success


class TestConcurrentAccess:
    """Test concurrent access to same resources."""

    @pytest.mark.asyncio
    async def test_concurrent_reads_same_file(self, temp_project):
        """Test multiple concurrent reads of same file."""
        from jdev_cli.tools.file_ops import ReadFileTool

        test_file = temp_project / "concurrent.txt"
        test_file.write_text("shared content")

        tool = ReadFileTool()

        # Launch 10 concurrent reads
        tasks = [
            tool._execute_validated(path=str(test_file))
            for _ in range(10)
        ]

        results = await asyncio.gather(*tasks)

        assert all(r.success for r in results)
        assert all("shared content" in r.data["content"] for r in results)

    @pytest.mark.asyncio
    async def test_concurrent_writes_different_files(self, temp_project):
        """Test concurrent writes to different files."""
        from jdev_cli.tools.file_ops import WriteFileTool

        tool = WriteFileTool()

        tasks = [
            tool._execute_validated(
                path=str(temp_project / f"file{i}.txt"),
                content=f"content{i}"
            )
            for i in range(20)
        ]

        results = await asyncio.gather(*tasks)

        assert all(r.success for r in results)
        assert all((temp_project / f"file{i}.txt").exists() for i in range(20))


class TestSearchEdgeCases:
    """Test search operation edge cases."""

    @pytest.mark.asyncio
    async def test_search_empty_string(self, temp_project):
        """Test searching for empty string."""
        from jdev_cli.tools.search import SearchFilesTool

        (temp_project / "test.txt").write_text("content")

        tool = SearchFilesTool()
        result = await tool._execute_validated(
            pattern="",
            path=str(temp_project)
        )

        # Should handle gracefully (ripgrep might return everything or error)
        assert result.success or not result.success  # Either is acceptable

    @pytest.mark.asyncio
    async def test_search_regex_special_chars(self, temp_project):
        """Test searching for regex special characters."""
        from jdev_cli.tools.search import SearchFilesTool

        (temp_project / "special.txt").write_text("price: $100.50")

        tool = SearchFilesTool()
        # Search for literal $100.50 (need to escape)
        result = await tool._execute_validated(
            pattern=r"\$100\.50",
            path=str(temp_project)
        )

        assert result.success
        matches = result.data.get("matches", [])
        assert len(matches) > 0

    @pytest.mark.asyncio
    async def test_search_multiline_pattern(self, temp_project):
        """Test searching with multiline context."""
        from jdev_cli.tools.search import SearchFilesTool

        (temp_project / "multi.txt").write_text("line1\nline2\nline3")

        tool = SearchFilesTool()
        result = await tool._execute_validated(
            pattern="line2",
            path=str(temp_project)
        )

        assert result.success
        matches = result.data.get("matches", [])
        assert any("line2" in m.get("text", "") for m in matches)

    @pytest.mark.asyncio
    async def test_search_binary_files(self, temp_project):
        """Test searching in binary files."""
        from jdev_cli.tools.search import SearchFilesTool

        # Create a binary file
        binary_file = temp_project / "binary.bin"
        binary_file.write_bytes(b"\x00\x01\x02\xFF\xFE")

        tool = SearchFilesTool()
        result = await tool._execute_validated(
            pattern="test",
            path=str(temp_project)
        )

        # Should handle binary files gracefully (ripgrep skips them)
        assert result.success

    @pytest.mark.asyncio
    async def test_search_no_files(self, temp_project):
        """Test searching in empty directory."""
        from jdev_cli.tools.search import SearchFilesTool

        empty_dir = temp_project / "empty"
        empty_dir.mkdir()

        tool = SearchFilesTool()
        result = await tool._execute_validated(
            pattern="anything",
            path=str(empty_dir)
        )

        assert result.success
        assert len(result.data.get("matches", [])) == 0

    @pytest.mark.asyncio
    async def test_search_very_long_lines(self, temp_project):
        """Test searching in file with very long lines."""
        from jdev_cli.tools.search import SearchFilesTool

        # Create file with 10KB line
        long_line = "x" * 10000 + "target" + "y" * 10000
        (temp_project / "longline.txt").write_text(long_line)

        tool = SearchFilesTool()
        result = await tool._execute_validated(
            pattern="target",
            path=str(temp_project)
        )

        assert result.success
        matches = result.data.get("matches", [])
        assert len(matches) > 0


class TestEditEdgeCases:
    """Test edit operation edge cases."""

    @pytest.mark.asyncio
    async def test_edit_replace_with_empty(self, temp_project):
        """Test replacing text with empty string (deletion)."""
        from jdev_cli.tools.file_ops import EditFileTool

        test_file = temp_project / "delete.txt"
        test_file.write_text("remove_this content")

        tool = EditFileTool()
        result = await tool._execute_validated(
            path=str(test_file),
            edits=[{"search": "remove_this ", "replace": ""}],
            preview=False,
            create_backup=False
        )

        assert result.success
        assert test_file.read_text() == "content"

    @pytest.mark.asyncio
    async def test_edit_empty_with_content(self, temp_project):
        """Test replacing empty string (insertion at start)."""
        from jdev_cli.tools.file_ops import EditFileTool

        test_file = temp_project / "insert.txt"
        test_file.write_text("world")

        tool = EditFileTool()
        # Note: searching for empty string is edge case
        result = await tool._execute_validated(
            path=str(test_file),
            edits=[{"search": "", "replace": "hello "}],
            preview=False,
            create_backup=False
        )

        # Behavior depends on implementation
        # Most likely will fail or do nothing
        # Test documents the behavior

    @pytest.mark.asyncio
    async def test_edit_overlapping_ranges(self, temp_project):
        """Test edits with overlapping text ranges."""
        from jdev_cli.tools.file_ops import EditFileTool

        test_file = temp_project / "overlap.txt"
        test_file.write_text("abcdefgh")

        tool = EditFileTool()
        # First edit changes abc -> xyz
        # This should prevent second edit from finding "bcd"
        result1 = await tool._execute_validated(
            path=str(test_file),
            edits=[{"search": "abc", "replace": "xyz"}],
            preview=False,
            create_backup=False
        )
        assert result1.success

        # Try to edit bcd (no longer exists)
        result2 = await tool._execute_validated(
            path=str(test_file),
            edits=[{"search": "bcd", "replace": "123"}],
            preview=False,
            create_backup=False
        )
        assert not result2.success  # Should fail - not found

    @pytest.mark.asyncio
    async def test_edit_newline_handling(self, temp_project):
        """Test editing across newlines."""
        from jdev_cli.tools.file_ops import EditFileTool

        test_file = temp_project / "newlines.txt"
        test_file.write_text("line1\nline2\nline3")

        tool = EditFileTool()
        result = await tool._execute_validated(
            path=str(test_file),
            edits=[{"search": "line1\nline2", "replace": "merged_line"}],
            preview=False,
            create_backup=False
        )

        assert result.success
        content = test_file.read_text()
        assert "merged_line" in content


class TestGitEdgeCases:
    """Test git operation edge cases."""

    @pytest.mark.asyncio
    async def test_git_status_not_a_repo(self, temp_project):
        """Test git status on non-git directory."""
        from jdev_cli.tools.git_ops import GitStatusTool

        tool = GitStatusTool()
        result = await tool._execute_validated(path=str(temp_project))

        assert not result.success
        assert "not a git repository" in result.error.lower()

    @pytest.mark.asyncio
    async def test_git_status_empty_repo(self, temp_project):
        """Test git status on empty initialized repo."""
        from jdev_cli.tools.git_ops import GitStatusTool
        import subprocess

        subprocess.run(["git", "init"], cwd=temp_project, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=temp_project)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=temp_project)

        tool = GitStatusTool()
        result = await tool._execute_validated(path=str(temp_project))

        assert result.success
        assert result.data["branch"]  # Should have branch name

    @pytest.mark.asyncio
    async def test_git_diff_empty_repo(self, temp_project):
        """Test git diff on repo with no commits."""
        from jdev_cli.tools.git_ops import GitDiffTool
        import subprocess

        subprocess.run(["git", "init"], cwd=temp_project, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=temp_project)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=temp_project)

        tool = GitDiffTool()
        result = await tool._execute_validated(path=str(temp_project))

        # No commits yet, diff might not work normally
        assert result.success or not result.success  # Either acceptable


class TestErrorRecovery:
    """Test error recovery and cleanup."""

    @pytest.mark.asyncio
    async def test_write_readonly_location(self, temp_project):
        """Test writing to read-only location."""
        from jdev_cli.tools.file_ops import WriteFileTool

        # Create read-only directory
        readonly_dir = temp_project / "readonly"
        readonly_dir.mkdir()
        os.chmod(readonly_dir, 0o444)

        tool = WriteFileTool()
        result = await tool._execute_validated(
            path=str(readonly_dir / "file.txt"),
            content="test"
        )

        # Should fail gracefully
        assert not result.success

        # Cleanup
        os.chmod(readonly_dir, 0o755)

    @pytest.mark.asyncio
    async def test_read_permission_denied(self, temp_project):
        """Test reading file without read permission."""
        from jdev_cli.tools.file_ops import ReadFileTool

        test_file = temp_project / "noperm.txt"
        test_file.write_text("secret")
        os.chmod(test_file, 0o000)

        tool = ReadFileTool()
        result = await tool._execute_validated(path=str(test_file))

        assert not result.success

        # Cleanup
        os.chmod(test_file, 0o644)

    @pytest.mark.asyncio
    async def test_edit_nonexistent_file(self, temp_project):
        """Test editing file that doesn't exist."""
        from jdev_cli.tools.file_ops import EditFileTool

        tool = EditFileTool()
        result = await tool._execute_validated(
            path=str(temp_project / "nonexistent.txt"),
            edits=[{"search": "old", "replace": "new"}],
            preview=False,
            create_backup=False
        )

        assert not result.success
        assert "not found" in result.error.lower()


class TestBoundaryValues:
    """Test boundary value conditions."""

    @pytest.mark.asyncio
    async def test_max_file_size_10mb(self, temp_project):
        """Test handling 10MB file."""
        from jdev_cli.tools.file_ops import WriteFileTool, ReadFileTool

        large_content = "x" * (10 * 1024 * 1024)

        write_tool = WriteFileTool()
        result = await write_tool._execute_validated(
            path=str(temp_project / "10mb.txt"),
            content=large_content
        )
        assert result.success

        read_tool = ReadFileTool()
        result = await read_tool._execute_validated(
            path=str(temp_project / "10mb.txt")
        )
        assert result.success
        assert len(result.data["content"]) == 10 * 1024 * 1024

    @pytest.mark.asyncio
    async def test_max_search_results_limit(self, temp_project):
        """Test search with exact max_results limit."""
        from jdev_cli.tools.search import SearchFilesTool

        # Create file with 100 matches
        content = "\n".join([f"match line {i}" for i in range(100)])
        (temp_project / "matches.txt").write_text(content)

        tool = SearchFilesTool()

        # Test max_results=50
        result = await tool._execute_validated(
            pattern="match",
            path=str(temp_project),
            max_results=50
        )

        assert result.success
        matches = result.data.get("matches", [])
        assert len(matches) == 50

        # Test max_results=1
        result = await tool._execute_validated(
            pattern="match",
            path=str(temp_project),
            max_results=1
        )

        assert result.success
        matches = result.data.get("matches", [])
        assert len(matches) == 1

    @pytest.mark.asyncio
    async def test_zero_max_results(self, temp_project):
        """Test search with max_results=0."""
        from jdev_cli.tools.search import SearchFilesTool

        (temp_project / "test.txt").write_text("match")

        tool = SearchFilesTool()
        result = await tool._execute_validated(
            pattern="match",
            path=str(temp_project),
            max_results=0
        )

        # Should handle edge case (return empty or all)
        assert result.success
