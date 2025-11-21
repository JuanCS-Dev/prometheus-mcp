"""Search and navigation tools."""
import logging
logger = logging.getLogger(__name__)

import subprocess
from pathlib import Path
from typing import Optional

from .base import Tool, ToolResult, ToolCategory
from .validated import ValidatedTool
from ..core.validation import Required, TypeCheck


class SearchFilesTool(ValidatedTool):
    """Search for text pattern in files using ripgrep."""
    
    def __init__(self):
        super().__init__()
        self.category = ToolCategory.SEARCH
        self.description = "Search for text pattern in files (uses ripgrep if available)"
        self.parameters = {
            "pattern": {
                "type": "string",
                "description": "Text pattern to search for",
                "required": True
            },
            "path": {
                "type": "string",
                "description": "Directory to search in",
                "required": False
            },
            "file_pattern": {
                "type": "string",
                "description": "File pattern to include (e.g., '*.py')",
                "required": False
            },
            "max_results": {
                "type": "integer",
                "description": "Maximum number of results",
                "required": False
            },
            "semantic": {
                "type": "boolean",
                "description": "Use semantic search (code symbols) instead of text search",
                "required": False
            }
        }
    def get_validators(self):
        """Validate parameters."""
        return {}

    
    async def _execute_validated(self, pattern: str, path: str = ".", file_pattern: Optional[str] = None, 
                                 max_results: int = 50, semantic: bool = False, indexer=None) -> ToolResult:
        """
        Search for pattern in files.
        
        Week 3 Day 1: Added semantic search mode using indexer.
        When semantic=True, searches code symbols instead of text.
        """
        try:
            # Week 3 Day 1: Semantic search mode
            if semantic and indexer:
                return await self._semantic_search(pattern, indexer, max_results)
            
            # Original text-based search
            # Try ripgrep first
            cmd = ["rg", "--line-number", "--with-filename", "--no-heading"]
            
            if file_pattern:
                cmd.extend(["--glob", file_pattern])
            
            cmd.extend([pattern, path])
            
            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                if result.returncode == 0:
                    lines = result.stdout.strip().split('\n')[:max_results]
                    
                    results = []
                    for line in lines:
                        if ':' in line:
                            parts = line.split(':', 2)
                            if len(parts) >= 3:
                                results.append({
                                    "file": parts[0],
                                    "line": int(parts[1]),
                                    "text": parts[2].strip()
                                })
                    
                    return ToolResult(
                        success=True,
                        data=results,
                        metadata={
                            "pattern": pattern,
                            "count": len(results),
                            "tool": "ripgrep"
                        }
                    )
            except FileNotFoundError:
                # Ripgrep not installed, fall back to grep
                logger.debug("ripgrep not available, falling back to grep")
            
            # Fallback to grep
            cmd = ["grep", "-rn", pattern, path]
            if file_pattern:
                cmd.extend(["--include", file_pattern])
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            lines = result.stdout.strip().split('\n')[:max_results]
            
            results = []
            for line in lines:
                if ':' in line:
                    parts = line.split(':', 2)
                    if len(parts) >= 3:
                        results.append({
                            "file": parts[0],
                            "line": int(parts[1]),
                            "text": parts[2].strip()
                        })
            
            return ToolResult(
                success=True,
                data=results,
                metadata={
                    "pattern": pattern,
                    "count": len(results),
                    "tool": "grep"
                }
            )
            
        except Exception as e:
            return ToolResult(success=False, error=str(e))
    
    async def _semantic_search(self, query: str, indexer, max_results: int) -> ToolResult:
        """
        Week 3 Day 1: Semantic search using indexer.
        
        Searches code symbols (classes, functions, methods) instead of text.
        Much faster and more accurate for code navigation.
        
        Args:
            query: Symbol name to search for
            indexer: SemanticIndexer instance
            max_results: Maximum number of results
        
        Returns:
            ToolResult with symbol matches
        """
        try:
            # Use indexer's search_symbols method
            symbols = indexer.search_symbols(query, limit=max_results)
            
            if not symbols:
                return ToolResult(
                    success=True,
                    data=[],
                    metadata={
                        "pattern": query,
                        "count": 0,
                        "tool": "semantic_indexer"
                    }
                )
            
            # Convert Symbol objects to dict format
            results = []
            for symbol in symbols:
                results.append({
                    "file": symbol.file_path,
                    "line": symbol.line_number,
                    "name": symbol.name,
                    "type": symbol.type,
                    "signature": symbol.signature or "",
                    "docstring": (symbol.docstring or "")[:100]  # First 100 chars
                })
            
            return ToolResult(
                success=True,
                data=results,
                metadata={
                    "pattern": query,
                    "count": len(results),
                    "tool": "semantic_indexer"
                }
            )
        
        except Exception as e:
            # Fall back to text search on error
            logger.warning(f"Semantic search failed: {e}, falling back to text search")
            return await self._execute_validated(query, semantic=False)


class GetDirectoryTreeTool(ValidatedTool):
    """Get hierarchical file tree structure."""
    
    def __init__(self):
        super().__init__()
        self.category = ToolCategory.SEARCH
        self.description = "Get hierarchical file tree structure"
        self.parameters = {
            "path": {
                "type": "string",
                "description": "Directory path",
                "required": False
            },
            "max_depth": {
                "type": "integer",
                "description": "Maximum depth to traverse",
                "required": False
            }
        }
    def get_validators(self):
        """Validate parameters."""
        return {}

    
    async def _execute_validated(self, path: str = ".", max_depth: int = 3) -> ToolResult:
        """Get directory tree."""
        try:
            dir_path = Path(path)
            
            if not dir_path.is_dir():
                return ToolResult(
                    success=False,
                    error=f"Not a directory: {path}"
                )
            
            def build_tree(dir_path: Path, prefix: str = "", depth: int = 0) -> list[str]:
                """Recursively build tree structure."""
                if depth > max_depth:
                    return []
                
                lines = []
                try:
                    items = sorted(dir_path.iterdir(), key=lambda x: (not x.is_dir(), x.name))
                    
                    # Skip hidden and common ignored directories
                    items = [x for x in items if not x.name.startswith('.') 
                            and x.name not in ['__pycache__', 'node_modules', 'venv']]
                    
                    for i, item in enumerate(items):
                        is_last = i == len(items) - 1
                        current_prefix = "└── " if is_last else "├── "
                        next_prefix = "    " if is_last else "│   "
                        
                        lines.append(f"{prefix}{current_prefix}{item.name}{'/' if item.is_dir() else ''}")
                        
                        if item.is_dir():
                            lines.extend(build_tree(item, prefix + next_prefix, depth + 1))
                except PermissionError as e:
                    logger.debug(f"Permission denied in directory tree: {e}")
                
                return lines
            
            tree_lines = [f"{dir_path.name}/"]
            tree_lines.extend(build_tree(dir_path))
            tree_str = '\n'.join(tree_lines)
            
            return ToolResult(
                success=True,
                data=tree_str,
                metadata={
                    "path": str(dir_path),
                    "max_depth": max_depth
                }
            )
        except Exception as e:
            return ToolResult(success=False, error=str(e))
