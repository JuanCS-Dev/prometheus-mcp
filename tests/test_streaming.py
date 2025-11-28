"""Tests for streaming module."""

import pytest
import asyncio
from jdev_cli.streaming import (
    AsyncCommandExecutor,
    ReactiveRenderer,
    RenderEvent,
    RenderEventType,
    StreamProcessor,
    StreamType,
    OutputChunk,
)


@pytest.mark.asyncio
async def test_stream_processor():
    """Test stream processor."""
    processor = StreamProcessor()

    # Feed chunks
    await processor.feed("line 1\n", StreamType.STDOUT)
    await processor.feed("line 2\n", StreamType.STDOUT)
    await processor.close()

    # Consume
    chunks = []
    async for chunk in processor.consume():
        chunks.append(chunk)

    assert len(chunks) == 2
    assert chunks[0].content == "line 1\n"
    assert chunks[1].content == "line 2\n"


@pytest.mark.asyncio
async def test_async_executor_simple():
    """Test async command execution."""
    executor = AsyncCommandExecutor()

    result = await executor.execute("echo 'hello world'")

    assert result.success
    assert result.exit_code == 0
    assert "hello world" in result.stdout


@pytest.mark.asyncio
async def test_async_executor_with_streaming():
    """Test async executor with streaming callback."""
    executor = AsyncCommandExecutor()

    chunks = []
    def callback(chunk: OutputChunk):
        chunks.append(chunk)

    result = await executor.execute(
        "echo 'line 1'; echo 'line 2'",
        stream_callback=callback
    )

    assert result.success
    assert len(chunks) > 0


@pytest.mark.asyncio
async def test_async_executor_parallel():
    """Test parallel execution."""
    executor = AsyncCommandExecutor()

    commands = [
        "echo 'cmd1'",
        "echo 'cmd2'",
        "echo 'cmd3'",
    ]

    results = await executor.execute_parallel(commands, max_concurrent=2)

    assert len(results) == 3
    assert all(r.success for r in results)


@pytest.mark.asyncio
async def test_async_executor_timeout():
    """Test execution timeout."""
    executor = AsyncCommandExecutor()

    result = await executor.execute(
        "sleep 5",
        timeout=0.5
    )

    assert not result.success
    assert result.exit_code != 0


@pytest.mark.asyncio
async def test_reactive_renderer():
    """Test reactive renderer."""
    renderer = ReactiveRenderer()

    await renderer.start()

    # Emit events
    await renderer.emit(RenderEvent(
        event_type=RenderEventType.OUTPUT,
        content="test output\n",
        metadata={}
    ))

    await renderer.emit(RenderEvent(
        event_type=RenderEventType.COMPLETE,
        content="Task completed",
        metadata={}
    ))

    # Give time to process
    await asyncio.sleep(0.2)

    await renderer.stop()

    # Check buffer
    buffer = renderer.get_output_buffer()
    assert len(buffer) > 0


@pytest.mark.asyncio
async def test_executor_error_handling():
    """Test error handling."""
    executor = AsyncCommandExecutor()

    result = await executor.execute("nonexistent_command_xyz")

    assert not result.success
    assert result.exit_code != 0


@pytest.mark.asyncio
async def test_executor_stderr():
    """Test stderr capture."""
    executor = AsyncCommandExecutor()

    result = await executor.execute("echo 'error' >&2")

    assert result.success  # exit 0
    assert "error" in result.stderr


@pytest.mark.asyncio
async def test_stream_processor_callbacks():
    """Test stream processor callbacks."""
    processor = StreamProcessor()

    received = []
    def callback(chunk: OutputChunk):
        received.append(chunk.content)

    processor.add_callback(callback)

    await processor.feed("test\n", StreamType.STDOUT)
    await processor.close()

    assert len(received) == 1
    assert received[0] == "test\n"
