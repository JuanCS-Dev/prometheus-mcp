"""Built-in suggestion patterns.

Boris Cherny: Each pattern is a pure function (Context → Optional[Suggestion])
"""

from typing import Optional
import re

from .types import (
    Suggestion,
    SuggestionType,
    SuggestionConfidence,
    Context,
    SuggestionPattern
)


def _suggest_git_push_after_commit(context: Context) -> Optional[Suggestion]:
    """Suggest git push after successful commit."""
    if not context.command_history:
        return None

    last_cmd = context.command_history[-1] if context.command_history else ""

    # Check if last command was git commit
    if "git commit" in last_cmd and context.git_branch:
        return Suggestion(
            type=SuggestionType.NEXT_STEP,
            content=f"git push origin {context.git_branch}",
            confidence=SuggestionConfidence.HIGH,
            reasoning="After committing, typically you want to push to remote"
        )

    return None


def _suggest_add_before_commit(context: Context) -> Optional[Suggestion]:
    """Suggest git add before commit attempt."""
    if not context.current_command:
        return None

    if "git commit" in context.current_command and "git add" not in str(context.command_history):
        return Suggestion(
            type=SuggestionType.ERROR_PREVENTION,
            content="git add <files>",
            confidence=SuggestionConfidence.MEDIUM,
            reasoning="You're about to commit, but haven't staged files yet"
        )

    return None


def _suggest_test_after_changes(context: Context) -> Optional[Suggestion]:
    """Suggest running tests after code changes."""
    if not context.recent_files:
        return None

    # Check if any test files or source files were modified
    code_modified = any(
        f.endswith(('.py', '.js', '.ts', '.go', '.rs'))
        for f in context.recent_files
    )

    if code_modified:
        # Try to infer test command from project
        test_cmd = "pytest"  # Default for Python

        return Suggestion(
            type=SuggestionType.NEXT_STEP,
            content=test_cmd,
            confidence=SuggestionConfidence.MEDIUM,
            reasoning="Code was modified, running tests ensures nothing broke"
        )

    return None


def _suggest_safer_rm(context: Context) -> Optional[Suggestion]:
    """Suggest safer alternatives to dangerous rm commands."""
    if not context.current_command:
        return None

    cmd = context.current_command

    # Detect dangerous rm patterns
    if re.match(r'rm\s+-rf?\s+/', cmd):
        return Suggestion(
            type=SuggestionType.ERROR_PREVENTION,
            content="Use trash or mv to .backup/ instead",
            confidence=SuggestionConfidence.HIGH,
            reasoning="Destructive rm detected - safer alternatives exist"
        )

    return None


def _suggest_backup_before_destructive(context: Context) -> Optional[Suggestion]:
    """Suggest backup before destructive operations."""
    if not context.current_command:
        return None

    destructive_keywords = ['rm', 'delete', 'truncate', 'drop']

    if any(kw in context.current_command.lower() for kw in destructive_keywords):
        return Suggestion(
            type=SuggestionType.ERROR_PREVENTION,
            content="Create backup first: cp -r <target> <target>.backup",
            confidence=SuggestionConfidence.MEDIUM,
            reasoning="Destructive operation detected - backup recommended"
        )

    return None


def _suggest_verbose_mode(context: Context) -> Optional[Suggestion]:
    """Suggest verbose flags for debugging."""
    if not context.recent_errors:
        return None

    if context.current_command and '-v' not in context.current_command:
        return Suggestion(
            type=SuggestionType.ERROR_PREVENTION,
            content=f"{context.current_command} -v",
            confidence=SuggestionConfidence.LOW,
            reasoning="Recent errors detected - verbose mode helps debugging"
        )

    return None


def _suggest_piping_to_grep(context: Context) -> Optional[Suggestion]:
    """Suggest piping large outputs to grep."""
    if not context.current_command:
        return None

    large_output_cmds = ['ls -la', 'ps aux', 'docker ps', 'kubectl get']

    if any(cmd in context.current_command for cmd in large_output_cmds):
        if '| grep' not in context.current_command:
            return Suggestion(
                type=SuggestionType.WORKFLOW_OPTIMIZATION,
                content=f"{context.current_command} | grep <pattern>",
                confidence=SuggestionConfidence.LOW,
                reasoning="Large output expected - grep can filter results"
            )

    return None


# Built-in patterns registry
BUILTIN_PATTERNS = [
    SuggestionPattern(
        name="git_push_after_commit",
        pattern="",
        suggestion_fn=_suggest_git_push_after_commit,
        priority=90
    ),
    SuggestionPattern(
        name="git_add_before_commit",
        pattern="git commit",
        suggestion_fn=_suggest_add_before_commit,
        priority=95
    ),
    SuggestionPattern(
        name="test_after_changes",
        pattern="",  # Always evaluate (checks recent_files)
        suggestion_fn=_suggest_test_after_changes,
        priority=70
    ),
    SuggestionPattern(
        name="safer_rm",
        pattern="rm ",
        suggestion_fn=_suggest_safer_rm,
        priority=100  # Highest priority for safety
    ),
    SuggestionPattern(
        name="backup_before_destructive",
        pattern="",  # Always evaluate
        suggestion_fn=_suggest_backup_before_destructive,
        priority=85
    ),
    SuggestionPattern(
        name="verbose_mode",
        pattern="",  # Always evaluate
        suggestion_fn=_suggest_verbose_mode,
        priority=60
    ),
    SuggestionPattern(
        name="pipe_to_grep",
        pattern="",  # Always evaluate
        suggestion_fn=_suggest_piping_to_grep,
        priority=50
    ),
]


def register_builtin_patterns(engine) -> None:
    """Register all built-in patterns with engine.
    
    Args:
        engine: SuggestionEngine instance
    """
    for pattern in BUILTIN_PATTERNS:
        engine.register_pattern(pattern)
