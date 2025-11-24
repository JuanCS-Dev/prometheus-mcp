"""
Atomic File Operations - All-or-Nothing File Writes
Pipeline de Diamante - Camada 3: EXECUTION SANDBOX

Addresses: ISSUE-002, ISSUE-004, ISSUE-057, ISSUE-058, ISSUE-066

Implements atomic file operations:
- Write-to-temp + rename pattern
- fsync for durability
- Rollback on failure
- File locking for concurrent access
- Checksum verification

Design Philosophy:
- All operations are atomic (all-or-nothing)
- Files are never in inconsistent state
- Concurrent access is safe
- Recovery is always possible

Based on:
- POSIX atomic file operations best practices
- Database ACID principles applied to files
- SQLite's atomic commit pattern
"""

from __future__ import annotations

import os
import sys
import hashlib
import tempfile
import shutil
import time
import json
from typing import Any, Callable, Dict, List, Optional, Tuple, Union
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum, auto
from contextlib import contextmanager
import logging

# Try to import filelock, graceful degradation if not available
try:
    from filelock import FileLock, Timeout as LockTimeout
    HAS_FILELOCK = True
except ImportError:
    HAS_FILELOCK = False
    FileLock = None
    LockTimeout = Exception

logger = logging.getLogger(__name__)


class AtomicOpType(Enum):
    """Types of atomic operations."""
    WRITE = auto()
    EDIT = auto()
    DELETE = auto()
    MOVE = auto()
    COPY = auto()


@dataclass
class OperationCheckpoint:
    """Checkpoint for rollback capability."""
    operation_id: str
    op_type: AtomicOpType
    target_path: str
    backup_path: Optional[str] = None
    temp_path: Optional[str] = None
    original_checksum: Optional[str] = None
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize checkpoint to dictionary."""
        return {
            "operation_id": self.operation_id,
            "op_type": self.op_type.name,
            "target_path": self.target_path,
            "backup_path": self.backup_path,
            "temp_path": self.temp_path,
            "original_checksum": self.original_checksum,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "OperationCheckpoint":
        """Deserialize checkpoint from dictionary."""
        return cls(
            operation_id=data["operation_id"],
            op_type=AtomicOpType[data["op_type"]],
            target_path=data["target_path"],
            backup_path=data.get("backup_path"),
            temp_path=data.get("temp_path"),
            original_checksum=data.get("original_checksum"),
            timestamp=data.get("timestamp", time.time()),
            metadata=data.get("metadata", {}),
        )


@dataclass
class AtomicResult:
    """Result of an atomic operation."""
    success: bool
    path: str
    checksum: Optional[str] = None
    backup_path: Optional[str] = None
    error: Optional[str] = None
    checkpoint: Optional[OperationCheckpoint] = None
    duration_ms: float = 0.0

    @classmethod
    def failure(cls, path: str, error: str) -> "AtomicResult":
        """Create a failure result."""
        return cls(success=False, path=path, error=error)


class AtomicFileOps:
    """
    Atomic file operations with rollback support.

    All operations follow the write-to-temp + rename pattern:
    1. Create temp file in same directory
    2. Write content to temp file
    3. fsync to ensure data is on disk
    4. Atomic rename temp -> target
    5. On failure, clean up temp file

    Usage:
        ops = AtomicFileOps()
        result = ops.write_atomic("/path/to/file", "content")
        if not result.success:
            print(f"Error: {result.error}")
    """

    # Default backup directory
    BACKUP_DIR = ".qwen_atomic_backups"

    # Lock timeout in seconds
    LOCK_TIMEOUT = 30

    def __init__(
        self,
        backup_dir: Optional[str] = None,
        enable_checkpoints: bool = True,
        enable_locking: bool = True,
        sync_on_write: bool = True,
    ):
        """
        Initialize AtomicFileOps.

        Args:
            backup_dir: Directory for backups (default: .qwen_atomic_backups)
            enable_checkpoints: Enable checkpointing for rollback
            enable_locking: Enable file locking for concurrent access
            sync_on_write: Call fsync after writes (slower but safer)
        """
        self.backup_dir = Path(backup_dir or self.BACKUP_DIR)
        self.enable_checkpoints = enable_checkpoints
        self.enable_locking = enable_locking and HAS_FILELOCK
        self.sync_on_write = sync_on_write
        self.checkpoints: Dict[str, OperationCheckpoint] = {}
        self._operation_counter = 0

    def _generate_op_id(self) -> str:
        """Generate unique operation ID."""
        self._operation_counter += 1
        return f"op_{int(time.time() * 1000)}_{self._operation_counter}"

    def _compute_checksum(self, content: Union[str, bytes]) -> str:
        """Compute SHA256 checksum of content."""
        if isinstance(content, str):
            content = content.encode('utf-8')
        return hashlib.sha256(content).hexdigest()

    def _get_lock_path(self, path: Path) -> Path:
        """Get lock file path for a given file."""
        return path.parent / f".{path.name}.lock"

    @contextmanager
    def _file_lock(self, path: Path, timeout: float = None):
        """Context manager for file locking."""
        if not self.enable_locking:
            yield
            return

        lock_path = self._get_lock_path(path)
        lock = FileLock(str(lock_path), timeout=timeout or self.LOCK_TIMEOUT)

        try:
            lock.acquire()
            yield
        except LockTimeout:
            raise TimeoutError(f"Could not acquire lock for {path} within {timeout}s")
        finally:
            try:
                lock.release()
            except Exception:
                pass

    def _ensure_backup_dir(self) -> Path:
        """Ensure backup directory exists."""
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        return self.backup_dir

    def _create_backup(self, path: Path) -> Optional[Path]:
        """Create backup of existing file."""
        if not path.exists():
            return None

        backup_dir = self._ensure_backup_dir()
        timestamp = int(time.time() * 1000)
        backup_name = f"{path.name}.{timestamp}.bak"
        backup_path = backup_dir / backup_name

        shutil.copy2(str(path), str(backup_path))
        return backup_path

    def _sync_file(self, fd: int) -> None:
        """Sync file descriptor to disk."""
        if not self.sync_on_write:
            return

        try:
            os.fsync(fd)
        except OSError:
            pass  # Best effort sync

    def _sync_directory(self, path: Path) -> None:
        """Sync directory to ensure rename is durable."""
        if not self.sync_on_write:
            return

        try:
            dir_fd = os.open(str(path.parent), os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(dir_fd)
            finally:
                os.close(dir_fd)
        except (OSError, AttributeError):
            pass  # Best effort, not available on all platforms

    def write_atomic(
        self,
        path: Union[str, Path],
        content: Union[str, bytes],
        encoding: str = 'utf-8',
        create_dirs: bool = True,
        create_backup: bool = True,
    ) -> AtomicResult:
        """
        Write file atomically using temp + rename pattern.

        Args:
            path: Target file path
            content: Content to write
            encoding: Text encoding (for string content)
            create_dirs: Create parent directories if needed
            create_backup: Create backup of existing file

        Returns:
            AtomicResult with operation status
        """
        start_time = time.time()
        path = Path(path)
        op_id = self._generate_op_id()

        # Ensure parent directory exists
        if create_dirs:
            path.parent.mkdir(parents=True, exist_ok=True)
        elif not path.parent.exists():
            return AtomicResult.failure(
                str(path),
                f"Parent directory does not exist: {path.parent}"
            )

        # Create checkpoint
        checkpoint = OperationCheckpoint(
            operation_id=op_id,
            op_type=AtomicOpType.WRITE,
            target_path=str(path),
        )

        # Compute checksum
        if isinstance(content, str):
            content_bytes = content.encode(encoding)
        else:
            content_bytes = content
        checksum = self._compute_checksum(content_bytes)

        temp_path = None
        backup_path = None

        try:
            with self._file_lock(path):
                # Store original checksum if file exists
                if path.exists():
                    original_content = path.read_bytes()
                    checkpoint.original_checksum = self._compute_checksum(original_content)

                    if create_backup:
                        backup_path = self._create_backup(path)
                        checkpoint.backup_path = str(backup_path) if backup_path else None

                # Create temp file in same directory (important for atomic rename)
                fd, temp_path = tempfile.mkstemp(
                    dir=str(path.parent),
                    prefix=f".{path.name}.",
                    suffix=".tmp"
                )

                checkpoint.temp_path = temp_path

                try:
                    # Write content
                    os.write(fd, content_bytes)

                    # Sync to disk
                    self._sync_file(fd)

                finally:
                    os.close(fd)

                # Atomic rename (POSIX guarantees this is atomic)
                os.replace(temp_path, str(path))
                temp_path = None  # Don't cleanup on success

                # Sync directory
                self._sync_directory(path)

            duration = (time.time() - start_time) * 1000

            # Store checkpoint
            if self.enable_checkpoints:
                self.checkpoints[op_id] = checkpoint

            return AtomicResult(
                success=True,
                path=str(path),
                checksum=checksum,
                backup_path=str(backup_path) if backup_path else None,
                checkpoint=checkpoint,
                duration_ms=duration,
            )

        except Exception as e:
            # Cleanup temp file on failure
            if temp_path and os.path.exists(temp_path):
                try:
                    os.unlink(temp_path)
                except OSError:
                    pass

            return AtomicResult.failure(str(path), str(e))

    def edit_atomic(
        self,
        path: Union[str, Path],
        edit_func: Callable[[str], str],
        encoding: str = 'utf-8',
        create_backup: bool = True,
    ) -> AtomicResult:
        """
        Edit file atomically using read-modify-write pattern.

        Args:
            path: Target file path
            edit_func: Function that transforms content
            encoding: Text encoding
            create_backup: Create backup before editing

        Returns:
            AtomicResult with operation status
        """
        path = Path(path)

        if not path.exists():
            return AtomicResult.failure(str(path), f"File not found: {path}")

        try:
            with self._file_lock(path):
                # Read current content
                original = path.read_text(encoding=encoding)

                # Apply edit function
                modified = edit_func(original)

                # Write atomically
                return self.write_atomic(
                    path, modified,
                    encoding=encoding,
                    create_dirs=False,
                    create_backup=create_backup
                )

        except Exception as e:
            return AtomicResult.failure(str(path), str(e))

    def delete_atomic(
        self,
        path: Union[str, Path],
        create_backup: bool = True,
    ) -> AtomicResult:
        """
        Delete file atomically with backup.

        Args:
            path: Target file path
            create_backup: Create backup before deletion

        Returns:
            AtomicResult with operation status
        """
        start_time = time.time()
        path = Path(path)
        op_id = self._generate_op_id()

        if not path.exists():
            return AtomicResult.failure(str(path), f"File not found: {path}")

        checkpoint = OperationCheckpoint(
            operation_id=op_id,
            op_type=AtomicOpType.DELETE,
            target_path=str(path),
        )

        backup_path = None

        try:
            with self._file_lock(path):
                # Store original checksum
                original_content = path.read_bytes()
                checkpoint.original_checksum = self._compute_checksum(original_content)

                # Create backup
                if create_backup:
                    backup_path = self._create_backup(path)
                    checkpoint.backup_path = str(backup_path) if backup_path else None

                # Delete file
                if path.is_dir():
                    shutil.rmtree(str(path))
                else:
                    path.unlink()

            duration = (time.time() - start_time) * 1000

            # Store checkpoint
            if self.enable_checkpoints:
                self.checkpoints[op_id] = checkpoint

            return AtomicResult(
                success=True,
                path=str(path),
                backup_path=str(backup_path) if backup_path else None,
                checkpoint=checkpoint,
                duration_ms=duration,
            )

        except Exception as e:
            return AtomicResult.failure(str(path), str(e))

    def move_atomic(
        self,
        source: Union[str, Path],
        dest: Union[str, Path],
        create_backup: bool = True,
    ) -> AtomicResult:
        """
        Move file atomically.

        Args:
            source: Source file path
            dest: Destination file path
            create_backup: Create backup if dest exists

        Returns:
            AtomicResult with operation status
        """
        start_time = time.time()
        source = Path(source)
        dest = Path(dest)
        op_id = self._generate_op_id()

        if not source.exists():
            return AtomicResult.failure(str(source), f"Source not found: {source}")

        checkpoint = OperationCheckpoint(
            operation_id=op_id,
            op_type=AtomicOpType.MOVE,
            target_path=str(dest),
            metadata={"source": str(source)},
        )

        backup_path = None

        try:
            # Lock both source and dest
            with self._file_lock(source):
                with self._file_lock(dest):
                    # Backup dest if it exists
                    if dest.exists() and create_backup:
                        backup_path = self._create_backup(dest)
                        checkpoint.backup_path = str(backup_path) if backup_path else None

                    # Ensure dest parent exists
                    dest.parent.mkdir(parents=True, exist_ok=True)

                    # Try atomic rename first
                    try:
                        os.replace(str(source), str(dest))
                    except OSError:
                        # Cross-device move: copy + delete
                        shutil.copy2(str(source), str(dest))
                        source.unlink()

            duration = (time.time() - start_time) * 1000

            # Store checkpoint
            if self.enable_checkpoints:
                self.checkpoints[op_id] = checkpoint

            return AtomicResult(
                success=True,
                path=str(dest),
                backup_path=str(backup_path) if backup_path else None,
                checkpoint=checkpoint,
                duration_ms=duration,
            )

        except Exception as e:
            return AtomicResult.failure(str(dest), str(e))

    def rollback(self, checkpoint: OperationCheckpoint) -> AtomicResult:
        """
        Rollback an operation using its checkpoint.

        Args:
            checkpoint: Checkpoint from previous operation

        Returns:
            AtomicResult with rollback status
        """
        try:
            target = Path(checkpoint.target_path)

            if checkpoint.op_type == AtomicOpType.WRITE:
                # Restore from backup or delete new file
                if checkpoint.backup_path:
                    backup = Path(checkpoint.backup_path)
                    if backup.exists():
                        shutil.copy2(str(backup), str(target))
                        return AtomicResult(success=True, path=str(target))
                elif checkpoint.original_checksum is None:
                    # File didn't exist before, delete it
                    if target.exists():
                        target.unlink()
                        return AtomicResult(success=True, path=str(target))

            elif checkpoint.op_type == AtomicOpType.DELETE:
                # Restore from backup
                if checkpoint.backup_path:
                    backup = Path(checkpoint.backup_path)
                    if backup.exists():
                        shutil.copy2(str(backup), str(target))
                        return AtomicResult(success=True, path=str(target))

            elif checkpoint.op_type == AtomicOpType.MOVE:
                # Move back
                source = checkpoint.metadata.get("source")
                if source:
                    if target.exists():
                        shutil.move(str(target), source)
                        return AtomicResult(success=True, path=source)

            return AtomicResult.failure(
                str(target),
                "Could not rollback: no backup available"
            )

        except Exception as e:
            return AtomicResult.failure(
                checkpoint.target_path,
                f"Rollback failed: {e}"
            )

    def verify_checksum(self, path: Union[str, Path], expected: str) -> bool:
        """Verify file checksum matches expected."""
        path = Path(path)
        if not path.exists():
            return False

        actual = self._compute_checksum(path.read_bytes())
        return actual == expected

    def cleanup_backups(self, max_age_hours: float = 24) -> int:
        """
        Clean up old backup files.

        Args:
            max_age_hours: Maximum age of backups to keep

        Returns:
            Number of files deleted
        """
        if not self.backup_dir.exists():
            return 0

        max_age_seconds = max_age_hours * 3600
        now = time.time()
        deleted = 0

        for backup_file in self.backup_dir.iterdir():
            if backup_file.is_file():
                age = now - backup_file.stat().st_mtime
                if age > max_age_seconds:
                    try:
                        backup_file.unlink()
                        deleted += 1
                    except OSError:
                        pass

        return deleted


# Convenience functions

def write_file_atomic(
    path: Union[str, Path],
    content: Union[str, bytes],
    **kwargs
) -> AtomicResult:
    """Write file atomically."""
    return AtomicFileOps().write_atomic(path, content, **kwargs)


def edit_file_atomic(
    path: Union[str, Path],
    edit_func: Callable[[str], str],
    **kwargs
) -> AtomicResult:
    """Edit file atomically."""
    return AtomicFileOps().edit_atomic(path, edit_func, **kwargs)


def delete_file_atomic(
    path: Union[str, Path],
    **kwargs
) -> AtomicResult:
    """Delete file atomically with backup."""
    return AtomicFileOps().delete_atomic(path, **kwargs)


def move_file_atomic(
    source: Union[str, Path],
    dest: Union[str, Path],
    **kwargs
) -> AtomicResult:
    """Move file atomically."""
    return AtomicFileOps().move_atomic(source, dest, **kwargs)


# Export all public symbols
__all__ = [
    'AtomicOpType',
    'OperationCheckpoint',
    'AtomicResult',
    'AtomicFileOps',
    'write_file_atomic',
    'edit_file_atomic',
    'delete_file_atomic',
    'move_file_atomic',
]
