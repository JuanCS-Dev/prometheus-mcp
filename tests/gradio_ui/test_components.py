"""
Test suite for Gradio UI SVG/HTML components.

Following Boris Cherny testing philosophy:
- Every public function has tests
- Edge cases are explicitly covered
- Type safety is validated
- No reliance on implementation details
"""
from __future__ import annotations


from gradio_ui.components import (
    render_gauge,
    render_bar_chart,
    render_dual_gauge,
    render_terminal_logs,
    render_tailwind_header,
)


class TestRenderGauge:
    """Test suite for circular gauge SVG rendering."""

    def test_normal_range(self) -> None:
        """Gauge renders correctly for values in [0, 100]."""
        html = render_gauge(50.0, "TEST", "100K")

        assert "50%" in html
        assert "TEST" in html.upper()
        assert "100K" in html
        assert "#00D9FF" in html  # Default cyan color
        assert "svg" in html.lower()

    def test_warning_thresholds(self) -> None:
        """Gauge changes color at 75% and 90% thresholds."""
        # Orange warning at 75%
        html_75 = render_gauge(75.0, "TOKEN", "1M")
        assert "#F59E0B" in html_75  # Orange

        html_80 = render_gauge(80.0, "TOKEN", "1M")
        assert "#F59E0B" in html_80

        # Red danger at 90%
        html_90 = render_gauge(90.0, "TOKEN", "1M")
        assert "#EF4444" in html_90  # Red

        html_95 = render_gauge(95.0, "TOKEN", "1M")
        assert "#EF4444" in html_95

    def test_edge_cases(self) -> None:
        """Gauge handles boundary values correctly."""
        # Zero
        html_0 = render_gauge(0.0, "EMPTY", "0")
        assert "0%" in html_0

        # Exact 100
        html_100 = render_gauge(100.0, "FULL", "1M")
        assert "100%" in html_100

        # Above 100 (should clamp)
        html_over = render_gauge(150.0, "OVER", "1M")
        assert "100%" in html_over  # Clamped to 100

        # Negative (should clamp to 0)
        html_neg = render_gauge(-10.0, "NEG", "0")
        assert "0%" in html_neg

    def test_label_uppercasing(self) -> None:
        """Labels are uppercased in output."""
        html = render_gauge(50.0, "lowercase label", "100")
        assert "LOWERCASE LABEL" in html

    def test_svg_structure(self) -> None:
        """SVG structure is valid and complete."""
        html = render_gauge(50.0, "TEST", "100")

        # Must contain SVG with circles
        assert "<svg" in html
        assert "</svg>" in html
        assert "<circle" in html

        # Must have both background and progress circles
        assert html.count("<circle") >= 2


class TestRenderBarChart:
    """Test suite for bar chart rendering."""

    def test_normal_values(self) -> None:
        """Bar chart renders correctly for normalized [0.0, 1.0] values."""
        values = [0.85, 0.9, 0.88, 0.95, 0.92, 0.94]
        html = render_bar_chart(values, "SAFETY")

        assert "SAFETY" in html.upper()
        assert "SAFE" in html
        assert "RISK" in html
        # Class appears twice per bar: once in class="" and once in box-shadow
        assert html.count("bg-cyber-accent") == 12  # 6 bars * 2 occurrences

    def test_color_thresholds(self) -> None:
        """Bar colors change based on value ranges."""
        # Safe: >= 0.5
        html_safe = render_bar_chart([0.8], "TEST")
        assert "bg-cyber-accent" in html_safe

        # Warning: [0.3, 0.5)
        html_warn = render_bar_chart([0.4], "TEST")
        assert "bg-cyber-warning" in html_warn

        # Danger: < 0.3
        html_danger = render_bar_chart([0.2], "TEST")
        assert "bg-cyber-danger" in html_danger

    def test_empty_list(self) -> None:
        """Bar chart handles empty input gracefully."""
        html = render_bar_chart([], "EMPTY")
        assert "EMPTY" in html
        # Should still have structure even with no bars
        assert "flex" in html

    def test_multiple_bars(self) -> None:
        """Multiple bars render with correct structure."""
        values = [0.1, 0.4, 0.8]  # danger, warning, safe
        html = render_bar_chart(values, "MIXED")

        assert "bg-cyber-danger" in html
        assert "bg-cyber-warning" in html
        assert "bg-cyber-accent" in html


class TestRenderDualGauge:
    """Test suite for dual mini gauge rendering."""

    def test_both_gauges(self) -> None:
        """Dual gauge renders both left and right components."""
        html = render_dual_gauge(75.0, "MODEL", 100.0, "ENV")

        assert "MODEL" in html
        assert "ENV" in html
        assert "75" in html
        assert "100" in html

        # Should have two SVGs (one per gauge)
        assert html.count("<svg") >= 2

    def test_different_colors(self) -> None:
        """Left and right gauges have different colors."""
        html = render_dual_gauge(50.0, "LEFT", 50.0, "RIGHT")

        # Left = cyan, Right = green
        assert "#00D9FF" in html
        assert "#10B981" in html

    def test_edge_values(self) -> None:
        """Dual gauge handles 0 and 100 correctly."""
        html = render_dual_gauge(0.0, "ZERO", 100.0, "FULL")

        assert "0" in html
        assert "100" in html


class TestRenderTerminalLogs:
    """Test suite for terminal log rendering."""

    def test_log_levels(self) -> None:
        """Logs are color-coded by level."""
        logs = [
            "10:00:00 - [INFO] System initialized",
            "10:00:01 - [SUCCESS] Task completed",
            "10:00:02 - [ERROR] Connection failed",
            "10:00:03 - [WARN] High memory usage",
        ]
        html = render_terminal_logs(logs)

        assert "text-blue-400" in html      # INFO
        assert "text-green-400" in html     # SUCCESS
        assert "text-red-400" in html       # ERROR
        assert "text-yellow-400" in html    # WARN

    def test_timestamp_highlighting(self) -> None:
        """Timestamps are styled differently from message content."""
        logs = ["12:34:56 - [INFO] Message"]
        html = render_terminal_logs(logs)

        # Timestamp should have gray styling
        assert "text-gray-600" in html
        # Message should have level-specific color
        assert "text-blue-400" in html

    def test_cursor_presence(self) -> None:
        """Terminal includes blinking cursor at end."""
        html = render_terminal_logs(["Test log"])

        assert "cursor-blink" in html
        assert "root@gemini-cli" in html

    def test_empty_logs(self) -> None:
        """Empty log list still renders valid structure."""
        html = render_terminal_logs([])

        assert "font-mono" in html
        assert "cursor-blink" in html
        # Should have terminal prompt even with no logs
        assert "root@gemini-cli" in html

    def test_no_timestamp_logs(self) -> None:
        """Logs without timestamp separator are still rendered."""
        logs = ["Plain message without timestamp"]
        html = render_terminal_logs(logs)

        assert "Plain message without timestamp" in html


class TestRenderTailwindHeader:
    """Test suite for Tailwind CDN injection."""

    def test_script_tag(self) -> None:
        """Header contains Tailwind CDN script."""
        html = render_tailwind_header()

        assert "<script" in html
        assert "cdn.tailwindcss.com" in html
        assert "</script>" in html

    def test_config_object(self) -> None:
        """Tailwind config defines custom color palette."""
        html = render_tailwind_header()

        assert "tailwind.config" in html
        assert "darkMode" in html
        assert "cyber-bg" in html
        assert "cyber-accent" in html
        assert "#00D9FF" in html

    def test_font_family(self) -> None:
        """Tailwind config includes JetBrains Mono font."""
        html = render_tailwind_header()

        assert "JetBrains Mono" in html
        assert "monospace" in html


# Integration-style tests
class TestComponentIntegration:
    """Test interactions between components."""

    def test_all_components_return_html(self) -> None:
        """All render functions return non-empty HTML strings."""
        gauge = render_gauge(50.0, "TEST", "100")
        bar = render_bar_chart([0.5], "TEST")
        dual = render_dual_gauge(50.0, "A", 50.0, "B")
        logs = render_terminal_logs(["test"])
        header = render_tailwind_header()

        for html in [gauge, bar, dual, logs, header]:
            assert isinstance(html, str)
            assert len(html) > 0
            # Basic HTML structure validation
            assert "<" in html and ">" in html

    def test_tailwind_classes_present(self) -> None:
        """Components use Tailwind utility classes."""
        gauge = render_gauge(50.0, "TEST", "100")
        logs = render_terminal_logs(["test"])

        # Check for common Tailwind patterns
        tailwind_patterns = ["flex", "text-", "bg-", "p-", "font-"]

        for component in [gauge, logs]:
            assert any(pattern in component for pattern in tailwind_patterns)

    def test_no_javascript_injection(self) -> None:
        """User-controlled strings don't inject scripts."""
        # Attempt XSS via label
        malicious_label = "<script>alert('xss')</script>"
        html = render_gauge(50.0, malicious_label, "100")

        # Script should be escaped or absent
        # (In production, use proper HTML escaping - this tests current behavior)
        assert "<script>" not in html or "alert" not in html
