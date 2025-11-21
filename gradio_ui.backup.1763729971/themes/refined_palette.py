"""
Refined Color Palette - 2025 Design Trends
Sophisticated, minimal, professional.

Philosophy: Less is more. Nuanced sophistication.
"""

# =======================
# LIGHT MODE (DEFAULT)
# =======================
LIGHT = {
    # Background (Soft whites with warmth)
    "bg_primary": "#FAFBFC",      # Almost white, gentle
    "bg_secondary": "#F5F7FA",    # Soft gray background
    "bg_elevated": "#FFFFFF",     # Pure white for cards
    
    # Text (High contrast, readable)
    "text_primary": "#1A202C",    # Almost black, warm
    "text_secondary": "#4A5568",  # Medium gray
    "text_tertiary": "#A0AEC0",   # Light gray
    
    # Accent (Trust blue - minimal use)
    "accent_primary": "#3B82F6",  # Blue 500
    "accent_hover": "#2563EB",    # Blue 600
    "accent_subtle": "#EFF6FF",   # Blue 50
    
    # Borders (Subtle, almost invisible)
    "border_light": "#E2E8F0",    # Very light gray
    "border_medium": "#CBD5E0",   # Light gray
    
    # Status colors
    "success": "#10B981",         # Green 500
    "warning": "#F59E0B",         # Amber 500
    "error": "#EF4444",           # Red 500
    
    # Shadows (Soft, natural)
    "shadow_sm": "0 1px 2px 0 rgba(0, 0, 0, 0.05)",
    "shadow_md": "0 4px 6px -1px rgba(0, 0, 0, 0.1)",
    "shadow_lg": "0 10px 15px -3px rgba(0, 0, 0, 0.1)",
}

# =======================
# DARK MODE (OPTIONAL)
# =======================
DARK = {
    # Background (Deep, rich blacks)
    "bg_primary": "#0F172A",      # Slate 900
    "bg_secondary": "#1E293B",    # Slate 800
    "bg_elevated": "#334155",     # Slate 700
    
    # Text (Soft whites, easy on eyes)
    "text_primary": "#F1F5F9",    # Slate 100
    "text_secondary": "#94A3B8",  # Slate 400
    "text_tertiary": "#64748B",   # Slate 500
    
    # Accent (Brighter blue for dark bg)
    "accent_primary": "#60A5FA",  # Blue 400
    "accent_hover": "#3B82F6",    # Blue 500
    "accent_subtle": "#1E3A8A",   # Blue 900
    
    # Borders (Subtle light lines)
    "border_light": "#334155",    # Slate 700
    "border_medium": "#475569",   # Slate 600
    
    # Status colors (adjusted for dark)
    "success": "#34D399",         # Green 400
    "warning": "#FBBF24",         # Amber 400
    "error": "#F87171",           # Red 400
    
    # Shadows (Deeper, softer)
    "shadow_sm": "0 1px 2px 0 rgba(0, 0, 0, 0.3)",
    "shadow_md": "0 4px 6px -1px rgba(0, 0, 0, 0.4)",
    "shadow_lg": "0 10px 15px -3px rgba(0, 0, 0, 0.5)",
}

# =======================
# TYPOGRAPHY SCALE
# =======================
TYPOGRAPHY = {
    "font_family": "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
    "font_family_mono": "'JetBrains Mono', 'Fira Code', monospace",
    
    # Sizes (rem scale)
    "text_xs": "0.75rem",    # 12px
    "text_sm": "0.875rem",   # 14px
    "text_base": "1rem",     # 16px
    "text_lg": "1.125rem",   # 18px
    "text_xl": "1.25rem",    # 20px
    "text_2xl": "1.5rem",    # 24px
    "text_3xl": "1.875rem",  # 30px
    "text_4xl": "2.25rem",   # 36px
    
    # Weights
    "font_normal": "400",
    "font_medium": "500",
    "font_semibold": "600",
    "font_bold": "700",
}

# =======================
# SPACING SCALE (8px base)
# =======================
SPACING = {
    "space_1": "0.25rem",   # 4px
    "space_2": "0.5rem",    # 8px
    "space_3": "0.75rem",   # 12px
    "space_4": "1rem",      # 16px
    "space_5": "1.25rem",   # 20px
    "space_6": "1.5rem",    # 24px
    "space_8": "2rem",      # 32px
    "space_10": "2.5rem",   # 40px
    "space_12": "3rem",     # 48px
    "space_16": "4rem",     # 64px
}

# =======================
# BORDER RADIUS
# =======================
RADIUS = {
    "radius_sm": "0.375rem",   # 6px
    "radius_md": "0.5rem",     # 8px
    "radius_lg": "0.75rem",    # 12px
    "radius_xl": "1rem",       # 16px
    "radius_2xl": "1.5rem",    # 24px
    "radius_full": "9999px",   # Pill shape
}

# =======================
# ANIMATION TIMING
# =======================
TRANSITIONS = {
    "ease_smooth": "cubic-bezier(0.4, 0.0, 0.2, 1)",
    "ease_in": "cubic-bezier(0.4, 0.0, 1, 1)",
    "ease_out": "cubic-bezier(0.0, 0.0, 0.2, 1)",
    "ease_in_out": "cubic-bezier(0.4, 0.0, 0.2, 1)",
    
    "duration_fast": "150ms",
    "duration_normal": "200ms",
    "duration_slow": "300ms",
}
