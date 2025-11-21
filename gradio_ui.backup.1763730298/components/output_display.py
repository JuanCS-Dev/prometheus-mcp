"""Output display component with streaming support."""
import gradio as gr


def create_output_display() -> gr.Textbox:
    """
    Create output display with syntax highlighting.
    
    Features:
    - Streaming support
    - Syntax highlighting
    - Copy button
    - Auto-scroll
    """
    
    output = gr.Textbox(
        label="📊 Output",
        lines=20,
        max_lines=30,
        interactive=False,
        show_copy_button=True,
        elem_classes=["output-container"],
        show_label=True
    )
    
    return output
