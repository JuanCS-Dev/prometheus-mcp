"""
UndoManager - Stack-based Undo/Redo System
Pipeline de Diamante - Camada 3: EXECUTION SANDBOX

Addresses: ISSUE-030 (Undo support)

Implements comprehensive undo/redo:
- Stack-based operation history
- Branching support (redo cleared on new action)
- Memory-efficient snapshots
- Operation descriptions for timeline view
- Automatic compaction of old operations

Design Philosophy:
- Every destructive operation can be undone
- Memory-bounded history (configurable)
- User-friendly operation descriptions
- Timeline visualization support
"""

from __future__ import annotations

import os
import json
import time
import shutil
import hashlib
from typing import Any, Callable, Dict, List, Optional, TypeVar
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum
from contextlib import contextmanager
import logging

from .atomic_ops import AtomicFileOps

logger = logging.getLogger(__name__)

T = TypeVar('T')


class OperationType(Enum):
    """Types of undoable operations."""
    FILE_CREATE = "file_create"
    FILE_EDIT = "file_edit"
    FILE_DELETE = "file_delete"
    FILE_MOVE = "file_move"
    FILE_RENAME = "file_rename"
    DIRECTORY_CREATE = "dir_create"
    DIRECTORY_DELETE = "dir_delete"
    GIT_COMMIT = "git_commit"
    GIT_BRANCH = "git_branch"
    COMMAND_EXEC = "command_exec"
    BATCH = "batch"  # Multiple operations as one


@dataclass
class UndoableOperation:
    """A single undoable operation."""
    id: str
    op_type: OperationType
    description: str
    timestamp: float

    # For file operations
    target_path: Optional[str] = None
    original_content: Optional[str] = None
    new_content: Optional[str] = None
    backup_path: Optional[str] = None

    # For move/rename
    source_path: Optional[str] = None
    dest_path: Optional[str] = None

    # For batch operations
    sub_operations: List["UndoableOperation"] = field(default_factory=list)

    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Undo/redo functions (if custom)
    _undo_func: Optional[Callable] = field(default=None, repr=False)
    _redo_func: Optional[Callable] = field(default=None, repr=False)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize operation to dictionary."""
        return {
            "id": self.id,
            "op_type": self.op_type.value,
            "description": self.description,
            "timestamp": self.timestamp,
            "target_path": self.target_path,
            "backup_path": self.backup_path,
            "source_path": self.source_path,
            "dest_path": self.dest_path,
            "sub_operations": [op.to_dict() for op in self.sub_operations],
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "UndoableOperation":
        """Deserialize operation from dictionary."""
        return cls(
            id=data["id"],
            op_type=OperationType(data["op_type"]),
            description=data["description"],
            timestamp=data["timestamp"],
            target_path=data.get("target_path"),
            backup_path=data.get("backup_path"),
            source_path=data.get("source_path"),
            dest_path=data.get("dest_path"),
            sub_operations=[cls.from_dict(op) for op in data.get("sub_operations", [])],
            metadata=data.get("metadata", {}),
        )


@dataclass
class UndoResult:
    """Result of an undo/redo operation."""
    success: bool
    operation: UndoableOperation
    message: str
    error: Optional[str] = None

    @classmethod
    def success_result(cls, op: UndoableOperation, message: str) -> "UndoResult":
        """Create successful result."""
        return cls(success=True, operation=op, message=message)

    @classmethod
    def failure_result(cls, op: UndoableOperation, error: str) -> "UndoResult":
        """Create failure result."""
        return cls(success=False, operation=op, message="", error=error)


class UndoManager:
    """
    Stack-based undo/redo manager.

    Features:
    - Bounded history stack (default 100 operations)
    - Redo stack cleared on new operation
    - Branching support for complex workflows
    - Persistent state for crash recovery
    - Memory-efficient snapshot storage

    Usage:
        manager = UndoManager()

        # Record an operation
        manager.record_file_edit("/path/to/file", "original", "modified")

        # Undo
        result = manager.undo()

        # Redo
        result = manager.redo()

        # Get history
        for op in manager.get_history():
            print(f"{op.description} at {op.timestamp}")
    """

    DEFAULT_MAX_SIZE = 100
    SNAPSHOT_DIR = ".qwen_undo_snapshots"
    STATE_FILE = ".qwen_undo_state.json"

    def __init__(
        self,
        max_size: int = DEFAULT_MAX_SIZE,
        snapshot_dir: Optional[str] = None,
        persist_state: bool = True,
        working_dir: Optional[str] = None,
    ):
        """
        Initialize UndoManager.

        Args:
            max_size: Maximum number of operations in history
            snapshot_dir: Directory for file snapshots
            persist_state: Save state to disk for crash recovery
            working_dir: Working directory (default: cwd)
        """
        self.max_size = max_size
        self.working_dir = Path(working_dir or os.getcwd())
        self.snapshot_dir = self.working_dir / (snapshot_dir or self.SNAPSHOT_DIR)
        self.persist_state = persist_state

        self._undo_stack: List[UndoableOperation] = []
        self._redo_stack: List[UndoableOperation] = []
        self._operation_counter = 0

        self._atomic_ops = AtomicFileOps()

        # Load persisted state
        if persist_state:
            self._load_state()

    def _generate_op_id(self) -> str:
        """Generate unique operation ID."""
        self._operation_counter += 1
        return f"undo_{int(time.time() * 1000)}_{self._operation_counter}"

    def _ensure_snapshot_dir(self) -> Path:
        """Ensure snapshot directory exists."""
        self.snapshot_dir.mkdir(parents=True, exist_ok=True)
        return self.snapshot_dir

    def _save_snapshot(self, content: str, op_id: str) -> str:
        """Save content snapshot to disk."""
        snapshot_dir = self._ensure_snapshot_dir()

        # Use hash for deduplication
        content_hash = hashlib.sha256(content.encode()).hexdigest()[:16]
        snapshot_path = snapshot_dir / f"{op_id}_{content_hash}.snapshot"

        snapshot_path.write_text(content)
        return str(snapshot_path)

    def _load_snapshot(self, path: str) -> Optional[str]:
        """Load content from snapshot."""
        try:
            return Path(path).read_text()
        except Exception:
            return None

    def _save_state(self) -> None:
        """Save manager state to disk."""
        if not self.persist_state:
            return

        state = {
            "undo_stack": [op.to_dict() for op in self._undo_stack],
            "redo_stack": [op.to_dict() for op in self._redo_stack],
            "counter": self._operation_counter,
            "timestamp": time.time(),
        }

        state_path = self.working_dir / self.STATE_FILE
        try:
            state_path.write_text(json.dumps(state, indent=2))
        except Exception as e:
            logger.warning(f"Could not save undo state: {e}")

    def _load_state(self) -> None:
        """Load manager state from disk."""
        state_path = self.working_dir / self.STATE_FILE

        if not state_path.exists():
            return

        try:
            state = json.loads(state_path.read_text())
            self._undo_stack = [
                UndoableOperation.from_dict(op)
                for op in state.get("undo_stack", [])
            ]
            self._redo_stack = [
                UndoableOperation.from_dict(op)
                for op in state.get("redo_stack", [])
            ]
            self._operation_counter = state.get("counter", 0)
        except Exception as e:
            logger.warning(f"Could not load undo state: {e}")

    def _push_operation(self, operation: UndoableOperation) -> None:
        """Push operation to undo stack."""
        # Clear redo stack (branching: new action clears redo)
        self._redo_stack.clear()

        # Add to undo stack
        self._undo_stack.append(operation)

        # Enforce max size
        while len(self._undo_stack) > self.max_size:
            removed = self._undo_stack.pop(0)
            # Clean up snapshot if exists
            if removed.backup_path and os.path.exists(removed.backup_path):
                try:
                    os.unlink(removed.backup_path)
                except Exception:
                    pass

        # Persist state
        self._save_state()

    def record_file_create(
        self,
        path: str,
        content: str,
        description: Optional[str] = None,
    ) -> UndoableOperation:
        """Record file creation operation."""
        op = UndoableOperation(
            id=self._generate_op_id(),
            op_type=OperationType.FILE_CREATE,
            description=description or f"Create {Path(path).name}",
            timestamp=time.time(),
            target_path=path,
            new_content=content,
        )

        self._push_operation(op)
        return op

    def record_file_edit(
        self,
        path: str,
        original_content: str,
        new_content: str,
        description: Optional[str] = None,
    ) -> UndoableOperation:
        """Record file edit operation."""
        # Save original content as snapshot
        op_id = self._generate_op_id()
        backup_path = self._save_snapshot(original_content, op_id)

        op = UndoableOperation(
            id=op_id,
            op_type=OperationType.FILE_EDIT,
            description=description or f"Edit {Path(path).name}",
            timestamp=time.time(),
            target_path=path,
            original_content=original_content,
            new_content=new_content,
            backup_path=backup_path,
        )

        self._push_operation(op)
        return op

    def record_file_delete(
        self,
        path: str,
        original_content: str,
        description: Optional[str] = None,
    ) -> UndoableOperation:
        """Record file deletion operation."""
        op_id = self._generate_op_id()
        backup_path = self._save_snapshot(original_content, op_id)

        op = UndoableOperation(
            id=op_id,
            op_type=OperationType.FILE_DELETE,
            description=description or f"Delete {Path(path).name}",
            timestamp=time.time(),
            target_path=path,
            original_content=original_content,
            backup_path=backup_path,
        )

        self._push_operation(op)
        return op

    def record_file_move(
        self,
        source: str,
        dest: str,
        description: Optional[str] = None,
    ) -> UndoableOperation:
        """Record file move/rename operation."""
        op = UndoableOperation(
            id=self._generate_op_id(),
            op_type=OperationType.FILE_MOVE,
            description=description or f"Move {Path(source).name} → {Path(dest).name}",
            timestamp=time.time(),
            source_path=source,
            dest_path=dest,
        )

        self._push_operation(op)
        return op

    def record_batch(
        self,
        operations: List[UndoableOperation],
        description: str,
    ) -> UndoableOperation:
        """Record multiple operations as a single undoable unit."""
        op = UndoableOperation(
            id=self._generate_op_id(),
            op_type=OperationType.BATCH,
            description=description,
            timestamp=time.time(),
            sub_operations=operations,
        )

        self._push_operation(op)
        return op

    def record_custom(
        self,
        description: str,
        undo_func: Callable[[], bool],
        redo_func: Callable[[], bool],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> UndoableOperation:
        """Record a custom operation with undo/redo functions."""
        op = UndoableOperation(
            id=self._generate_op_id(),
            op_type=OperationType.COMMAND_EXEC,
            description=description,
            timestamp=time.time(),
            metadata=metadata or {},
            _undo_func=undo_func,
            _redo_func=redo_func,
        )

        self._push_operation(op)
        return op

    def _execute_undo(self, op: UndoableOperation) -> UndoResult:
        """Execute undo for a single operation."""
        try:
            if op._undo_func:
                # Custom undo function
                success = op._undo_func()
                if success:
                    return UndoResult.success_result(op, f"Undid: {op.description}")
                else:
                    return UndoResult.failure_result(op, "Custom undo failed")

            if op.op_type == OperationType.FILE_CREATE:
                # Undo create = delete
                path = Path(op.target_path)
                if path.exists():
                    path.unlink()
                return UndoResult.success_result(op, f"Undid: {op.description}")

            elif op.op_type == OperationType.FILE_EDIT:
                # Undo edit = restore original
                original = self._load_snapshot(op.backup_path) or op.original_content
                if original is not None:
                    result = self._atomic_ops.write_atomic(
                        op.target_path, original, create_backup=False
                    )
                    if result.success:
                        return UndoResult.success_result(op, f"Undid: {op.description}")
                    else:
                        return UndoResult.failure_result(op, result.error or "Write failed")
                return UndoResult.failure_result(op, "No original content available")

            elif op.op_type == OperationType.FILE_DELETE:
                # Undo delete = restore file
                original = self._load_snapshot(op.backup_path) or op.original_content
                if original is not None:
                    result = self._atomic_ops.write_atomic(
                        op.target_path, original, create_backup=False
                    )
                    if result.success:
                        return UndoResult.success_result(op, f"Undid: {op.description}")
                    else:
                        return UndoResult.failure_result(op, result.error or "Write failed")
                return UndoResult.failure_result(op, "No backup content available")

            elif op.op_type == OperationType.FILE_MOVE:
                # Undo move = move back
                result = self._atomic_ops.move_atomic(
                    op.dest_path, op.source_path, create_backup=False
                )
                if result.success:
                    return UndoResult.success_result(op, f"Undid: {op.description}")
                else:
                    return UndoResult.failure_result(op, result.error or "Move failed")

            elif op.op_type == OperationType.BATCH:
                # Undo batch = undo all sub-operations in reverse
                errors = []
                for sub_op in reversed(op.sub_operations):
                    sub_result = self._execute_undo(sub_op)
                    if not sub_result.success:
                        errors.append(sub_result.error)

                if errors:
                    return UndoResult.failure_result(op, "; ".join(errors))
                return UndoResult.success_result(op, f"Undid: {op.description}")

            return UndoResult.failure_result(op, f"Unknown operation type: {op.op_type}")

        except Exception as e:
            return UndoResult.failure_result(op, str(e))

    def _execute_redo(self, op: UndoableOperation) -> UndoResult:
        """Execute redo for a single operation."""
        try:
            if op._redo_func:
                # Custom redo function
                success = op._redo_func()
                if success:
                    return UndoResult.success_result(op, f"Redid: {op.description}")
                else:
                    return UndoResult.failure_result(op, "Custom redo failed")

            if op.op_type == OperationType.FILE_CREATE:
                # Redo create = create again
                result = self._atomic_ops.write_atomic(
                    op.target_path, op.new_content, create_backup=False
                )
                if result.success:
                    return UndoResult.success_result(op, f"Redid: {op.description}")
                else:
                    return UndoResult.failure_result(op, result.error or "Write failed")

            elif op.op_type == OperationType.FILE_EDIT:
                # Redo edit = apply new content
                result = self._atomic_ops.write_atomic(
                    op.target_path, op.new_content, create_backup=False
                )
                if result.success:
                    return UndoResult.success_result(op, f"Redid: {op.description}")
                else:
                    return UndoResult.failure_result(op, result.error or "Write failed")

            elif op.op_type == OperationType.FILE_DELETE:
                # Redo delete = delete again
                path = Path(op.target_path)
                if path.exists():
                    path.unlink()
                return UndoResult.success_result(op, f"Redid: {op.description}")

            elif op.op_type == OperationType.FILE_MOVE:
                # Redo move = move again
                result = self._atomic_ops.move_atomic(
                    op.source_path, op.dest_path, create_backup=False
                )
                if result.success:
                    return UndoResult.success_result(op, f"Redid: {op.description}")
                else:
                    return UndoResult.failure_result(op, result.error or "Move failed")

            elif op.op_type == OperationType.BATCH:
                # Redo batch = redo all sub-operations in order
                errors = []
                for sub_op in op.sub_operations:
                    sub_result = self._execute_redo(sub_op)
                    if not sub_result.success:
                        errors.append(sub_result.error)

                if errors:
                    return UndoResult.failure_result(op, "; ".join(errors))
                return UndoResult.success_result(op, f"Redid: {op.description}")

            return UndoResult.failure_result(op, f"Unknown operation type: {op.op_type}")

        except Exception as e:
            return UndoResult.failure_result(op, str(e))

    def undo(self) -> Optional[UndoResult]:
        """
        Undo the most recent operation.

        Returns:
            UndoResult if there was something to undo, None otherwise
        """
        if not self._undo_stack:
            return None

        op = self._undo_stack.pop()
        result = self._execute_undo(op)

        if result.success:
            self._redo_stack.append(op)

        self._save_state()
        return result

    def redo(self) -> Optional[UndoResult]:
        """
        Redo the most recently undone operation.

        Returns:
            UndoResult if there was something to redo, None otherwise
        """
        if not self._redo_stack:
            return None

        op = self._redo_stack.pop()
        result = self._execute_redo(op)

        if result.success:
            self._undo_stack.append(op)

        self._save_state()
        return result

    def can_undo(self) -> bool:
        """Check if undo is available."""
        return len(self._undo_stack) > 0

    def can_redo(self) -> bool:
        """Check if redo is available."""
        return len(self._redo_stack) > 0

    def get_history(self, limit: int = 10) -> List[UndoableOperation]:
        """
        Get recent operation history.

        Args:
            limit: Maximum number of operations to return

        Returns:
            List of recent operations (newest first)
        """
        return list(reversed(self._undo_stack[-limit:]))

    def get_redo_stack(self, limit: int = 10) -> List[UndoableOperation]:
        """Get redo stack."""
        return list(reversed(self._redo_stack[-limit:]))

    def clear_history(self) -> None:
        """Clear all undo/redo history."""
        self._undo_stack.clear()
        self._redo_stack.clear()
        self._save_state()

        # Clean up snapshots
        if self.snapshot_dir.exists():
            shutil.rmtree(str(self.snapshot_dir))

    @contextmanager
    def batch_operations(self, description: str):
        """
        Context manager for batch operations.

        All operations within this context will be grouped as one undoable unit.

        Usage:
            with manager.batch_operations("Refactor module"):
                manager.record_file_edit(...)
                manager.record_file_edit(...)
        """
        batch_ops: List[UndoableOperation] = []
        original_push = self._push_operation

        def batch_push(op: UndoableOperation) -> None:
            batch_ops.append(op)

        self._push_operation = batch_push

        try:
            yield
        finally:
            self._push_operation = original_push
            if batch_ops:
                self.record_batch(batch_ops, description)


# Global instance for convenience
_default_manager: Optional[UndoManager] = None


def get_undo_manager() -> UndoManager:
    """Get the default undo manager instance."""
    global _default_manager
    if _default_manager is None:
        _default_manager = UndoManager()
    return _default_manager


# Convenience functions

def undo() -> Optional[UndoResult]:
    """Undo the most recent operation."""
    return get_undo_manager().undo()


def redo() -> Optional[UndoResult]:
    """Redo the most recently undone operation."""
    return get_undo_manager().redo()


def can_undo() -> bool:
    """Check if undo is available."""
    return get_undo_manager().can_undo()


def can_redo() -> bool:
    """Check if redo is available."""
    return get_undo_manager().can_redo()


# Export all public symbols
__all__ = [
    'OperationType',
    'UndoableOperation',
    'UndoResult',
    'UndoManager',
    'get_undo_manager',
    'undo',
    'redo',
    'can_undo',
    'can_redo',
]
