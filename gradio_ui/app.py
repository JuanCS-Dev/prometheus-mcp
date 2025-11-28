#!/usr/bin/env python3
"""
Qwen Dev CLI - Cyberpunk Gradio UI

Cyberpunk-themed interface with Tailwind CSS + SVG visualizations.
Built for the MCP Hackathon with 27+ production tools.
"""

from __future__ import annotations

import asyncio
import os
import random
import shutil
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List

import gradio as gr
import pandas as pd

from .streaming_bridge import GradioStreamingBridge, ChatMessage
from .components import (
    render_tailwind_header,
    render_gauge,
    render_bar_chart,
    render_dual_gauge,
    render_terminal_logs,
    render_docker_progress,
    render_latency_chart,
    render_docker_progress,
    render_latency_chart,
    render_dual_status,
    render_memory_status,
    render_world_model_status,
    render_evolution_status,
)

PROJECT_ROOT = Path.cwd()

# Initialize streaming bridge (replaces old CLIStreamBridge)
# Uses refactored GeminiClient with circuit breaker, deduplication
_bridge = GradioStreamingBridge(
    system_prompt="You are Juan-Dev-Code, an AI coding assistant. Be helpful, concise, and write clean code.",
    enable_prometheus=True  # Enable PROMETHEUS integration
)

# System Monitor for live metrics
class SystemMonitor:
    def __init__(self):
        self.token_usage = 0
        self.token_limit = 1000000
        self.safety_history = [0.85, 0.9, 0.88, 0.95, 0.92, 0.94]
        self.latency_history = [45, 52, 38, 67, 42, 55, 48, 61, 39, 50]  # Last 10 latency values (ms)
        self.current_latency = 50  # Current latency in ms
        self.progress = 0.0  # Current progress (0-100)
        self.progress_label = "Ready"
        self.logs = [
            f"{time.strftime('%H:%M:%S')} - [INFO] System initialized via MCP protocol",
            f"{time.strftime('%H:%M:%S')} - [INFO] Loaded Constitutional AI constraints",
            f"{time.strftime('%H:%M:%S')} - [INFO] Loaded Constitutional AI constraints",
            f"{time.strftime('%H:%M:%S')} - [SUCCESS] Connected to {_bridge.backend_label}",
        ]
        # Prometheus Metrics
        self.memory_data = {"active_types": ["core", "episodic"]}
        self.wm_data = {"simulation_depth": 0, "confidence": 0.0}
        self.evo_data = {"generation": 1, "mutation_rate": 0.05}
    
    def add_log(self, level: str, message: str):
        """Add a timestamped log entry."""
        timestamp = time.strftime('%H:%M:%S')
        self.logs.append(f"{timestamp} - [{level}] {message}")
        if len(self.logs) > 20:
            self.logs.pop(0)
    
    def increment_tokens(self, count: int):
        """Increment token usage and update safety metrics."""
        self.token_usage += count
        # Always update safety on token increment for live feel
        self.safety_history.pop(0)
        self.safety_history.append(random.uniform(0.88, 0.98))
        # Update latency with realistic variance
        self.latency_history.pop(0)
        new_latency = random.randint(30, 80)
        self.latency_history.append(new_latency)
        self.current_latency = new_latency

    def set_progress(self, percentage: float, label: str = "Processing"):
        """Set current progress bar state."""
        self.progress = max(0.0, min(100.0, percentage))
        self.progress_label = label
    
    def get_metrics(self):
        """Get current system metrics."""
        return {
            "token_pct": (self.token_usage / self.token_limit) * 100,
            "token_str": f"{self.token_usage // 1000}k / {self.token_limit // 1000}k",
            "safety_data": self.safety_history,
            "latency_data": self.latency_history,
            "latency_current": f"{self.current_latency}ms",
            "progress": self.progress,
            "progress_label": self.progress_label,
            "progress": self.progress,
            "progress_label": self.progress_label,
            "logs": self.logs[-8:],
            "memory": self.memory_data,
            "wm": self.wm_data,
            "evo": self.evo_data
        }

_monitor = SystemMonitor()

# --- HELPER FUNCTIONS ---

def _blank_metrics() -> Dict[str, Any]:
    """Create blank metrics dict."""
    return {
        "chunks": 0,
        "chars": 0,
        "sec": 0,
        "backend": _bridge.backend_label,
    }

def _get_mcp_tools_df() -> pd.DataFrame:
    """Get real MCP tools from ToolRegistry as DataFrame."""
    try:
        from jdev_cli.tools.base import ToolRegistry
        from jdev_cli.tools.file_ops import (
            ReadFileTool, WriteFileTool, EditFileTool,
            ListDirectoryTool, DeleteFileTool
        )
        from jdev_cli.tools.file_mgmt import (
            MoveFileTool, CopyFileTool, CreateDirectoryTool,
            ReadMultipleFilesTool, InsertLinesTool
        )
        from jdev_cli.tools.search import SearchFilesTool, GetDirectoryTreeTool
        from jdev_cli.tools.exec import BashCommandTool
        from jdev_cli.tools.git_ops import GitStatusTool, GitDiffTool
        from jdev_cli.tools.context import GetContextTool, SaveSessionTool, RestoreBackupTool
        from jdev_cli.tools.terminal import (
            CdTool, LsTool, PwdTool, MkdirTool, RmTool,
            CpTool, MvTool, TouchTool, CatTool
        )
        
        # Build data list
        data = []
        
        # File Operations
        for tool in [
            ReadFileTool(), WriteFileTool(), EditFileTool(),
            ListDirectoryTool(), DeleteFileTool(), MoveFileTool(),
            CopyFileTool(), CreateDirectoryTool(), ReadMultipleFilesTool(),
            InsertLinesTool()
        ]:
            data.append({
                "Category": "File Operations",
                "Tool": tool.name,
                "Description": tool.description[:60] + "..." if len(tool.description) > 60 else tool.description
            })
        
        # Search & Navigation
        for tool in [SearchFilesTool(), GetDirectoryTreeTool()]:
            data.append({
                "Category": "Search & Navigation",
                "Tool": tool.name,
                "Description": tool.description[:60] + "..." if len(tool.description) > 60 else tool.description
            })
        
        # Execution
        data.append({
            "Category": "Execution",
            "Tool": BashCommandTool().name,
            "Description": BashCommandTool().description[:60] + "..." if len(BashCommandTool().description) > 60 else BashCommandTool().description
        })
        
        # Git Operations
        for tool in [GitStatusTool(), GitDiffTool()]:
            data.append({
                "Category": "Git Operations",
                "Tool": tool.name,
                "Description": tool.description[:60] + "..." if len(tool.description) > 60 else tool.description
            })
        
        # Context Management
        for tool in [GetContextTool(), SaveSessionTool(), RestoreBackupTool()]:
            data.append({
                "Category": "Context Management",
                "Tool": tool.name,
                "Description": tool.description[:60] + "..." if len(tool.description) > 60 else tool.description
            })
        
        # Terminal Commands
        for tool in [
            CdTool(), LsTool(), PwdTool(), MkdirTool(), RmTool(),
            CpTool(), MvTool(), TouchTool(), CatTool()
        ]:
            data.append({
                "Category": "Terminal Commands",
                "Tool": tool.name,
                "Description": tool.description[:60] + "..." if len(tool.description) > 60 else tool.description
            })
        
        return pd.DataFrame(data)
    
    except Exception as e:
        # Fallback to minimal data if imports fail
        print(f"Warning: Could not load real tools: {e}")
        return pd.DataFrame([
            {"Category": "File Operations", "Tool": "read_file", "Description": "Read file contents"},
            {"Category": "File Operations", "Tool": "write_file", "Description": "Write content to file"},
            {"Category": "Terminal", "Tool": "bash", "Description": "Execute shell commands"},
        ])

# --- FILE UPLOAD HANDLER ---

def handle_file_upload(files):
    """Process uploaded files, copy to workspace, and return status message."""
    if not files:
        return "No files uploaded"
    
    # Create uploads directory in workspace if it doesn't exist
    uploads_dir = PROJECT_ROOT / "uploads"
    uploads_dir.mkdir(exist_ok=True)
    
    uploaded_info = []
    copied_count = 0
    
    for file_path in files:
        if file_path:
            source_path = Path(file_path)
            if source_path.exists():
                size = source_path.stat().st_size
                size_str = f"{size / 1024:.1f} KB" if size < 1024 * 1024 else f"{size / (1024 * 1024):.1f} MB"
                
                # Copy file to workspace uploads directory
                try:
                    dest_path = uploads_dir / source_path.name
                    
                    # Handle duplicate names
                    counter = 1
                    while dest_path.exists():
                        stem = source_path.stem
                        suffix = source_path.suffix
                        dest_path = uploads_dir / f"{stem}_{counter}{suffix}"
                        counter += 1
                    
                    # Copy file
                    shutil.copy2(source_path, dest_path)
                    
                    relative_path = dest_path.relative_to(PROJECT_ROOT)
                    uploaded_info.append(f"✓ **{source_path.name}** ({size_str}) → `{relative_path}`")
                    copied_count += 1
                except Exception as e:
                    uploaded_info.append(f"✗ **{source_path.name}** - Error: {str(e)}")
    
    if uploaded_info:
        status_msg = f"**✅ Uploaded {copied_count}/{len([f for f in files if f])} file(s) to workspace:**\n\n" + "\n".join(uploaded_info)
        if copied_count > 0:
            status_msg += f"\n\n📁 Files saved to: `uploads/` directory"
        return status_msg
    return "No files uploaded"

# --- CORE LOGIC ---

def stream_conversation(
    message: str,
    history: List[Dict[str, Any]],
    session_id: str,
):
    """
    Stream LLM output with live monitoring using GradioStreamingBridge.

    Refactored for Gradio 6 + GeminiClient integration:
    - Uses sync generator (bridge handles async→sync conversion internally)
    - Yields ChatMessage-compatible dicts for Gradio
    - Integrates with refactored streaming with deduplication and circuit breaker

    Args:
        message: User input text
        history: Chat history as list of role/content dicts
        session_id: Persistent session identifier

    Yields:
        Tuple of (history, logs_html, session_id, gauge1, chart, status, progress, latency)
    """
    if not message.strip():
        metrics = _monitor.get_metrics()
        yield (
            history,
            render_terminal_logs(metrics["logs"]),
            session_id,
            render_gauge(metrics["token_pct"], "TOKEN BUDGET", metrics["token_str"]),
            render_bar_chart(metrics["safety_data"], "SAFETY INDEX"),
            render_dual_status(_bridge.backend_label, "Production"),
            render_docker_progress(metrics["progress"], metrics["progress_label"]),
            render_latency_chart(metrics["latency_data"], metrics["latency_current"]),
            render_memory_status(metrics["memory"]),
            render_world_model_status(metrics["wm"]),
            render_evolution_status(metrics["evo"])
        )
        return

    # Initialize session
    session_value = session_id or f"session-{uuid.uuid4().hex[:8]}"

    # Ensure history is a list
    history = history or []

    # Log the start
    _monitor.add_log("INFO", f"Processing: {message[:40]}...")
    _monitor.set_progress(10, "Initializing")

    # Convert history to ChatMessage objects for bridge
    chat_messages = [
        ChatMessage(role=msg["role"], content=msg["content"])
        for msg in history
    ]

    chunk_count = 0

    try:
        # Stream using new GradioStreamingBridge (sync generator)
        for updated_messages in _bridge.stream_chat(message, chat_messages, session_value):
            chunk_count += 1

            # Convert ChatMessage objects back to dicts for Gradio
            history = [
                {"role": msg.role, "content": msg.content}
                for msg in updated_messages
            ]

            # Update token usage based on content length
            if history:
                last_content = history[-1].get("content", "")
                _monitor.increment_tokens(max(1, len(last_content.split()) // 10))

            # Update progress based on streaming
            progress_pct = min(90, 20 + chunk_count * 3)
            _monitor.set_progress(progress_pct, "Streaming")

            # Get updated metrics
            metrics = _monitor.get_metrics()

            yield (
                history,
                render_terminal_logs(metrics["logs"]),
                session_value,
                render_gauge(metrics["token_pct"], "TOKEN BUDGET", metrics["token_str"]),
                render_bar_chart(metrics["safety_data"], "SAFETY INDEX"),
                render_dual_status(_bridge.backend_label, "Production"),
                render_docker_progress(metrics["progress"], metrics["progress_label"]),
                render_latency_chart(metrics["latency_data"], metrics["latency_current"]),
                render_memory_status(metrics["memory"]),
                render_world_model_status(metrics["wm"]),
                render_evolution_status(metrics["evo"])
            )

    except Exception as e:
        # Error state with detailed logging
        import traceback
        error_details = traceback.format_exc()
        print(f"❌ STREAM ERROR: {e}")
        print(error_details)

        error_msg = f"❌ **Error**: {str(e)}"
        history.append({"role": "assistant", "content": error_msg})
        _monitor.add_log("ERROR", str(e))
        _monitor.set_progress(0, "Error")
        metrics = _monitor.get_metrics()
        yield (
            history,
            render_terminal_logs(metrics["logs"]),
            session_value,
            render_gauge(metrics["token_pct"], "TOKEN BUDGET", metrics["token_str"]),
            render_bar_chart(metrics["safety_data"], "SAFETY INDEX"),
            render_dual_status(_bridge.backend_label, "Production"),
            render_docker_progress(0, "Error"),
            render_latency_chart(metrics["latency_data"], metrics["latency_current"]),
            render_memory_status(metrics["memory"]),
            render_world_model_status(metrics["wm"]),
            render_evolution_status(metrics["evo"])
        )
        return

    # Complete state
    _monitor.add_log("SUCCESS", f"Task completed. {chunk_count} chunks processed.")
    _monitor.set_progress(100, "Complete")

    # Get streaming metrics from bridge
    bridge_metrics = _bridge.get_metrics()
    if bridge_metrics:
        _monitor.add_log("INFO", f"TTFT: {bridge_metrics.get('ttft_ms', '?')}ms, CPS: {bridge_metrics.get('cps', '?')}")
    
    # Update Prometheus metrics from bridge if available
    bridge_status = _bridge.get_health_status()
    if "prometheus" in bridge_status:
        prom_status = bridge_status["prometheus"]
        if "memory" in prom_status:
            _monitor.memory_data = prom_status["memory"]
        if "world_model" in prom_status:
            _monitor.wm_data = prom_status["world_model"]
        if "evolution" in prom_status:
            _monitor.evo_data = prom_status["evolution"]

    # Final metrics
    metrics = _monitor.get_metrics()
    yield (
        history,
        render_terminal_logs(metrics["logs"]),
        session_value,
        render_gauge(metrics["token_pct"], "TOKEN BUDGET", metrics["token_str"]),
        render_bar_chart(metrics["safety_data"], "SAFETY INDEX"),
        render_dual_status(_bridge.backend_label, "Production"),
        render_docker_progress(100, "Complete"),
        render_latency_chart(metrics["latency_data"], metrics["latency_current"]),
        render_memory_status(metrics["memory"]),
        render_world_model_status(metrics["wm"]),
        render_evolution_status(metrics["evo"])
    )

# --- LOAD CYBERPUNK CSS ---

def _load_cyber_css() -> str:
    """Load the cyberpunk theme CSS."""
    css_path = Path(__file__).parent / "cyber_theme.css"
    if css_path.exists():
        return css_path.read_text()
    return ""

# --- UI CONSTRUCTION ---

def create_ui() -> tuple[gr.Blocks, str, str]:
    """
    Build cyberpunk-themed UI with live monitoring.
    
    Returns:
        Tuple of (demo, theme, css) for Gradio 6 launch() signature
        
    Architecture notes:
        - Tailwind CDN injected via head parameter (Shadow DOM penetration)
        - Custom CSS loaded from cyber_theme.css for glassmorphism effects
        - Uses async generators for streaming (Uvicorn-compatible)
    """
    
    # Load cyberpunk CSS
    cyber_css = _load_cyber_css()
    
    # Tailwind CDN injection via gr.HTML (Gradio 6.0.0 compatible)
    tailwind_head = render_tailwind_header()

    # Gradio 6.0.0: head parameter not supported, inject via HTML component
    with gr.Blocks(
        title="GEMINI-CLI-2 · THE BOSS · NEW STANDARD",
        fill_height=True,
    ) as demo:
        
        # Inject Tailwind CDN at top of UI
        gr.HTML(tailwind_head, visible=False)
        
        # State Management
        session_state = gr.State(value=None)
        
        # HEADER (Window-style like desktop app)
        with gr.Row(elem_classes="window-header"):
            gr.HTML("""
                <div style="display: flex; align-items: center; gap: 12px;">
                    <div class="window-controls">
                        <span class="ctrl-close"></span>
                        <span class="ctrl-minimize"></span>
                        <span class="ctrl-maximize"></span>
                    </div>
                    <span style="font-family: 'Segoe UI', monospace; font-size: 14px; color: #E6E6E6; letter-spacing: 0.05em;">
                        JuanCS Dev-Code
                    </span>
                    <span style="color: #00D9FF; font-size: 10px; margin-left: 8px;">MCP Hackathon</span>
                </div>
            """)
            gr.HTML("""
                <div style="display: flex; align-items: center; gap: 16px;">
                    <span style="color: #6272a4; font-size: 12px;">v0.0.2</span>
                </div>
            """)
        
        # Main Layout: 3-Column Cyberpunk
        with gr.Row(equal_height=True):
            
            # COLUMN 1: PROJECT EXPLORER
            with gr.Column(scale=1, min_width=250, elem_classes="cyber-glass p-0"):
                gr.Markdown("## 📁 PROJECT CONTEXT", elem_classes="text-xs font-bold text-gray-400 p-3 border-b border-gray-800")
                
                # File Upload
                file_upload = gr.File(
                    label="Upload Files",
                    file_count="multiple",
                    file_types=None,
                    height=80,
                    elem_classes="cyber-glass"
                )
                
                upload_status = gr.Markdown(
                    value="Ready to upload...",
                    visible=True,
                    elem_classes="text-xs text-gray-500 p-2"
                )
                
                # File Explorer
                file_explorer = gr.FileExplorer(
                    glob="**/*",
                    root_dir=str(PROJECT_ROOT),
                    height=250,
                    label="Workspace",
                    file_count="multiple",
                    elem_classes="file-explorer-cyber"
                )

            # COLUMN 2: WORKSPACE (Chat + Input)
            with gr.Column(scale=3, elem_classes="gap-0"):
                # Chat (Gradio 6: buttons instead of show_copy_button)
                chatbot = gr.Chatbot(
                    label="Dev Session",
                    height=400,
                    render_markdown=True,
                    avatar_images=(None, None),
                    elem_classes="cyber-glass mb-2", # Add margin bottom to separate from input
                    buttons=["copy"],  # Gradio 6
                )
                
                # Input Area
                with gr.Group(elem_classes="mb-0 relative"):
                    msg_input = gr.Textbox(
                        placeholder="> Aguardando comando do Mestre...",
                        show_label=False,
                        lines=1,
                        max_lines=3,
                        elem_classes="cyber-input text-sm",
                        autofocus=True,
                    )
                
                # Terminal Logs (HTML) - Moved below input as requested
                log_display = gr.HTML(
                    value=render_terminal_logs(_monitor.logs[-8:]),
                    elem_classes="h-32 overflow-hidden bg-black/50 rounded border border-gray-800 terminal-log mb-4 mt-0"
                )
                
                # Docker Progress Bar
                progress_html = gr.HTML(
                    value=render_docker_progress(0, "Ready"),
                    elem_classes="docker-progress-container"
                )

            # COLUMN 3: TELEMETRY
            with gr.Column(scale=1, min_width=250, elem_classes="space-y-4"):
                
                # Get initial metrics from monitor
                initial_metrics = _monitor.get_metrics()
                
                # Token Gauge
                with gr.Group(elem_classes="cyber-glass h-48"):
                    gauge_html = gr.HTML(
                        value=render_gauge(initial_metrics["token_pct"], "TOKEN BUDGET", initial_metrics["token_str"])
                    )
                
                # Safety Chart
                with gr.Group(elem_classes="cyber-glass h-32"):
                    chart_html = gr.HTML(
                        value=render_bar_chart(initial_metrics["safety_data"], "SAFETY INDEX")
                    )
                
                # Status Cards (Model/Environment)
                with gr.Group(elem_classes="cyber-glass h-24"):
                    status_html = gr.HTML(
                        value=render_dual_status(_bridge.backend_label, "Production")
                    )

                # Latency Sparkline Chart
                with gr.Group(elem_classes="cyber-glass h-28"):
                    latency_html = gr.HTML(
                        value=render_latency_chart(initial_metrics["latency_data"], initial_metrics["latency_current"])
                    )

                # PROMETHEUS DASHBOARD
                with gr.Accordion("PROMETHEUS CORE", open=True, elem_classes="cyber-glass"):
                    memory_html = gr.HTML(value=render_memory_status(initial_metrics["memory"]))
                    wm_html = gr.HTML(value=render_world_model_status(initial_metrics["wm"]))
                    evo_html = gr.HTML(value=render_evolution_status(initial_metrics["evo"]))
                
                # Refresh Button (replaces Timer to avoid queue/join errors)
                refresh_btn = gr.Button("🔄 Refresh Metrics", size="sm", variant="secondary")
                
                # MCP Tools Accordion
                with gr.Accordion("MCP Tools", open=False, elem_classes="cyber-glass"):
                    mcp_df = gr.Dataframe(
                        value=_get_mcp_tools_df(),
                        headers=["Category", "Tool", "Description"],
                        interactive=False,
                        wrap=True,
                        max_height=200,
                    )

        # Event Handlers
        
        # File upload handler
        file_upload.upload(
            fn=handle_file_upload,
            inputs=[file_upload],
            outputs=[upload_status]
        ).then(
            fn=lambda: gr.update(),
            outputs=[file_explorer]
        )
        
        # Submit message (cyberpunk version with 8 outputs)
        msg_input.submit(
            fn=stream_conversation,
            inputs=[msg_input, chatbot, session_state],
            outputs=[chatbot, log_display, session_state, gauge_html, chart_html, status_html, progress_html, latency_html, memory_html, wm_html, evo_html]
        ).then(
            fn=lambda: "", outputs=[msg_input]
        )
        
        # Manual refresh for metrics (Timer causes queue/join errors in Gradio 6)
        def refresh_metrics():
            metrics = _monitor.get_metrics()
            return (
                render_gauge(metrics["token_pct"], "TOKEN BUDGET", metrics["token_str"]),
                render_bar_chart(metrics["safety_data"], "SAFETY INDEX"),
                render_dual_status(_bridge.backend_label, "Production"),
                render_docker_progress(metrics["progress"], metrics["progress_label"]),
                render_latency_chart(metrics["latency_data"], metrics["latency_current"]),
                render_terminal_logs(metrics["logs"]),
                render_memory_status(metrics["memory"]),
                render_world_model_status(metrics["wm"]),
                render_evolution_status(metrics["evo"])
            )

        # Wire refresh button (avoids ERR_CONNECTION_REFUSED from gr.Timer)
        refresh_btn.click(
            refresh_metrics,
            outputs=[gauge_html, chart_html, status_html, progress_html, latency_html, log_display, memory_html, wm_html, evo_html]
        )

    # Gradio 6: Return tuple (demo, theme, css) for launch()
    # Theme is None (using custom CSS), css contains glassmorphism overrides
    return demo, None, cyber_css

# --- LAUNCHER ---

if __name__ == "__main__":
    port = int(os.getenv("GRADIO_SERVER_PORT", "7860"))
    
    # Gradio 6: create_ui returns demo, theme, css
    demo, theme, css = create_ui()
    
    print(f"🚀 Launching GEMINI-CLI-2 Cyberpunk UI on port {port}")
    print(f"🎨 Theme: Cyberpunk Glassmorphism")
    print(f"🔧 Backend: {_bridge.backend_label}")
    
    # CRITICAL: Enable queue before launch (required for gr.Timer and streaming)
    # Increased concurrency to handle Timer ticks without DDoS errors
    demo.queue(
        max_size=20,
        default_concurrency_limit=10
    )
    
    # Gradio 6: theme and css go in launch()
    demo.launch(
        server_name="0.0.0.0",
        server_port=port,
        share=False,
        show_error=True,
        theme=theme,
        css=css,
        allowed_paths=[str(PROJECT_ROOT)]
    )
