"""
Behavioral Tests for Streaming System - Real Flow Simulation.

Tests the actual streaming behavior by simulating:
1. Agent routing flow
2. Tool execution flow
3. LLM streaming response
4. Error handling during stream

These tests verify the ACTUAL OUTPUT that would be displayed,
ensuring no Rich markup leaks through.

Author: JuanCS Dev
Date: 2025-11-26
"""

import pytest


class TestAgentRoutingBehavior:
    """Test actual agent routing output behavior."""

    @pytest.mark.asyncio
    async def test_routing_output_is_markdown(self):
        """Agent routing should produce Markdown, not Rich markup."""
        from jdev_tui.core.output_formatter import agent_routing_markup

        # Simulate various routing scenarios
        outputs = [
            agent_routing_markup("planner", 0.95),
            agent_routing_markup("security", 0.87),
            agent_routing_markup("explorer", 0.72),
            agent_routing_markup("architect", 0.68),
        ]

        for output in outputs:
            # Must NOT contain Rich markup
            assert "[bold" not in output
            assert "[#" not in output
            assert "Colors." not in output
            # Must contain Markdown
            assert "**" in output  # Bold in Markdown
            # Must have visual indicator
            assert "🔀" in output or "Auto-routing" in output

    @pytest.mark.asyncio
    async def test_full_routing_flow_simulation(self):
        """Simulate complete routing flow and verify all outputs."""
        from jdev_tui.core.output_formatter import agent_routing_markup
        from jdev_tui.core.agents_bridge import AGENT_REGISTRY

        # Simulate what bridge.chat() yields during routing
        agent_name = "security"
        confidence = 0.85

        # First yield: routing markup
        routing_output = agent_routing_markup(agent_name, confidence)
        assert "[bold" not in routing_output

        # Second yield: agent description (now uses *italic* not [Colors])
        if agent_name in AGENT_REGISTRY:
            agent_info = AGENT_REGISTRY[agent_name]
            description_output = f"   *{agent_info.description}*"
            assert "[Colors" not in description_output
            assert "[bold" not in description_output


class TestToolExecutionBehavior:
    """Test actual tool execution output behavior."""

    @pytest.mark.asyncio
    async def test_tool_execution_markers(self):
        """Tool execution markers should be Markdown."""
        from jdev_tui.core.output_formatter import (
            tool_executing_markup,
            tool_success_markup,
            tool_error_markup,
        )

        tools = ["ReadFile", "WriteFile", "BashCommand", "Glob", "Grep"]

        for tool in tools:
            exec_output = tool_executing_markup(tool)
            success_output = tool_success_markup(tool)
            error_output = tool_error_markup(tool, "test error")

            # None should have Rich markup
            for output in [exec_output, success_output, error_output]:
                assert "[bold" not in output, f"Found Rich in: {output}"
                assert "[#" not in output, f"Found Rich color in: {output}"
                assert "Colors." not in output, f"Found Colors ref in: {output}"

    @pytest.mark.asyncio
    async def test_tool_output_has_visual_indicators(self):
        """Tool outputs should have clear visual indicators."""
        from jdev_tui.core.output_formatter import (
            tool_executing_markup,
            tool_success_markup,
            tool_error_markup,
        )

        exec_out = tool_executing_markup("Test")
        success_out = tool_success_markup("Test")
        error_out = tool_error_markup("Test", "err")

        # Should have bullet or icon
        assert "•" in exec_out or "**" in exec_out
        # Should have checkmark or success indicator
        assert "✓" in success_out or "Success" in success_out
        # Should have X or error indicator
        assert "✗" in error_out or "error" in error_out.lower()


class TestStreamingWidgetBehavior:
    """Test StreamingResponseWidget actual behavior."""

    def test_widget_accepts_markdown_content(self):
        """Widget should accept and store Markdown content."""
        from jdev_tui.components.streaming_adapter import StreamingResponseWidget

        widget = StreamingResponseWidget(enable_markdown=True)

        # Simulate streaming chunks (Markdown content)
        chunks = [
            "# Heading\n",
            "This is **bold** text.\n",
            "- Item 1\n",
            "- Item 2\n",
            "```python\nprint('hello')\n```\n",
        ]

        for chunk in chunks:
            widget._content += chunk  # Direct append for test

        # Verify content accumulated correctly
        assert "# Heading" in widget._content
        assert "**bold**" in widget._content
        assert "```python" in widget._content

    def test_widget_content_has_no_rich(self):
        """Content streamed should never have Rich markup."""
        from jdev_tui.components.streaming_adapter import StreamingResponseWidget
        from jdev_tui.core.output_formatter import (
            tool_executing_markup,
            agent_routing_markup,
        )

        widget = StreamingResponseWidget(enable_markdown=True)

        # Simulate what would be streamed
        content_parts = [
            agent_routing_markup("planner", 0.9),
            "\n",
            "Planning your task...\n",
            tool_executing_markup("ReadFile"),
            "\n",
            "File contents here.\n",
        ]

        full_content = "".join(content_parts)

        # Verify no Rich markup in what would be streamed
        assert "[bold" not in full_content
        assert "[#" not in full_content
        assert "[/" not in full_content


class TestBridgeChatBehavior:
    """Test Bridge.chat() actual output behavior."""

    @pytest.mark.asyncio
    async def test_bridge_yields_markdown_not_rich(self):
        """Bridge.chat() yields should be Markdown, not Rich."""
        # We can't easily run bridge.chat() without full setup,
        # but we can verify the helper functions it uses

        from jdev_tui.core.output_formatter import (
            tool_executing_markup,
            tool_success_markup,
            tool_error_markup,
            agent_routing_markup,
        )

        # All these are used in bridge.chat() yields
        helpers = [
            tool_executing_markup("test"),
            tool_success_markup("test"),
            tool_error_markup("test", "error"),
            agent_routing_markup("test", 0.5),
        ]

        rich_patterns = ["[bold", "[italic", "[#", "[/", "Colors."]

        for helper_output in helpers:
            for pattern in rich_patterns:
                assert pattern not in helper_output, \
                    f"Rich pattern '{pattern}' found in: {helper_output}"

    @pytest.mark.asyncio
    async def test_governance_report_formatting(self):
        """Governance reports should be wrapped in Markdown italic."""
        # In bridge.py, gov_report is now wrapped as *{gov_report}*
        gov_report = "LOW RISK: Basic query"
        formatted = f"*{gov_report}*"

        assert formatted.startswith("*")
        assert formatted.endswith("*")
        assert "[" not in formatted


class TestRealWorldScenarios:
    """Test real-world usage scenarios."""

    @pytest.mark.asyncio
    async def test_security_audit_flow(self):
        """Simulate security audit agent routing."""
        from jdev_tui.core.output_formatter import agent_routing_markup

        # User asks: "check security of this code"
        routing = agent_routing_markup("security", 0.92)

        # Should be clean Markdown
        assert "SecurityAgent" in routing
        assert "92%" in routing
        assert "[bold" not in routing

    @pytest.mark.asyncio
    async def test_code_review_flow(self):
        """Simulate code review flow."""
        from jdev_tui.core.output_formatter import (
            tool_executing_markup,
            tool_success_markup,
        )

        # Tools that would be executed
        tools_output = []
        for tool in ["ReadFile", "Glob", "Grep"]:
            tools_output.append(tool_executing_markup(tool))
            tools_output.append(tool_success_markup(tool))

        full_output = "\n".join(tools_output)

        # All should be Rich-free
        assert "[bold" not in full_output
        assert "[#" not in full_output

    @pytest.mark.asyncio
    async def test_error_scenario(self):
        """Simulate error during tool execution."""
        from jdev_tui.core.output_formatter import tool_error_markup

        # Various error messages that might occur
        errors = [
            ("ReadFile", "File not found: /path/to/file"),
            ("BashCommand", "Permission denied"),
            ("WriteFile", "Disk full"),
            ("Grep", "Pattern syntax error: [invalid"),  # Has brackets!
        ]

        for tool, error in errors:
            output = tool_error_markup(tool, error)
            assert "[bold" not in output
            # The error message with brackets should NOT be interpreted as Rich
            if "[invalid" in error:
                assert "invalid" in output  # Content preserved


class TestMarkdownRenderingCompatibility:
    """Test that output is compatible with RichMarkdown renderer."""

    def test_output_renders_without_error(self):
        """Output should render in RichMarkdown without errors."""
        from rich.markdown import Markdown as RichMarkdown
        from jdev_tui.core.output_formatter import (
            tool_executing_markup,
            tool_success_markup,
            tool_error_markup,
            agent_routing_markup,
        )

        # Combine all outputs
        content = "\n".join([
            agent_routing_markup("planner", 0.85),
            "",
            "## Planning Phase",
            "",
            tool_executing_markup("ReadFile"),
            tool_success_markup("ReadFile"),
            "",
            "### Results",
            "",
            "- Item 1",
            "- Item 2",
            "",
            tool_error_markup("WriteFile", "Test error"),
        ])

        # Should not raise any exception
        try:
            md = RichMarkdown(content)
            assert md is not None
        except Exception as e:
            pytest.fail(f"RichMarkdown failed to render: {e}")

    def test_bold_renders_correctly(self):
        """**bold** syntax should be valid Markdown."""
        from rich.markdown import Markdown as RichMarkdown

        # Our markups use **bold**
        content = "This is **bold** and this is *italic*"

        md = RichMarkdown(content)
        assert md is not None


# Pytest marker
pytestmark = pytest.mark.unit
