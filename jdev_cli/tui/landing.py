"""
Neuroshell Landing Screen - 2025 Cyberpunk Edition
High-fidelity TUI with neon aesthetics and system integration.
"""

import time
import psutil
import os
import random
from typing import Optional
from datetime import datetime

from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.align import Align
from rich.box import ROUNDED, DOUBLE, SIMPLE

try:
    import pyfiglet
except ImportError:
    pyfiglet = None

# 2025 Neon Palette
NEON_CYAN = "#00ffff"
NEON_GREEN = "#00ff00"
NEON_MAGENTA = "#ff00ff"
NEON_YELLOW = "#ffff00"
DARK_BG = "#0a0a0a"

class LandingScreen:
    """
    Premium landing screen for Neuroshell (2025 Edition).
    """

    def __init__(self, console: Optional[Console] = None):
        self.console = console or Console()
        self.start_time = time.time()

    def _get_banner(self) -> Panel:
        """Render the Neuroshell ASCII banner using pyfiglet."""
        if pyfiglet:
            # Fonts: 'slant', 'small', 'ansi_shadow', 'electronic'
            try:
                ascii_art = pyfiglet.figlet_format("NEUROSHELL", font="slant")
            except (pyfiglet.FontNotFound, Exception):
                ascii_art = pyfiglet.figlet_format("NEUROSHELL")
        else:
            ascii_art = "NEUROSHELL (pyfiglet not found)"

        # Create a gradient effect (simulated with rich styles)
        text = Text(ascii_art, style=f"bold {NEON_CYAN}")

        # Subtitle with "glitch" effect
        subtitle = Text()
        subtitle.append(" v2.5 PRO ", style=f"bold black on {NEON_GREEN}")
        subtitle.append(" • ", style="dim white")
        subtitle.append("NEURAL INTERFACE ACTIVE", style=f"bold {NEON_MAGENTA} blink")

        return Panel(
            Align.center(text),
            box=DOUBLE,
            border_style=f"{NEON_CYAN}",
            padding=(1, 2),
            subtitle=subtitle,
            subtitle_align="right",
            title="[bold white]SYSTEM INITIALIZED[/bold white]",
            title_align="left"
        )

    def _get_system_hud(self) -> Panel:
        """Render system vitals in a HUD style."""
        cpu = psutil.cpu_percent()
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage('/')

        # HUD Grid
        table = Table.grid(padding=(0, 2), expand=True)
        table.add_column(style=f"bold {NEON_GREEN}")
        table.add_column(justify="right", style="white")
        table.add_column(style="dim white", width=10) # Bar column

        # CPU
        cpu_bar = "█" * int(cpu / 10) + "░" * (10 - int(cpu / 10))
        table.add_row("CPU CORE", f"{cpu}%", f"[{cpu_bar}]")

        # MEMORY
        mem_pct = mem.percent
        mem_bar = "█" * int(mem_pct / 10) + "░" * (10 - int(mem_pct / 10))
        table.add_row("NEURAL MEM", f"{mem_pct}%", f"[{mem_bar}]")

        # DISK
        disk_pct = disk.percent
        disk_bar = "█" * int(disk_pct / 10) + "░" * (10 - int(disk_pct / 10))
        table.add_row("STORAGE", f"{disk_pct}%", f"[{disk_bar}]")

        return Panel(
            table,
            title=f"[bold {NEON_GREEN}]SYSTEM VITALS[/bold {NEON_GREEN}]",
            border_style=f"{NEON_GREEN}",
            box=ROUNDED
        )

    def _get_quick_actions(self) -> Panel:
        """Render quick actions menu."""
        table = Table.grid(padding=(0, 1), expand=True)
        table.add_column(justify="center", style=f"bold black on {NEON_YELLOW}", width=3)
        table.add_column(style="white")

        actions = [
            ("N", "New Session"),
            ("R", "Resume Last"),
            ("L", "Load Session"),
            ("C", "Config"),
            ("Q", "Quit"),
        ]

        for key, desc in actions:
            table.add_row(f"{key}", f" {desc}")
            table.add_row("", "") # Spacer

        return Panel(
            table,
            title=f"[bold {NEON_YELLOW}]QUICK ACTIONS[/bold {NEON_YELLOW}]",
            border_style=f"{NEON_YELLOW}",
            box=ROUNDED
        )

    def _get_recent_sessions(self) -> Panel:
        """Render recent sessions list."""
        try:
            from ..session import SessionManager
            manager = SessionManager()
            sessions = manager.list_sessions(limit=3)
        except (ImportError, AttributeError, Exception):
            sessions = []

        if not sessions:
            content = Align.center(Text("NO RECENT LINKS DETECTED", style="dim italic white"))
        else:
            table = Table.grid(padding=(0, 1), expand=True)
            table.add_column(style=f"{NEON_MAGENTA}")
            table.add_column(justify="right", style="dim white")

            for s in sessions:
                dt = datetime.fromisoformat(s['last_activity'])
                time_str = dt.strftime("%H:%M")
                cwd_name = os.path.basename(s['cwd']) or "root"

                table.add_row(f"⚡ {cwd_name}", time_str)
                table.add_row(f"   [dim]{s['id'][:8]}...[/dim]", "")

            content = table

        return Panel(
            content,
            title=f"[bold {NEON_MAGENTA}]RECENT LINKS[/bold {NEON_MAGENTA}]",
            border_style=f"{NEON_MAGENTA}",
            box=ROUNDED
        )

    def _get_footer(self) -> Panel:
        """Render footer with tips/status."""
        tips = [
            "TIP: Use /help for a list of neural commands",
            "TIP: 'explain <file>' to analyze code structure",
            "TIP: Ctrl+D to disconnect safely",
            "STATUS: AI Model Connected",
            "STATUS: MCP Servers Online",
            "TIP: Use natural language for complex tasks"
        ]
        tip = random.choice(tips)

        # 2025 style: minimal, tech-focused
        return Panel(
            Align.center(Text(tip, style=f"italic {NEON_CYAN}")),
            box=SIMPLE,
            border_style="dim white"
        )

    def render(self) -> Layout:
        """Render the full landing screen layout."""
        layout = Layout()

        # Split into Header, Main, Footer
        layout.split_column(
            Layout(name="header", size=10),
            Layout(name="main", ratio=1),
            Layout(name="footer", size=3)
        )

        # Header
        layout["header"].update(self._get_banner())

        # Main Grid: 3 Columns
        layout["main"].split_row(
            Layout(name="left"),
            Layout(name="center"),
            Layout(name="right")
        )

        # Left: System Vitals
        layout["left"].update(self._get_system_hud())

        # Center: Quick Actions
        layout["center"].update(self._get_quick_actions())

        # Right: Recent Sessions
        layout["right"].update(self._get_recent_sessions())

        # Footer
        layout["footer"].update(self._get_footer())

        return layout

def create_landing_screen(console: Optional[Console] = None) -> LandingScreen:
    return LandingScreen(console)

def show_landing_screen(console: Console, duration: float = 2.0):
    """Show landing screen for specified duration"""
    screen = LandingScreen(console)
    console.clear()
    console.print(screen.render())
    time.sleep(duration)
