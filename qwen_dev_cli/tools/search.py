"""Search and navigation tools."""

import subprocess
from pathlib import Path
from typing import Optional

from .base import Tool, ToolResult, ToolCategory


class SearchFilesTool(Tool):
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
            }
        }
    
    async def execute(self, pattern: str, path: str = ".", file_pattern: Optional[str] = None, max_results: int = 50) -> ToolResult:
        """Search for pattern in files."""
        try:
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


class GetDirectoryTreeTool(Tool):
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
    
    async def execute(self, path: str = ".", max_depth: int = 3) -> ToolResult:
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
