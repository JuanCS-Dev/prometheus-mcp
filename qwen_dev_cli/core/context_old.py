"""Context builder for injecting file contents into prompts."""

import os
from pathlib import Path
from typing import List, Optional, Dict
from .config import config


class ContextBuilder:
    """Build rich context from environment for LLM prompts."""
    
    def __init__(self, max_files: Optional[int] = None, max_file_size_kb: Optional[int] = None):
        """Initialize context builder.
        
        Args:
            max_files: Maximum number of files to include
            max_file_size_kb: Maximum file size in KB
        """
        self.max_files = max_files or config.max_context_files
        self.max_file_size_kb = max_file_size_kb or config.max_file_size_kb
        self.files: Dict[str, str] = {}
        self._git_cache = None
        self._env_cache = None
    
    def read_file(self, file_path: str) -> tuple[bool, str, str]:
        """Read a single file.
        
        Args:
            file_path: Path to file (relative or absolute)
            
        Returns:
            Tuple of (success, content, error_message)
        """
        try:
            path = Path(file_path).resolve()
            
            # Validate file exists
            if not path.exists():
                return False, "", f"File not found: {file_path}"
            
            if not path.is_file():
                return False, "", f"Not a file: {file_path}"
            
            # Check file size
            size_kb = path.stat().st_size / 1024
            if size_kb > self.max_file_size_kb:
                return False, "", f"File too large: {size_kb:.1f}KB (max: {self.max_file_size_kb}KB)"
            
            # Read file content
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            return True, content, ""
            
        except UnicodeDecodeError:
            return False, "", f"Cannot read binary file: {file_path}"
        except PermissionError:
            return False, "", f"Permission denied: {file_path}"
        except Exception as e:
            return False, "", f"Error reading file: {str(e)}"
    
    def add_file(self, file_path: str) -> tuple[bool, str]:
        """Add a file to context.
        
        Args:
            file_path: Path to file
            
        Returns:
            Tuple of (success, message)
        """
        # Check file limit
        if len(self.files) >= self.max_files:
            return False, f"Maximum files reached ({self.max_files})"
        
        # Read file
        success, content, error = self.read_file(file_path)
        
        if not success:
            return False, error
        
        # Store with relative path as key
        path = Path(file_path).resolve()
        key = str(path)
        self.files[key] = content
        
        return True, f"Added: {path.name}"
    
    def add_files(self, file_paths: List[str]) -> Dict[str, str]:
        """Add multiple files to context.
        
        Args:
            file_paths: List of file paths
            
        Returns:
            Dictionary of file_path -> result message
        """
        results = {}
        
        for file_path in file_paths:
            success, message = self.add_file(file_path)
            results[file_path] = message
        
        return results
    
    def clear(self):
        """Clear all files from context."""
        self.files.clear()
    
    def get_context(self) -> str:
        """Get formatted context string.
        
        Returns:
            Formatted context with all files
        """
        if not self.files:
            return ""
        
        context_parts = ["Here are the relevant files:\n"]
        
        for file_path, content in self.files.items():
            path = Path(file_path)
            context_parts.append(f"\n## File: {path.name}")
            context_parts.append(f"Path: {file_path}")
            context_parts.append(f"\n```{path.suffix[1:] if path.suffix else ''}")
            context_parts.append(content)
            context_parts.append("```\n")
        
        return "\n".join(context_parts)
    
    def inject_to_prompt(self, prompt: str) -> str:
        """Inject context into user prompt.
        
        Args:
            prompt: User's original prompt
            
        Returns:
            Prompt with context injected
        """
        context = self.get_context()
        
        if not context:
            return prompt
        
        return f"{context}\n\n---\n\n{prompt}"
    
    def get_stats(self) -> Dict[str, any]:
        """Get context statistics.
        
        Returns:
            Dictionary with stats
        """
        total_chars = sum(len(content) for content in self.files.values())
        total_lines = sum(content.count('\n') + 1 for content in self.files.values())
        
        return {
            "files": len(self.files),
            "max_files": self.max_files,
            "total_chars": total_chars,
            "total_lines": total_lines,
            "approx_tokens": total_chars // 4
        }


# Global context builder instance
context_builder = ContextBuilder()

    def get_git_context(self) -> Dict[str, any]:
        """Get git repository context."""
        if self._git_cache:
            return self._git_cache
        
        import subprocess
        
        context = {
            'is_git_repo': False,
            'branch': None,
            'status': None,
            'recent_commits': [],
            'uncommitted_changes': False
        }
        
        try:
            # Check if in git repo
            result = subprocess.run(
                ['git', 'rev-parse', '--git-dir'],
                capture_output=True,
                text=True,
                timeout=2
            )
            
            if result.returncode == 0:
                context['is_git_repo'] = True
                
                # Get current branch
                result = subprocess.run(
                    ['git', 'branch', '--show-current'],
                    capture_output=True,
                    text=True,
                    timeout=2
                )
                if result.returncode == 0:
                    context['branch'] = result.stdout.strip()
                
                # Get status (short)
                result = subprocess.run(
                    ['git', 'status', '--short'],
                    capture_output=True,
                    text=True,
                    timeout=2
                )
                if result.returncode == 0:
                    status = result.stdout.strip()
                    context['status'] = status
                    context['uncommitted_changes'] = bool(status)
                
                # Get recent commits (last 3)
                result = subprocess.run(
                    ['git', 'log', '--oneline', '-3'],
                    capture_output=True,
                    text=True,
                    timeout=2
                )
                if result.returncode == 0:
                    commits = [line.strip() for line in result.stdout.strip().split('\n') if line.strip()]
                    context['recent_commits'] = commits
        
        except Exception:
            pass  # Not in git repo or git not available
        
        self._git_cache = context
        return context
    
    def get_environment_context(self) -> Dict[str, any]:
        """Get relevant environment variables."""
        if self._env_cache:
            return self._env_cache
        
        important_vars = [
            'PATH', 'HOME', 'USER', 'SHELL', 
            'EDITOR', 'LANG', 'PWD', 'OLDPWD',
            'VIRTUAL_ENV', 'CONDA_DEFAULT_ENV',
            'NODE_ENV', 'PYTHON_VERSION'
        ]
        
        context = {}
        for var in important_vars:
            value = os.environ.get(var)
            if value:
                # Truncate PATH (can be very long)
                if var == 'PATH':
                    paths = value.split(':')
                    context[var] = f"{len(paths)} paths"
                else:
                    context[var] = value
        
        self._env_cache = context
        return context
    
    def get_recent_files(self, directory: str = '.', limit: int = 5) -> List[Dict[str, any]]:
        """Get recently modified files in directory."""
        import glob
        import time
        
        try:
            files = []
            
            # Get all files (not hidden)
            for pattern in ['**/*.py', '**/*.js', '**/*.ts', '**/*.go', '**/*.rs', '**/*.md']:
                for file in glob.glob(os.path.join(directory, pattern), recursive=True):
                    if '/.git/' in file or '/node_modules/' in file or '/venv/' in file:
                        continue
                    
                    try:
                        stat = os.stat(file)
                        files.append({
                            'path': file,
                            'size': stat.st_size,
                            'modified': stat.st_mtime
                        })
                    except:
                        continue
            
            # Sort by modification time
            files.sort(key=lambda x: x['modified'], reverse=True)
            
            # Return top N with relative times
            now = time.time()
            recent = []
            for f in files[:limit]:
                age = now - f['modified']
                if age < 60:
                    age_str = f"{int(age)}s ago"
                elif age < 3600:
                    age_str = f"{int(age/60)}m ago"
                elif age < 86400:
                    age_str = f"{int(age/3600)}h ago"
                else:
                    age_str = f"{int(age/86400)}d ago"
                
                recent.append({
                    'path': f['path'].replace(directory + '/', ''),
                    'size': f"{f['size']/1024:.1f}KB",
                    'modified': age_str
                })
            
            return recent
        
        except Exception:
            return []
    
    def build_rich_context(self, include_files: bool = True, include_git: bool = True,
                          include_env: bool = True, include_recent: bool = True) -> Dict[str, any]:
        """Build comprehensive context for LLM.
        
        This is what gets injected into every prompt (Cursor-style).
        """
        context = {
            'cwd': os.getcwd(),
            'os': os.name,
        }
        
        if include_git:
            context['git'] = self.get_git_context()
        
        if include_env:
            context['environment'] = self.get_environment_context()
        
        if include_recent:
            context['recent_files'] = self.get_recent_files(limit=5)
        
        if include_files and self.files:
            context['files'] = list(self.files.keys())
            context['file_count'] = len(self.files)
        
        return context
    
    def format_context_for_llm(self, context: Dict = None) -> str:
        """Format rich context as string for LLM prompt."""
        if context is None:
            context = self.build_rich_context()
        
        lines = []
        lines.append("=== CONTEXT ===")
        lines.append(f"Directory: {context.get('cwd', 'unknown')}")
        lines.append(f"OS: {context.get('os', 'unknown')}")
        
        # Git info
        git = context.get('git', {})
        if git.get('is_git_repo'):
            lines.append(f"\nGit:")
            lines.append(f"  Branch: {git.get('branch', 'unknown')}")
            if git.get('uncommitted_changes'):
                lines.append(f"  Status: Uncommitted changes")
            if git.get('recent_commits'):
                lines.append(f"  Recent commits:")
                for commit in git['recent_commits'][:2]:
                    lines.append(f"    - {commit}")
        
        # Recent files
        recent = context.get('recent_files', [])
        if recent:
            lines.append(f"\nRecent files:")
            for f in recent[:3]:
                lines.append(f"  - {f['path']} ({f['size']}, {f['modified']})")
        
        # Environment
        env = context.get('environment', {})
        if env:
            lines.append(f"\nEnvironment:")
            for key in ['SHELL', 'EDITOR', 'VIRTUAL_ENV']:
                if key in env:
                    lines.append(f"  {key}: {env[key]}")
        
        lines.append("=== END CONTEXT ===")
        return '\n'.join(lines)
