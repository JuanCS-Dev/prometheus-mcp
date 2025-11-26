"""Ultra-fast shell with lazy loading and uvloop."""

import asyncio
import sys
import os
from typing import Optional
from pathlib import Path

# Lazy loader - only import this
from .core.lazy_loader import LazyLoader
from .core.shell_core import ShellCore
from .core.uvloop_bootstrap import install_uvloop
from .core.streaming_engine import StreamingEngine

# Bootstrap uvloop
install_uvloop()


class FastShell:
    """Lightning-fast interactive shell."""
    
    def __init__(self):
        # ONLY core - instant
        self.core = ShellCore()
        self.lazy = LazyLoader()
        self.streamer = StreamingEngine()
        
        # Lazy properties
        self._llm = None
        self._tools = None
        
    async def run(self):
        """Run shell with minimal startup."""
        await self.core.show_welcome()  # <50ms
        
        # Background preload (non-blocking)
        # Preload tools as they are most likely to be used
        asyncio.create_task(self.lazy.preload('tools'))
        
        while True:
            try:
                user_input = await self.core.get_input()
                if not user_input:
                    continue
                    
                if user_input.lower() in ('exit', 'quit'):
                    break
                    
                await self.process(user_input)
            except KeyboardInterrupt:
                continue
            except EOFError:
                break
            except Exception as e:
                print(f"\nError: {e}")
                
    async def process(self, user_input: str):
        """Process with lazy loading and intelligence."""
        # Check for system commands first
        if user_input.startswith('/'):
            await self._handle_system_command(user_input)
            return

        # 1. Load Intelligence (RAG/LSP) - Background or On-Demand
        # We load it to get context for the query
        if not hasattr(self, '_intelligence'):
            # Show spinner only if it takes time
            print("\033[2m🧠 Accessing Neural Cortex...\033[0m", end='\r')
            intel_module = await self.lazy.load('intelligence')
            # Instantiate and initialize the plugin
            self._intel_plugin = intel_module.Plugin()
            await self._intel_plugin.initialize()
            self._intelligence = self._intel_plugin.indexer
            # Also load LSP if needed, but let's start with RAG
            
        # 2. Get Context (RAG)
        context = ""
        try:
            # Quick search for relevant code
            results = await self._intelligence.search(user_input, limit=3)
            if results:
                context = "\n".join([f"File: {r.file_path}\nCode:\n{r.content}" for r in results])
                await self.core.print_success(f"Found {len(results)} relevant context snippets")
        except Exception:
            # Fail silently on context to keep it fast
            pass

        # 3. Load LLM
        if self._llm is None:
            print("\033[2m🔌 Connecting to Mainframe...\033[0m", end='\r')
            llm_module = await self.lazy.load('llm')
            self._llm = llm_module.llm_client
            print(" " * 40, end='\r')
            
        # 4. Determine Intent (Simple vs Complex)
        # Heuristic: If input starts with "plan", "refactor", "create project", delegate to DevSquad
        is_complex = any(k in user_input.lower() for k in ['plan', 'refactor', 'create', 'architect', 'squad'])
        
        if is_complex:
            await self._delegate_to_squad(user_input, context)
            return

        # 5. Standard Chat / Tool Loop (ReAct)
        await self._run_react_loop(user_input, context)

    async def _approval_callback(self, plan: dict) -> bool:
        """Callback for human approval."""
        import json
        plan_str = json.dumps(plan, indent=2)
        await self.core.print_code(plan_str, language="json")
        response = await self.core.get_input("Approve plan? (y/n): ")
        return response.lower().startswith('y')

    async def _delegate_to_squad(self, user_input: str, context: str):
        """Delegate complex tasks to DevSquad."""
        await self.core.print_panel(f"[bold yellow]Delegating to DevSquad[/bold yellow]\n{user_input}", title="🤖 Orchestrator")
        
        if not hasattr(self, '_devsquad_plugin'):
            squad_module = await self.lazy.load('devsquad')
            # Instantiate and initialize plugin
            self._devsquad_plugin = squad_module.Plugin()
            await self._devsquad_plugin.initialize()
            self._devsquad = self._devsquad_plugin.squad
            
        # Run Squad
        try:
            result = await self._devsquad.execute_workflow(
                request=user_input,
                context={"raw_context": context},
                approval_callback=self._approval_callback
            )
            
            # Show summary
            summary = self._devsquad.get_phase_summary(result)
            style = "green" if result.status == "completed" else "red"
            await self.core.print_panel(summary, title=f"Mission Result: {result.status.value}", style=style)
            
        except Exception as e:
            await self.core.print_error(f"DevSquad mission failed: {e}")
        
    async def _run_react_loop(self, user_input: str, context: str):
        """Run the ReAct loop for standard queries."""
        max_turns = 5
        current_turn = 0
        messages = [{"role": "user", "content": user_input}]
        
        # Load tools
        if self._tools is None:
            tools_module = await self.lazy.load('tools')
            self._tools = tools_module.tool_registry

        while current_turn < max_turns:
            current_turn += 1
            
            # Prepare System Prompt with Tools & Context
            if current_turn == 1:
                tools_desc = "\n".join([f"- {t.name}: {t.description}" for t in self._tools.get_all().values()])
                system_prompt = f"""You are Neuroshell, an elite coding assistant.
                
CONTEXT:
{context}

TOOLS:
{tools_desc}

INSTRUCTIONS:
- To use a tool, output EXACTLY: TOOL: tool_name(arg1="val", arg2=123)
- If no tool is needed, just answer directly.
- Be concise and professional.
- Use Markdown for formatting.
"""
                messages.insert(0, {"role": "system", "content": system_prompt})

            # Stream Response
            full_response = ""
            generator = self._llm.stream_chat(prompt=user_input if current_turn == 1 else "", context=None) # Context already in system prompt
            
            # We need to capture the output to render markdown properly AFTER streaming
            # OR stream raw text and then render markdown for the final block.
            # For "Beautiful" output, we might want to use a Live display from Rich, 
            # but that's complex with async generator.
            # Let's stick to raw streaming for speed, then render markdown if it's a final answer.
            
            print("", end="", flush=True)
            async for chunk in self.streamer.stream_with_chunking(generator):
                await self.core.output_chunk(chunk)
                full_response += chunk
            await self.core.output_line("") 
            
            # Tool Parsing
            import re
            import ast
            tool_match = re.search(r"TOOL:\s*(\w+)\((.*)\)", full_response, re.DOTALL)
            
            if tool_match:
                tool_name = tool_match.group(1)
                tool_args_str = tool_match.group(2)
                
                await self.core.print_panel(f"Executing: {tool_name}", style="yellow")
                
                try:
                    # Naive Arg Parsing (improved)
                    try:
                        tree = ast.parse(f"func({tool_args_str})")
                        call = tree.body[0].value
                        kwargs = {}
                        for keyword in call.keywords:
                            kwargs[keyword.arg] = ast.literal_eval(keyword.value)
                    except Exception:
                        kwargs = {} # Fallback

                    tool = self._tools.get_tool(tool_name)
                    if tool:
                        result = await tool.execute(**kwargs)
                        output_str = str(result)
                        if len(output_str) > 500:
                            output_str = output_str[:500] + "... (truncated)"
                        
                        await self.core.print_code(output_str, language="text")
                        
                        # Feed back
                        messages.append({"role": "assistant", "content": full_response})
                        messages.append({"role": "user", "content": f"Tool Output: {result}"})
                        continue
                    else:
                        await self.core.print_error(f"Tool {tool_name} not found")
                except Exception as e:
                    await self.core.print_error(f"Execution failed: {e}")
                break
            
            # If no tool, we are done
            break

    async def _handle_system_command(self, cmd: str):
        """Handle system commands with a robust registry."""
        parts = cmd.strip().split()
        command = parts[0].lower()
        args = parts[1:] if len(parts) > 1 else []
        
        # Command Registry
        commands = {
            '/help': self._cmd_help,
            '/debug': self._cmd_debug,
            '/clear': self._cmd_clear,
            '/cls': self._cmd_clear,
            '/exit': self._cmd_exit,
            '/quit': self._cmd_exit,
            '/squad': self._cmd_squad,
            '/mission': self._cmd_squad,
            '/tools': self._cmd_tools,
            '/workflows': self._cmd_workflows,
            '/git': self._cmd_git,
            '/history': self._cmd_history,
            '/mode': self._cmd_mode,
        }
        
        handler = commands.get(command)
        if handler:
            try:
                await handler(args)
            except Exception as e:
                print(f"\033[91mCommand error: {e}\033[0m")
        else:
            print(f"\033[93mUnknown command: {command}\033[0m")
            print("Type /help for available commands.")

    # --- Command Handlers ---

    async def _cmd_help(self, args):
        """Show help message."""
        help_text = """
# 🚀 Neuroshell Fast Commands

## Core
- `/help`: Show this help
- `/clear`: Clear screen
- `/exit`: Exit shell
- `/debug`: Show debug info
- `/history`: Show command history

## Intelligence
- `/squad [task]`: Delegate complex task to DevSquad
- `/mode [fast|pro]`: Switch AI mode (simulated)

## Tools & Workflows
- `/tools`: List available tools
- `/workflows`: List available workflows
- `/git [status|diff]`: Git operations
"""
        await self.core.render_markdown(help_text)

    async def _cmd_clear(self, args):
        """Clear screen."""
        os.system('clear')
        await self.core.show_welcome()

    async def _cmd_exit(self, args):
        """Exit shell."""
        print("Goodbye!")
        sys.exit(0)

    async def _cmd_debug(self, args):
        """Show debug info."""
        print("Debug Info:")
        print(f"Loaded components: {list(self.lazy._cache.keys())}")
        from .core.uvloop_bootstrap import get_loop_info
        print(f"Event Loop: {get_loop_info()}")

    async def _cmd_squad(self, args):
        """Run DevSquad mission."""
        if not args:
            print("Usage: /squad <mission description>")
            return
            
        mission = " ".join(args)
        await self._delegate_to_squad(mission, context="")

    async def _cmd_tools(self, args):
        """List tools."""
        if self._tools is None:
            tools_module = await self.lazy.load('tools')
            self._tools = tools_module.tool_registry
            
        tools = self._tools.get_all().values()
        
        # Render as table using Rich
        from rich.table import Table
        table = Table(title="Available Tools")
        table.add_column("Name", style="cyan")
        table.add_column("Description", style="white")
        
        for t in tools:
            table.add_row(t.name, t.description)
            
        console = self.core._get_console()
        console.print(table)

    async def _cmd_workflows(self, args):
        """List workflows."""
        # Lazy load workflows
        try:
            from .orchestration.workflows import WorkflowLibrary
            library = WorkflowLibrary()
            workflows = library.list_workflows()
            
            from rich.table import Table
            table = Table(title="Available Workflows")
            table.add_column("ID", style="cyan")
            table.add_column("Name", style="green")
            table.add_column("Description", style="white")
            
            for w in workflows:
                table.add_row(w.id, w.name, w.description)
                
            console = self.core._get_console()
            console.print(table)
            console.print("\n[dim]Run a workflow with: /squad run <workflow_id>[/dim]")
            
        except ImportError:
            print("Workflow library not found.")
        except Exception as e:
            print(f"Error listing workflows: {e}")

    async def _cmd_git(self, args):
        """Git operations."""
        if not args:
            print("Usage: /git <status|diff|log>")
            return
            
        subcmd = args[0]
        if subcmd == 'status':
            # Use existing tool if available or direct shell
            os.system('git status')
        elif subcmd == 'diff':
            os.system('git diff')
        elif subcmd == 'log':
            os.system('git log --oneline -n 10')
        else:
            print(f"Unknown git command: {subcmd}")

    async def _cmd_history(self, args):
        """Show history."""
        # Access prompt_toolkit history if possible
        if self.core._session:
            # SECURITY: Read file directly instead of os.system
            history_file = Path.home() / ".qwen_shell_history"
            if history_file.exists():
                print(f"History from {history_file}:")
                try:
                    with open(history_file, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                        for line in lines[-10:]:  # Last 10 lines
                            print(line.rstrip())
                except (IOError, OSError) as e:
                    print(f"Error reading history: {e}")
        else:
            print("History not available yet.")

    async def _cmd_mode(self, args):
        """Switch mode."""
        if not args:
            print("Current mode: FAST (Default)")
            return
        print(f"Switched to {args[0].upper()} mode (Simulated)")


async def async_main():
    shell = FastShell()
    await shell.run()


def main():
    """Synchronous entry point for setuptools."""
    try:
        asyncio.run(async_main())
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"\nFatal Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
