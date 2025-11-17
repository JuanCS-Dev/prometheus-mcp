"""Gradio web UI for qwen-dev-cli."""

import asyncio
from typing import List, Tuple, Generator
import gradio as gr

from .core.llm import llm_client
from .core.context import context_builder
from .core.mcp import mcp_manager
from .core.config import config


def create_ui() -> gr.Blocks:
    """Create Gradio Blocks UI with mobile-responsive design.
    
    Returns:
        Gradio Blocks interface
    """
    
    # Mobile-first CSS with responsive breakpoints
    mobile_css = """
    /* Mobile-first responsive design */
    .chat-container {
        min-height: 400px;
    }
    
    .upload-area {
        border: 2px dashed #ccc;
        padding: 15px;
        border-radius: 8px;
        text-align: center;
    }
    
    /* Touch-friendly buttons (min 44px) */
    .gr-button {
        min-height: 44px !important;
        font-size: 16px !important;
    }
    
    /* Readable text on mobile (min 16px) */
    .gr-textbox textarea, .gr-textbox input {
        font-size: 16px !important;
    }
    
    /* Mobile optimizations */
    @media (max-width: 768px) {
        .chat-container {
            min-height: 300px;
        }
        
        .gr-padded {
            padding: 10px !important;
        }
        
        /* Stack columns on mobile */
        .gr-row {
            flex-direction: column !important;
        }
        
        .gr-column {
            width: 100% !important;
        }
    }
    
    /* Dark mode support */
    @media (prefers-color-scheme: dark) {
        .upload-area {
            border-color: #555;
        }
    }
    """
    
    with gr.Blocks(
        title="QWEN-DEV-CLI - AI Code Assistant",
        theme=gr.themes.Soft(
            spacing_size="sm",
            radius_size="md",
        ),
        css=mobile_css
    ) as demo:
        
        # Responsive Header
        gr.Markdown("""
        # 🚀 QWEN-DEV-CLI
        **AI-Powered Code Assistant with MCP Integration**
        
        > Ask questions about your code, generate new functions, or get explanations with context awareness.
        """)
        
        # Main Layout (responsive: stacks on mobile)
        with gr.Row():
            # Left Column: Chat Interface (60% desktop, 100% mobile)
            with gr.Column(scale=3, min_width=320):
                chatbot = gr.Chatbot(
                    label="💬 Chat",
                    height=500,
                    show_label=True,
                    container=True,
                    elem_classes=["chat-container"],
                    type="messages",
                    bubble_full_width=False,
                    show_copy_button=True,
                )
                
                with gr.Row():
                    msg_input = gr.Textbox(
                        placeholder="Ask about code, request generation...",
                        label="Your Message",
                        lines=2,
                        max_lines=4,
                        scale=4,
                        autofocus=True,
                        show_label=False
                    )
                    send_btn = gr.Button(
                        "🚀",
                        variant="primary",
                        scale=1,
                        min_width=44,
                        size="lg"
                    )
                
                with gr.Row():
                    clear_btn = gr.Button("🗑️ Clear", size="sm", scale=1)
                    retry_btn = gr.Button("♻️ Retry", size="sm", scale=1)
                    examples_btn = gr.Button("💡 Examples", size="sm", scale=1)
            
            # Right Column: Controls & Context (40% desktop, 100% mobile)
            with gr.Column(scale=2, min_width=280):
                # Collapsible Settings (better for mobile)
                with gr.Accordion("⚙️ Model Settings", open=False):
                    temperature = gr.Slider(
                        minimum=0.0,
                        maximum=2.0,
                        value=config.temperature,
                        step=0.1,
                        label="Temperature",
                        info="Creativity level"
                    )
                    
                    max_tokens = gr.Slider(
                        minimum=128,
                        maximum=4096,
                        value=config.max_tokens,
                        step=128,
                        label="Max Tokens",
                        info="Response length"
                    )
                    
                    stream_enabled = gr.Checkbox(
                        label="⚡ Enable Streaming",
                        value=True,
                        info="Progressive response"
                    )
                
                # File Upload (touch-friendly)
                with gr.Accordion("📁 Context Files", open=True):
                    file_upload = gr.File(
                        label="Upload Files",
                        file_count="multiple",
                        file_types=[".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".cpp", ".c", ".go", ".rs", ".md", ".txt", ".json", ".yaml", ".yml"],
                        elem_classes=["upload-area"],
                        height=120
                    )
                    
                    context_status = gr.Textbox(
                        label="Status",
                        value="No files loaded",
                        interactive=False,
                        lines=2,
                        max_lines=4,
                        show_label=False
                    )
                    
                    clear_context_btn = gr.Button("🧹 Clear Context", size="sm", variant="secondary")
                
                # MCP Toggle (simplified for mobile)
                with gr.Accordion("🔧 MCP", open=False):
                    mcp_enabled = gr.Checkbox(
                        label="Enable MCP Filesystem",
                        value=mcp_manager.enabled,
                        info="Access local files"
                    )
                    
                    mcp_status = gr.Textbox(
                        label="MCP Status",
                        value="Ready" if mcp_manager.enabled else "Disabled",
                        interactive=False,
                        show_label=False
                    )
                
                # Stats (collapsible on mobile)
                with gr.Accordion("📊 Stats", open=False):
                    stats_display = gr.JSON(
                        label="Context Statistics",
                        value={"files": 0, "chars": 0, "tokens": 0}
                    )
        
        # State management
        chat_history = gr.State([])
        last_user_msg = gr.State("")
        show_examples = gr.State(False)
        
        # Examples (toggle visibility)
        examples_row = gr.Examples(
            examples=[
                ["Explain this Python function and suggest improvements"],
                ["Generate a FastAPI endpoint for user authentication"],
                ["What are best practices for error handling?"],
                ["Refactor this function to be more efficient"],
                ["Review this code for security vulnerabilities"],
            ],
            inputs=msg_input,
            label="💡 Example Prompts"
        )
        
        # Event Handlers
        
        def respond_stream(message: str, history: List, temp: float, max_tok: int, stream: bool) -> Generator:
            """Handle chat response with streaming support."""
            if not message.strip():
                yield history
                return
            
            # Add user message
            history.append({"role": "user", "content": message})
            history.append({"role": "assistant", "content": ""})
            
            if stream:
                # Streaming mode
                async def stream_response():
                    full_response = ""
                    try:
                        async for chunk in llm_client.stream_chat(message, temperature=temp, max_tokens=max_tok):
                            full_response += chunk
                            history[-1]["content"] = full_response
                            yield history
                    except Exception as e:
                        history[-1]["content"] = f"❌ Error: {str(e)}"
                        yield history
                
                # Run async generator
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    async_gen = stream_response()
                    while True:
                        try:
                            result = loop.run_until_complete(async_gen.__anext__())
                            yield result
                        except StopAsyncIteration:
                            break
                finally:
                    loop.close()
            else:
                # Non-streaming mode
                try:
                    response = asyncio.run(llm_client.generate(message, temperature=temp, max_tokens=max_tok))
                    history[-1]["content"] = response
                except Exception as e:
                    history[-1]["content"] = f"❌ Error: {str(e)}"
                
                yield history
        
        def upload_files(files) -> Tuple[str, dict]:
            """Handle file uploads."""
            if not files:
                return "No files uploaded", context_builder.get_stats()
            
            context_builder.clear()
            
            results = []
            for file in files:
                success, message = context_builder.add_file(file.name)
                status = "✅" if success else "❌"
                results.append(f"{status} {message}")
            
            status_text = "\n".join(results)
            stats = context_builder.get_stats()
            
            return status_text, stats
        
        def clear_context() -> Tuple[str, dict]:
            """Clear context files."""
            context_builder.clear()
            return "Context cleared", context_builder.get_stats()
        
        def clear_chat() -> Tuple[List, str]:
            """Clear chat history."""
            return [], ""
        
        def retry_last(history: List, last_msg: str, temp: float, max_tok: int, stream: bool) -> Generator:
            """Retry last message."""
            if not last_msg:
                yield history
                return
            
            # Remove last exchange
            if len(history) >= 2 and history[-2].get("role") == "user":
                history = history[:-2]
            
            yield from respond_stream(last_msg, history, temp, max_tok, stream)
        
        def toggle_mcp(enabled: bool) -> str:
            """Toggle MCP on/off."""
            mcp_manager.toggle(enabled)
            status = "✅ MCP Enabled" if enabled else "⚠️ MCP Disabled"
            return status
        
        # Wire events
        send_btn.click(
            respond_stream,
            inputs=[msg_input, chatbot, temperature, max_tokens, stream_enabled],
            outputs=[chatbot]
        ).then(
            lambda: ("", context_builder.get_stats()),
            outputs=[msg_input, stats_display]
        ).then(
            lambda hist: hist[-2]["content"] if len(hist) >= 2 else "",
            inputs=[chatbot],
            outputs=[last_user_msg]
        )
        
        msg_input.submit(
            respond_stream,
            inputs=[msg_input, chatbot, temperature, max_tokens, stream_enabled],
            outputs=[chatbot]
        ).then(
            lambda: ("", context_builder.get_stats()),
            outputs=[msg_input, stats_display]
        ).then(
            lambda hist: hist[-2]["content"] if len(hist) >= 2 else "",
            inputs=[chatbot],
            outputs=[last_user_msg]
        )
        
        clear_btn.click(clear_chat, outputs=[chatbot, last_user_msg])
        retry_btn.click(
            retry_last,
            inputs=[chatbot, last_user_msg, temperature, max_tokens, stream_enabled],
            outputs=[chatbot]
        )
        
        file_upload.change(upload_files, inputs=[file_upload], outputs=[context_status, stats_display])
        clear_context_btn.click(clear_context, outputs=[context_status, stats_display])
        mcp_enabled.change(toggle_mcp, inputs=[mcp_enabled], outputs=[mcp_status])
        
        # Footer (mobile-friendly)
        gr.Markdown("""
        ---
        <div style="text-align: center; font-size: 14px;">
        <strong>MCP 1st Birthday Hackathon</strong> | 
        <a href="https://github.com/JuanCS-Dev/qwen-dev-cli" target="_blank">GitHub</a> | 
        <em>Soli Deo Gloria</em> 🙏
        </div>
        """)
    
    return demo


if __name__ == "__main__":
    demo = create_ui()
    demo.launch(
        server_name="0.0.0.0",
        server_port=config.gradio_port,
        share=config.gradio_share
    )
