"""
qwen_core: The Domain Kernel.

This package contains the core domain types and protocols that define
the contract between all other packages. Dependencies flow INWARD:

    qwen_cli ─────┐
                  │
    qwen_agents ──┼──> qwen_core
                  │
    qwen_tools ───┘

RULES:
1. qwen_core imports NOTHING from qwen_cli, qwen_dev_cli, or qwen_agents
2. All types here are immutable value objects or protocols
3. No side effects, no I/O, no state
4. 100% type coverage required

Author: Boris Cherny (Anthropic Claude Code Team Pattern)
"""

from qwen_core.types import (
    # Enums
    AgentRole,
    AgentCapability,
    TaskStatus,
    # Models
    AgentTask,
    AgentResponse,
    TaskResult,
    # Exceptions
    CapabilityViolationError,
    QwenCoreError,
)

from qwen_core.protocols import (
    LLMClientProtocol,
    MCPClientProtocol,
    AgentProtocol,
    ToolProtocol,
)

from qwen_core.language_detector import (
    LanguageDetector,
    LANGUAGE_NAMES,
)

__all__ = [
    # Enums
    "AgentRole",
    "AgentCapability",
    "TaskStatus",
    # Models
    "AgentTask",
    "AgentResponse",
    "TaskResult",
    # Exceptions
    "CapabilityViolationError",
    "QwenCoreError",
    # Protocols
    "LLMClientProtocol",
    "MCPClientProtocol",
    "AgentProtocol",
    "ToolProtocol",
    # Utilities
    "LanguageDetector",
    "LANGUAGE_NAMES",
]

__version__ = "1.0.0"
