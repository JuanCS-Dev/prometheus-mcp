"""
qwen_core.types: Immutable Domain Types.

All domain value objects and enums live here. These types are:
- Immutable (frozen Pydantic models where possible)
- Fully typed (no Any except in generic contexts)
- Validated (Pydantic strict mode enabled)
- Serializable (JSON-compatible)

Design Principles:
- Single source of truth for domain types
- No circular imports possible (this module imports only stdlib + pydantic)
- Defensive validation with clear error messages
"""

from __future__ import annotations

import sys
import uuid
import warnings
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, model_validator


# =============================================================================
# EXCEPTIONS
# =============================================================================

class QwenCoreError(Exception):
    """Base exception for all qwen_core errors."""
    pass


class CapabilityViolationError(QwenCoreError):
    """Raised when an agent attempts an action beyond its capabilities."""
    pass


class ValidationError(QwenCoreError):
    """Raised when input validation fails."""
    pass


# =============================================================================
# ENUMS
# =============================================================================

class AgentRole(str, Enum):
    """
    Agent role types in the qwen multi-agent system.

    Core Roles:
        ARCHITECT: System architecture and design decisions
        EXPLORER: Codebase exploration and understanding
        PLANNER: Task planning and coordination
        REFACTORER: Code refactoring and improvement
        REVIEWER: Code review and quality assurance
        EXECUTOR: Command execution agent

    Specialized Roles:
        SECURITY: Security analysis and vulnerability detection
        PERFORMANCE: Performance optimization and profiling
        TESTING: Test generation and execution
        DOCUMENTATION: Documentation generation and maintenance
        DATABASE: Database operations and schema management
        DEVOPS: DevOps operations and CI/CD

    Governance Roles:
        GOVERNANCE: Constitutional governance (Justiça framework)
        COUNSELOR: Wise counselor (Sofia framework)
    """
    # Core roles
    ARCHITECT = "architect"
    EXPLORER = "explorer"
    PLANNER = "planner"
    REFACTORER = "refactorer"
    REVIEWER = "reviewer"
    EXECUTOR = "executor"

    # Specialized roles
    SECURITY = "security"
    PERFORMANCE = "performance"
    TESTING = "testing"
    DOCUMENTATION = "documentation"
    DATABASE = "database"
    DEVOPS = "devops"

    # Legacy alias
    REFACTOR = "refactor"

    # Governance roles
    GOVERNANCE = "governance"
    COUNSELOR = "counselor"


class AgentCapability(str, Enum):
    """
    Capability flags for agent sandboxing.

    Used to restrict what tools an agent can access.
    """
    READ_ONLY = "read_only"
    FILE_EDIT = "file_edit"
    BASH_EXEC = "bash_exec"
    GIT_OPS = "git_ops"
    DESIGN = "design"
    DATABASE = "database"


class TaskStatus(str, Enum):
    """Status of a task in the execution pipeline."""
    PENDING = "pending"
    THINKING = "thinking"
    ACTING = "acting"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"


# =============================================================================
# PYDANTIC MODELS
# =============================================================================

class AgentTask(BaseModel):
    """
    Immutable task specification for agent execution.

    Attributes:
        task_id: Unique identifier (auto-generated UUID)
        request: The task description/prompt
        context: Additional context data (limited to 10MB)
        session_id: Session identifier for multi-turn conversations
        metadata: Arbitrary metadata (limited to 10k keys)
        history: Previous interactions for context
    """
    model_config = {
        "strict": True,
        "validate_assignment": True,
        "frozen": False,  # Allow mutation for history append
    }

    task_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    request: str = Field(..., min_length=1, max_length=100_000)
    context: Dict[str, Any] = Field(default_factory=dict)
    session_id: str = Field(default="default", min_length=1)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    history: List[Dict[str, Any]] = Field(default_factory=list)

    @model_validator(mode='before')
    @classmethod
    def handle_deprecated_description(cls, values: Any) -> Any:
        """Migrate deprecated 'description' field to 'request'."""
        if isinstance(values, dict) and 'description' in values:
            warnings.warn(
                "AgentTask field 'description' is deprecated. Use 'request' instead.",
                DeprecationWarning,
                stacklevel=3
            )
            if 'request' not in values:
                values['request'] = values['description']
            del values['description']
        return values

    @model_validator(mode='after')
    def validate_size_limits(self) -> AgentTask:
        """Prevent resource exhaustion attacks."""
        # Context size limit: 10MB
        context_size = sys.getsizeof(str(self.context))
        max_context_size = 10 * 1024 * 1024
        if context_size > max_context_size:
            raise ValueError(
                f"Context size ({context_size:,} bytes) exceeds limit "
                f"({max_context_size:,} bytes)"
            )

        # Key count limit: 10k
        if isinstance(self.context, dict) and len(self.context) > 10_000:
            raise ValueError(
                f"Context has {len(self.context):,} keys (max 10,000)"
            )

        return self


class AgentResponse(BaseModel):
    """
    Immutable response from agent execution.

    Attributes:
        success: Whether the task completed successfully
        data: Result data from execution
        reasoning: Chain-of-thought explanation
        error: Error message if failed
        metrics: Numeric execution metrics (tokens, time, etc.)
        timestamp: When the response was created
        metadata: Additional non-numeric metadata
    """
    model_config = {
        "strict": True,
        "validate_assignment": True,
        "frozen": True,  # Responses are immutable
    }

    success: bool
    data: Dict[str, Any] = Field(default_factory=dict)
    reasoning: str = Field(default="")
    error: Optional[str] = Field(default=None)
    metrics: Dict[str, float] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class TaskResult(BaseModel):
    """
    Result wrapper for task execution.

    Used for compatibility with orchestration systems.
    """
    model_config = {
        "strict": True,
        "frozen": True,
    }

    task_id: str
    status: TaskStatus
    output: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)
