"""
Type definitions for qwen-dev-cli.

This module contains all type aliases, protocols, and type definitions
used throughout the codebase. Following Boris Cherny's philosophy:
"If it doesn't have types, it's not production."

Design principles:
- Explicit over implicit
- Type safety over convenience
- Runtime validation where needed
- Zero `Any` types (except for truly dynamic cases)
"""

from __future__ import annotations

from typing import (
    Any,
    Callable,
    Coroutine,
    Dict,
    List,
    Literal,
    Optional,
    Protocol,
    TypeAlias,
    TypedDict,
    TypeVar,
    Union,
    runtime_checkable,
)
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass
from enum import Enum


# ============================================================================
# GENERIC TYPE VARIABLES
# ============================================================================

T = TypeVar('T')
T_co = TypeVar('T_co', covariant=True)
T_contra = TypeVar('T_contra', contravariant=True)


# ============================================================================
# MESSAGE & CONVERSATION TYPES
# ============================================================================

class MessageRole(str, Enum):
    """Role of a message in a conversation."""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class Message(TypedDict, total=False):
    """Single message in a conversation.
    
    Required fields:
        role: Who sent the message
        content: The message text
    
    Optional fields:
        name: Name of the tool/function (for role="tool")
        tool_call_id: ID of the tool call this message responds to
    """
    role: MessageRole
    content: str
    name: str  # Optional
    tool_call_id: str  # Optional


MessageList: TypeAlias = List[Message]


# ============================================================================
# TOOL & FUNCTION TYPES
# ============================================================================

class ToolParameter(TypedDict, total=False):
    """Parameter definition for a tool."""
    type: str
    description: str
    enum: List[str]  # For enum types
    required: bool


class ToolDefinition(TypedDict):
    """Complete tool definition for LLM function calling."""
    name: str
    description: str
    parameters: Dict[str, ToolParameter]


class ToolCall(TypedDict):
    """A tool invocation request from the LLM."""
    id: str
    tool: str
    arguments: Dict[str, Any]


class ToolResult(TypedDict):
    """Result of a tool execution."""
    tool_call_id: str
    success: bool
    output: str
    error: Optional[str]


# ============================================================================
# FILE & PATH TYPES
# ============================================================================

FilePath: TypeAlias = Union[str, Path]
FileContent: TypeAlias = str
FileEncoding: TypeAlias = Literal["utf-8", "ascii", "latin-1"]


class FileEdit(TypedDict):
    """Specification for a file edit operation."""
    path: FilePath
    old_text: str
    new_text: str
    line_range: Optional[tuple[int, int]]


class FileOperation(TypedDict):
    """A file system operation."""
    operation: Literal["read", "write", "edit", "delete", "move", "copy"]
    path: FilePath
    content: Optional[FileContent]
    destination: Optional[FilePath]  # For move/copy


# ============================================================================
# CONTEXT & STATE TYPES
# ============================================================================

class ContextEntry(TypedDict):
    """Single entry in the execution context."""
    key: str
    value: Any
    timestamp: datetime
    source: str


class SessionState(TypedDict):
    """Complete session state for persistence."""
    session_id: str
    cwd: FilePath
    history: List[str]
    conversation: MessageList
    context: Dict[str, Any]
    files_read: List[FilePath]
    files_modified: List[FilePath]
    tool_calls_count: int
    created_at: datetime
    last_activity: datetime


# ============================================================================
# ERROR & RECOVERY TYPES
# ============================================================================

class ErrorCategory(str, Enum):
    """Category of error for recovery strategies."""
    SYNTAX = "syntax"
    IMPORT = "import"
    TYPE = "type"
    RUNTIME = "runtime"
    PERMISSION = "permission"
    NETWORK = "network"
    TIMEOUT = "timeout"
    RESOURCE = "resource"
    UNKNOWN = "unknown"


class ErrorInfo(TypedDict):
    """Structured error information."""
    category: ErrorCategory
    message: str
    traceback: Optional[str]
    file: Optional[FilePath]
    line: Optional[int]
    recoverable: bool


class RecoveryStrategy(TypedDict):
    """Strategy for recovering from an error."""
    category: ErrorCategory
    max_attempts: int
    backoff_factor: float
    timeout_seconds: float
    fallback: Optional[str]


# ============================================================================
# LLM & GENERATION TYPES
# ============================================================================

class GenerationConfig(TypedDict, total=False):
    """Configuration for LLM generation."""
    max_tokens: int
    temperature: float
    top_p: float
    top_k: int
    stop_sequences: List[str]
    presence_penalty: float
    frequency_penalty: float


class TokenUsage(TypedDict):
    """Token usage statistics."""
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost_estimate: Optional[float]


class LLMResponse(TypedDict):
    """Complete LLM response with metadata."""
    content: str
    usage: TokenUsage
    model: str
    finish_reason: Literal["stop", "length", "tool_calls", "error"]
    tool_calls: Optional[List[ToolCall]]


# ============================================================================
# VALIDATION & CONSTRAINTS
# ============================================================================

class ValidationRule(TypedDict):
    """A validation rule for input."""
    field: str
    rule: Literal["required", "type", "range", "pattern", "custom"]
    constraint: Any
    error_message: str


class ValidationResult(TypedDict):
    """Result of validation."""
    valid: bool
    errors: List[str]
    warnings: List[str]


# ============================================================================
# PROTOCOLS (Structural Subtyping)
# ============================================================================

@runtime_checkable
class Serializable(Protocol):
    """Protocol for objects that can be serialized."""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        ...

    @classmethod
    def from_dict(cls: type[T], data: Dict[str, Any]) -> T:
        """Create instance from dictionary."""
        ...


@runtime_checkable
class Validatable(Protocol):
    """Protocol for objects that can be validated."""

    def validate(self) -> ValidationResult:
        """Validate the object's state."""
        ...


@runtime_checkable
class AsyncExecutable(Protocol[T_co]):
    """Protocol for async executable objects."""

    async def execute(self) -> T_co:
        """Execute the operation asynchronously."""
        ...


@runtime_checkable
class Streamable(Protocol[T_co]):
    """Protocol for objects that can stream data."""

    async def stream(self) -> Coroutine[Any, Any, T_co]:
        """Stream data asynchronously."""
        ...


# ============================================================================
# WORKFLOW & ORCHESTRATION TYPES
# ============================================================================

class WorkflowStep(TypedDict):
    """Single step in a workflow."""
    id: str
    name: str
    tool: str
    arguments: Dict[str, Any]
    depends_on: List[str]
    timeout_seconds: float
    retry_policy: Optional[RecoveryStrategy]


class WorkflowDefinition(TypedDict):
    """Complete workflow definition."""
    id: str
    name: str
    description: str
    steps: List[WorkflowStep]
    rollback_steps: Optional[List[WorkflowStep]]


class WorkflowState(str, Enum):
    """State of a workflow execution."""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


class WorkflowExecution(TypedDict):
    """State of a workflow execution."""
    workflow_id: str
    state: WorkflowState
    current_step: Optional[str]
    completed_steps: List[str]
    failed_step: Optional[str]
    error: Optional[ErrorInfo]
    started_at: datetime
    completed_at: Optional[datetime]


# ============================================================================
# CONFIGURATION TYPES
# ============================================================================

class ProviderConfig(TypedDict, total=False):
    """Configuration for an LLM provider."""
    api_key: str
    base_url: str
    model: str
    timeout: float
    max_retries: int


class AppConfig(TypedDict, total=False):
    """Application configuration."""
    # LLM providers
    hf_token: str
    nebius_api_key: str
    gemini_api_key: str
    ollama_enabled: bool

    # Models
    hf_model: str
    gemini_model: str

    # Limits
    max_context_tokens: int
    max_output_tokens: int

    # Features
    enable_sandbox: bool
    enable_hooks: bool
    enable_recovery: bool

    # UI
    gradio_port: int
    gradio_share: bool


# ============================================================================
# CALLBACK TYPES
# ============================================================================

ProgressCallback: TypeAlias = Callable[[float, str], None]
ErrorCallback: TypeAlias = Callable[[ErrorInfo], None]
TokenCallback: TypeAlias = Callable[[int, int], None]  # (input_tokens, output_tokens)


# ============================================================================
# DATACLASSES (Immutable Data)
# ============================================================================

@dataclass(frozen=True)
class CodeSpan:
    """A span of code with location information."""
    file: FilePath
    start_line: int
    end_line: int
    content: str


@dataclass(frozen=True)
class DiffHunk:
    """A single hunk in a diff."""
    old_start: int
    old_count: int
    new_start: int
    new_count: int
    lines: List[str]


# ============================================================================
# TYPE GUARDS (Runtime Type Checking)
# ============================================================================

def is_message(obj: Any) -> bool:
    """Check if object is a valid Message."""
    if not isinstance(obj, dict):
        return False
    return (
        'role' in obj and
        'content' in obj and
        isinstance(obj['role'], str) and
        isinstance(obj['content'], str)
    )


def is_message_list(obj: Any) -> bool:
    """Check if object is a valid MessageList."""
    if not isinstance(obj, list):
        return False
    return all(is_message(msg) for msg in obj)


def is_file_path(obj: Any) -> bool:
    """Check if object is a valid FilePath."""
    return isinstance(obj, (str, Path))


# ============================================================================
# EXPORTS
# ============================================================================

__all__ = [
    # Type vars
    'T', 'T_co', 'T_contra',

    # Enums
    'MessageRole', 'ErrorCategory', 'WorkflowState',

    # Type aliases
    'FilePath', 'FileContent', 'FileEncoding',
    'MessageList', 'ProgressCallback', 'ErrorCallback', 'TokenCallback',

    # TypedDicts
    'Message', 'ToolParameter', 'ToolDefinition', 'ToolCall', 'ToolResult',
    'FileEdit', 'FileOperation', 'ContextEntry', 'SessionState',
    'ErrorInfo', 'RecoveryStrategy', 'GenerationConfig', 'TokenUsage',
    'LLMResponse', 'ValidationRule', 'ValidationResult',
    'WorkflowStep', 'WorkflowDefinition', 'WorkflowExecution',
    'ProviderConfig', 'AppConfig',

    # Protocols
    'Serializable', 'Validatable', 'AsyncExecutable', 'Streamable',

    # Dataclasses
    'CodeSpan', 'DiffHunk',

    # Type guards
    'is_message', 'is_message_list', 'is_file_path',
]
