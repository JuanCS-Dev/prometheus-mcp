"""Explanation engine - adaptive command explanations.

Combines Claude's adaptive detail with structured breakdown.
Boris Cherny: Clear, testable, no magic.
"""

import re
from typing import Optional, Dict, List, Callable

from .types import (
    Explanation,
    ExplanationLevel,
    CommandBreakdown,
    CommandPart
)
from ..intelligence.context_enhanced import ExpertiseLevel, RichContext
from ..intelligence.risk import assess_risk, RiskLevel


class ExplanationEngine:
    """Engine for generating adaptive command explanations.
    
    Adapts detail level based on:
    - User expertise (from RichContext)
    - Command complexity
    - Risk level
    """
    
    def __init__(self):
        self._explainers: Dict[str, Callable] = {}
        self._register_builtin_explainers()
    
    def explain(
        self,
        command: str,
        context: Optional[RichContext] = None
    ) -> Explanation:
        """Generate explanation for command.
        
        Args:
            command: Command to explain
            context: Rich context (for expertise level)
            
        Returns:
            Explanation adapted to user expertise
        """
        # Determine detail level
        level = self._get_detail_level(command, context)
        
        # Try specific explainer first
        cmd_base = command.split()[0] if command else ""
        if cmd_base in self._explainers:
            return self._explainers[cmd_base](command, level)
        
        # Fallback to generic explanation
        return self._generic_explain(command, level)
    
    def _get_detail_level(
        self,
        command: str,
        context: Optional[RichContext]
    ) -> ExplanationLevel:
        """Determine appropriate detail level.
        
        Factors:
        - User expertise (primary)
        - Command risk (high risk = more detail)
        - Command complexity
        """
        # Default based on expertise
        if context:
            if context.user_expertise == ExpertiseLevel.EXPERT:
                level = ExplanationLevel.CONCISE
            elif context.user_expertise == ExpertiseLevel.BEGINNER:
                level = ExplanationLevel.DETAILED
            else:
                level = ExplanationLevel.BALANCED
        else:
            level = ExplanationLevel.BALANCED
        
        # Upgrade detail for risky commands
        risk = assess_risk(command)
        if risk.level in [RiskLevel.HIGH, RiskLevel.CRITICAL]:
            if level == ExplanationLevel.CONCISE:
                level = ExplanationLevel.BALANCED
            elif level == ExplanationLevel.BALANCED:
                level = ExplanationLevel.DETAILED
        
        return level
    
    def register_explainer(
        self,
        command: str,
        explainer_fn: Callable[[str, ExplanationLevel], Explanation]
    ):
        """Register custom explainer for specific command."""
        self._explainers[command] = explainer_fn
    
    def _generic_explain(
        self,
        command: str,
        level: ExplanationLevel
    ) -> Explanation:
        """Generic explanation for unknown commands."""
        parts = command.split()
        if not parts:
            return Explanation(
                command="",
                summary="Empty command",
                level=level
            )
        
        cmd = parts[0]
        args = parts[1:] if len(parts) > 1 else []
        
        summary = f"Execute '{cmd}'"
        if args:
            summary += f" with {len(args)} argument(s)"
        
        breakdown = None
        if level != ExplanationLevel.CONCISE:
            breakdown_parts = [
                CommandPart(cmd, f"Command: {cmd}", "command")
            ]
            for arg in args:
                breakdown_parts.append(
                    CommandPart(arg, "Argument", "argument")
                )
            breakdown = CommandBreakdown(breakdown_parts)
        
        return Explanation(
            command=command,
            summary=summary,
            breakdown=breakdown,
            level=level
        )
    
    def _register_builtin_explainers(self):
        """Register explanations for common commands."""
        self.register_explainer("git", self._explain_git)
        self.register_explainer("rm", self._explain_rm)
        self.register_explainer("chmod", self._explain_chmod)
        self.register_explainer("docker", self._explain_docker)
        self.register_explainer("npm", self._explain_npm)
        self.register_explainer("pip", self._explain_pip)
    
    def _explain_git(
        self,
        command: str,
        level: ExplanationLevel
    ) -> Explanation:
        """Explain git commands."""
        parts = command.split()
        if len(parts) < 2:
            return Explanation(
                command=command,
                summary="Git version control system",
                level=level
            )
        
        subcommand = parts[1]
        
        summaries = {
            "add": "Stage files for commit",
            "commit": "Record changes to repository",
            "push": "Upload commits to remote repository",
            "pull": "Download and merge changes from remote",
            "clone": "Copy a repository to local machine",
            "status": "Show working tree status",
            "log": "Show commit history",
            "branch": "List, create, or delete branches",
            "checkout": "Switch branches or restore files",
            "merge": "Join two or more development histories",
        }
        
        summary = summaries.get(subcommand, f"Git {subcommand} operation")
        
        # Build breakdown
        breakdown = None
        if level != ExplanationLevel.CONCISE:
            breakdown_parts = [
                CommandPart("git", "Version control system", "command"),
                CommandPart(subcommand, summary, "subcommand")
            ]
            
            for arg in parts[2:]:
                if arg.startswith('-'):
                    breakdown_parts.append(
                        CommandPart(arg, "Option/flag", "flag")
                    )
                else:
                    breakdown_parts.append(
                        CommandPart(arg, "Argument", "argument")
                    )
            
            breakdown = CommandBreakdown(breakdown_parts)
        
        # Add warnings for dangerous operations
        warnings = []
        if "push" in command and "-f" in command:
            warnings.append("Force push can overwrite remote history")
        if "reset" in command and "--hard" in command:
            warnings.append("Hard reset discards all changes permanently")
        
        # Add examples for beginners
        examples = []
        if level == ExplanationLevel.DETAILED:
            if subcommand == "add":
                examples = [
                    "git add file.txt",
                    "git add .",
                    "git add -A"
                ]
            elif subcommand == "commit":
                examples = [
                    "git commit -m 'Your message'",
                    "git commit -am 'Add and commit'",
                ]
        
        return Explanation(
            command=command,
            summary=f"Git: {summary}",
            breakdown=breakdown,
            warnings=warnings,
            examples=examples,
            level=level
        )
    
    def _explain_rm(
        self,
        command: str,
        level: ExplanationLevel
    ) -> Explanation:
        """Explain rm commands with safety warnings."""
        summary = "Remove files or directories"
        
        warnings = []
        if "-rf" in command or "-fr" in command:
            warnings.append("⚠️  DESTRUCTIVE: Recursive force delete (no confirmation)")
            warnings.append("⚠️  Cannot be undone!")
        elif "-r" in command:
            warnings.append("Recursive: deletes directories and contents")
        
        if "/" in command:
            warnings.append("🔴 DANGER: Operating on root paths!")
        
        breakdown = None
        if level != ExplanationLevel.CONCISE:
            parts = command.split()
            breakdown_parts = [
                CommandPart("rm", "Remove files/directories", "command")
            ]
            
            for part in parts[1:]:
                if part.startswith('-'):
                    if 'r' in part:
                        breakdown_parts.append(
                            CommandPart(part, "Recursive (includes subdirectories)", "flag")
                        )
                    elif 'f' in part:
                        breakdown_parts.append(
                            CommandPart(part, "Force (no confirmation)", "flag")
                        )
                    else:
                        breakdown_parts.append(
                            CommandPart(part, "Option", "flag")
                        )
                else:
                    breakdown_parts.append(
                        CommandPart(part, "Target file/directory", "argument")
                    )
            
            breakdown = CommandBreakdown(breakdown_parts)
        
        see_also = ["mv", "trash-put", "trash-cli"] if level == ExplanationLevel.DETAILED else []
        
        return Explanation(
            command=command,
            summary=summary,
            breakdown=breakdown,
            warnings=warnings,
            see_also=see_also,
            level=level
        )
    
    def _explain_chmod(self, command: str, level: ExplanationLevel) -> Explanation:
        """Explain chmod commands."""
        summary = "Change file permissions"
        
        warnings = []
        if "777" in command:
            warnings.append("777 = Full permissions for everyone (security risk)")
        if "-R" in command:
            warnings.append("Recursive: affects all subdirectories")
        
        return Explanation(
            command=command,
            summary=summary,
            warnings=warnings,
            level=level
        )
    
    def _explain_docker(self, command: str, level: ExplanationLevel) -> Explanation:
        """Explain docker commands."""
        parts = command.split()
        subcommand = parts[1] if len(parts) > 1 else ""
        
        summaries = {
            "run": "Create and start a container",
            "build": "Build image from Dockerfile",
            "ps": "List containers",
            "images": "List images",
            "pull": "Download image from registry",
            "push": "Upload image to registry",
        }
        
        return Explanation(
            command=command,
            summary=summaries.get(subcommand, "Docker operation"),
            level=level
        )
    
    def _explain_npm(self, command: str, level: ExplanationLevel) -> Explanation:
        """Explain npm commands."""
        parts = command.split()
        subcommand = parts[1] if len(parts) > 1 else ""
        
        summaries = {
            "install": "Install dependencies from package.json",
            "start": "Run start script",
            "test": "Run test script",
            "run": "Run custom script",
            "build": "Run build script",
        }
        
        return Explanation(
            command=command,
            summary=summaries.get(subcommand, "NPM operation"),
            level=level
        )
    
    def _explain_pip(self, command: str, level: ExplanationLevel) -> Explanation:
        """Explain pip commands."""
        parts = command.split()
        subcommand = parts[1] if len(parts) > 1 else ""
        
        summaries = {
            "install": "Install Python package(s)",
            "uninstall": "Remove Python package(s)",
            "list": "List installed packages",
            "freeze": "Output installed packages in requirements format",
        }
        
        return Explanation(
            command=command,
            summary=summaries.get(subcommand, "Pip operation"),
            level=level
        )


# Convenience function
def explain_command(
    command: str,
    context: Optional[RichContext] = None
) -> Explanation:
    """Explain a command (convenience function).
    
    Args:
        command: Command to explain
        context: Optional rich context
        
    Returns:
        Explanation object
    """
    engine = ExplanationEngine()
    return engine.explain(command, context)
