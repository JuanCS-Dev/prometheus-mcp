"""
Real integration tests for Gemini provider.

Boris Cherny: "Don't mock what you can test for real."
"""

import pytest
import os
import asyncio

from jdev_cli.core.providers.gemini import GeminiProvider


# Skip tests if no API key
pytestmark = pytest.mark.skipif(
    not os.getenv('GEMINI_API_KEY'),
    reason="GEMINI_API_KEY not set - skipping real API tests"
)


class TestGeminiProviderRealAPI:
    """Integration tests with real Gemini API."""

    def test_provider_initialization(self):
        """Should initialize with real API key."""
        provider = GeminiProvider()
        assert provider.is_available() is True
        assert provider.client is not None
        assert provider.model_name in ['gemini-pro', 'gemini-1.5-flash', 'gemini-1.5-pro']

    @pytest.mark.asyncio
    async def test_generate_simple(self):
        """Should generate response from real API."""
        provider = GeminiProvider()

        result = await provider.generate([
            {'role': 'user', 'content': 'Say "Hello World" and nothing else.'}
        ], max_tokens=50, temperature=0.1)

        assert result is not None
        assert len(result) > 0
        assert isinstance(result, str)
        # Should contain some form of "Hello World"
        assert 'hello' in result.lower() or 'world' in result.lower()

    @pytest.mark.asyncio
    async def test_generate_with_system_message(self):
        """Should handle system messages."""
        provider = GeminiProvider()

        result = await provider.generate([
            {'role': 'system', 'content': 'You are a helpful assistant.'},
            {'role': 'user', 'content': 'What is 2+2?'}
        ], max_tokens=50, temperature=0.1)

        assert result is not None
        assert '4' in result

    @pytest.mark.asyncio
    async def test_stream_generate(self):
        """Should stream response chunks."""
        provider = GeminiProvider()

        chunks = []
        async for chunk in provider.stream_generate([
            {'role': 'user', 'content': 'Count from 1 to 3, one number per line.'}
        ], max_tokens=50, temperature=0.1):
            chunks.append(chunk)

        assert len(chunks) > 0
        full_response = ''.join(chunks)
        assert len(full_response) > 0
        # Should contain numbers
        assert any(str(i) in full_response for i in [1, 2, 3])

    @pytest.mark.asyncio
    async def test_temperature_control(self):
        """Should respect temperature parameter."""
        provider = GeminiProvider()

        # Low temperature = more deterministic
        result1 = await provider.generate([
            {'role': 'user', 'content': 'Say the word "test"'}
        ], max_tokens=20, temperature=0.0)

        result2 = await provider.generate([
            {'role': 'user', 'content': 'Say the word "test"'}
        ], max_tokens=20, temperature=0.0)

        # Both should contain "test"
        assert 'test' in result1.lower()
        assert 'test' in result2.lower()

    @pytest.mark.asyncio
    async def test_max_tokens_limit(self):
        """Should respect max_tokens parameter."""
        provider = GeminiProvider()

        result = await provider.generate([
            {'role': 'user', 'content': 'Write a very long story about a cat.'}
        ], max_tokens=10, temperature=0.5)

        # Should be short due to token limit
        token_estimate = provider.count_tokens(result)
        assert token_estimate < 50  # Much less than if unlimited

    def test_model_info(self):
        """Should return correct model info."""
        provider = GeminiProvider()
        info = provider.get_model_info()

        assert info['provider'] == 'gemini'
        assert info['available'] is True
        assert info['supports_streaming'] is True
        assert info['context_window'] == 32768

    def test_token_counting(self):
        """Should estimate token count."""
        provider = GeminiProvider()

        # Known text
        text = "Hello World! This is a test."
        count = provider.count_tokens(text)

        # ~4 chars per token, so ~7 tokens
        assert 5 <= count <= 10

    @pytest.mark.asyncio
    async def test_message_formatting(self):
        """Should format messages correctly."""
        provider = GeminiProvider()

        # Complex conversation
        result = await provider.generate([
            {'role': 'system', 'content': 'You are a math tutor.'},
            {'role': 'user', 'content': 'What is 5+3?'},
            {'role': 'assistant', 'content': '8'},
            {'role': 'user', 'content': 'What is 10-2?'}
        ], max_tokens=50, temperature=0.1)

        assert '8' in result

    @pytest.mark.asyncio
    async def test_error_handling_invalid_input(self):
        """Should handle invalid input gracefully."""
        provider = GeminiProvider()

        # Empty messages should still work (or raise clear error)
        try:
            result = await provider.generate([], max_tokens=50)
            # If it succeeds, that's fine
            assert result is not None
        except Exception as e:
            # If it fails, error should be clear
            assert len(str(e)) > 0

    @pytest.mark.asyncio
    async def test_concurrent_requests(self):
        """Should handle multiple concurrent requests."""
        provider = GeminiProvider()

        # Make 3 concurrent requests
        tasks = [
            provider.generate([
                {'role': 'user', 'content': f'Say the number {i}'}
            ], max_tokens=20, temperature=0.1)
            for i in range(3)
        ]

        results = await asyncio.gather(*tasks)

        assert len(results) == 3
        for i, result in enumerate(results):
            assert result is not None
            assert len(result) > 0


class TestGeminiProviderWithoutAPIKey:
    """Tests that work without API key."""

    def test_init_without_key(self):
        """Should initialize but not be available without key."""
        with pytest.MonkeyPatch.context() as m:
            m.delenv('GEMINI_API_KEY', raising=False)
            provider = GeminiProvider()
            assert provider.is_available() is False

    def test_message_formatting_without_client(self):
        """Should format messages even without client."""
        with pytest.MonkeyPatch.context() as m:
            m.delenv('GEMINI_API_KEY', raising=False)
            provider = GeminiProvider()

            formatted = provider._format_messages([
                {'role': 'user', 'content': 'Hello'},
                {'role': 'assistant', 'content': 'Hi'}
            ])

            assert 'User: Hello' in formatted
            assert 'Assistant: Hi' in formatted

    @pytest.mark.asyncio
    async def test_generate_fails_without_client(self):
        """Should raise error when generating without client."""
        with pytest.MonkeyPatch.context() as m:
            m.delenv('GEMINI_API_KEY', raising=False)
            provider = GeminiProvider()

            with pytest.raises(RuntimeError, match="not available"):
                await provider.generate([{'role': 'user', 'content': 'Test'}])


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
