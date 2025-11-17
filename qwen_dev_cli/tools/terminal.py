"""Terminal navigation and basic commands."""

import os
import shutil
from pathlib import Path
from typing import Optional

from .base import Tool, ToolResult, ToolCategory


class CdTool(Tool):
    """Change directory."""
    
    def __init__(self):
        super().__init__()
        self.category = ToolCategory.EXECUTION
        self.description = "Change current working directory"
        self.parameters = {
            "path": {
                "type": "string",
                "description": "Directory path to change to (. for current, .. for parent, ~ for home)",
                "required": True
            }
        }
    
    async def execute(self, path: str) -> ToolResult:
        """Change directory."""
        try:
            # Expand special paths
            if path == "~":
                path = str(Path.home())
            elif path == "..":
                path = str(Path.cwd().parent)
            elif path == ".":
                path = str(Path.cwd())
            
            target = Path(path).expanduser().resolve()
            
            if not target.exists():
                return ToolResult(
                    success=False,
                    error=f"Directory not found: {path}"
                )
            
            if not target.is_dir():
                return ToolResult(
                    success=False,
                    error=f"Not a directory: {path}"
                )
            
            # Change directory
            os.chdir(target)
            
            return ToolResult(
                success=True,
                data=f"Changed directory to {target}",
                metadata={
                    "old_cwd": str(Path.cwd()),
                    "new_cwd": str(target)
                }
            )
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class LsTool(Tool):
    """List directory contents (like ls command)."""
    
    def __init__(self):
        super().__init__()
        self.category = ToolCategory.FILE_READ
        self.description = "List directory contents (like ls command)"
        self.parameters = {
            "path": {
                "type": "string",
                "description": "Directory path to list (default: current directory)",
                "required": False
            },
            "all": {
                "type": "boolean",
                "description": "Show hidden files (like ls -a)",
                "required": False
            },
            "long": {
                "type": "boolean",
                "description": "Show detailed information (like ls -l)",
                "required": False
            }
        }
    
    async def execute(self, path: str = ".", all: bool = False, long: bool = False) -> ToolResult:
        """List directory contents."""
        try:
            dir_path = Path(path).expanduser().resolve()
            
            if not dir_path.exists():
                return ToolResult(
                    success=False,
                    error=f"Directory not found: {path}"
                )
            
            if not dir_path.is_dir():
                return ToolResult(
                    success=False,
                    error=f"Not a directory: {path}"
                )
            
            # List items
            items = []
            for item in sorted(dir_path.iterdir()):
                # Skip hidden files unless -a
                if not all and item.name.startswith('.'):
                    continue
                
                item_info = {
                    "name": item.name,
                    "type": "dir" if item.is_dir() else "file"
                }
                
                if long:
                    stat = item.stat()
                    item_info.update({
                        "size": stat.st_size,
                        "permissions": oct(stat.st_mode)[-3:],
                        "modified": stat.st_mtime
                    })
                
                items.append(item_info)
            
            return ToolResult(
                success=True,
                data=items,
                metadata={
                    "path": str(dir_path),
                    "count": len(items),
                    "show_all": all,
                    "long_format": long
                }
            )
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class PwdTool(Tool):
    """Print working directory."""
    
    def __init__(self):
        super().__init__()
        self.category = ToolCategory.EXECUTION
        self.description = "Print current working directory (pwd)"
        self.parameters = {}
    
    async def execute(self) -> ToolResult:
        """Get current directory."""
        try:
            cwd = Path.cwd()
            return ToolResult(
                success=True,
                data=str(cwd),
                metadata={"cwd": str(cwd)}
            )
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class MkdirTool(Tool):
    """Make directory (mkdir)."""
    
    def __init__(self):
        super().__init__()
        self.category = ToolCategory.FILE_MGMT
        self.description = "Create directory (mkdir)"
        self.parameters = {
            "path": {
                "type": "string",
                "description": "Directory path to create",
                "required": True
            },
            "parents": {
                "type": "boolean",
                "description": "Create parent directories if needed (mkdir -p)",
                "required": False
            }
        }
    
    async def execute(self, path: str, parents: bool = True) -> ToolResult:
        """Create directory."""
        try:
            dir_path = Path(path).expanduser()
            
            if dir_path.exists():
                return ToolResult(
                    success=False,
                    error=f"Directory already exists: {path}"
                )
            
            dir_path.mkdir(parents=parents, exist_ok=False)
            
            return ToolResult(
                success=True,
                data=f"Created directory: {path}",
                metadata={"path": str(dir_path)}
            )
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class RmTool(Tool):
    """Remove file or directory (rm)."""
    
    def __init__(self):
        super().__init__()
        self.category = ToolCategory.FILE_MGMT
        self.description = "Remove file or directory (rm)"
        self.parameters = {
            "path": {
                "type": "string",
                "description": "Path to remove",
                "required": True
            },
            "recursive": {
                "type": "boolean",
                "description": "Remove directories recursively (rm -r)",
                "required": False
            },
            "force": {
                "type": "boolean",
                "description": "Force removal without confirmation (rm -f)",
                "required": False
            }
        }
    
    async def execute(self, path: str, recursive: bool = False, force: bool = False) -> ToolResult:
        """Remove file/directory."""
        try:
            target = Path(path).expanduser()
            
            if not target.exists():
                if force:
                    return ToolResult(
                        success=True,
                        data=f"Path does not exist (ignored with -f): {path}"
                    )
                return ToolResult(
                    success=False,
                    error=f"Path not found: {path}"
                )
            
            # Safety check - prevent removing important directories
            dangerous_paths = ["/", str(Path.home()), "/usr", "/etc", "/var"]
            if str(target.resolve()) in dangerous_paths:
                return ToolResult(
                    success=False,
                    error=f"Refusing to remove protected directory: {path}"
                )
            
            if target.is_dir():
                if not recursive:
                    return ToolResult(
                        success=False,
                        error=f"Cannot remove directory without -r flag: {path}"
                    )
                shutil.rmtree(target)
            else:
                target.unlink()
            
            return ToolResult(
                success=True,
                data=f"Removed: {path}",
                metadata={
                    "path": str(target),
                    "type": "directory" if target.is_dir() else "file"
                }
            )
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class CpTool(Tool):
    """Copy file or directory (cp)."""
    
    def __init__(self):
        super().__init__()
        self.category = ToolCategory.FILE_MGMT
        self.description = "Copy file or directory (cp)"
        self.parameters = {
            "source": {
                "type": "string",
                "description": "Source path",
                "required": True
            },
            "destination": {
                "type": "string",
                "description": "Destination path",
                "required": True
            },
            "recursive": {
                "type": "boolean",
                "description": "Copy directories recursively (cp -r)",
                "required": False
            }
        }
    
    async def execute(self, source: str, destination: str, recursive: bool = False) -> ToolResult:
        """Copy file/directory."""
        try:
            src = Path(source).expanduser()
            dst = Path(destination).expanduser()
            
            if not src.exists():
                return ToolResult(
                    success=False,
                    error=f"Source not found: {source}"
                )
            
            if src.is_dir():
                if not recursive:
                    return ToolResult(
                        success=False,
                        error=f"Cannot copy directory without -r flag: {source}"
                    )
                shutil.copytree(src, dst)
            else:
                shutil.copy2(src, dst)
            
            return ToolResult(
                success=True,
                data=f"Copied {source} → {destination}",
                metadata={
                    "source": str(src),
                    "destination": str(dst),
                    "type": "directory" if src.is_dir() else "file"
                }
            )
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class MvTool(Tool):
    """Move/rename file or directory (mv)."""
    
    def __init__(self):
        super().__init__()
        self.category = ToolCategory.FILE_MGMT
        self.description = "Move or rename file/directory (mv)"
        self.parameters = {
            "source": {
                "type": "string",
                "description": "Source path",
                "required": True
            },
            "destination": {
                "type": "string",
                "description": "Destination path",
                "required": True
            }
        }
    
    async def execute(self, source: str, destination: str) -> ToolResult:
        """Move/rename file/directory."""
        try:
            src = Path(source).expanduser()
            dst = Path(destination).expanduser()
            
            if not src.exists():
                return ToolResult(
                    success=False,
                    error=f"Source not found: {source}"
                )
            
            shutil.move(str(src), str(dst))
            
            return ToolResult(
                success=True,
                data=f"Moved {source} → {destination}",
                metadata={
                    "source": str(src),
                    "destination": str(dst)
                }
            )
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class TouchTool(Tool):
    """Create empty file or update timestamp (touch)."""
    
    def __init__(self):
        super().__init__()
        self.category = ToolCategory.FILE_WRITE
        self.description = "Create empty file or update timestamp (touch)"
        self.parameters = {
            "path": {
                "type": "string",
                "description": "File path",
                "required": True
            }
        }
    
    async def execute(self, path: str) -> ToolResult:
        """Touch file."""
        try:
            file_path = Path(path).expanduser()
            
            if file_path.exists():
                # Update timestamp
                file_path.touch()
                action = "Updated timestamp"
            else:
                # Create empty file
                file_path.touch()
                action = "Created file"
            
            return ToolResult(
                success=True,
                data=f"{action}: {path}",
                metadata={"path": str(file_path)}
            )
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class CatTool(Tool):
    """Display file contents (cat)."""
    
    def __init__(self):
        super().__init__()
        self.category = ToolCategory.FILE_READ
        self.description = "Display file contents (cat)"
        self.parameters = {
            "path": {
                "type": "string",
                "description": "File path to display",
                "required": True
            },
            "lines": {
                "type": "integer",
                "description": "Number of lines to show (head -n)",
                "required": False
            }
        }
    
    async def execute(self, path: str, lines: Optional[int] = None) -> ToolResult:
        """Display file contents."""
        try:
            file_path = Path(path).expanduser()
            
            if not file_path.exists():
                return ToolResult(
                    success=False,
                    error=f"File not found: {path}"
                )
            
            if not file_path.is_file():
                return ToolResult(
                    success=False,
                    error=f"Not a file: {path}"
                )
            
            content = file_path.read_text()
            
            if lines:
                content_lines = content.split('\n')
                content = '\n'.join(content_lines[:lines])
            
            return ToolResult(
                success=True,
                data=content,
                metadata={
                    "path": str(file_path),
                    "size": file_path.stat().st_size,
                    "lines": len(content.split('\n'))
                }
            )
        except Exception as e:
            return ToolResult(success=False, error=str(e))
