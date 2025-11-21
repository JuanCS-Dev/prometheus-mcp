#!/usr/bin/env python3
"""
QWEN-DEV-CLI Gradio UI - Emotional Design
Main application entry point.

Philosophy: Craft over Code. Art over Engineering.
"""
import gradio as gr
from pathlib import Path
from typing import Optional

# Import our custom theme
from themes.glass_theme import create_glass_theme
from components.hero import create_hero_section
from components.command_input import create_command_interface
from components.output_display import create_output_display
from components.status_bar import create_status_bar

# Import backend integration
from backend.cli_bridge import CLIBridge


class QwenGradioUI:
    """Main Gradio UI application with emotional design."""
    
    def __init__(self):
        """Initialize UI with CLI backend."""
        self.cli = CLIBridge()
        self.theme = create_glass_theme()
        
    def build(self) -> gr.Blocks:
        """Build the complete UI with glassmorphism."""
        
        # Load custom CSS
        css_file = Path(__file__).parent / "styles" / "main.css"
        custom_css = css_file.read_text() if css_file.exists() else ""
        
        with gr.Blocks(
            theme=self.theme,
            title="🚀 QWEN-DEV-CLI",
            css=custom_css,
            head=self._get_custom_head()
        ) as demo:
            
            # Hero Section (Emotional Entry)
            create_hero_section()
            
            # Main Layout
            with gr.Row():
                # Sidebar (Context & History)
                with gr.Column(scale=1, elem_classes=["sidebar"]):
                    gr.HTML("""
                        <div style="
                            display: flex;
                            align-items: center;
                            gap: 8px;
                            margin-bottom: 10px;
                            color: #6E6E73;
                            font-weight: 600;
                            font-size: 13px;
                            text-transform: uppercase;
                            letter-spacing: 0.5px;
                        ">
                            <span style="font-size: 16px;">📁</span>
                            <span>Project Files</span>
                        </div>
                    """)
                    file_browser = gr.File(
                        label="",
                        file_count="multiple",
                        show_label=False
                    )
                    
                    gr.HTML("""
                        <div style="
                            display: flex;
                            align-items: center;
                            gap: 8px;
                            margin-top: 28px;
                            margin-bottom: 10px;
                            color: #6E6E73;
                            font-weight: 600;
                            font-size: 13px;
                            text-transform: uppercase;
                            letter-spacing: 0.5px;
                        ">
                            <span style="font-size: 16px;">🕒</span>
                            <span>History</span>
                        </div>
                    """)
                    history = gr.Dataframe(
                        headers=["Time", "Command"],
                        interactive=False,
                        show_label=False
                    )
                
                # Main Content Area
                with gr.Column(scale=3, elem_classes=["main-content"]):
                    # Command Interface
                    command_input, suggestions = create_command_interface()
                    
                    # Output Display
                    output_display = create_output_display()
                    
            # Status Bar (Bottom)
            create_status_bar()
            
            # Event handlers
            self._setup_event_handlers(
                command_input=command_input,
                output_display=output_display,
                history=history
            )
            
        return demo
    
    def _get_custom_head(self) -> str:
        """Inject custom meta tags and fonts."""
        return """
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <link rel="preconnect" href="https://fonts.googleapis.com">
        <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
        """
    
    def _setup_event_handlers(
        self,
        command_input: gr.Textbox,
        output_display: gr.Textbox,
        history: gr.Dataframe
    ):
        """Wire up interactive behavior."""
        
        def process_command(command: str):
            """Process user command via CLI backend."""
            if not command.strip():
                return "", "❌ Empty command"
            
            # Execute via CLI bridge (streaming)
            output_chunks = []
            for chunk in self.cli.execute_command(command):
                output_chunks.append(chunk)
            
            result = "\n".join(output_chunks)
            return "", result
        
        # Submit on Enter or button click
        command_input.submit(
            fn=process_command,
            inputs=[command_input],
            outputs=[command_input, output_display],
        )
    

    def launch(self, **kwargs):
        """Launch the Gradio app."""
        demo = self.build()
        demo.launch(**kwargs)


def main():
    """Entry point for Gradio UI."""
    app = QwenGradioUI()
    app.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
        show_error=True
    )


if __name__ == "__main__":
    main()
