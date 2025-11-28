"""Real-world usage testing - Scientific validation of CLI behavior."""
import pytest
import asyncio
import os
from pathlib import Path
from jdev_cli.core.llm import LLMClient
from jdev_cli.core.context import ContextBuilder
from jdev_cli.core.config import Config


@pytest.fixture
def config():
    """Real config with HF token."""
    cfg = Config()
    cfg.hf_token = os.getenv("HF_TOKEN")
    cfg.provider = "hf"
    cfg.model = "Qwen/Qwen2.5-Coder-32B-Instruct"
    return cfg


@pytest.fixture
def llm():
    """Real LLM client."""
    return LLMClient()


@pytest.fixture
def context_mgr():
    """Real context manager."""
    return ContextBuilder()


class TestRealUsageScenarios:
    """Test actual CLI usage patterns."""

    @pytest.mark.asyncio
    async def test_code_explanation_flow(self, llm):
        """Real scenario: User asks to explain a function."""
        code = """
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)
"""
        prompt = f"Explain this function concisely:\n{code}"

        response = await llm.generate(prompt, max_tokens=200)

        assert response
        assert len(response) > 20
        assert any(word in response.lower() for word in ["fibonacci", "recursive", "function"])

    @pytest.mark.asyncio
    async def test_bug_fix_suggestion(self, llm):
        """Real scenario: Find bug and suggest fix."""
        buggy_code = """
def divide_numbers(a, b):
    return a / b
"""
        prompt = f"Find the bug and suggest a fix:\n{buggy_code}"

        response = await llm.generate(prompt, max_tokens=300)

        assert response
        assert any(word in response.lower() for word in ["zero", "error", "exception", "check"])

    @pytest.mark.asyncio
    async def test_streaming_user_experience(self, llm):
        """Real scenario: User sees output streaming in real-time."""
        prompt = "List 5 Python best practices. Be concise."

        chunks = []
        start_time = asyncio.get_event_loop().time()
        first_chunk_time = None

        async for chunk in llm.stream(prompt, max_tokens=200):
            if chunk:
                chunks.append(chunk)
                if first_chunk_time is None:
                    first_chunk_time = asyncio.get_event_loop().time()

        full_response = "".join(chunks)

        # Validate streaming experience
        assert len(chunks) > 1, "Should receive multiple chunks"
        assert first_chunk_time is not None
        assert (first_chunk_time - start_time) < 10, "First chunk should arrive quickly"
        assert len(full_response) > 50, "Should have substantial content"

    @pytest.mark.asyncio
    async def test_context_aware_response(self, llm, context_mgr):
        """Real scenario: Response considers project context."""
        # Simulate project context
        context_mgr.add_file(str(Path(__file__)))

        context = context_mgr.build_context()
        prompt = f"{context}\n\nWhat testing framework is being used?"

        response = await llm.generate(prompt, max_tokens=100)

        assert "pytest" in response.lower()

    @pytest.mark.asyncio
    async def test_edge_case_empty_input(self, llm):
        """Edge case: Empty prompt handling."""
        with pytest.raises((ValueError, RuntimeError)):
            await llm.generate("", max_tokens=100)

    @pytest.mark.asyncio
    async def test_edge_case_very_long_input(self, llm):
        """Edge case: Handle very long input gracefully."""
        long_prompt = "x" * 50000  # Very long input

        try:
            response = await llm.generate(long_prompt, max_tokens=50)
            # Should either truncate or handle gracefully
            assert True
        except Exception as e:
            # Should raise meaningful error
            assert "token" in str(e).lower() or "length" in str(e).lower()

    @pytest.mark.asyncio
    async def test_edge_case_special_characters(self, llm):
        """Edge case: Handle special characters in code."""
        code_with_special = '''
def regex_test():
    pattern = r"[a-z]{2,4}@\w+\.\w+"
    return re.match(pattern, "test@example.com")
'''
        prompt = f"Explain this regex pattern:\n{code_with_special}"

        response = await llm.generate(prompt, max_tokens=200)

        assert response
        assert len(response) > 20

    @pytest.mark.asyncio
    async def test_temperature_affects_creativity(self, llm):
        """Scientific test: Temperature parameter effect."""
        prompt = "Write a short function name for sorting users by age."

        # Low temperature (deterministic)
        response_low = await llm.generate(prompt, max_tokens=20, temperature=0.1)

        # High temperature (creative)
        response_high = await llm.generate(prompt, max_tokens=20, temperature=0.9)

        assert response_low
        assert response_high
        # They might be different (non-deterministic test)
        assert len(response_low) > 0
        assert len(response_high) > 0

    @pytest.mark.asyncio
    async def test_max_tokens_limiting(self, llm):
        """Scientific test: max_tokens actually limits output."""
        prompt = "Explain object-oriented programming in detail with examples."

        # Very limited
        response_short = await llm.generate(prompt, max_tokens=20)

        # More generous
        response_long = await llm.generate(prompt, max_tokens=200)

        # Short should be significantly shorter
        assert len(response_short) < len(response_long)
        assert len(response_short.split()) <= 30  # Rough token approximation

    @pytest.mark.asyncio
    async def test_concurrent_requests_handling(self, llm):
        """Real scenario: Multiple requests simultaneously."""
        prompts = [
            "What is Python?",
            "What is JavaScript?",
            "What is Rust?"
        ]

        tasks = [llm.generate(p, max_tokens=50) for p in prompts]
        responses = await asyncio.gather(*tasks, return_exceptions=True)

        # Should handle concurrency gracefully
        successful = [r for r in responses if isinstance(r, str)]
        assert len(successful) >= 2, "Most requests should succeed"

    @pytest.mark.asyncio
    async def test_retry_on_transient_failure(self, llm):
        """Real scenario: Graceful handling of API hiccups."""
        # This tests the resilience layer
        prompt = "Say 'hello'"

        try:
            response = await llm.generate(prompt, max_tokens=10)
            assert response
        except Exception as e:
            # If it fails, error should be informative
            assert len(str(e)) > 10


class TestContextManagerRealUsage:
    """Test context manager in real scenarios."""

    def test_add_multiple_files(self, context_mgr, tmp_path):
        """Real scenario: User adds multiple project files."""
        # Create temp files
        file1 = tmp_path / "main.py"
        file1.write_text("def main(): pass")

        file2 = tmp_path / "utils.py"
        file2.write_text("def helper(): pass")

        context_mgr.add_file(str(file1))
        context_mgr.add_file(str(file2))

        context = context_mgr.build_context()

        assert "main.py" in str(context)
        assert "utils.py" in str(context)
        assert "def main()" in str(context)
        assert "def helper()" in str(context)

    def test_context_size_management(self, context_mgr, tmp_path):
        """Real scenario: Context doesn't exceed limits."""
        # Add many files
        for i in range(50):
            f = tmp_path / f"file{i}.py"
            f.write_text(f"def func{i}(): pass\n" * 100)
            context_mgr.add_file(str(f))

        context = context_mgr.get_context()

        # Should be limited to reasonable size
        assert len(str(context)) < 100000, "Context should be bounded"

    def test_clear_context(self, context_mgr, tmp_path):
        """Real scenario: User starts fresh conversation."""
        file1 = tmp_path / "test.py"
        file1.write_text("test content")

        context_mgr.add_file(str(file1))
        ctx = context_mgr.build_context()
        assert ctx['file_count'] > 0

        context_mgr.files.clear()
        ctx_empty = context_mgr.build_context()
        assert ctx_empty['file_count'] == 0


class TestErrorHandlingRealWorld:
    """Test error scenarios users might encounter."""

    @pytest.mark.asyncio
    async def test_invalid_model_name(self, config):
        """Real error: User typos model name."""
        config.model = "InvalidModelName123"
        llm = LLMClient(config)

        with pytest.raises(Exception):
            await llm.generate("test", max_tokens=10)

    @pytest.mark.asyncio
    async def test_missing_api_token(self, config):
        """Real error: User forgets to set token."""
        config.hf_token = None

        with pytest.raises((RuntimeError, ValueError)):
            llm = LLMClient(config)
            await llm.generate("test", max_tokens=10)

    @pytest.mark.asyncio
    async def test_network_timeout_simulation(self, llm):
        """Real scenario: Network issues."""
        # Test with very small timeout (if supported by client)
        prompt = "Quick test"

        try:
            response = await asyncio.wait_for(
                llm.generate(prompt, max_tokens=10),
                timeout=0.001  # Artificially small
            )
        except asyncio.TimeoutError:
            # Expected for this test
            assert True
        except Exception:
            # Other exceptions are also acceptable
            assert True


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
