"""
DEVSQUAD: Federation of Specialists - Agent Foundation

This module provides the base abstractions for the multi-agent system where
specialized AI agents collaborate to solve complex development tasks.

Architecture:
    - BaseAgent: Abstract base class for all specialist agents
    - AgentRole: Enum defining specialist roles (Architect, Explorer, etc.)
    - AgentCapability: Enum defining what tools each agent can use
    - AgentTask: Pydantic model for task definition
    - AgentResponse: Pydantic model for agent output

Philosophy (Boris Cherny):
    "Each agent is a specialist, not a generalist."
    - Strict capability enforcement
    - Type-safe communication
    - Zero placeholders
    - Production-ready code only
"""

from qwen_dev_cli.agents.base import (
    AgentCapability,
    AgentRole,
    AgentTask,
    AgentResponse,
    BaseAgent,
)
from qwen_dev_cli.agents.architect import ArchitectAgent
from qwen_dev_cli.agents.explorer import ExplorerAgent
from qwen_dev_cli.agents.planner import PlannerAgent
from qwen_dev_cli.agents.refactorer import RefactorerAgent
from qwen_dev_cli.agents.reviewer import ReviewerAgent

__all__ = [
    "AgentCapability",
    "AgentRole",
    "AgentTask",
    "AgentResponse",
    "BaseAgent",
    "ArchitectAgent",
    "ExplorerAgent",
    "PlannerAgent",
    "RefactorerAgent",
    "ReviewerAgent",
]
