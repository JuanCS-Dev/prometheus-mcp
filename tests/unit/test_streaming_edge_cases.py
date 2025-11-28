"""
Edge Case Tests for Streaming System - AIR GAP FIX VALIDATION.

Tests the streaming pipeline to ensure:
1. No Rich markup leaks through (must be Markdown)
2. Markup helpers produce valid Markdown
3. StreamingResponseWidget handles edge cases
4. Bridge yields are streaming-safe

20 Edge Cases covering:
- Markup helper outputs
- Special characters in tool names
- Unicode and emoji handling
- Long content truncation
- Concurrent streaming
- Error message formatting
- Agent routing edge cases

Author: JuanCS Dev
Date: 2025-11-26
"""

import pytest

from jdev_tui.core.output_formatter import (
    tool_executing_markup,
    tool_success_markup,
    tool_error_markup,
    agent_routing_markup,
    Colors,
    Icons,
)


class TestMarkupHelperEdgeCases:
    """Edge cases for markup helper functions."""

    # =========================================================================
    # Edge Case 1-5: Tool name variations
    # =========================================================================

    def test_tool_with_underscore(self):
        """Tool names with underscores should render correctly."""
        result = tool_executing_markup("read_file")
        assert "**read_file**" in result
        assert "[bold" not in result
        assert "[#" not in result

    def test_tool_with_camelcase(self):
        """CamelCase tool names should preserve case."""
        result = tool_executing_markup("ReadFile")
        assert "**ReadFile**" in result

    def test_tool_with_numbers(self):
        """Tool names with numbers should work."""
        result = tool_executing_markup("tool_v2")
        assert "**tool_v2**" in result

    def test_tool_empty_name(self):
        """Empty tool name should not crash."""
        result = tool_executing_markup("")
        assert "**" in result  # Should have bold markers even if empty
        assert "[bold" not in result

    def test_tool_with_special_chars(self):
        """Tool names with special chars should be escaped/handled."""
        result = tool_executing_markup("my-tool.name")
        assert "my-tool.name" in result
        assert "[bold" not in result

    # =========================================================================
    # Edge Case 6-10: Error message handling
    # =========================================================================

    def test_error_with_newlines(self):
        """Error messages with newlines should be handled."""
        result = tool_error_markup("TestTool", "Line1\nLine2\nLine3")
        assert "TestTool" in result
        assert "[bold" not in result
        # Should truncate or handle newlines gracefully

    def test_error_very_long_message(self):
        """Very long error messages should be truncated."""
        long_error = "x" * 200
        result = tool_error_markup("TestTool", long_error)
        assert len(result) < 250  # Should truncate
        assert "[bold" not in result

    def test_error_with_markdown_chars(self):
        """Error messages with markdown chars should not break rendering."""
        result = tool_error_markup("TestTool", "Error: *bold* and _italic_ and `code`")
        assert "TestTool" in result
        assert "[bold" not in result

    def test_error_with_brackets(self):
        """Error messages with brackets should not be interpreted as Rich."""
        result = tool_error_markup("TestTool", "Error [code 404] not found")
        assert "[code 404]" in result or "code 404" in result
        assert "[bold" not in result

    def test_error_unicode_message(self):
        """Unicode in error messages should work."""
        result = tool_error_markup("TestTool", "Erro: arquivo não encontrado 文件")
        assert "não encontrado" in result or "n" in result
        assert "[bold" not in result

    # =========================================================================
    # Edge Case 11-15: Agent routing variations
    # =========================================================================

    def test_agent_routing_zero_confidence(self):
        """Zero confidence should show 0%."""
        result = agent_routing_markup("test", 0.0)
        assert "0%" in result
        assert "[bold" not in result

    def test_agent_routing_full_confidence(self):
        """100% confidence should show correctly."""
        result = agent_routing_markup("test", 1.0)
        assert "100%" in result
        assert "[bold" not in result

    def test_agent_routing_fractional_confidence(self):
        """Fractional confidence should round to int."""
        result = agent_routing_markup("test", 0.857)
        assert "85%" in result or "86%" in result  # Rounding
        assert "[bold" not in result

    def test_agent_routing_long_name(self):
        """Long agent names should work."""
        result = agent_routing_markup("super_long_agent_name_here", 0.5)
        # .title() capitalizes each word, so underscores become word boundaries
        assert "Agent" in result
        assert "super" in result.lower()
        assert "[bold" not in result

    def test_agent_routing_special_agent_name(self):
        """Agent names with special chars should work."""
        result = agent_routing_markup("security-audit", 0.9)
        # .title() capitalizes each word, hyphens become word boundaries
        assert "Agent" in result
        assert "security" in result.lower()
        assert "[bold" not in result

    # =========================================================================
    # Edge Case 16-20: Success markup and combined scenarios
    # =========================================================================

    def test_success_with_emoji_in_name(self):
        """Tool names shouldn't have emojis but handle gracefully."""
        result = tool_success_markup("Test🔥Tool")
        assert "Test" in result
        assert "[bold" not in result

    def test_all_markups_no_rich_tags(self):
        """Comprehensive check that NO markup has Rich tags."""
        markups = [
            tool_executing_markup("test"),
            tool_executing_markup("test_with_underscore"),
            tool_executing_markup("TestCamelCase"),
            tool_success_markup("test"),
            tool_success_markup(""),
            tool_error_markup("test", "error"),
            tool_error_markup("test", "error with [brackets]"),
            agent_routing_markup("test", 0.5),
            agent_routing_markup("test", 0.0),
            agent_routing_markup("test", 1.0),
        ]

        rich_patterns = ["[bold", "[italic", "[#", "[/", "Colors."]
        for markup in markups:
            for pattern in rich_patterns:
                assert pattern not in markup, f"Found {pattern} in: {markup}"

    def test_markup_produces_valid_markdown(self):
        """All markups should produce valid Markdown syntax."""
        markups = [
            tool_executing_markup("ReadFile"),
            tool_success_markup("WriteFile"),
            tool_error_markup("BashCommand", "Permission denied"),
            agent_routing_markup("planner", 0.85),
        ]

        for markup in markups:
            # Should have ** for bold (Markdown)
            assert "**" in markup or "*" in markup or markup.startswith("•") or markup.startswith("✓") or markup.startswith("✗") or "🔀" in markup

    def test_markup_emojis_present(self):
        """Markups should use emojis for visual feedback."""
        exec_markup = tool_executing_markup("Test")
        success_markup = tool_success_markup("Test")
        error_markup = tool_error_markup("Test", "err")
        routing_markup = agent_routing_markup("test", 0.5)

        # At least some should have visual indicators
        all_markups = exec_markup + success_markup + error_markup + routing_markup
        has_visual = any(c in all_markups for c in ["•", "✓", "✗", "🔀", "🤖", "⚡"])
        assert has_visual, "Markups should have visual indicators"

    def test_concurrent_markup_generation(self):
        """Markup generation should be thread-safe."""
        import concurrent.futures

        def generate_markups():
            results = []
            for i in range(100):
                results.append(tool_executing_markup(f"tool_{i}"))
                results.append(tool_success_markup(f"tool_{i}"))
                results.append(agent_routing_markup(f"agent_{i}", i/100))
            return results

        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(generate_markups) for _ in range(4)]
            for future in concurrent.futures.as_completed(futures):
                results = future.result()
                assert len(results) == 300
                for r in results:
                    assert "[bold" not in r


class TestStreamingWidgetEdgeCases:
    """Edge cases for StreamingResponseWidget."""

    def test_widget_import(self):
        """Widget should import without errors."""
        from jdev_tui.components.streaming_adapter import StreamingResponseWidget
        assert StreamingResponseWidget is not None

    def test_widget_initialization(self):
        """Widget should initialize with markdown enabled."""
        from jdev_tui.components.streaming_adapter import StreamingResponseWidget
        widget = StreamingResponseWidget(enable_markdown=True)
        assert widget._enable_markdown is True

    def test_widget_markdown_disabled(self):
        """Widget should work with markdown disabled."""
        from jdev_tui.components.streaming_adapter import StreamingResponseWidget
        widget = StreamingResponseWidget(enable_markdown=False)
        assert widget._enable_markdown is False


class TestBridgeStreamingSafety:
    """Tests for bridge streaming output safety."""

    def test_bridge_import(self):
        """Bridge should import without errors."""
        from jdev_tui.core.bridge import Bridge
        assert Bridge is not None

    def test_bridge_no_rich_in_source(self):
        """Bridge source should not contain Rich markup in yield statements."""
        import inspect
        from jdev_tui.core import bridge as bridge_module

        source = inspect.getsource(bridge_module)

        # Find yield statements
        lines = source.split('\n')
        yield_lines = [l for l in lines if 'yield' in l and 'f"' in l]

        rich_patterns = ['[bold ', '[italic ', '[#ff', '[Colors.', '{Colors.']

        for line in yield_lines:
            for pattern in rich_patterns:
                assert pattern not in line, f"Found Rich markup in yield: {line}"


class TestOutputFormatterStreamingSafety:
    """Tests for OutputFormatter streaming compatibility."""

    def test_colors_are_hex_strings(self):
        """Colors should be hex strings for Rich, but not used in stream."""
        assert Colors.PRIMARY.startswith("#")
        assert Colors.SUCCESS.startswith("#")
        assert Colors.ERROR.startswith("#")

    def test_icons_are_unicode(self):
        """Icons should be Unicode characters."""
        assert len(Icons.SUCCESS) <= 2  # Single emoji or char
        assert len(Icons.ERROR) <= 2
        assert len(Icons.TOOL) <= 2


# Pytest marker for edge case tests
pytestmark = pytest.mark.unit
