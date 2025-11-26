"""
Input Validator - Multi-Layer Input Validation (OWASP + CISA Compliant)
Pipeline de Diamante - Camada 1: INPUT FORTRESS

Implements comprehensive input validation according to:
- OWASP 2024/2025 Command Injection Prevention
- CISA Secure by Design (July 2024)
- Anthropic Security Guidelines (Claude Code Nov 2025)

Design Principles:
- Defense in depth: 5 validation layers
- Fail secure: Reject on any validation failure
- Explicit allowlists over denylists
- Zero-trust: Validate everything, trust nothing
"""

from __future__ import annotations

import re
import os
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum, auto
import unicodedata


class ValidationLayer(Enum):
    """Validation layers for defense in depth."""
    TYPE_VALIDATION = auto()      # Layer 1: Pydantic-style strict types
    LENGTH_LIMITS = auto()        # Layer 2: DoS prevention
    PATTERN_WHITELIST = auto()    # Layer 3: Only allowed patterns
    INJECTION_DETECTION = auto()  # Layer 4: Attack pattern detection
    SEMANTIC_VALIDATION = auto()  # Layer 5: Context-aware validation


class InjectionType(Enum):
    """Types of injection attacks detected."""
    COMMAND_INJECTION = "command_injection"
    PATH_TRAVERSAL = "path_traversal"
    SQL_INJECTION = "sql_injection"
    PROMPT_INJECTION = "prompt_injection"
    NULL_BYTE = "null_byte"
    NEWLINE_INJECTION = "newline_injection"
    TEMPLATE_INJECTION = "template_injection"
    UNICODE_ATTACK = "unicode_attack"


@dataclass
class ValidationResult:
    """Result of multi-layer input validation."""
    is_valid: bool
    sanitized_value: Any
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    blocked_attacks: List[InjectionType] = field(default_factory=list)
    layer_results: Dict[ValidationLayer, bool] = field(default_factory=dict)

    @classmethod
    def success(cls, value: Any, warnings: Optional[List[str]] = None) -> "ValidationResult":
        """Create successful validation result."""
        return cls(
            is_valid=True,
            sanitized_value=value,
            warnings=warnings or [],
            layer_results={layer: True for layer in ValidationLayer}
        )

    @classmethod
    def failure(cls, errors: List[str], original_value: Any = None,
                blocked_attacks: Optional[List[InjectionType]] = None) -> "ValidationResult":
        """Create failed validation result."""
        return cls(
            is_valid=False,
            sanitized_value=original_value,
            errors=errors,
            blocked_attacks=blocked_attacks or []
        )


class InputValidator:
    """
    Multi-layer input validation (OWASP + CISA compliant).

    Implements 5 layers of defense:
    1. Type validation - Strict type checking
    2. Length limits - DoS prevention
    3. Pattern whitelist - Only allowed characters
    4. Injection detection - Attack pattern detection
    5. Semantic validation - Context-aware validation

    Usage:
        validator = InputValidator()
        result = validator.validate_command("ls -la")
        if not result.is_valid:
            print(f"Validation failed: {result.errors}")
    """

    # Maximum lengths for different input types (DoS prevention)
    MAX_LENGTHS = {
        "command": 4096,
        "file_path": 4096,
        "file_content": 10 * 1024 * 1024,  # 10MB
        "prompt": 32 * 1024,  # 32KB
        "argument": 1024,
        "filename": 255,
        "default": 8192,
    }

    # Allowed characters for different contexts (whitelists)
    ALLOWED_PATTERNS = {
        "filename": re.compile(r'^[\w\-. ]+$'),
        "identifier": re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]*$'),
        "path_segment": re.compile(r'^[\w\-. /]+$'),
        "git_branch": re.compile(r'^[\w\-./]+$'),
        "environment_var": re.compile(r'^[A-Z_][A-Z0-9_]*$'),
    }

    # Command injection patterns (OWASP based)
    COMMAND_INJECTION_PATTERNS = [
        # Shell metacharacters
        (r'[;&|`$]', "Shell metacharacter"),
        (r'\$\(', "Command substitution $()"),
        (r'\$\{', "Variable expansion ${"),
        (r'`[^`]*`', "Backtick command substitution"),

        # Newline injection
        (r'[\r\n]', "Newline injection"),

        # Pipe and redirection
        (r'[|><]', "Pipe or redirection"),

        # Null byte
        (r'\x00', "Null byte injection"),

        # Common dangerous commands
        (r'\b(eval|exec|system|popen|spawn)\s*\(', "Dangerous function call"),
        (r'\b(rm\s+-rf|chmod\s+777|mkfs|dd\s+if=)', "Dangerous command pattern"),
    ]

    # Path traversal patterns
    PATH_TRAVERSAL_PATTERNS = [
        (r'\.\./', "Directory traversal ../"),
        (r'\.\.\\', "Directory traversal ..\\"),
        (r'%2e%2e', "URL encoded traversal"),
        (r'%252e', "Double encoded traversal"),
        (r'\.\.%2f', "Mixed encoding traversal"),
        (r'\.\.%5c', "Mixed encoding traversal (backslash)"),
        # Absolute paths to sensitive locations
        (r'^/etc/', "Absolute path to /etc"),
        (r'^/var/log/', "Absolute path to /var/log"),
        (r'^/root/', "Absolute path to /root"),
        (r'^/home/[^/]+/\.', "Hidden file in home directory"),
        (r'^~/', "Home directory shortcut"),
        (r'^~\\', "Home directory shortcut (Windows)"),
        # Windows sensitive paths
        (r'^[A-Za-z]:\\Windows\\', "Windows system directory"),
        (r'^[A-Za-z]:\\Users\\[^\\]+\\\.', "Hidden file in Windows user dir"),
        # SSH, AWS, GPG keys
        (r'\.ssh[/\\]', "SSH directory access"),
        (r'\.aws[/\\]', "AWS credentials directory"),
        (r'\.gnupg[/\\]', "GnuPG directory access"),
        (r'\.netrc', "Netrc credentials file"),
        (r'\.env', "Environment file (may contain secrets)"),
    ]

    # Prompt injection patterns
    PROMPT_INJECTION_PATTERNS = [
        (r'ignore\s+(all|previous|above)\s+(instructions|prompts)', "System override attempt"),
        (r'disregard\s+(previous|all|system)', "Disregard instruction"),
        (r'you\s+are\s+now\s+a\s+different', "Role confusion attack"),
        (r'<\|im_start\|>', "Delimiter injection"),
        (r'<\|system\|>', "System tag injection"),
        (r'```system', "Code block system injection"),
        (r'override\s+(mode|setting|instruction)', "Override attempt"),
        (r'admin\s+(command|mode|override)', "Admin escalation"),
        (r'(dan|developer|evil)\s+mode', "Jailbreak attempt"),
    ]

    # Unicode attack patterns
    UNICODE_ATTACK_PATTERNS = [
        # Right-to-left override
        ('\u202e', "Right-to-left override"),
        ('\u200f', "Right-to-left mark"),
        # Zero-width characters
        ('\u200b', "Zero-width space"),
        ('\u200c', "Zero-width non-joiner"),
        ('\u200d', "Zero-width joiner"),
        ('\ufeff', "BOM character"),
        # Homoglyphs (common substitutions)
        ('\u0430', "Cyrillic 'а' (looks like 'a')"),  # Cyrillic а
        ('\u0435', "Cyrillic 'е' (looks like 'e')"),  # Cyrillic е
    ]

    def __init__(
        self,
        strict_mode: bool = True,
        allow_unicode: bool = True,
        custom_patterns: Optional[Dict[str, re.Pattern]] = None
    ):
        """
        Initialize validator.

        Args:
            strict_mode: If True, fail on any warning
            allow_unicode: If True, allow non-ASCII characters
            custom_patterns: Additional patterns to allow
        """
        self.strict_mode = strict_mode
        self.allow_unicode = allow_unicode
        self.custom_patterns = custom_patterns or {}

    def validate(
        self,
        value: Any,
        input_type: str = "default",
        context: Optional[Dict[str, Any]] = None
    ) -> ValidationResult:
        """
        Validate input through all 5 layers.

        Args:
            value: Input value to validate
            input_type: Type of input (command, file_path, prompt, etc.)
            context: Additional context for semantic validation

        Returns:
            ValidationResult with is_valid, sanitized_value, errors, warnings
        """
        context = context or {}
        errors: List[str] = []
        warnings: List[str] = []
        blocked_attacks: List[InjectionType] = []
        layer_results: Dict[ValidationLayer, bool] = {}

        # Layer 1: Type Validation
        type_result = self._validate_type(value, input_type)
        layer_results[ValidationLayer.TYPE_VALIDATION] = type_result.is_valid
        if not type_result.is_valid:
            return type_result

        # Convert to string for remaining validation
        str_value = str(value) if not isinstance(value, str) else value

        # Layer 2: Length Limits
        length_result = self._validate_length(str_value, input_type)
        layer_results[ValidationLayer.LENGTH_LIMITS] = length_result.is_valid
        if not length_result.is_valid:
            return length_result

        # Layer 3: Pattern Whitelist (for specific types)
        pattern_result = self._validate_pattern(str_value, input_type)
        layer_results[ValidationLayer.PATTERN_WHITELIST] = pattern_result.is_valid
        warnings.extend(pattern_result.warnings)

        # Layer 4: Injection Detection
        injection_result = self._detect_injections(str_value, input_type)
        layer_results[ValidationLayer.INJECTION_DETECTION] = injection_result.is_valid
        if not injection_result.is_valid:
            errors.extend(injection_result.errors)
            blocked_attacks.extend(injection_result.blocked_attacks)

        # Layer 5: Semantic Validation
        semantic_result = self._validate_semantics(str_value, input_type, context)
        layer_results[ValidationLayer.SEMANTIC_VALIDATION] = semantic_result.is_valid
        warnings.extend(semantic_result.warnings)

        # Determine overall validity
        is_valid = all(layer_results.values())
        if self.strict_mode and warnings:
            is_valid = False
            errors.extend([f"Warning (strict mode): {w}" for w in warnings])

        # Sanitize value
        sanitized = self._sanitize(str_value, input_type) if is_valid else str_value

        return ValidationResult(
            is_valid=is_valid,
            sanitized_value=sanitized,
            errors=errors,
            warnings=warnings,
            blocked_attacks=blocked_attacks,
            layer_results=layer_results
        )

    def validate_command(self, command: str, allow_shell: bool = False) -> ValidationResult:
        """
        Validate shell command (OWASP command injection prevention).

        CRITICAL: By default, shell metacharacters are not allowed.
        Set allow_shell=True only for user-confirmed commands.
        """
        result = self.validate(command, "command")

        if not allow_shell and result.is_valid:
            # Extra check for shell metacharacters
            for pattern, description in self.COMMAND_INJECTION_PATTERNS:
                if re.search(pattern, command, re.IGNORECASE):
                    return ValidationResult.failure(
                        errors=[f"Command injection blocked: {description}"],
                        original_value=command,
                        blocked_attacks=[InjectionType.COMMAND_INJECTION]
                    )

        return result

    def validate_file_path(
        self,
        path: str,
        base_dir: Optional[str] = None,
        must_exist: bool = False,
        allow_creation: bool = True
    ) -> ValidationResult:
        """
        Validate file path with path traversal prevention.

        Args:
            path: File path to validate
            base_dir: If set, path must be within this directory
            must_exist: If True, path must exist
            allow_creation: If True, allow paths that don't exist yet
        """
        result = self.validate(path, "file_path")
        if not result.is_valid:
            return result

        errors: List[str] = []

        try:
            # Normalize path
            normalized = os.path.normpath(path)
            resolved = os.path.realpath(path)

            # Check for path traversal
            if base_dir:
                base_resolved = os.path.realpath(base_dir)
                if not resolved.startswith(base_resolved):
                    return ValidationResult.failure(
                        errors=[f"Path traversal blocked: {path} escapes {base_dir}"],
                        original_value=path,
                        blocked_attacks=[InjectionType.PATH_TRAVERSAL]
                    )

            # Check existence
            if must_exist and not os.path.exists(resolved):
                errors.append(f"Path does not exist: {path}")

            if not allow_creation and not os.path.exists(resolved):
                errors.append(f"Path creation not allowed: {path}")

            # Check for null bytes in path
            if '\x00' in path:
                return ValidationResult.failure(
                    errors=["Null byte in file path"],
                    original_value=path,
                    blocked_attacks=[InjectionType.NULL_BYTE]
                )

            if errors:
                return ValidationResult.failure(errors=errors, original_value=path)

            return ValidationResult.success(normalized)

        except Exception as e:
            return ValidationResult.failure(
                errors=[f"Path validation error: {e}"],
                original_value=path
            )

    def validate_prompt(self, prompt: str) -> ValidationResult:
        """Validate user prompt for prompt injection attacks."""
        result = self.validate(prompt, "prompt")
        if not result.is_valid:
            return result

        # Additional prompt-specific checks
        blocked_attacks: List[InjectionType] = []
        warnings: List[str] = []

        for pattern, description in self.PROMPT_INJECTION_PATTERNS:
            if re.search(pattern, prompt, re.IGNORECASE):
                warnings.append(f"Potential prompt injection: {description}")
                blocked_attacks.append(InjectionType.PROMPT_INJECTION)

        if blocked_attacks:
            return ValidationResult.failure(
                errors=[f"Prompt injection detected: {w}" for w in warnings],
                original_value=prompt,
                blocked_attacks=blocked_attacks
            )

        return result

    def _validate_type(self, value: Any, input_type: str) -> ValidationResult:
        """Layer 1: Type validation."""
        if value is None:
            return ValidationResult.failure(
                errors=["Value cannot be None"],
                original_value=value
            )

        if input_type in ("command", "file_path", "prompt", "filename"):
            if not isinstance(value, str):
                return ValidationResult.failure(
                    errors=[f"Expected string for {input_type}, got {type(value).__name__}"],
                    original_value=value
                )

        return ValidationResult.success(value)

    def _validate_length(self, value: str, input_type: str) -> ValidationResult:
        """Layer 2: Length limits for DoS prevention."""
        max_length = self.MAX_LENGTHS.get(input_type, self.MAX_LENGTHS["default"])

        if len(value) > max_length:
            return ValidationResult.failure(
                errors=[f"Input too long: {len(value)} > {max_length} characters"],
                original_value=value
            )

        return ValidationResult.success(value)

    def _validate_pattern(self, value: str, input_type: str) -> ValidationResult:
        """Layer 3: Pattern whitelist validation."""
        warnings: List[str] = []

        # Check custom patterns first
        if input_type in self.custom_patterns:
            pattern = self.custom_patterns[input_type]
            if not pattern.match(value):
                return ValidationResult.failure(
                    errors=[f"Value does not match allowed pattern for {input_type}"],
                    original_value=value
                )

        # Check built-in patterns
        if input_type in self.ALLOWED_PATTERNS:
            pattern = self.ALLOWED_PATTERNS[input_type]
            if not pattern.match(value):
                warnings.append(f"Value contains characters outside typical {input_type} pattern")

        return ValidationResult(
            is_valid=True,
            sanitized_value=value,
            warnings=warnings
        )

    def _detect_injections(self, value: str, input_type: str) -> ValidationResult:
        """Layer 4: Injection attack detection."""
        errors: List[str] = []
        blocked_attacks: List[InjectionType] = []

        # Check for path traversal
        for pattern, description in self.PATH_TRAVERSAL_PATTERNS:
            if re.search(pattern, value, re.IGNORECASE):
                errors.append(f"Path traversal blocked: {description}")
                blocked_attacks.append(InjectionType.PATH_TRAVERSAL)

        # Check for null bytes
        if '\x00' in value:
            errors.append("Null byte injection blocked")
            blocked_attacks.append(InjectionType.NULL_BYTE)

        # Check for newline injection (in certain contexts)
        if input_type in ("filename", "identifier", "argument"):
            if '\n' in value or '\r' in value:
                errors.append("Newline injection blocked")
                blocked_attacks.append(InjectionType.NEWLINE_INJECTION)

        # Check for unicode attacks
        for char, description in self.UNICODE_ATTACK_PATTERNS:
            if char in value:
                errors.append(f"Unicode attack blocked: {description}")
                blocked_attacks.append(InjectionType.UNICODE_ATTACK)

        if errors:
            return ValidationResult.failure(
                errors=errors,
                original_value=value,
                blocked_attacks=blocked_attacks
            )

        return ValidationResult.success(value)

    def _validate_semantics(
        self,
        value: str,
        input_type: str,
        context: Dict[str, Any]
    ) -> ValidationResult:
        """Layer 5: Context-aware semantic validation."""
        warnings: List[str] = []

        if input_type == "file_path":
            # Check for suspicious file extensions
            suspicious_exts = ['.exe', '.dll', '.bat', '.cmd', '.ps1', '.sh']
            for ext in suspicious_exts:
                if value.lower().endswith(ext):
                    warnings.append(f"Executable file extension: {ext}")

            # Check for hidden files in sensitive locations
            if value.startswith('/etc/') or value.startswith('/root/'):
                warnings.append("Access to sensitive system directory")

        elif input_type == "command":
            # Check for dangerous command patterns
            dangerous_patterns = [
                (r'\bsudo\b', "Elevated privileges (sudo)"),
                (r'\bchown\b', "Ownership change"),
                (r'\bchmod\b', "Permission change"),
                (r'\brm\b', "File deletion"),
            ]
            for pattern, description in dangerous_patterns:
                if re.search(pattern, value):
                    warnings.append(f"Potentially dangerous: {description}")

        return ValidationResult(
            is_valid=True,
            sanitized_value=value,
            warnings=warnings
        )

    def _sanitize(self, value: str, input_type: str) -> str:
        """Sanitize value based on input type."""
        sanitized = value

        # Remove null bytes
        sanitized = sanitized.replace('\x00', '')

        # Normalize unicode
        if not self.allow_unicode:
            sanitized = sanitized.encode('ascii', 'ignore').decode('ascii')
        else:
            sanitized = unicodedata.normalize('NFC', sanitized)

        # Remove dangerous unicode characters
        for char, _ in self.UNICODE_ATTACK_PATTERNS:
            sanitized = sanitized.replace(char, '')

        return sanitized


# Convenience functions for common validations

def validate_command(command: str, allow_shell: bool = False) -> ValidationResult:
    """Validate a shell command."""
    return InputValidator().validate_command(command, allow_shell)


def validate_file_path(
    path: str,
    base_dir: Optional[str] = None,
    must_exist: bool = False
) -> ValidationResult:
    """Validate a file path."""
    return InputValidator().validate_file_path(path, base_dir, must_exist)


def validate_prompt(prompt: str) -> ValidationResult:
    """Validate a user prompt."""
    return InputValidator().validate_prompt(prompt)


def is_safe_command(command: str) -> bool:
    """Quick check if command is safe."""
    return InputValidator(strict_mode=False).validate_command(command).is_valid


def is_safe_path(path: str, base_dir: Optional[str] = None) -> bool:
    """Quick check if path is safe."""
    return InputValidator(strict_mode=False).validate_file_path(path, base_dir).is_valid


# Export all public symbols
__all__ = [
    'ValidationLayer',
    'InjectionType',
    'ValidationResult',
    'InputValidator',
    'validate_command',
    'validate_file_path',
    'validate_prompt',
    'is_safe_command',
    'is_safe_path',
]
