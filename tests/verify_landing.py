import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from rich.console import Console
from qwen_dev_cli.tui.landing import create_landing_screen

def verify():
    console = Console()
    console.print("[bold blue]Testing Landing Screen Rendering (2025 Edition)...[/bold blue]")
    
    try:
        landing = create_landing_screen(console)
        console.print(landing.render())
        console.print("\n[bold green]✅ Landing Screen Rendered Successfully![/bold green]")
    except Exception as e:
        console.print(f"\n[bold red]❌ Error rendering landing screen:[/bold red] {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    verify()
