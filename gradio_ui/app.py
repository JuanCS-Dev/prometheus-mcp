"""Minimal Gradio UI for QWEN-DEV-CLI."""

import asyncio
import gradio as gr
from typing import List, Dict, Tuple
from .cli_adapter import CLIAdapter


# Global adapter instance
adapter = CLIAdapter()


async def chat_handler(
    message: str,
    history: List[Dict[str, str]]
) -> Tuple[List[Dict[str, str]], str]:
    """
    Handle chat messages with streaming.
    
    Args:
        message: User input
        history: Chat history [{"role": "user/assistant", "content": "..."}, ...]
    
    Returns:
        (updated_history, empty_string)
    """
    if not message.strip():
        return history, ""
    
    # Add user message to history
    history = history + [{"role": "user", "content": message}]
    
    # Stream response
    assistant_response = ""
    async for event in adapter.execute_streaming(message):
        if event["type"] == "thinking":
            assistant_response = f"🤔 {event['content']}"
        elif event["type"] == "result":
            assistant_response = event['content']
        elif event["type"] == "error":
            assistant_response = f"❌ {event['content']}"
    
    # Add assistant response
    history = history + [{"role": "assistant", "content": assistant_response}]
    
    return history, ""


def get_status() -> str:
    """Get current session status."""
    state = adapter.get_session_state()
    
    status_parts = [
        f"📁 {state['cwd']}",
        f"🎫 Tokens: {state['tokens_used']:,}",
        f"🔧 Commands: {state['commands_executed']}"
    ]
    
    return " | ".join(status_parts)


def create_ui() -> gr.Blocks:
    """Create Gradio interface."""
    
    with gr.Blocks(
        title="QWEN-DEV-CLI",
        theme=gr.themes.Soft(
            primary_hue="slate",
            secondary_hue="gray",
            neutral_hue="slate",
        )
    ) as demo:
        # Header
        gr.Markdown("# 🤖 QWEN-DEV-CLI")
        gr.Markdown("*AI-powered development assistant*")
        
        # Main chat interface
        chatbot = gr.Chatbot(
            label="Conversation",
            height=500,
            show_copy_button=True,
            type="messages"
        )
        
        # Input area
        with gr.Row():
            msg = gr.Textbox(
                placeholder="What would you like to do?",
                show_label=False,
                scale=9
            )
            submit = gr.Button("Send", scale=1, variant="primary")
        
        # Status bar
        status = gr.Textbox(
            label="Status",
            value=get_status(),
            interactive=False
        )
        
        # Examples
        gr.Examples(
            examples=[
                "List files in current directory",
                "Create a Python script that prints hello world",
                "Show git status",
                "Find all TODO comments in .py files"
            ],
            inputs=msg
        )
        
        # Event handlers
        def submit_handler(message, history):
            """Sync wrapper for async chat handler."""
            return asyncio.run(chat_handler(message, history))
        
        submit.click(
            fn=submit_handler,
            inputs=[msg, chatbot],
            outputs=[chatbot, msg]
        ).then(
            fn=get_status,
            inputs=None,
            outputs=status
        )
        
        msg.submit(
            fn=submit_handler,
            inputs=[msg, chatbot],
            outputs=[chatbot, msg]
        ).then(
            fn=get_status,
            inputs=None,
            outputs=status
        )
    
    return demo


def launch():
    """Launch the Gradio app."""
    demo = create_ui()
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False
    )


if __name__ == "__main__":
    launch()
