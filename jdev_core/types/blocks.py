"""
Unified Block Types for Markdown/Output Rendering.

SCALE & SUSTAIN Phase 1.3 - Type Consolidation.

Consolidated from:
- jdev_cli/tui/components/block_detector.py:17 (string values)
- jdev_cli/tui/components/block_renderers.py:48 (auto values)

Author: JuanCS Dev
Date: 2025-11-26
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, Dict, Any


class BlockType(Enum):
    """
    Unified block types for markdown and output rendering.

    String values maintained for serialization compatibility.

    To add new type:
        MY_TYPE = "my_type"

    Categories:
        - Core markdown (PARAGRAPH, CODE_FENCE, etc.)
        - Claude Code Web style (TOOL_CALL, DIFF_BLOCK, etc.)
        - Extensions (MERMAID_DIAGRAM, etc.)
    """
    # Core markdown blocks
    UNKNOWN = "unknown"
    PARAGRAPH = "paragraph"
    CODE_FENCE = "code_fence"
    TABLE = "table"
    CHECKLIST = "checklist"
    HEADING = "heading"
    LIST = "list"
    BLOCKQUOTE = "blockquote"
    HORIZONTAL_RULE = "horizontal_rule"
    EMPTY = "empty"

    # Claude Code Web style blocks
    TOOL_CALL = "tool_call"
    TOOL_OUTPUT = "tool_output"
    DIFF_BLOCK = "diff_block"
    STATUS_BADGE = "status_badge"

    # Extension blocks (for future use)
    MERMAID_DIAGRAM = "mermaid_diagram"
    MATH_BLOCK = "math_block"
    ALERT_BLOCK = "alert_block"


@dataclass
class BlockInfo:
    """Information about a detected block."""
    block_type: BlockType
    start_line: int
    end_line: Optional[int] = None
    language: Optional[str] = None  # For code fences
    is_complete: bool = False
    content: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Ensure end_line is set."""
        if self.end_line is None:
            self.end_line = self.start_line


@dataclass
class BlockRenderConfig:
    """Configuration for block rendering."""
    show_line_numbers: bool = True
    show_language_badge: bool = True
    max_height: Optional[int] = None
    syntax_theme: str = "monokai"
    copyable: bool = True


__all__ = [
    'BlockType',
    'BlockInfo',
    'BlockRenderConfig',
]
