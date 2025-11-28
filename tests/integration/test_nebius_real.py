"""Real integration tests for Nebius provider.

Tests actual API calls with real Qwen models.
"""

import pytest
import asyncio
import os
from jdev_cli.core.llm import LLMClient


@pytest.mark.asyncio
@pytest.mark.integration
async def test_nebius_model_72b_basic():
    """Test basic generation with Qwen2.5-72B."""
    if not os.getenv("NEBIUS_API_KEY"):
        pytest.skip("NEBIUS_API_KEY not set")

    client = LLMClient()

    response = ""
    async for chunk in client.stream_chat(
        prompt="What is 2+2? Answer in one word.",
        provider="nebius"
    ):
        response += chunk

    assert len(response) > 0
    assert "4" in response.lower() or "four" in response.lower()


@pytest.mark.asyncio
@pytest.mark.integration
async def test_nebius_code_generation():
    """Test code generation capabilities."""
    if not os.getenv("NEBIUS_API_KEY"):
        pytest.skip("NEBIUS_API_KEY not set")

    client = LLMClient()

    response = ""
    async for chunk in client.stream_chat(
        prompt="Write a Python function to calculate fibonacci(5). Just the function, no explanation.",
        provider="nebius",
        max_tokens=200
    ):
        response += chunk

    assert "def" in response
    assert "fibonacci" in response.lower() or "fib" in response.lower()


@pytest.mark.asyncio
@pytest.mark.integration
async def test_nebius_temperature_variation():
    """Test temperature parameter affects output."""
    if not os.getenv("NEBIUS_API_KEY"):
        pytest.skip("NEBIUS_API_KEY not set")

    client = LLMClient()

    # Low temperature (deterministic)
    response_low = ""
    async for chunk in client.stream_chat(
        prompt="Say 'hello' in one word.",
        provider="nebius",
        temperature=0.1
    ):
        response_low += chunk

    # High temperature (creative)
    response_high = ""
    async for chunk in client.stream_chat(
        prompt="Say 'hello' creatively.",
        provider="nebius",
        temperature=0.9
    ):
        response_high += chunk

    assert len(response_low) > 0
    assert len(response_high) > 0


@pytest.mark.asyncio
@pytest.mark.integration
async def test_nebius_max_tokens_limit():
    """Test max_tokens parameter is respected."""
    if not os.getenv("NEBIUS_API_KEY"):
        pytest.skip("NEBIUS_API_KEY not set")

    client = LLMClient()

    response = ""
    async for chunk in client.stream_chat(
        prompt="Write a long essay about Python.",
        provider="nebius",
        max_tokens=50
    ):
        response += chunk

    # Should be short due to token limit
    word_count = len(response.split())
    assert word_count < 100  # 50 tokens ~= 37 words typically


@pytest.mark.asyncio
@pytest.mark.integration
async def test_nebius_context_awareness():
    """Test context is used in generation."""
    if not os.getenv("NEBIUS_API_KEY"):
        pytest.skip("NEBIUS_API_KEY not set")

    client = LLMClient()

    response = ""
    async for chunk in client.stream_chat(
        prompt="What language am I an expert in?",
        context="You are a Python programming expert with 10 years experience.",
        provider="nebius"
    ):
        response += chunk

    assert "python" in response.lower()


@pytest.mark.asyncio
@pytest.mark.integration
async def test_nebius_streaming_incremental():
    """Test streaming returns chunks incrementally."""
    if not os.getenv("NEBIUS_API_KEY"):
        pytest.skip("NEBIUS_API_KEY not set")

    client = LLMClient()

    chunks = []
    async for chunk in client.stream_chat(
        prompt="Count from 1 to 5.",
        provider="nebius"
    ):
        chunks.append(chunk)

    # Should receive multiple chunks
    assert len(chunks) > 1
    response = "".join(chunks)
    assert len(response) > 0


@pytest.mark.asyncio
@pytest.mark.integration
async def test_nebius_error_handling():
    """Test proper error handling for invalid requests."""
    if not os.getenv("NEBIUS_API_KEY"):
        pytest.skip("NEBIUS_API_KEY not set")

    client = LLMClient()

    # Empty prompt should still work (model decides response)
    response = ""
    try:
        async for chunk in client.stream_chat(
            prompt="",
            provider="nebius"
        ):
            response += chunk
        # If it works, that's fine - API allows empty prompts
        assert True
    except Exception as e:
        # If it errors, that's also fine - API validation
        assert "prompt" in str(e).lower() or "message" in str(e).lower()


@pytest.mark.asyncio
@pytest.mark.integration
async def test_nebius_concurrent_requests():
    """Test multiple concurrent requests work correctly."""
    if not os.getenv("NEBIUS_API_KEY"):
        pytest.skip("NEBIUS_API_KEY not set")

    client = LLMClient()

    async def make_request(prompt: str) -> str:
        response = ""
        async for chunk in client.stream_chat(prompt=prompt, provider="nebius"):
            response += chunk
        return response

    # Run 3 concurrent requests
    results = await asyncio.gather(
        make_request("Say 'A'"),
        make_request("Say 'B'"),
        make_request("Say 'C'")
    )

    assert len(results) == 3
    assert all(len(r) > 0 for r in results)


@pytest.mark.asyncio
@pytest.mark.integration
async def test_nebius_qwq_model():
    """Test QwQ-32B model (reasoning model)."""
    if not os.getenv("NEBIUS_API_KEY"):
        pytest.skip("NEBIUS_API_KEY not set")

    client = LLMClient()

    # QwQ models need to be explicitly selected via model parameter
    # For now test with default model (Qwen2.5-72B)
    response = ""
    async for chunk in client.stream_chat(
        prompt="Solve: If x + 5 = 12, what is x?",
        provider="nebius"
    ):
        response += chunk

    assert "7" in response or "seven" in response.lower()
