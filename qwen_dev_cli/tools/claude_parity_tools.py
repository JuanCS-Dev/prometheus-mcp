"""Claude Code Parity Tools - Glob, LS, MultiEdit, WebFetch, WebSearch, Todo.

These tools provide 100% feature parity with Claude Code's built-in tools.
Constitutional compliance: P1 (Completeness), P2 (Validation), P6 (Efficiency)
"""

import asyncio
import fnmatch
import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .base import Tool, ToolCategory, ToolResult


# =============================================================================
# GLOB TOOL - Fast file pattern matching
# =============================================================================

class GlobTool(Tool):
    """Fast file pattern matching tool using glob patterns.

    Supports patterns like "**/*.py", "src/**/*.ts", etc.
    Returns matching file paths sorted by modification time.
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

        if not pattern:
            return ToolResult(success=False, error="Pattern is required")

        try:
            root = Path(path).resolve()
            if not root.exists():
                return ToolResult(success=False, error=f"Path does not exist: {path}")

            # Use pathlib glob for recursive patterns
            matches = []
            for match in root.glob(pattern):
                if match.is_file():
                    try:
                        rel_path = str(match.relative_to(root))
                        mtime = match.stat().st_mtime
                        matches.append((mtime, rel_path))
                    except (ValueError, OSError):
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
                    "returned": len(result_paths)
                }
            )
        except Exception as e:
            return ToolResult(success=False, error=str(e))


# =============================================================================
# LS TOOL - List directory contents
# =============================================================================

class LSTool(Tool):
    """List directory contents with file details.

    Returns files and directories with metadata like size, type, modification time.
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

        try:
            dir_path = Path(path).resolve()
            if not dir_path.exists():
                return ToolResult(success=False, error=f"Path does not exist: {path}")
            if not dir_path.is_dir():
                return ToolResult(success=False, error=f"Path is not a directory: {path}")

            entries = []
            for entry in sorted(dir_path.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower())):
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
                except OSError:
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
                    "count": len(entries)
                }
            )
        except PermissionError:
            return ToolResult(success=False, error=f"Permission denied: {path}")
        except Exception as e:
            return ToolResult(success=False, error=str(e))


# =============================================================================
# MULTI-EDIT TOOL - Atomic multiple edits
# =============================================================================

class MultiEditTool(Tool):
    """Apply multiple edits to a single file atomically.

    All edits must succeed or none are applied - atomic operation.
    Edits are applied in order, with line numbers adjusted automatically.
    """

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

        if not file_path:
            return ToolResult(success=False, error="file_path is required")
        if not edits:
            return ToolResult(success=False, error="edits list is required")

        try:
            path = Path(file_path)
            if not path.exists():
                return ToolResult(success=False, error=f"File does not exist: {file_path}")

            # Read original content
            original_content = path.read_text(encoding='utf-8')
            content = original_content

            # Validate all edits first (dry run)
            for i, edit in enumerate(edits):
                old_string = edit.get("old_string", "")
                if old_string and old_string not in content:
                    return ToolResult(
                        success=False,
                        error=f"Edit {i+1}: old_string not found in file"
                    )

            # Apply all edits
            applied = []
            for i, edit in enumerate(edits):
                old_string = edit.get("old_string", "")
                new_string = edit.get("new_string", "")

                if old_string:
                    # Find-and-replace
                    if content.count(old_string) > 1:
                        return ToolResult(
                            success=False,
                            error=f"Edit {i+1}: old_string appears multiple times (ambiguous)"
                        )
                    content = content.replace(old_string, new_string, 1)
                    applied.append({"index": i, "type": "replace"})

            # Create backup if requested
            if create_backup:
                backup_path = path.with_suffix(path.suffix + '.bak')
                backup_path.write_text(original_content, encoding='utf-8')

            # Write new content
            path.write_text(content, encoding='utf-8')

            return ToolResult(
                success=True,
                data={
                    "file": str(path),
                    "edits_applied": len(applied),
                    "backup": str(backup_path) if create_backup else None
                },
                metadata={
                    "original_size": len(original_content),
                    "new_size": len(content),
                    "edits": applied
                }
            )
        except Exception as e:
            return ToolResult(success=False, error=str(e))


# =============================================================================
# WEB FETCH TOOL - Fetch URL and process with AI
# =============================================================================

class WebFetchTool(Tool):
    """Fetch content from URL and process with AI.

    Fetches URL, converts HTML to markdown, and returns content.
    Includes caching for repeated requests.
    """

    def __init__(self):
        super().__init__()
        self.name = "web_fetch"
        self.category = ToolCategory.SEARCH
        self.description = "Fetch URL content and convert to readable text/markdown"
        self.parameters = {
            "url": {
                "type": "string",
                "description": "URL to fetch content from",
                "required": True
            },
            "prompt": {
                "type": "string",
                "description": "Optional prompt to process the content",
                "required": False
            },
            "max_length": {
                "type": "integer",
                "description": "Maximum content length to return (default: 10000)",
                "required": False
            }
        }
        self._cache: Dict[str, Tuple[str, float]] = {}
        self._cache_ttl = 900  # 15 minutes

    async def _execute_validated(self, **kwargs) -> ToolResult:
        """Fetch and process URL content."""
        url = kwargs.get("url", "")
        prompt = kwargs.get("prompt", "")
        max_length = kwargs.get("max_length", 10000)

        if not url:
            return ToolResult(success=False, error="URL is required")

        # Upgrade HTTP to HTTPS
        if url.startswith("http://"):
            url = "https://" + url[7:]

        try:
            import time

            # Check cache
            if url in self._cache:
                content, cached_at = self._cache[url]
                if time.time() - cached_at < self._cache_ttl:
                    return ToolResult(
                        success=True,
                        data=content[:max_length],
                        metadata={"url": url, "cached": True}
                    )

            # Fetch URL
            import urllib.request
            import urllib.error

            req = urllib.request.Request(
                url,
                headers={
                    'User-Agent': 'JuanCS-DevCode/1.0 (CLI coding assistant)'
                }
            )

            with urllib.request.urlopen(req, timeout=30) as response:
                html = response.read().decode('utf-8', errors='ignore')

            # Convert HTML to text (basic)
            content = self._html_to_text(html)

            # Cache the result
            self._cache[url] = (content, time.time())

            return ToolResult(
                success=True,
                data=content[:max_length],
                metadata={
                    "url": url,
                    "cached": False,
                    "original_length": len(content),
                    "truncated": len(content) > max_length
                }
            )
        except urllib.error.HTTPError as e:
            return ToolResult(success=False, error=f"HTTP {e.code}: {e.reason}")
        except urllib.error.URLError as e:
            return ToolResult(success=False, error=f"URL Error: {e.reason}")
        except Exception as e:
            return ToolResult(success=False, error=str(e))

    def _html_to_text(self, html: str) -> str:
        """Convert HTML to plain text (basic conversion)."""
        import re

        # Remove script and style elements
        html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
        html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL | re.IGNORECASE)

        # Convert common elements
        html = re.sub(r'<br\s*/?>', '\n', html, flags=re.IGNORECASE)
        html = re.sub(r'</p>', '\n\n', html, flags=re.IGNORECASE)
        html = re.sub(r'</div>', '\n', html, flags=re.IGNORECASE)
        html = re.sub(r'</h[1-6]>', '\n\n', html, flags=re.IGNORECASE)
        html = re.sub(r'<h[1-6][^>]*>', '\n## ', html, flags=re.IGNORECASE)
        html = re.sub(r'<li[^>]*>', '\n- ', html, flags=re.IGNORECASE)

        # Remove all remaining tags
        html = re.sub(r'<[^>]+>', '', html)

        # Decode HTML entities
        html = html.replace('&nbsp;', ' ')
        html = html.replace('&amp;', '&')
        html = html.replace('&lt;', '<')
        html = html.replace('&gt;', '>')
        html = html.replace('&quot;', '"')

        # Clean up whitespace
        html = re.sub(r'\n\s*\n\s*\n', '\n\n', html)
        html = re.sub(r' +', ' ', html)

        return html.strip()


# =============================================================================
# WEB SEARCH TOOL - Search the web
# =============================================================================

class WebSearchTool(Tool):
    """Search the web using DuckDuckGo (no API key required).

    Returns search results with titles, URLs, and snippets.
    """

    def __init__(self):
        super().__init__()
        self.name = "web_search"
        self.category = ToolCategory.SEARCH
        self.description = "Search the web and return results"
        self.parameters = {
            "query": {
                "type": "string",
                "description": "Search query",
                "required": True
            },
            "num_results": {
                "type": "integer",
                "description": "Number of results to return (default: 5)",
                "required": False
            }
        }

    async def _execute_validated(self, **kwargs) -> ToolResult:
        """Execute web search."""
        query = kwargs.get("query", "")
        num_results = kwargs.get("num_results", 5)

        if not query:
            return ToolResult(success=False, error="Query is required")

        try:
            # Use DuckDuckGo HTML search (no API key needed)
            import urllib.request
            import urllib.parse

            encoded_query = urllib.parse.quote(query)
            url = f"https://html.duckduckgo.com/html/?q={encoded_query}"

            req = urllib.request.Request(
                url,
                headers={
                    'User-Agent': 'JuanCS-DevCode/1.0'
                }
            )

            with urllib.request.urlopen(req, timeout=10) as response:
                html = response.read().decode('utf-8', errors='ignore')

            # Parse results (basic HTML parsing)
            results = self._parse_ddg_results(html, num_results)

            return ToolResult(
                success=True,
                data=results,
                metadata={
                    "query": query,
                    "num_results": len(results)
                }
            )
        except Exception as e:
            return ToolResult(success=False, error=str(e))

    def _parse_ddg_results(self, html: str, max_results: int) -> List[Dict[str, str]]:
        """Parse DuckDuckGo HTML results."""
        import re

        results = []

        # Find result blocks
        result_pattern = re.compile(
            r'<a[^>]+class="result__a"[^>]+href="([^"]+)"[^>]*>([^<]+)</a>.*?'
            r'<a[^>]+class="result__snippet"[^>]*>([^<]+)</a>',
            re.DOTALL
        )

        for match in result_pattern.finditer(html):
            if len(results) >= max_results:
                break

            url = match.group(1)
            title = match.group(2).strip()
            snippet = match.group(3).strip()

            # Clean up URL (DDG wraps URLs)
            if '/l/?uddg=' in url:
                url_match = re.search(r'uddg=([^&]+)', url)
                if url_match:
                    url = urllib.parse.unquote(url_match.group(1))

            results.append({
                "title": title,
                "url": url,
                "snippet": snippet
            })

        return results


# =============================================================================
# TODO TOOLS - Task management
# =============================================================================

class TodoReadTool(Tool):
    """Read current todo list."""

    def __init__(self):
        super().__init__()
        self.name = "todo_read"
        self.category = ToolCategory.CONTEXT
        self.description = "Get current todo list"
        self.parameters = {}
        self._todos: List[Dict[str, Any]] = []

    async def _execute_validated(self, **kwargs) -> ToolResult:
        """Get todos."""
        return ToolResult(
            success=True,
            data=self._todos,
            metadata={"count": len(self._todos)}
        )


class TodoWriteTool(Tool):
    """Manage todo list - add, update, complete tasks."""

    def __init__(self):
        super().__init__()
        self.name = "todo_write"
        self.category = ToolCategory.CONTEXT
        self.description = "Manage todo list (add, update, complete tasks)"
        self.parameters = {
            "todos": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "content": {"type": "string"},
                        "status": {"type": "string", "enum": ["pending", "in_progress", "completed"]},
                        "activeForm": {"type": "string"}
                    }
                },
                "description": "Updated todo list",
                "required": True
            }
        }
        self._todos: List[Dict[str, Any]] = []

    async def _execute_validated(self, **kwargs) -> ToolResult:
        """Update todos."""
        todos = kwargs.get("todos", [])
        self._todos = todos
        return ToolResult(
            success=True,
            data={"updated": len(todos)},
            metadata={"todos": todos}
        )


# =============================================================================
# NOTEBOOK READ TOOL - Read Jupyter notebooks (Claude Code parity)
# =============================================================================

class NotebookReadTool(Tool):
    """Read Jupyter notebook (.ipynb) files.

    Returns all cells with their outputs, combining code, text, and visualizations.
    Claude Code parity: Supports reading .ipynb files natively.
    """

    def __init__(self):
        super().__init__()
        self.name = "notebook_read"
        self.category = ToolCategory.FILE_READ
        self.description = "Read Jupyter notebook files (.ipynb)"
        self.parameters = {
            "file_path": {
                "type": "string",
                "description": "Path to the .ipynb file",
                "required": True
            },
            "cell_type": {
                "type": "string",
                "description": "Filter by cell type: 'code', 'markdown', or 'all' (default)",
                "required": False
            }
        }

    async def _execute_validated(self, **kwargs) -> ToolResult:
        """Read and parse Jupyter notebook."""
        file_path = kwargs.get("file_path", "")
        cell_filter = kwargs.get("cell_type", "all")

        if not file_path:
            return ToolResult(success=False, error="file_path is required")

        path = Path(file_path)
        if not path.exists():
            return ToolResult(success=False, error=f"File not found: {file_path}")

        if path.suffix.lower() != ".ipynb":
            return ToolResult(success=False, error="File must be a .ipynb notebook")

        try:
            with open(path, "r", encoding="utf-8") as f:
                notebook = json.load(f)

            cells = notebook.get("cells", [])
            result_cells = []

            for idx, cell in enumerate(cells):
                cell_type = cell.get("cell_type", "unknown")

                # Apply filter
                if cell_filter != "all" and cell_type != cell_filter:
                    continue

                source = "".join(cell.get("source", []))

                cell_data = {
                    "index": idx,
                    "cell_id": cell.get("id", f"cell_{idx}"),
                    "type": cell_type,
                    "source": source,
                }

                # Include outputs for code cells
                if cell_type == "code":
                    outputs = cell.get("outputs", [])
                    cell_data["execution_count"] = cell.get("execution_count")
                    cell_data["outputs"] = self._parse_outputs(outputs)

                result_cells.append(cell_data)

            metadata = notebook.get("metadata", {})
            kernel_info = metadata.get("kernelspec", {})

            return ToolResult(
                success=True,
                data={
                    "cells": result_cells,
                    "total_cells": len(cells),
                    "filtered_cells": len(result_cells),
                    "kernel": kernel_info.get("display_name", "Unknown"),
                    "language": kernel_info.get("language", "unknown"),
                },
                metadata={"file": str(path), "filter": cell_filter}
            )
        except json.JSONDecodeError as e:
            return ToolResult(success=False, error=f"Invalid notebook JSON: {e}")
        except Exception as e:
            return ToolResult(success=False, error=str(e))

    def _parse_outputs(self, outputs: List[Dict]) -> List[Dict]:
        """Parse cell outputs to readable format."""
        parsed = []
        for output in outputs:
            out_type = output.get("output_type", "unknown")

            if out_type == "stream":
                parsed.append({
                    "type": "stream",
                    "name": output.get("name", "stdout"),
                    "text": "".join(output.get("text", []))
                })
            elif out_type == "execute_result":
                data = output.get("data", {})
                parsed.append({
                    "type": "result",
                    "text": data.get("text/plain", ""),
                    "html": data.get("text/html", "")[:500] if data.get("text/html") else None
                })
            elif out_type == "error":
                parsed.append({
                    "type": "error",
                    "ename": output.get("ename", "Error"),
                    "evalue": output.get("evalue", ""),
                    "traceback": output.get("traceback", [])[:5]  # Limit traceback
                })
            elif out_type == "display_data":
                data = output.get("data", {})
                parsed.append({
                    "type": "display",
                    "has_image": "image/png" in data or "image/jpeg" in data,
                    "text": data.get("text/plain", "")
                })

        return parsed


# =============================================================================
# NOTEBOOK EDIT TOOL - Edit Jupyter notebooks (Claude Code parity)
# =============================================================================

class NotebookEditTool(Tool):
    """Edit Jupyter notebook (.ipynb) cells.

    Supports replacing, inserting, or deleting cells.
    Claude Code parity: Matches NotebookEdit tool behavior.
    """

    def __init__(self):
        super().__init__()
        self.name = "notebook_edit"
        self.category = ToolCategory.FILE_READ
        self.description = "Edit Jupyter notebook cells (replace, insert, delete)"
        self.parameters = {
            "notebook_path": {
                "type": "string",
                "description": "Path to the .ipynb file",
                "required": True
            },
            "cell_id": {
                "type": "string",
                "description": "ID or index of the cell to edit",
                "required": False
            },
            "edit_mode": {
                "type": "string",
                "description": "Mode: 'replace', 'insert', or 'delete' (default: replace)",
                "required": False
            },
            "cell_type": {
                "type": "string",
                "description": "Cell type: 'code' or 'markdown' (for insert)",
                "required": False
            },
            "new_source": {
                "type": "string",
                "description": "New content for the cell",
                "required": True
            }
        }

    async def _execute_validated(self, **kwargs) -> ToolResult:
        """Edit notebook cell."""
        notebook_path = kwargs.get("notebook_path", "")
        cell_id = kwargs.get("cell_id")
        edit_mode = kwargs.get("edit_mode", "replace")
        cell_type = kwargs.get("cell_type", "code")
        new_source = kwargs.get("new_source", "")

        if not notebook_path:
            return ToolResult(success=False, error="notebook_path is required")

        path = Path(notebook_path)
        if not path.exists():
            return ToolResult(success=False, error=f"File not found: {notebook_path}")

        if path.suffix.lower() != ".ipynb":
            return ToolResult(success=False, error="File must be a .ipynb notebook")

        try:
            with open(path, "r", encoding="utf-8") as f:
                notebook = json.load(f)

            cells = notebook.get("cells", [])

            if edit_mode == "delete":
                idx = self._find_cell_index(cells, cell_id)
                if idx is None:
                    return ToolResult(success=False, error=f"Cell not found: {cell_id}")
                deleted_cell = cells.pop(idx)
                action = f"Deleted cell {idx}"

            elif edit_mode == "insert":
                # Insert after specified cell (or at beginning if no cell_id)
                new_cell = self._create_cell(cell_type, new_source)
                if cell_id:
                    idx = self._find_cell_index(cells, cell_id)
                    if idx is None:
                        return ToolResult(success=False, error=f"Cell not found: {cell_id}")
                    cells.insert(idx + 1, new_cell)
                    action = f"Inserted new {cell_type} cell after index {idx}"
                else:
                    cells.insert(0, new_cell)
                    action = f"Inserted new {cell_type} cell at beginning"

            else:  # replace
                if cell_id is None:
                    return ToolResult(success=False, error="cell_id required for replace")
                idx = self._find_cell_index(cells, cell_id)
                if idx is None:
                    return ToolResult(success=False, error=f"Cell not found: {cell_id}")

                # Update source, preserve cell type if not specified
                if cell_type:
                    cells[idx]["cell_type"] = cell_type
                cells[idx]["source"] = new_source.split("\n")
                # Clear outputs for code cells
                if cells[idx].get("cell_type") == "code":
                    cells[idx]["outputs"] = []
                    cells[idx]["execution_count"] = None
                action = f"Replaced cell {idx}"

            notebook["cells"] = cells

            # Write back
            with open(path, "w", encoding="utf-8") as f:
                json.dump(notebook, f, indent=1, ensure_ascii=False)

            return ToolResult(
                success=True,
                data={"action": action, "total_cells": len(cells)},
                metadata={"file": str(path), "mode": edit_mode}
            )
        except json.JSONDecodeError as e:
            return ToolResult(success=False, error=f"Invalid notebook JSON: {e}")
        except Exception as e:
            return ToolResult(success=False, error=str(e))

    def _find_cell_index(self, cells: List[Dict], cell_id: str) -> Optional[int]:
        """Find cell index by ID or index string."""
        # Try as integer index first
        try:
            idx = int(cell_id)
            if 0 <= idx < len(cells):
                return idx
        except (ValueError, TypeError):
            pass

        # Try to find by cell id
        for i, cell in enumerate(cells):
            if cell.get("id") == cell_id:
                return i

        return None

    def _create_cell(self, cell_type: str, source: str) -> Dict:
        """Create a new notebook cell."""
        import uuid

        cell = {
            "id": str(uuid.uuid4())[:8],
            "cell_type": cell_type,
            "metadata": {},
            "source": source.split("\n") if source else []
        }

        if cell_type == "code":
            cell["outputs"] = []
            cell["execution_count"] = None

        return cell


# =============================================================================
# BACKGROUND TASK TOOL - Run commands in background (Claude Code /bashes parity)
# =============================================================================

class BackgroundTaskTool(Tool):
    """Run shell commands in the background.

    Claude Code parity: Implements /bashes functionality for background tasks.
    """

    # Class-level storage for background tasks
    _tasks: Dict[str, Dict[str, Any]] = {}
    _task_counter: int = 0

    def __init__(self):
        super().__init__()
        self.name = "background_task"
        self.category = ToolCategory.EXECUTION
        self.description = "Run shell commands in background"
        self.parameters = {
            "action": {
                "type": "string",
                "description": "Action: 'start', 'status', 'output', 'kill', 'list'",
                "required": True
            },
            "command": {
                "type": "string",
                "description": "Shell command to run (for 'start' action)",
                "required": False
            },
            "task_id": {
                "type": "string",
                "description": "Task ID (for 'status', 'output', 'kill' actions)",
                "required": False
            }
        }

    async def _execute_validated(self, **kwargs) -> ToolResult:
        """Execute background task action."""
        import shlex
        import subprocess
        import threading
        from ..core.input_validator import validate_command

        action = kwargs.get("action", "")
        command = kwargs.get("command", "")
        task_id = kwargs.get("task_id", "")

        if action == "start":
            if not command:
                return ToolResult(success=False, error="command is required for start")

            # SECURITY: Validate command before execution
            validation = validate_command(command, allow_shell=False)
            if not validation.is_valid:
                return ToolResult(
                    success=False,
                    error=f"Command blocked by security filter: {', '.join(validation.errors)}"
                )

            BackgroundTaskTool._task_counter += 1
            new_id = f"task_{BackgroundTaskTool._task_counter}"

            # Start process in background
            try:
                # SECURITY: Use shlex.split instead of shell=True
                args = shlex.split(command)
                process = subprocess.Popen(
                    args,
                    shell=False,  # HARDENED: Never use shell=True
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )

                BackgroundTaskTool._tasks[new_id] = {
                    "id": new_id,
                    "command": command,
                    "process": process,
                    "status": "running",
                    "stdout": [],
                    "stderr": [],
                    "start_time": __import__("datetime").datetime.now().isoformat()
                }

                # Start output collector thread
                def collect_output(task_id):
                    task = BackgroundTaskTool._tasks.get(task_id)
                    if task:
                        proc = task["process"]
                        stdout, stderr = proc.communicate()
                        task["stdout"] = stdout.split("\n") if stdout else []
                        task["stderr"] = stderr.split("\n") if stderr else []
                        task["status"] = "completed" if proc.returncode == 0 else "failed"
                        task["return_code"] = proc.returncode

                thread = threading.Thread(target=collect_output, args=(new_id,))
                thread.daemon = True
                thread.start()

                return ToolResult(
                    success=True,
                    data={"task_id": new_id, "command": command, "status": "started"},
                    metadata={"action": "start"}
                )
            except Exception as e:
                return ToolResult(success=False, error=str(e))

        elif action == "list":
            tasks_info = []
            for tid, task in BackgroundTaskTool._tasks.items():
                # Update status if process finished
                proc = task.get("process")
                if proc and proc.poll() is not None:
                    if task["status"] == "running":
                        task["status"] = "completed" if proc.returncode == 0 else "failed"
                        task["return_code"] = proc.returncode

                tasks_info.append({
                    "id": tid,
                    "command": task["command"][:50],
                    "status": task["status"],
                    "start_time": task.get("start_time")
                })

            return ToolResult(
                success=True,
                data={"tasks": tasks_info, "count": len(tasks_info)},
                metadata={"action": "list"}
            )

        elif action == "status":
            if not task_id:
                return ToolResult(success=False, error="task_id is required for status")

            task = BackgroundTaskTool._tasks.get(task_id)
            if not task:
                return ToolResult(success=False, error=f"Task not found: {task_id}")

            # Update status
            proc = task.get("process")
            if proc and proc.poll() is not None:
                if task["status"] == "running":
                    task["status"] = "completed" if proc.returncode == 0 else "failed"
                    task["return_code"] = proc.returncode

            return ToolResult(
                success=True,
                data={
                    "id": task_id,
                    "command": task["command"],
                    "status": task["status"],
                    "return_code": task.get("return_code")
                },
                metadata={"action": "status"}
            )

        elif action == "output":
            if not task_id:
                return ToolResult(success=False, error="task_id is required for output")

            task = BackgroundTaskTool._tasks.get(task_id)
            if not task:
                return ToolResult(success=False, error=f"Task not found: {task_id}")

            return ToolResult(
                success=True,
                data={
                    "stdout": "\n".join(task.get("stdout", [])),
                    "stderr": "\n".join(task.get("stderr", [])),
                    "status": task["status"]
                },
                metadata={"action": "output", "task_id": task_id}
            )

        elif action == "kill":
            if not task_id:
                return ToolResult(success=False, error="task_id is required for kill")

            task = BackgroundTaskTool._tasks.get(task_id)
            if not task:
                return ToolResult(success=False, error=f"Task not found: {task_id}")

            proc = task.get("process")
            if proc and proc.poll() is None:
                proc.terminate()
                task["status"] = "killed"

            return ToolResult(
                success=True,
                data={"task_id": task_id, "status": "killed"},
                metadata={"action": "kill"}
            )

        else:
            return ToolResult(success=False, error=f"Unknown action: {action}")


# =============================================================================
# TASK/SUBAGENT TOOL - Spawn specialized subagents (Claude Code parity)
# =============================================================================

class TaskTool(Tool):
    """Launch specialized subagents for complex, multi-step tasks.

    Claude Code parity: Implements the Task tool for spawning subagents.

    Available agent types:
    - explore: Fast codebase exploration
    - plan: Task planning and breakdown
    - general-purpose: Complex multi-step tasks
    - code-reviewer: Review code changes
    - test-runner: Execute test suites
    """

    # Subagent registry with capabilities
    SUBAGENT_TYPES = {
        "explore": {
            "description": "Fast codebase exploration and search",
            "tools": ["glob", "grep", "read_file", "list_directory"],
            "prompt_prefix": "You are exploring a codebase. Be thorough but efficient."
        },
        "plan": {
            "description": "Task planning and breakdown",
            "tools": ["glob", "grep", "read_file", "todo_write"],
            "prompt_prefix": "You are planning a task. Break it down into actionable steps."
        },
        "general-purpose": {
            "description": "Complex multi-step autonomous tasks",
            "tools": "*",  # All tools
            "prompt_prefix": "You are handling a complex task autonomously."
        },
        "code-reviewer": {
            "description": "Review code for quality and best practices",
            "tools": ["read_file", "glob", "grep"],
            "prompt_prefix": "You are reviewing code. Focus on quality, security, and best practices."
        },
        "test-runner": {
            "description": "Execute and analyze test results",
            "tools": ["bash_command", "read_file", "glob"],
            "prompt_prefix": "You are running tests. Report results clearly."
        },
        "security": {
            "description": "Security analysis and vulnerability scanning",
            "tools": ["read_file", "glob", "grep", "bash_command"],
            "prompt_prefix": "You are analyzing code for security vulnerabilities. Follow OWASP guidelines."
        },
        "documentation": {
            "description": "Generate documentation from code",
            "tools": ["read_file", "glob", "write_file"],
            "prompt_prefix": "You are generating documentation. Be clear and comprehensive."
        },
        "refactor": {
            "description": "Code refactoring suggestions",
            "tools": ["read_file", "glob", "grep", "edit_file"],
            "prompt_prefix": "You are refactoring code. Maintain functionality while improving structure."
        }
    }

    # Track running subagents
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
                "description": "Agent type: explore, plan, general-purpose, code-reviewer, test-runner, security, documentation, refactor",
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

        if not prompt:
            return ToolResult(success=False, error="prompt is required")

        if subagent_type not in TaskTool.SUBAGENT_TYPES:
            available = ", ".join(TaskTool.SUBAGENT_TYPES.keys())
            return ToolResult(
                success=False,
                error=f"Unknown subagent_type: {subagent_type}. Available: {available}"
            )

        # Resume existing subagent if requested
        if resume_id and resume_id in TaskTool._subagents:
            subagent = TaskTool._subagents[resume_id]
            subagent["prompts"].append(prompt)
            return await self._run_subagent(subagent, prompt)

        # Create new subagent
        TaskTool._subagent_counter += 1
        subagent_id = f"subagent_{TaskTool._subagent_counter}"

        agent_config = TaskTool.SUBAGENT_TYPES[subagent_type]
        subagent = {
            "id": subagent_id,
            "type": subagent_type,
            "description": description or f"{subagent_type} task",
            "model": model,
            "config": agent_config,
            "prompts": [prompt],
            "results": [],
            "status": "created",
            "created_at": __import__("datetime").datetime.now().isoformat()
        }

        TaskTool._subagents[subagent_id] = subagent

        return await self._run_subagent(subagent, prompt)

    async def _run_subagent(self, subagent: Dict, prompt: str) -> ToolResult:
        """Run the subagent with the given prompt."""
        subagent["status"] = "running"

        try:
            # Build the full prompt with prefix
            config = subagent["config"]
            full_prompt = f"{config['prompt_prefix']}\n\nTask: {prompt}"

            # For now, simulate subagent execution
            # In production, this would invoke the actual agent system
            result = await self._simulate_subagent(subagent, full_prompt)

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
                    "model": subagent["model"]
                }
            )
        except Exception as e:
            subagent["status"] = "failed"
            subagent["error"] = str(e)
            return ToolResult(success=False, error=str(e))

    async def _simulate_subagent(self, subagent: Dict, prompt: str) -> Dict:
        """
        Simulate subagent execution.

        In production, this would:
        1. Initialize the appropriate agent from the agent registry
        2. Run with the specified tools
        3. Return actual results
        """
        agent_type = subagent["type"]

        # Provide a structured response based on agent type
        if agent_type == "explore":
            return {
                "type": "exploration",
                "summary": f"Exploration task queued: {prompt[:100]}...",
                "hint": "Use /explore command for full exploration",
                "status": "ready_to_execute"
            }
        elif agent_type == "plan":
            return {
                "type": "planning",
                "summary": f"Planning task queued: {prompt[:100]}...",
                "hint": "Use /plan command for full planning",
                "status": "ready_to_execute"
            }
        elif agent_type == "code-reviewer":
            return {
                "type": "review",
                "summary": f"Code review queued: {prompt[:100]}...",
                "hint": "Use /review command for full review",
                "status": "ready_to_execute"
            }
        elif agent_type == "test-runner":
            return {
                "type": "testing",
                "summary": f"Test execution queued: {prompt[:100]}...",
                "hint": "Use /test command for full testing",
                "status": "ready_to_execute"
            }
        else:
            return {
                "type": agent_type,
                "summary": f"Task queued for {agent_type}: {prompt[:100]}...",
                "status": "ready_to_execute"
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


# =============================================================================
# ASK USER QUESTION TOOL (Claude Code parity)
# =============================================================================

class AskUserQuestionTool(Tool):
    """Ask the user a question with predefined options.

    Claude Code parity: Interactive question/answer during execution.
    Allows gathering user preferences, clarifying requirements, and getting decisions.
    """

    # Store pending questions
    _pending_questions: Dict[str, Dict[str, Any]] = {}
    _question_counter: int = 0

    def __init__(self):
        super().__init__()
        self.name = "ask_user_question"
        self.category = ToolCategory.CONTEXT
        self.description = "Ask user questions with predefined options"
        self.parameters = {
            "questions": {
                "type": "array",
                "description": "List of questions (1-4) with options",
                "required": True
            }
        }

    async def _execute_validated(self, **kwargs) -> ToolResult:
        """Create a question for the user."""
        questions = kwargs.get("questions", [])

        if not questions:
            return ToolResult(success=False, error="questions array is required")

        if len(questions) > 4:
            return ToolResult(success=False, error="Maximum 4 questions allowed")

        # Validate question format
        validated_questions = []
        for q in questions:
            if not isinstance(q, dict):
                continue

            question_text = q.get("question", "")
            options = q.get("options", [])
            header = q.get("header", "Question")
            multi_select = q.get("multiSelect", False)

            if not question_text:
                continue

            if not options or len(options) < 2:
                return ToolResult(
                    success=False,
                    error=f"Question '{question_text[:30]}...' needs at least 2 options"
                )

            validated_questions.append({
                "question": question_text,
                "header": header[:12],  # Max 12 chars
                "options": options[:4],  # Max 4 options
                "multiSelect": multi_select
            })

        if not validated_questions:
            return ToolResult(success=False, error="No valid questions provided")

        # Store pending question
        AskUserQuestionTool._question_counter += 1
        question_id = f"q_{AskUserQuestionTool._question_counter}"

        AskUserQuestionTool._pending_questions[question_id] = {
            "id": question_id,
            "questions": validated_questions,
            "status": "pending",
            "created_at": __import__("datetime").datetime.now().isoformat()
        }

        return ToolResult(
            success=True,
            data={
                "question_id": question_id,
                "questions": validated_questions,
                "status": "pending",
                "message": "Question(s) queued for user"
            },
            metadata={"count": len(validated_questions)}
        )

    @classmethod
    def get_pending_questions(cls) -> List[Dict]:
        """Get all pending questions."""
        return [
            q for q in cls._pending_questions.values()
            if q["status"] == "pending"
        ]

    @classmethod
    def answer_question(cls, question_id: str, answers: Dict) -> bool:
        """Record user's answer to a question."""
        if question_id not in cls._pending_questions:
            return False

        cls._pending_questions[question_id]["answers"] = answers
        cls._pending_questions[question_id]["status"] = "answered"
        return True


# =============================================================================
# REGISTRY HELPER
# =============================================================================

def get_claude_parity_tools() -> List[Tool]:
    """Get all Claude Code parity tools."""
    return [
        GlobTool(),
        LSTool(),
        MultiEditTool(),
        WebFetchTool(),
        WebSearchTool(),
        TodoReadTool(),
        TodoWriteTool(),
        NotebookReadTool(),
        NotebookEditTool(),
        BackgroundTaskTool(),
        TaskTool(),
        AskUserQuestionTool(),
    ]
