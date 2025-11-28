"""
File Tools - Glob, LS, MultiEdit
================================

File system operations for Claude Code parity.

Contains:
- GlobTool: Fast file pattern matching
- LSTool: Directory listing with details
- MultiEditTool: Atomic multiple file edits

Author: JuanCS Dev
Date: 2025-11-27
"""

from __future__ import annotations

import fnmatch
import logging
from pathlib import Path
from typing import List

from jdev_cli.tools.base import Tool, ToolCategory, ToolResult

logger = logging.getLogger(__name__)


# =============================================================================
# GLOB TOOL
# =============================================================================

class GlobTool(Tool):
    """
    Fast file pattern matching tool using glob patterns.

    Supports patterns like "**/*.py", "src/**/*.ts", etc.
    Returns matching file paths sorted by modification time.

    Example:
        result = await glob_tool.execute(pattern="**/*.py", path="src")
        # Returns list of Python files sorted by mtime
    """

    def __init__(self):
        super().__init__()
        self.name = "glob"
        self.category = ToolCategory.SEARCH
        self.description = "Fast file pattern matching using glob patterns like **/*.py"
        self.parameters = {
            "pattern": {
                "type": "string",
                "description": "Glob pattern to match files (e.g., '**/*.py', 'src/**/*.ts')",
                "required": True
            },
            "path": {
                "type": "string",
                "description": "Directory to search in (default: current directory)",
                "required": False
            },
            "max_results": {
                "type": "integer",
                "description": "Maximum number of results to return (default: 100)",
                "required": False
            }
        }

    async def _execute_validated(self, **kwargs) -> ToolResult:
        """Execute glob pattern matching."""
        pattern = kwargs.get("pattern", "")
        path = kwargs.get("path", ".")
        max_results = kwargs.get("max_results", 100)

        # Validate required parameter
        if not pattern:
            return ToolResult(success=False, error="Pattern is required")

        # Validate max_results bounds
        if not isinstance(max_results, int) or max_results < 1:
            max_results = 100
        max_results = min(max_results, 10000)  # Hard limit

        try:
            root = Path(path).resolve()
            if not root.exists():
                return ToolResult(success=False, error=f"Path does not exist: {path}")

            if not root.is_dir():
                return ToolResult(success=False, error=f"Path is not a directory: {path}")

            # Use pathlib glob for recursive patterns
            matches = []
            for match in root.glob(pattern):
                if match.is_file():
                    try:
                        rel_path = str(match.relative_to(root))
                        mtime = match.stat().st_mtime
                        matches.append((mtime, rel_path))
                    except (ValueError, OSError) as e:
                        logger.debug(f"Skipping {match}: {e}")
                        continue

            # Sort by modification time (newest first)
            matches.sort(key=lambda x: x[0], reverse=True)

            # Return just the paths, limited to max_results
            result_paths = [p for _, p in matches[:max_results]]

            return ToolResult(
                success=True,
                data=result_paths,
                metadata={
                    "pattern": pattern,
                    "path": str(root),
                    "total_matches": len(matches),
                    "returned": len(result_paths),
                    "truncated": len(matches) > max_results
                }
            )

        except PermissionError:
            return ToolResult(success=False, error=f"Permission denied: {path}")
        except Exception as e:
            logger.error(f"Glob error: {e}")
            return ToolResult(success=False, error=str(e))


# =============================================================================
# LS TOOL
# =============================================================================

class LSTool(Tool):
    """
    List directory contents with file details.

    Returns files and directories with metadata like size, type, modification time.

    Example:
        result = await ls_tool.execute(path="src", all=True)
        # Returns list of entries with name, type, size, modified
    """

    def __init__(self):
        super().__init__()
        self.name = "ls"
        self.category = ToolCategory.FILE_READ
        self.description = "List directory contents with details (size, type, modified)"
        self.parameters = {
            "path": {
                "type": "string",
                "description": "Directory path to list (default: current directory)",
                "required": False
            },
            "all": {
                "type": "boolean",
                "description": "Include hidden files (starting with .)",
                "required": False
            },
            "ignore": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Patterns to ignore (e.g., ['node_modules', '__pycache__'])",
                "required": False
            }
        }

    async def _execute_validated(self, **kwargs) -> ToolResult:
        """Execute directory listing."""
        path = kwargs.get("path", ".")
        show_all = kwargs.get("all", False)
        ignore_patterns = kwargs.get("ignore", [])

        # Validate ignore_patterns
        if not isinstance(ignore_patterns, list):
            ignore_patterns = []

        try:
            dir_path = Path(path).resolve()

            if not dir_path.exists():
                return ToolResult(success=False, error=f"Path does not exist: {path}")

            if not dir_path.is_dir():
                return ToolResult(success=False, error=f"Path is not a directory: {path}")

            entries = []
            try:
                dir_contents = sorted(
                    dir_path.iterdir(),
                    key=lambda p: (not p.is_dir(), p.name.lower())
                )
            except PermissionError:
                return ToolResult(success=False, error=f"Permission denied reading: {path}")

            for entry in dir_contents:
                name = entry.name

                # Skip hidden files unless requested
                if not show_all and name.startswith('.'):
                    continue

                # Skip ignored patterns
                if any(fnmatch.fnmatch(name, pat) for pat in ignore_patterns):
                    continue

                try:
                    stat = entry.stat()
                    entries.append({
                        "name": name,
                        "type": "directory" if entry.is_dir() else "file",
                        "size": stat.st_size if entry.is_file() else None,
                        "modified": stat.st_mtime,
                    })
                except OSError as e:
                    logger.debug(f"Cannot stat {entry}: {e}")
                    entries.append({
                        "name": name,
                        "type": "unknown",
                        "size": None,
                        "modified": None
                    })

            return ToolResult(
                success=True,
                data=entries,
                metadata={
                    "path": str(dir_path),
                    "count": len(entries),
                    "show_hidden": show_all
                }
            )

        except PermissionError:
            return ToolResult(success=False, error=f"Permission denied: {path}")
        except Exception as e:
            logger.error(f"LS error: {e}")
            return ToolResult(success=False, error=str(e))


# =============================================================================
# MULTI-EDIT TOOL
# =============================================================================

class MultiEditTool(Tool):
    """
    Apply multiple edits to a single file atomically.

    All edits must succeed or none are applied - atomic operation.
    Edits are applied in order, with line numbers adjusted automatically.

    Security: Validates edits before applying to prevent data loss.

    Example:
        result = await multi_edit.execute(
            file_path="/path/to/file.py",
            edits=[
                {"old_string": "foo", "new_string": "bar"},
                {"old_string": "baz", "new_string": "qux"}
            ]
        )
    """

    # Maximum file size to process (10MB)
    MAX_FILE_SIZE = 10 * 1024 * 1024

    def __init__(self):
        super().__init__()
        self.name = "multi_edit"
        self.category = ToolCategory.FILE_WRITE
        self.description = "Apply multiple atomic edits to a file (all succeed or none)"
        self.parameters = {
            "file_path": {
                "type": "string",
                "description": "Absolute path to the file to edit",
                "required": True
            },
            "edits": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "old_string": {"type": "string"},
                        "new_string": {"type": "string"}
                    }
                },
                "description": "List of {old_string, new_string} edits to apply",
                "required": True
            },
            "create_backup": {
                "type": "boolean",
                "description": "Create backup before editing (default: true)",
                "required": False
            }
        }

    async def _execute_validated(self, **kwargs) -> ToolResult:
        """Execute multiple edits atomically."""
        file_path = kwargs.get("file_path", "")
        edits = kwargs.get("edits", [])
        create_backup = kwargs.get("create_backup", True)

        # Validate required parameters
        if not file_path:
            return ToolResult(success=False, error="file_path is required")

        if not edits:
            return ToolResult(success=False, error="edits list is required")

        if not isinstance(edits, list):
            return ToolResult(success=False, error="edits must be an array")

        try:
            path = Path(file_path)

            if not path.exists():
                return ToolResult(success=False, error=f"File does not exist: {file_path}")

            if not path.is_file():
                return ToolResult(success=False, error=f"Path is not a file: {file_path}")

            # Check file size
            file_size = path.stat().st_size
            if file_size > self.MAX_FILE_SIZE:
                return ToolResult(
                    success=False,
                    error=f"File too large ({file_size} bytes). Max: {self.MAX_FILE_SIZE}"
                )

            # Read original content
            try:
                original_content = path.read_text(encoding='utf-8')
            except UnicodeDecodeError:
                return ToolResult(success=False, error="File is not valid UTF-8 text")

            content = original_content

            # Phase 1: Validate all edits first (dry run)
            validation_errors = []
            for i, edit in enumerate(edits):
                if not isinstance(edit, dict):
                    validation_errors.append(f"Edit {i+1}: must be an object")
                    continue

                old_string = edit.get("old_string", "")
                if old_string and old_string not in content:
                    validation_errors.append(f"Edit {i+1}: old_string not found in file")

            if validation_errors:
                return ToolResult(
                    success=False,
                    error="; ".join(validation_errors)
                )

            # Phase 2: Apply all edits
            applied = []
            for i, edit in enumerate(edits):
                old_string = edit.get("old_string", "")
                new_string = edit.get("new_string", "")

                if old_string:
                    # Check for ambiguous matches
                    count = content.count(old_string)
                    if count > 1:
                        return ToolResult(
                            success=False,
                            error=f"Edit {i+1}: old_string appears {count} times (ambiguous)"
                        )

                    content = content.replace(old_string, new_string, 1)
                    applied.append({
                        "index": i,
                        "type": "replace",
                        "old_len": len(old_string),
                        "new_len": len(new_string)
                    })

            # Create backup if requested
            backup_path = None
            if create_backup:
                backup_path = path.with_suffix(path.suffix + '.bak')
                try:
                    backup_path.write_text(original_content, encoding='utf-8')
                except OSError as e:
                    logger.warning(f"Could not create backup: {e}")
                    backup_path = None

            # Write new content
            path.write_text(content, encoding='utf-8')

            return ToolResult(
                success=True,
                data={
                    "file": str(path),
                    "edits_applied": len(applied),
                    "backup": str(backup_path) if backup_path else None
                },
                metadata={
                    "original_size": len(original_content),
                    "new_size": len(content),
                    "edits": applied,
                    "size_delta": len(content) - len(original_content)
                }
            )

        except PermissionError:
            return ToolResult(success=False, error=f"Permission denied: {file_path}")
        except Exception as e:
            logger.error(f"MultiEdit error: {e}")
            return ToolResult(success=False, error=str(e))


# =============================================================================
# REGISTRY HELPER
# =============================================================================

def get_file_tools() -> List[Tool]:
    """Get all file operation tools."""
    return [
        GlobTool(),
        LSTool(),
        MultiEditTool(),
    ]


__all__ = [
    "GlobTool",
    "LSTool",
    "MultiEditTool",
    "get_file_tools",
]
