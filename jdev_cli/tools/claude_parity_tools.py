"""
Claude Code Parity Tools - Registry Facade
==========================================

This module provides backward-compatible imports for Claude Code parity tools.

All implementations have been decomposed into focused modules under jdev_cli/tools/parity/:
- file_tools.py: GlobTool, LSTool, MultiEditTool
- web_tools.py: WebFetchTool, WebSearchTool
- notebook_tools.py: NotebookReadTool, NotebookEditTool
- todo_tools.py: TodoReadTool, TodoWriteTool
- execution_tools.py: BackgroundTaskTool, BashOutputTool, KillShellTool
- interaction_tools.py: AskUserQuestionTool, SkillTool, SlashCommandTool
- task_tool.py: TaskTool

Refactored: Nov 2025 (2069 -> 80 lines)
Author: JuanCS Dev
"""



# Re-export all tools from parity submodules for backward compatibility
from jdev_cli.tools.parity import (
    # File Tools
    GlobTool,
    LSTool,
    MultiEditTool,
    # Web Tools
    WebFetchTool,
    WebSearchTool,
    # Notebook Tools
    NotebookReadTool,
    NotebookEditTool,
    # Todo Tools
    TodoReadTool,
    TodoWriteTool,
    # Execution Tools
    BackgroundTaskTool,
    BashOutputTool,
    KillShellTool,
    # Interaction Tools
    AskUserQuestionTool,
    SkillTool,
    SlashCommandTool,
    # Task/Subagent Tool
    TaskTool,
    # Registry function
    get_claude_parity_tools,
)


__all__ = [
    # File Tools
    "GlobTool",
    "LSTool",
    "MultiEditTool",
    # Web Tools
    "WebFetchTool",
    "WebSearchTool",
    # Notebook Tools
    "NotebookReadTool",
    "NotebookEditTool",
    # Todo Tools
    "TodoReadTool",
    "TodoWriteTool",
    # Execution Tools
    "BackgroundTaskTool",
    "BashOutputTool",
    "KillShellTool",
    # Interaction Tools
    "AskUserQuestionTool",
    "SkillTool",
    "SlashCommandTool",
    # Task/Subagent Tool
    "TaskTool",
    # Registry
    "get_claude_parity_tools",
]
