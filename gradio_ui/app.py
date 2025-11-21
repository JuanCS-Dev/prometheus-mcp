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

from .cli_bridge import CLIStreamBridge
from .components import (
    render_tailwind_header,
    render_gauge,
    render_bar_chart,
    render_dual_gauge,
    render_terminal_logs,
)

PROJECT_ROOT = Path.cwd()

# Initialize CLI bridge
_bridge = CLIStreamBridge()

# System Monitor for live metrics
class SystemMonitor:
    def __init__(self):
        self.token_usage = 0
        self.token_limit = 1000000
        self.safety_history = [0.85, 0.9, 0.88, 0.95, 0.92, 0.94]
        self.logs = [
            f"{time.strftime('%H:%M:%S')} - [INFO] System initialized via MCP protocol",
            f"{time.strftime('%H:%M:%S')} - [INFO] Loaded Constitutional AI constraints",
            f"{time.strftime('%H:%M:%S')} - [SUCCESS] Connected to {_bridge.backend_label}",
        ]
    
    def add_log(self, level: str, message: str):
        """Add a timestamped log entry."""
        timestamp = time.strftime('%H:%M:%S')
        self.logs.append(f"{timestamp} - [{level}] {message}")
        if len(self.logs) > 20:
            self.logs.pop(0)
    
    def increment_tokens(self, count: int):
        """Increment token usage."""
        self.token_usage += count
        if random.random() > 0.7:  # Simulate safety fluctuation
            self.safety_history.pop(0)
            self.safety_history.append(random.uniform(0.85, 1.0))
    
    def get_metrics(self):
        """Get current system metrics."""
        return {
            "token_pct": (self.token_usage / self.token_limit) * 100,
            "token_str": f"{self.token_usage // 1000}k / {self.token_limit // 1000}k",
            "safety_data": self.safety_history,
            "logs": self.logs[-8:]
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
        from qwen_dev_cli.tools.base import ToolRegistry
        from qwen_dev_cli.tools.file_ops import (
            ReadFileTool, WriteFileTool, EditFileTool,
            ListDirectoryTool, DeleteFileTool
        )
        from qwen_dev_cli.tools.file_mgmt import (
            MoveFileTool, CopyFileTool, CreateDirectoryTool,
            ReadMultipleFilesTool, InsertLinesTool
        )
        from qwen_dev_cli.tools.search import SearchFilesTool, GetDirectoryTreeTool
        from qwen_dev_cli.tools.exec import BashCommandTool
        from qwen_dev_cli.tools.git_ops import GitStatusTool, GitDiffTool
        from qwen_dev_cli.tools.context import GetContextTool, SaveSessionTool, RestoreBackupTool
        from qwen_dev_cli.tools.terminal import (
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

async def stream_conversation(
    message: str,
    history: List[Dict[str, Any]],
    session_id: str,
):
    """
    Stream LLM output with live monitoring (async I/O handler).
    
    Following Gradio 6 + Uvicorn async best practices:
    - Uses async/await for network I/O (LLM streaming)
    - Yields frequently to keep event loop responsive
    - No blocking operations in async context
    
    Args:
        message: User input text
        history: Chat history as list of role/content dicts
        session_id: Persistent session identifier
        
    Yields:
        Tuple of (history, logs_html, session_id, gauge1, chart, gauge2)
    """
    if not message.strip():
        metrics = _monitor.get_metrics()
        yield (
            history,
            render_terminal_logs(metrics["logs"]),
            session_id,
            render_gauge(metrics["token_pct"], "TOKEN BUDGET", metrics["token_str"]),
            render_bar_chart(metrics["safety_data"], "SAFETY INDEX"),
            render_dual_gauge(99, "MODEL", 100, "ENV")
        )
        return

    # Initialize session
    session_value = session_id or f"session-{uuid.uuid4().hex[:8]}"
    
    # Update history with user message
    history = history or []
    history.append({"role": "user", "content": message})
    
    # Add thinking state
    history.append({"role": "assistant", "content": "⏳ Analyzing request..."})
    _monitor.add_log("INFO", f"Processing: {message[:40]}...")
    
    metrics = _monitor.get_metrics()
    yield (
        history,
        render_terminal_logs(metrics["logs"]),
        session_value,
        render_gauge(metrics["token_pct"], "TOKEN BUDGET", metrics["token_str"]),
        render_bar_chart(metrics["safety_data"], "SAFETY INDEX"),
        render_dual_gauge(99, "MODEL", 100, "ENV")
    )

    start = time.monotonic()
    live_text = ""
    chunk_count = 0
    
    try:
        # Stream execution (async I/O bound - network call to LLM)
        async for chunk in _bridge.stream_command(message, session_value):
            chunk_text = chunk or ""
            chunk_count += 1
            live_text += chunk_text
            
            # Simulate token usage (in real impl, get from backend)
            _monitor.increment_tokens(len(chunk_text.split()))
            
            # Update chat with streaming cursor
            history[-1]["content"] = live_text + " ▌"
            
            # Get updated metrics
            metrics = _monitor.get_metrics()
            
            yield (
                history,
                render_terminal_logs(metrics["logs"]),
                session_value,
                render_gauge(metrics["token_pct"], "TOKEN BUDGET", metrics["token_str"]),
                render_bar_chart(metrics["safety_data"], "SAFETY INDEX"),
                render_dual_gauge(99, "MODEL", 100, "ENV")
            )
            
            # CRITICAL: Yield to event loop (Gradio 6 async best practice)
            # Prevents blocking Uvicorn when stream is very fast
            await asyncio.sleep(0)
            
    except Exception as e:
        # Error state
        error_msg = f"❌ **Error**: {str(e)}"
        history[-1]["content"] = error_msg
        _monitor.add_log("ERROR", str(e))
        metrics = _monitor.get_metrics()
        yield (
            history,
            render_terminal_logs(metrics["logs"]),
            session_value,
            render_gauge(metrics["token_pct"], "TOKEN BUDGET", metrics["token_str"]),
            render_bar_chart(metrics["safety_data"], "SAFETY INDEX"),
            render_dual_gauge(99, "MODEL", 100, "ENV")
        )
        return

    # Complete state - remove cursor
    history[-1]["content"] = live_text
    _monitor.add_log("SUCCESS", f"Task completed. {chunk_count} chunks processed.")
    
    # Final metrics
    metrics = _monitor.get_metrics()
    yield (
        history,
        render_terminal_logs(metrics["logs"]),
        session_value,
        render_gauge(metrics["token_pct"], "TOKEN BUDGET", metrics["token_str"]),
        render_bar_chart(metrics["safety_data"], "SAFETY INDEX"),
        render_dual_gauge(99, "MODEL", 100, "ENV")
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
        
        # HEADER (Cyberpunk Style)
        with gr.Row(elem_classes="mb-2 items-center border-b border-gray-800 pb-2"):
            with gr.Column(scale=1):
                gr.Markdown("# GEMINI-CLI-2", elem_classes="text-2xl font-bold text-white tracking-tighter cyber-glow")
                gr.Markdown("THE BOSS // NEW STANDARD", elem_classes="text-[10px] text-cyber-accent tracking-[0.3em] -mt-2")
            with gr.Column(scale=1):
                gr.Markdown("Resistance is futile.", elem_classes="text-right text-red-500 text-xs font-mono animate-pulse")
        
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
            with gr.Column(scale=3):
                # Chat
                chatbot = gr.Chatbot(
                    label="Dev Session",
                    height=400,
                    render_markdown=True,
                    avatar_images=(None, None),
                    elem_classes="cyber-glass"
                )
                
                # Input Area
                with gr.Group(elem_classes="mb-4 relative"):
                    msg_input = gr.Textbox(
                        placeholder="> Aguardando comando do Mestre...",
                        show_label=False,
                        lines=1,
                        max_lines=3,
                        elem_classes="cyber-input text-sm",
                        autofocus=True,
                    )
                
                # Terminal Logs (HTML)
                log_display = gr.HTML(
                    value=render_terminal_logs(_monitor.logs[-8:]),
                    elem_classes="h-32 overflow-hidden bg-black/50 rounded border border-gray-800 terminal-log"
                )

            # COLUMN 3: TELEMETRY
            with gr.Column(scale=1, min_width=250, elem_classes="space-y-4"):
                
                # Token Gauge
                with gr.Group(elem_classes="cyber-glass h-48"):
                    gauge_html = gr.HTML(
                        value=render_gauge(0, "TOKEN BUDGET", "0k/1M")
                    )
                
                # Safety Chart
                with gr.Group(elem_classes="cyber-glass h-32"):
                    chart_html = gr.HTML(
                        value=render_bar_chart([0.85, 0.9, 0.88, 0.95, 0.92, 0.94], "SAFETY INDEX")
                    )
                
                # Status Mini-Gauges
                with gr.Group(elem_classes="cyber-glass h-24"):
                    status_html = gr.HTML(
                        value=render_dual_gauge(99, "MODEL", 100, "ENV")
                    )
                
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
        
        # Submit message (cyberpunk version with 6 outputs)
        msg_input.submit(
            fn=stream_conversation,
            inputs=[msg_input, chatbot, session_state],
            outputs=[chatbot, log_display, session_state, gauge_html, chart_html, status_html]
        ).then(
            fn=lambda: "", outputs=[msg_input]
        )
        
        # Auto-refresh telemetry every 2 seconds
        def refresh_metrics():
            metrics = _monitor.get_metrics()
            return (
                render_gauge(metrics["token_pct"], "TOKEN BUDGET", metrics["token_str"]),
                render_bar_chart(metrics["safety_data"], "SAFETY INDEX"),
                render_dual_gauge(99, "MODEL", 100, "ENV"),
                render_terminal_logs(metrics["logs"])
            )
        
        timer = gr.Timer(2)
        timer.tick(
            refresh_metrics,
            outputs=[gauge_html, chart_html, status_html, log_display]
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
    demo.queue(max_size=10)
    
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
