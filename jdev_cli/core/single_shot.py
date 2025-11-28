"""Single-shot execution for non-interactive mode.

This module provides functionality for executing single commands without
entering the interactive REPL, following the Constitutional AI principles.
"""

import os
import json
from typing import Dict, Any
from pathlib import Path

from .llm import llm_client
from .context import ContextBuilder
from ..tools.base import ToolRegistry
from ..tools.file_ops import (
    ReadFileTool, WriteFileTool, EditFileTool,
    ListDirectoryTool
)
from ..tools.search import SearchFilesTool
from ..tools.exec_hardened import BashCommandTool
from ..tools.git_ops import GitStatusTool, GitDiffTool


class SingleShotExecutor:
    """Execute single command without interactive session."""

    def __init__(self):
        """Initialize executor with tools and LLM client."""
        self.llm = llm_client
        self.context_builder = ContextBuilder()
        self.registry = ToolRegistry()
        self._register_tools()

    def _register_tools(self):
        """Register essential tools for single-shot execution."""
        tools = [
            ReadFileTool(),
            WriteFileTool(),
            EditFileTool(),
            ListDirectoryTool(),
            SearchFilesTool(),
            BashCommandTool(),
            GitStatusTool(),
            GitDiffTool(),
        ]

        for tool in tools:
            self.registry.register(tool)

    async def execute(
        self,
        message: str,
        include_context: bool = True
    ) -> Dict[str, Any]:
        """Execute single message and return structured result.
        
        Args:
            message: User's command/request
            include_context: Whether to include project context
            
        Returns:
            Dictionary with execution result:
            {
                'success': bool,
                'output': str,
                'actions_taken': List[str],
                'errors': List[str]
            }
        """
        try:
            # Build context
            context = {}
            if include_context:
                context = self._build_context()

            # Generate LLM response with tool calls
            response = await self._get_llm_response(message, context)

            # Parse and execute tool calls
            tool_calls = self._parse_tool_calls(response)

            if not tool_calls:
                # No tools needed, return LLM response directly
                return {
                    'success': True,
                    'output': response,
                    'actions_taken': [],
                    'errors': []
                }

            # Execute tools
            results = await self._execute_tool_calls(tool_calls)

            # Format results
            return self._format_results(results)

        except Exception as e:
            return {
                'success': False,
                'output': "",
                'actions_taken': [],
                'errors': [f"Execution error: {str(e)}"]
            }

    def _build_context(self) -> Dict[str, Any]:
        """Build project context for LLM."""
        return {
            'cwd': os.getcwd(),
            'project_structure': self._get_project_structure(),
        }

    def _get_project_structure(self) -> str:
        """Get basic project structure."""
        try:
            cwd = Path.cwd()
            files = list(cwd.glob('*'))
            structure = '\n'.join(f"  - {f.name}" for f in files[:20])
            return f"Current directory:\n{structure}"
        except Exception:
            return "Unable to read project structure"

    async def _get_llm_response(
        self,
        message: str,
        context: Dict[str, Any]
    ) -> str:
        """Get LLM response for user message."""
        # Build system prompt
        tool_schemas = self.registry.get_schemas()
        tool_list = '\n'.join(
            f"- {schema['name']}: {schema['description']}"
            for schema in tool_schemas
        )

        system_prompt = f"""You are an AI code assistant with access to tools.

Available tools:
{tool_list}

Current context:
- Working directory: {context.get('cwd', 'unknown')}

INSTRUCTIONS:
1. Analyze the user's request
2. If tools are needed, respond ONLY with a JSON array of tool calls
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

User: "what is Python?"
Response: Python is a high-level programming language...
"""

        # LLMClient.generate() aceita prompt e system_prompt separados
        response = await self.llm.generate(
            prompt=message,
            system_prompt=system_prompt,
            temperature=0.1,
            max_tokens=2000
        )

        return response

    def _parse_tool_calls(self, response: str) -> list:
        """Parse tool calls from LLM response."""
        try:
            # Look for JSON array in response
            if '[' in response and ']' in response:
                start = response.index('[')
                end = response.rindex(']') + 1
                json_str = response[start:end]
                tool_calls = json.loads(json_str)

                if isinstance(tool_calls, list):
                    return tool_calls
        except (json.JSONDecodeError, ValueError):
            pass

        return []

    async def _execute_tool_calls(
        self,
        tool_calls: list
    ) -> list:
        """Execute sequence of tool calls."""
        results = []

        for call in tool_calls:
            tool_name = call.get("tool", "")
            args = call.get("args", {})

            tool = self.registry.get(tool_name)

            if not tool:
                results.append({
                    'success': False,
                    'tool': tool_name,
                    'error': f"Unknown tool: {tool_name}"
                })
                continue

            try:
                result = await tool.execute(**args)
                results.append({
                    'success': result.success,
                    'tool': tool_name,
                    'output': str(result.data) if result.success else None,
                    'error': result.error if not result.success else None
                })
            except Exception as e:
                results.append({
                    'success': False,
                    'tool': tool_name,
                    'error': str(e)
                })

        return results

    def _format_results(self, results: list) -> Dict[str, Any]:
        """Format tool execution results."""
        all_success = all(r['success'] for r in results)

        output_parts = []
        errors = []
        actions = []

        for result in results:
            actions.append(result['tool'])

            if result['success']:
                if result.get('output'):
                    output_parts.append(f"✓ {result['tool']}: {result['output']}")
                else:
                    output_parts.append(f"✓ {result['tool']}: Success")
            else:
                error_msg = f"✗ {result['tool']}: {result.get('error', 'Unknown error')}"
                output_parts.append(error_msg)
                errors.append(error_msg)

        return {
            'success': all_success,
            'output': '\n'.join(output_parts),
            'actions_taken': actions,
            'errors': errors
        }


# Singleton instance
_executor = None


def get_executor() -> SingleShotExecutor:
    """Get or create singleton executor instance."""
    global _executor
    if _executor is None:
        _executor = SingleShotExecutor()
    return _executor


async def execute_single_shot(
    message: str,
    include_context: bool = True
) -> Dict[str, Any]:
    """Execute single message in non-interactive mode.
    
    This is the main entry point for non-interactive execution.
    
    Args:
        message: User's command/request
        include_context: Whether to include project context
        
    Returns:
        Execution result dictionary
    """
    executor = get_executor()
    return await executor.execute(message, include_context)
