"""
Glassmorphism Theme for QWEN-DEV-CLI
Emotional design with depth and transparency.
"""
import gradio as gr


def create_glass_theme() -> gr.themes.Base:
    """
    Create custom glassmorphism theme.
    
    Design principles:
    - Dark background (OLED-optimized)
    - Frosted glass cards
    - Subtle gradients
    - Soft shadows
    - Smooth transitions
    """
    
    # Use Default theme with dark mode
    theme = gr.themes.Default(
        primary_hue="blue",
        secondary_hue="cyan",
        neutral_hue="slate",
        font=gr.themes.GoogleFont("Inter"),
    ).set(
        # Force dark background
        body_background_fill="rgb(15, 23, 42)",
        body_background_fill_dark="rgb(15, 23, 42)",
        
        # Block styling
        block_background_fill="rgba(255, 255, 255, 0.05)",
        block_border_width="1px",
        block_border_color="rgba(255, 255, 255, 0.1)",
        
        # Input styling
        input_background_fill="rgba(255, 255, 255, 0.08)",
        input_border_color="rgba(255, 255, 255, 0.1)",
        
        # Button styling
        button_primary_background_fill="#3b82f6",
        button_primary_background_fill_hover="#2563eb",
        
        # Text colors
        body_text_color="#f1f5f9",
        body_text_color_subdued="#94a3b8",
    )
    
    return theme
