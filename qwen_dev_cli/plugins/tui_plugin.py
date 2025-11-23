"""Lazy loaded TUI plugin."""

class Plugin:
    """TUI plugin for Rich console and visualizations."""
    
    def __init__(self):
        self.console = None
        self.theme = None
        
    async def initialize(self) -> None:
        """Initialize Rich console."""
        from rich.console import Console
        from qwen_dev_cli.tui.styles import get_rich_theme
        
        self.theme = get_rich_theme()
        self.console = Console(theme=self.theme)
        
    async def shutdown(self) -> None:
        pass
        
    def print(self, *args, **kwargs):
        """Proxy to console.print."""
        if self.console:
            self.console.print(*args, **kwargs)
