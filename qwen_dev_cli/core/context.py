"""Context builder for injecting file contents into prompts."""

import os
from pathlib import Path
from typing import List, Optional, Dict
from .config import config


class ContextBuilder:
    """Build context from files for LLM prompts."""
    
    def __init__(self, max_files: Optional[int] = None, max_file_size_kb: Optional[int] = None):
        """Initialize context builder.
        
        Args:
            max_files: Maximum number of files to include
            max_file_size_kb: Maximum file size in KB
        """
        self.max_files = max_files or config.max_context_files
        self.max_file_size_kb = max_file_size_kb or config.max_file_size_kb
        self.files: Dict[str, str] = {}
    
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
