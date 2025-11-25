"""
qwen_cli.components - Bridge components for streaming markdown.

This module provides adapters that connect qwen_cli (main entry point)
to qwen_dev_cli.tui.components (streaming markdown widgets).

CORRIGE AIR GAP:
- Entry point usa qwen_cli.app, não qwen_dev_cli.tui
- Componentes streaming estavam órfãos em qwen_dev_cli/tui/components/
- Este adapter faz a ponte entre os dois mundos

Created: 2025-11-25
"""

from .streaming_adapter import (
    StreamingResponseWidget,
    StreamingMarkdownAdapter,
)

__all__ = [
    "StreamingResponseWidget",
    "StreamingMarkdownAdapter",
]
