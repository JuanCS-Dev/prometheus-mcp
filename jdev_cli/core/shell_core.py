"""Minimal shell core - ultra-fast prompt loop."""

from pathlib import Path


class ShellCore:
    """Core shell functionality - minimal and fast."""

    def __init__(self):
        self.cwd = Path.cwd()
        self._session = None  # Lazy load prompt_toolkit

    async def show_welcome(self):
        """Show welcome - ultra fast, no dependencies."""
        # Simple print - NO rich/TUI overhead for instant feedback
        # We use ANSI escape codes for basic coloring without heavy libs
        cyan = "\033[96m"
        green = "\033[92m"
        reset = "\033[0m"
        dim = "\033[2m"

        print(f"\n{cyan}🚀 NEUROSHELL v2.0{reset} - {green}ULTRA FAST MODE{reset}")
        print(f"{dim}📁 {self.cwd}{reset}")
        print(f"{dim}Type 'help' for commands{reset}\n")

    async def get_input(self) -> str:
        """Get user input with lazy session loading."""
        if self._session is None:
            # Lazy import apenas quando necessário
            # This saves ~200-400ms on startup
            try:
                from prompt_toolkit import PromptSession
                from prompt_toolkit.history import FileHistory

                history_file = Path.home() / ".qwen_shell_history"
                self._session = PromptSession(history=FileHistory(str(history_file)))
            except ImportError:
                # Fallback if prompt_toolkit not installed (should not happen in dev env)
                return input("❯ ")

        return await self._session.prompt_async("❯ ")

    async def output_chunk(self, chunk: str):
        """Output chunk - streaming mode."""
        print(chunk, end='', flush=True)

    async def output_line(self, line: str):
        """Output full line."""
        print(line)

    def _get_console(self):
        """Lazy load rich console."""
        if not hasattr(self, '_console'):
            from rich.console import Console
            from rich.theme import Theme
            # Premium theme
            theme = Theme({
                "info": "cyan",
                "warning": "yellow",
                "error": "bold red",
                "success": "bold green",
                "code": "bold white on #1e1e1e",
                "panel.border": "blue",
            })
            self._console = Console(theme=theme)
        return self._console

    async def render_markdown(self, text: str):
        """Render markdown content using Rich."""
        try:
            from rich.markdown import Markdown
            console = self._get_console()
            console.print(Markdown(text))
        except ImportError:
            print(text)

    async def print_panel(self, content: str, title: str = None, style: str = "blue"):
        """Print a styled panel."""
        try:
            from rich.panel import Panel
            console = self._get_console()
            console.print(Panel(content, title=title, border_style=style))
        except ImportError:
            print(f"\n[{title}]\n{content}\n")

    async def print_code(self, code: str, language: str = "python"):
        """Print syntax highlighted code."""
        try:
            from rich.syntax import Syntax
            console = self._get_console()
            syntax = Syntax(code, language, theme="monokai", line_numbers=True)
            console.print(syntax)
        except ImportError:
            print(f"```{language}\n{code}\n```")

    async def print_success(self, message: str):
        """Print success message."""
        try:
            console = self._get_console()
            console.print(f"✅ {message}", style="success")
        except ImportError:
            print(f"SUCCESS: {message}")

    async def print_error(self, message: str):
        """Print error message."""
        try:
            console = self._get_console()
            console.print(f"❌ {message}", style="error")
        except ImportError:
            print(f"ERROR: {message}")
