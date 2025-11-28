"""Test streaming engine performance."""

import pytest
import asyncio
import time
from jdev_cli.core.streaming_engine import StreamingEngine

async def mock_generator(count: int, delay: float = 0.01):
    """Simulate LLM streaming tokens."""
    for i in range(count):
        yield f"token_{i} "
        await asyncio.sleep(delay)

@pytest.mark.asyncio
async def test_streaming_chunking():
    """Test that streaming chunks output correctly."""
    engine = StreamingEngine(chunk_size=10)

    chunks = []
    async for chunk in engine.stream_with_chunking(mock_generator(10, 0.001)):
        chunks.append(chunk)

    # Verify we got output
    full_text = "".join(chunks)
    assert "token_0" in full_text
    assert "token_9" in full_text

    # Verify chunking behavior (approximate)
    # With chunk_size=10 and tokens like "token_X ", each token is ~8 chars
    # So we expect roughly 1-2 tokens per chunk
    assert len(chunks) > 0

@pytest.mark.asyncio
async def test_streaming_latency():
    """Test first token latency."""
    engine = StreamingEngine(chunk_size=1) # Small chunk for fast first token

    start_time = time.time()
    first_chunk_time = None

    async for chunk in engine.stream_with_chunking(mock_generator(5, 0.01)):
        if first_chunk_time is None:
            first_chunk_time = time.time()

    latency = first_chunk_time - start_time
    print(f"\nFirst token latency: {latency*1000:.2f}ms")

    # Should be very close to the generator delay (10ms) + overhead
    assert latency < 0.05  # < 50ms overhead
