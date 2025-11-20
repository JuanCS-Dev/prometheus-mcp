"""File operation tools - read, write, edit files."""

import os
import shutil
from pathlib import Path
from typing import Optional
from datetime import datetime
import logging

from .base import Tool, ToolResult, ToolCategory

logger = logging.getLogger(__name__)


class ReadFileTool(Tool):
    """Read complete contents of a file."""
    
    def __init__(self):
        super().__init__()
        self.category = ToolCategory.FILE_READ
        self.description = "Read complete contents of a file"
        self.parameters = {
            "path": {
                "type": "string",
                "description": "File path relative to current directory",
                "required": True
            },
            "line_range": {
                "type": "array",
                "description": "Optional [start, end] line range to read",
                "required": False
            }
        }
    
    async def execute(self, path: str, line_range: Optional[tuple] = None) -> ToolResult:
        """Read file contents."""
        try:
            file_path = Path(path)
            
            if not file_path.exists():
                return ToolResult(
                    success=False,
                    error=f"File not found: {path}"
                )
            
            if not file_path.is_file():
                return ToolResult(
                    success=False,
                    error=f"Path is not a file: {path}"
                )
            
            content = file_path.read_text()
            lines = content.split('\n')
            
            # Apply line range if specified
            if line_range and len(line_range) == 2:
                start, end = line_range
                lines = lines[start-1:end]  # 1-indexed
                content = '\n'.join(lines)
            
            # Detect language
            suffix = file_path.suffix.lstrip('.')
            lang_map = {
                'py': 'python', 'js': 'javascript', 'ts': 'typescript',
                'java': 'java', 'cpp': 'cpp', 'c': 'c', 'go': 'go',
                'rs': 'rust', 'rb': 'ruby', 'php': 'php'
            }
            language = lang_map.get(suffix, suffix or 'text')
            
            return ToolResult(
                success=True,
                data=content,
                metadata={
                    "path": str(file_path),
                    "lines": len(lines),
                    "language": language,
                    "size": file_path.stat().st_size
                }
            )
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class WriteFileTool(Tool):
    """Create new file with content."""
    
    def __init__(self, hook_executor=None, config_loader=None):
        super().__init__()
        self.category = ToolCategory.FILE_WRITE
        self.description = "Create new file with content (fails if file exists)"
        self.hook_executor = hook_executor
        self.config_loader = config_loader
        self.parameters = {
            "path": {
                "type": "string",
                "description": "File path to create",
                "required": True
            },
            "content": {
                "type": "string",
                "description": "File content",
                "required": True
            },
            "create_dirs": {
                "type": "boolean",
                "description": "Create parent directories if needed",
                "required": False
            }
        }
    
    async def execute(self, path: str, content: str, create_dirs: bool = True, 
                     preview: bool = True, console=None) -> ToolResult:
        """Create file with content."""
        try:
            file_path = Path(path)
            
            # Show preview if file exists (Integration Sprint Week 1: Task 1.3)
            if file_path.exists():
                if preview and console:
                    from ..tui.components.preview import EditPreview
                    
                    original_content = file_path.read_text()
                    preview_component = EditPreview()
                    accepted = await preview_component.show_diff_interactive(
                        original_content=original_content,
                        proposed_content=content,
                        file_path=str(file_path),
                        console=console
                    )
                    
                    if not accepted:
                        return ToolResult(
                            success=False,
                            data={"path": str(path), "message": "Overwrite cancelled by user"},
                            error="Overwrite cancelled by user"
                        )
                else:
                    return ToolResult(
                        success=False,
                        error=f"File already exists: {path}. Use edit_file to modify."
                    )
            
            # Create parent directories if needed
            if create_dirs and not file_path.parent.exists():
                file_path.parent.mkdir(parents=True, exist_ok=True)
            
            file_path.write_text(content)
            
            result = ToolResult(
                success=True,
                data=f"Created {path}",
                metadata={
                    "path": str(file_path),
                    "size": len(content),
                    "lines": len(content.split('\n'))
                }
            )
            
            # Execute post_write hooks
            await self._execute_hooks("post_write", file_path)
            
            return result
        except Exception as e:
            return ToolResult(success=False, error=str(e))
    
    async def _execute_hooks(self, event_name: str, file_path: Path):
        """Execute hooks for this event."""
        if not self.hook_executor or not self.config_loader:
            return
        
        try:
            from qwen_dev_cli.hooks import HookEvent, HookContext
            
            # Get hooks from config
            config = self.config_loader.config
            if not config or not config.hooks:
                return
            
            hooks_to_run = getattr(config.hooks, event_name, [])
            if not hooks_to_run:
                return
            
            # Create context
            context = HookContext(
                file_path=file_path,
                event_name=event_name,
                cwd=Path.cwd(),
                project_name=config.project.name if config.project else "unknown"
            )
            
            # Execute hooks
            event = HookEvent(event_name)
            results = await self.hook_executor.execute_hooks(event, context, hooks_to_run)
            
            # Log results
            for result in results:
                if result.success:
                    logger.debug(f"Hook succeeded: {result.command}")
                else:
                    logger.warning(f"Hook failed: {result.command} - {result.error}")
                    
        except Exception as e:
            logger.error(f"Error executing hooks: {e}")


class EditFileTool(Tool):
    """Modify existing file using search/replace."""
    
    def __init__(self, hook_executor=None, config_loader=None):
        super().__init__()
        self.category = ToolCategory.FILE_WRITE
        self.description = "Modify existing file using search/replace blocks"
        self.hook_executor = hook_executor
        self.config_loader = config_loader
        self.parameters = {
            "path": {
                "type": "string",
                "description": "File path to edit",
                "required": True
            },
            "edits": {
                "type": "array",
                "description": "Array of {search, replace} edit operations",
                "required": True
            },
            "create_backup": {
                "type": "boolean",
                "description": "Create backup before editing",
                "required": False
            }
        }
    
    async def execute(self, path: str, edits: list[dict], create_backup: bool = True, 
                     preview: bool = True, console=None) -> ToolResult:
        """Edit file with search/replace operations."""
        try:
            file_path = Path(path)
            
            if not file_path.exists():
                return ToolResult(
                    success=False,
                    error=f"File not found: {path}"
                )
            
            # Read current content
            original_content = file_path.read_text()
            modified_content = original_content
            
            # Create backup
            backup_path = None
            if create_backup:
                backup_dir = Path(".qwen_backups")
                backup_dir.mkdir(exist_ok=True)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_path = backup_dir / f"{file_path.name}.{timestamp}.bak"
                backup_path.write_text(original_content)
            
            # Apply edits
            changes = 0
            for edit in edits:
                search = edit.get('search', '')
                replace = edit.get('replace', '')
                
                if search in modified_content:
                    modified_content = modified_content.replace(search, replace, 1)
                    changes += 1
                else:
                    return ToolResult(
                        success=False,
                        error=f"Search string not found: {search[:50]}..."
                    )
            
            # Show preview if enabled (Integration Sprint Week 1: Task 1.3)
            if preview and console and original_content != modified_content:
                from ..tui.components.preview import EditPreview
                
                preview_component = EditPreview()
                accepted = await preview_component.show_diff_interactive(
                    original_content=original_content,
                    proposed_content=modified_content,
                    file_path=str(file_path),
                    console=console
                )
                
                if not accepted:
                    return ToolResult(
                        success=False,
                        data={"path": str(path), "message": "Edit cancelled by user"},
                        error="Edit cancelled by user"
                    )
            
            # Write modified content
            file_path.write_text(modified_content)
            
            result = ToolResult(
                success=True,
                data=f"Applied {changes} edits to {path}",
                metadata={
                    "path": str(file_path),
                    "backup": str(backup_path) if backup_path else None,
                    "changes": changes,
                    "lines_before": len(original_content.split('\n')),
                    "lines_after": len(modified_content.split('\n'))
                }
            )
            
            # Execute post_edit hooks
            await self._execute_hooks("post_edit", file_path)
            
            return result
        except Exception as e:
            return ToolResult(success=False, error=str(e))
    
    async def _execute_hooks(self, event_name: str, file_path: Path):
        """Execute hooks for this event."""
        if not self.hook_executor or not self.config_loader:
            return
        
        try:
            from qwen_dev_cli.hooks import HookEvent, HookContext
            
            # Get hooks from config
            config = self.config_loader.config
            if not config or not config.hooks:
                return
            
            hooks_to_run = getattr(config.hooks, event_name, [])
            if not hooks_to_run:
                return
            
            # Create context
            context = HookContext(
                file_path=file_path,
                event_name=event_name,
                cwd=Path.cwd(),
                project_name=config.project.name if config.project else "unknown"
            )
            
            # Execute hooks
            event = HookEvent(event_name)
            results = await self.hook_executor.execute_hooks(event, context, hooks_to_run)
            
            # Log results
            for result in results:
                if result.success:
                    logger.debug(f"Hook succeeded: {result.command}")
                else:
                    logger.warning(f"Hook failed: {result.command} - {result.error}")
                    
        except Exception as e:
            logger.error(f"Error executing hooks: {e}")


class ListDirectoryTool(Tool):
    """List files and directories."""
    
    def __init__(self):
        super().__init__()
        self.category = ToolCategory.FILE_READ
        self.description = "List files and directories"
        self.parameters = {
            "path": {
                "type": "string",
                "description": "Directory path to list",
                "required": False
            },
            "recursive": {
                "type": "boolean",
                "description": "List recursively",
                "required": False
            },
            "pattern": {
                "type": "string",
                "description": "Glob pattern to filter (e.g., '*.py')",
                "required": False
            }
        }
    
    async def execute(self, path: str = ".", recursive: bool = False, pattern: Optional[str] = None) -> ToolResult:
        """List directory contents."""
        try:
            dir_path = Path(path)
            
            if not dir_path.exists():
                return ToolResult(
                    success=False,
                    error=f"Directory not found: {path}"
                )
            
            if not dir_path.is_dir():
                return ToolResult(
                    success=False,
                    error=f"Path is not a directory: {path}"
                )
            
            # List files
            if pattern:
                if recursive:
                    files = list(dir_path.rglob(pattern))
                else:
                    files = list(dir_path.glob(pattern))
            else:
                if recursive:
                    files = list(dir_path.rglob("*"))
                else:
                    files = list(dir_path.glob("*"))
            
            # Format results
            file_list = []
            dir_list = []
            
            for f in files:
                if f.name.startswith('.'):
                    continue  # Skip hidden files
                
                info = {
                    "name": f.name,
                    "path": str(f.relative_to(dir_path)),
                    "type": "directory" if f.is_dir() else "file",
                    "size": f.stat().st_size if f.is_file() else 0
                }
                
                if f.is_dir():
                    dir_list.append(info)
                else:
                    file_list.append(info)
            
            return ToolResult(
                success=True,
                data={
                    "files": file_list,
                    "directories": dir_list
                },
                metadata={
                    "path": str(dir_path),
                    "file_count": len(file_list),
                    "dir_count": len(dir_list)
                }
            )
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class DeleteFileTool(Tool):
    """Delete file (moves to .trash for safety)."""
    
    def __init__(self):
        super().__init__()
        self.category = ToolCategory.FILE_MGMT
        self.description = "Delete file (moves to .trash/ for safety)"
        self.parameters = {
            "path": {
                "type": "string",
                "description": "File path to delete",
                "required": True
            },
            "permanent": {
                "type": "boolean",
                "description": "Permanently delete (skip trash)",
                "required": False
            }
        }
    
    async def execute(self, path: str, permanent: bool = False) -> ToolResult:
        """Delete file."""
        try:
            file_path = Path(path)
            
            if not file_path.exists():
                return ToolResult(
                    success=False,
                    error=f"File not found: {path}"
                )
            
            if permanent:
                # Permanent delete
                if file_path.is_dir():
                    shutil.rmtree(file_path)
                else:
                    file_path.unlink()
                
                return ToolResult(
                    success=True,
                    data=f"Permanently deleted {path}",
                    metadata={"path": str(file_path), "permanent": True}
                )
            else:
                # Move to trash
                trash_dir = Path(".trash")
                trash_dir.mkdir(exist_ok=True)
                
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                trash_path = trash_dir / f"{file_path.name}.{timestamp}"
                
                shutil.move(str(file_path), str(trash_path))
                
                return ToolResult(
                    success=True,
                    data=f"Moved {path} to trash",
                    metadata={
                        "path": str(file_path),
                        "trash_path": str(trash_path),
                        "permanent": False
                    }
                )
        except Exception as e:
            return ToolResult(success=False, error=str(e))
