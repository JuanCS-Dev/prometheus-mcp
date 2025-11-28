#!/usr/bin/env python3
"""
Verify Streaming Components (SoftBuffer, BlockDetector, WidgetFactory).
"""

import sys
from pathlib import Path
from rich.console import Console

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from jdev_tui.core.streaming.soft_buffer import SoftBuffer
from jdev_cli.tui.components.block_detector import BlockDetector, BlockType
from jdev_cli.tui.components.streaming_markdown import BlockWidgetFactory

console = Console()

def test_soft_buffer():
    print("\n[1] Testing SoftBuffer...")
    buffer = SoftBuffer()

    # Test 1: Safe text
    assert buffer.feed("Hello ") == "Hello "
    print("✅ Safe text passed")

    # Test 2: Incomplete suffix
    assert buffer.feed("This is *") == ""
    print("✅ Incomplete suffix buffered")

    # Test 3: Complete suffix (released by non-marker)
    assert buffer.feed("*bold") == "This is **bold"
    print("✅ Complete suffix released")

    # Test 4: Incomplete code
    assert buffer.feed("Code `") == ""
    print("✅ Incomplete code buffered")

    assert buffer.feed("print()`") == ""
    print("✅ Code span buffered (ends with backtick)")

    assert buffer.feed(" ") == "Code `print()` "
    print("✅ Complete code released by space")

def test_block_detector():
    print("\n[2] Testing BlockDetector...")
    detector = BlockDetector()

    # Test Gemini Native Tool Call
    chunk = "[TOOL_CALL:code_execution:{\"code\": \"print('hello')\"}]"
    blocks = detector.process_chunk(chunk)

    found = False
    for block in blocks:
        if block.block_type == BlockType.TOOL_CALL:
            print(f"✅ Detected TOOL_CALL: {block.content}")
            found = True
            break

    if not found:
        print(f"❌ Failed to detect TOOL_CALL. Blocks: {blocks}")

def test_widget_factory():
    print("\n[3] Testing BlockWidgetFactory...")
    factory = BlockWidgetFactory()
    detector = BlockDetector()

    chunk = "[TOOL_CALL:code_execution:{\"code\": \"print('hello')\"}]"
    blocks = detector.process_chunk(chunk)

    for block in blocks:
        if block.block_type == BlockType.TOOL_CALL:
            renderable = factory.render_block(block)
            console.print(renderable)
            print("✅ Rendered TOOL_CALL (Visual Check)")

if __name__ == "__main__":
    test_soft_buffer()
    test_block_detector()
    test_widget_factory()
