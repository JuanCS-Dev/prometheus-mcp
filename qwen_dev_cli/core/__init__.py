"""
Core modules for qwen-dev-cli.
Pipeline de Diamante - Core Infrastructure

This package contains the foundational components for the Diamond Pipeline:

CAMADA 1 - INPUT FORTRESS:
- input_validator: Multi-layer input validation (OWASP compliant)
- prompt_shield: Prompt injection prevention
- input_enhancer: Typo correction and smart input processing

CAMADA 2 - GOVERNANCE GATE:
- audit_logger: Governance audit logging with traceability

CAMADA 3 - EXECUTION SANDBOX:
- sandbox: Secure command execution
- python_sandbox: Python code sandboxing
- atomic_ops: Atomic file operations
- undo_manager: Undo/redo system
- tool_chain: Transaction-like tool execution
- resilience: Concurrency, rate limiting, resource management

CAMADA 4 - OUTPUT SHIELD:
- error_presenter: User-friendly error messages
- session_manager: Session persistence and recovery
- context_tracker: Conversation context awareness
"""

# Lazy imports for performance
__all__ = [
    # Input Fortress (Camada 1)
    'InputValidator',
    'ValidationResult',
    'validate_command',
    'validate_file_path',
    'PromptShield',
    'ShieldResult',
    'InputEnhancer',
    'EnhancedInput',

    # Governance Gate (Camada 2)
    'AuditLogger',
    'AuditEventType',
    'audit_log',
    'audit_governance',

    # Execution Sandbox (Camada 3)
    'SecureExecutor',
    'ExecutionResult',
    'PythonSandbox',
    'AtomicFileOps',
    'AtomicResult',
    'UndoManager',
    'AtomicToolChain',
    'ConcurrencyManager',
    'ResourceLimits',
    'RateLimiter',
    'EncodingSafety',

    # Output Shield (Camada 4)
    'ErrorPresenter',
    'PresentedError',
    'SessionManager',
    'SessionSnapshot',
    'ContextTracker',
    'ResolvedReference',
]


def __getattr__(name: str):
    """Lazy loading of modules for faster startup."""

    # Input Validator
    if name in ('InputValidator', 'ValidationResult', 'validate_command', 'validate_file_path'):
        from .input_validator import InputValidator, ValidationResult, validate_command, validate_file_path
        return locals()[name]

    # Prompt Shield
    if name in ('PromptShield', 'ShieldResult'):
        from .prompt_shield import PromptShield, ShieldResult
        return locals()[name]

    # Input Enhancer
    if name in ('InputEnhancer', 'EnhancedInput'):
        from .input_enhancer import InputEnhancer, EnhancedInput
        return locals()[name]

    # Audit Logger
    if name in ('AuditLogger', 'AuditEventType', 'audit_log', 'audit_governance'):
        from .audit_logger import AuditLogger, AuditEventType, audit_log, audit_governance
        return locals()[name]

    # Secure Executor
    if name in ('SecureExecutor', 'ExecutionResult'):
        from .sandbox import SecureExecutor, ExecutionResult
        return locals()[name]

    # Python Sandbox
    if name in ('PythonSandbox',):
        from .python_sandbox import PythonSandbox
        return locals()[name]

    # Atomic Operations
    if name in ('AtomicFileOps', 'AtomicResult'):
        from .atomic_ops import AtomicFileOps, AtomicResult
        return locals()[name]

    # Undo Manager
    if name in ('UndoManager',):
        from .undo_manager import UndoManager
        return locals()[name]

    # Tool Chain
    if name in ('AtomicToolChain',):
        from .tool_chain import AtomicToolChain
        return locals()[name]

    # Resilience
    if name in ('ConcurrencyManager', 'ResourceLimits', 'RateLimiter', 'EncodingSafety'):
        from .resilience import ConcurrencyManager, ResourceLimits, RateLimiter, EncodingSafety
        return locals()[name]

    # Error Presenter
    if name in ('ErrorPresenter', 'PresentedError'):
        from .error_presenter import ErrorPresenter, PresentedError
        return locals()[name]

    # Session Manager
    if name in ('SessionManager', 'SessionSnapshot'):
        from .session_manager import SessionManager, SessionSnapshot
        return locals()[name]

    # Context Tracker
    if name in ('ContextTracker', 'ResolvedReference'):
        from .context_tracker import ContextTracker, ResolvedReference
        return locals()[name]

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
