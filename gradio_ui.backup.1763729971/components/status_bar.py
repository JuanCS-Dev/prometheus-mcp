"""Status bar component - Ambient awareness."""
import gradio as gr


def create_status_bar():
    """
    Create status bar with real-time info.
    
    Displays:
    - Connection status
    - Token usage
    - Cost estimation
    """
    
    with gr.Row(elem_classes=["status-bar"]):
        gr.HTML(
            """
            <div style="display: flex; gap: 24px; align-items: center;">
                <div class="status-item">
                    <div class="status-indicator connected"></div>
                    <span>Connected</span>
                </div>
                <div class="status-item">
                    <span>⚡ Tokens: 0</span>
                </div>
                <div class="status-item">
                    <span>💰 Cost: $0.00</span>
                </div>
            </div>
            """,
            elem_classes=["status-content"]
        )
