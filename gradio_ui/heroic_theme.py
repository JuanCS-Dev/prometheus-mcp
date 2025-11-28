"""
Heroic Glassmorphism Theme for Qwen Dev CLI (Gradio 6.0)
Simplified version - CSS does heavy lifting
"""

from __future__ import annotations

import gradio as gr


def create_heroic_theme() -> gr.Theme:
    """Simple Gradio 6 theme - glassmorphism via CSS"""

    # Use Soft theme as base (minimal customization)
    theme = gr.themes.Soft(
        primary_hue="neutral",
        secondary_hue="neutral",
        font=gr.themes.GoogleFont("Inter"),
        font_mono=gr.themes.GoogleFont("JetBrains Mono"),
    )

    return theme


def get_glassmorphism_css() -> str:
    """Glassmorphism CSS for Gradio 6"""
    return """
    /* Glassmorphism */
    .gr-box, .gr-panel {
        backdrop-filter: blur(12px) saturate(180%);
        -webkit-backdrop-filter: blur(12px) saturate(180%);
        background: rgba(255, 255, 255, 0.75) !important;
        border: 1px solid rgba(255, 255, 255, 0.18) !important;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.08);
    }
    
    /* Smooth transitions */
    * {
        transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
    }
    
    /* Dark mode */
    @media (prefers-color-scheme: dark) {
        .gr-box, .gr-panel {
            background: rgba(23, 23, 23, 0.75) !important;
            border: 1px solid rgba(64, 64, 64, 0.3) !important;
        }
    }
    
    /* Fallback for no backdrop-filter support */
    @supports not (backdrop-filter: blur(12px)) {
        .gr-box, .gr-panel {
            background: rgba(255, 255, 255, 0.95) !important;
        }
        @media (prefers-color-scheme: dark) {
            .gr-box, .gr-panel {
                background: rgba(23, 23, 23, 0.95) !important;
            }
        }
    }
    """
