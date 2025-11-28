"""
Surgical TUI (Terminal User Interface) System.

A minimalist yet impactful terminal UI framework inspired by:
- Gemini CLI (visual hierarchy)
- Cursor (UX excellence)
- Claude Code (stability)
- GitHub Copilot CLI (minimalism)

Philosophy: "Surgical Simplicity with Purposeful Polish"

Architecture:
├── theme.py - Color palette (GitHub Dark inspired)
├── typography.py - Font system (sizes, weights, spacing)
├── spacing.py - 8px baseline grid
├── styles.py - Rich Style presets
├── animations.py - Micro-interactions
└── components/ - Reusable UI components
    ├── message.py - Message boxes with typing effect
    ├── status.py - Status badges and spinners
    ├── progress.py - Animated progress bars
    ├── code.py - Enhanced code blocks
    ├── diff.py - Diff viewer (GitHub style)
    ├── tree.py - File tree (collapsible)
    ├── palette.py - Command palette (Cmd+K)
    ├── toast.py - Notification toasts
    └── context_pills.py - Context file pills

Created: 2025-11-18 20:05 UTC
Constitutional Compliance: 100%
LEI Target: < 1.0 (zero placeholders)
"""

__version__ = "1.0.0"
__author__ = "Maestro AI + Arquiteto-Chefe Juan"
__status__ = "Phase 1 - Foundation"

from .theme import COLORS, ColorHelpers, ThemeVariant
from .typography import FONTS, SIZES, WEIGHTS, LineHeights
from .spacing import SPACING, margin, padding
from .styles import create_style, PRESET_STYLES, get_syntax_theme

__all__ = [
    # Theme
    "COLORS",
    "ColorHelpers",
    "ThemeVariant",

    # Typography
    "FONTS",
    "SIZES",
    "WEIGHTS",
    "LineHeights",

    # Spacing
    "SPACING",
    "margin",
    "padding",

    # Styles
    "create_style",
    "PRESET_STYLES",
    "get_syntax_theme",
]
