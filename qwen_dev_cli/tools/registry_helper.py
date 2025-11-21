"""Helper to create default registry instance."""
from qwen_dev_cli.tools.base import ToolRegistry
from qwen_dev_cli.tools.file_ops import (
    ReadFileTool, WriteFileTool, EditFileTool,
    ListDirectoryTool, DeleteFileTool
)
from qwen_dev_cli.tools.file_mgmt import (
    MoveFileTool, CopyFileTool, CreateDirectoryTool,
    ReadMultipleFilesTool, InsertLinesTool
)
from qwen_dev_cli.tools.search import SearchFilesTool, GetDirectoryTreeTool
from qwen_dev_cli.tools.exec_hardened import BashCommandTool
from qwen_dev_cli.tools.git_ops import GitStatusTool, GitDiffTool
from qwen_dev_cli.tools.context import GetContextTool, SaveSessionTool, RestoreBackupTool
from qwen_dev_cli.tools.terminal import (
    CdTool, LsTool, PwdTool, MkdirTool, RmTool,
    CpTool, MvTool, TouchTool, CatTool
)


def get_default_registry() -> ToolRegistry:
    """Create and populate default tool registry."""
    registry = ToolRegistry()
    
    tools = [
        ReadFileTool(), WriteFileTool(), EditFileTool(),
        ListDirectoryTool(), DeleteFileTool(),
        MoveFileTool(), CopyFileTool(), CreateDirectoryTool(),
        ReadMultipleFilesTool(), InsertLinesTool(),
        SearchFilesTool(), GetDirectoryTreeTool(),
        BashCommandTool(),
        GitStatusTool(), GitDiffTool(),
        GetContextTool(), SaveSessionTool(), RestoreBackupTool(),
        CdTool(), LsTool(), PwdTool(), MkdirTool(), RmTool(),
        CpTool(), MvTool(), TouchTool(), CatTool(),
    ]
    
    for tool in tools:
        registry.register(tool)
    
    return registry
