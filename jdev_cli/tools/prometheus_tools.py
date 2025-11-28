"""
PROMETHEUS Tools for MCP - EXPANDED SET (8+ Tools).

Exposes PROMETHEUS capabilities as MCP tools:

CORE TOOLS (4):
- prometheus_execute: Execute task via PROMETHEUS
- prometheus_memory_query: Query PROMETHEUS memory
- prometheus_simulate: Simulate action via world model
- prometheus_evolve: Run evolution cycle

EXPANDED TOOLS (4+):
- prometheus_reflect: Trigger reflection on completed action
- prometheus_create_tool: Generate new tool dynamically (AutoTools)
- prometheus_get_status: Get full system status (memory, world model, evolution)
- prometheus_benchmark: Run benchmark suite to measure capabilities
- prometheus_memory_consolidate: Force memory consolidation to vault
- prometheus_world_model_reset: Reset world model state
"""

from typing import Optional
from jdev_cli.tools.base import ToolResult, ToolCategory
from jdev_cli.tools.validated import ValidatedTool


class PrometheusExecuteTool(ValidatedTool):
    """Execute task via PROMETHEUS agent."""

    def __init__(self, prometheus_provider=None):
        super().__init__()
        self._provider = prometheus_provider
        self.category = ToolCategory.EXECUTION
        self.description = """
Execute a task using PROMETHEUS self-evolving meta-agent.

PROMETHEUS provides:
- World model simulation (plans before acting)
- 6-type persistent memory (learns from experience)
- Self-reflection (improves over time)
- Automatic tool creation (generates tools on-demand)

Use this for complex tasks that benefit from planning and learning.
"""
        self.parameters = {
            "task": {
                "type": "string",
                "description": "Task description to execute",
                "required": True
            },
            "use_world_model": {
                "type": "boolean",
                "description": "Enable world model simulation (default: true)",
                "required": False
            },
            "use_memory": {
                "type": "boolean",
                "description": "Enable memory retrieval (default: true)",
                "required": False
            }
        }

    def set_provider(self, provider):
        """Set PROMETHEUS provider (for lazy initialization)."""
        self._provider = provider

    async def _execute_validated(
        self,
        task: str,
        use_world_model: bool = True,
        use_memory: bool = True
    ) -> ToolResult:
        if not self._provider:
            return ToolResult(success=False, error="Prometheus provider not initialized")

        try:
            # Configure provider on the fly if needed
            self._provider.config.enable_world_model = use_world_model
            self._provider.config.enable_memory = use_memory

            result = await self._provider.generate(task)
            return ToolResult(success=True, data=result)
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class PrometheusMemoryQueryTool(ValidatedTool):
    """Query PROMETHEUS memory system."""

    def __init__(self, prometheus_provider=None):
        super().__init__()
        self._provider = prometheus_provider
        self.category = ToolCategory.CONTEXT
        self.description = "Query PROMETHEUS 6-type persistent memory system (MIRIX)."
        self.parameters = {
            "query": {
                "type": "string",
                "description": "Query string",
                "required": True
            },
            "memory_type": {
                "type": "string",
                "description": "Specific memory type (episodic, semantic, procedural, core, resource, vault) or 'all'",
                "required": False
            }
        }

    def set_provider(self, provider):
        self._provider = provider

    async def _execute_validated(self, query: str, memory_type: str = "all") -> ToolResult:
        if not self._provider:
            return ToolResult(success=False, error="Prometheus provider not initialized")

        try:
            # Assuming provider has a method to query memory directly or via orchestrator
            # Since get_memory_context is available, we use that for now,
            # or we might need to extend provider to support specific queries if get_memory_context is task-based.
            # For now, we use get_memory_context with the query as the task.
            context = self._provider.get_memory_context(query)
            return ToolResult(success=True, data=context)
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class PrometheusSimulateTool(ValidatedTool):
    """Simulate action via World Model."""

    def __init__(self, prometheus_provider=None):
        super().__init__()
        self._provider = prometheus_provider
        self.category = ToolCategory.EXECUTION
        self.description = "Simulate an action or plan using the World Model (SimuRA) without executing it."
        self.parameters = {
            "action_plan": {
                "type": "string",
                "description": "Action plan to simulate",
                "required": True
            }
        }

    def set_provider(self, provider):
        self._provider = provider

    async def _execute_validated(self, action_plan: str) -> ToolResult:
        if not self._provider:
            return ToolResult(success=False, error="Prometheus provider not initialized")

        try:
            # We need to access the orchestrator's world model directly if possible
            await self._provider._ensure_initialized()
            if self._provider._orchestrator and hasattr(self._provider._orchestrator, 'world_model'):
                # Assuming world_model has a simulate method
                if hasattr(self._provider._orchestrator.world_model, 'simulate'):
                     simulation = await self._provider._orchestrator.world_model.simulate(action_plan)
                     return ToolResult(success=True, data=simulation)
                else:
                     return ToolResult(success=False, error="World Model does not have simulate method")
            return ToolResult(success=False, error="World Model not available")
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class PrometheusEvolveTool(ValidatedTool):
    """Run evolution cycle."""

    def __init__(self, prometheus_provider=None):
        super().__init__()
        self._provider = prometheus_provider
        self.category = ToolCategory.SYSTEM
        self.description = "Run self-evolution cycle (Agent0) to improve capabilities."
        self.parameters = {
            "iterations": {
                "type": "integer",
                "description": "Number of evolution iterations",
                "required": False
            }
        }

    def set_provider(self, provider):
        self._provider = provider

    async def _execute_validated(self, iterations: int = 5) -> ToolResult:
        if not self._provider:
            return ToolResult(success=False, error="Prometheus provider not initialized")

        try:
            result = await self._provider.evolve(iterations)
            return ToolResult(success=True, data=result)
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class PrometheusReflectTool(ValidatedTool):
    """Trigger reflection."""

    def __init__(self, prometheus_provider=None):
        super().__init__()
        self._provider = prometheus_provider
        self.category = ToolCategory.SYSTEM
        self.description = "Trigger self-reflection on a completed task or action."
        self.parameters = {
            "task_id": {
                "type": "string",
                "description": "ID of the task to reflect on (optional, reflects on last if empty)",
                "required": False
            },
             "outcome": {
                "type": "string",
                "description": "Outcome of the task (success/failure details)",
                "required": True
            }
        }

    def set_provider(self, provider):
        self._provider = provider

    async def _execute_validated(self, outcome: str, task_id: Optional[str] = None) -> ToolResult:
        if not self._provider:
            return ToolResult(success=False, error="Prometheus provider not initialized")

        try:
             await self._provider._ensure_initialized()
             if self._provider._orchestrator and hasattr(self._provider._orchestrator, 'reflection'):
                 # Assuming reflection module has a reflect method
                 if hasattr(self._provider._orchestrator.reflection, 'reflect'):
                     reflection = await self._provider._orchestrator.reflection.reflect(outcome, task_id)
                     return ToolResult(success=True, data=reflection)
             return ToolResult(success=False, error="Reflection module not available")
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class PrometheusCreateToolTool(ValidatedTool):
    """Generate new tool dynamically."""

    def __init__(self, prometheus_provider=None):
        super().__init__()
        self._provider = prometheus_provider
        self.category = ToolCategory.SYSTEM
        self.description = "Generate a new tool dynamically (AutoTools) based on description."
        self.parameters = {
            "tool_description": {
                "type": "string",
                "description": "Description of the tool to create",
                "required": True
            },
            "language": {
                "type": "string",
                "description": "Language for the tool (python/bash)",
                "required": False
            }
        }

    def set_provider(self, provider):
        self._provider = provider

    async def _execute_validated(self, tool_description: str, language: str = "python") -> ToolResult:
        if not self._provider:
            return ToolResult(success=False, error="Prometheus provider not initialized")

        try:
             await self._provider._ensure_initialized()
             # Assuming orchestrator has a tool_factory
             if hasattr(self._provider._orchestrator, 'tool_factory'):
                 new_tool = await self._provider._orchestrator.tool_factory.create_tool(tool_description, language)
                 return ToolResult(success=True, data=new_tool)
             return ToolResult(success=False, error="Tool Factory not available")
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class PrometheusGetStatusTool(ValidatedTool):
    """Get full system status."""

    def __init__(self, prometheus_provider=None):
        super().__init__()
        self._provider = prometheus_provider
        self.category = ToolCategory.SYSTEM
        self.description = "Get full PROMETHEUS system status (memory, world model, evolution)."
        self.parameters = {}

    def set_provider(self, provider):
        self._provider = provider

    async def _execute_validated(self) -> ToolResult:
        if not self._provider:
            return ToolResult(success=False, error="Prometheus provider not initialized")

        try:
            status = self._provider.get_status()
            return ToolResult(success=True, data=status)
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class PrometheusBenchmarkTool(ValidatedTool):
    """Run benchmark suite."""

    def __init__(self, prometheus_provider=None):
        super().__init__()
        self._provider = prometheus_provider
        self.category = ToolCategory.SYSTEM
        self.description = "Run PROMETHEUS benchmark suite to measure capabilities."
        self.parameters = {
             "suite": {
                "type": "string",
                "description": "Benchmark suite to run (reasoning, coding, memory, all)",
                "required": False
            }
        }

    def set_provider(self, provider):
        self._provider = provider

    async def _execute_validated(self, suite: str = "all") -> ToolResult:
        if not self._provider:
            return ToolResult(success=False, error="Prometheus provider not initialized")

        try:
             await self._provider._ensure_initialized()
             # Assuming orchestrator has a run_benchmark method
             if hasattr(self._provider._orchestrator, 'run_benchmark'):
                 results = await self._provider._orchestrator.run_benchmark(suite)
                 return ToolResult(success=True, data=results)
             return ToolResult(success=False, error="Benchmark capability not available")
        except Exception as e:
            return ToolResult(success=False, error=str(e))
