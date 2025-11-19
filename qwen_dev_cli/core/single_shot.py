"""Single-shot execution for non-interactive mode."""

import os
import asyncio
from pathlib import Path
from typing import Dict, Any, List
from rich.console import Console

from .llm import llm_client
from .parser import ResponseParser
from .context import context_builder
from ..integration.shell_bridge import ShellBridge
from ..integration.safety import SafetyValidator

console = Console()


async def execute_single_shot(
    message: str,
    cwd: str = None,
    include_context: bool = True
) -> Dict[str, Any]:
    """
    Execute single message and return result.
    
    Args:
        message: User message/command
        cwd: Working directory (default: current)
        include_context: Include project context in prompt
    
    Returns:
        Dict with:
            - success: bool
            - output: str (formatted result)
            - actions_taken: List[str] (tool names used)
            - errors: List[str] (any errors encountered)
            - raw_response: str (LLM raw response)
    """
    # Set working directory
    if cwd:
        original_cwd = os.getcwd()
        os.chdir(cwd)
    else:
        cwd = os.getcwd()
    
    try:
        # Initialize components
        parser = ResponseParser()
        bridge = ShellBridge()
        safety = SafetyValidator(allowed_paths=[Path(cwd)])
        
        # Build context if requested
        prompt = message
        if include_context:
            context = _build_rich_context(cwd)
            if context:
                prompt = f"{context}\n\nUser request: {message}"
        
        # Generate response from LLM
        console.print("[dim]🤖 Generating response...[/dim]")
        raw_response = await llm_client.generate(prompt)
        
        # Parse response to extract actions
        console.print("[dim]📋 Parsing actions...[/dim]")
        parse_result = parser.parse(raw_response)
        actions = parse_result.tool_calls if parse_result and parse_result.success else []
        
        if not actions:
            # No structured actions found, return raw text
            return {
                'success': True,
                'output': raw_response,
                'actions_taken': [],
                'errors': [],
                'raw_response': raw_response
            }
        
        # Execute actions through bridge
        console.print(f"[dim]⚡ Executing {len(actions)} action(s)...[/dim]")
        results = []
        errors = []
        
        try:
            # Execute all actions through bridge
            execution_results = await bridge.execute_tool_calls(actions)
            
            for result in execution_results:
                results.append(result)
                
                if not result.get('success', False):
                    error_msg = result.get('error', 'Unknown error')
                    errors.append(error_msg)
                    
        except Exception as e:
            errors.append(f"Execution error: {str(e)}")
        
        # Format output
        output_lines = []
        
        # Add LLM explanation if present
        if raw_response and not raw_response.strip().startswith('['):
            output_lines.append("💬 AI Response:")
            output_lines.append(raw_response.split('[')[0].strip())
            output_lines.append("")
        
        # Add action results
        if results:
            output_lines.append("📊 Actions Executed:")
            for i, result in enumerate(results, 1):
                tool_name = result.get('tool', 'unknown')
                success = result.get('success', False)
                status = "✓" if success else "✗"
                output_lines.append(f"  {status} {tool_name}")
                
                if result.get('output'):
                    output_lines.append(f"     Output: {result['output'][:200]}")
            output_lines.append("")
        
        # Add errors if any
        if errors:
            output_lines.append("⚠️  Errors:")
            for error in errors:
                output_lines.append(f"  • {error}")
            output_lines.append("")
        
        formatted_output = "\n".join(output_lines)
        
        return {
            'success': len(errors) == 0,
            'output': formatted_output,
            'actions_taken': [r.get('tool', 'unknown') for r in results],
            'errors': errors,
            'raw_response': raw_response
        }
        
    finally:
        # Restore working directory
        if cwd and 'original_cwd' in locals():
            os.chdir(original_cwd)


def _build_rich_context(cwd: str) -> str:
    """Build rich context about current project."""
    context_parts = []
    
    # Working directory
    context_parts.append(f"Working Directory: {cwd}")
    
    # Git info
    git_dir = Path(cwd) / ".git"
    if git_dir.exists():
        try:
            import subprocess
            branch = subprocess.check_output(
                ["git", "branch", "--show-current"],
                cwd=cwd,
                stderr=subprocess.DEVNULL
            ).decode().strip()
            
            status = subprocess.check_output(
                ["git", "status", "--short"],
                cwd=cwd,
                stderr=subprocess.DEVNULL
            ).decode().strip()
            
            context_parts.append(f"Git Branch: {branch}")
            if status:
                context_parts.append(f"Git Status: {len(status.splitlines())} modified files")
        except:
            pass
    
    # Project files
    try:
        files = list(Path(cwd).glob("*"))
        file_names = [f.name for f in files if f.is_file()][:10]
        dir_names = [f.name for f in files if f.is_dir() and not f.name.startswith('.')][:5]
        
        if file_names:
            context_parts.append(f"Files: {', '.join(file_names)}")
        if dir_names:
            context_parts.append(f"Directories: {', '.join(dir_names)}")
    except:
        pass
    
    return "\n".join(context_parts)
