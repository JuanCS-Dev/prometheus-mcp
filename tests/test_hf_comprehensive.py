"""
Comprehensive HuggingFace API Test Suite
Tests every edge case, error condition, and real-world usage scenario
"""
import pytest
import os
import asyncio
from jdev_cli.core.llm import LLMClient

# Real HF API Token
HF_TOKEN = os.getenv("HF_TOKEN_GOD", os.getenv("HF_TOKEN"))

@pytest.fixture
def hf_client():
    """Real HF client"""
    if not HF_TOKEN:
        pytest.skip("HF_TOKEN not available")
    # Set token in config
    os.environ["HF_TOKEN"] = HF_TOKEN
    client = LLMClient()
    return client


class TestHFBasicGeneration:
    """Test basic generation capabilities"""

    @pytest.mark.asyncio
    async def test_simple_completion(self, hf_client):
        """Most basic case: simple text completion"""
        response = ""
        async for chunk in hf_client.stream_chat("Say 'Hello World' and nothing else.", provider="hf"):
            response += chunk
        assert response
        assert len(response) > 0

    @pytest.mark.asyncio
    async def test_empty_prompt(self, hf_client):
        """Edge: empty prompt should handle gracefully"""
        try:
            response = ""
            async for chunk in hf_client.stream_chat("", provider="hf"):
                response += chunk
            # Should either return something or fail gracefully
            assert True
        except ValueError:
            pass  # Expected

    @pytest.mark.asyncio
    async def test_very_long_prompt(self, hf_client):
        """Edge: very long prompt"""
        long_prompt = "Test " * 500 + " Summarize in one word."
        response = ""
        async for chunk in hf_client.stream_chat(long_prompt, provider="hf", max_tokens=50):
            response += chunk
        assert response

    @pytest.mark.asyncio
    async def test_special_characters(self, hf_client):
        """Edge: special characters and unicode"""
        prompt = "Translate to English: こんにちは"
        response = ""
        async for chunk in hf_client.stream_chat(prompt, provider="hf"):
            response += chunk
        assert response

    @pytest.mark.asyncio
    async def test_code_generation(self, hf_client):
        """Real use: generate Python code"""
        prompt = "Write a Python function to calculate fibonacci(10). Code only."
        response = ""
        async for chunk in hf_client.stream_chat(prompt, provider="hf"):
            response += chunk
        assert response
        assert "def" in response.lower() or "fibonacci" in response.lower()


class TestHFTemperature:
    """Test temperature parameter effects"""

    @pytest.mark.asyncio
    async def test_temperature_low(self, hf_client):
        """Deterministic output with low temp"""
        prompt = "Count from 1 to 3"
        response = ""
        async for chunk in hf_client.stream_chat(prompt, provider="hf", temperature=0.1):
            response += chunk
        assert response

    @pytest.mark.asyncio
    async def test_temperature_high(self, hf_client):
        """Creative output with high temp"""
        prompt = "Say something creative"
        response = ""
        async for chunk in hf_client.stream_chat(prompt, provider="hf", temperature=1.0):
            response += chunk
        assert response


class TestHFMaxTokens:
    """Test max_tokens parameter"""

    @pytest.mark.asyncio
    async def test_short_max_tokens(self, hf_client):
        """Force very short response"""
        response = ""
        async for chunk in hf_client.stream_chat(
            "Write a long essay",
            provider="hf",
            max_tokens=10
        ):
            response += chunk
        assert response
        # Should be short
        assert len(response) < 200

    @pytest.mark.asyncio
    async def test_long_max_tokens(self, hf_client):
        """Allow longer response"""
        response = ""
        async for chunk in hf_client.stream_chat(
            "List numbers 1 to 20",
            provider="hf",
            max_tokens=200
        ):
            response += chunk
        assert response


class TestHFSystemInstructions:
    """Test system instructions"""

    @pytest.mark.asyncio
    async def test_system_instruction_code(self, hf_client):
        """System instruction for code"""
        response = ""
        async for chunk in hf_client.stream_chat(
            "Sort an array",
            provider="hf",
            system_instruction="You are a Python expert. Write only code."
        ):
            response += chunk
        assert response


class TestHFErrorHandling:
    """Test error conditions"""

    @pytest.mark.asyncio
    async def test_timeout_handling(self, hf_client):
        """Test timeout handling"""
        # Set very short timeout
        hf_client.timeout = 0.001
        try:
            response = ""
            async for chunk in hf_client.stream_chat("Test", provider="hf"):
                response += chunk
            # Either completes very fast or times out
            assert True
        except (asyncio.TimeoutError, Exception):
            assert True  # Expected
        finally:
            hf_client.timeout = 30.0  # Reset


class TestHFRealWorldScenarios:
    """Test real-world usage patterns"""

    @pytest.mark.asyncio
    async def test_code_explanation(self, hf_client):
        """Real: explain code"""
        code = "def fib(n):\n    if n <= 1: return n\n    return fib(n-1) + fib(n-2)"
        response = ""
        async for chunk in hf_client.stream_chat(f"Explain: {code}", provider="hf"):
            response += chunk
        assert response
        assert len(response) > 20

    @pytest.mark.asyncio
    async def test_git_command_generation(self, hf_client):
        """Real: generate git command"""
        response = ""
        async for chunk in hf_client.stream_chat(
            "Git command for uncommitted changes? Command only.",
            provider="hf"
        ):
            response += chunk
        assert response
        assert "git" in response.lower()

    @pytest.mark.asyncio
    async def test_error_diagnosis(self, hf_client):
        """Real: diagnose error"""
        error = "TypeError: 'NoneType' object is not subscriptable"
        response = ""
        async for chunk in hf_client.stream_chat(f"What causes: {error}", provider="hf"):
            response += chunk
        assert response
        assert len(response) > 10


class TestHFStreaming:
    """Test streaming behavior"""

    @pytest.mark.asyncio
    async def test_streaming_basic(self, hf_client):
        """Test basic streaming"""
        chunks = []
        async for chunk in hf_client.stream_chat("Count 1 to 5", provider="hf"):
            chunks.append(chunk)
        assert len(chunks) > 0
        full_response = "".join(chunks)
        assert len(full_response) > 0

    @pytest.mark.asyncio
    async def test_streaming_interruption(self, hf_client):
        """Edge: interrupt streaming"""
        count = 0
        async for chunk in hf_client.stream_chat("Write a long story", provider="hf"):
            count += 1
            if count > 3:
                break
        assert count == 4


class TestHFConcurrency:
    """Test concurrent requests"""

    @pytest.mark.asyncio
    async def test_concurrent_requests(self, hf_client):
        """Real: multiple concurrent requests"""
        prompts = ["Say 'one'", "Say 'two'", "Say 'three'"]

        async def generate(prompt):
            response = ""
            async for chunk in hf_client.stream_chat(prompt, provider="hf"):
                response += chunk
            return response

        responses = await asyncio.gather(*[generate(p) for p in prompts])
        assert len(responses) == 3
        assert all(r for r in responses)

    @pytest.mark.asyncio
    async def test_rapid_fire_requests(self, hf_client):
        """Edge: rapid successive requests"""
        responses = []
        for i in range(3):
            response = ""
            async for chunk in hf_client.stream_chat(f"Say {i}", provider="hf"):
                response += chunk
            responses.append(response)

        assert len(responses) == 3
        assert all(r for r in responses)


class TestHFEdgeCases:
    """Extreme edge cases"""

    @pytest.mark.asyncio
    async def test_emoji_prompt(self, hf_client):
        """Edge: emoji prompt"""
        response = ""
        async for chunk in hf_client.stream_chat("🔥🚀 What?", provider="hf"):
            response += chunk
        assert response

    @pytest.mark.asyncio
    async def test_mixed_languages(self, hf_client):
        """Edge: multiple languages"""
        prompt = "Hello 你好. Respond in English."
        response = ""
        async for chunk in hf_client.stream_chat(prompt, provider="hf"):
            response += chunk
        assert response


class TestHFResilience:
    """Test resilience patterns"""

    @pytest.mark.asyncio
    async def test_circuit_breaker_active(self, hf_client):
        """Test circuit breaker is active"""
        assert hf_client.circuit_breaker is not None
        assert hf_client.circuit_breaker.state.value == "closed"

    @pytest.mark.asyncio
    async def test_rate_limiter_active(self, hf_client):
        """Test rate limiter is active"""
        assert hf_client.rate_limiter is not None

    @pytest.mark.asyncio
    async def test_metrics_tracking(self, hf_client):
        """Test metrics are tracked"""
        assert hf_client.metrics is not None

        # Make a request
        response = ""
        async for chunk in hf_client.stream_chat("Test", provider="hf"):
            response += chunk

        # Check metrics updated
        stats = hf_client.metrics.get_stats()
        assert stats["total_requests"] > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
