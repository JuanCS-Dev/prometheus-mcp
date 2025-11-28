"""
Git Workflow Tools - Registry Facade
=====================================

This module provides backward-compatible imports for git workflow tools.

All implementations have been decomposed into focused modules under jdev_cli/tools/git/:
- safety.py: GitSafetyConfig, GitSafetyError, validate_git_command
- inspect_tools.py: GitStatusEnhancedTool, GitLogTool, GitDiffEnhancedTool
- mutate_tools.py: GitCommitTool, GitPRCreateTool

Refactored: Nov 2025 (841 -> 55 lines)
Author: JuanCS Dev
"""



# Re-export all tools from git submodules for backward compatibility
from jdev_cli.tools.git import (
    # Safety
    GitSafetyConfig,
    GitSafetyError,
    validate_git_command,
    get_safety_config,
    # Inspect Tools
    GitStatusEnhancedTool,
    GitLogTool,
    GitDiffEnhancedTool,
    # Mutate Tools
    GitCommitTool,
    GitPRCreateTool,
    # Registry
    get_git_workflow_tools,
)


__all__ = [
    # Safety
    "GitSafetyConfig",
    "GitSafetyError",
    "validate_git_command",
    "get_safety_config",
    # Inspect Tools
    "GitStatusEnhancedTool",
    "GitLogTool",
    "GitDiffEnhancedTool",
    # Mutate Tools
    "GitCommitTool",
    "GitPRCreateTool",
    # Registry
    "get_git_workflow_tools",
]
