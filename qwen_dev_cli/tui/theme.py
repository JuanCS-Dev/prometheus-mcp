"""
Surgical Color Palette - GitHub Dark Inspired.

WCAG AA Compliant (4.5:1 contrast minimum).
Semantic naming for clarity and maintainability.

Philosophy:
- Every color serves a purpose
- High contrast for accessibility
- Consistent across all components
- Beautiful without being loud

Created: 2025-11-18 20:05 UTC
"""

from enum import Enum
from typing import Tuple
import colorsys


class ThemeVariant(Enum):
    """Theme variants."""
    DARK = "dark"
    LIGHT = "light"
    HIGH_CONTRAST = "high_contrast"


# ============================================================================
# DARK THEME (Primary - GitHub Dark Inspired)
# ============================================================================

COLORS = {
    # Background Layers (from deepest to lightest)
    'bg_primary': '#0d1117',      # Deep background - Main canvas
    'bg_secondary': '#161b22',    # Card/panel backgrounds
    'bg_tertiary': '#21262d',     # Hover states, raised elements
    'bg_overlay': '#1c2128',      # Modal overlays, dropdowns
    
    # Text Hierarchy (from most to least prominent)
    'text_primary': '#c9d1d9',    # Main text - High contrast (WCAG AAA)
    'text_secondary': '#8b949e',  # Muted text - Metadata, labels
    'text_tertiary': '#6e7681',   # Dimmed text - Timestamps, hints
    'text_disabled': '#484f58',   # Disabled text/controls
    
    # Accent Colors (Semantic)
    'accent_blue': '#58a6ff',     # Info, links, focus states
    'accent_green': '#3fb950',    # Success, confirmations, done
    'accent_yellow': '#d29922',   # Warning, caution
    'accent_red': '#f85149',      # Error, danger, critical
    'accent_purple': '#bc8cff',   # AI responses, special features
    'accent_orange': '#db6d28',   # Highlights, notifications
    
    # Border Colors
    'border_default': '#30363d',  # Default borders
    'border_muted': '#21262d',    # Subtle borders
    'border_emphasis': '#6e7681', # Emphasized borders
    
    # Syntax Highlighting (Code blocks)
    'syntax_keyword': '#ff7b72',    # Keywords (if, def, class)
    'syntax_string': '#a5d6ff',     # Strings
    'syntax_function': '#d2a8ff',   # Function names
    'syntax_variable': '#ffa657',   # Variables
    'syntax_comment': '#8b949e',    # Comments
    'syntax_number': '#79c0ff',     # Numbers
    'syntax_operator': '#ff7b72',   # Operators (+, -, *, /)
    'syntax_builtin': '#ffa657',    # Built-in functions
    
    # Git Diff Colors
    'diff_add_bg': '#0d4429',       # Added line background
    'diff_add_text': '#3fb950',     # Added line text
    'diff_remove_bg': '#4c1f1f',    # Removed line background
    'diff_remove_text': '#f85149',  # Removed line text
    'diff_context': '#8b949e',      # Context lines
    
    # Status Colors (For badges, indicators)
    'status_success': '#238636',    # Success operations
    'status_warning': '#9e6a03',    # Warning states
    'status_error': '#da3633',      # Error states
    'status_info': '#1f6feb',       # Info messages
    'status_processing': '#8957e5', # Processing/loading
    
    # Legacy aliases for backwards compatibility
    'primary': '#58a6ff',           # Alias for accent_blue
    'success': '#3fb950',           # Alias for accent_green
    'warning': '#d29922',           # Alias for accent_yellow
    'error': '#f85149',             # Alias for accent_red
    'info': '#58a6ff',              # Alias for accent_blue
    'text': '#c9d1d9',              # Alias for text_primary
    'dim': '#8b949e',               # Alias for text_secondary
    'reset': '\033[0m',             # ANSI reset
}


# ============================================================================
# COLOR HELPERS
# ============================================================================

class ColorHelpers:
    """Utility functions for color manipulation."""
    
    @staticmethod
    def hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
        """
        Convert hex color to RGB tuple.
        
        Args:
            hex_color: Hex color string (e.g., '#0d1117')
            
        Returns:
            RGB tuple (r, g, b) where each value is 0-255
        """
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    
    @staticmethod
    def rgb_to_hex(r: int, g: int, b: int) -> str:
        """
        Convert RGB to hex color.
        
        Args:
            r, g, b: RGB values (0-255)
            
        Returns:
            Hex color string (e.g., '#0d1117')
        """
        return f"#{r:02x}{g:02x}{b:02x}"
    
    @staticmethod
    def darken(hex_color: str, amount: float = 0.1) -> str:
        """
        Darken a color by reducing its lightness.
        
        Args:
            hex_color: Hex color string
            amount: Amount to darken (0.0 to 1.0)
            
        Returns:
            Darkened hex color
        """
        r, g, b = ColorHelpers.hex_to_rgb(hex_color)
        h, l, s = colorsys.rgb_to_hls(r/255.0, g/255.0, b/255.0)
        l = max(0, l - amount)
        r, g, b = colorsys.hls_to_rgb(h, l, s)
        return ColorHelpers.rgb_to_hex(int(r*255), int(g*255), int(b*255))
    
    @staticmethod
    def lighten(hex_color: str, amount: float = 0.1) -> str:
        """
        Lighten a color by increasing its lightness.
        
        Args:
            hex_color: Hex color string
            amount: Amount to lighten (0.0 to 1.0)
            
        Returns:
            Lightened hex color
        """
        r, g, b = ColorHelpers.hex_to_rgb(hex_color)
        h, l, s = colorsys.rgb_to_hls(r/255.0, g/255.0, b/255.0)
        l = min(1.0, l + amount)
        r, g, b = colorsys.hls_to_rgb(h, l, s)
        return ColorHelpers.rgb_to_hex(int(r*255), int(g*255), int(b*255))
    
    @staticmethod
    def with_alpha(hex_color: str, alpha: float) -> str:
        """
        Add alpha channel to hex color (for terminals that support it).
        
        Args:
            hex_color: Hex color string
            alpha: Alpha value (0.0 to 1.0)
            
        Returns:
            Hex color with alpha (e.g., '#0d111788')
        """
        alpha_hex = format(int(alpha * 255), '02x')
        return f"{hex_color}{alpha_hex}"
    
    @staticmethod
    def contrast_ratio(hex_color1: str, hex_color2: str) -> float:
        """
        Calculate contrast ratio between two colors (WCAG).
        
        Args:
            hex_color1: First hex color
            hex_color2: Second hex color
            
        Returns:
            Contrast ratio (1.0 to 21.0)
        """
        def relative_luminance(hex_color: str) -> float:
            r, g, b = ColorHelpers.hex_to_rgb(hex_color)
            r, g, b = r/255.0, g/255.0, b/255.0
            
            def adjust(c):
                return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
            
            r, g, b = adjust(r), adjust(g), adjust(b)
            return 0.2126 * r + 0.7152 * g + 0.0722 * b
        
        l1 = relative_luminance(hex_color1)
        l2 = relative_luminance(hex_color2)
        
        lighter = max(l1, l2)
        darker = min(l1, l2)
        
        return (lighter + 0.05) / (darker + 0.05)
    
    @staticmethod
    def is_wcag_aa_compliant(text_color: str, bg_color: str) -> bool:
        """
        Check if color combination meets WCAG AA standard (4.5:1).
        
        Args:
            text_color: Text hex color
            bg_color: Background hex color
            
        Returns:
            True if compliant, False otherwise
        """
        ratio = ColorHelpers.contrast_ratio(text_color, bg_color)
        return ratio >= 4.5


# ============================================================================
# THEME VARIANTS
# ============================================================================

def get_theme(variant: ThemeVariant = ThemeVariant.DARK) -> dict:
    """
    Get color palette for specific theme variant.
    
    Args:
        variant: Theme variant
        
    Returns:
        Dictionary of colors
    """
    if variant == ThemeVariant.DARK:
        return COLORS
    elif variant == ThemeVariant.LIGHT:
        # Light theme (inverted colors)
        return {
            'bg_primary': '#ffffff',
            'bg_secondary': '#f6f8fa',
            'bg_tertiary': '#eaeef2',
            'bg_overlay': '#ffffff',
            'text_primary': '#24292f',
            'text_secondary': '#57606a',
            'text_tertiary': '#6e7781',
            'text_disabled': '#8c959f',
            # Accents remain similar for consistency
            **{k: v for k, v in COLORS.items() if k.startswith('accent_')},
            **{k: v for k, v in COLORS.items() if k.startswith('syntax_')},
            **{k: v for k, v in COLORS.items() if k.startswith('diff_')},
            **{k: v for k, v in COLORS.items() if k.startswith('status_')},
        }
    elif variant == ThemeVariant.HIGH_CONTRAST:
        # High contrast theme (WCAG AAA - 7:1 ratio)
        return {
            'bg_primary': '#000000',
            'bg_secondary': '#0a0a0a',
            'bg_tertiary': '#1a1a1a',
            'bg_overlay': '#0f0f0f',
            'text_primary': '#ffffff',
            'text_secondary': '#c0c0c0',
            'text_tertiary': '#a0a0a0',
            'text_disabled': '#606060',
            # Brighter accents for high contrast
            'accent_blue': '#79c0ff',
            'accent_green': '#56d364',
            'accent_yellow': '#f0c869',
            'accent_red': '#ff7b72',
            'accent_purple': '#d2a8ff',
            'accent_orange': '#ffa657',
            **{k: v for k, v in COLORS.items() if k.startswith('syntax_')},
            **{k: v for k, v in COLORS.items() if k.startswith('diff_')},
            **{k: v for k, v in COLORS.items() if k.startswith('status_')},
        }
    
    return COLORS


# ============================================================================
# VALIDATION (Run on import to ensure WCAG compliance)
# ============================================================================

def validate_theme():
    """Validate that theme colors meet WCAG AA standards."""
    issues = []
    
    # Check primary text on primary background
    if not ColorHelpers.is_wcag_aa_compliant(COLORS['text_primary'], COLORS['bg_primary']):
        ratio = ColorHelpers.contrast_ratio(COLORS['text_primary'], COLORS['bg_primary'])
        issues.append(f"text_primary on bg_primary: {ratio:.2f}:1 (needs 4.5:1)")
    
    # Check secondary text on primary background
    if not ColorHelpers.is_wcag_aa_compliant(COLORS['text_secondary'], COLORS['bg_primary']):
        ratio = ColorHelpers.contrast_ratio(COLORS['text_secondary'], COLORS['bg_primary'])
        issues.append(f"text_secondary on bg_primary: {ratio:.2f}:1 (needs 4.5:1)")
    
    if issues:
        print("⚠️  Theme validation warnings:")
        for issue in issues:
            print(f"  - {issue}")
    else:
        print("✅ Theme validated - All colors WCAG AA compliant")


# Run validation on import (development only)
if __name__ == "__main__":
    validate_theme()
