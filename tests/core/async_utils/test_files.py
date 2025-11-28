"""
Tests for async file operations.

SCALE & SUSTAIN Phase 3.1 validation.
"""


import pytest

from jdev_core.async_utils import (
    read_file,
    write_file,
    read_json,
    write_json,
    file_exists,
    list_dir,
    read_bytes,
    write_bytes,
    AIOFILES_AVAILABLE,
)


class TestAsyncFileOperations:
    """Test async file read/write operations."""

    @pytest.mark.asyncio
    async def test_write_and_read_file(self, tmp_path):
        """Test writing and reading a text file."""
        test_file = tmp_path / "test.txt"
        content = "Hello, async world!"

        await write_file(test_file, content)
        result = await read_file(test_file)

        assert result == content

    @pytest.mark.asyncio
    async def test_write_creates_parent_dirs(self, tmp_path):
        """Test that write_file creates parent directories."""
        test_file = tmp_path / "nested" / "deep" / "test.txt"
        content = "Nested content"

        await write_file(test_file, content, create_dirs=True)

        assert test_file.exists()
        result = await read_file(test_file)
        assert result == content

    @pytest.mark.asyncio
    async def test_read_file_with_encoding(self, tmp_path):
        """Test reading file with specific encoding."""
        test_file = tmp_path / "unicode.txt"
        content = "Olá, mundo! 你好世界! 🎉"

        await write_file(test_file, content, encoding='utf-8')
        result = await read_file(test_file, encoding='utf-8')

        assert result == content

    @pytest.mark.asyncio
    async def test_file_exists_true(self, tmp_path):
        """Test file_exists returns True for existing file."""
        test_file = tmp_path / "exists.txt"
        test_file.write_text("content")

        result = await file_exists(test_file)
        assert result is True

    @pytest.mark.asyncio
    async def test_file_exists_false(self, tmp_path):
        """Test file_exists returns False for non-existing file."""
        test_file = tmp_path / "not_exists.txt"

        result = await file_exists(test_file)
        assert result is False


class TestAsyncJsonOperations:
    """Test async JSON read/write operations."""

    @pytest.mark.asyncio
    async def test_write_and_read_json(self, tmp_path):
        """Test writing and reading JSON data."""
        test_file = tmp_path / "data.json"
        data = {"name": "test", "values": [1, 2, 3], "nested": {"key": "value"}}

        await write_json(test_file, data)
        result = await read_json(test_file)

        assert result == data

    @pytest.mark.asyncio
    async def test_write_json_with_indent(self, tmp_path):
        """Test JSON is written with proper indentation."""
        test_file = tmp_path / "formatted.json"
        data = {"key": "value"}

        await write_json(test_file, data, indent=4)
        content = await read_file(test_file)

        assert "    " in content  # 4-space indent


class TestAsyncBinaryOperations:
    """Test async binary read/write operations."""

    @pytest.mark.asyncio
    async def test_write_and_read_bytes(self, tmp_path):
        """Test writing and reading binary data."""
        test_file = tmp_path / "binary.bin"
        data = b"\x00\x01\x02\x03\xff\xfe\xfd"

        await write_bytes(test_file, data)
        result = await read_bytes(test_file)

        assert result == data

    @pytest.mark.asyncio
    async def test_write_bytes_creates_dirs(self, tmp_path):
        """Test write_bytes creates parent directories."""
        test_file = tmp_path / "nested" / "binary.bin"
        data = b"binary content"

        await write_bytes(test_file, data, create_dirs=True)

        assert test_file.exists()


class TestListDir:
    """Test async directory listing."""

    @pytest.mark.asyncio
    async def test_list_dir_all_files(self, tmp_path):
        """Test listing all files in directory."""
        (tmp_path / "file1.txt").write_text("1")
        (tmp_path / "file2.txt").write_text("2")
        (tmp_path / "file3.py").write_text("3")

        result = await list_dir(tmp_path)

        assert len(result) == 3

    @pytest.mark.asyncio
    async def test_list_dir_with_pattern(self, tmp_path):
        """Test listing files with glob pattern."""
        (tmp_path / "file1.txt").write_text("1")
        (tmp_path / "file2.txt").write_text("2")
        (tmp_path / "file3.py").write_text("3")

        result = await list_dir(tmp_path, pattern="*.txt")

        assert len(result) == 2
        assert all(p.suffix == ".txt" for p in result)


class TestAiofilesAvailability:
    """Test aiofiles detection."""

    def test_aiofiles_flag_is_boolean(self):
        """Test AIOFILES_AVAILABLE is a boolean."""
        assert isinstance(AIOFILES_AVAILABLE, bool)

    def test_aiofiles_is_available(self):
        """Test aiofiles is installed (expected in this project)."""
        # This project has aiofiles installed
        assert AIOFILES_AVAILABLE is True
