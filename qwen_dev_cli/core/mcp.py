"""MCP (Model Context Protocol) filesystem server manager."""

import json
from pathlib import Path
from typing import List, Optional, Dict
from .context import ContextBuilder


class MCPManager:
    """Manage MCP filesystem server integration.
    
    This is a simplified implementation that uses direct file injection
    instead of complex tool calling, based on validated approach from research.
    """
    
    def __init__(self, root_dir: Optional[str] = None):
        """Initialize MCP manager.
        
        Args:
            root_dir: Root directory for filesystem access (default: current dir)
        """
        self.root_dir = Path(root_dir or Path.cwd()).resolve()
        self.context_builder = ContextBuilder()
        self.enabled = True
    
    def list_files(self, pattern: str = "*.py", recursive: bool = True) -> List[str]:
        """List files in root directory.
        
        Args:
            pattern: Glob pattern for files
            recursive: Search recursively
            
        Returns:
            List of file paths (relative to root_dir)
        """
        try:
            if recursive:
                files = list(self.root_dir.rglob(pattern))
            else:
                files = list(self.root_dir.glob(pattern))
            
            # Filter out venv, .git, __pycache__
            filtered = []
            for f in files:
                rel_path = f.relative_to(self.root_dir)
                parts = rel_path.parts
                
                if any(p.startswith('.') or p in ['venv', 'env', '__pycache__', 'node_modules'] 
                       for p in parts):
                    continue
                
                filtered.append(str(f))
            
            return filtered
            
        except Exception as e:
            print(f"Error listing files: {e}")
            return []
    
    def get_file_info(self, file_path: str) -> Dict[str, any]:
        """Get file information.
        
        Args:
            file_path: Path to file
            
        Returns:
            Dictionary with file info
        """
        try:
            path = Path(file_path).resolve()
            
            if not path.exists():
                return {"error": "File not found"}
            
            stat = path.stat()
            
            return {
                "name": path.name,
                "path": str(path),
                "size": stat.st_size,
                "size_kb": stat.st_size / 1024,
                "modified": stat.st_mtime,
                "is_file": path.is_file(),
                "suffix": path.suffix
            }
            
        except Exception as e:
            return {"error": str(e)}
    
    def inject_files_to_context(self, file_paths: List[str]) -> Dict[str, str]:
        """Inject multiple files into context builder.
        
        Args:
            file_paths: List of file paths
            
        Returns:
            Dictionary of results
        """
        return self.context_builder.add_files(file_paths)
    
    def inject_pattern_to_context(self, pattern: str = "*.py") -> Dict[str, str]:
        """Inject files matching pattern to context.
        
        Args:
            pattern: Glob pattern
            
        Returns:
            Dictionary of results
        """
        files = self.list_files(pattern, recursive=False)
        
        if not files:
            return {"error": f"No files found matching: {pattern}"}
        
        # Limit to max_context_files
        max_files = self.context_builder.max_files
        if len(files) > max_files:
            files = files[:max_files]
        
        return self.inject_files_to_context(files)
    
    def get_context(self) -> str:
        """Get formatted context from all injected files.
        
        Returns:
            Formatted context string
        """
        return self.context_builder.get_context()
    
    def get_stats(self) -> Dict[str, any]:
        """Get MCP context statistics.
        
        Returns:
            Dictionary with stats
        """
        stats = self.context_builder.get_stats()
        stats["root_dir"] = str(self.root_dir)
        stats["enabled"] = self.enabled
        return stats
    
    def clear(self):
        """Clear all context."""
        self.context_builder.clear()
    
    def toggle(self, enabled: bool = True):
        """Enable or disable MCP.
        
        Args:
            enabled: True to enable, False to disable
        """
        self.enabled = enabled
    
    def as_tool_description(self) -> Dict[str, any]:
        """Get MCP filesystem server as tool description.
        
        Returns:
            Tool description dictionary
        """
        return {
            "name": "filesystem",
            "description": "Read files from the local filesystem",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to file to read"
                    },
                    "pattern": {
                        "type": "string",
                        "description": "Glob pattern for multiple files"
                    }
                }
            }
        }


# Global MCP manager instance
mcp_manager = MCPManager()
