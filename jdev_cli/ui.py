"""Gradio 6 Web UI for qwen-dev-cli - SPECTACULAR CHAMPION EDITION.

Features:
- Gradio 6 compatible (theme and css in launch())
- Cyberpunk glassmorphism theme
- DevSquad multi-agent visualization  
- Real-time workflow tracking
- Mobile-responsive design
"""

import asyncio
from typing import List, Tuple, Generator
import gradio as gr

from .core.llm import llm_client
from .core.context import context_builder
from .core.mcp import mcp_manager
from .core.config import config

# Try to import DevSquad (optional)
try:
    from .orchestration.squad import DevSquad
    from .core.mcp_client import MCPClient
    from .tools.registry_helper import get_default_registry
    DEVSQUAD_AVAILABLE = True
except ImportError:
    DEVSQUAD_AVAILABLE = False


def create_ui() -> gr.Blocks:
    """Create SPECTACULAR Gradio 6 UI.
    
    Returns:
        Gradio Blocks interface (theme and css applied in launch())
    """

    with gr.Blocks(
        title="🚀 QWEN-DEV-CLI - AI DevSquad",
        analytics_enabled=False,
    ) as demo:

        # 🎯 Spectacular Header
        gr.Markdown("""
        <div style="text-align: center; padding: 20px 0;">
            <h1 style="font-size: 48px; margin-bottom: 10px;">
                🚀 QWEN-DEV-CLI
            </h1>
            <p style="font-size: 20px; color: #00ff88; font-weight: 600;">
                AI-Powered DevSquad with Multi-Agent Orchestration
            </p>
            <p style="font-size: 14px; color: #888; margin-top: 10px;">
                ⚡ Architect • Explorer • Planner • Refactorer • Reviewer ⚡
            </p>
        </div>
        """)

        # 🎮 Main Layout
        with gr.Row():
            # Left: Chat Interface (70%)
            with gr.Column(scale=7, min_width=400):
                chatbot = gr.Chatbot(
                    label="💬 AI DevSquad Chat",
                    height=600,
                    show_label=True,
                    container=True,
                    # Gradio 6: No 'type' parameter, messages format is default
                    # Gradio 6: Use 'buttons' instead of 'show_copy_button'
                    buttons=["copy"],
                    elem_classes=["chat-container"],
                )

                # Input area
                with gr.Row():
                    msg_input = gr.Textbox(
                        placeholder="🎯 Ask DevSquad to architect, explore, plan, code, or review...",
                        label="Your Message",
                        lines=3,
                        max_lines=6,
                        scale=5,
                        autofocus=True,
                        show_label=False,
                        container=False,
                    )
                    send_btn = gr.Button(
                        "🚀 SEND",
                        variant="primary",
                        scale=1,
                        min_width=100,
                        size="lg"
                    )

                # Action buttons
                with gr.Row():
                    clear_btn = gr.Button("🗑️ Clear", size="sm", scale=1, variant="secondary")
                    retry_btn = gr.Button("♻️ Retry", size="sm", scale=1, variant="secondary")
                    if DEVSQUAD_AVAILABLE:
                        squad_btn = gr.Button("🤖 DevSquad", size="sm", scale=1, variant="primary")
                    examples_btn = gr.Button("💡 Examples", size="sm", scale=1, variant="secondary")

            # Right: Controls & Status (30%)
            with gr.Column(scale=3, min_width=320):

                # 🤖 DevSquad Status (if available)
                if DEVSQUAD_AVAILABLE:
                    with gr.Accordion("🤖 DevSquad Status", open=True):
                        squad_status = gr.Markdown("""
                        <div class="agent-card">
                            <h3>🏗️ Architect</h3>
                            <span class="status-dot status-idle"></span> Idle
                        </div>
                        <div class="agent-card">
                            <h3>🔍 Explorer</h3>
                            <span class="status-dot status-idle"></span> Idle
                        </div>
                        <div class="agent-card">
                            <h3>📋 Planner</h3>
                            <span class="status-dot status-idle"></span> Idle
                        </div>
                        <div class="agent-card">
                            <h3>⚙️ Refactorer</h3>
                            <span class="status-dot status-idle"></span> Idle
                        </div>
                        <div class="agent-card">
                            <h3>✅ Reviewer</h3>
                            <span class="status-dot status-idle"></span> Idle
                        </div>
                        """, elem_classes=["squad-status"])

                        squad_mode = gr.Checkbox(
                            label="Enable DevSquad Orchestration",
                            value=False,
                            info="Use multi-agent workflow"
                        )

                # ⚙️ Model Settings
                with gr.Accordion("⚙️ Model Settings", open=True):
                    provider_dropdown = gr.Dropdown(
                        choices=llm_client.get_available_providers(),
                        value="auto",
                        label="🎯 LLM Provider",
                        info="Smart routing (auto recommended)",
                        interactive=True
                    )

                    temperature = gr.Slider(
                        minimum=0.0,
                        maximum=2.0,
                        value=config.temperature,
                        step=0.1,
                        label="🌡️ Temperature",
                        info="Creativity level"
                    )

                    max_tokens = gr.Slider(
                        minimum=128,
                        maximum=8192,
                        value=config.max_tokens,
                        step=128,
                        label="📏 Max Tokens",
                        info="Response length"
                    )

                    stream_enabled = gr.Checkbox(
                        label="⚡ Enable Streaming",
                        value=True,
                        info="Real-time response"
                    )

                # 📁 Context Files
                with gr.Accordion("📁 Context Files", open=False):
                    file_upload = gr.File(
                        label="Upload Code Files",
                        file_count="multiple",
                        file_types=[".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".cpp", ".c", ".go", ".rs", ".md", ".txt", ".json", ".yaml", ".yml", ".toml"],
                        elem_classes=["upload-area"],
                        height=140
                    )

                    context_status = gr.Textbox(
                        label="Status",
                        value="📂 No files loaded",
                        interactive=False,
                        lines=2,
                        show_label=False
                    )

                    clear_context_btn = gr.Button("🧹 Clear Context", size="sm", variant="secondary")

                # 🔧 MCP Tools
                with gr.Accordion("🔧 MCP Tools", open=False):
                    mcp_enabled = gr.Checkbox(
                        label="Enable MCP Filesystem",
                        value=mcp_manager.enabled,
                        info="Access local files"
                    )

                    mcp_status = gr.Textbox(
                        label="MCP Status",
                        value="✅ Ready" if mcp_manager.enabled else "⚠️ Disabled",
                        interactive=False,
                        show_label=False
                    )

                # ⚡ Performance Metrics
                with gr.Accordion("⚡ Performance", open=True):
                    perf_display = gr.Markdown("""
                    **Last Response:**
                    - 🎯 Provider: Not used yet
                    - ⚡ TTFT: - ms
                    - ⏱️ Total: - s
                    - 🔥 Status: Ready
                    """, elem_classes=["perf-metrics"])

                # 📊 Statistics
                with gr.Accordion("📊 Statistics", open=False):
                    stats_display = gr.JSON(
                        label="Context Stats",
                        value={"files": 0, "chars": 0, "tokens": 0}
                    )

        # State management
        chat_history = gr.State([])
        last_user_msg = gr.State("")

        # 💡 Examples
        examples_row = gr.Examples(
            examples=[
                ["🏗️ Architect: Analyze if we can add JWT authentication"],
                ["🔍 Explorer: Find all authentication-related files"],
                ["📋 Planner: Create plan to add user registration"],
                ["⚙️ Refactorer: Implement login endpoint with error handling"],
                ["✅ Reviewer: Review code for security vulnerabilities"],
                ["🤖 DevSquad: Add complete authentication system with JWT"],
            ],
            inputs=msg_input,
            label="💡 Example Prompts"
        )

        # 🎯 Event Handlers

        def respond_stream(message: str, history: List, temp: float, max_tok: int, stream: bool, provider: str, use_squad: bool = False) -> Generator:
            """Handle chat response with optional DevSquad."""
            import time

            if not message.strip():
                yield history, None, None
                return

            # Add user message (Gradio 6 messages format)
            history.append({"role": "user", "content": message})
            history.append({"role": "assistant", "content": ""})

            start_time = time.time()
            first_token_time = None

            # DevSquad mode
            if use_squad and DEVSQUAD_AVAILABLE:
                try:
                    # Update status
                    squad_html = """
                    <div class="agent-card agent-active">
                        <h3>🏗️ Architect</h3>
                        <span class="status-dot status-active"></span> Analyzing...
                    </div>
                    <div class="agent-card">
                        <h3>🔍 Explorer</h3>
                        <span class="status-dot status-idle"></span> Waiting
                    </div>
                    <div class="agent-card">
                        <h3>📋 Planner</h3>
                        <span class="status-dot status-idle"></span> Waiting
                    </div>
                    <div class="agent-card">
                        <h3>⚙️ Refactorer</h3>
                        <span class="status-dot status-idle"></span> Waiting
                    </div>
                    <div class="agent-card">
                        <h3>✅ Reviewer</h3>
                        <span class="status-dot status-idle"></span> Waiting
                    </div>
                    """
                    yield history, squad_html, None

                    # Execute DevSquad
                    registry = get_default_registry()
                    mcp_client = MCPClient(registry)
                    squad = DevSquad(llm_client, mcp_client, require_human_approval=False)

                    async def run_squad():
                        return await squad.execute_workflow(message)

                    result = asyncio.run(run_squad())

                    # Format response
                    response_text = "**DevSquad Workflow Complete!**\n\n"
                    response_text += f"**Status:** {result.status.value}\n"
                    response_text += f"**Phases:** {len(result.phases)}\n\n"

                    for phase in result.phases:
                        icon = "✅" if phase.success else "❌"
                        response_text += f"{icon} **{phase.phase.value.capitalize()}**: {phase.duration_seconds:.2f}s\n"

                    history[-1]["content"] = response_text

                    # Final status
                    squad_html = """
                    <div class="agent-card">
                        <h3>🏗️ Architect</h3>
                        <span class="status-dot status-active"></span> ✅ Complete
                    </div>
                    <div class="agent-card">
                        <h3>🔍 Explorer</h3>
                        <span class="status-dot status-active"></span> ✅ Complete
                    </div>
                    <div class="agent-card">
                        <h3>📋 Planner</h3>
                        <span class="status-dot status-active"></span> ✅ Complete
                    </div>
                    <div class="agent-card">
                        <h3>⚙️ Refactorer</h3>
                        <span class="status-dot status-active"></span> ✅ Complete
                    </div>
                    <div class="agent-card">
                        <h3>✅ Reviewer</h3>
                        <span class="status-dot status-active"></span> ✅ Complete
                    </div>
                    """

                    total_time = time.time() - start_time
                    perf_info = f"""
**Last Response:**
- 🎯 Provider: DevSquad (Multi-Agent)
- ⚡ TTFT: {(time.time() - start_time) * 1000:.0f}ms
- ⏱️ Total: {total_time:.2f}s
- 🔥 Status: ✅ Complete
"""
                    yield history, squad_html, perf_info
                    return

                except Exception as e:
                    history[-1]["content"] = f"❌ DevSquad Error: {str(e)}"
                    yield history, None, None
                    return

            # Regular LLM mode
            if stream:
                async def stream_response():
                    nonlocal first_token_time
                    full_response = ""
                    try:
                        async for chunk in llm_client.stream_chat(message, temperature=temp, max_tokens=max_tok, provider=provider):
                            if first_token_time is None:
                                first_token_time = time.time()
                            full_response += chunk
                            history[-1]["content"] = full_response

                            elapsed = (time.time() - start_time) * 1000
                            ttft = (first_token_time - start_time) * 1000 if first_token_time else elapsed

                            perf_info = f"""
**Last Response:**
- 🎯 Provider: `{provider}`
- ⚡ TTFT: {ttft:.0f}ms
- ⏱️ Streaming: {elapsed:.0f}ms
- 🔥 Status: Streaming...
"""
                            yield history, None, perf_info
                    except Exception as e:
                        history[-1]["content"] = f"❌ Error: {str(e)}"
                        yield history, None, None

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
                try:
                    response = asyncio.run(llm_client.generate(message, temperature=temp, max_tokens=max_tok, provider=provider))
                    history[-1]["content"] = response

                    total_time = time.time() - start_time
                    perf_info = f"""
**Last Response:**
- 🎯 Provider: `{provider}`
- ⏱️ Total: {total_time:.2f}s
- 🔥 Status: ✅ Complete
"""
                    yield history, None, perf_info
                except Exception as e:
                    history[-1]["content"] = f"❌ Error: {str(e)}"
                    yield history, None, None

        def upload_files(files) -> Tuple[str, dict]:
            """Handle file uploads."""
            if not files:
                return "📂 No files uploaded", context_builder.get_stats()

            context_builder.clear()

            results = []
            for file in files:
                success, message = context_builder.add_file(file.name)
                status = "✅" if success else "❌"
                results.append(f"{status} {message}")

            status_text = "\n".join(results)
            stats = context_builder.get_stats()

            return f"📁 {status_text}", stats

        def clear_context() -> Tuple[str, dict]:
            """Clear context files."""
            context_builder.clear()
            return "🧹 Context cleared", context_builder.get_stats()

        def clear_chat() -> Tuple[List, str]:
            """Clear chat history."""
            return [], ""

        def toggle_mcp(enabled: bool) -> str:
            """Toggle MCP on/off."""
            mcp_manager.toggle(enabled)
            return "✅ MCP Enabled" if enabled else "⚠️ MCP Disabled"

        # Wire events
        send_outputs = [chatbot, perf_display] if not DEVSQUAD_AVAILABLE else [chatbot, squad_status, perf_display]
        send_inputs = [msg_input, chatbot, temperature, max_tokens, stream_enabled, provider_dropdown]
        if DEVSQUAD_AVAILABLE:
            send_inputs.append(squad_mode)

        send_btn.click(
            respond_stream,
            inputs=send_inputs,
            outputs=send_outputs
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
            inputs=send_inputs,
            outputs=send_outputs
        ).then(
            lambda: ("", context_builder.get_stats()),
            outputs=[msg_input, stats_display]
        ).then(
            lambda hist: hist[-2]["content"] if len(hist) >= 2 else "",
            inputs=[chatbot],
            outputs=[last_user_msg]
        )

        clear_btn.click(clear_chat, outputs=[chatbot, last_user_msg])
        file_upload.change(upload_files, inputs=[file_upload], outputs=[context_status, stats_display])
        clear_context_btn.click(clear_context, outputs=[context_status, stats_display])
        mcp_enabled.change(toggle_mcp, inputs=[mcp_enabled], outputs=[mcp_status])

        # Footer
        gr.Markdown("""
        ---
        <div style="text-align: center; padding: 20px 0;">
            <p style="font-size: 16px; color: #00ff88; font-weight: 600;">
                ⚡ Powered by DevSquad Multi-Agent System ⚡
            </p>
            <p style="font-size: 14px; color: #888;">
                <strong>MCP 1st Birthday Hackathon</strong> | 
                <a href="https://github.com/JuanCS-Dev/qwen-dev-cli" target="_blank" style="color: #0088ff;">GitHub</a> | 
                <em>Soli Deo Gloria</em> 🙏
            </p>
        </div>
        """)

    return demo


if __name__ == "__main__":
    demo = create_ui()

    # 🎨 Gradio 6: Theme and CSS go in launch(), not Blocks()
    theme = gr.themes.Base(
        primary_hue="green",
        secondary_hue="blue",
        neutral_hue="slate",
        font=["Inter", "system-ui", "sans-serif"],
    ).set(
        body_background_fill="*neutral_950",
        body_text_color="*neutral_100",
        button_primary_background_fill="*primary_500",
        button_primary_text_color="*neutral_950",
    )

    # 🎨 Spectacular Cyberpunk CSS
    spectacular_css = """
    /* Cyberpunk Glassmorphism Theme */
    :root {
        --primary-glow: #00ff88;
        --secondary-glow: #0088ff;
        --accent-glow: #ff0088;
        --glass-bg: rgba(15, 15, 35, 0.7);
        --glass-border: rgba(255, 255, 255, 0.1);
    }
    
    .gradio-container {
        background: linear-gradient(135deg, #0a0a1f 0%, #1a0a2e 50%, #0f0a1f 100%) !important;
        background-attachment: fixed !important;
    }
    
    .gr-box, .gr-panel, .gr-form {
        background: var(--glass-bg) !important;
        backdrop-filter: blur(10px) !important;
        border: 1px solid var(--glass-border) !important;
        border-radius: 16px !important;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3) !important;
    }
    
    h1, h2, h3 {
        background: linear-gradient(90deg, var(--primary-glow), var(--secondary-glow));
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        font-weight: 800 !important;
    }
    
    .gr-button {
        background: linear-gradient(135deg, var(--primary-glow), var(--secondary-glow)) !important;
        border: none !important;
        border-radius: 12px !important;
        color: #0a0a1f !important;
        font-weight: 700 !important;
        min-height: 48px !important;
        transition: all 0.3s ease !important;
    }
    
    .gr-button:hover {
        transform: translateY(-2px) scale(1.02) !important;
        box-shadow: 0 8px 32px rgba(0, 255, 136, 0.5) !important;
    }
    
    /* Agent cards */
    .agent-card {
        background: var(--glass-bg) !important;
        border: 1px solid var(--glass-border) !important;
        border-radius: 12px !important;
        padding: 12px !important;
        margin: 8px 0 !important;
        transition: all 0.3s ease !important;
    }
    
    .agent-card:hover {
        border-color: var(--primary-glow) !important;
        transform: scale(1.02) !important;
    }
    
    .agent-active {
        border-color: var(--primary-glow) !important;
        box-shadow: 0 0 20px rgba(0, 255, 136, 0.4) !important;
        animation: pulse-border 1.5s ease-in-out infinite !important;
    }
    
    @keyframes pulse-border {
        0%, 100% { border-color: var(--primary-glow); }
        50% { border-color: var(--secondary-glow); }
    }
    
    /* Status dots */
    .status-dot {
        display: inline-block;
        width: 10px;
        height: 10px;
        border-radius: 50%;
        margin-right: 8px;
    }
    
    .status-active {
        background: var(--primary-glow);
        box-shadow: 0 0 10px var(--primary-glow);
        animation: pulse 2s ease-in-out infinite;
    }
    
    .status-idle {
        background: #666;
    }
    
    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.5; }
    }
    
    /* Mobile responsive */
    @media (max-width: 768px) {
        .gr-button {
            min-height: 44px !important;
            font-size: 14px !important;
        }
        
        h1 { font-size: 32px !important; }
    }
    """

    demo.launch(
        server_name="0.0.0.0",
        server_port=config.gradio_port,
        share=config.gradio_share,
        show_error=True,
        theme=theme,
        css=spectacular_css,
    )
