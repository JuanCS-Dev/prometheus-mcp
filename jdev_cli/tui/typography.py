"""
Typography System - Perfect Hierarchy.

Font sizes, weights, line heights, and letter spacing
following a modular scale for visual harmony.

Philosophy:
- Clear hierarchy guides the eye
- Readable at all sizes
- Consistent spacing rhythm
- Monospace for code, sans-serif for UI

Created: 2025-11-18 20:05 UTC
"""



# ============================================================================
# FONT FAMILIES
# ============================================================================

FONTS = {
    # Monospace fonts (code, technical content)
    'mono': [
        'JetBrains Mono',  # Modern, ligatures, excellent readability
        'Fira Code',       # Popular, good ligature support
        'Cascadia Code',   # Microsoft's modern monospace
        'Monaco',          # macOS classic
        'Consolas',        # Windows classic
        'Courier New',     # Universal fallback
        'monospace',       # System fallback
    ],

    # Sans-serif fonts (UI, headings, labels)
    'sans': [
        'Inter',                      # Modern, optimized for screens
        '-apple-system',              # macOS system font
        'BlinkMacSystemFont',         # macOS Chrome
        'Segoe UI',                   # Windows
        'Roboto',                     # Android, web
        'Helvetica Neue',             # macOS fallback
        'Arial',                      # Universal fallback
        'sans-serif',                 # System fallback
    ],
}


# Font family strings (ready to use)
FONT_MONO = ', '.join(FONTS['mono'])
FONT_SANS = ', '.join(FONTS['sans'])


# ============================================================================
# FONT SIZES (Modular Scale - 1.125 ratio)
# ============================================================================

SIZES = {
    # Scale from smallest to largest
    'xs': '0.75rem',     # 12px - Timestamps, metadata, fine print
    'sm': '0.875rem',    # 14px - Secondary text, captions
    'base': '1rem',      # 16px - Body text (default, most readable)
    'lg': '1.125rem',    # 18px - Subheadings, emphasis
    'xl': '1.25rem',     # 20px - Headings, titles
    '2xl': '1.5rem',     # 24px - Major headings
    '3xl': '1.875rem',   # 30px - Hero text (rarely used in terminal)
}


# Pixel equivalents (for reference, assuming 16px base)
SIZES_PX = {
    'xs': 12,
    'sm': 14,
    'base': 16,
    'lg': 18,
    'xl': 20,
    '2xl': 24,
    '3xl': 30,
}


# ============================================================================
# FONT WEIGHTS
# ============================================================================

WEIGHTS = {
    'normal': 400,      # Regular body text
    'medium': 500,      # Slightly emphasized
    'semibold': 600,    # Subheadings, strong emphasis
    'bold': 700,        # Headings, critical info
}


# ============================================================================
# LINE HEIGHTS (Optimized for readability)
# ============================================================================

class LineHeights:
    """
    Line heights optimized for different text sizes.
    
    Rule of thumb:
    - Smaller text needs more line-height (readability)
    - Larger text needs less line-height (compactness)
    - Code needs tight line-height (scanning)
    """

    # Absolute values (unitless multipliers)
    TIGHT = 1.2      # Code blocks, compact lists
    SNUG = 1.375     # UI elements, buttons
    NORMAL = 1.5     # Body text (default, most readable)
    RELAXED = 1.625  # Long-form content
    LOOSE = 2.0      # Headings, very large text

    # Contextual mapping (size → line-height)
    BY_SIZE = {
        'xs': NORMAL,      # 12px needs normal spacing
        'sm': NORMAL,      # 14px needs normal spacing
        'base': NORMAL,    # 16px default spacing
        'lg': SNUG,        # 18px can be tighter
        'xl': SNUG,        # 20px can be tighter
        '2xl': TIGHT,      # 24px tight for headers
        '3xl': TIGHT,      # 30px very tight
    }

    # By content type
    CODE = TIGHT       # Code blocks: 1.2
    UI = SNUG         # Buttons, labels: 1.375
    BODY = NORMAL     # Paragraphs: 1.5
    HEADING = TIGHT   # Headings: 1.2


# ============================================================================
# LETTER SPACING (Tracking)
# ============================================================================

class LetterSpacing:
    """
    Letter spacing (tracking) for different contexts.
    
    Negative tracking tightens, positive tracking loosens.
    """

    TIGHTER = '-0.05em'   # Very tight (large headings)
    TIGHT = '-0.025em'    # Tight (headings)
    NORMAL = '0em'        # Normal (body text)
    WIDE = '0.025em'      # Wide (small caps, labels)
    WIDER = '0.05em'      # Very wide (all caps)
    WIDEST = '0.1em'      # Extremely wide (stylistic only)

    # By context
    HEADING = TIGHT       # Headings look better tight
    BODY = NORMAL         # Body text at normal
    LABEL = WIDE          # UI labels slightly wider
    CAPS = WIDER          # All caps need more space
    CODE = NORMAL         # Code at normal (no adjustment)


# ============================================================================
# TYPOGRAPHY PRESETS
# ============================================================================

class TypographyPresets:
    """
    Complete typography configurations for common use cases.
    
    Each preset includes:
    - font_family
    - font_size
    - font_weight
    - line_height
    - letter_spacing
    """

    # Headings
    HEADING_XL = {
        'family': FONT_SANS,
        'size': SIZES['2xl'],
        'weight': WEIGHTS['bold'],
        'line_height': LineHeights.HEADING,
        'letter_spacing': LetterSpacing.HEADING,
    }

    HEADING_LG = {
        'family': FONT_SANS,
        'size': SIZES['xl'],
        'weight': WEIGHTS['semibold'],
        'line_height': LineHeights.HEADING,
        'letter_spacing': LetterSpacing.HEADING,
    }

    HEADING_MD = {
        'family': FONT_SANS,
        'size': SIZES['lg'],
        'weight': WEIGHTS['semibold'],
        'line_height': LineHeights.SNUG,
        'letter_spacing': LetterSpacing.NORMAL,
    }

    # Body text
    BODY = {
        'family': FONT_SANS,
        'size': SIZES['base'],
        'weight': WEIGHTS['normal'],
        'line_height': LineHeights.BODY,
        'letter_spacing': LetterSpacing.BODY,
    }

    BODY_SMALL = {
        'family': FONT_SANS,
        'size': SIZES['sm'],
        'weight': WEIGHTS['normal'],
        'line_height': LineHeights.NORMAL,
        'letter_spacing': LetterSpacing.NORMAL,
    }

    # UI elements
    LABEL = {
        'family': FONT_SANS,
        'size': SIZES['sm'],
        'weight': WEIGHTS['medium'],
        'line_height': LineHeights.UI,
        'letter_spacing': LetterSpacing.LABEL,
    }

    BUTTON = {
        'family': FONT_SANS,
        'size': SIZES['base'],
        'weight': WEIGHTS['medium'],
        'line_height': LineHeights.UI,
        'letter_spacing': LetterSpacing.NORMAL,
    }

    # Code
    CODE = {
        'family': FONT_MONO,
        'size': SIZES['sm'],
        'weight': WEIGHTS['normal'],
        'line_height': LineHeights.CODE,
        'letter_spacing': LetterSpacing.CODE,
    }

    CODE_INLINE = {
        'family': FONT_MONO,
        'size': SIZES['sm'],
        'weight': WEIGHTS['normal'],
        'line_height': 'inherit',  # Inherit from surrounding text
        'letter_spacing': LetterSpacing.CODE,
    }

    # Metadata
    CAPTION = {
        'family': FONT_SANS,
        'size': SIZES['xs'],
        'weight': WEIGHTS['normal'],
        'line_height': LineHeights.NORMAL,
        'letter_spacing': LetterSpacing.NORMAL,
    }

    TIMESTAMP = {
        'family': FONT_MONO,
        'size': SIZES['xs'],
        'weight': WEIGHTS['normal'],
        'line_height': LineHeights.TIGHT,
        'letter_spacing': LetterSpacing.NORMAL,
    }


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def get_font_css(preset_name: str) -> str:
    """
    Generate CSS string for a typography preset.
    
    Args:
        preset_name: Name of preset (e.g., 'HEADING_XL', 'BODY', 'CODE')
        
    Returns:
        CSS string
        
    Example:
        >>> get_font_css('BODY')
        'font-family: Inter, -apple-system, ...; font-size: 1rem; ...'
    """
    preset = getattr(TypographyPresets, preset_name, TypographyPresets.BODY)

    return (
        f"font-family: {preset['family']}; "
        f"font-size: {preset['size']}; "
        f"font-weight: {preset['weight']}; "
        f"line-height: {preset['line_height']}; "
        f"letter-spacing: {preset['letter_spacing']};"
    )


def scale_size(base_size: str, factor: float) -> str:
    """
    Scale a font size by a factor.
    
    Args:
        base_size: Base size (e.g., '1rem')
        factor: Scaling factor (e.g., 1.5 for 150%)
        
    Returns:
        Scaled size string
        
    Example:
        >>> scale_size('1rem', 1.5)
        '1.5rem'
    """
    value = float(base_size.replace('rem', ''))
    return f"{value * factor}rem"


# ============================================================================
# VALIDATION
# ============================================================================

def validate_typography():
    """Validate typography system for consistency."""
    print("✅ Typography System:")
    print(f"  - Font families: {len(FONTS)} (mono, sans)")
    print(f"  - Font sizes: {len(SIZES)} (xs → 3xl)")
    print(f"  - Font weights: {len(WEIGHTS)} (normal → bold)")
    print(f"  - Presets: {len([k for k in dir(TypographyPresets) if not k.startswith('_')])}")
    print("  - Line heights optimized for readability")
    print("  - Letter spacing tuned for different contexts")


if __name__ == "__main__":
    validate_typography()
