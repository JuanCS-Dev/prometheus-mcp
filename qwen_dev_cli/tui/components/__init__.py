"""
TUI Components - Reusable UI building blocks.

Component library for consistent, beautiful terminal UI.

Philosophy:
- Composable and reusable
- Consistent styling
- Accessible by default
- Performant (60 FPS target)
- SCALABLE (Registry-based architecture)

Components Implemented:
✅ message.py - Message boxes with typing effect
✅ status.py - Status badges and spinners
✅ progress.py - Animated progress bars
✅ code.py - Enhanced code blocks
✅ diff.py - Diff viewer (GitHub style)
✅ file_tree.py - Collapsible file tree (Cursor-style)
✅ pills.py - Context pills (Cursor @ mentions)
✅ toast.py - Notification toasts (VSCode-style)
✅ autocomplete.py - Context-aware autocomplete
✅ block_renderers.py - Scalable block rendering (NEW)
✅ streaming_v2.py - Scalable streaming response (NEW)

SCALABLE ARCHITECTURE (v4.0):
To add a new block type, just create a class:

    from .block_renderers import BlockRenderer, BlockType

    class MyRenderer(BlockRenderer):
        block_type = BlockType.MY_TYPE
        pattern = r'^my-pattern'
        priority = 50

        def render(self, block):
            return Text(block.content)

Auto-registered, auto-detected, auto-rendered!

Created: 2025-11-18 20:05 UTC
Updated: 2025-11-25 (Scalable Architecture v4.0)
Status: Phase 4 Complete - Scalable Streaming
"""

__version__ = "4.0.0"
__status__ = "Phase 4 Complete - Scalable Streaming"

# Core components
from ._enums import MessageRole, ProgressStyle
from .message import MessageBox, Message, create_assistant_message, create_user_message
from .status import StatusBadge, StatusLevel, Spinner, SpinnerStyle, create_processing_indicator
from .progress import ProgressBar, ProgressState, create_progress_bar
from .code import CodeBlock, CodeSnippet, InlineCode, create_code_block
from .diff import DiffViewer, DiffMode, DiffLine

# Advanced components (Cursor-inspired)
from .file_tree import FileTree, FileNode, FileType, create_file_tree
from .pills import ContextPill, PillContainer, PillType, create_pill_from_file
from .toasts import (
    Toast, ToastManager, ToastType,
    show_success, show_error, show_info, show_warning, show_wisdom,
    create_toast_manager
)
from .autocomplete import (
    ContextAwareCompleter, SmartAutoSuggest, CompletionItem, CompletionType,
    create_completer
)

# Scalable Streaming Architecture (v4.0)
from .block_renderers import (
    BlockType, BlockInfo, BlockRenderer, BlockRendererRegistry,
    detect_block_type, render_block, list_renderers,
    # Built-in renderers (for extension)
    HeadingRenderer, CodeFenceRenderer, TableRenderer,
    ChecklistRenderer, ToolCallRenderer, StatusBadgeRenderer,
    DiffBlockRenderer, BlockquoteRenderer, ListRenderer,
)
from .streaming_v2 import StreamingResponseV2, StreamingMetrics
from .block_detector_v2 import BlockDetectorV2

__all__ = [
    # Core
    "MessageBox", "Message", "MessageRole", "create_assistant_message", "create_user_message",
    "StatusBadge", "StatusLevel", "Spinner", "SpinnerStyle", "create_processing_indicator",
    "ProgressBar", "ProgressState", "ProgressStyle", "create_progress_bar",
    "CodeBlock", "CodeSnippet", "InlineCode", "create_code_block",
    "DiffViewer", "DiffMode", "DiffLine",
    
    # Advanced
    "FileTree", "FileNode", "FileType", "create_file_tree",
    "ContextPill", "PillContainer", "PillType", "create_pill_from_file",
    "Toast", "ToastManager", "ToastType",
    "show_success", "show_error", "show_info", "show_warning", "show_wisdom",
    "create_toast_manager",
    "ContextAwareCompleter", "SmartAutoSuggest", "CompletionItem", "CompletionType",
    "create_completer",

    # Scalable Streaming (v4.0)
    "BlockType", "BlockInfo", "BlockRenderer", "BlockRendererRegistry",
    "detect_block_type", "render_block", "list_renderers",
    "StreamingResponseV2", "StreamingMetrics", "BlockDetectorV2",
    # Built-in renderers
    "HeadingRenderer", "CodeFenceRenderer", "TableRenderer",
    "ChecklistRenderer", "ToolCallRenderer", "StatusBadgeRenderer",
    "DiffBlockRenderer", "BlockquoteRenderer", "ListRenderer",
]
