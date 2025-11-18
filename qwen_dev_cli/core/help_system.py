#!/usr/bin/env python3
"""
Interactive Help System - Context-aware help with examples.

Inspired by:
- GitHub CLI: Interactive tutorials
- Cursor: Example library
- tldr: Simplified man pages
"""

from typing import Dict, List, Optional
from dataclasses import dataclass
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.markdown import Markdown


@dataclass
class Example:
    """Command example with explanation."""
    title: str
    command: str
    explanation: str
    category: str


class HelpSystem:
    """Interactive help system with examples and tutorials."""
    
    def __init__(self):
        self.console = Console()
        self.examples = self._build_examples()
    
    def _build_examples(self) -> Dict[str, List[Example]]:
        """Build example library."""
        return {
            'files': [
                Example(
                    title="List large files",
                    command="find . -type f -size +100M",
                    explanation="Find files larger than 100MB in current directory",
                    category="files"
                ),
                Example(
                    title="Search in files",
                    command="grep -r 'pattern' .",
                    explanation="Search for text pattern recursively",
                    category="files"
                ),
                Example(
                    title="Delete old files",
                    command="find . -type f -mtime +30 -delete",
                    explanation="Delete files older than 30 days",
                    category="files"
                ),
            ],
            'git': [
                Example(
                    title="Undo last commit",
                    command="git reset --soft HEAD~1",
                    explanation="Undo commit but keep changes staged",
                    category="git"
                ),
                Example(
                    title="View file history",
                    command="git log -p filename",
                    explanation="Show all changes to a specific file",
                    category="git"
                ),
                Example(
                    title="Create branch from commit",
                    command="git branch new-branch commit-hash",
                    explanation="Create a new branch from specific commit",
                    category="git"
                ),
            ],
            'system': [
                Example(
                    title="Find process by port",
                    command="lsof -i :8080",
                    explanation="Find which process is using port 8080",
                    category="system"
                ),
                Example(
                    title="Monitor system resources",
                    command="htop",
                    explanation="Interactive process viewer (better than top)",
                    category="system"
                ),
                Example(
                    title="Check disk usage",
                    command="du -sh */ | sort -h",
                    explanation="Show directory sizes sorted by size",
                    category="system"
                ),
            ],
            'network': [
                Example(
                    title="Test connection",
                    command="ping -c 4 google.com",
                    explanation="Send 4 ping packets to check connectivity",
                    category="network"
                ),
                Example(
                    title="Download file",
                    command="curl -O https://example.com/file.txt",
                    explanation="Download file with original name",
                    category="network"
                ),
                Example(
                    title="Check open ports",
                    command="netstat -tuln",
                    explanation="List all listening ports",
                    category="network"
                ),
            ],
            'docker': [
                Example(
                    title="Remove stopped containers",
                    command="docker container prune",
                    explanation="Clean up stopped containers",
                    category="docker"
                ),
                Example(
                    title="View container logs",
                    command="docker logs -f container-name",
                    explanation="Follow logs in real-time",
                    category="docker"
                ),
                Example(
                    title="Execute in container",
                    command="docker exec -it container-name bash",
                    explanation="Open interactive shell in running container",
                    category="docker"
                ),
            ],
        }
    
    def show_main_help(self):
        """Show main help screen."""
        help_text = """
# Qwen CLI - AI-Powered Shell Assistant

## 🚀 Quick Start

Just type what you want in natural language:
- "list large files"
- "find files modified today"  
- "show processes using most memory"

## 📚 System Commands

- `help` - Show this help
- `help examples` - Show example library
- `help <topic>` - Get help on specific topic
- `/explain <command>` - Explain what a command does
- `/tutorial` - Start interactive tutorial
- `quit` or `exit` - Exit shell

## 🎯 Topics

Type `help <topic>` for examples:
- `files` - File operations
- `git` - Git commands
- `system` - System management
- `network` - Network tools
- `docker` - Docker operations

## 🛡️ Safety

Commands are classified by danger level:
- ✓ Safe (auto-execute): ls, pwd, cat
- ⚠️  Caution (confirm): cp, mv, git
- 🚨 Dangerous (double-confirm): rm, chmod 777
- 💀 Critical (type exact command): rm -rf /, dd

## 💡 Tips

- Use arrow keys for history
- Tab for autocomplete (if available)
- Ctrl+C to cancel current input
- LLM suggests commands, you approve

---
*Powered by Qwen + Constitutional AI*
"""
        md = Markdown(help_text)
        self.console.print(md)
    
    def show_examples(self, category: Optional[str] = None):
        """Show example library."""
        if category and category in self.examples:
            # Show specific category
            examples = self.examples[category]
            
            self.console.print(f"\n[bold cyan]Examples: {category.title()}[/bold cyan]\n")
            
            for i, ex in enumerate(examples, 1):
                self.console.print(f"[bold]{i}. {ex.title}[/bold]")
                self.console.print(f"   [cyan]$ {ex.command}[/cyan]")
                self.console.print(f"   [dim]{ex.explanation}[/dim]")
                self.console.print()
        
        else:
            # Show all categories
            table = Table(title="📚 Example Library", show_header=True, header_style="bold cyan")
            table.add_column("Category", style="cyan", width=12)
            table.add_column("Examples", style="white", width=50)
            
            for cat, examples in self.examples.items():
                example_titles = "\n".join([f"• {ex.title}" for ex in examples[:3]])
                table.add_row(cat.title(), example_titles)
            
            self.console.print(table)
            self.console.print("\n[dim]Usage: help <category> for details (e.g., 'help git')[/dim]\n")
    
    def explain_command(self, command: str) -> str:
        """Generate explanation for a command."""
        # Parse command
        parts = command.strip().split()
        if not parts:
            return "No command provided"
        
        cmd = parts[0]
        
        # Common command explanations
        explanations = {
            'ls': "List directory contents",
            'cd': "Change directory",
            'pwd': "Print working directory",
            'mkdir': "Create directory",
            'rm': "Remove files or directories",
            'cp': "Copy files or directories",
            'mv': "Move or rename files",
            'cat': "Display file contents",
            'grep': "Search for patterns in files",
            'find': "Search for files",
            'git': "Version control system",
            'docker': "Container management",
            'curl': "Transfer data from/to servers",
            'wget': "Download files from web",
            'ssh': "Secure shell remote login",
            'chmod': "Change file permissions",
            'chown': "Change file ownership",
            'ps': "Show running processes",
            'kill': "Terminate processes",
            'df': "Show disk space usage",
            'du': "Show directory space usage",
            'tar': "Archive files",
            'zip': "Compress files",
            'sudo': "Execute command as superuser",
        }
        
        base_explanation = explanations.get(cmd, f"Command: {cmd}")
        
        # Build detailed explanation
        lines = []
        lines.append(f"[bold cyan]Command:[/bold cyan] {command}")
        lines.append(f"[bold]Base:[/bold] {base_explanation}")
        
        # Parse flags
        flags = [p for p in parts[1:] if p.startswith('-')]
        if flags:
            lines.append(f"[bold]Flags:[/bold] {' '.join(flags)}")
        
        # Parse arguments
        args = [p for p in parts[1:] if not p.startswith('-')]
        if args:
            lines.append(f"[bold]Arguments:[/bold] {' '.join(args)}")
        
        return '\n'.join(lines)
    
    def show_tutorial(self):
        """Show interactive tutorial."""
        tutorial = """
╔════════════════════════════════════════════════════════════╗
║                   🎓 INTERACTIVE TUTORIAL                   ║
╚════════════════════════════════════════════════════════════╝

Welcome to Qwen CLI! Let's learn how to use it.

STEP 1: Natural Language Commands
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Instead of remembering exact syntax, just describe what you want:

✓ "list files modified today"
✓ "show me the 10 largest files"  
✓ "delete old log files"

The AI will translate this to the actual command.

STEP 2: Review & Approve
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Before executing, you'll see:

  You: list large files
  
  💡 Suggested action:
     find . -type f -size +100M
  
  ✓ Safe command
  Execute? [Y/n]

You ALWAYS have control. Review before confirming.

STEP 3: Learn from Errors
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
If something fails, you get intelligent suggestions:

  ❌ Failed
  bash: git: command not found
  
  💡 The command 'git' is not installed
  
  Suggestions:
  1. Install it: sudo apt install git
  2. Check if it's in PATH: echo $PATH

STEP 4: Safety Levels
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Commands are classified by danger:

✓ Safe (ls, pwd) → Auto-execute with [Y/n]
⚠️  Caution (cp, mv) → Confirm with [y/N]
🚨 Dangerous (rm -rf) → Type 'YES'
💀 Critical (rm -rf /) → Type exact command

STEP 5: Get Help Anytime
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- Type 'help' for main help
- Type 'help examples' for common tasks
- Type 'help git' for git examples
- Type '/explain ls -la' to understand commands

╔════════════════════════════════════════════════════════════╗
║  You're ready! Try: "list files in current directory"     ║
╚════════════════════════════════════════════════════════════╝
"""
        self.console.print(tutorial)
    
    def show_tips(self, context: Dict = None):
        """Show context-aware tips."""
        tips = []
        
        # Git tips
        if context and context.get('git', {}).get('is_git_repo'):
            if context['git'].get('uncommitted_changes'):
                tips.append("💡 You have uncommitted changes. Try: 'show git status'")
        
        # Generic tips
        if not tips:
            import random
            all_tips = [
                "💡 Tip: Use 'help examples' to see common tasks",
                "💡 Tip: Type '/explain <cmd>' to understand any command",
                "💡 Tip: Commands are safe by default - you always approve",
                "💡 Tip: Use natural language, no need for exact syntax",
                "💡 Tip: Arrow keys navigate command history",
            ]
            tips.append(random.choice(all_tips))
        
        for tip in tips:
            self.console.print(f"[dim]{tip}[/dim]")


# Global help system
help_system = HelpSystem()
