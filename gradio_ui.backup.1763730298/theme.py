"""
Modern Professional Theme (2025)
Based on Claude Code + Cursor IDE aesthetics
"""
import gradio as gr

def create_modern_theme():
    """Professional neutral theme with subtle interactions"""
    return gr.themes.Glass(
        primary_hue="slate",
        secondary_hue="slate",
        neutral_hue="slate",
        font=[
            "Inter",
            "SF Pro Display",
            "-apple-system",
            "BlinkMacSystemFont",
            "system-ui",
            "sans-serif"
        ],
        font_mono=[
            "SF Mono",
            "Monaco",
            "Consolas",
            "monospace"
        ]
    )
