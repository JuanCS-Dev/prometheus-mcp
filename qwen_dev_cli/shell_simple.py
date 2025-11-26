#!/usr/bin/env python3
"""
SIMPLE WORKING SHELL - No bullshit, just works
Inspired by max-code/claude-code
"""
import asyncio
import os
import shlex
import subprocess
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory

from .core.llm import LLMClient
from .core.input_validator import validate_command


class SimpleShell:
    """Minimal working shell - no complex features, just input → LLM → execute"""
    
    def __init__(self):
        self.console = Console()
        self.llm = LLMClient()
        self.cwd = os.getcwd()
        
        # Simple prompt session
        history_file = Path.home() / ".qwen_history"
        self.session = PromptSession(history=FileHistory(str(history_file)))
        
    def show_welcome(self):
        """Simple welcome banner"""
        self.console.print()
        self.console.print(Panel(
            "[bold cyan]QWEN-DEV-CLI[/bold cyan]\n"
            "[dim]Type your request or 'quit' to exit[/dim]",
            border_style="cyan"
        ))
        self.console.print()
        
    async def get_llm_response(self, user_input: str) -> str:
        """Get response from LLM - use existing generate method"""
        try:
            # Use the ACTUAL method from LLMClient
            response = await self.llm.generate(
                prompt=user_input,
                context=f"Current directory: {self.cwd}",
                max_tokens=500
            )
            return response.strip()
        except Exception as e:
            return f"LLM Error: {e}"
    
    async def execute_command(self, command: str):
        """Execute a shell command with security validation."""
        # SECURITY: Validate command before execution
        validation = validate_command(command, allow_shell=False)
        if not validation.is_valid:
            self.console.print(f"[red]Security: Command blocked - {', '.join(validation.errors)}[/red]")
            return

        if validation.warnings:
            for warning in validation.warnings:
                self.console.print(f"[yellow]⚠ {warning}[/yellow]")

        try:
            # SECURITY: Use shlex.split instead of shell=True
            args = shlex.split(command)
            result = subprocess.run(
                args,
                shell=False,  # HARDENED: Never use shell=True
                cwd=self.cwd,
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.stdout:
                self.console.print(result.stdout)
            if result.stderr:
                self.console.print(f"[red]{result.stderr}[/red]")

        except subprocess.TimeoutExpired:
            self.console.print("[red]Command timed out[/red]")
        except ValueError as e:
            self.console.print(f"[red]Invalid command syntax: {e}[/red]")
        except FileNotFoundError:
            self.console.print(f"[red]Command not found: {command.split()[0]}[/red]")
        except Exception as e:
            self.console.print(f"[red]Error: {e}[/red]")
    
    async def run(self):
        """Main loop - SIMPLE"""
        self.show_welcome()
        
        while True:
            try:
                # Get input
                user_input = await self.session.prompt_async(f"{Path(self.cwd).name} > ")
                
                if not user_input.strip():
                    continue
                    
                # Handle quit
                if user_input.lower() in ['quit', 'exit', 'q']:
                    self.console.print("[cyan]Goodbye![/cyan]")
                    break
                
                # Handle cd
                if user_input.startswith('cd '):
                    new_dir = user_input[3:].strip()
                    try:
                        os.chdir(new_dir)
                        self.cwd = os.getcwd()
                        self.console.print(f"[dim]→ {self.cwd}[/dim]")
                    except Exception as e:
                        self.console.print(f"[red]cd failed: {e}[/red]")
                    continue
                
                # If it looks like a shell command, just execute it
                if user_input.startswith(('ls', 'cat', 'grep', 'find', 'git', 'python', 'npm', 'docker')):
                    await self.execute_command(user_input)
                    continue
                
                # Otherwise, ask LLM
                self.console.print("[dim]💭 Thinking...[/dim]")
                response = await self.get_llm_response(user_input)
                
                self.console.print()
                self.console.print(f"[cyan]{response}[/cyan]")
                self.console.print()
                
                # Ask if user wants to execute
                execute = await self.session.prompt_async("Execute? [Y/n] ")
                if execute.lower() in ['', 'y', 'yes']:
                    await self.execute_command(response)
                    
            except KeyboardInterrupt:
                self.console.print()
                continue
            except EOFError:
                break
            except Exception as e:
                self.console.print(f"[red]Error: {e}[/red]")


def main():
    """Entry point"""
    shell = SimpleShell()
    asyncio.run(shell.run())


if __name__ == "__main__":
    main()
