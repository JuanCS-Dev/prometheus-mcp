"""Tests for Sprint 3 Claude Code Parity Features.

Tests:
- Image/PDF reading tools
- Git commit workflow with safety protocols
- Context auto-compact
"""

import pytest
import tempfile
from pathlib import Path


# =============================================================================
# IMAGE READING TESTS
# =============================================================================

class TestImageReadTool:
    """Test ImageReadTool."""

    def test_tool_import(self):
        """Test tool can be imported."""
        from jdev_cli.tools.media_tools import ImageReadTool
        assert ImageReadTool is not None

    def test_tool_creation(self):
        """Test tool creation."""
        from jdev_cli.tools.media_tools import ImageReadTool

        tool = ImageReadTool()
        assert tool.name == "image_read"
        assert "file_path" in tool.parameters

    def test_supported_formats(self):
        """Test supported format list."""
        from jdev_cli.tools.media_tools import ImageReadTool

        tool = ImageReadTool()
        assert ".png" in tool.SUPPORTED_FORMATS
        assert ".jpg" in tool.SUPPORTED_FORMATS
        assert ".gif" in tool.SUPPORTED_FORMATS
        assert ".webp" in tool.SUPPORTED_FORMATS

    @pytest.mark.asyncio
    async def test_read_nonexistent_image(self):
        """Test reading nonexistent image."""
        from jdev_cli.tools.media_tools import ImageReadTool

        tool = ImageReadTool()
        result = await tool._execute_validated(file_path="/nonexistent/image.png")

        assert result.success is False
        assert "not found" in result.error.lower()

    @pytest.mark.asyncio
    async def test_read_unsupported_format(self):
        """Test reading unsupported format."""
        from jdev_cli.tools.media_tools import ImageReadTool

        with tempfile.NamedTemporaryFile(suffix=".xyz", delete=False) as f:
            f.write(b"fake data")
            temp_path = f.name

        try:
            tool = ImageReadTool()
            result = await tool._execute_validated(file_path=temp_path)

            assert result.success is False
            assert "Unsupported format" in result.error
        finally:
            Path(temp_path).unlink()

    @pytest.mark.asyncio
    async def test_read_valid_png(self):
        """Test reading a valid PNG file."""
        from jdev_cli.tools.media_tools import ImageReadTool

        # Create a minimal valid PNG
        png_data = (
            b'\x89PNG\r\n\x1a\n'  # PNG signature
            b'\x00\x00\x00\rIHDR'  # IHDR chunk
            b'\x00\x00\x00\x10'  # Width: 16
            b'\x00\x00\x00\x10'  # Height: 16
            b'\x08\x02'  # Bit depth, color type
            b'\x00\x00\x00'  # Compression, filter, interlace
            b'\x90wS\xde'  # CRC
            b'\x00\x00\x00\x00IEND\xaeB`\x82'  # IEND chunk
        )

        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            f.write(png_data)
            temp_path = f.name

        try:
            tool = ImageReadTool()
            result = await tool._execute_validated(file_path=temp_path)

            assert result.success is True
            assert result.data["format"] == "PNG"
            assert result.data["width"] == 16
            assert result.data["height"] == 16
        finally:
            Path(temp_path).unlink()


# =============================================================================
# PDF READING TESTS
# =============================================================================

class TestPDFReadTool:
    """Test PDFReadTool."""

    def test_tool_import(self):
        """Test tool can be imported."""
        from jdev_cli.tools.media_tools import PDFReadTool
        assert PDFReadTool is not None

    def test_tool_creation(self):
        """Test tool creation."""
        from jdev_cli.tools.media_tools import PDFReadTool

        tool = PDFReadTool()
        assert tool.name == "pdf_read"
        assert "file_path" in tool.parameters

    @pytest.mark.asyncio
    async def test_read_nonexistent_pdf(self):
        """Test reading nonexistent PDF."""
        from jdev_cli.tools.media_tools import PDFReadTool

        tool = PDFReadTool()
        result = await tool._execute_validated(file_path="/nonexistent/doc.pdf")

        assert result.success is False
        assert "not found" in result.error.lower()

    @pytest.mark.asyncio
    async def test_read_non_pdf_file(self):
        """Test reading non-PDF file."""
        from jdev_cli.tools.media_tools import PDFReadTool

        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
            f.write(b"not a pdf")
            temp_path = f.name

        try:
            tool = PDFReadTool()
            result = await tool._execute_validated(file_path=temp_path)

            assert result.success is False
            assert "PDF" in result.error
        finally:
            Path(temp_path).unlink()


# =============================================================================
# GIT WORKFLOW TESTS
# =============================================================================

class TestGitSafety:
    """Test git safety protocols."""

    def test_validate_safe_command(self):
        """Test safe commands pass validation."""
        from jdev_cli.tools.git_workflow import validate_git_command

        is_safe, reason = validate_git_command("git status")
        assert is_safe is True

        is_safe, reason = validate_git_command("git log --oneline -10")
        assert is_safe is True

        is_safe, reason = validate_git_command("git diff HEAD~1")
        assert is_safe is True

    def test_block_force_push(self):
        """Test force push is blocked."""
        from jdev_cli.tools.git_workflow import validate_git_command

        is_safe, reason = validate_git_command("git push --force origin main")
        assert is_safe is False
        assert "force" in reason.lower()

    def test_block_hard_reset(self):
        """Test hard reset is blocked."""
        from jdev_cli.tools.git_workflow import validate_git_command

        is_safe, reason = validate_git_command("git reset --hard HEAD~1")
        assert is_safe is False
        assert "hard" in reason.lower()

    def test_block_config(self):
        """Test git config is blocked."""
        from jdev_cli.tools.git_workflow import validate_git_command

        is_safe, reason = validate_git_command("git config user.email evil@hack.com")
        assert is_safe is False
        assert "config" in reason.lower()

    def test_block_no_verify(self):
        """Test --no-verify is blocked."""
        from jdev_cli.tools.git_workflow import validate_git_command

        is_safe, reason = validate_git_command("git commit --no-verify -m 'test'")
        assert is_safe is False
        assert "no-verify" in reason.lower()


class TestGitCommitTool:
    """Test GitCommitTool."""

    def test_tool_import(self):
        """Test tool can be imported."""
        from jdev_cli.tools.git_workflow import GitCommitTool
        assert GitCommitTool is not None

    def test_tool_creation(self):
        """Test tool creation."""
        from jdev_cli.tools.git_workflow import GitCommitTool

        tool = GitCommitTool()
        assert tool.name == "git_commit"
        assert "message" in tool.parameters
        assert "amend" in tool.parameters

    def test_build_commit_message(self):
        """Test commit message building."""
        from jdev_cli.tools.git_workflow import GitCommitTool

        tool = GitCommitTool()

        # With signature
        msg = tool._build_commit_message("Test commit", add_signature=True)
        assert "Test commit" in msg
        assert "Juan-Dev-Code" in msg
        assert "Co-Authored-By" in msg

        # Without signature
        msg = tool._build_commit_message("Test commit", add_signature=False)
        assert msg == "Test commit"


class TestGitPRCreateTool:
    """Test GitPRCreateTool."""

    def test_tool_import(self):
        """Test tool can be imported."""
        from jdev_cli.tools.git_workflow import GitPRCreateTool
        assert GitPRCreateTool is not None

    def test_tool_creation(self):
        """Test tool creation."""
        from jdev_cli.tools.git_workflow import GitPRCreateTool

        tool = GitPRCreateTool()
        assert tool.name == "git_pr_create"
        assert "title" in tool.parameters
        assert "body" in tool.parameters

    def test_build_pr_body(self):
        """Test PR body building."""
        from jdev_cli.tools.git_workflow import GitPRCreateTool

        tool = GitPRCreateTool()

        body = tool._build_pr_body("## Summary\n\nTest PR")
        assert "Test PR" in body
        assert "Juan-Dev-Code" in body


# =============================================================================
# CONTEXT COMPACT TESTS
# =============================================================================

class TestContextCompactor:
    """Test ContextCompactor."""

    def test_import(self):
        """Test compactor can be imported."""
        from jdev_cli.core.context_compact import ContextCompactor, get_context_compactor
        assert ContextCompactor is not None
        assert get_context_compactor is not None

    def test_creation(self):
        """Test compactor creation."""
        from jdev_cli.core.context_compact import ContextCompactor

        compactor = ContextCompactor(max_tokens=10000)
        assert compactor.max_tokens == 10000
        assert compactor.entry_count == 0

    def test_add_entry(self):
        """Test adding entries."""
        from jdev_cli.core.context_compact import ContextCompactor

        compactor = ContextCompactor(max_tokens=10000)

        entry = compactor.add_entry("Hello world", entry_type="user")

        assert compactor.entry_count == 1
        assert entry.content == "Hello world"
        assert entry.entry_type == "user"

    def test_auto_priority(self):
        """Test automatic priority assignment."""
        from jdev_cli.core.context_compact import ContextCompactor

        compactor = ContextCompactor()

        # System messages get highest priority
        entry = compactor.add_entry("System prompt", entry_type="system")
        assert entry.priority == compactor.PRIORITY_CRITICAL

        # Code gets high priority
        entry = compactor.add_entry("```python\nprint('hello')\n```", entry_type="assistant")
        assert entry.priority == compactor.PRIORITY_HIGH

        # Long tool outputs get low priority
        entry = compactor.add_entry("x" * 3000, entry_type="tool_result")
        assert entry.priority == compactor.PRIORITY_VERBOSE

    def test_should_compact(self):
        """Test compaction trigger."""
        from jdev_cli.core.context_compact import ContextCompactor

        compactor = ContextCompactor(max_tokens=100, compact_threshold=0.5)

        # Below threshold
        compactor.add_entry("short", entry_type="user")
        assert not compactor.should_compact()

        # Above threshold (50 tokens = 50% of 100)
        compactor.add_entry("x" * 200, entry_type="user")  # ~50 tokens
        assert compactor.should_compact()

    def test_deduplication(self):
        """Test duplicate removal."""
        from jdev_cli.core.context_compact import ContextCompactor, reset_context_compactor

        reset_context_compactor()
        compactor = ContextCompactor(max_tokens=100000)

        # Add duplicates
        compactor.add_entry("duplicate content", entry_type="user")
        compactor.add_entry("duplicate content", entry_type="user")
        compactor.add_entry("unique content", entry_type="user")

        # Trigger compaction
        result = compactor.compact()

        # Should have removed 1 duplicate
        assert result.removed_count >= 1

    def test_get_context(self):
        """Test context retrieval."""
        from jdev_cli.core.context_compact import ContextCompactor

        compactor = ContextCompactor()
        compactor.add_entry("Hello", entry_type="user")
        compactor.add_entry("Hi there!", entry_type="assistant")

        context = compactor.get_context()

        assert "User: Hello" in context
        assert "Assistant: Hi there!" in context

    def test_stats(self):
        """Test statistics."""
        from jdev_cli.core.context_compact import ContextCompactor

        compactor = ContextCompactor(max_tokens=1000)
        compactor.add_entry("Test", entry_type="user")
        compactor.add_entry("Response", entry_type="assistant")

        stats = compactor.get_stats()

        assert "total_tokens" in stats
        assert "entry_count" in stats
        assert stats["entry_count"] == 2


# =============================================================================
# INTEGRATION TESTS
# =============================================================================

class TestSprint3Integration:
    """Integration tests for Sprint 3 features."""

    def test_all_tools_importable(self):
        """Test all Sprint 3 tools are importable."""
        from jdev_cli.tools import (
            ImageReadTool,
            PDFReadTool,
            GitCommitTool,
            GitPRCreateTool,
        )

        assert ImageReadTool is not None
        assert PDFReadTool is not None
        assert GitCommitTool is not None
        assert GitPRCreateTool is not None

    def test_helper_functions(self):
        """Test helper functions return tools."""
        from jdev_cli.tools import get_media_tools, get_git_workflow_tools

        media_tools = get_media_tools()
        assert len(media_tools) >= 3

        git_tools = get_git_workflow_tools()
        assert len(git_tools) >= 5

    def test_context_compactor_singleton(self):
        """Test context compactor singleton."""
        from jdev_cli.core.context_compact import (
            get_context_compactor,
            reset_context_compactor
        )

        reset_context_compactor()

        c1 = get_context_compactor()
        c2 = get_context_compactor()

        assert c1 is c2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
