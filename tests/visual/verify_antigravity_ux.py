"""
tests/visual/verify_antigravity_ux.py
-------------------------------------
Automated Visual Regression Test for Gemini Native Streaming.
Generates SVG screenshots of the TUI at critical rendering states.
"""
import asyncio
from textual.app import App, ComposeResult
from textual.widgets import Static
from textual.containers import Vertical
from rich.markdown import Markdown
from rich.panel import Panel

# --- MOCK COMPONENTS (Para isolar a UI da Rede) ---

class MockGeminiStream:
    """Simulates Gemini 3 Pro gRPC stream with Antigravity pacing."""

    SCENARIO = [
        # Phase 1: Thinking (Fast, dimmed)
        {"text": "Analyzing request...", "type": "thought"},
        {"text": " The user wants to calculate Fibonacci.", "type": "thought"},

        # Phase 2: Native Tool Call (High visibility)
        {"text": "", "tool_call": {"name": "code_execution", "args": {"code": "def fib(n):..."}}},

        # Phase 3: Tool Result (System feedback)
        {"text": "", "tool_result": "12586269025"},

        # Phase 4: Status Badges
        {"text": "\n### Security Analysis\n", "type": "content"},
        {"text": "🔴 **BLOCKER**: Critical vulnerability in auth.\n", "type": "content"},
        {"text": "🟡 **WARNING**: Deprecated dependency detected.\n", "type": "content"},
        {"text": "🟢 **SUGESTÃO**: Use `crypto/rand` instead of `math/rand`.\n\n", "type": "content"},

        # Phase 5: Table
        {"text": "| Severity | Count | Status |\n", "type": "content"},
        {"text": "|---|---|---|\n", "type": "content"},
        {"text": "| 🔴 BLOCKER | 6 | Immediate Action |\n", "type": "content"},
        {"text": "| 🟡 WARNING | 41 | High Priority |\n", "type": "content"},
        {"text": "| 🟢 SUGGESTION | 43 | Nice to have |\n\n", "type": "content"},

        # Phase 6: Final Response (Markdown, structured)
        {"text": "The 50th Fibonacci number is **12,586,269,025**.\n\n", "type": "content"},
        {"text": "I calculated this using the native sandbox to ensure precision.", "type": "content"}
    ]

    async def stream(self):
        for chunk in self.SCENARIO:
            # Simulate gRPC jitter (ultra-fast but varied)
            await asyncio.sleep(0.05)
            yield chunk

class AntigravityTestApp(App):
    """Harness to verify rendering without booting the full shell."""
    CSS = """
    Screen { background: #0d1117; }
    #stream-container { padding: 1; }
    .thought { color: #6e7681; text-style: italic; }
    .tool { color: #3fb950; background: #161b22; border: solid #3fb950; }
    """

    def compose(self) -> ComposeResult:
        yield Vertical(id="stream-container")

    async def on_mount(self):
        self.container = self.query_one("#stream-container")
        # Start simulation
        self.run_worker(self.run_simulation())

    async def run_simulation(self):
        mock = MockGeminiStream()
        buffer = ""

        # --- SNAPSHOT 1: IDLE ---
        self.save_screenshot("tests/visual/snapshots/01_idle.svg")

        async for chunk in mock.stream():

            # -- Lógica de Renderização Simplificada (simulando seu ResponseView) --
            if chunk.get("type") == "thought":
                # Render Thinking
                self.container.mount(Static(f"⚡ {chunk['text']}", classes="thought"))

            elif "tool_call" in chunk:
                # Render Tool
                tool = chunk['tool_call']
                panel = Panel(
                    f"Running: {tool['args'].get('code', '')[:20]}...",
                    title=f"🐍 {tool['name']}",
                    style="green"
                )
                self.container.mount(Static(panel))

                # --- SNAPSHOT 2: TOOL EXECUTION ---
                self.save_screenshot("tests/visual/snapshots/02_tool_exec.svg")

            elif "tool_result" in chunk:
                # Render Result
                from rich.text import Text
                self.container.mount(Static(Text(f"└─ Result: {chunk['tool_result']}", style="dim green")))

            elif chunk.get("type") == "content":
                # Render Content
                buffer += chunk['text']
                # In real app, you'd update a Markdown widget here
                self.container.mount(Static(Markdown(chunk['text'])))

        # --- SNAPSHOT 3: FINAL STATE ---
        self.save_screenshot("tests/visual/snapshots/03_final.svg")
        self.exit()

if __name__ == "__main__":
    import os
    os.makedirs("tests/visual/snapshots", exist_ok=True)
    app = AntigravityTestApp()
    app.run()
