"""
PROMETHEUS Tools Module.

AutoTools-inspired automatic tool generation (arXiv:2405.16533):
- Generate tools on-demand from natural language
- Test and validate in sandbox
- Improve iteratively based on failures
- Register for future use
"""

from .tool_factory import ToolFactory, ToolSpec, ToolGenerationRequest, ToolGenerationError

__all__ = [
    "ToolFactory",
    "ToolSpec",
    "ToolGenerationRequest",
    "ToolGenerationError",
]
