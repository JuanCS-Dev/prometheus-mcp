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
    
    # Minimal suggestions
    suggestions = gr.HTML(
        """
        <div style="margin-top: 20px;">
            <p style="
                color: #6E6E73;
                font-size: 13px;
                margin-bottom: 10px;
                font-weight: 600;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            ">Suggestions</p>
            <div style="display: flex; flex-wrap: wrap; gap: 8px;">
                <span class="chip-suggest" style="
                    display: inline-flex;
                    align-items: center;
                    background: #FAFAFA;
                    border: 0.5px solid #D2D2D7;
                    color: #1D1D1F;
                    padding: 7px 14px;
                    border-radius: 20px;
                    cursor: pointer;
                    transition: all 180ms ease;
                    font-size: 13px;
                    font-weight: 500;
                    letter-spacing: -0.01em;
                " onmouseover="this.style.background='#FFFFFF'; this.style.borderColor='#007AFF'; this.style.color='#007AFF'; this.style.boxShadow='0 2px 8px rgba(0,122,255,0.15)'; this.style.transform='translateY(-1px)'" onmouseout="this.style.background='#FAFAFA'; this.style.borderColor='#D2D2D7'; this.style.color='#1D1D1F'; this.style.boxShadow='none'; this.style.transform='translateY(0)'">Read README.md</span>
                <span class="chip-suggest" style="
                    display: inline-flex;
                    align-items: center;
                    background: #FAFAFA;
                    border: 0.5px solid #D2D2D7;
                    color: #1D1D1F;
                    padding: 7px 14px;
                    border-radius: 20px;
                    cursor: pointer;
                    transition: all 180ms ease;
                    font-size: 13px;
                    font-weight: 500;
                    letter-spacing: -0.01em;
                " onmouseover="this.style.background='#FFFFFF'; this.style.borderColor='#007AFF'; this.style.color='#007AFF'; this.style.boxShadow='0 2px 8px rgba(0,122,255,0.15)'; this.style.transform='translateY(-1px)'" onmouseout="this.style.background='#FAFAFA'; this.style.borderColor='#D2D2D7'; this.style.color='#1D1D1F'; this.style.boxShadow='none'; this.style.transform='translateY(0)'">Search imports</span>
                <span class="chip-suggest" style="
                    display: inline-flex;
                    align-items: center;
                    background: #FAFAFA;
                    border: 0.5px solid #D2D2D7;
                    color: #1D1D1F;
                    padding: 7px 14px;
                    border-radius: 20px;
                    cursor: pointer;
                    transition: all 180ms ease;
                    font-size: 13px;
                    font-weight: 500;
                    letter-spacing: -0.01em;
                " onmouseover="this.style.background='#FFFFFF'; this.style.borderColor='#007AFF'; this.style.color='#007AFF'; this.style.boxShadow='0 2px 8px rgba(0,122,255,0.15)'; this.style.transform='translateY(-1px)'" onmouseout="this.style.background='#FAFAFA'; this.style.borderColor='#D2D2D7'; this.style.color='#1D1D1F'; this.style.boxShadow='none'; this.style.transform='translateY(0)'">LSP diagnostics</span>
            </div>
        </div>
        """
    )
    
    return command_input, suggestions
