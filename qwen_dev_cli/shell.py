"""Interactive shell with tool-based architecture."""

import asyncio
import os
import json
from typing import Optional, Dict, Any
from pathlib import Path

from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table

from .core.context import ContextBuilder

# Import LLM client (using existing implementation)
try:
    from .core.llm import llm_client as default_llm_client
except ImportError:
    default_llm_client = None
from .tools.base import ToolRegistry
from .tools.file_ops import (
    ReadFileTool, WriteFileTool, EditFileTool,
    ListDirectoryTool, DeleteFileTool
)
from .tools.file_mgmt import (
    MoveFileTool, CopyFileTool, CreateDirectoryTool,
    ReadMultipleFilesTool, InsertLinesTool
)
from .tools.search import SearchFilesTool, GetDirectoryTreeTool
from .tools.exec import BashCommandTool
from .tools.git_ops import GitStatusTool, GitDiffTool
from .tools.context import GetContextTool, SaveSessionTool, RestoreBackupTool
from .tools.terminal import (
    CdTool, LsTool, PwdTool, MkdirTool, RmTool,
    CpTool, MvTool, TouchTool, CatTool
)


class SessionContext:
    """Persistent context across shell session."""
    
    def __init__(self):
        self.cwd = os.getcwd()
        self.conversation = []
        self.modified_files = set()
        self.read_files = set()
        self.tool_calls = []
    
    def track_tool_call(self, tool_name: str, args: Dict[str, Any], result: Any):
        """Track tool usage."""
        self.tool_calls.append({
            "tool": tool_name,
            "args": args,
            "result": result,
            "success": getattr(result, 'success', True)
        })
        
        # Track file operations
        if tool_name == "write_file" or tool_name == "edit_file":
            self.modified_files.add(args.get("path", ""))
        elif tool_name == "read_file":
            self.read_files.add(args.get("path", ""))


class InteractiveShell:
    """Tool-based interactive shell (Claude Code-level)."""
    
    def __init__(self, llm_client=None):
        self.console = Console()
        self.llm = llm_client or default_llm_client
        self.context = SessionContext()
        self.context_builder = ContextBuilder()
        
        # Setup prompt session
        history_file = Path.home() / ".qwen_shell_history"
        self.session = PromptSession(
            history=FileHistory(str(history_file)),
            auto_suggest=AutoSuggestFromHistory(),
        )
        
        # Initialize tool registry
        self.registry = ToolRegistry()
        self._register_tools()
    
    def _register_tools(self):
        """Register all available tools."""
        tools = [
            # File reading (4 tools)
            ReadFileTool(),
            ReadMultipleFilesTool(),
            ListDirectoryTool(),
            
            # File writing (4 tools)
            WriteFileTool(),
            EditFileTool(),
            InsertLinesTool(),
            DeleteFileTool(),
            
            # File management (3 tools)
            MoveFileTool(),
            CopyFileTool(),
            CreateDirectoryTool(),
            
            # Search (2 tools)
            SearchFilesTool(),
            GetDirectoryTreeTool(),
            
            # Execution (1 tool)
            BashCommandTool(),
            
            # Git (2 tools)
            GitStatusTool(),
            GitDiffTool(),
            
            # Context (3 tools)
            GetContextTool(),
            SaveSessionTool(),
            RestoreBackupTool(),
            
            # Terminal commands (9 tools)
            CdTool(),
            LsTool(),
            PwdTool(),
            MkdirTool(),
            RmTool(),
            CpTool(),
            MvTool(),
            TouchTool(),
            CatTool(),
        ]
        
        for tool in tools:
            self.registry.register(tool)
        
        self.console.print(f"[dim]Loaded {len(tools)} tools[/dim]")
    
    def _show_welcome(self):
        """Show welcome message."""
        welcome = Panel(
            "[bold cyan]QWEN-DEV-CLI Interactive Shell v1.0[/bold cyan]\n\n"
            f"Tools available: {len(self.registry.get_all())}\n"
            f"Working directory: {self.context.cwd}\n\n"
            "Type natural language commands or /help for system commands",
            title="🚀 AI-Powered Code Shell",
            border_style="cyan"
        )
        self.console.print(welcome)
    
    async def _process_tool_calls(self, user_input: str) -> str:
        """Process user input and execute tools via LLM."""
        try:
            # Build prompt for LLM
            tool_schemas = self.registry.get_schemas()
            
            # Group tools by category for better understanding
            tool_list = []
            for schema in tool_schemas:
                tool_list.append(f"- {schema['name']}: {schema['description']}")
            
            system_prompt = f"""You are an AI code assistant with access to tools for file operations, git, search, and execution.

Available tools ({len(tool_schemas)} total):
{chr(10).join(tool_list)}

Current context:
- Working directory: {self.context.cwd}
- Modified files: {list(self.context.modified_files) if self.context.modified_files else 'none'}
- Read files: {list(self.context.read_files) if self.context.read_files else 'none'}

INSTRUCTIONS:
1. Analyze the user's request
2. If it requires tools, respond ONLY with a JSON array of tool calls
3. If no tools needed, respond with helpful text

Tool call format:
[
  {{"tool": "tool_name", "args": {{"param": "value"}}}}
]

Examples:
User: "read api.py"
Response: [{{"tool": "readfile", "args": {{"path": "api.py"}}}}]

User: "show git status"
Response: [{{"tool": "gitstatus", "args": {{}}}}]

User: "search for TODO in python files"
Response: [{{"tool": "searchfiles", "args": {{"pattern": "TODO", "file_pattern": "*.py"}}}}]

User: "what time is it?"
Response: I don't have a tool to check the current time, but I can help you with code-related tasks."""
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_input}
            ]
            
            # Get LLM response
            response = await self.llm.generate_async(
                messages=messages,
                temperature=0.1,
                max_tokens=2000
            )
            
            # Parse response
            response_text = response.get("content", "")
            
            # Try to parse as tool calls
            try:
                # Look for JSON array in response
                if '[' in response_text and ']' in response_text:
                    start = response_text.index('[')
                    end = response_text.rindex(']') + 1
                    json_str = response_text[start:end]
                    tool_calls = json.loads(json_str)
                    
                    if isinstance(tool_calls, list) and tool_calls:
                        return await self._execute_tool_calls(tool_calls)
            except (json.JSONDecodeError, ValueError):
                pass
            
            # If not tool calls, return as regular response
            return response_text
            
        except Exception as e:
            return f"Error: {str(e)}"
    
    async def _execute_tool_calls(self, tool_calls: list[Dict[str, Any]]) -> str:
        """Execute a sequence of tool calls."""
        results = []
        
        for call in tool_calls:
            tool_name = call.get("tool", "")
            args = call.get("args", {})
            
            tool = self.registry.get(tool_name)
            if not tool:
                results.append(f"❌ Unknown tool: {tool_name}")
                continue
            
            # Show what we're doing
            args_str = ', '.join(f'{k}={v}' for k, v in args.items())
            self.console.print(f"[dim]→ {tool_name}({args_str})[/dim]")
            
            # Add session context for tools that need it
            if tool_name in ['getcontext', 'savesession']:
                args['session_context'] = self.context
            
            # Execute tool
            result = await tool.execute(**args)
            
            # Track tool call
            self.context.track_tool_call(tool_name, args, result)
            
            # Format result
            if result.success:
                if tool_name == "read_file":
                    # Show file content with syntax highlighting
                    lang = result.metadata.get("language", "text")
                    syntax = Syntax(str(result.data), lang, theme="monokai", line_numbers=True)
                    self.console.print(syntax)
                    results.append(f"✓ Read {result.metadata['path']} ({result.metadata['lines']} lines)")
                
                elif tool_name in ["write_file", "edit_file"]:
                    results.append(f"✓ {result.data}")
                    if result.metadata.get("backup"):
                        results.append(f"  Backup: {result.metadata['backup']}")
                
                elif tool_name == "search_files":
                    # Show search results as table
                    if result.data:
                        table = Table(title=f"Search Results: '{args['pattern']}'")
                        table.add_column("File", style="cyan")
                        table.add_column("Line", style="yellow", justify="right")
                        table.add_column("Text", style="white")
                        
                        for match in result.data[:10]:  # Show first 10
                            table.add_row(
                                match["file"],
                                str(match["line"]),
                                match["text"][:80]
                            )
                        
                        self.console.print(table)
                        results.append(f"✓ Found {result.metadata['count']} matches")
                    else:
                        results.append("No matches found")
                
                elif tool_name == "bash_command":
                    data = result.data
                    if data.get("stdout"):
                        self.console.print("[dim]stdout:[/dim]")
                        self.console.print(data["stdout"])
                    if data.get("stderr"):
                        self.console.print("[yellow]stderr:[/yellow]")
                        self.console.print(data["stderr"])
                    results.append(f"✓ Exit code: {data['exit_code']}")
                
                elif tool_name == "git_status":
                    data = result.data
                    status_text = f"Branch: {data['branch']}\n"
                    if data['modified']:
                        status_text += f"Modified: {', '.join(data['modified'])}\n"
                    if data['untracked']:
                        status_text += f"Untracked: {', '.join(data['untracked'])}\n"
                    if data['staged']:
                        status_text += f"Staged: {', '.join(data['staged'])}\n"
                    self.console.print(Panel(status_text, title="Git Status", border_style="green"))
                    results.append("✓ Git status retrieved")
                
                elif tool_name == "git_diff":
                    if result.data:
                        self.console.print(Syntax(result.data, "diff", theme="monokai"))
                        results.append("✓ Diff shown")
                    else:
                        results.append("No changes")
                
                elif tool_name == "get_directory_tree":
                    self.console.print(Panel(result.data, title="Directory Tree", border_style="blue"))
                    results.append("✓ Tree shown")
                
                elif tool_name == "list_directory":
                    data = result.data
                    self.console.print(f"[cyan]Directories ({len(data['directories'])}):[/cyan]")
                    for d in data['directories'][:10]:
                        self.console.print(f"  📁 {d['name']}")
                    self.console.print(f"\n[cyan]Files ({len(data['files'])}):[/cyan]")
                    for f in data['files'][:10]:
                        self.console.print(f"  📄 {f['name']} ({f['size']} bytes)")
                    results.append(f"✓ Listed {result.metadata['file_count']} files, {result.metadata['dir_count']} directories")
                
                # Terminal commands
                elif tool_name == "ls":
                    items = result.data
                    for item in items:
                        icon = "📁" if item['type'] == 'dir' else "📄"
                        name = f"[bold cyan]{item['name']}[/bold cyan]" if item['type'] == 'dir' else item['name']
                        if result.metadata.get('long_format'):
                            self.console.print(f"{icon} {name} ({item.get('size', 0)} bytes)")
                        else:
                            self.console.print(f"{icon} {name}")
                    results.append(f"✓ {result.metadata['count']} items")
                
                elif tool_name == "pwd":
                    self.console.print(f"[bold green]{result.data}[/bold green]")
                    results.append("✓ Current directory shown")
                
                elif tool_name == "cd":
                    self.console.print(f"[green]→ {result.metadata['new_cwd']}[/green]")
                    results.append(f"✓ {result.data}")
                
                elif tool_name == "cat":
                    from rich.syntax import Syntax
                    # Try to detect language from file extension
                    path = result.metadata.get('path', '')
                    lang = Path(path).suffix.lstrip('.') or 'text'
                    syntax = Syntax(result.data, lang, theme="monokai", line_numbers=True)
                    self.console.print(syntax)
                    results.append(f"✓ Displayed {result.metadata['lines']} lines")
                
                else:
                    results.append(f"✓ {result.data}")
            else:
                results.append(f"❌ {result.error}")
        
        return "\n".join(results)
    
    async def _handle_system_command(self, cmd: str) -> tuple[bool, Optional[str]]:
        """Handle system commands (/help, /exit, etc.)."""
        cmd = cmd.strip()
        
        if cmd in ["/exit", "/quit"]:
            self.console.print("[yellow]Goodbye! 👋[/yellow]")
            return True, None
        
        elif cmd == "/help":
            help_text = """
[bold]System Commands:[/bold]
  /help     - Show this help
  /exit     - Exit shell
  /tools    - List available tools
  /context  - Show session context
  /clear    - Clear screen

[bold]Natural Language Commands:[/bold]
  Just type what you want to do, e.g.:
  - "read api.py"
  - "search for UserModel in python files"
  - "show git status"
  - "list files in current directory"
"""
            self.console.print(Panel(help_text, title="Help", border_style="yellow"))
            return False, None
        
        elif cmd == "/tools":
            tools = self.registry.get_all()
            table = Table(title="Available Tools")
            table.add_column("Tool", style="cyan")
            table.add_column("Category", style="yellow")
            table.add_column("Description", style="white")
            
            for tool_name, tool in tools.items():
                table.add_row(tool_name, tool.category.value, tool.description)
            
            self.console.print(table)
            return False, None
        
        elif cmd == "/context":
            context_text = f"""
CWD: {self.context.cwd}
Modified files: {len(self.context.modified_files)}
Read files: {len(self.context.read_files)}
Tool calls: {len(self.context.tool_calls)}
"""
            self.console.print(Panel(context_text, title="Session Context", border_style="blue"))
            return False, None
        
        elif cmd == "/clear":
            self.console.clear()
            return False, None
        
        else:
            return False, f"Unknown command: {cmd}"
    
    async def run(self):
        """Main REPL loop."""
        self._show_welcome()
        
        while True:
            try:
                # Get user input
                user_input = await self.session.prompt_async("┃ > ")
                
                if not user_input.strip():
                    continue
                
                # Handle system commands
                if user_input.startswith("/"):
                    should_exit, message = await self._handle_system_command(user_input)
                    if message:
                        self.console.print(f"[red]{message}[/red]")
                    if should_exit:
                        break
                    continue
                
                # Process with tools
                response = await self._process_tool_calls(user_input)
                
                if response:
                    # Show response
                    if response.startswith("✓") or response.startswith("❌"):
                        # Tool execution result
                        self.console.print(response)
                    else:
                        # Regular LLM response
                        md = Markdown(response)
                        self.console.print(md)
                
            except KeyboardInterrupt:
                continue
            except EOFError:
                break
            except Exception as e:
                self.console.print(f"[red]Error: {str(e)}[/red]")


async def main():
    """Entry point for shell."""
    shell = InteractiveShell()
    await shell.run()


if __name__ == "__main__":
    asyncio.run(main())
