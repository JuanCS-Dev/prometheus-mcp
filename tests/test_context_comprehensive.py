"""Comprehensive context manager tests."""

import tempfile
from pathlib import Path
from jdev_cli.core.context import ContextBuilder, context_builder


class TestContextBuilderBasics:
    """Basic context builder functionality."""

    def test_initialization_defaults(self):
        """Test default initialization."""
        builder = ContextBuilder()
        assert builder.max_files == 5
        assert builder.max_file_size_kb == 100
        assert len(builder.files) == 0

    def test_initialization_custom(self):
        """Test custom initialization."""
        builder = ContextBuilder(max_files=10, max_file_size_kb=200)
        assert builder.max_files == 10
        assert builder.max_file_size_kb == 200

    def test_clear(self):
        """Test clearing context."""
        builder = ContextBuilder()
        builder.files["test"] = "content"
        builder.clear()
        assert len(builder.files) == 0


class TestFileOperations:
    """Test file reading and adding."""

    def test_read_valid_file(self):
        """Test reading a valid file."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write("test content\n")
            temp_path = f.name

        try:
            builder = ContextBuilder()
            success, content, error = builder.read_file(temp_path)
            assert success
            assert content == "test content\n"
            assert error == ""
        finally:
            Path(temp_path).unlink()

    def test_read_nonexistent_file(self):
        """Test reading nonexistent file."""
        builder = ContextBuilder()
        success, content, error = builder.read_file("/tmp/nonexistent_xyz.txt")
        assert not success
        assert "not found" in error.lower()

    def test_read_directory(self):
        """Test reading directory fails."""
        builder = ContextBuilder()
        success, content, error = builder.read_file("/tmp")
        assert not success
        assert "not a file" in error.lower()

    def test_read_binary_file(self):
        """Test reading binary file fails gracefully."""
        with tempfile.NamedTemporaryFile(delete=False, suffix='.bin') as f:
            f.write(b'\x00\x01\x02\x03\xff\xfe')
            temp_path = f.name

        try:
            builder = ContextBuilder()
            success, content, error = builder.read_file(temp_path)
            assert not success
            assert "binary" in error.lower() or "decode" in error.lower()
        finally:
            Path(temp_path).unlink()

    def test_read_large_file(self):
        """Test reading file exceeding size limit."""
        builder = ContextBuilder(max_file_size_kb=1)  # 1KB limit

        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write("x" * 2000)  # 2KB file
            temp_path = f.name

        try:
            success, content, error = builder.read_file(temp_path)
            assert not success
            assert "too large" in error.lower()
        finally:
            Path(temp_path).unlink()

    def test_add_file_success(self):
        """Test adding file successfully."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.py') as f:
            f.write("print('hello')\n")
            temp_path = f.name

        try:
            builder = ContextBuilder()
            success, message = builder.add_file(temp_path)
            assert success
            assert len(builder.files) == 1
            assert "Added" in message
        finally:
            Path(temp_path).unlink()

    def test_add_file_limit(self):
        """Test file limit enforcement."""
        builder = ContextBuilder(max_files=2)

        files = []
        for i in range(3):
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
                f.write(f"content {i}\n")
                files.append(f.name)

        try:
            success1, _ = builder.add_file(files[0])
            success2, _ = builder.add_file(files[1])
            success3, msg3 = builder.add_file(files[2])

            assert success1
            assert success2
            assert not success3
            assert "maximum" in msg3.lower()
        finally:
            for f in files:
                Path(f).unlink(missing_ok=True)

    def test_add_multiple_files(self):
        """Test adding multiple files at once."""
        files = []
        for i in range(3):
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
                f.write(f"content {i}\n")
                files.append(f.name)

        try:
            builder = ContextBuilder()
            results = builder.add_files(files)

            assert len(results) == 3
            assert all(path in results for path in files)
        finally:
            for f in files:
                Path(f).unlink(missing_ok=True)


class TestContextFormatting:
    """Test context formatting and injection."""

    def test_empty_context(self):
        """Test empty context returns empty string."""
        builder = ContextBuilder()
        context = builder.get_context()
        assert context == ""

    def test_single_file_context(self):
        """Test context with single file."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.py') as f:
            f.write("def hello():\n    print('world')\n")
            temp_path = f.name

        try:
            builder = ContextBuilder()
            builder.add_file(temp_path)
            context = builder.get_context()

            assert "Here are the relevant files" in context
            assert temp_path in context
            assert "def hello()" in context
            assert "```" in context
        finally:
            Path(temp_path).unlink()

    def test_multiple_files_context(self):
        """Test context with multiple files."""
        files = []
        for i in range(2):
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
                f.write(f"file {i} content\n")
                files.append(f.name)

        try:
            builder = ContextBuilder()
            for f in files:
                builder.add_file(f)

            context = builder.get_context()
            assert all(Path(f).name in context for f in files)
        finally:
            for f in files:
                Path(f).unlink(missing_ok=True)

    def test_inject_to_empty_prompt(self):
        """Test injecting context to prompt."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write("test content\n")
            temp_path = f.name

        try:
            builder = ContextBuilder()
            builder.add_file(temp_path)

            prompt = builder.inject_to_prompt("Explain this")
            assert "test content" in prompt
            assert "Explain this" in prompt
            assert "---" in prompt
        finally:
            Path(temp_path).unlink()

    def test_inject_to_prompt_no_context(self):
        """Test injection with no context returns original prompt."""
        builder = ContextBuilder()
        original = "Just a prompt"
        result = builder.inject_to_prompt(original)
        assert result == original


class TestContextStats:
    """Test context statistics."""

    def test_empty_stats(self):
        """Test stats for empty context."""
        builder = ContextBuilder()
        stats = builder.get_stats()

        assert stats["files"] == 0
        assert stats["total_chars"] == 0
        assert stats["total_lines"] == 0
        assert stats["approx_tokens"] == 0

    def test_stats_with_files(self):
        """Test stats with files added."""
        content = "line1\nline2\nline3\n"

        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write(content)
            temp_path = f.name

        try:
            builder = ContextBuilder()
            builder.add_file(temp_path)
            stats = builder.get_stats()

            assert stats["files"] == 1
            assert stats["total_chars"] == len(content)
            assert stats["total_lines"] == 4  # 3 lines + 1
            assert stats["approx_tokens"] == len(content) // 4
        finally:
            Path(temp_path).unlink()


class TestGlobalInstance:
    """Test global context builder instance."""

    def test_global_instance_exists(self):
        """Test global instance is available."""
        assert context_builder is not None
        assert isinstance(context_builder, ContextBuilder)

    def test_global_instance_isolation(self):
        """Test global instance can be used independently."""
        context_builder.clear()

        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write("global test\n")
            temp_path = f.name

        try:
            success, _ = context_builder.add_file(temp_path)
            assert success
            assert len(context_builder.files) == 1

            context_builder.clear()
            assert len(context_builder.files) == 0
        finally:
            Path(temp_path).unlink()


class TestRealWorldScenarios:
    """Test real-world usage scenarios."""

    def test_python_file_context(self):
        """Test adding Python source file."""
        code = '''#!/usr/bin/env python3
"""Module docstring."""

def function():
    """Function docstring."""
    return 42

if __name__ == "__main__":
    print(function())
'''

        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.py') as f:
            f.write(code)
            temp_path = f.name

        try:
            builder = ContextBuilder()
            success, _ = builder.add_file(temp_path)
            assert success

            context = builder.get_context()
            assert "```py" in context
            assert "def function()" in context
        finally:
            Path(temp_path).unlink()

    def test_mixed_file_types(self):
        """Test context with different file types."""
        files = [
            ('.py', 'print("hello")\n'),
            ('.js', 'console.log("world");\n'),
            ('.md', '# Title\n\nContent\n'),
        ]

        temp_files = []
        for ext, content in files:
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix=ext) as f:
                f.write(content)
                temp_files.append(f.name)

        try:
            builder = ContextBuilder()
            for path in temp_files:
                builder.add_file(path)

            context = builder.get_context()
            assert "```py" in context
            assert "```js" in context
            assert "```md" in context
        finally:
            for f in temp_files:
                Path(f).unlink(missing_ok=True)

    def test_workflow_add_inject_clear(self):
        """Test typical workflow: add files, inject, clear."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write("context data\n")
            temp_path = f.name

        try:
            builder = ContextBuilder()

            # Add file
            builder.add_file(temp_path)
            assert len(builder.files) == 1

            # Inject to prompt
            prompt = builder.inject_to_prompt("Analyze this")
            assert "context data" in prompt

            # Clear for next use
            builder.clear()
            assert len(builder.files) == 0

            # Empty context now
            new_prompt = builder.inject_to_prompt("New query")
            assert new_prompt == "New query"
        finally:
            Path(temp_path).unlink()
