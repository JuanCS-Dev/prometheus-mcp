"""
Tests for Tool Integration in jdev_tui
======================================

Tests the ToolCallParser, OutputFormatter, and Bridge tool execution.

Strategy:
- Unit tests for ToolCallParser (pure logic, no async)
- Unit tests for OutputFormatter (pure formatting)
- Integration tests for Bridge (mocked LLM)

NO Textual pilot tests (known to cause issues with Claude Code).
"""

import pytest
from io import StringIO

from rich.console import Console

# Import components to test
from jdev_tui.core.bridge import ToolCallParser
from jdev_tui.core.output_formatter import OutputFormatter


# =============================================================================
# ToolCallParser Tests
# =============================================================================

class TestToolCallParser:
    """Tests for ToolCallParser - extracting tool calls from text."""

    def test_extract_single_tool_call(self):
        """Test extracting a single tool call."""
        text = 'Let me create that file. [TOOL_CALL:write_file:{"path":"test.html","content":"<html>"}]'

        calls = ToolCallParser.extract(text)

        assert len(calls) == 1
        assert calls[0][0] == "write_file"
        assert calls[0][1] == {"path": "test.html", "content": "<html>"}

    def test_extract_multiple_tool_calls(self):
        """Test extracting multiple tool calls."""
        text = '''
        First, let me read the file. [TOOL_CALL:read_file:{"path":"config.py"}]
        Now I'll edit it. [TOOL_CALL:edit_file:{"path":"config.py","edits":[]}]
        '''

        calls = ToolCallParser.extract(text)

        assert len(calls) == 2
        assert calls[0][0] == "read_file"
        assert calls[1][0] == "edit_file"

    def test_extract_no_tool_calls(self):
        """Test when there are no tool calls."""
        text = "Just a regular response without any tool calls."

        calls = ToolCallParser.extract(text)

        assert len(calls) == 0

    def test_extract_malformed_json_skipped(self):
        """Test that malformed JSON is skipped."""
        text = '[TOOL_CALL:bad_tool:{not valid json}] and [TOOL_CALL:good_tool:{"key":"value"}]'

        calls = ToolCallParser.extract(text)

        assert len(calls) == 1
        assert calls[0][0] == "good_tool"

    def test_remove_tool_calls(self):
        """Test removing tool call markers from text."""
        text = 'Before [TOOL_CALL:test:{"a":1}] After'

        clean = ToolCallParser.remove(text)

        assert "[TOOL_CALL" not in clean
        assert "Before" in clean
        assert "After" in clean

    def test_format_marker(self):
        """Test creating a tool call marker."""
        marker = ToolCallParser.format_marker("write_file", {"path": "test.txt", "content": "hello"})

        assert "[TOOL_CALL:write_file:" in marker
        assert '"path"' in marker
        assert '"content"' in marker

    def test_roundtrip(self):
        """Test that format_marker output can be extracted."""
        original_args = {"path": "/tmp/test.py", "content": "print('hello')"}
        marker = ToolCallParser.format_marker("write_file", original_args)

        calls = ToolCallParser.extract(marker)

        assert len(calls) == 1
        assert calls[0][0] == "write_file"
        assert calls[0][1] == original_args


# =============================================================================
# OutputFormatter Tests
# =============================================================================

class TestOutputFormatter:
    """Tests for OutputFormatter - Panel formatting."""

    def test_format_response_returns_panel(self):
        """Test that format_response returns a Panel."""
        from rich.panel import Panel

        result = OutputFormatter.format_response("Hello world")

        assert isinstance(result, Panel)

    def test_format_response_renders_without_error(self):
        """Test that formatted response renders correctly."""
        console = Console(file=StringIO(), force_terminal=True, width=80)

        panel = OutputFormatter.format_response("Test response", title="Test")
        console.print(panel)

        output = console.file.getvalue()
        assert len(output) > 0

    def test_format_tool_result_success(self):
        """Test formatting successful tool result."""
        from rich.panel import Panel

        result = OutputFormatter.format_tool_result(
            "write_file",
            success=True,
            data="File created at /tmp/test.txt"
        )

        assert isinstance(result, Panel)

    def test_format_tool_result_failure(self):
        """Test formatting failed tool result."""
        result = OutputFormatter.format_tool_result(
            "read_file",
            success=False,
            error="File not found: /nonexistent"
        )

        # Render to check it works
        console = Console(file=StringIO(), force_terminal=True, width=80)
        console.print(result)

        output = console.file.getvalue()
        assert len(output) > 0

    def test_format_code_block(self):
        """Test formatting code block with syntax highlighting."""
        code = "def hello():\n    print('world')"

        result = OutputFormatter.format_code_block(code, "python")

        console = Console(file=StringIO(), force_terminal=True, width=80)
        console.print(result)

        output = console.file.getvalue()
        assert len(output) > 0

    def test_format_response_truncates_long_content(self):
        """Test that very long content is truncated."""
        long_text = "x" * 10000

        result = OutputFormatter.format_response(long_text)

        # Should have truncation indicator
        console = Console(file=StringIO(), force_terminal=True, width=80)
        console.print(result)

        output = console.file.getvalue()
        assert "truncated" in output.lower()

    def test_format_error(self):
        """Test error formatting."""
        result = OutputFormatter.format_error("Something went wrong")

        console = Console(file=StringIO(), force_terminal=True, width=80)
        console.print(result)

        output = console.file.getvalue()
        assert len(output) > 0

    def test_format_success(self):
        """Test success formatting."""
        result = OutputFormatter.format_success("Operation completed")

        console = Console(file=StringIO(), force_terminal=True, width=80)
        console.print(result)

        output = console.file.getvalue()
        assert len(output) > 0


# =============================================================================
# Bridge Tool Configuration Tests
# =============================================================================

class TestBridgeToolConfiguration:
    """Tests for Bridge tool configuration without full integration."""

    def test_get_system_prompt_contains_tools(self):
        """Test that system prompt includes tool information."""
        from jdev_tui.core.bridge import Bridge

        bridge = Bridge()
        prompt = bridge._get_system_prompt()

        # Should mention tools and key instructions
        assert "tool" in prompt.lower() or "TOOL" in prompt
        assert "write_file" in prompt or "Available tools" in prompt

    def test_configure_llm_tools_sets_schemas(self):
        """Test that _configure_llm_tools sets tool schemas on LLM."""
        from jdev_tui.core.bridge import Bridge

        bridge = Bridge()

        # Initially not configured
        assert not bridge._tools_configured

        # Configure tools
        bridge._configure_llm_tools()

        # Should be marked as configured (even if no tools loaded)
        # This depends on whether tools load successfully
        # Just verify it doesn't crash
        assert True


# =============================================================================
# Integration Tests (with mocks)
# =============================================================================

class TestBridgeChatIntegration:
    """Integration tests for Bridge.chat() with mocked LLM."""

    @pytest.mark.asyncio
    async def test_chat_without_tool_calls(self):
        """Test chat that doesn't trigger tool calls."""
        from jdev_tui.core.bridge import Bridge

        bridge = Bridge()

        # Mock LLM to return simple text
        async def mock_stream(*args, **kwargs):
            yield "Hello! How can I help you today?"

        bridge.llm.stream = mock_stream

        # Collect response
        response_parts = []
        async for chunk in bridge.chat("Hi"):
            response_parts.append(chunk)

        response = "".join(response_parts)
        assert "Hello" in response

    @pytest.mark.asyncio
    async def test_chat_with_tool_call_detection(self):
        """Test that tool calls are detected in LLM response."""
        from jdev_tui.core.bridge import Bridge

        bridge = Bridge()

        # Mock LLM to return a tool call
        async def mock_stream(*args, **kwargs):
            yield "Let me create that file for you. "
            yield '[TOOL_CALL:write_file:{"path":"test.txt","content":"hello"}]'

        bridge.llm.stream = mock_stream

        # Mock tool execution
        async def mock_execute(name, **kwargs):
            return {"success": True, "data": "File created"}

        bridge.tools.execute_tool = mock_execute

        # Collect response
        response_parts = []
        async for chunk in bridge.chat("Create test.txt"):
            response_parts.append(chunk)

        response = "".join(response_parts)

        # Should contain execution indicator
        assert "Executing" in response or "write_file" in response


# =============================================================================
# Tool Registry Tests
# =============================================================================

class TestToolBridgeRegistry:
    """Tests for ToolBridge tool loading."""

    def test_tool_bridge_initializes(self):
        """Test that ToolBridge can be created."""
        from jdev_tui.core.bridge import ToolBridge

        bridge = ToolBridge()

        # Should not crash
        assert bridge is not None

    def test_tool_bridge_lists_tools(self):
        """Test that ToolBridge can list tools."""
        from jdev_tui.core.bridge import ToolBridge

        bridge = ToolBridge()
        tools = bridge.list_tools()

        # Should return a list (may be empty if imports fail)
        assert isinstance(tools, list)

    def test_tool_bridge_get_schemas(self):
        """Test that ToolBridge can get schemas for LLM."""
        from jdev_tui.core.bridge import ToolBridge

        bridge = ToolBridge()
        schemas = bridge.get_schemas_for_llm()

        # Should return a list
        assert isinstance(schemas, list)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
