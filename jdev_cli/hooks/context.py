"""Hook execution context with variable substitution."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict
from datetime import datetime


@dataclass
class HookContext:
    """Context information passed to hook executors.
    
    Provides all necessary information for variable substitution
    in hook commands (e.g., {file}, {dir}, {project_name}).
    
    Attributes:
        file_path: Full path to the file that triggered the hook
        event_name: Name of the event (post_write, post_edit, etc)
        cwd: Current working directory
        project_name: Name of the project (from config)
        timestamp: When the hook was triggered
        metadata: Additional event-specific metadata
    """

    file_path: Path
    event_name: str
    cwd: Path = field(default_factory=Path.cwd)
    project_name: str = "unknown"
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, str] = field(default_factory=dict)

    @property
    def file(self) -> str:
        """Full file path as string."""
        return str(self.file_path)

    @property
    def file_name(self) -> str:
        """File name with extension (e.g., 'test.py')."""
        return self.file_path.name

    @property
    def file_stem(self) -> str:
        """File name without extension (e.g., 'test')."""
        return self.file_path.stem

    @property
    def file_extension(self) -> str:
        """File extension without dot (e.g., 'py')."""
        return self.file_path.suffix.lstrip('.')

    @property
    def dir(self) -> str:
        """Directory path containing the file."""
        return str(self.file_path.parent)

    @property
    def relative_path(self) -> str:
        """File path relative to cwd."""
        try:
            return str(self.file_path.relative_to(self.cwd))
        except ValueError:
            return str(self.file_path)

    def get_variables(self) -> Dict[str, str]:
        """Get all available variables for substitution.
        
        Returns:
            Dictionary mapping variable names to their values.
            
        Example:
            >>> ctx = HookContext(Path("src/utils/helper.py"), "post_write")
            >>> ctx.get_variables()
            {
                "file": "/path/to/src/utils/helper.py",
                "file_name": "helper.py",
                "file_stem": "helper",
                "file_extension": "py",
                "dir": "/path/to/src/utils",
                "relative_path": "src/utils/helper.py",
                "cwd": "/path/to",
                "project_name": "unknown",
                "event": "post_write"
            }
        """
        return {
            "file": self.file,
            "file_name": self.file_name,
            "file_stem": self.file_stem,
            "file_extension": self.file_extension,
            "dir": self.dir,
            "relative_path": self.relative_path,
            "cwd": str(self.cwd),
            "project_name": self.project_name,
            "event": self.event_name,
            **self.metadata
        }
