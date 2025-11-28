"""
Task Tool - Subagent Spawning
=============================

Specialized subagent launcher for Claude Code parity.

Contains:
- TaskTool: Launch specialized subagents for complex tasks

Author: JuanCS Dev
Date: 2025-11-27
"""

from __future__ import annotations

import datetime
import logging
from typing import Any, Dict, List, Optional

from jdev_cli.tools.base import Tool, ToolCategory, ToolResult

logger = logging.getLogger(__name__)


# =============================================================================
# SUBAGENT CONFIGURATION
# =============================================================================

SUBAGENT_TYPES: Dict[str, Dict[str, Any]] = {
    "explore": {
        "description": "Fast codebase exploration and search",
        "tools": ["glob", "grep", "read_file", "list_directory"],
        "prompt_prefix": "You are exploring a codebase. Be thorough but efficient.",
        "read_only": True
    },
    "plan": {
        "description": "Task planning and breakdown",
        "tools": ["glob", "grep", "read_file", "todo_write"],
        "prompt_prefix": "You are planning a task. Break it down into actionable steps.",
        "read_only": True
    },
    "general-purpose": {
        "description": "Complex multi-step autonomous tasks",
        "tools": "*",  # All tools
        "prompt_prefix": "You are handling a complex task autonomously.",
        "read_only": False
    },
    "code-reviewer": {
        "description": "Review code for quality and best practices",
        "tools": ["read_file", "glob", "grep"],
        "prompt_prefix": "You are reviewing code. Focus on quality, security, and best practices.",
        "read_only": True
    },
    "test-runner": {
        "description": "Execute and analyze test results",
        "tools": ["bash_command", "read_file", "glob"],
        "prompt_prefix": "You are running tests. Report results clearly.",
        "read_only": True
    },
    "security": {
        "description": "Security analysis and vulnerability scanning",
        "tools": ["read_file", "glob", "grep", "bash_command"],
        "prompt_prefix": "You are analyzing code for security vulnerabilities. Follow OWASP guidelines.",
        "read_only": True
    },
    "documentation": {
        "description": "Generate documentation from code",
        "tools": ["read_file", "glob", "write_file"],
        "prompt_prefix": "You are generating documentation. Be clear and comprehensive.",
        "read_only": False
    },
    "refactor": {
        "description": "Code refactoring suggestions",
        "tools": ["read_file", "glob", "grep", "edit_file"],
        "prompt_prefix": "You are refactoring code. Maintain functionality while improving structure.",
        "read_only": False
    }
}


# =============================================================================
# TASK TOOL
# =============================================================================

class TaskTool(Tool):
    """
    Launch specialized subagents for complex, multi-step tasks.

    Claude Code parity: Implements the Task tool for spawning subagents.

    Available agent types:
    - explore: Fast codebase exploration
    - plan: Task planning and breakdown
    - general-purpose: Complex multi-step tasks
    - code-reviewer: Review code changes
    - test-runner: Execute test suites
    - security: Security analysis
    - documentation: Generate docs
    - refactor: Code refactoring

    Example:
        result = await task.execute(
            prompt="Find all Python files that import asyncio",
            subagent_type="explore",
            description="Find asyncio imports"
        )
    """

    # Track running subagents (class-level)
    _subagents: Dict[str, Dict[str, Any]] = {}
    _subagent_counter: int = 0

    def __init__(self):
        super().__init__()
        self.name = "task"
        self.category = ToolCategory.EXECUTION
        self.description = "Launch specialized subagents for autonomous task handling"
        self.parameters = {
            "prompt": {
                "type": "string",
                "description": "The task for the subagent to perform",
                "required": True
            },
            "subagent_type": {
                "type": "string",
                "description": f"Agent type: {', '.join(SUBAGENT_TYPES.keys())}",
                "required": True
            },
            "description": {
                "type": "string",
                "description": "Short (3-5 word) description of the task",
                "required": False
            },
            "model": {
                "type": "string",
                "description": "Model to use: 'default', 'fast', 'smart' (default: inherit)",
                "required": False
            },
            "resume": {
                "type": "string",
                "description": "Subagent ID to resume from previous execution",
                "required": False
            }
        }

    async def _execute_validated(self, **kwargs) -> ToolResult:
        """Execute subagent task."""
        prompt = kwargs.get("prompt", "")
        subagent_type = kwargs.get("subagent_type", "general-purpose")
        description = kwargs.get("description", "")
        model = kwargs.get("model", "default")
        resume_id = kwargs.get("resume")

        # Validate prompt
        if not prompt:
            return ToolResult(success=False, error="prompt is required")

        if len(prompt) > 10000:
            return ToolResult(success=False, error="prompt too long (max 10000 chars)")

        # Validate subagent type
        if subagent_type not in SUBAGENT_TYPES:
            available = ", ".join(SUBAGENT_TYPES.keys())
            return ToolResult(
                success=False,
                error=f"Unknown subagent_type: {subagent_type}. Available: {available}"
            )

        # Resume existing subagent if requested
        if resume_id and resume_id in TaskTool._subagents:
            subagent = TaskTool._subagents[resume_id]
            subagent["prompts"].append(prompt)
            logger.info(f"Resuming subagent {resume_id}")
            return await self._run_subagent(subagent, prompt)

        # Create new subagent
        TaskTool._subagent_counter += 1
        subagent_id = f"subagent_{TaskTool._subagent_counter}"

        agent_config = SUBAGENT_TYPES[subagent_type]
        subagent = {
            "id": subagent_id,
            "type": subagent_type,
            "description": description[:100] if description else f"{subagent_type} task",
            "model": model,
            "config": agent_config,
            "prompts": [prompt],
            "results": [],
            "status": "created",
            "created_at": datetime.datetime.now().isoformat()
        }

        TaskTool._subagents[subagent_id] = subagent
        logger.info(f"Created subagent {subagent_id} type={subagent_type}")

        return await self._run_subagent(subagent, prompt)

    async def _run_subagent(self, subagent: Dict, prompt: str) -> ToolResult:
        """
        Run the subagent with isolated context and restricted tools.

        Claude Code Parity: Subagents run autonomously with:
        - Isolated LLM context (no parent conversation history)
        - Restricted tool set based on agent type
        - Independent execution with result aggregation
        """
        subagent["status"] = "running"

        try:
            config = subagent["config"]
            full_prompt = f"{config['prompt_prefix']}\n\nTask: {prompt}"

            # Execute with real LLM if available
            result = await self._execute_with_llm(subagent, full_prompt)

            subagent["results"].append(result)
            subagent["status"] = "completed"

            return ToolResult(
                success=True,
                data={
                    "subagent_id": subagent["id"],
                    "type": subagent["type"],
                    "description": subagent["description"],
                    "result": result,
                    "can_resume": True
                },
                metadata={
                    "prompts_count": len(subagent["prompts"]),
                    "model": subagent["model"],
                    "tools_available": config["tools"],
                    "read_only": config.get("read_only", False)
                }
            )

        except Exception as e:
            subagent["status"] = "failed"
            subagent["error"] = str(e)
            logger.error(f"Subagent {subagent['id']} failed: {e}")
            return ToolResult(success=False, error=str(e))

    async def _execute_with_llm(self, subagent: Dict, prompt: str) -> Dict:
        """
        Execute subagent task using real LLM with restricted tools.

        Claude Code Pattern:
        - Create isolated GeminiClient instance
        - Filter tools based on subagent type
        - Run agentic loop with tool calls
        - Return aggregated results
        """
        config = subagent["config"]
        agent_type = subagent["type"]
        allowed_tools = config["tools"]

        # Try to use real LLM
        try:
            from jdev_tui.core.llm_client import GeminiClient, ToolCallParser

            # Create isolated LLM instance
            llm = GeminiClient()

            if not llm.is_available:
                return self._fallback_execution(subagent, prompt)

            # Try to get tools bridge
            try:
                from jdev_tui.core.tools_bridge import ToolBridge
                tools = ToolBridge()
                all_schemas = tools.get_schemas_for_llm()

                # Filter schemas based on allowed tools
                if allowed_tools == "*":
                    filtered_schemas = all_schemas
                else:
                    filtered_schemas = [
                        s for s in all_schemas
                        if s.get("name") in allowed_tools
                    ]

                # Configure LLM with restricted tools
                if filtered_schemas:
                    llm.set_tools(filtered_schemas)

            except ImportError:
                logger.debug("ToolBridge not available")
                filtered_schemas = []

            # Build system prompt for subagent
            system_prompt = self._build_subagent_system_prompt(agent_type, allowed_tools)

            # Execute with LLM
            response_text = ""
            tool_calls_executed = []

            async for chunk in llm.stream(prompt, system_prompt=system_prompt):
                response_text += chunk

            # Parse any tool calls from response
            tool_calls = ToolCallParser.extract(response_text)

            # Execute tool calls if any (limited to allowed tools)
            if tool_calls and 'tools' in dir():
                for tool_name, args in tool_calls[:10]:  # Limit tool calls
                    if allowed_tools == "*" or tool_name in allowed_tools:
                        try:
                            result = await tools.execute_tool(tool_name, **args)
                            tool_calls_executed.append({
                                "tool": tool_name,
                                "success": result.get("success", False),
                                "summary": str(result.get("data", ""))[:200]
                            })
                        except Exception as e:
                            tool_calls_executed.append({
                                "tool": tool_name,
                                "success": False,
                                "error": str(e)[:100]
                            })

            # Clean response
            clean_response = ToolCallParser.remove(response_text)

            return {
                "type": agent_type,
                "response": clean_response[:5000],  # Limit response size
                "tool_calls": tool_calls_executed,
                "tools_used": len(tool_calls_executed),
                "status": "completed"
            }

        except ImportError as e:
            logger.debug(f"LLM not available: {e}")
            return self._fallback_execution(subagent, prompt)

        except Exception as e:
            logger.error(f"Subagent LLM execution failed: {e}")
            return {
                "type": agent_type,
                "error": str(e)[:200],
                "fallback": True,
                "summary": f"Subagent execution failed: {str(e)[:100]}",
                "status": "failed"
            }

    def _build_subagent_system_prompt(self, agent_type: str, allowed_tools: Any) -> str:
        """Build system prompt for subagent based on type."""
        base = f"You are a specialized {agent_type} subagent. Execute tasks autonomously and return results."

        type_prompts = {
            "explore": """
Focus on:
- Finding relevant files and code patterns
- Understanding project structure
- Reporting findings concisely
Do NOT modify any files. Read-only exploration.""",

            "plan": """
Focus on:
- Breaking down tasks into actionable steps
- Identifying dependencies between steps
- Estimating complexity
Create a clear, numbered plan.""",

            "code-reviewer": """
Focus on:
- Code quality and best practices
- Potential bugs or issues
- Security concerns
- Performance considerations
Provide specific, actionable feedback.""",

            "test-runner": """
Focus on:
- Running relevant test suites
- Reporting pass/fail status
- Identifying failing tests
- Suggesting fixes for failures""",

            "security": """
Focus on:
- OWASP Top 10 vulnerabilities
- Input validation issues
- Authentication/authorization flaws
- Data exposure risks
Prioritize findings by severity.""",

            "documentation": """
Focus on:
- Clear, comprehensive documentation
- Code examples where helpful
- API documentation if applicable
Write in markdown format.""",

            "refactor": """
Focus on:
- Improving code structure
- Reducing complexity
- Enhancing readability
- Maintaining functionality
Explain each refactoring decision.""",

            "general-purpose": """
Execute the task completely and autonomously.
Use available tools as needed.
Report results clearly."""
        }

        tools_str = ", ".join(allowed_tools) if isinstance(allowed_tools, list) else "all"
        tools_note = f"\nAvailable tools: {tools_str}"

        return base + type_prompts.get(agent_type, type_prompts["general-purpose"]) + tools_note

    def _fallback_execution(self, subagent: Dict, prompt: str) -> Dict:
        """Fallback when LLM is not available."""
        agent_type = subagent["type"]
        return {
            "type": agent_type,
            "summary": f"Task queued for {agent_type}: {prompt[:200]}...",
            "hint": "LLM not available. Configure GEMINI_API_KEY to enable full subagent capabilities.",
            "status": "queued",
            "fallback": True
        }

    @classmethod
    def list_subagents(cls) -> List[Dict]:
        """List all subagents and their status."""
        return [
            {
                "id": s["id"],
                "type": s["type"],
                "description": s["description"],
                "status": s["status"],
                "prompts_count": len(s["prompts"]),
                "created_at": s["created_at"]
            }
            for s in cls._subagents.values()
        ]

    @classmethod
    def get_subagent(cls, subagent_id: str) -> Optional[Dict]:
        """Get a specific subagent by ID."""
        return cls._subagents.get(subagent_id)

    @classmethod
    def clear_subagents(cls) -> None:
        """Clear all subagents (for testing)."""
        cls._subagents.clear()
        cls._subagent_counter = 0


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    "TaskTool",
    "SUBAGENT_TYPES",
]
