import asyncio
import sys
from pathlib import Path
from prompt_toolkit import PromptSession
from prompt_toolkit.styles import Style
from prompt_toolkit.history import FileHistory
from rich.console import Console
from rich.markdown import Markdown
from dotenv import load_dotenv

from jdev_cli.shell.executor import ShellExecutor
from jdev_cli.core.providers.gemini import GeminiProvider

# Load .env
env_path = Path(__file__).parent.parent.parent / ".env"
if env_path.exists():
    load_dotenv(env_path)
    print(f"✓ Loaded .env from {env_path}")

# Tema estilo Cyberpunk/Dark
style = Style.from_dict({
    'prompt': 'ansicyan bold',
    'input': '#00ff00',
})

class ShellREPL:
    def __init__(self):
        self.console = Console()
        self.session = PromptSession(history=FileHistory('.qwen_history'))

        # Inicializa componentes
        try:
            # Use o provider corrigido diretamente para garantir funcionamento
            self.llm = GeminiProvider()
            self.executor = ShellExecutor(self.llm, self.console)
        except Exception as e:
            self.console.print(f"[bold red]Critical Startup Error:[/bold red] {e}")
            sys.exit(1)

    async def start(self):
        """Loop principal do Shell."""
        self.console.clear()
        self.console.print(Markdown("# 🚀 QWEN-DEV-CLI v2.0 (Reborn)"))
        self.console.print("[dim]Architecture: Modular | LLM: Gemini-Flash Fixed | Mode: Pragmatic[/dim]\n")

        while True:
            try:
                # Input assíncrono que não bloqueia o event loop principal
                user_input = await self.session.prompt_async(
                    "╭─(dev) ❯ ",
                    style=style
                )

                if not user_input.strip():
                    continue

                if user_input.lower() in ["exit", "quit", "/q"]:
                    self.console.print("[yellow]Shutting down...[/yellow]")
                    break

                if user_input.lower() == "clear":
                    self.console.clear()
                    continue

                # Delega para o executor (Cérebro)
                await self.executor.execute(user_input)
                self.console.print("╰─✔\n", style="dim green")

            except KeyboardInterrupt:
                continue
            except EOFError:
                break
            except Exception as e:
                self.console.print(f"[bold red]Runtime Error:[/bold red] {e}")

def main():
    repl = ShellREPL()
    try:
        asyncio.run(repl.start())
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    main()
