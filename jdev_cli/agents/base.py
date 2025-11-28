"""
BaseAgent v2.1: The Cybernetic Kernel.

Implements the OODA Loop (Observe, Orient, Decide, Act) for AI Agents.
Features:
- Structured Reasoning (Chain of Thought enforcement)
- Tool Capability Sandboxing
- Telemetry & Token Budgeting
- Self-Correction Mechanism

Philosophy:
    "An agent that cannot correct its own errors is just a script."

v2.1 Changes:
    - Types moved to jdev_core for dependency inversion
    - Re-exports maintained for backward compatibility
"""

import abc
import logging
from typing import Any, Dict, List, Optional, cast

# =============================================================================
# IMPORTS FROM jdev_core (Single Source of Truth)
# =============================================================================
# All core types are now defined in jdev_core.types
# We re-export them here for backward compatibility

from jdev_core.types import (
    # Enums
    AgentRole,
    AgentCapability,
    TaskStatus,
    # Models
    AgentTask,
    AgentResponse,
    TaskResult,
    # Exceptions
    CapabilityViolationError,
)

# Re-export for backward compatibility
__all__ = [
    "AgentRole",
    "AgentCapability",
    "TaskStatus",
    "AgentTask",
    "AgentResponse",
    "TaskResult",
    "CapabilityViolationError",
    "BaseAgent",
]


# =============================================================================
# NOTE: The following types are now imported from jdev_core:
# - AgentRole (enum)
# - AgentCapability (enum)
# - TaskStatus (enum)
# - AgentTask (Pydantic model)
# - AgentResponse (Pydantic model)
# - TaskResult (Pydantic model)
# - CapabilityViolationError (exception)
#
# This enables dependency inversion:
#   jdev_tui ───┐
#               ├──> jdev_core (types & protocols)
#   qwen_agents ┘
# =============================================================================


# =============================================================================
# BASE AGENT CLASS
# =============================================================================

class BaseAgent(abc.ABC):
    """
    Abstract Cybernetic Agent.
    
    Enforces the 'Think before Act' protocol and manages tool safety.
    """

    def __init__(
        self,
        role: AgentRole,
        capabilities: List[AgentCapability],
        llm_client: Any,
        mcp_client: Any,
        system_prompt: str = "",
    ) -> None:
        self.role = role
        self.capabilities = capabilities
        self.llm_client = llm_client
        self.mcp_client = mcp_client
        self.system_prompt = system_prompt
        self.execution_count = 0
        self.logger = logging.getLogger(f"agent.{role.value}")

    @abc.abstractmethod
    async def execute(self, task: AgentTask) -> AgentResponse:
        """Main entry point. Must be implemented by subclasses."""
        pass

    async def _reason(self, task: AgentTask, context_str: str) -> str:
        """
        Internal 'Thinking' Step.
        Forces the agent to perform Chain of Thought before touching tools.
        """
        prompt = f"""
        TASK: {task.request}
        CONTEXT: {context_str}
        
        Analyze the situation. 
        1. Identify the goal.
        2. Identify constraints.
        3. Formulate a plan.
        
        Respond with your reasoning trace.
        """
        return await self._call_llm(prompt, system_prompt=self.system_prompt)

    async def _call_llm(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs: Any,
    ) -> str:
        """Wrapper for LLM calls with error handling and logging."""
        final_sys_prompt = system_prompt or self.system_prompt
        try:
            # Handle both async generate() and async stream()
            if hasattr(self.llm_client, 'generate'):
                response = await self.llm_client.generate(
                    prompt=prompt,
                    system_prompt=final_sys_prompt,
                    **kwargs,
                )
            else:
                # Fallback for streaming client
                buffer = []
                async for chunk in self.llm_client.stream(
                    prompt=prompt,
                    system_prompt=final_sys_prompt,
                    **kwargs,
                ):
                    buffer.append(chunk)
                response = ''.join(buffer)

            self.execution_count += 1
            return cast(str, response)
        except Exception as e:
            self.logger.error(f"LLM call failed (role={self.role.value}): {type(e).__name__}: {e}", exc_info=True)
            raise

    async def _stream_llm(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs: Any,
    ):
        """Stream LLM responses token by token for 30 FPS updates.

        Yields:
            str: Individual tokens as they arrive from LLM
        """
        final_sys_prompt = system_prompt or self.system_prompt
        try:
            # Use stream_chat for real-time token delivery
            if hasattr(self.llm_client, 'stream_chat'):
                async for chunk in self.llm_client.stream_chat(
                    prompt=prompt,
                    context=final_sys_prompt,
                    **kwargs,
                ):
                    yield chunk
            elif hasattr(self.llm_client, 'stream'):
                async for chunk in self.llm_client.stream(
                    prompt=prompt,
                    system_prompt=final_sys_prompt,
                    **kwargs,
                ):
                    yield chunk
            else:
                # Fallback: call non-streaming and yield whole response
                response = await self._call_llm(prompt, system_prompt, **kwargs)
                yield response

            self.execution_count += 1
        except Exception as e:
            self.logger.error(f"LLM stream failed (role={self.role.value}): {type(e).__name__}: {e}", exc_info=True)
            raise

    def _can_use_tool(self, tool_name: str) -> bool:
        """Strict capability enforcement."""
        # Mapping definition (Expanded for v2)
        tool_map = {
            "read_file": AgentCapability.READ_ONLY,
            "list_files": AgentCapability.READ_ONLY,
            "grep_search": AgentCapability.READ_ONLY,
            "ast_parse": AgentCapability.READ_ONLY,
            "find_files": AgentCapability.READ_ONLY,
            "write_file": AgentCapability.FILE_EDIT,
            "edit_file": AgentCapability.FILE_EDIT,
            "delete_file": AgentCapability.FILE_EDIT,
            "create_directory": AgentCapability.FILE_EDIT,
            "bash_command": AgentCapability.BASH_EXEC,
            "exec_command": AgentCapability.BASH_EXEC,
            "git_diff": AgentCapability.GIT_OPS,
            "git_commit": AgentCapability.GIT_OPS,
            "git_push": AgentCapability.GIT_OPS,
            "git_status": AgentCapability.GIT_OPS,
            "db_query": AgentCapability.DATABASE,
            "db_execute": AgentCapability.DATABASE,
            "db_schema": AgentCapability.DATABASE,
            "k8s_action": AgentCapability.BASH_EXEC,  # DevOps: Kubernetes operations
            "docker_build": AgentCapability.BASH_EXEC,  # DevOps: Docker operations
            "argocd_sync": AgentCapability.BASH_EXEC,  # DevOps: ArgoCD operations
            # Web Tools (Enabled by default for READ_ONLY)
            "web_search": AgentCapability.READ_ONLY,
            "search_documentation": AgentCapability.READ_ONLY,
            "fetch_url": AgentCapability.READ_ONLY,
            "package_search": AgentCapability.READ_ONLY,
            "download_file": AgentCapability.FILE_EDIT,  # Writes to disk
        }

        required = tool_map.get(tool_name)
        if not required:
            # If tool is unknown, default to blocking it for safety
            self.logger.warning(f"Unknown tool requested: {tool_name}")
            return False

        return required in self.capabilities

    async def _execute_tool(
        self,
        tool_name: str,
        parameters: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Executes MCP tool with safety checks."""
        if not self._can_use_tool(tool_name):
            msg = f"SECURITY VIOLATION: {self.role.value} attempted to use forbidden tool '{tool_name}'"
            self.logger.critical(msg)
            raise CapabilityViolationError(msg)

        try:
            self.logger.info(f"Executing {tool_name} with params: {parameters.keys()}")

            # Handle case where mcp_client is None (fallback to direct calls)
            if self.mcp_client is None:
                self.logger.warning("MCP client not available, tool execution skipped")
                return {"success": False, "error": "MCP client not initialized"}

            result = await self.mcp_client.call_tool(tool_name=tool_name, arguments=parameters)
            return cast(Dict[str, Any], result)
        except Exception as e:
            self.logger.error(f"Tool '{tool_name}' execution failed (role={self.role.value}): {type(e).__name__}: {e}", exc_info=True)
            return {"success": False, "error": f"{type(e).__name__}: {str(e)}"}

# Compatibility aliases for existing agents
TaskContext = AgentTask  # Alias for old code
