"""Enhanced context builder with rich environment awareness."""

import os
import subprocess
import glob
import time
from pathlib import Path
from typing import List, Optional, Dict


class RichContextBuilder:
    """Build rich context from environment for LLM prompts."""
    
    def __init__(self):
        """Initialize context builder."""
        self._git_cache = None
        self._env_cache = None
    
    def get_git_context(self) -> Dict[str, any]:
        """Get git repository context."""
        if self._git_cache:
            return self._git_cache
        
        context = {
            'is_git_repo': False,
            'branch': None,
            'status': None,
            'recent_commits': [],
            'uncommitted_changes': False
        }
        
        try:
            result = subprocess.run(
                ['git', 'rev-parse', '--git-dir'],
                capture_output=True,
                text=True,
                timeout=2
            )
            
            if result.returncode == 0:
                context['is_git_repo'] = True
                
                result = subprocess.run(
                    ['git', 'branch', '--show-current'],
                    capture_output=True,
                    text=True,
                    timeout=2
                )
                if result.returncode == 0:
                    context['branch'] = result.stdout.strip()
                
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
            pass
        
        self._git_cache = context
        return context
    
    def get_environment_context(self) -> Dict[str, any]:
        """Get relevant environment variables."""
        if self._env_cache:
            return self._env_cache
        
        important_vars = [
            'PATH', 'HOME', 'USER', 'SHELL', 
            'EDITOR', 'LANG', 'PWD',
            'VIRTUAL_ENV', 'CONDA_DEFAULT_ENV',
        ]
        
        context = {}
        for var in important_vars:
            value = os.environ.get(var)
            if value:
                if var == 'PATH':
                    paths = value.split(':')
                    context[var] = f"{len(paths)} paths"
                else:
                    context[var] = value
        
        self._env_cache = context
        return context
    
    def get_recent_files(self, directory: str = '.', limit: int = 5) -> List[Dict[str, any]]:
        """Get recently modified files in directory."""
        try:
            files = []
            
            for pattern in ['**/*.py', '**/*.js', '**/*.md']:
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
            
            files.sort(key=lambda x: x['modified'], reverse=True)
            
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
    
    def build_rich_context(self, include_git: bool = True,
                          include_env: bool = True, include_recent: bool = True) -> Dict[str, any]:
        """Build comprehensive context for LLM."""
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
        
        return context
    
    def format_context_for_llm(self, context: Dict = None) -> str:
        """Format rich context as string for LLM prompt."""
        if context is None:
            context = self.build_rich_context()
        
        lines = []
        lines.append("=== CONTEXT ===")
        lines.append(f"Directory: {context.get('cwd', 'unknown')}")
        lines.append(f"OS: {context.get('os', 'unknown')}")
        
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
        
        recent = context.get('recent_files', [])
        if recent:
            lines.append(f"\nRecent files:")
            for f in recent[:3]:
                lines.append(f"  - {f['path']} ({f['size']}, {f['modified']})")
        
        env = context.get('environment', {})
        if env:
            lines.append(f"\nEnvironment:")
            for key in ['SHELL', 'EDITOR', 'VIRTUAL_ENV']:
                if key in env:
                    lines.append(f"  {key}: {env[key]}")
        
        lines.append("=== END CONTEXT ===")
        return '\n'.join(lines)


# Global instance
rich_context_builder = RichContextBuilder()
