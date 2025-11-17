"""Professional prompt engineering for Qwen-based code CLI."""

from .system_prompts import SYSTEM_PROMPT, build_system_prompt
from .few_shot_examples import FEW_SHOT_EXAMPLES, get_examples_for_context
from .user_templates import build_user_prompt, format_tool_schemas, format_context

__all__ = [
    "SYSTEM_PROMPT",
    "build_system_prompt",
    "FEW_SHOT_EXAMPLES",
    "get_examples_for_context",
    "build_user_prompt",
    "format_tool_schemas",
    "format_context",
]
