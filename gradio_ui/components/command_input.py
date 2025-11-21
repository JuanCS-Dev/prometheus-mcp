"""Command input component with suggestions."""
import gradio as gr
from typing import Tuple


def create_command_interface() -> Tuple[gr.Textbox, gr.HTML]:
    """
    Create command input with smart suggestions.
    
    Returns:
        Tuple of (input_box, suggestions_html)
    """
    
    # Command input
    command_input = gr.Textbox(
        label="💬 What would you like to do?",
        placeholder="read main.py, refactor legacy code, fix all TODOs...",
        lines=2,
        elem_classes=["command-input"],
        show_label=True
    )
    
    # Smart suggestions with inline styles
    suggestions = gr.HTML(
        """
        <div style="margin-top: 16px;">
            <p style="color: #94a3b8; font-size: 0.9rem; margin-bottom: 12px;">💡 Quick Suggestions:</p>
            <div style="display: flex; flex-wrap: wrap; gap: 8px;">
                <span class="suggestion-chip" style="
                    display: inline-block;
                    background: rgba(59, 130, 246, 0.15);
                    border: 1px solid rgba(59, 130, 246, 0.4);
                    color: #60a5fa;
                    padding: 8px 16px;
                    border-radius: 20px;
                    cursor: pointer;
                    transition: all 0.2s ease;
                    font-size: 0.9rem;
                ">📖 Read main.py</span>
                <span class="suggestion-chip" style="
                    display: inline-block;
                    background: rgba(59, 130, 246, 0.15);
                    border: 1px solid rgba(59, 130, 246, 0.4);
                    color: #60a5fa;
                    padding: 8px 16px;
                    border-radius: 20px;
                    cursor: pointer;
                    transition: all 0.2s ease;
                    font-size: 0.9rem;
                ">🔧 Refactor legacy code</span>
                <span class="suggestion-chip" style="
                    display: inline-block;
                    background: rgba(59, 130, 246, 0.15);
                    border: 1px solid rgba(59, 130, 246, 0.4);
                    color: #60a5fa;
                    padding: 8px 16px;
                    border-radius: 20px;
                    cursor: pointer;
                    transition: all 0.2s ease;
                    font-size: 0.9rem;
                ">✅ Fix all TODOs</span>
                <span class="suggestion-chip" style="
                    display: inline-block;
                    background: rgba(59, 130, 246, 0.15);
                    border: 1px solid rgba(59, 130, 246, 0.4);
                    color: #60a5fa;
                    padding: 8px 16px;
                    border-radius: 20px;
                    cursor: pointer;
                    transition: all 0.2s ease;
                    font-size: 0.9rem;
                ">🔍 Search for imports</span>
            </div>
        </div>
        """
    )
    
    return command_input, suggestions
