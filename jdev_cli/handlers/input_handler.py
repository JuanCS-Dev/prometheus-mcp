"""
Input Handler.

SCALE & SUSTAIN Phase 1.2.4 - CC Reduction.

Handles user input processing: parsing, validation, preprocessing.
Reduces CC by extracting input processing logic from shell_main.py.

Author: JuanCS Dev
Date: 2025-11-26
"""

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class InputType(Enum):
    """Type of user input."""
    COMMAND = "command"          # /help, /exit, etc.
    QUERY = "query"              # Natural language query
    CODE = "code"                # Code block
    FILE_PATH = "file_path"      # File path reference
    URL = "url"                  # URL reference
    EMPTY = "empty"              # Empty input
    CONTINUATION = "continuation"  # Multi-line continuation


class ValidationStatus(Enum):
    """Input validation status."""
    VALID = "valid"
    INVALID = "invalid"
    WARNING = "warning"
    NEEDS_CONFIRMATION = "needs_confirmation"


@dataclass
class ParsedInput:
    """Parsed user input."""

    raw: str
    input_type: InputType
    command: Optional[str] = None
    args: Optional[str] = None
    content: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_command(self) -> bool:
        """Check if input is a command."""
        return self.input_type == InputType.COMMAND

    @property
    def is_empty(self) -> bool:
        """Check if input is empty."""
        return self.input_type == InputType.EMPTY

    @property
    def has_file_references(self) -> bool:
        """Check if input contains file references."""
        return bool(self.metadata.get('file_references', []))

    @property
    def has_urls(self) -> bool:
        """Check if input contains URLs."""
        return bool(self.metadata.get('urls', []))


@dataclass
class ValidationResult:
    """Result of input validation."""

    status: ValidationStatus
    message: str = ""
    warnings: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        """Check if validation passed."""
        return self.status in (ValidationStatus.VALID, ValidationStatus.WARNING)

    @property
    def needs_confirmation(self) -> bool:
        """Check if user confirmation is needed."""
        return self.status == ValidationStatus.NEEDS_CONFIRMATION


class InputHandler:
    """
    Handle user input processing.

    Provides parsing, validation, and preprocessing of user input.
    Reduces CC in shell_main.py by -5 to -8 points.

    Usage:
        handler = InputHandler()
        parsed = handler.parse_input("/help")
        validation = handler.validate_input(parsed)
        if validation.is_valid:
            processed = handler.preprocess_input(parsed)
    """

    # Command pattern: starts with /
    COMMAND_PATTERN = re.compile(r'^/(\w+)(?:\s+(.*))?$', re.DOTALL)

    # File path patterns
    FILE_PATH_PATTERN = re.compile(r'(?:^|\s)([./~][\w./\-_]+(?:\.\w+)?)')

    # URL pattern
    URL_PATTERN = re.compile(r'https?://[^\s<>"{}|\\^`\[\]]+')

    # Code block pattern (markdown)
    CODE_BLOCK_PATTERN = re.compile(r'```(\w*)\n(.*?)```', re.DOTALL)

    # Dangerous command patterns (for validation)
    DANGEROUS_PATTERNS = [
        re.compile(r'\brm\s+-rf\s+[/~]', re.IGNORECASE),
        re.compile(r'\bsudo\s+rm\b', re.IGNORECASE),
        re.compile(r'\b:(){ :|:& };:', re.IGNORECASE),  # Fork bomb
        re.compile(r'\bdd\s+if=.*of=/dev/', re.IGNORECASE),
        re.compile(r'\bmkfs\b', re.IGNORECASE),
        re.compile(r'\bchmod\s+-R\s+777\s+/', re.IGNORECASE),
    ]

    # Known commands
    KNOWN_COMMANDS = {
        'help', 'exit', 'quit', 'clear', 'model', 'context',
        'history', 'stats', 'config', 'tools', 'agents',
        'lsp', 'index', 'find', 'suggest', 'refactor',
        'workflow', 'squad', 'compact', 'session', 'sessions',
        'memory', 'forget', 'remember', 'recall',
    }

    def __init__(
        self,
        max_input_length: int = 100000,
        allow_dangerous: bool = False
    ):
        """
        Initialize input handler.

        Args:
            max_input_length: Maximum allowed input length
            allow_dangerous: Allow dangerous commands without confirmation
        """
        self.max_input_length = max_input_length
        self.allow_dangerous = allow_dangerous

    def parse_input(self, raw: str) -> ParsedInput:
        """
        Parse raw user input.

        Args:
            raw: Raw input string

        Returns:
            ParsedInput with parsed components
        """
        # Handle empty input
        if not raw or not raw.strip():
            return ParsedInput(
                raw=raw,
                input_type=InputType.EMPTY,
                content=""
            )

        stripped = raw.strip()

        # Check for command
        command_match = self.COMMAND_PATTERN.match(stripped)
        if command_match:
            command = command_match.group(1).lower()
            args = command_match.group(2) or ""
            return ParsedInput(
                raw=raw,
                input_type=InputType.COMMAND,
                command=command,
                args=args.strip(),
                content=stripped
            )

        # Check for code blocks
        code_blocks = self.CODE_BLOCK_PATTERN.findall(stripped)
        if code_blocks:
            return ParsedInput(
                raw=raw,
                input_type=InputType.CODE,
                content=stripped,
                metadata={
                    'code_blocks': [
                        {'language': lang or 'text', 'code': code}
                        for lang, code in code_blocks
                    ]
                }
            )

        # Extract file references
        file_refs = self.FILE_PATH_PATTERN.findall(stripped)

        # Extract URLs
        urls = self.URL_PATTERN.findall(stripped)

        # Determine input type
        if urls and not file_refs:
            input_type = InputType.URL
        elif file_refs and len(file_refs) == len(stripped.split()):
            input_type = InputType.FILE_PATH
        else:
            input_type = InputType.QUERY

        return ParsedInput(
            raw=raw,
            input_type=input_type,
            content=stripped,
            metadata={
                'file_references': file_refs,
                'urls': urls,
            }
        )

    def validate_input(self, parsed: ParsedInput) -> ValidationResult:
        """
        Validate parsed input.

        Args:
            parsed: Parsed input

        Returns:
            ValidationResult with status and messages
        """
        warnings = []
        suggestions = []

        # Check length
        if len(parsed.raw) > self.max_input_length:
            return ValidationResult(
                status=ValidationStatus.INVALID,
                message=f"Input too long ({len(parsed.raw)} > {self.max_input_length})"
            )

        # Validate commands
        if parsed.is_command:
            if parsed.command not in self.KNOWN_COMMANDS:
                # Check for similar commands
                similar = self._find_similar_commands(parsed.command)
                if similar:
                    suggestions.append(f"Did you mean: /{similar[0]}?")
                warnings.append(f"Unknown command: /{parsed.command}")

        # Check for dangerous patterns
        if not self.allow_dangerous:
            for pattern in self.DANGEROUS_PATTERNS:
                if pattern.search(parsed.content):
                    return ValidationResult(
                        status=ValidationStatus.NEEDS_CONFIRMATION,
                        message="Potentially dangerous command detected",
                        warnings=["This command may cause data loss or system damage"]
                    )

        # Check file references exist (optional)
        if parsed.has_file_references:
            import os
            missing = [
                f for f in parsed.metadata.get('file_references', [])
                if not os.path.exists(f) and not f.startswith('~')
            ]
            if missing:
                warnings.append(f"Referenced files not found: {', '.join(missing[:3])}")

        # Determine final status
        if warnings:
            return ValidationResult(
                status=ValidationStatus.WARNING,
                message="Input valid with warnings",
                warnings=warnings,
                suggestions=suggestions
            )

        return ValidationResult(
            status=ValidationStatus.VALID,
            message="Input valid"
        )

    def preprocess_input(self, parsed: ParsedInput) -> str:
        """
        Preprocess input for processing.

        Args:
            parsed: Parsed and validated input

        Returns:
            Preprocessed input string
        """
        content = parsed.content

        # Expand home directory in file paths
        if parsed.has_file_references:
            import os
            for file_ref in parsed.metadata.get('file_references', []):
                if file_ref.startswith('~'):
                    expanded = os.path.expanduser(file_ref)
                    content = content.replace(file_ref, expanded)

        # Normalize whitespace
        content = ' '.join(content.split())

        return content

    def _find_similar_commands(self, command: str, max_results: int = 3) -> List[str]:
        """Find similar known commands."""
        from difflib import get_close_matches
        return get_close_matches(command, self.KNOWN_COMMANDS, n=max_results, cutoff=0.6)

    def extract_context_hints(self, parsed: ParsedInput) -> Dict[str, Any]:
        """
        Extract context hints from input.

        Identifies mentions of files, functions, classes, etc.

        Args:
            parsed: Parsed input

        Returns:
            Dictionary of context hints
        """
        hints = {
            'files': parsed.metadata.get('file_references', []),
            'urls': parsed.metadata.get('urls', []),
            'code_blocks': parsed.metadata.get('code_blocks', []),
            'mentions': [],
        }

        # Extract function/class mentions
        content = parsed.content

        # Function pattern: function_name() or def function_name
        func_pattern = re.compile(r'(?:def\s+)?(\w+)\s*\(')
        hints['mentions'].extend(func_pattern.findall(content))

        # Class pattern: class ClassName or ClassName.
        class_pattern = re.compile(r'(?:class\s+)?([A-Z]\w+)(?:\.|:|\s|$)')
        hints['mentions'].extend(class_pattern.findall(content))

        # Deduplicate
        hints['mentions'] = list(set(hints['mentions']))

        return hints


# Global handler instance
_global_handler: Optional[InputHandler] = None


def get_input_handler() -> InputHandler:
    """Get global input handler."""
    global _global_handler
    if _global_handler is None:
        _global_handler = InputHandler()
    return _global_handler


def parse_input(raw: str) -> ParsedInput:
    """Parse input using global handler."""
    return get_input_handler().parse_input(raw)


def validate_input(parsed: ParsedInput) -> ValidationResult:
    """Validate input using global handler."""
    return get_input_handler().validate_input(parsed)


__all__ = [
    'InputHandler',
    'InputType',
    'ParsedInput',
    'ValidationResult',
    'ValidationStatus',
    'get_input_handler',
    'parse_input',
    'validate_input',
]
