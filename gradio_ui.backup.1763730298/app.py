#!/usr/bin/env python3
"""
QWEN-DEV-CLI - Modern Professional Web UI (2025)
Inspired by: Claude Code, Cursor IDE, Linear App
Zero fluff. Pure function.
"""
import gradio as gr
from pathlib import Path
from theme import create_modern_theme

# Load CSS
CSS_PATH = Path(__file__).parent / "styles" / "modern.css"
CUSTOM_CSS = CSS_PATH.read_text() if CSS_PATH.exists() else ""

def create_app():
    """Build clean, professional UI"""
    
    theme = create_modern_theme()
    
    with gr.Blocks(
        theme=theme,
        css=CUSTOM_CSS,
        title="QWEN-DEV-CLI"
    ) as app:
        
        with gr.Row(elem_classes="container"):
            # LEFT: Sidebar (20%)
            with gr.Column(scale=2, elem_classes="sidebar"):
                gr.HTML("""
                    <div style="margin-bottom: 32px;">
                        <div style="font-size: 20px; font-weight: 600; color: #1F2937; margin-bottom: 4px;">
                            QWEN-DEV-CLI
                        </div>
                        <div style="font-size: 13px; color: #6B7280;">
                            AI Development Partner
                        </div>
                    </div>
                """)
                
                # Project Files
                gr.HTML('<div class="section-label">PROJECT</div>')
                project_tree = gr.Dataframe(
                    headers=["Files"],
                    value=[
                        ["qwen_dev_cli/"],
                        ["  agent.py"],
                        ["  tools/"],
                        ["tests/"],
                        ["README.md"]
                    ],
                    elem_classes="card",
                    interactive=False,
                    show_label=False
                )
                
                # Upload
                file_upload = gr.File(
                    label="Add Files",
                    file_count="multiple",
                    elem_classes="card"
                )
                
                # History
                gr.HTML('<div class="section-label" style="margin-top: 24px;">HISTORY</div>')
                history = gr.Dataframe(
                    headers=["Time", "Action"],
                    value=[
                        ["10:23", "Read README"],
                        ["10:25", "Search TODO"],
                        ["10:27", "Fix imports"]
                    ],
                    elem_classes="card",
                    interactive=False,
                    show_label=False
                )
            
            # CENTER: Main Content (60%)
            with gr.Column(scale=6, elem_classes="main-content"):
                # Command Input
                gr.HTML('<div class="section-label">COMMAND</div>')
                command_input = gr.Textbox(
                    placeholder="What would you like to do?",
                    lines=3,
                    elem_classes="card",
                    show_label=False
                )
                
                with gr.Row():
                    submit_btn = gr.Button("Execute", variant="primary")
                    clear_btn = gr.Button("Clear", variant="secondary")
                
                # Response Output
                gr.HTML('<div class="section-label" style="margin-top: 24px;">OUTPUT</div>')
                output_display = gr.Markdown(
                    value="*Ready to assist...*",
                    elem_classes="card"
                )
            
            # RIGHT: Context Panel (20%)
            with gr.Column(scale=2, elem_classes="sidebar"):
                gr.HTML('<div class="section-label">CONTEXT</div>')
                
                # Active File
                gr.HTML("""
                    <div class="card">
                        <div style="font-size: 11px; color: #9CA3AF; margin-bottom: 6px;">ACTIVE FILE</div>
                        <div style="font-size: 13px; color: #1F2937; font-family: monospace;">
                            agent.py
                        </div>
                    </div>
                """)
                
                # Tools Available
                gr.HTML("""
                    <div class="card" style="margin-top: 16px;">
                        <div style="font-size: 11px; color: #9CA3AF; margin-bottom: 8px;">TOOLS</div>
                        <div style="font-size: 12px; color: #6B7280; line-height: 1.8;">
                            • File Operations<br>
                            • Code Search<br>
                            • LSP Integration<br>
                            • Git Commands<br>
                            • Refactoring
                        </div>
                    </div>
                """)
                
                # Stats
                gr.HTML("""
                    <div class="card" style="margin-top: 16px;">
                        <div style="font-size: 11px; color: #9CA3AF; margin-bottom: 8px;">STATS</div>
                        <div style="font-size: 12px; color: #6B7280;">
                            <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
                                <span>Files</span>
                                <span style="color: #1F2937; font-weight: 600;">27</span>
                            </div>
                            <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
                                <span>Lines</span>
                                <span style="color: #1F2937; font-weight: 600;">3.2k</span>
                            </div>
                            <div style="display: flex; justify-content: space-between;">
                                <span>Lang</span>
                                <span style="color: #1F2937; font-weight: 600;">Python</span>
                            </div>
                        </div>
                    </div>
                """)
        
        # Event handlers
        def execute_command(cmd):
            if not cmd.strip():
                return "⚠️ Please enter a command"
            return f"**Executing:** `{cmd}`\n\n✓ Command processed successfully"
        
        def clear_command():
            return ""
        
        submit_btn.click(
            fn=execute_command,
            inputs=command_input,
            outputs=output_display
        )
        
        clear_btn.click(
            fn=clear_command,
            outputs=command_input
        )
    
    return app

if __name__ == "__main__":
    app = create_app()
    app.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
        show_api=False
    )
