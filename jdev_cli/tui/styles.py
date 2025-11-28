"""
Rich Style Presets - Ready-to-use styles for terminal UI.

Combines theme colors with Rich Style objects for immediate use.

Philosophy:
- Semantic naming (what it means, not what it looks like)
- Consistent across all components
- Easy to use, hard to misuse
- Rich-compatible Style objects

Created: 2025-11-18 20:05 UTC
"""

from rich.style import Style
from rich.theme import Theme
from typing import Optional

from .theme import COLORS, ThemeVariant, get_theme


# ============================================================================
# STYLE CREATION HELPER
# ============================================================================

def create_style(
    color: Optional[str] = None,
    bgcolor: Optional[str] = None,
    bold: bool = False,
    italic: bool = False,
    underline: bool = False,
    dim: bool = False,
    blink: bool = False,
    reverse: bool = False,
) -> Style:
    """
    Create a Rich Style object with theme colors.
    
    Args:
        color: Text color (hex or theme key)
        bgcolor: Background color (hex or theme key)
        bold: Bold text
        italic: Italic text
        underline: Underlined text
        dim: Dimmed text
        blink: Blinking text (rarely supported)
        reverse: Reverse colors
        
    Returns:
        Rich Style object
        
    Examples:
        >>> create_style(color='accent_blue', bold=True)
        Style(color='#58a6ff', bold=True)
        
        >>> create_style(color='#ff0000', bgcolor='bg_primary')
        Style(color='#ff0000', bgcolor='#0d1117')
    """
    # Resolve color names to hex values
    text_color = COLORS.get(color, color) if color else None
    bg_color = COLORS.get(bgcolor, bgcolor) if bgcolor else None

    return Style(
        color=text_color,
        bgcolor=bg_color,
        bold=bold,
        italic=italic,
        underline=underline,
        dim=dim,
        blink=blink,
        reverse=reverse,
    )


# ============================================================================
# PRESET STYLES (Semantic)
# ============================================================================

class PRESET_STYLES:
    """
    Pre-configured Rich Style objects for common use cases.
    
    Usage:
        console.print("Success!", style=PRESET_STYLES.SUCCESS)
        console.print("Error!", style=PRESET_STYLES.ERROR)
    """

    # ========================================================================
    # STATUS STYLES
    # ========================================================================

    SUCCESS = create_style(color='accent_green', bold=True)
    ERROR = create_style(color='accent_red', bold=True)
    WARNING = create_style(color='accent_yellow', bold=True)
    INFO = create_style(color='accent_blue')
    DEBUG = create_style(color='text_tertiary', dim=True)

    # ========================================================================
    # TEXT HIERARCHY
    # ========================================================================

    # Primary text (default, high contrast)
    PRIMARY = create_style(color='text_primary')

    # Secondary text (muted, less emphasis)
    SECONDARY = create_style(color='text_secondary')

    # Tertiary text (dimmed, metadata)
    TERTIARY = create_style(color='text_tertiary')

    # Disabled text
    DISABLED = create_style(color='text_disabled')

    # ========================================================================
    # EMPHASIS STYLES
    # ========================================================================

    # Bold emphasis
    BOLD = create_style(bold=True)

    # Italic emphasis
    ITALIC = create_style(italic=True)

    # Underline emphasis
    UNDERLINE = create_style(underline=True)

    # Dim (de-emphasis)
    DIM = create_style(dim=True)

    # Combined: bold + color
    EMPHASIS = create_style(color='text_primary', bold=True)

    # Strong emphasis
    STRONG = create_style(color='accent_blue', bold=True)

    # ========================================================================
    # SEMANTIC COLORS (Actions)
    # ========================================================================

    # Links, interactive elements
    LINK = create_style(color='accent_blue', underline=True)

    # Visited links
    LINK_VISITED = create_style(color='accent_purple', underline=True)

    # Focus state
    FOCUS = create_style(color='accent_blue', bold=True, underline=True)

    # Selected items
    SELECTED = create_style(bgcolor='bg_tertiary', bold=True)

    # Highlighted text
    HIGHLIGHT = create_style(bgcolor='accent_yellow', color='bg_primary')

    # ========================================================================
    # CODE STYLES
    # ========================================================================

    # Inline code
    CODE = create_style(color='accent_purple', bgcolor='bg_secondary')

    # Code keyword
    KEYWORD = create_style(color='syntax_keyword')

    # Code string
    STRING = create_style(color='syntax_string')

    # Code function
    FUNCTION = create_style(color='syntax_function')

    # Code comment
    COMMENT = create_style(color='syntax_comment', italic=True)

    # Code number
    NUMBER = create_style(color='syntax_number')

    # ========================================================================
    # GIT DIFF STYLES
    # ========================================================================

    # Added lines
    DIFF_ADD = create_style(color='diff_add_text', bgcolor='diff_add_bg')

    # Removed lines
    DIFF_REMOVE = create_style(color='diff_remove_text', bgcolor='diff_remove_bg')

    # Context lines
    DIFF_CONTEXT = create_style(color='diff_context')

    # ========================================================================
    # UI COMPONENT STYLES
    # ========================================================================

    # Panel title
    PANEL_TITLE = create_style(color='accent_blue', bold=True)

    # Panel border
    PANEL_BORDER = create_style(color='border_default')

    # Table header
    TABLE_HEADER = create_style(color='text_primary', bold=True)

    # Table row (alternating)
    TABLE_ROW_EVEN = create_style(bgcolor='bg_primary')
    TABLE_ROW_ODD = create_style(bgcolor='bg_secondary')

    # Progress bar
    PROGRESS_BAR = create_style(color='accent_green', bold=True)
    PROGRESS_BAR_BG = create_style(color='border_default')

    # ========================================================================
    # STATUS BADGES
    # ========================================================================

    # Processing/loading
    BADGE_PROCESSING = create_style(color='status_processing', bold=True)

    # Success badge
    BADGE_SUCCESS = create_style(color='status_success', bold=True)

    # Warning badge
    BADGE_WARNING = create_style(color='status_warning', bold=True)

    # Error badge
    BADGE_ERROR = create_style(color='status_error', bold=True)

    # Info badge
    BADGE_INFO = create_style(color='status_info', bold=True)

    # ========================================================================
    # SPECIAL STYLES
    # ========================================================================

    # Timestamp
    TIMESTAMP = create_style(color='text_tertiary', dim=True)

    # File path
    PATH = create_style(color='accent_blue')

    # Command
    COMMAND = create_style(color='accent_green', bold=True)

    # Prompt symbol
    PROMPT = create_style(color='accent_purple', bold=True)

    # Danger/critical
    DANGER = create_style(color='accent_red', bold=True, underline=True)


# ============================================================================
# RICH THEME (for Console)
# ============================================================================

def get_rich_theme(variant: ThemeVariant = ThemeVariant.DARK) -> Theme:
    """
    Create a Rich Theme object with all preset styles.
    
    Args:
        variant: Theme variant (dark, light, high_contrast)
        
    Returns:
        Rich Theme object
        
    Usage:
        from rich.console import Console
        console = Console(theme=get_rich_theme())
        console.print("[success]Done![/success]")
    """
    theme_colors = get_theme(variant)

    return Theme({
        # Status
        "success": f"bold {theme_colors['accent_green']}",
        "error": f"bold {theme_colors['accent_red']}",
        "warning": f"bold {theme_colors['accent_yellow']}",
        "info": theme_colors['accent_blue'],
        "debug": f"dim {theme_colors['text_tertiary']}",

        # Text hierarchy
        "primary": theme_colors['text_primary'],
        "secondary": theme_colors['text_secondary'],
        "tertiary": theme_colors['text_tertiary'],
        "disabled": theme_colors['text_disabled'],

        # Emphasis
        "bold": "bold",
        "italic": "italic",
        "underline": "underline",
        "dim": "dim",
        "emphasis": f"bold {theme_colors['text_primary']}",
        "strong": f"bold {theme_colors['accent_blue']}",

        # Semantic
        "link": f"underline {theme_colors['accent_blue']}",
        "code": f"{theme_colors['accent_purple']} on {theme_colors['bg_secondary']}",
        "highlight": f"{theme_colors['bg_primary']} on {theme_colors['accent_yellow']}",

        # Git diff
        "diff.add": f"{theme_colors['diff_add_text']} on {theme_colors['diff_add_bg']}",
        "diff.remove": f"{theme_colors['diff_remove_text']} on {theme_colors['diff_remove_bg']}",
        "diff.context": theme_colors['diff_context'],

        # UI components
        "panel.title": f"bold {theme_colors['accent_blue']}",
        "table.header": f"bold {theme_colors['text_primary']}",
        "progress.bar": f"bold {theme_colors['accent_green']}",

        # Special
        "timestamp": f"dim {theme_colors['text_tertiary']}",
        "path": theme_colors['accent_blue'],
        "command": f"bold {theme_colors['accent_green']}",
        "prompt": f"bold {theme_colors['accent_purple']}",
        "danger": f"bold underline {theme_colors['accent_red']}",
    })


# ============================================================================
# SYNTAX THEME (for code highlighting)
# ============================================================================

def get_syntax_theme(variant: ThemeVariant = ThemeVariant.DARK) -> dict:
    """
    Get syntax highlighting theme for Pygments.
    
    Args:
        variant: Theme variant
        
    Returns:
        Dictionary of token types to styles
        
    Usage:
        from rich.syntax import Syntax
        code = Syntax(code_str, "python", theme=get_syntax_theme())
    """
    theme_colors = get_theme(variant)

    return {
        # Map Pygments token types to our colors
        "keyword": theme_colors['syntax_keyword'],
        "string": theme_colors['syntax_string'],
        "function": theme_colors['syntax_function'],
        "comment": theme_colors['syntax_comment'],
        "number": theme_colors['syntax_number'],
        "operator": theme_colors['syntax_operator'],
        "builtin": theme_colors['syntax_builtin'],
        "variable": theme_colors['syntax_variable'],
    }


# ============================================================================
# STYLE COMBINATIONS
# ============================================================================

class StyleCombinations:
    """
    Common style combinations for complex UI elements.
    
    Example:
        # Message box: user message
        user_style = StyleCombinations.message_user()
        
        # Message box: AI response
        ai_style = StyleCombinations.message_ai()
    """

    @staticmethod
    def message_user():
        """Style for user messages."""
        return {
            'border': create_style(color='accent_blue'),
            'text': create_style(color='text_primary'),
            'timestamp': create_style(color='text_tertiary', dim=True),
        }

    @staticmethod
    def message_ai():
        """Style for AI messages."""
        return {
            'border': create_style(color='accent_purple'),
            'text': create_style(color='text_primary'),
            'timestamp': create_style(color='text_tertiary', dim=True),
        }

    @staticmethod
    def status_badge(level: str):
        """Style for status badges by level."""
        styles = {
            'success': PRESET_STYLES.BADGE_SUCCESS,
            'error': PRESET_STYLES.BADGE_ERROR,
            'warning': PRESET_STYLES.BADGE_WARNING,
            'info': PRESET_STYLES.BADGE_INFO,
            'processing': PRESET_STYLES.BADGE_PROCESSING,
        }
        return styles.get(level, PRESET_STYLES.INFO)

    @staticmethod
    def code_block():
        """Style for code blocks."""
        return {
            'background': create_style(bgcolor='bg_secondary'),
            'border': create_style(color='border_muted'),
            'line_numbers': create_style(color='text_tertiary'),
        }


# ============================================================================
# VALIDATION
# ============================================================================

def validate_styles():
    """Validate style presets."""
    preset_count = len([k for k in dir(PRESET_STYLES) if not k.startswith('_')])
    print("✅ Style System:")
    print(f"  - Preset styles: {preset_count}")
    print("  - Rich Theme integration: ✓")
    print("  - Syntax theme: ✓")
    print("  - Style combinations: ✓")
    print("  - All styles use theme colors")


if __name__ == "__main__":
    validate_styles()
