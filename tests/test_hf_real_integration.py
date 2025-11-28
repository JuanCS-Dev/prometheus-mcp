"""Real-world integration tests using HuggingFace API - PRODUCTION VALIDATION"""
import pytest
import os
from jdev_cli.core.llm import LLMClient
from jdev_cli.core.context import ContextBuilder

class TestHFRealIntegration:
    """Test real LLM behavior with actual API calls"""

    @pytest.fixture
    def client(self):
        token = os.getenv("HF_TOKEN")
        if not token:
            pytest.skip("HF_TOKEN not available")
        return LLMClient()
    @pytest.fixture
    def client(self):
        token = os.getenv("HF_TOKEN")
        if not token:
            pytest.skip("HF_TOKEN not available")
        return LLMClient()
    @pytest.fixture
    def client(self):
        token = os.getenv("HF_TOKEN")
        if not token:
            pytest.skip("HF_TOKEN not available")
        return LLMClient()
    @pytest.fixture
    def client(self):
        token = os.getenv("HF_TOKEN")
        if not token:
            pytest.skip("HF_TOKEN not available")
        return LLMClient()
    @pytest.fixture
    def client(self):
        token = os.getenv("HF_TOKEN")
        if not token:
            pytest.skip("HF_TOKEN not available")
        return LLMClient()
    @pytest.fixture
    def client(self):
        token = os.getenv("HF_TOKEN")
        if not token:
            pytest.skip("HF_TOKEN not available")
        return LLMClient()
    @pytest.fixture
    def client(self):
        token = os.getenv("HF_TOKEN")
        if not token:
            pytest.skip("HF_TOKEN not available")
        return LLMClient()
    @pytest.fixture
    def client(self):
        token = os.getenv("HF_TOKEN")
        if not token:
            pytest.skip("HF_TOKEN not available")
        return LLMClient()
    @pytest.fixture
    def client(self):
        token = os.getenv("HF_TOKEN")
        if not token:
            pytest.skip("HF_TOKEN not available")
        return LLMClient()

    @pytest.fixture
    def context_manager(self):
        return ContextBuilder()


    async def test_code_generation_quality(self, client):
        """Test if LLM generates syntactically correct code"""
        response = await client.generate(
            "Write a Python function to calculate fibonacci sequence",
            max_tokens=200,
            provider="hf"
        )

        # Extract code from markdown if present
        import re
        code_match = re.search(r'```python\n(.+?)```', response, re.DOTALL)
        if code_match:
            code = code_match.group(1)
        else:
            code = response

        assert "def" in code
        try:
            compile(code, '<string>', 'exec')
        except SyntaxError as e:
            pytest.fail(f"Invalid Python: {e}")

    async def test_context_retention(self, client, context_manager):
        """Test if context manager properly feeds conversation history"""
        context_manager.add_message("user", "My name is Boris")
        context_manager.add_message("assistant", "Hello Boris!")
        context_manager.add_message("user", "What is my name?")

        messages = context_manager.get_messages()
        response = client.generate_with_context(messages, max_tokens=50)

        assert "boris" in response.lower()

    async def test_streaming_real_tokens(self, client):
        """Test streaming returns actual tokens progressively"""
        tokens_received = []

        for chunk in client.stream("Explain async/await in Python", max_tokens=100):
            tokens_received.append(chunk)
            assert isinstance(chunk, str)
            assert len(chunk) > 0

        assert len(tokens_received) > 5, "Should receive multiple chunks"
        full_response = "".join(tokens_received)
        assert "async" in full_response.lower()

    async def test_error_handling_invalid_model(self):
        """Test graceful handling of invalid model"""
        with pytest.raises(Exception):
            client = LLMClient(
                model="invalid/model/name",
                api_key=os.getenv("HF_TOKEN")
            )
            client.generate("test")

    async def test_token_limit_respect(self, client):
        """Test if LLM respects max_tokens parameter"""
        response = await client.generate("Write a very long essay about Python", max_tokens=50, provider="hf"
        )

        # Response should be truncated, not thousands of tokens
        word_count = len(response.split())
        assert word_count < 100, f"Expected ~50 tokens, got {word_count} words"

    async def test_instruction_following(self, client):
        """Test if LLM follows specific formatting instructions"""
        response = await client.generate("List 3 Python frameworks. Format: 1. Name - Description", max_tokens=150, provider="hf"
        )

        assert "1." in response
        assert "-" in response or ":" in response
        lines = [l for l in response.split("\n") if l.strip()]
        assert len(lines) >= 3, "Should list at least 3 items"

    async def test_code_explanation_accuracy(self, client):
        """Test if LLM correctly explains code behavior"""
        code = """
def factorial(n):
    return 1 if n <= 1 else n * factorial(n-1)
"""
        response = await client.generate(
            f"Explain what this code does:\n{code}",
            max_tokens=100
        )

        assert "factorial" in response.lower()
        assert "recursive" in response.lower() or "recursion" in response.lower()

    async def test_multi_turn_consistency(self, client, context_manager):
        """Test consistency across multiple conversation turns"""
        context_manager.add_message("user", "I'm building a REST API")
        context_manager.add_message("assistant", "Great! What framework?")
        context_manager.add_message("user", "FastAPI")
        context_manager.add_message("assistant", "Excellent choice!")
        context_manager.add_message("user", "What framework am I using?")

        messages = context_manager.get_messages()
        response = client.generate_with_context(messages, max_tokens=30)

        assert "fastapi" in response.lower()

    async def test_temperature_effect(self, client):
        """Test if temperature parameter affects output diversity"""
        prompt = "Say hello"

        # Low temp - deterministic
        responses_low = [
            client.generate(prompt, temperature=0.1, max_tokens=20)
            for _ in range(3)
        ]

        # High temp - creative
        responses_high = [
            client.generate(prompt, temperature=1.5, max_tokens=20)
            for _ in range(3)
        ]

        # Low temp should be more consistent
        assert len(set(responses_low)) <= len(set(responses_high))

    async def test_system_prompt_effectiveness(self, client):
        """Test if system prompts properly guide behavior"""
        system_prompt = "You are a Python expert. Always include code examples."

        response = await client.generate(
            "Explain list comprehension",
            system_prompt=system_prompt,
            max_tokens=150
        )

        # Should contain code
        assert "[" in response and "]" in response
        assert "for" in response

    @pytest.mark.slow
    async def test_long_context_handling(self, client, context_manager):
        """Test handling of long conversation contexts"""
        # Simulate long conversation
        for i in range(20):
            context_manager.add_message("user", f"Question {i}")
            context_manager.add_message("assistant", f"Answer {i}")

        context_manager.add_message("user", "Summarize our conversation")
        messages = context_manager.get_messages()

        response = client.generate_with_context(messages, max_tokens=100)
        assert response, "Should handle long context without crashing"

    async def test_special_characters_handling(self, client):
        """Test handling of code with special characters"""
        code_with_special = r'''
def regex_test():
    pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
    return pattern
'''
        response = await client.generate(
            f"What does this regex match?\n{code_with_special}",
            max_tokens=50
        )

        assert "email" in response.lower() or "@" in response
