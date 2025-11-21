"""
Refined Minimal Theme for QWEN-DEV-CLI
2025 design trends - sophisticated, clean, professional.
"""
import gradio as gr
from .refined_palette import LIGHT


def create_refined_theme() -> gr.themes.Base:
    """
    Create refined minimal theme (LIGHT MODE default).
    
    Design principles (2025):
    - Soft, warm neutrals
    - Subtle shadows
    - Generous whitespace
    - Minimal accent color
    - High contrast text
    """
    
    # Start with Soft theme (cleanest base)
    theme = gr.themes.Soft(
        primary_hue="blue",
        secondary_hue="slate",
        neutral_hue="slate",
        font=gr.themes.GoogleFont("Inter"),
        spacing_size="md",
        radius_size="md",
    ).set(
        # LIGHT MODE (DEFAULT)
        # Backgrounds
        body_background_fill=LIGHT["bg_primary"],
        body_background_fill_dark=LIGHT["bg_primary"],
        
        block_background_fill=LIGHT["bg_elevated"],
        block_background_fill_dark=LIGHT["bg_elevated"],
        
        # Borders (subtle)
        block_border_width="1px",
        block_border_color=LIGHT["border_light"],
        block_border_color_dark=LIGHT["border_light"],
        
        # Text
        body_text_color=LIGHT["text_primary"],
        body_text_color_dark=LIGHT["text_primary"],
        body_text_color_subdued=LIGHT["text_secondary"],
        body_text_color_subdued_dark=LIGHT["text_secondary"],
        
        # Inputs
        input_background_fill=LIGHT["bg_elevated"],
        input_background_fill_dark=LIGHT["bg_elevated"],
        input_border_color=LIGHT["border_medium"],
        input_border_color_dark=LIGHT["border_medium"],
        input_border_width="1px",
        
        # Buttons
        button_primary_background_fill=LIGHT["accent_primary"],
        button_primary_background_fill_hover=LIGHT["accent_hover"],
        button_primary_background_fill_dark=LIGHT["accent_primary"],
        button_primary_text_color="#FFFFFF",
        
        button_secondary_background_fill=LIGHT["bg_elevated"],
        button_secondary_border_color=LIGHT["border_medium"],
        button_secondary_text_color=LIGHT["text_primary"],
        
        # Shadows (subtle)
        shadow_drop="0 1px 2px 0 rgba(0, 0, 0, 0.05)",
        shadow_drop_lg="0 4px 6px -1px rgba(0, 0, 0, 0.1)",
    )
    
    return theme


# Alias for backwards compatibility
create_glass_theme = create_refined_theme
