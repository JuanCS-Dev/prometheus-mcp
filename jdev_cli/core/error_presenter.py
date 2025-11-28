"""
ErrorPresenter - User-Friendly Error Messages (Dual Audience)
Pipeline de Diamante - Camada 4: OUTPUT SHIELD

Addresses: ISSUE-021, ISSUE-022, ISSUE-023, ISSUE-024 (Error message clarity)

Implements dual-audience error presentation:
- Beginner mode: Simple language, step-by-step fixes
- Developer mode: Full stacktrace, technical details
- Auto-detection based on command complexity
- Actionable suggestions for each error type

Design Philosophy:
- Errors should help, not frustrate
- Different users need different detail levels
- Every error has a suggested fix
- Context-aware error messages
"""

from __future__ import annotations

import re
import traceback
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass, field
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class AudienceLevel(Enum):
    """Target audience for error messages."""
    BEGINNER = "beginner"      # Simple, friendly, step-by-step
    INTERMEDIATE = "intermediate"  # Some technical detail
    DEVELOPER = "developer"    # Full technical detail


class ErrorCategory(Enum):
    """Categories of errors."""
    FILE_NOT_FOUND = "file_not_found"
    PERMISSION_DENIED = "permission_denied"
    SYNTAX_ERROR = "syntax_error"
    IMPORT_ERROR = "import_error"
    NETWORK_ERROR = "network_error"
    TIMEOUT = "timeout"
    MEMORY_ERROR = "memory_error"
    COMMAND_ERROR = "command_error"
    GIT_ERROR = "git_error"
    VALIDATION_ERROR = "validation_error"
    UNKNOWN = "unknown"


@dataclass
class ErrorExplanation:
    """Structured error explanation."""
    category: ErrorCategory
    title: str
    simple_explanation: str
    technical_explanation: str
    suggestions: List[str]
    example_fix: Optional[str] = None
    documentation_url: Optional[str] = None
    related_errors: List[str] = field(default_factory=list)


@dataclass
class PresentedError:
    """A formatted error ready for display."""
    title: str
    message: str
    suggestions: List[str]
    technical_details: Optional[str] = None
    example_fix: Optional[str] = None
    category: ErrorCategory = ErrorCategory.UNKNOWN
    location: Optional[str] = None  # File:line location of error
    traceback: Optional[str] = None  # Full traceback string
    # Vibe coder support fields
    simple_explanation: Optional[str] = None
    code_example: Optional[str] = None
    steps: List[str] = field(default_factory=list)
    how_to_fix: Optional[str] = None
    help_available: bool = True
    further_help: Optional[str] = "Need more help? Ask for a detailed explanation."
    learn_more: Optional[str] = None
    resources: List[str] = field(default_factory=list)


# Error pattern matchers and explanations
ERROR_PATTERNS: Dict[str, ErrorExplanation] = {
    # File errors
    r"No such file or directory|FileNotFoundError|ENOENT": ErrorExplanation(
        category=ErrorCategory.FILE_NOT_FOUND,
        title="File Not Found",
        simple_explanation="The file or folder you're looking for doesn't exist.",
        technical_explanation="FileNotFoundError: The specified path does not exist in the filesystem.",
        suggestions=[
            "Check if you typed the file name correctly",
            "Make sure you're in the right folder (use 'pwd' to check)",
            "Use 'ls' to see what files exist in the current folder",
            "If creating a new file, the parent folder must exist first",
        ],
        example_fix="# To check what files exist:\nls -la\n\n# To create parent folders:\nmkdir -p path/to/folder",
    ),

    r"Permission denied|PermissionError|EACCES": ErrorExplanation(
        category=ErrorCategory.PERMISSION_DENIED,
        title="Permission Denied",
        simple_explanation="You don't have permission to access this file or folder.",
        technical_explanation="PermissionError: The current user lacks the required filesystem permissions.",
        suggestions=[
            "Check the file permissions with 'ls -la filename'",
            "You might need to change permissions with 'chmod'",
            "If it's a system file, you may need admin/sudo access",
            "Check if the file is owned by another user",
        ],
        example_fix="# To see permissions:\nls -la filename\n\n# To make a file readable:\nchmod +r filename\n\n# To make executable:\nchmod +x script.sh",
    ),

    # Python errors
    r"SyntaxError|invalid syntax": ErrorExplanation(
        category=ErrorCategory.SYNTAX_ERROR,
        title="Syntax Error",
        simple_explanation="There's a typo or mistake in the code structure.",
        technical_explanation="SyntaxError: The Python interpreter cannot parse the code due to invalid syntax.",
        suggestions=[
            "Check for missing colons (:) after if, for, def, class",
            "Make sure all parentheses () and brackets [] are balanced",
            "Check for missing quotes in strings",
            "Look at the line number mentioned in the error",
        ],
        example_fix='# Common fixes:\n# Missing colon:\nif x == 1:  # <- colon needed\n    print("yes")\n\n# Unbalanced brackets:\nmy_list = [1, 2, 3]  # <- all brackets matched',
    ),

    r"ModuleNotFoundError|ImportError|No module named": ErrorExplanation(
        category=ErrorCategory.IMPORT_ERROR,
        title="Missing Package",
        simple_explanation="A required package is not installed.",
        technical_explanation="ImportError: The Python module cannot be found in the current environment.",
        suggestions=[
            "Install the missing package with pip",
            "Make sure you're using the right Python environment",
            "Check if the package name is spelled correctly",
            "The package might have a different import name than its pip name",
        ],
        example_fix="# To install a package:\npip install package_name\n\n# To install from requirements:\npip install -r requirements.txt\n\n# To check installed packages:\npip list",
    ),

    # Network errors
    r"ConnectionError|ConnectionRefused|Connection refused|ECONNREFUSED": ErrorExplanation(
        category=ErrorCategory.NETWORK_ERROR,
        title="Connection Failed",
        simple_explanation="Could not connect to the server or service.",
        technical_explanation="ConnectionError: The network connection was refused or failed.",
        suggestions=[
            "Check if you have internet connectivity",
            "Verify the server/service is running",
            "Check if the URL or port is correct",
            "A firewall might be blocking the connection",
        ],
        example_fix="# To test connectivity:\nping google.com\n\n# To check if a port is open:\nnc -zv localhost 8080",
    ),

    r"TimeoutError|timed out|ETIMEDOUT": ErrorExplanation(
        category=ErrorCategory.TIMEOUT,
        title="Operation Timed Out",
        simple_explanation="The operation took too long and was cancelled.",
        technical_explanation="TimeoutError: The operation exceeded the maximum allowed time.",
        suggestions=[
            "Try again - it might be a temporary issue",
            "Check your internet connection speed",
            "The server might be overloaded",
            "Consider increasing the timeout if possible",
        ],
    ),

    # Memory errors
    r"MemoryError|killed|OOM|Out of memory": ErrorExplanation(
        category=ErrorCategory.MEMORY_ERROR,
        title="Out of Memory",
        simple_explanation="The operation needs more memory than available.",
        technical_explanation="MemoryError: The system ran out of available RAM.",
        suggestions=[
            "Try processing smaller amounts of data",
            "Close other applications to free memory",
            "Consider using streaming/chunked processing",
            "The dataset might be too large for your system",
        ],
    ),

    # Git errors
    r"not a git repository|fatal: not a git repo": ErrorExplanation(
        category=ErrorCategory.GIT_ERROR,
        title="Not a Git Repository",
        simple_explanation="This folder is not set up for Git version control.",
        technical_explanation="Git cannot find a .git directory in this path or any parent.",
        suggestions=[
            "Initialize a new repository with 'git init'",
            "Make sure you're in the right folder",
            "Navigate to the project root folder",
        ],
        example_fix="# To initialize a new repo:\ngit init\n\n# To clone an existing repo:\ngit clone https://github.com/user/repo.git",
    ),

    r"CONFLICT|Merge conflict": ErrorExplanation(
        category=ErrorCategory.GIT_ERROR,
        title="Merge Conflict",
        simple_explanation="Git can't automatically combine changes from different branches.",
        technical_explanation="Merge conflict: The same lines were modified in both branches.",
        suggestions=[
            "Open the conflicted files and look for <<<<<<< markers",
            "Manually choose which changes to keep",
            "After resolving, stage the files with 'git add'",
            "Then complete the merge with 'git commit'",
        ],
        example_fix="# To see conflicted files:\ngit status\n\n# After manually editing conflicts:\ngit add resolved_file.py\ngit commit -m 'Resolved merge conflict'",
    ),
}


class ErrorPresenter:
    """
    Dual-audience error message presenter.

    Features:
    - Automatic error categorization
    - Audience-appropriate explanations
    - Actionable suggestions
    - Code examples for fixes

    Usage:
        presenter = ErrorPresenter(audience=AudienceLevel.BEGINNER)
        # or
        presenter = ErrorPresenter(mode="developer")

        try:
            # some code
        except Exception as e:
            error = presenter.present(e)
            print(error.message)
    """

    def __init__(
        self,
        audience: AudienceLevel = AudienceLevel.INTERMEDIATE,
        show_technical: bool = True,
        show_suggestions: bool = True,
        show_examples: bool = True,
        mode: Optional[str] = None,  # "beginner", "developer", "intermediate"
        default_mode: Optional[str] = None,  # Alias for mode (test compat)
    ):
        """
        Initialize ErrorPresenter.

        Args:
            audience: Target audience level
            show_technical: Show technical details (for dev mode)
            show_suggestions: Show fix suggestions
            show_examples: Show code examples
            mode: Shorthand for audience level (overrides audience if set)
            default_mode: Alias for mode (test compatibility)
        """
        # Handle mode/default_mode parameter (for test compatibility)
        effective_mode = mode or default_mode
        if effective_mode:
            mode_map = {
                "beginner": AudienceLevel.BEGINNER,
                "developer": AudienceLevel.DEVELOPER,
                "intermediate": AudienceLevel.INTERMEDIATE,
            }
            self.audience = mode_map.get(effective_mode.lower(), AudienceLevel.INTERMEDIATE)
        else:
            self.audience = audience
        self.show_technical = show_technical
        self.show_suggestions = show_suggestions
        self.show_examples = show_examples

    def categorize(self, error: Union[Exception, str]) -> ErrorCategory:
        """
        Categorize an error.

        Args:
            error: Exception or error message

        Returns:
            ErrorCategory
        """
        error_str = str(error)

        for pattern, explanation in ERROR_PATTERNS.items():
            if re.search(pattern, error_str, re.IGNORECASE):
                return explanation.category

        return ErrorCategory.UNKNOWN

    def get_explanation(self, error: Union[Exception, str]) -> Optional[ErrorExplanation]:
        """
        Get explanation for an error.

        Args:
            error: Exception or error message

        Returns:
            ErrorExplanation if found
        """
        error_str = str(error)

        for pattern, explanation in ERROR_PATTERNS.items():
            if re.search(pattern, error_str, re.IGNORECASE):
                return explanation

        return None

    def present(
        self,
        error: Union[Exception, str],
        context: Optional[Dict[str, Any]] = None,
        mode: Optional[str] = None,
        include_traceback: bool = False,
    ) -> PresentedError:
        """
        Present an error in user-friendly format.

        Args:
            error: Exception or error message
            context: Additional context (file path, command, etc.)
            mode: Override audience mode for this call
            include_traceback: Force include traceback

        Returns:
            PresentedError ready for display
        """
        context = context or {}
        error_str = str(error)
        explanation = self.get_explanation(error)

        # Temporarily override audience if mode specified
        original_audience = self.audience
        if mode:
            mode_map = {
                "beginner": AudienceLevel.BEGINNER,
                "developer": AudienceLevel.DEVELOPER,
                "intermediate": AudienceLevel.INTERMEDIATE,
            }
            self.audience = mode_map.get(mode.lower(), self.audience)

        try:
            if explanation:
                result = self._present_known_error(error, explanation, context)
            else:
                result = self._present_unknown_error(error, context)

            # Add location info from error if available
            if isinstance(error, Exception):
                if hasattr(error, 'filename') and hasattr(error, 'lineno'):
                    result.location = f"{error.filename}:{error.lineno}"
                elif hasattr(error, '__traceback__') and error.__traceback__:
                    import traceback as tb_module
                    frames = tb_module.extract_tb(error.__traceback__)
                    if frames:
                        last_frame = frames[-1]
                        result.location = f"{last_frame.filename}:{last_frame.lineno}"

                # Add full traceback if requested or in developer mode
                if include_traceback or self.audience == AudienceLevel.DEVELOPER:
                    import traceback as tb_module
                    result.traceback = "".join(tb_module.format_exception(
                        type(error), error, error.__traceback__
                    ))

            return result
        finally:
            self.audience = original_audience

    def _present_known_error(
        self,
        error: Union[Exception, str],
        explanation: ErrorExplanation,
        context: Dict[str, Any],
    ) -> PresentedError:
        """Present a known error type."""
        # Choose explanation based on audience
        if self.audience == AudienceLevel.BEGINNER:
            message = explanation.simple_explanation
        elif self.audience == AudienceLevel.DEVELOPER:
            message = explanation.technical_explanation
        else:
            message = f"{explanation.simple_explanation}\n\nTechnical: {explanation.technical_explanation}"

        # Add context to message
        if context:
            if "file_path" in context:
                message += f"\n\nFile: {context['file_path']}"
            if "command" in context:
                message += f"\nCommand: {context['command']}"

        # Technical details for developers
        technical_details = None
        if self.show_technical and isinstance(error, Exception):
            technical_details = "".join(traceback.format_exception(
                type(error), error, error.__traceback__
            ))

        # Suggestions
        suggestions = explanation.suggestions if self.show_suggestions else []

        # Example fix
        example_fix = explanation.example_fix if self.show_examples else None

        # Build steps from suggestions
        steps = [f"Step {i+1}: {s}" for i, s in enumerate(suggestions[:4])]

        # Generate simple explanation for beginners
        simple_explanation = self._generate_simple_explanation(error, explanation)

        # How to fix summary
        how_to_fix = suggestions[0] if suggestions else None

        return PresentedError(
            title=explanation.title,
            message=message,
            suggestions=suggestions,
            technical_details=technical_details,
            example_fix=example_fix,
            category=explanation.category,
            simple_explanation=simple_explanation,
            code_example=example_fix,
            steps=steps,
            how_to_fix=how_to_fix,
            learn_more=explanation.documentation_url,
            resources=[explanation.documentation_url] if explanation.documentation_url else [],
        )

    def _present_unknown_error(
        self,
        error: Union[Exception, str],
        context: Dict[str, Any],
    ) -> PresentedError:
        """Present an unknown error type."""
        error_str = str(error)

        if self.audience == AudienceLevel.BEGINNER:
            message = f"Something went wrong: {error_str}"
            simple_explanation = self._generate_simple_explanation(error, None)
            suggestions = [
                "Try running the command again",
                "Check that all required files exist",
                "Make sure you have the necessary permissions",
                "If the problem persists, try restarting",
            ]
        else:
            message = error_str
            simple_explanation = error_str
            suggestions = [
                "Check the error message for clues",
                "Search for this error online",
                "Review recent changes that might have caused this",
            ]

        # Technical details
        technical_details = None
        if self.show_technical and isinstance(error, Exception):
            technical_details = "".join(traceback.format_exception(
                type(error), error, error.__traceback__
            ))

        steps = [f"Step {i+1}: {s}" for i, s in enumerate(suggestions[:4])]

        return PresentedError(
            title="Error Occurred",
            message=message,
            suggestions=suggestions,
            technical_details=technical_details,
            category=ErrorCategory.UNKNOWN,
            simple_explanation=simple_explanation,
            steps=steps,
            how_to_fix=suggestions[0] if suggestions else None,
        )

    def _generate_simple_explanation(
        self,
        error: Union[Exception, str],
        explanation: Optional[ErrorExplanation],
    ) -> str:
        """Generate a beginner-friendly explanation of the error."""
        error_str = str(error)
        error_type = type(error).__name__ if isinstance(error, Exception) else "Error"

        # Specific explanations for common errors
        simple_explanations = {
            "SyntaxError": "There's a typo or missing character in your code. Python couldn't understand what you wrote. Check for missing parentheses, brackets, or colons.",
            "NameError": "You're trying to use a variable or function that doesn't exist. This usually means a typo, or you forgot to define something before using it.",
            "TypeError": "You're trying to do something with the wrong type of data. For example, adding a number to text won't work directly.",
            "ImportError": "Python can't find the module you're trying to import. You might need to install it with pip, or check the spelling.",
            "ModuleNotFoundError": "The package you need isn't installed. Try running: pip install <package_name>",
            "AttributeError": "You're trying to access something that doesn't exist on this object. Maybe the variable is empty (None) or the method name is wrong.",
            "ValueError": "The value you provided isn't valid for this operation. Check that your data is in the right format.",
            "KeyError": "You're looking for something in a dictionary that doesn't exist. Double-check the key name.",
            "IndexError": "You're trying to access an item at a position that doesn't exist. Remember: lists start at 0, not 1!",
            "IndentationError": "Python uses spaces to understand code blocks. Make sure your indentation is consistent - don't mix tabs and spaces.",
            "FileNotFoundError": "The file you're looking for doesn't exist at that location. Check the path and filename spelling.",
            "PermissionError": "You don't have permission to access this file or folder. Try running with different permissions.",
            "ZeroDivisionError": "You can't divide by zero! Check your math.",
            "RuntimeError": "Something unexpected happened while running your code.",
        }

        if error_type in simple_explanations:
            base_explanation = simple_explanations[error_type]
        elif explanation:
            base_explanation = explanation.simple_explanation
        else:
            base_explanation = f"An error occurred: {error_str}"

        # Add specific context from the error message
        if "prnt" in error_str.lower() and "print" not in error_str.lower():
            base_explanation += " Did you mean 'print'?"
        elif "pands" in error_str.lower():
            base_explanation += " Did you mean 'pandas'?"
        elif "missing" in error_str.lower() and ")" in error_str:
            base_explanation += " You're probably missing a closing parenthesis."
        elif "unexpected indent" in error_str.lower():
            base_explanation = "Your code has inconsistent indentation. Python needs consistent spacing at the start of lines."

        return base_explanation

    def format_for_terminal(
        self,
        presented: PresentedError,
        use_color: bool = True,
    ) -> str:
        """
        Format presented error for terminal display.

        Args:
            presented: PresentedError to format
            use_color: Use ANSI color codes

        Returns:
            Formatted string
        """
        lines = []

        # Title with color
        if use_color:
            title = f"\033[1;31m{presented.title}\033[0m"  # Bold red
        else:
            title = presented.title
        lines.append(f"\n{title}")
        lines.append("=" * len(presented.title))

        # Message
        lines.append(f"\n{presented.message}")

        # Suggestions
        if presented.suggestions:
            lines.append("\n\033[1;33mSuggestions:\033[0m" if use_color else "\nSuggestions:")
            for i, suggestion in enumerate(presented.suggestions, 1):
                lines.append(f"  {i}. {suggestion}")

        # Example fix
        if presented.example_fix:
            lines.append("\n\033[1;36mExample Fix:\033[0m" if use_color else "\nExample Fix:")
            for line in presented.example_fix.split('\n'):
                lines.append(f"  {line}")

        # Technical details (collapsed for non-developers)
        if presented.technical_details and self.audience == AudienceLevel.DEVELOPER:
            lines.append("\n\033[1;35mTechnical Details:\033[0m" if use_color else "\nTechnical Details:")
            lines.append("```")
            # Limit traceback length
            tb_lines = presented.technical_details.split('\n')
            if len(tb_lines) > 20:
                lines.extend(tb_lines[:10])
                lines.append("  ... (truncated) ...")
                lines.extend(tb_lines[-5:])
            else:
                lines.extend(tb_lines)
            lines.append("```")

        return "\n".join(lines)

    def format_for_rich(self, presented: PresentedError) -> Any:
        """
        Format presented error for Rich console.

        Returns a Rich Panel that can be printed directly.
        """
        try:
            from rich.panel import Panel
            from rich.text import Text
            from rich.syntax import Syntax
            from rich import box

            content = Text()

            # Message
            content.append(presented.message + "\n\n")

            # Suggestions
            if presented.suggestions:
                content.append("Suggestions:\n", style="bold yellow")
                for i, suggestion in enumerate(presented.suggestions, 1):
                    content.append(f"  {i}. {suggestion}\n")

            # Example fix
            if presented.example_fix:
                content.append("\nExample Fix:\n", style="bold cyan")

            panel = Panel(
                content,
                title=f"[bold red]{presented.title}[/bold red]",
                border_style="red",
                box=box.ROUNDED,
            )

            return panel

        except ImportError:
            # Fallback to plain text
            return self.format_for_terminal(presented, use_color=False)


# Convenience functions

def present_error(
    error: Union[Exception, str],
    audience: AudienceLevel = AudienceLevel.INTERMEDIATE,
    context: Optional[Dict[str, Any]] = None,
) -> PresentedError:
    """Present an error with default settings."""
    presenter = ErrorPresenter(audience=audience)
    return presenter.present(error, context)


def explain_error(error: Union[Exception, str]) -> str:
    """Get a simple explanation of an error."""
    presenter = ErrorPresenter(audience=AudienceLevel.BEGINNER)
    presented = presenter.present(error)
    return presented.message


def get_error_suggestions(error: Union[Exception, str]) -> List[str]:
    """Get fix suggestions for an error."""
    presenter = ErrorPresenter()
    presented = presenter.present(error)
    return presented.suggestions


def format_error_terminal(error: Union[Exception, str], **kwargs) -> str:
    """Format error for terminal display."""
    presenter = ErrorPresenter(**kwargs)
    presented = presenter.present(error)
    return presenter.format_for_terminal(presented)


# Export all public symbols
__all__ = [
    'AudienceLevel',
    'ErrorCategory',
    'ErrorExplanation',
    'PresentedError',
    'ErrorPresenter',
    'present_error',
    'explain_error',
    'get_error_suggestions',
    'format_error_terminal',
]
