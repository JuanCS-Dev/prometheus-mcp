"""Workflow state machines for intelligent next-step suggestions (Cursor pattern).

Boris Cherny: State machines make implicit workflows explicit and testable.
"""

from typing import List, Optional
from abc import ABC, abstractmethod

from .types import Suggestion, SuggestionType, SuggestionConfidence
from .context_enhanced import RichContext


class Workflow(ABC):
    """Base class for workflow state machines."""
    
    @abstractmethod
    def is_active(self, context: RichContext) -> bool:
        """Check if this workflow is currently active."""
        raise NotImplementedError("Subclasses must implement is_active()")
    
    @abstractmethod
    def suggest_next(self, context: RichContext) -> List[Suggestion]:
        """Suggest next steps in this workflow."""
        raise NotImplementedError("Subclasses must implement suggest_next()")


class GitWorkflow(Workflow):
    """Git workflow state machine.
    
    States:
    - IDLE → git add → STAGED → git commit → COMMITTED → git push → PUSHED
    """
    
    def is_active(self, context: RichContext) -> bool:
        """Active if in git repository."""
        return context.git_status is not None
    
    def suggest_next(self, context: RichContext) -> List[Suggestion]:
        """Suggest next git actions."""
        if not context.git_status:
            return []
        
        suggestions = []
        git = context.git_status
        last_cmd = context.command_history[-1] if context.command_history else ""
        
        # State: Just did "git add"
        if "git add" in last_cmd and git.staged_files:
            suggestions.append(Suggestion(
                type=SuggestionType.NEXT_STEP,
                content="git commit -m ''",
                confidence=SuggestionConfidence.HIGH,
                reasoning="Files staged, ready to commit",
                metadata={'workflow': 'git', 'state': 'staged'}
            ))
        
        # State: Just did "git commit"
        elif "git commit" in last_cmd and git.has_remote:
            branch = git.branch or "main"
            suggestions.append(Suggestion(
                type=SuggestionType.NEXT_STEP,
                content=f"git push origin {branch}",
                confidence=SuggestionConfidence.HIGH,
                reasoning="Commit created, ready to push to remote",
                metadata={'workflow': 'git', 'state': 'committed'}
            ))
        
        # State: Unstaged changes exist
        elif git.unstaged_files or git.untracked_files:
            suggestions.append(Suggestion(
                type=SuggestionType.NEXT_STEP,
                content="git add .",
                confidence=SuggestionConfidence.MEDIUM,
                reasoning=f"{len(git.unstaged_files + git.untracked_files)} files modified",
                metadata={'workflow': 'git', 'state': 'modified'}
            ))
        
        return suggestions


class NpmWorkflow(Workflow):
    """NPM workflow state machine.
    
    States:
    - npm install → INSTALLED → npm run dev / npm test
    """
    
    def is_active(self, context: RichContext) -> bool:
        """Active if in Node.js project."""
        return (
            context.workspace is not None and
            context.workspace.language == 'javascript'
        )
    
    def suggest_next(self, context: RichContext) -> List[Suggestion]:
        """Suggest next npm actions."""
        suggestions = []
        last_cmd = context.command_history[-1] if context.command_history else ""
        
        # State: Just installed dependencies
        if "npm install" in last_cmd or "yarn add" in last_cmd:
            # Suggest starting dev server
            suggestions.append(Suggestion(
                type=SuggestionType.NEXT_STEP,
                content="npm run dev",
                confidence=SuggestionConfidence.HIGH,
                reasoning="Dependencies installed, start development server",
                metadata={'workflow': 'npm', 'state': 'installed'}
            ))
            
            # Or running tests
            if context.workspace and context.workspace.has_tests:
                suggestions.append(Suggestion(
                    type=SuggestionType.NEXT_STEP,
                    content=context.workspace.test_command,
                    confidence=SuggestionConfidence.MEDIUM,
                    reasoning="Run tests after dependency changes",
                    metadata={'workflow': 'npm', 'state': 'installed'}
                ))
        
        # State: Code files were modified
        elif context.recent_files:
            code_files = [
                f for f in context.recent_files
                if f.endswith(('.js', '.ts', '.jsx', '.tsx'))
            ]
            
            if code_files and context.workspace and context.workspace.has_tests:
                suggestions.append(Suggestion(
                    type=SuggestionType.NEXT_STEP,
                    content=context.workspace.test_command,
                    confidence=SuggestionConfidence.MEDIUM,
                    reasoning=f"{len(code_files)} code files modified",
                    metadata={'workflow': 'npm', 'state': 'modified'}
                ))
        
        return suggestions


class PythonWorkflow(Workflow):
    """Python workflow state machine."""
    
    def is_active(self, context: RichContext) -> bool:
        """Active if in Python project."""
        return (
            context.workspace is not None and
            context.workspace.language == 'python'
        )
    
    def suggest_next(self, context: RichContext) -> List[Suggestion]:
        """Suggest next Python actions."""
        suggestions = []
        last_cmd = context.command_history[-1] if context.command_history else ""
        
        # State: Just installed dependencies
        if "pip install" in last_cmd:
            if context.workspace and context.workspace.has_tests:
                suggestions.append(Suggestion(
                    type=SuggestionType.NEXT_STEP,
                    content=context.workspace.test_command,
                    confidence=SuggestionConfidence.MEDIUM,
                    reasoning="Dependencies installed, run tests",
                    metadata={'workflow': 'python', 'state': 'installed'}
                ))
        
        # State: Python files modified
        elif context.recent_files:
            py_files = [f for f in context.recent_files if f.endswith('.py')]
            
            if py_files and context.workspace and context.workspace.has_tests:
                suggestions.append(Suggestion(
                    type=SuggestionType.NEXT_STEP,
                    content=context.workspace.test_command,
                    confidence=SuggestionConfidence.MEDIUM,
                    reasoning=f"{len(py_files)} Python files modified",
                    metadata={'workflow': 'python', 'state': 'modified'}
                ))
        
        return suggestions


class DockerWorkflow(Workflow):
    """Docker workflow state machine."""
    
    def is_active(self, context: RichContext) -> bool:
        """Active if Dockerfile exists."""
        import os
        return os.path.exists(os.path.join(context.working_directory, "Dockerfile"))
    
    def suggest_next(self, context: RichContext) -> List[Suggestion]:
        """Suggest next Docker actions."""
        suggestions = []
        last_cmd = context.command_history[-1] if context.command_history else ""
        
        # State: Just built image
        if "docker build" in last_cmd:
            suggestions.append(Suggestion(
                type=SuggestionType.NEXT_STEP,
                content="docker run <image>",
                confidence=SuggestionConfidence.HIGH,
                reasoning="Image built, ready to run container",
                metadata={'workflow': 'docker', 'state': 'built'}
            ))
        
        # State: Dockerfile modified
        elif "Dockerfile" in str(context.recent_files):
            suggestions.append(Suggestion(
                type=SuggestionType.NEXT_STEP,
                content="docker build -t <tag> .",
                confidence=SuggestionConfidence.MEDIUM,
                reasoning="Dockerfile modified, rebuild image",
                metadata={'workflow': 'docker', 'state': 'modified'}
            ))
        
        return suggestions


class WorkflowOrchestrator:
    """Orchestrates multiple workflows.
    
    Boris Cherny: Composition over inheritance. Each workflow is independent.
    """
    
    def __init__(self):
        self.workflows: List[Workflow] = [
            GitWorkflow(),
            NpmWorkflow(),
            PythonWorkflow(),
            DockerWorkflow(),
        ]
    
    def get_workflow_suggestions(
        self,
        context: RichContext,
        max_per_workflow: int = 2
    ) -> List[Suggestion]:
        """Get suggestions from all active workflows.
        
        Args:
            context: Rich context
            max_per_workflow: Max suggestions per workflow
            
        Returns:
            List of suggestions from all workflows
        """
        all_suggestions = []
        
        for workflow in self.workflows:
            if workflow.is_active(context):
                suggestions = workflow.suggest_next(context)
                all_suggestions.extend(suggestions[:max_per_workflow])
        
        return all_suggestions
