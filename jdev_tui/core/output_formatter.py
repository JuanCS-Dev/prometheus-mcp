"""
Output Formatter - Rich Panel formatting for LLM responses and tool results.
============================================================================

Provides beautiful, consistent formatting for:
- LLM responses (orange bordered panels)
- Tool execution results (green/red panels)
- Code blocks with syntax highlighting
- Error messages

Design Philosophy:
- Panel com borda (rich.Panel) for all major outputs
- Orange (#ff8c00) for AI responses and primary accent
- Green for success, Red for errors (universal conventions)
- Smart truncation for long outputs

Color Palette (JuanCS Dev-Code Brand):
- Primary: #ff8c00 (Dark Orange)
- Secondary: #b8860b (Dark Goldenrod)
- Action: #ff6600 (Orange)
- Success: #1DB954 (Green - universal)
- Error: #DC3545 (Red - universal)
- Warning: #f5a623 (Amber)
- Muted: #6b6b6b (Gray)
"""

from typing import Any, Optional, Tuple
from dataclasses import dataclass
from rich.panel import Panel
from rich.markdown import Markdown
from rich.syntax import Syntax
from rich.text import Text
from rich.table import Table
from rich.console import Group
from rich import box


# =============================================================================
# JUANCS DEV-CODE COLOR PALETTE - Centralized Brand Colors
# =============================================================================

class Colors:
    """JuanCS Dev-Code brand colors - centralized for consistency."""

    # Primary accent - Orange theme
    PRIMARY = "#ff8c00"        # Dark Orange - Main accent
    SECONDARY = "#b8860b"      # Dark Goldenrod - Secondary
    ACTION = "#ff6600"         # Orange - Tool actions

    # Status colors (universal conventions - DO NOT CHANGE)
    SUCCESS = "#1DB954"        # Green - Success
    ERROR = "#DC3545"          # Red - Errors
    WARNING = "#f5a623"        # Amber - Warnings
    INFO = "#3498db"           # Blue - Info

    # Text colors
    MUTED = "#6b6b6b"          # Gray - Muted/dim text
    DIM = "#888888"            # Light gray - Very dim

    # Tool-specific
    TOOL_EXEC = "#ff8c00"      # Tool execution indicator
    TOOL_SUCCESS = "#1DB954"   # Tool success
    TOOL_ERROR = "#DC3545"     # Tool failure

    # Agent-specific
    AGENT = "#ff6600"          # Agent indicator
    ROUTING = "#ff8c00"        # Auto-routing indicator


class Icons:
    """Consistent icons for different output types."""

    # Status icons
    SUCCESS = "✓"
    ERROR = "✗"
    WARNING = "⚠"
    INFO = "ℹ"

    # Action icons
    EXECUTING = "●"
    THINKING = "●"
    ROUTING = "🎯"

    # Tool icons
    TOOL = "⚡"
    FILE = "📄"
    CODE = "💻"
    SEARCH = "🔍"
    GIT = "📦"
    WEB = "🌐"
    BASH = "💲"

    # Agent icons
    AGENT = "🤖"
    PLAN = "📋"
    REVIEW = "👁"
    SECURITY = "🔒"

    # Truncation icons
    EXPAND = "▼"
    COLLAPSE = "▲"
    TRUNCATED = "···"


# =============================================================================
# SMART TRUNCATION SYSTEM - Claude Code / OpenAI Codex Style
# =============================================================================

@dataclass
class TruncationConfig:
    """Configuration for smart truncation behavior."""

    # Content limits (increased from original 5000)
    max_chars: int = 50000           # 50K chars before truncation
    max_lines: int = 500             # Max lines before truncation
    preview_lines: int = 30          # Lines shown when truncated
    preview_chars: int = 3000        # Chars shown when truncated

    # Table limits
    max_table_rows: int = 50         # Max rows visible
    max_table_cols: int = 10         # Max columns visible
    max_cell_width: int = 50         # Max chars per cell

    # Code block limits
    max_code_lines: int = 40         # Code lines before collapse
    code_preview_lines: int = 20     # Lines shown in preview

    # Tool output limits
    max_tool_output: int = 2000      # Tool result chars
    max_error_length: int = 500      # Error message chars


# Global config instance
TRUNCATION_CONFIG = TruncationConfig()


@dataclass
class TruncatedContent:
    """Represents content that may be truncated with expansion capability."""

    content: str
    is_truncated: bool
    full_length: int
    preview_length: int
    content_type: str  # "text", "code", "table", "tool_output"
    expand_hint: str = ""

    @property
    def truncation_info(self) -> str:
        """Human-readable truncation info."""
        if not self.is_truncated:
            return ""
        hidden = self.full_length - self.preview_length
        if self.content_type == "code":
            return f"[{Colors.DIM}]{Icons.TRUNCATED} {hidden} more lines (use /expand to see full)[/{Colors.DIM}]"
        elif self.content_type == "table":
            return f"[{Colors.DIM}]{Icons.TRUNCATED} {hidden} more rows[/{Colors.DIM}]"
        else:
            return f"[{Colors.DIM}]{Icons.TRUNCATED} {hidden} more chars[/{Colors.DIM}]"


class SmartTruncator:
    """
    Intelligent content truncation with expansion support.

    Features:
    - Preserves semantic boundaries (paragraphs, code blocks)
    - Shows truncation indicator with size info
    - Supports /expand command to see full content
    - Different strategies for different content types
    """

    def __init__(self, config: TruncationConfig = None):
        self.config = config or TRUNCATION_CONFIG

    def truncate_text(self, text: str, max_lines: int = None, max_chars: int = None) -> TruncatedContent:
        """
        Truncate text intelligently, preserving paragraph boundaries.

        Args:
            text: Input text
            max_lines: Override max lines
            max_chars: Override max chars

        Returns:
            TruncatedContent with preview and metadata
        """
        max_lines = max_lines or self.config.preview_lines
        max_chars = max_chars or self.config.preview_chars

        lines = text.split('\n')
        full_length = len(text)

        # Check if truncation needed
        if len(lines) <= max_lines and len(text) <= max_chars:
            return TruncatedContent(
                content=text,
                is_truncated=False,
                full_length=full_length,
                preview_length=full_length,
                content_type="text"
            )

        # Truncate by lines first, then by chars
        preview_lines = lines[:max_lines]
        preview = '\n'.join(preview_lines)

        if len(preview) > max_chars:
            preview = preview[:max_chars]
            # Try to break at paragraph/sentence boundary
            last_para = preview.rfind('\n\n')
            last_sentence = max(preview.rfind('. '), preview.rfind('.\n'))

            if last_para > max_chars * 0.6:
                preview = preview[:last_para]
            elif last_sentence > max_chars * 0.6:
                preview = preview[:last_sentence + 1]

        return TruncatedContent(
            content=preview,
            is_truncated=True,
            full_length=full_length,
            preview_length=len(preview),
            content_type="text",
            expand_hint="Use /expand to see full response"
        )

    def truncate_code(self, code: str, language: str = "text") -> TruncatedContent:
        """
        Truncate code blocks, preserving function/class boundaries when possible.

        Args:
            code: Source code
            language: Programming language

        Returns:
            TruncatedContent with preview
        """
        lines = code.split('\n')
        full_lines = len(lines)

        if full_lines <= self.config.code_preview_lines:
            return TruncatedContent(
                content=code,
                is_truncated=False,
                full_length=full_lines,
                preview_length=full_lines,
                content_type="code"
            )

        # Take preview lines
        preview_lines = lines[:self.config.code_preview_lines]

        # Try to end at a logical boundary (empty line, closing brace)
        for i in range(len(preview_lines) - 1, max(10, len(preview_lines) - 10), -1):
            line = preview_lines[i].strip()
            if line == '' or line in ['}', ']', ')', 'end', 'fi', 'done']:
                preview_lines = preview_lines[:i + 1]
                break

        preview = '\n'.join(preview_lines)
        hidden_lines = full_lines - len(preview_lines)

        return TruncatedContent(
            content=preview,
            is_truncated=True,
            full_length=full_lines,
            preview_length=len(preview_lines),
            content_type="code",
            expand_hint=f"# ... {hidden_lines} more lines"
        )

    def truncate_table_data(
        self,
        headers: list,
        rows: list,
        max_rows: int = None,
        max_cols: int = None
    ) -> Tuple[list, list, bool, str]:
        """
        Truncate table data for display.

        Returns:
            (truncated_headers, truncated_rows, is_truncated, info_message)
        """
        max_rows = max_rows or self.config.max_table_rows
        max_cols = max_cols or self.config.max_table_cols

        truncated_cols = False
        truncated_rows = False
        info_parts = []

        # Truncate columns
        if len(headers) > max_cols:
            headers = headers[:max_cols] + [f"...+{len(headers) - max_cols}"]
            rows = [row[:max_cols] + ["..."] for row in rows]
            truncated_cols = True
            info_parts.append(f"{len(headers) - max_cols} cols hidden")

        # Truncate rows
        if len(rows) > max_rows:
            hidden_rows = len(rows) - max_rows
            rows = rows[:max_rows]
            truncated_rows = True
            info_parts.append(f"{hidden_rows} rows hidden")

        # Truncate cell content
        max_width = self.config.max_cell_width
        for i, row in enumerate(rows):
            rows[i] = [
                (cell[:max_width - 3] + "..." if len(str(cell)) > max_width else str(cell))
                for cell in row
            ]

        is_truncated = truncated_cols or truncated_rows
        info = " | ".join(info_parts) if info_parts else ""

        return headers, rows, is_truncated, info

    def truncate_tool_output(self, output: str, tool_name: str = "") -> TruncatedContent:
        """
        Truncate tool execution output.

        Args:
            output: Tool output string
            tool_name: Name of the tool for context

        Returns:
            TruncatedContent with preview
        """
        max_chars = self.config.max_tool_output
        full_length = len(output)

        if full_length <= max_chars:
            return TruncatedContent(
                content=output,
                is_truncated=False,
                full_length=full_length,
                preview_length=full_length,
                content_type="tool_output"
            )

        # For tool output, try to end at a line boundary
        preview = output[:max_chars]
        last_newline = preview.rfind('\n')
        if last_newline > max_chars * 0.7:
            preview = preview[:last_newline]

        return TruncatedContent(
            content=preview,
            is_truncated=True,
            full_length=full_length,
            preview_length=len(preview),
            content_type="tool_output",
            expand_hint=f"... {full_length - len(preview)} more chars"
        )


# Global truncator instance
TRUNCATOR = SmartTruncator()


class OutputFormatter:
    """
    Format outputs with rich.Panel for consistent, beautiful display.

    Usage:
        formatter = OutputFormatter()
        panel = formatter.format_response("Hello world")
        console.print(panel)
    """

    # Default styles - Using JuanCS brand colors
    RESPONSE_BORDER = Colors.PRIMARY   # Orange for AI responses
    SUCCESS_BORDER = Colors.SUCCESS    # Green (universal)
    ERROR_BORDER = Colors.ERROR        # Red (universal)
    WARNING_BORDER = Colors.WARNING    # Amber
    INFO_BORDER = Colors.INFO          # Blue

    # Max content length before truncation (INCREASED - use SmartTruncator for fine control)
    MAX_CONTENT_LENGTH = 50000   # 50K chars (was 5000)
    MAX_LINES = 500              # 500 lines (was 100)

    @staticmethod
    def format_response(
        text: str,
        title: str = "Response",
        border_style: str = None,
        expand: bool = True,
        smart_truncate: bool = True
    ) -> Panel:
        """
        Format LLM response in a styled Panel with smart truncation.

        Args:
            text: Response text (may contain markdown)
            title: Panel title
            border_style: Border color (defaults to PRIMARY orange)
            expand: Whether panel should expand to full width
            smart_truncate: Use SmartTruncator for intelligent truncation

        Returns:
            rich.Panel with formatted content
        """
        border_style = border_style or Colors.PRIMARY

        # Use smart truncation
        if smart_truncate:
            truncated_content = TRUNCATOR.truncate_text(text)
            display_text = truncated_content.content
            is_truncated = truncated_content.is_truncated
            truncation_info = truncated_content.truncation_info
        else:
            # Legacy truncation (fallback)
            is_truncated = False
            if len(text) > OutputFormatter.MAX_CONTENT_LENGTH:
                display_text = text[:OutputFormatter.MAX_CONTENT_LENGTH]
                is_truncated = True
            else:
                display_text = text

            lines = display_text.split('\n')
            if len(lines) > OutputFormatter.MAX_LINES:
                display_text = '\n'.join(lines[:OutputFormatter.MAX_LINES])
                is_truncated = True

            truncation_info = ""

        # Parse as markdown for rich formatting
        try:
            content = Markdown(display_text)
        except Exception:
            # Fallback to plain text
            content = Text(display_text)

        # Build final content with truncation indicator
        if is_truncated and truncation_info:
            final_content = Group(
                content,
                Text(""),  # Spacer
                Text(truncation_info, style=Colors.DIM)
            )
        else:
            final_content = content

        # Build title with optional truncation marker
        title_str = f"[{border_style}]{title}[/{border_style}]"
        if is_truncated:
            title_str += f" [{Colors.DIM}](truncated)[/{Colors.DIM}]"

        return Panel(
            final_content,
            title=title_str,
            border_style=border_style,
            padding=(1, 2),
            expand=expand
        )

    @staticmethod
    def format_tool_result(
        tool_name: str,
        success: bool,
        data: Any = None,
        error: Optional[str] = None
    ) -> Panel:
        """
        Format tool execution result with smart truncation.

        Args:
            tool_name: Name of the executed tool
            success: Whether execution succeeded
            data: Result data (on success)
            error: Error message (on failure)

        Returns:
            rich.Panel with result
        """
        if success:
            style = OutputFormatter.SUCCESS_BORDER
            icon = Icons.SUCCESS
            content_text = str(data) if data else "Success"
        else:
            style = OutputFormatter.ERROR_BORDER
            icon = Icons.ERROR
            content_text = error or "Failed"

        # Smart truncation for tool output
        truncated = TRUNCATOR.truncate_tool_output(content_text, tool_name)
        display_text = truncated.content

        # Add truncation indicator if needed
        if truncated.is_truncated:
            display_text += f"\n\n[{Colors.DIM}]{Icons.TRUNCATED} {truncated.expand_hint}[/{Colors.DIM}]"

        return Panel(
            Text(display_text),
            title=f"[{style}]{icon} {tool_name}[/{style}]",
            border_style=style,
            padding=(0, 1),
            expand=False
        )

    @staticmethod
    def format_code_block(
        code: str,
        language: str = "python",
        title: Optional[str] = None,
        line_numbers: bool = True,
        show_line_count: bool = True
    ) -> Panel:
        """
        Format code with syntax highlighting in a Panel with smart truncation.

        Args:
            code: Source code
            language: Programming language for highlighting
            title: Optional title (defaults to language)
            line_numbers: Whether to show line numbers
            show_line_count: Show total line count in title

        Returns:
            rich.Panel with syntax highlighted code
        """
        # Smart truncation for code
        truncated = TRUNCATOR.truncate_code(code, language)
        display_code = truncated.content
        total_lines = truncated.full_length

        # Add truncation comment if needed
        if truncated.is_truncated:
            display_code += f"\n\n{truncated.expand_hint}"

        syntax = Syntax(
            display_code,
            language,
            theme="dracula",
            line_numbers=line_numbers,
            word_wrap=True,
            background_color="#1e1e2e"
        )

        # Build title with line count
        display_title = title or language.upper()
        if show_line_count:
            display_title += f" ({total_lines} lines)"
        if truncated.is_truncated:
            display_title += f" [{Colors.DIM}]truncated[/{Colors.DIM}]"

        return Panel(
            syntax,
            title=f"[{Colors.PRIMARY}]{Icons.CODE} {display_title}[/{Colors.PRIMARY}]",
            border_style=Colors.PRIMARY,
            padding=(0, 1)
        )

    @staticmethod
    def format_table(
        headers: list,
        rows: list,
        title: str = None,
        show_row_count: bool = True
    ) -> Panel:
        """
        Format a table with smart truncation for rows, columns, and cell content.

        Args:
            headers: List of column headers
            rows: List of row data (each row is a list)
            title: Optional table title
            show_row_count: Show total row count in title

        Returns:
            rich.Panel containing the formatted table
        """
        total_rows = len(rows)
        total_cols = len(headers)

        # Smart truncation
        headers, rows, is_truncated, truncation_info = TRUNCATOR.truncate_table_data(
            headers, rows
        )

        # Build Rich Table
        table = Table(
            box=box.ROUNDED,
            header_style=f"bold {Colors.PRIMARY}",
            row_styles=["", Colors.DIM],
            padding=(0, 1),
            collapse_padding=True,
            show_lines=False
        )

        # Add columns with max width
        for header in headers:
            table.add_column(
                header,
                style=Colors.SECONDARY,
                max_width=TRUNCATION_CONFIG.max_cell_width,
                overflow="ellipsis"
            )

        # Add rows
        for row in rows:
            table.add_row(*[str(cell) for cell in row])

        # Build title
        title_parts = []
        if title:
            title_parts.append(title)
        if show_row_count:
            title_parts.append(f"{total_rows} rows x {total_cols} cols")
        if is_truncated:
            title_parts.append(f"[{Colors.DIM}]{truncation_info}[/{Colors.DIM}]")

        display_title = " | ".join(title_parts) if title_parts else "Table"

        return Panel(
            table,
            title=f"[{Colors.PRIMARY}]{display_title}[/{Colors.PRIMARY}]",
            border_style=Colors.PRIMARY,
            padding=(0, 1)
        )

    @staticmethod
    def format_error(message: str, title: str = "Error") -> Panel:
        """Format error message with smart truncation."""
        # Truncate very long errors
        if len(message) > TRUNCATION_CONFIG.max_error_length:
            display_msg = message[:TRUNCATION_CONFIG.max_error_length]
            display_msg += f"\n\n[{Colors.DIM}]{Icons.TRUNCATED} ... {len(message) - TRUNCATION_CONFIG.max_error_length} more chars[/{Colors.DIM}]"
        else:
            display_msg = message

        return Panel(
            Text(display_msg, style=Colors.ERROR),
            title=f"[{Colors.ERROR}]{Icons.ERROR} {title}[/{Colors.ERROR}]",
            border_style=Colors.ERROR,
            padding=(0, 1)
        )

    @staticmethod
    def format_success(message: str, title: str = "Success") -> Panel:
        """Format success message."""
        return Panel(
            Text(message, style=Colors.SUCCESS),
            title=f"[{Colors.SUCCESS}]{Icons.SUCCESS} {title}[/{Colors.SUCCESS}]",
            border_style=Colors.SUCCESS,
            padding=(0, 1)
        )

    @staticmethod
    def format_warning(message: str, title: str = "Warning") -> Panel:
        """Format warning message."""
        return Panel(
            Text(message, style=Colors.WARNING),
            title=f"[{Colors.WARNING}]{Icons.WARNING} {title}[/{Colors.WARNING}]",
            border_style=Colors.WARNING,
            padding=(0, 1)
        )

    @staticmethod
    def format_info(message: str, title: str = "Info") -> Panel:
        """Format info message."""
        return Panel(
            Text(message, style=Colors.INFO),
            title=f"[{Colors.INFO}]{Icons.INFO} {title}[/{Colors.INFO}]",
            border_style=Colors.INFO,
            padding=(0, 1)
        )

    @staticmethod
    def format_action(action: str) -> Text:
        """Format action indicator with orange color."""
        text = Text()
        text.append(f"{Icons.EXECUTING} ", style=f"bold {Colors.ACTION}")
        text.append(action, style=Colors.MUTED)
        return text

    @staticmethod
    def format_thinking() -> Text:
        """Format thinking indicator with orange color."""
        text = Text()
        text.append(f"{Icons.THINKING} ", style=f"bold {Colors.ACTION}")
        text.append("Thinking...", style=f"italic {Colors.MUTED}")
        return text

    # =========================================================================
    # TOOL EXECUTION FORMATTING - Rich formatting for tool operations
    # =========================================================================

    @staticmethod
    def format_tool_executing(tool_name: str, args: dict = None) -> Text:
        """Format tool execution indicator."""
        text = Text()
        text.append(f"{Icons.TOOL} ", style=f"bold {Colors.TOOL_EXEC}")
        text.append("Executing: ", style=Colors.MUTED)
        text.append(tool_name, style=f"bold {Colors.PRIMARY}")
        if args:
            # Show truncated args
            args_str = str(args)[:50] + "..." if len(str(args)) > 50 else str(args)
            text.append(f" {args_str}", style=Colors.DIM)
        return text

    @staticmethod
    def format_tool_success(tool_name: str, result: str = None) -> Text:
        """Format tool success message."""
        text = Text()
        text.append(f"{Icons.SUCCESS} ", style=f"bold {Colors.SUCCESS}")
        text.append(tool_name, style=f"bold {Colors.PRIMARY}")
        text.append(": ", style=Colors.MUTED)
        text.append("Success", style=Colors.SUCCESS)
        if result:
            result_str = str(result)[:100] + "..." if len(str(result)) > 100 else str(result)
            text.append(f" - {result_str}", style=Colors.DIM)
        return text

    @staticmethod
    def format_tool_error(tool_name: str, error: str) -> Text:
        """Format tool error message."""
        text = Text()
        text.append(f"{Icons.ERROR} ", style=f"bold {Colors.ERROR}")
        text.append(tool_name, style=f"bold {Colors.PRIMARY}")
        text.append(": ", style=Colors.MUTED)
        text.append(error[:200], style=Colors.ERROR)
        return text

    # =========================================================================
    # AGENT FORMATTING - Rich formatting for agent operations
    # =========================================================================

    @staticmethod
    def format_agent_routing(agent_name: str, confidence: float) -> Text:
        """Format agent auto-routing message."""
        text = Text()
        text.append(f"{Icons.ROUTING} ", style=f"bold {Colors.ROUTING}")
        text.append("Auto-routing to ", style=Colors.MUTED)
        text.append(f"{agent_name.title()}Agent", style=f"bold {Colors.AGENT}")
        text.append(f" (confidence: {int(confidence*100)}%)", style=Colors.DIM)
        return text

    @staticmethod
    def format_agent_description(description: str) -> Text:
        """Format agent description."""
        text = Text()
        text.append("   ", style="")
        text.append(description, style=f"italic {Colors.SECONDARY}")
        return text

    @staticmethod
    def format_governance_report(report: str) -> Text:
        """Format governance observation report."""
        text = Text()
        text.append("🛡️ ", style="bold")
        text.append(report, style=Colors.MUTED)
        return text


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def response_panel(text: str, title: str = "Response") -> Panel:
    """Quick helper for response panels."""
    return OutputFormatter.format_response(text, title)


def tool_panel(name: str, success: bool, data: Any = None, error: str = None) -> Panel:
    """Quick helper for tool result panels."""
    return OutputFormatter.format_tool_result(name, success, data, error)


def code_panel(code: str, language: str = "python") -> Panel:
    """Quick helper for code panels."""
    return OutputFormatter.format_code_block(code, language)


# =============================================================================
# STREAM-SAFE MARKUP HELPERS - Plain text with emojis for streaming
# =============================================================================
# IMPORTANT: These return PLAIN TEXT, not Rich markup!
# The streaming system uses RichMarkdown which does NOT process [bold] tags.
# Use emojis and plain text for Claude-Code-Web style output.

def tool_executing_markup(tool_name: str) -> str:
    """Return plain text for tool execution (streaming safe)."""
    return f"• **{tool_name}**"


def tool_success_markup(tool_name: str) -> str:
    """Return plain text for tool success (streaming safe)."""
    return f"✓ {tool_name}: Success"


def tool_error_markup(tool_name: str, error: str) -> str:
    """Return plain text for tool error (streaming safe)."""
    return f"✗ {tool_name}: {error[:100]}"


def agent_routing_markup(agent_name: str, confidence: float) -> str:
    """Return plain text for agent routing (streaming safe)."""
    confidence_pct = int(confidence * 100)
    return f"🔀 Auto-routing to **{agent_name.title()}Agent** (confidence: {confidence_pct}%)"
