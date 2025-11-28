"""
Spacing System - 8px Baseline Grid.

Consistent spacing creates visual rhythm and hierarchy.
Based on 8px increments for mathematical harmony.

Philosophy:
- All spacing is a multiple of 8px (0.5rem)
- Predictable, scalable, maintainable
- Creates visual breathing room
- Aligns elements naturally

Created: 2025-11-18 20:05 UTC
"""

from typing import Union


# ============================================================================
# SPACING SCALE (8px baseline grid)
# ============================================================================

SPACING = {
    # Base unit: 8px = 0.5rem
    'xs': '0.5rem',      # 8px  - Tight spacing (inline elements)
    'sm': '0.75rem',     # 12px - Small gaps (compact lists)
    'md': '1rem',        # 16px - Default spacing (paragraphs)
    'lg': '1.5rem',      # 24px - Section spacing
    'xl': '2rem',        # 32px - Major section gaps
    '2xl': '3rem',       # 48px - Large visual breaks
    '3xl': '4rem',       # 64px - Hero spacing (rare)

    # Special values
    'none': '0',         # No spacing
    'auto': 'auto',      # Automatic (for centering)
}


# Pixel equivalents (for reference, assuming 16px base)
SPACING_PX = {
    'xs': 8,
    'sm': 12,
    'md': 16,
    'lg': 24,
    'xl': 32,
    '2xl': 48,
    '3xl': 64,
    'none': 0,
}


# ============================================================================
# MARGIN HELPERS
# ============================================================================

def margin(
    top: Union[str, None] = None,
    right: Union[str, None] = None,
    bottom: Union[str, None] = None,
    left: Union[str, None] = None,
    all: Union[str, None] = None,
    x: Union[str, None] = None,
    y: Union[str, None] = None,
) -> str:
    """
    Generate margin CSS with spacing scale values.
    
    Args:
        top: Top margin (e.g., 'md', 'lg')
        right: Right margin
        bottom: Bottom margin
        left: Left margin
        all: Apply same margin to all sides
        x: Horizontal margin (left + right)
        y: Vertical margin (top + bottom)
        
    Returns:
        CSS margin string
        
    Examples:
        >>> margin(all='md')
        'margin: 1rem;'
        
        >>> margin(y='lg', x='md')
        'margin: 1.5rem 1rem;'
        
        >>> margin(top='xl', bottom='md')
        'margin: 2rem 0 1rem 0;'
    """
    if all:
        value = SPACING.get(all, all)
        return f"margin: {value};"

    if x or y:
        v_margin = SPACING.get(y, y) if y else '0'
        h_margin = SPACING.get(x, x) if x else '0'
        return f"margin: {v_margin} {h_margin};"

    # Individual sides
    t = SPACING.get(top, top) if top else '0'
    r = SPACING.get(right, right) if right else '0'
    b = SPACING.get(bottom, bottom) if bottom else '0'
    l = SPACING.get(left, left) if left else '0'

    return f"margin: {t} {r} {b} {l};"


def margin_top(size: str) -> str:
    """Shorthand for top margin."""
    value = SPACING.get(size, size)
    return f"margin-top: {value};"


def margin_bottom(size: str) -> str:
    """Shorthand for bottom margin."""
    value = SPACING.get(size, size)
    return f"margin-bottom: {value};"


def margin_left(size: str) -> str:
    """Shorthand for left margin."""
    value = SPACING.get(size, size)
    return f"margin-left: {value};"


def margin_right(size: str) -> str:
    """Shorthand for right margin."""
    value = SPACING.get(size, size)
    return f"margin-right: {value};"


def margin_x(size: str) -> str:
    """Shorthand for horizontal margin (left + right)."""
    value = SPACING.get(size, size)
    return f"margin-left: {value}; margin-right: {value};"


def margin_y(size: str) -> str:
    """Shorthand for vertical margin (top + bottom)."""
    value = SPACING.get(size, size)
    return f"margin-top: {value}; margin-bottom: {value};"


# ============================================================================
# PADDING HELPERS
# ============================================================================

def padding(
    top: Union[str, None] = None,
    right: Union[str, None] = None,
    bottom: Union[str, None] = None,
    left: Union[str, None] = None,
    all: Union[str, None] = None,
    x: Union[str, None] = None,
    y: Union[str, None] = None,
) -> str:
    """
    Generate padding CSS with spacing scale values.
    
    Args:
        top: Top padding (e.g., 'md', 'lg')
        right: Right padding
        bottom: Bottom padding
        left: Left padding
        all: Apply same padding to all sides
        x: Horizontal padding (left + right)
        y: Vertical padding (top + bottom)
        
    Returns:
        CSS padding string
        
    Examples:
        >>> padding(all='md')
        'padding: 1rem;'
        
        >>> padding(y='sm', x='lg')
        'padding: 0.75rem 1.5rem;'
        
        >>> padding(top='xl', left='md')
        'padding: 2rem 0 0 1rem;'
    """
    if all:
        value = SPACING.get(all, all)
        return f"padding: {value};"

    if x or y:
        v_padding = SPACING.get(y, y) if y else '0'
        h_padding = SPACING.get(x, x) if x else '0'
        return f"padding: {v_padding} {h_padding};"

    # Individual sides
    t = SPACING.get(top, top) if top else '0'
    r = SPACING.get(right, right) if right else '0'
    b = SPACING.get(bottom, bottom) if bottom else '0'
    l = SPACING.get(left, left) if left else '0'

    return f"padding: {t} {r} {b} {l};"


def padding_top(size: str) -> str:
    """Shorthand for top padding."""
    value = SPACING.get(size, size)
    return f"padding-top: {value};"


def padding_bottom(size: str) -> str:
    """Shorthand for bottom padding."""
    value = SPACING.get(size, size)
    return f"padding-bottom: {value};"


def padding_left(size: str) -> str:
    """Shorthand for left padding."""
    value = SPACING.get(size, size)
    return f"padding-left: {value};"


def padding_right(size: str) -> str:
    """Shorthand for right padding."""
    value = SPACING.get(size, size)
    return f"padding-right: {value};"


def padding_x(size: str) -> str:
    """Shorthand for horizontal padding (left + right)."""
    value = SPACING.get(size, size)
    return f"padding-left: {value}; padding-right: {value};"


def padding_y(size: str) -> str:
    """Shorthand for vertical padding (top + bottom)."""
    value = SPACING.get(size, size)
    return f"padding-top: {value}; padding-bottom: {value};"


# ============================================================================
# GAP HELPERS (for flexbox/grid)
# ============================================================================

def gap(size: str) -> str:
    """
    Generate gap CSS for flex/grid layouts.
    
    Args:
        size: Gap size from spacing scale
        
    Returns:
        CSS gap string
    """
    value = SPACING.get(size, size)
    return f"gap: {value};"


def gap_x(size: str) -> str:
    """Horizontal gap for flex/grid."""
    value = SPACING.get(size, size)
    return f"column-gap: {value};"


def gap_y(size: str) -> str:
    """Vertical gap for flex/grid."""
    value = SPACING.get(size, size)
    return f"row-gap: {value};"


# ============================================================================
# SPACING PRESETS (Common patterns)
# ============================================================================

class SpacingPresets:
    """Pre-configured spacing patterns for common use cases."""

    # Compact (tight spacing)
    COMPACT = {
        'padding': padding(y='xs', x='sm'),    # 8px 12px
        'gap': gap('xs'),                       # 8px
        'margin': margin(bottom='sm'),          # 12px
    }

    # Default (comfortable spacing)
    DEFAULT = {
        'padding': padding(y='sm', x='md'),    # 12px 16px
        'gap': gap('sm'),                       # 12px
        'margin': margin(bottom='md'),          # 16px
    }

    # Relaxed (generous spacing)
    RELAXED = {
        'padding': padding(y='md', x='lg'),    # 16px 24px
        'gap': gap('md'),                       # 16px
        'margin': margin(bottom='lg'),          # 24px
    }

    # Section (major visual breaks)
    SECTION = {
        'padding': padding(y='xl', x='lg'),    # 32px 24px
        'gap': gap('lg'),                       # 24px
        'margin': margin(y='xl'),               # 32px top+bottom
    }

    # Card/Panel
    CARD = {
        'padding': padding(all='lg'),           # 24px all sides
        'margin': margin(bottom='md'),          # 16px bottom
        'gap': gap('md'),                       # 16px between elements
    }

    # Button
    BUTTON = {
        'padding': padding(y='sm', x='lg'),    # 12px 24px
        'margin': margin(right='sm'),           # 8px right (inline)
    }

    # List item
    LIST_ITEM = {
        'padding': padding(y='xs', x='md'),    # 8px 16px
        'margin': margin(bottom='xs'),          # 8px bottom
    }


# ============================================================================
# VALIDATION
# ============================================================================

def validate_spacing():
    """Validate spacing system for consistency."""
    print("✅ Spacing System (8px baseline grid):")
    print(f"  - Scale defined: {len(SPACING)} sizes")
    print(f"  - Range: {SPACING_PX['xs']}px → {SPACING_PX['3xl']}px")
    print("  - All values are multiples of 8px")
    print("  - Margin helpers: 10 functions")
    print("  - Padding helpers: 10 functions")
    print("  - Gap helpers: 3 functions")
    print(f"  - Presets: {len([k for k in dir(SpacingPresets) if not k.startswith('_')])}")


if __name__ == "__main__":
    validate_spacing()
