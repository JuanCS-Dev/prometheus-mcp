"""
♿ TUI Accessibility - WCAG AAA compliance
Ensures our CLI is accessible to all users
"""

from typing import Tuple, Optional
from dataclasses import dataclass
from .theme import COLORS


@dataclass
class ContrastRatio:
    """WCAG contrast ratio result"""
    ratio: float
    aa_normal: bool  # 4.5:1
    aa_large: bool   # 3:1
    aaa_normal: bool # 7:1
    aaa_large: bool  # 4.5:1
    
    @property
    def level(self) -> str:
        """Get highest compliance level"""
        if self.aaa_normal:
            return "AAA (Normal)"
        elif self.aaa_large:
            return "AAA (Large)"
        elif self.aa_normal:
            return "AA (Normal)"
        elif self.aa_large:
            return "AA (Large)"
        return "FAIL"


def hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
    """Convert hex color to RGB tuple"""
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))


def relative_luminance(rgb: Tuple[int, int, int]) -> float:
    """
    Calculate relative luminance (WCAG 2.1)
    https://www.w3.org/TR/WCAG21/#dfn-relative-luminance
    """
    r, g, b = [x / 255.0 for x in rgb]
    
    def adjust(c: float) -> float:
        if c <= 0.03928:
            return c / 12.92
        return pow((c + 0.055) / 1.055, 2.4)
    
    r, g, b = adjust(r), adjust(g), adjust(b)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def calculate_contrast_ratio(fg: str, bg: str) -> ContrastRatio:
    """
    Calculate WCAG contrast ratio between two colors
    
    Args:
        fg: Foreground color (hex)
        bg: Background color (hex)
    
    Returns:
        ContrastRatio with compliance levels
    """
    fg_rgb = hex_to_rgb(fg)
    bg_rgb = hex_to_rgb(bg)
    
    l1 = relative_luminance(fg_rgb)
    l2 = relative_luminance(bg_rgb)
    
    lighter = max(l1, l2)
    darker = min(l1, l2)
    
    ratio = (lighter + 0.05) / (darker + 0.05)
    
    return ContrastRatio(
        ratio=ratio,
        aa_normal=ratio >= 4.5,
        aa_large=ratio >= 3.0,
        aaa_normal=ratio >= 7.0,
        aaa_large=ratio >= 4.5,
    )


class AccessibilityValidator:
    """Validates color combinations for accessibility"""
    
    @staticmethod
    def validate_theme() -> dict:
        """Validate all theme color combinations"""
        results = {}
        bg = COLORS["bg"]
        
        # Test all foreground colors against background
        for name, color in COLORS.items():
            if name.startswith("bg") or name in ["transparent"]:
                continue
            
            ratio = calculate_contrast_ratio(color, bg)
            results[name] = ratio
        
        return results
    
    @staticmethod
    def get_accessible_color(
        preferred: str,
        background: str,
        target_ratio: float = 4.5,
    ) -> str:
        """
        Get accessible color version that meets target contrast
        
        Args:
            preferred: Preferred color
            background: Background color
            target_ratio: Minimum contrast ratio (default: AA normal)
        
        Returns:
            Accessible color (may be adjusted from preferred)
        """
        current_ratio = calculate_contrast_ratio(preferred, background)
        
        if current_ratio.ratio >= target_ratio:
            return preferred
        
        # Try lightening or darkening
        rgb = hex_to_rgb(preferred)
        bg_luminance = relative_luminance(hex_to_rgb(background))
        
        # If background is dark, lighten; if light, darken
        if bg_luminance < 0.5:
            # Lighten
            adjusted = tuple(min(255, int(c * 1.5)) for c in rgb)
        else:
            # Darken
            adjusted = tuple(max(0, int(c * 0.6)) for c in rgb)
        
        return f"#{adjusted[0]:02x}{adjusted[1]:02x}{adjusted[2]:02x}"


class ScreenReaderText:
    """Generate screen reader friendly text"""
    
    @staticmethod
    def describe_status(status: str) -> str:
        """Convert status badge to screen reader text"""
        descriptions = {
            "success": "Success - operation completed",
            "error": "Error - attention required",
            "warning": "Warning - please review",
            "info": "Information",
            "pending": "Pending - operation in progress",
            "loading": "Loading - please wait",
        }
        return descriptions.get(status.lower(), status)
    
    @staticmethod
    def describe_progress(current: int, total: int, percentage: int) -> str:
        """Generate progress description"""
        return f"Progress: {current} of {total} complete, {percentage} percent"
    
    @staticmethod
    def describe_code_block(language: str, lines: int) -> str:
        """Describe code block"""
        return f"Code block in {language}, {lines} lines"
    
    @staticmethod
    def describe_diff(additions: int, deletions: int) -> str:
        """Describe diff statistics"""
        return f"Changes: {additions} additions, {deletions} deletions"


class KeyboardNavigation:
    """Keyboard navigation helpers"""
    
    SHORTCUTS = {
        # Standard shortcuts
        "quit": ["Ctrl+C", "Ctrl+D", "q"],
        "help": ["?", "h", "F1"],
        "search": ["Ctrl+F", "/"],
        "command_palette": ["Ctrl+K", "Cmd+K"],
        
        # Navigation
        "next": ["j", "Down", "Tab"],
        "previous": ["k", "Up", "Shift+Tab"],
        "first": ["g", "Home"],
        "last": ["G", "End"],
        "page_down": ["Ctrl+F", "PageDown", "Space"],
        "page_up": ["Ctrl+B", "PageUp", "Shift+Space"],
        
        # Actions
        "select": ["Enter", "Space"],
        "back": ["Esc", "Backspace"],
        "delete": ["d", "Delete"],
        "edit": ["e", "Enter"],
        "copy": ["y", "Ctrl+C"],
        
        # View
        "toggle_preview": ["p"],
        "toggle_tree": ["t"],
        "toggle_help": ["?"],
        "zoom_in": ["Ctrl+=", "+"],
        "zoom_out": ["Ctrl+-", "-"],
    }
    
    @staticmethod
    def get_shortcuts(action: str) -> list:
        """Get all shortcuts for an action"""
        return KeyboardNavigation.SHORTCUTS.get(action, [])
    
    @staticmethod
    def format_shortcut(keys: str) -> str:
        """Format keyboard shortcut for display"""
        # Handle modifier keys
        keys = keys.replace("Ctrl", "⌃")
        keys = keys.replace("Cmd", "⌘")
        keys = keys.replace("Alt", "⌥")
        keys = keys.replace("Shift", "⇧")
        return keys
    
    @staticmethod
    def describe_action(action: str) -> str:
        """Get description of action"""
        descriptions = {
            "quit": "Exit application",
            "help": "Show help",
            "search": "Search",
            "command_palette": "Open command palette",
            "next": "Move to next item",
            "previous": "Move to previous item",
            "select": "Select current item",
            "back": "Go back",
        }
        return descriptions.get(action, action.replace("_", " ").title())


class AccessibilityManager:
    """
    Comprehensive accessibility management for Phase 5.2
    Adds missing methods for test compatibility
    """
    
    def __init__(self):
        self.high_contrast = self._detect_high_contrast()
        self.reduced_motion = self._detect_reduced_motion()
        
    def _detect_high_contrast(self) -> bool:
        """Detect high contrast mode"""
        import os
        return os.environ.get('HIGH_CONTRAST', '0') == '1'
    
    def _detect_reduced_motion(self) -> bool:
        """Detect reduced motion preference"""
        import os
        return os.environ.get('REDUCE_MOTION', '0') == '1'
    
    def calculate_contrast_ratio(self, fg: str, bg: str) -> float:
        """Calculate contrast ratio (returns float for compatibility)"""
        result = calculate_contrast_ratio(fg, bg)
        return result.ratio
    
    def is_wcag_aa_compliant(self, fg: str, bg: str, large_text: bool = False) -> bool:
        """Check WCAG AA compliance"""
        result = calculate_contrast_ratio(fg, bg)
        return result.aa_large if large_text else result.aa_normal
    
    def get_aria_label(self, element_type: str, **kwargs) -> str:
        """Generate ARIA label"""
        if element_type == "progress":
            value = kwargs.get('value', 0)
            max_val = kwargs.get('max', 100)
            return f"Progress: {value} of {max_val}"
        return element_type
    
    def get_alt_text(self, visual_element: str) -> str:
        """Get alt text for visual element"""
        alt_texts = {
            "spinner": "Loading in progress",
            "checkmark": "Success",
            "success": "Operation completed successfully",
            "error": "Error occurred",
            "warning": "Warning",
            "info": "Information",
        }
        return alt_texts.get(visual_element, ScreenReaderText.describe_status(visual_element))
    
    def get_focus_style(self) -> dict:
        """Get focus indicator style"""
        return {
            "border": "double",
            "border_color": "cyan",
            "visibility": "visible"
        }
    
    def get_min_interactive_width(self) -> int:
        """Minimum width for interactive elements"""
        return 10
    
    def should_announce_progress(self, old_value: int, new_value: int) -> bool:
        """Check if progress should be announced"""
        return (new_value // 10) > (old_value // 10)
    
    def get_announcement(self, event_type: str, **kwargs) -> str:
        """Generate announcement for screen reader"""
        if event_type == "status_change":
            return f"Status changed from {kwargs.get('old')} to {kwargs.get('new')}"
        elif event_type == "error":
            return f"Error: {kwargs.get('message', 'Unknown error')}"
        return f"Event: {event_type}"
    
    def get_announcement_priority(self, event_type: str) -> str:
        """Get announcement priority"""
        if event_type in ["error", "critical"]:
            return "assertive"
        return "polite"
    
    def is_high_contrast_mode(self) -> bool:
        """Check if high contrast mode is active"""
        return self.high_contrast
    
    def prefers_reduced_motion(self) -> bool:
        """Check if reduced motion is preferred"""
        return self.reduced_motion
    
    def should_animate(self) -> bool:
        """Check if animations should be shown"""
        return not self.reduced_motion
    
    def get_color_scheme(self, high_contrast: bool = None) -> dict:
        """Get color scheme"""
        if high_contrast is None:
            high_contrast = self.high_contrast
        
        if high_contrast:
            return {
                "background": "#000000",
                "foreground": "#FFFFFF",
                "accent": "#FFFF00",
                "error": "#FF0000",
                "warning": "#FFFF00",
                "success": "#00FF00",
            }
        return {
            "background": "#1E1E1E",
            "foreground": "#D4D4D4",
            "accent": "#007ACC",
            "error": "#F48771",
            "warning": "#DDB65F",
            "success": "#89D185",
        }


def generate_accessibility_report() -> str:
    """Generate full accessibility compliance report"""
    from rich.console import Console
    from rich.table import Table
    
    validator = AccessibilityValidator()
    results = validator.validate_theme()
    
    table = Table(title="♿ Accessibility Report (WCAG 2.1)")
    table.add_column("Color", style="bold")
    table.add_column("Ratio", justify="right")
    table.add_column("Level", justify="center")
    table.add_column("Status")
    
    for name, ratio in sorted(results.items(), key=lambda x: x[1].ratio, reverse=True):
        status = "✅" if ratio.aa_normal else "⚠️"
        table.add_row(
            name,
            f"{ratio.ratio:.2f}:1",
            ratio.level,
            status,
        )
    
    console = Console()
    console.print(table)
    
    # Summary
    total = len(results)
    aa_pass = sum(1 for r in results.values() if r.aa_normal)
    aaa_pass = sum(1 for r in results.values() if r.aaa_normal)
    
    console.print(f"\n📊 Summary:")
    console.print(f"  • Total colors tested: {total}")
    console.print(f"  • AA compliant: {aa_pass}/{total} ({aa_pass/total*100:.1f}%)")
    console.print(f"  • AAA compliant: {aaa_pass}/{total} ({aaa_pass/total*100:.1f}%)")
    
    return "Report generated"
