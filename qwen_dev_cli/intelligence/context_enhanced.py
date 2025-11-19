"""Enhanced context with multi-source information (Cursor pattern).

Boris Cherny: Rich context = better decisions. Aggregate everything.
"""

import os
import json
import subprocess
from dataclasses import dataclass, field
from typing import Optional, Dict, List
from enum import Enum

from .types import Context


class ExpertiseLevel(Enum):
    """User expertise level (Claude pattern)."""
    
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    EXPERT = "expert"


class RiskTolerance(Enum):
    """User risk tolerance (Claude pattern)."""
    
    CAUTIOUS = "cautious"
    BALANCED = "balanced"
    AGGRESSIVE = "aggressive"


@dataclass(frozen=True)
class GitStatus:
    """Git repository status."""
    
    branch: Optional[str] = None
    staged_files: List[str] = field(default_factory=list)
    unstaged_files: List[str] = field(default_factory=list)
    untracked_files: List[str] = field(default_factory=list)
    has_remote: bool = False
    ahead: int = 0
    behind: int = 0


@dataclass(frozen=True)
class WorkspaceInfo:
    """Workspace/project information."""
    
    language: Optional[str] = None
    framework: Optional[str] = None
    dependencies: Dict[str, str] = field(default_factory=dict)
    has_tests: bool = False
    test_command: Optional[str] = None


@dataclass(frozen=True)
class TerminalInfo:
    """Terminal state information."""
    
    working_directory: str = "."
    last_exit_code: int = 0
    shell: str = "bash"


@dataclass(frozen=True)
class RichContext(Context):
    """Enhanced context with multi-source information.
    
    Combines patterns from:
    - Cursor: Multi-source context fusion
    - Claude: User expertise and preferences
    """
    
    # Git information
    git_status: Optional[GitStatus] = None
    
    # Workspace information
    workspace: Optional[WorkspaceInfo] = None
    
    # Terminal information
    terminal: Optional[TerminalInfo] = None
    
    # User preferences (Claude pattern)
    user_expertise: ExpertiseLevel = ExpertiseLevel.INTERMEDIATE
    risk_tolerance: RiskTolerance = RiskTolerance.BALANCED


def detect_git_status(working_dir: str = ".") -> Optional[GitStatus]:
    """Detect git repository status.
    
    Args:
        working_dir: Directory to check
        
    Returns:
        GitStatus if in git repo, None otherwise
    """
    try:
        # Check if in git repo
        subprocess.run(
            ["git", "rev-parse", "--git-dir"],
            cwd=working_dir,
            capture_output=True,
            check=True,
            timeout=2
        )
        
        # Get branch
        branch_result = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=working_dir,
            capture_output=True,
            text=True,
            timeout=2
        )
        branch = branch_result.stdout.strip() or None
        
        # Get status
        status_result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=working_dir,
            capture_output=True,
            text=True,
            timeout=2
        )
        
        staged = []
        unstaged = []
        untracked = []
        
        for line in status_result.stdout.splitlines():
            if not line.strip():
                continue
            
            status = line[:2]
            filename = line[3:]
            
            if status[0] in ['M', 'A', 'D', 'R', 'C']:
                staged.append(filename)
            if status[1] in ['M', 'D']:
                unstaged.append(filename)
            if status == '??':
                untracked.append(filename)
        
        # Check for remote
        remote_result = subprocess.run(
            ["git", "remote"],
            cwd=working_dir,
            capture_output=True,
            text=True,
            timeout=2
        )
        has_remote = bool(remote_result.stdout.strip())
        
        return GitStatus(
            branch=branch,
            staged_files=staged,
            unstaged_files=unstaged,
            untracked_files=untracked,
            has_remote=has_remote
        )
    
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
        return None


def detect_workspace(working_dir: str = ".") -> WorkspaceInfo:
    """Detect workspace type and configuration.
    
    Args:
        working_dir: Directory to analyze
        
    Returns:
        WorkspaceInfo with detected information
    """
    info = WorkspaceInfo()
    
    # Check for package.json (Node.js)
    package_json = os.path.join(working_dir, "package.json")
    if os.path.exists(package_json):
        try:
            with open(package_json) as f:
                pkg = json.load(f)
                deps = pkg.get('dependencies', {})
                dev_deps = pkg.get('devDependencies', {})
                scripts = pkg.get('scripts', {})
                
                # Detect framework
                framework = None
                if 'react' in deps:
                    framework = 'react'
                elif 'vue' in deps:
                    framework = 'vue'
                elif 'next' in deps:
                    framework = 'nextjs'
                elif 'express' in deps:
                    framework = 'express'
                
                # Detect test setup
                has_tests = 'test' in scripts or any(
                    t in dev_deps for t in ['jest', 'vitest', 'mocha']
                )
                test_cmd = scripts.get('test', 'npm test') if has_tests else None
                
                info = WorkspaceInfo(
                    language='javascript',
                    framework=framework,
                    dependencies=deps,
                    has_tests=has_tests,
                    test_command=test_cmd
                )
        except (json.JSONDecodeError, IOError) as e:
            logger.debug(f"Failed to parse package.json: {e}")
    
    # Check for requirements.txt (Python)
    requirements = os.path.join(working_dir, "requirements.txt")
    if os.path.exists(requirements):
        try:
            with open(requirements) as f:
                reqs = f.read().lower()
                
                framework = None
                if 'django' in reqs:
                    framework = 'django'
                elif 'flask' in reqs:
                    framework = 'flask'
                elif 'fastapi' in reqs:
                    framework = 'fastapi'
                
                has_tests = 'pytest' in reqs or 'unittest' in reqs
                test_cmd = 'pytest' if 'pytest' in reqs else 'python -m unittest'
                
                info = WorkspaceInfo(
                    language='python',
                    framework=framework,
                    has_tests=has_tests,
                    test_command=test_cmd if has_tests else None
                )
        except IOError as e:
            logger.debug(f"Failed to read requirements.txt: {e}")
    
    # Check for Cargo.toml (Rust)
    cargo_toml = os.path.join(working_dir, "Cargo.toml")
    if os.path.exists(cargo_toml):
        info = WorkspaceInfo(
            language='rust',
            has_tests=True,
            test_command='cargo test'
        )
    
    # Check for go.mod (Go)
    go_mod = os.path.join(working_dir, "go.mod")
    if os.path.exists(go_mod):
        info = WorkspaceInfo(
            language='go',
            has_tests=True,
            test_command='go test ./...'
        )
    
    return info


def build_rich_context(
    current_command: Optional[str] = None,
    command_history: Optional[List[str]] = None,
    recent_errors: Optional[List[str]] = None,
    working_dir: str = "."
) -> RichContext:
    """Build rich context from multiple sources.
    
    Args:
        current_command: Current command being typed
        command_history: Recent command history
        recent_errors: Recent error messages
        working_dir: Working directory
        
    Returns:
        RichContext with all available information
    """
    git_status = detect_git_status(working_dir)
    workspace = detect_workspace(working_dir)
    terminal = TerminalInfo(working_directory=working_dir)
    
    return RichContext(
        current_command=current_command,
        command_history=command_history or [],
        recent_errors=recent_errors or [],
        working_directory=working_dir,
        git_branch=git_status.branch if git_status else None,
        recent_files=[],  # File tracking would require filesystem watcher
        environment={},   # Env vars accessible via os.environ if needed
        git_status=git_status,
        workspace=workspace,
        terminal=terminal
    )
