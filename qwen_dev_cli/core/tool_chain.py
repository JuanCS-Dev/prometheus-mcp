"""
AtomicToolChain - Transaction-like Tool Execution
Pipeline de Diamante - Camada 3: EXECUTION SANDBOX

Addresses: ISSUE-083, ISSUE-084, ISSUE-085 (Tool chaining and atomicity)

Implements:
- Transaction-like semantics for tool chains
- Rollback on any failure
- Dependency detection
- Parallel execution where safe

Design Philosophy:
- All-or-nothing execution
- Automatic rollback on failure
- Preserve system consistency
- Traceable operations
"""

from __future__ import annotations

import asyncio
import time
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, TypeVar, Awaitable
from dataclasses import dataclass, field
from enum import Enum, auto
from contextlib import asynccontextmanager
import logging

from .atomic_ops import AtomicFileOps, AtomicResult
from .undo_manager import UndoManager, UndoableOperation

logger = logging.getLogger(__name__)


class ChainStatus(Enum):
    """Status of tool chain execution."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


class ToolDependency(Enum):
    """Types of dependencies between tools."""
    NONE = "none"
    SEQUENTIAL = "sequential"  # Must run after previous
    FILE_READ = "file_read"    # Reads file created by previous
    FILE_WRITE = "file_write"  # Writes to same file
    STATE = "state"           # Depends on state from previous


@dataclass
class ToolOperation:
    """A single operation in a tool chain."""
    op_id: str
    tool_name: str
    parameters: Dict[str, Any]
    dependencies: List[str] = field(default_factory=list)
    rollback_fn: Optional[Callable[[], Awaitable[bool]]] = None
    result: Optional[Any] = None
    error: Optional[str] = None
    executed: bool = False
    start_time: Optional[float] = None
    end_time: Optional[float] = None


@dataclass
class ChainResult:
    """Result of tool chain execution."""
    chain_id: str
    status: ChainStatus
    operations: List[ToolOperation]
    start_time: float
    end_time: float
    rolled_back: bool = False
    error: Optional[str] = None

    @property
    def duration(self) -> float:
        return self.end_time - self.start_time

    @property
    def successful_ops(self) -> int:
        return sum(1 for op in self.operations if op.executed and not op.error)


class AtomicToolChain:
    """
    Execute multiple tools atomically with rollback support.

    Features:
    - Transaction semantics (all-or-nothing)
    - Automatic rollback on failure
    - Dependency-aware execution order
    - Parallel execution for independent tools
    - Full operation logging

    Usage:
        chain = AtomicToolChain()

        chain.add_operation("write_file", {"path": "a.py", "content": "..."})
        chain.add_operation("write_file", {"path": "b.py", "content": "..."})
        chain.add_operation("run_tests", {}, dependencies=["op_1", "op_2"])

        result = await chain.execute(tool_registry)
        if not result.status == ChainStatus.COMPLETED:
            print(f"Chain failed: {result.error}")
    """

    def __init__(
        self,
        chain_id: Optional[str] = None,
        rollback_on_failure: bool = True,
        parallel_execution: bool = True,
    ):
        """
        Initialize AtomicToolChain.

        Args:
            chain_id: Unique chain identifier
            rollback_on_failure: Auto-rollback on any failure
            parallel_execution: Execute independent ops in parallel
        """
        import uuid
        self.chain_id = chain_id or str(uuid.uuid4())
        self.rollback_on_failure = rollback_on_failure
        self.parallel_execution = parallel_execution

        self._operations: List[ToolOperation] = []
        self._op_counter = 0
        self._status = ChainStatus.PENDING
        self._executed_ops: List[ToolOperation] = []

        self._atomic_ops = AtomicFileOps()
        self._undo_manager = UndoManager()

    def add_operation(
        self,
        tool_name: str,
        parameters: Dict[str, Any],
        dependencies: Optional[List[str]] = None,
        rollback_fn: Optional[Callable[[], Awaitable[bool]]] = None,
        op_id: Optional[str] = None,
    ) -> str:
        """
        Add an operation to the chain.

        Args:
            tool_name: Name of the tool to execute
            parameters: Tool parameters
            dependencies: List of operation IDs this depends on
            rollback_fn: Custom rollback function
            op_id: Optional operation ID

        Returns:
            Operation ID
        """
        self._op_counter += 1
        op_id = op_id or f"op_{self._op_counter}"

        operation = ToolOperation(
            op_id=op_id,
            tool_name=tool_name,
            parameters=parameters,
            dependencies=dependencies or [],
            rollback_fn=rollback_fn,
        )

        self._operations.append(operation)
        return op_id

    def _get_execution_order(self) -> List[List[ToolOperation]]:
        """
        Determine execution order respecting dependencies.

        Returns list of batches that can be executed in parallel within each batch.
        """
        # Build dependency graph
        remaining = set(op.op_id for op in self._operations)
        op_map = {op.op_id: op for op in self._operations}
        batches: List[List[ToolOperation]] = []

        while remaining:
            # Find operations with all dependencies satisfied
            ready = []
            for op_id in remaining:
                op = op_map[op_id]
                deps_satisfied = all(
                    dep not in remaining
                    for dep in op.dependencies
                )
                if deps_satisfied:
                    ready.append(op)

            if not ready:
                # Circular dependency detected
                raise ValueError(f"Circular dependency in operations: {remaining}")

            batches.append(ready)
            for op in ready:
                remaining.remove(op.op_id)

        return batches

    async def execute(
        self,
        tool_executor: Callable[[str, Dict], Awaitable[Any]],
    ) -> ChainResult:
        """
        Execute the tool chain.

        Args:
            tool_executor: Async function to execute tools (tool_name, params) -> result

        Returns:
            ChainResult with execution status
        """
        start_time = time.time()
        self._status = ChainStatus.RUNNING
        error = None

        try:
            # Get execution order
            batches = self._get_execution_order()

            # Execute batches
            for batch in batches:
                if self.parallel_execution and len(batch) > 1:
                    # Execute batch in parallel
                    results = await asyncio.gather(
                        *[self._execute_operation(op, tool_executor) for op in batch],
                        return_exceptions=True
                    )

                    # Check for failures
                    for op, result in zip(batch, results):
                        if isinstance(result, Exception):
                            op.error = str(result)
                            raise result
                else:
                    # Execute sequentially
                    for op in batch:
                        await self._execute_operation(op, tool_executor)

            self._status = ChainStatus.COMPLETED

        except Exception as e:
            error = str(e)
            self._status = ChainStatus.FAILED
            logger.error(f"Chain {self.chain_id} failed: {error}")

            if self.rollback_on_failure:
                await self._rollback()

        end_time = time.time()

        return ChainResult(
            chain_id=self.chain_id,
            status=self._status,
            operations=self._operations,
            start_time=start_time,
            end_time=end_time,
            rolled_back=self._status == ChainStatus.ROLLED_BACK,
            error=error,
        )

    async def _execute_operation(
        self,
        op: ToolOperation,
        tool_executor: Callable[[str, Dict], Awaitable[Any]],
    ) -> Any:
        """Execute a single operation."""
        op.start_time = time.time()

        try:
            result = await tool_executor(op.tool_name, op.parameters)
            op.result = result
            op.executed = True
            self._executed_ops.append(op)

            logger.debug(f"Operation {op.op_id} ({op.tool_name}) completed")
            return result

        except Exception as e:
            op.error = str(e)
            op.executed = True
            self._executed_ops.append(op)
            logger.error(f"Operation {op.op_id} failed: {e}")
            raise

        finally:
            op.end_time = time.time()

    async def _rollback(self) -> bool:
        """Rollback executed operations in reverse order."""
        logger.info(f"Rolling back chain {self.chain_id}")

        success = True
        for op in reversed(self._executed_ops):
            try:
                if op.rollback_fn:
                    await op.rollback_fn()
                    logger.debug(f"Rolled back operation {op.op_id}")
                elif op.tool_name in ("write_file", "edit_file"):
                    # Use undo manager for file operations
                    undo_result = self._undo_manager.undo()
                    if undo_result and not undo_result.success:
                        logger.warning(f"Failed to undo {op.op_id}")
                        success = False
            except Exception as e:
                logger.error(f"Rollback failed for {op.op_id}: {e}")
                success = False

        self._status = ChainStatus.ROLLED_BACK if success else ChainStatus.FAILED
        return success

    def clear(self) -> None:
        """Clear all operations from the chain."""
        self._operations.clear()
        self._executed_ops.clear()
        self._op_counter = 0
        self._status = ChainStatus.PENDING


@asynccontextmanager
async def atomic_transaction(
    tool_executor: Callable[[str, Dict], Awaitable[Any]],
    rollback_on_failure: bool = True,
):
    """
    Context manager for atomic tool transactions.

    Usage:
        async with atomic_transaction(executor) as chain:
            chain.add_operation("write_file", {...})
            chain.add_operation("run_tests", {...})
        # Auto-executes on exit, rolls back on exception
    """
    chain = AtomicToolChain(rollback_on_failure=rollback_on_failure)

    try:
        yield chain
        result = await chain.execute(tool_executor)
        if result.status == ChainStatus.FAILED:
            raise RuntimeError(f"Transaction failed: {result.error}")
    except Exception:
        if chain._status == ChainStatus.RUNNING:
            await chain._rollback()
        raise


# Export all public symbols
__all__ = [
    'ChainStatus',
    'ToolDependency',
    'ToolOperation',
    'ChainResult',
    'AtomicToolChain',
    'atomic_transaction',
]
