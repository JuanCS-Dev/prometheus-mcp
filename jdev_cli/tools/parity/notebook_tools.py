"""
Notebook Tools - NotebookRead, NotebookEdit
============================================

Jupyter notebook operations for Claude Code parity.

Contains:
- NotebookReadTool: Read .ipynb files with cell outputs
- NotebookEditTool: Edit notebook cells (replace, insert, delete)

Author: JuanCS Dev
Date: 2025-11-27
"""

from __future__ import annotations

import json
import logging
import uuid
from pathlib import Path
from typing import Dict, List, Optional

from jdev_cli.tools.base import Tool, ToolCategory, ToolResult

logger = logging.getLogger(__name__)


# =============================================================================
# NOTEBOOK READ TOOL
# =============================================================================

class NotebookReadTool(Tool):
    """
    Read Jupyter notebook (.ipynb) files.

    Returns all cells with their outputs, combining code, text, and visualizations.
    Claude Code parity: Supports reading .ipynb files natively.

    Example:
        result = await read.execute(file_path="notebook.ipynb", cell_type="code")
    """

    # Maximum notebook size (50MB)
    MAX_NOTEBOOK_SIZE = 50 * 1024 * 1024

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

        # Validate required parameter
        if not file_path:
            return ToolResult(success=False, error="file_path is required")

        # Validate cell_type
        if cell_filter not in ("all", "code", "markdown", "raw"):
            cell_filter = "all"

        path = Path(file_path)

        if not path.exists():
            return ToolResult(success=False, error=f"File not found: {file_path}")

        if path.suffix.lower() != ".ipynb":
            return ToolResult(success=False, error="File must be a .ipynb notebook")

        # Check file size
        try:
            file_size = path.stat().st_size
            if file_size > self.MAX_NOTEBOOK_SIZE:
                return ToolResult(
                    success=False,
                    error=f"Notebook too large ({file_size} bytes). Max: {self.MAX_NOTEBOOK_SIZE}"
                )
        except OSError as e:
            return ToolResult(success=False, error=f"Cannot access file: {e}")

        try:
            with open(path, "r", encoding="utf-8") as f:
                notebook = json.load(f)

            # Validate notebook structure
            if not isinstance(notebook, dict):
                return ToolResult(success=False, error="Invalid notebook format")

            cells = notebook.get("cells", [])
            if not isinstance(cells, list):
                return ToolResult(success=False, error="Invalid notebook: missing cells")

            result_cells = []
            for idx, cell in enumerate(cells):
                if not isinstance(cell, dict):
                    continue

                cell_type = cell.get("cell_type", "unknown")

                # Apply filter
                if cell_filter != "all" and cell_type != cell_filter:
                    continue

                # Get source (can be string or list of strings)
                source = cell.get("source", [])
                if isinstance(source, list):
                    source = "".join(source)

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

            # Extract metadata
            metadata = notebook.get("metadata", {})
            kernel_info = metadata.get("kernelspec", {})
            nbformat = notebook.get("nbformat", 4)
            nbformat_minor = notebook.get("nbformat_minor", 0)

            return ToolResult(
                success=True,
                data={
                    "cells": result_cells,
                    "total_cells": len(cells),
                    "filtered_cells": len(result_cells),
                    "kernel": kernel_info.get("display_name", "Unknown"),
                    "language": kernel_info.get("language", "unknown"),
                },
                metadata={
                    "file": str(path),
                    "filter": cell_filter,
                    "nbformat": f"{nbformat}.{nbformat_minor}",
                    "file_size": file_size
                }
            )

        except json.JSONDecodeError as e:
            return ToolResult(success=False, error=f"Invalid notebook JSON: {e}")
        except UnicodeDecodeError:
            return ToolResult(success=False, error="Notebook file is not valid UTF-8")
        except Exception as e:
            logger.error(f"NotebookRead error: {e}")
            return ToolResult(success=False, error=str(e))

    def _parse_outputs(self, outputs: List[Dict]) -> List[Dict]:
        """Parse cell outputs to readable format."""
        if not isinstance(outputs, list):
            return []

        parsed = []
        for output in outputs:
            if not isinstance(output, dict):
                continue

            out_type = output.get("output_type", "unknown")

            if out_type == "stream":
                text = output.get("text", [])
                if isinstance(text, list):
                    text = "".join(text)
                parsed.append({
                    "type": "stream",
                    "name": output.get("name", "stdout"),
                    "text": text[:5000]  # Limit text length
                })

            elif out_type == "execute_result":
                data = output.get("data", {})
                parsed.append({
                    "type": "result",
                    "text": str(data.get("text/plain", ""))[:2000],
                    "html": data.get("text/html", "")[:1000] if data.get("text/html") else None
                })

            elif out_type == "error":
                parsed.append({
                    "type": "error",
                    "ename": output.get("ename", "Error"),
                    "evalue": output.get("evalue", "")[:500],
                    "traceback": output.get("traceback", [])[:5]  # Limit traceback
                })

            elif out_type == "display_data":
                data = output.get("data", {})
                parsed.append({
                    "type": "display",
                    "has_image": "image/png" in data or "image/jpeg" in data,
                    "text": str(data.get("text/plain", ""))[:1000]
                })

        return parsed


# =============================================================================
# NOTEBOOK EDIT TOOL
# =============================================================================

class NotebookEditTool(Tool):
    """
    Edit Jupyter notebook (.ipynb) cells.

    Supports replacing, inserting, or deleting cells.
    Claude Code parity: Matches NotebookEdit tool behavior.

    Example:
        # Replace a cell
        result = await edit.execute(
            notebook_path="notebook.ipynb",
            cell_id="0",
            edit_mode="replace",
            new_source="print('Hello!')"
        )

        # Insert a new cell
        result = await edit.execute(
            notebook_path="notebook.ipynb",
            cell_id="2",
            edit_mode="insert",
            cell_type="markdown",
            new_source="## Section Header"
        )
    """

    def __init__(self):
        super().__init__()
        self.name = "notebook_edit"
        self.category = ToolCategory.FILE_WRITE
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

        # Validate required parameters
        if not notebook_path:
            return ToolResult(success=False, error="notebook_path is required")

        # Validate edit_mode
        if edit_mode not in ("replace", "insert", "delete"):
            return ToolResult(
                success=False,
                error=f"Invalid edit_mode: {edit_mode}. Use: replace, insert, delete"
            )

        # Validate cell_type
        if cell_type not in ("code", "markdown", "raw"):
            cell_type = "code"

        path = Path(notebook_path)

        if not path.exists():
            return ToolResult(success=False, error=f"File not found: {notebook_path}")

        if path.suffix.lower() != ".ipynb":
            return ToolResult(success=False, error="File must be a .ipynb notebook")

        try:
            # Read notebook
            with open(path, "r", encoding="utf-8") as f:
                notebook = json.load(f)

            if not isinstance(notebook, dict):
                return ToolResult(success=False, error="Invalid notebook format")

            cells = notebook.get("cells", [])
            if not isinstance(cells, list):
                return ToolResult(success=False, error="Invalid notebook: missing cells")

            # Execute edit operation
            if edit_mode == "delete":
                result = self._delete_cell(cells, cell_id)
            elif edit_mode == "insert":
                result = self._insert_cell(cells, cell_id, cell_type, new_source)
            else:  # replace
                result = self._replace_cell(cells, cell_id, cell_type, new_source)

            if not result["success"]:
                return ToolResult(success=False, error=result["error"])

            notebook["cells"] = cells

            # Write back with consistent formatting
            with open(path, "w", encoding="utf-8") as f:
                json.dump(notebook, f, indent=1, ensure_ascii=False)

            return ToolResult(
                success=True,
                data={
                    "action": result["action"],
                    "total_cells": len(cells)
                },
                metadata={
                    "file": str(path),
                    "mode": edit_mode
                }
            )

        except json.JSONDecodeError as e:
            return ToolResult(success=False, error=f"Invalid notebook JSON: {e}")
        except PermissionError:
            return ToolResult(success=False, error=f"Permission denied: {notebook_path}")
        except Exception as e:
            logger.error(f"NotebookEdit error: {e}")
            return ToolResult(success=False, error=str(e))

    def _find_cell_index(self, cells: List[Dict], cell_id: Optional[str]) -> Optional[int]:
        """Find cell index by ID or index string."""
        if cell_id is None:
            return None

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

    def _delete_cell(self, cells: List[Dict], cell_id: Optional[str]) -> Dict:
        """Delete a cell by ID or index."""
        idx = self._find_cell_index(cells, cell_id)
        if idx is None:
            return {"success": False, "error": f"Cell not found: {cell_id}"}

        cells.pop(idx)
        return {"success": True, "action": f"Deleted cell {idx}"}

    def _insert_cell(
        self,
        cells: List[Dict],
        cell_id: Optional[str],
        cell_type: str,
        source: str
    ) -> Dict:
        """Insert a new cell after specified cell (or at beginning)."""
        new_cell = self._create_cell(cell_type, source)

        if cell_id:
            idx = self._find_cell_index(cells, cell_id)
            if idx is None:
                return {"success": False, "error": f"Cell not found: {cell_id}"}
            cells.insert(idx + 1, new_cell)
            return {"success": True, "action": f"Inserted new {cell_type} cell after index {idx}"}
        else:
            cells.insert(0, new_cell)
            return {"success": True, "action": f"Inserted new {cell_type} cell at beginning"}

    def _replace_cell(
        self,
        cells: List[Dict],
        cell_id: Optional[str],
        cell_type: Optional[str],
        source: str
    ) -> Dict:
        """Replace cell content."""
        if cell_id is None:
            return {"success": False, "error": "cell_id required for replace"}

        idx = self._find_cell_index(cells, cell_id)
        if idx is None:
            return {"success": False, "error": f"Cell not found: {cell_id}"}

        # Update source, preserve cell type if not specified
        if cell_type:
            cells[idx]["cell_type"] = cell_type

        cells[idx]["source"] = source.split("\n") if source else []

        # Clear outputs for code cells
        if cells[idx].get("cell_type") == "code":
            cells[idx]["outputs"] = []
            cells[idx]["execution_count"] = None

        return {"success": True, "action": f"Replaced cell {idx}"}


# =============================================================================
# REGISTRY HELPER
# =============================================================================

def get_notebook_tools() -> List[Tool]:
    """Get all notebook operation tools."""
    return [
        NotebookReadTool(),
        NotebookEditTool(),
    ]


__all__ = [
    "NotebookReadTool",
    "NotebookEditTool",
    "get_notebook_tools",
]
