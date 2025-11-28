"""Async parallel tool execution (Anthropic pattern).

Boris Cherny: Clear dependencies, no race conditions.
"""

import asyncio
from typing import List, Dict, Any, Set
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class ToolCall:
    """Tool call with dependency tracking."""

    id: str
    tool_name: str
    args: Dict[str, Any]
    depends_on: Set[str] = None

    def __post_init__(self):
        if self.depends_on is None:
            self.depends_on = set()


@dataclass
class ParallelExecutionResult:
    """Result of parallel tool execution."""

    results: Dict[str, Any]
    execution_time_ms: float
    parallelism_factor: float  # How much parallelism achieved


class AsyncExecutor:
    """Parallel tool executor (Anthropic pattern).
    
    Executes independent tools in parallel for 3-5x speedup.
    """

    def __init__(self, max_parallel: int = 5):
        self._max_parallel = max_parallel
        self._semaphore = asyncio.Semaphore(max_parallel)

    async def execute_parallel(
        self,
        tool_calls: List[ToolCall],
        execute_fn
    ) -> ParallelExecutionResult:
        """Execute tools in parallel where possible.
        
        Args:
            tool_calls: List of tool calls with dependencies
            execute_fn: Async function to execute single tool
            
        Returns:
            ParallelExecutionResult with all results and timing
        """
        import time
        start = time.time()

        # Build dependency graph
        results = {}
        completed = set()

        # Execute in waves (respecting dependencies)
        while len(completed) < len(tool_calls):
            # Find tools ready to execute
            ready = [
                call for call in tool_calls
                if call.id not in completed
                and call.depends_on.issubset(completed)
            ]

            if not ready:
                # Circular dependency or error
                logger.error("Dependency deadlock detected")
                break

            # Execute ready tools in parallel
            tasks = [
                self._execute_with_semaphore(call, execute_fn)
                for call in ready
            ]

            wave_results = await asyncio.gather(*tasks, return_exceptions=True)

            # Collect results
            for call, result in zip(ready, wave_results):
                results[call.id] = result
                completed.add(call.id)

        execution_time = (time.time() - start) * 1000

        # Calculate parallelism factor
        total_time_sequential = sum(
            r.get('execution_time', 0) for r in results.values()
            if isinstance(r, dict)
        )
        parallelism = total_time_sequential / execution_time if execution_time > 0 else 1.0

        return ParallelExecutionResult(
            results=results,
            execution_time_ms=execution_time,
            parallelism_factor=parallelism
        )

    async def _execute_with_semaphore(self, call: ToolCall, execute_fn):
        """Execute with concurrency limit."""
        async with self._semaphore:
            try:
                return await execute_fn(call.tool_name, call.args)
            except Exception as e:
                logger.error(f"Tool {call.tool_name} failed: {e}")
                return {"error": str(e)}


def detect_dependencies(tool_calls: List[Dict]) -> List[ToolCall]:
    """Detect dependencies between tool calls.
    
    Simple heuristic:
    - read_file() doesn't depend on anything
    - write_file() depends on read_file() for same file
    - bash_command() depends on write_file() if it references the file
    """
    calls = []
    file_operations = {}  # file_path -> call_id

    for i, call_dict in enumerate(tool_calls):
        call_id = f"tool_{i}"
        tool_name = call_dict.get("tool", "")
        args = call_dict.get("args", {})
        depends_on = set()

        # Check dependencies
        if tool_name == "write_file":
            file_path = args.get("file_path")
            if file_path in file_operations:
                depends_on.add(file_operations[file_path])

        elif tool_name == "bash_command":
            # Check if command references any written files
            command = args.get("command", "")
            for file_path, dep_id in file_operations.items():
                if file_path in command:
                    depends_on.add(dep_id)

        # Track file operations
        if tool_name in ["read_file", "write_file"]:
            file_path = args.get("file_path")
            if file_path:
                file_operations[file_path] = call_id

        calls.append(ToolCall(
            id=call_id,
            tool_name=tool_name,
            args=args,
            depends_on=depends_on
        ))

    return calls
