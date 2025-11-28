"""Phase 3.5: Reactive TUI & Async Streaming - Full Validation.

Tests Constitutional Requirements:
- P1: Zero UI blocking (Producer-Consumer)
- P2: Real-time streaming
- P3: Concurrent visuals
- P4: Optimistic UI
- P5: No infinite loading
"""

import asyncio
import pytest
from jdev_cli.streaming.executor import AsyncCommandExecutor
from jdev_cli.streaming.renderer import ReactiveRenderer, RenderEvent, RenderEventType


@pytest.mark.asyncio
async def test_zero_ui_blocking():
    """P1: Producer-Consumer pattern."""
    executor = AsyncCommandExecutor()
    renderer = ReactiveRenderer()

    await renderer.start()

    # Simulate heavy I/O (should not block renderer)
    async def slow_callback(chunk):
        await asyncio.sleep(0.01)  # Simulate processing
        await renderer.emit(RenderEvent(
            event_type=RenderEventType.OUTPUT,
            content=chunk.content,
            metadata={}
        ))

    result = await executor.execute('echo "test"', stream_callback=slow_callback)

    assert result.success
    await renderer.stop()


@pytest.mark.asyncio
async def test_realtime_streaming():
    """P2: Incremental output (line-by-line)."""
    executor = AsyncCommandExecutor()

    lines_received = []

    async def capture_callback(chunk):
        lines_received.append(chunk.content)

    # Command that produces multiple lines
    result = await executor.execute(
        'for i in 1 2 3; do echo "Line $i"; done',
        stream_callback=capture_callback
    )

    assert result.success
    assert len(lines_received) >= 3  # Should receive lines incrementally


@pytest.mark.asyncio
async def test_concurrent_execution():
    """P3: Multiple parallel streams without race conditions."""
    executor = AsyncCommandExecutor()

    commands = [
        'echo "Task 1"',
        'echo "Task 2"',
        'echo "Task 3"',
        'echo "Task 4"',
        'echo "Task 5"'
    ]

    results = await executor.execute_parallel(commands, max_concurrent=3)

    assert len(results) == 5
    assert all(r.success for r in results)


@pytest.mark.asyncio
async def test_optimistic_ui():
    """P4: Non-blocking feedback."""
    renderer = ReactiveRenderer()
    await renderer.start()

    # Emit should never block
    start = asyncio.get_event_loop().time()

    for i in range(100):
        await renderer.emit(RenderEvent(
            event_type=RenderEventType.OUTPUT,
            content=f"Line {i}\n",
            metadata={}
        ))

    elapsed = asyncio.get_event_loop().time() - start

    # Should be nearly instant (< 50ms for 100 emits)
    assert elapsed < 0.05

    await renderer.stop()


@pytest.mark.asyncio
async def test_no_buffering():
    """P5: Output appears immediately, not at completion."""
    executor = AsyncCommandExecutor()

    first_line_time = None
    completion_time = None

    async def timestamp_callback(chunk):
        nonlocal first_line_time
        if first_line_time is None:
            first_line_time = asyncio.get_event_loop().time()

    start = asyncio.get_event_loop().time()

    # Slow command (0.5s total)
    result = await executor.execute(
        'echo "First"; sleep 0.3; echo "Last"',
        stream_callback=timestamp_callback
    )

    completion_time = asyncio.get_event_loop().time()

    # First line should appear way before completion
    assert first_line_time is not None
    assert (completion_time - first_line_time) > 0.2  # Significant gap


@pytest.mark.asyncio
async def test_integration_shell_streaming():
    """Integration: Shell uses streaming for bash commands."""
    from jdev_cli.tools.exec import BashCommandTool

    tool = BashCommandTool()

    # Execute command via tool
    result = await tool.execute(command='ls -la | head -3')

    assert result.success
    assert 'exit_code' in result.data
    assert result.data['exit_code'] == 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
