"""Comprehensive Ollama integration tests."""

import pytest
import asyncio
from qwen_dev_cli.core.llm import LLMClient
from qwen_dev_cli.core.config import config

pytestmark = pytest.mark.asyncio


class TestOllamaIntegration:
    """Test Ollama local inference integration."""
    
    @pytest.fixture
    def ollama_client(self):
        """Create Ollama-enabled client."""
        config.ollama_enabled = True
        client = LLMClient()
        return client
    
    async def test_ollama_available(self, ollama_client):
        """Test Ollama is detected and initialized."""
        assert ollama_client.ollama_client is not None
        valid, msg = ollama_client.validate()
        assert valid
        assert "Ollama" in msg
    
    async def test_ollama_streaming(self, ollama_client):
        """Test streaming with Ollama."""
        chunks = []
        async for chunk in ollama_client.stream_chat(
            prompt="Say 'test' and nothing else",
            provider="ollama"
        ):
            chunks.append(chunk)
        
        result = "".join(chunks).strip().lower()
        assert len(result) > 0
        assert "test" in result
    
    async def test_ollama_with_temperature(self, ollama_client):
        """Test temperature parameter."""
        result1 = await ollama_client.generate(
            "Say hello in 3 words",
            temperature=0.1,
            provider="ollama",
            max_tokens=20
        )
        
        assert len(result1) > 0
    
    async def test_ollama_with_context(self, ollama_client):
        """Test context injection."""
        context = "You are a pirate. Always say 'Arrr' in your responses."
        result = await ollama_client.generate(
            "Say hello",
            context=context,
            provider="ollama",
            max_tokens=50
        )
        
        assert len(result) > 0
    
    async def test_ollama_code_generation(self, ollama_client):
        """Test code generation with Qwen2.5-coder."""
        result = await ollama_client.generate(
            "Write a Python function that adds two numbers. Just the code, no explanation.",
            provider="ollama",
            max_tokens=200
        )
        
        assert "def" in result
        assert "return" in result or "+" in result
    
    async def test_ollama_failover_to_hf(self, ollama_client):
        """Test failover from Ollama to HF."""
    async def test_ollama_failover_to_hf(self, ollama_client):
        """Test failover from Ollama to HF."""
        original_model = config.ollama_model
        config.ollama_model = "nonexistent-model"
        
        # Failover happens automatically in stream_chat
        result = await ollama_client.generate(
            "Say test",
            provider="auto",
            max_tokens=20
        )
        
        assert len(result) > 0
        config.ollama_model = original_model
            
            max_tokens=20
        )
        
        assert len(result) > 0
        config.ollama_model = original_model


class TestOllamaPerformance:
    """Performance tests for Ollama."""
    
    @pytest.fixture
    def ollama_client(self):
        config.ollama_enabled = True
        return LLMClient()
    
    async def test_ollama_latency(self, ollama_client):
        """Measure Ollama response latency."""
        import time
        
        start = time.time()
        await ollama_client.generate(
            "Say hi",
            provider="ollama",
            max_tokens=10
        )
        latency = time.time() - start
        
        assert latency < 10.0
    
    async def test_ollama_streaming_latency(self, ollama_client):
        """Test first token latency in streaming."""
        import time
        
        start = time.time()
        first_token_time = None
        
        async for chunk in ollama_client.stream_chat(
            "Say hello",
            provider="ollama",
            max_tokens=20
        ):
            if first_token_time is None:
                first_token_time = time.time() - start
            if first_token_time:
                break
        
        assert first_token_time is not None
        assert first_token_time < 10.0


class TestOllamaHFComparison:
    """Compare Ollama vs HF behavior."""
    
    @pytest.fixture
    def client(self):
        config.ollama_enabled = True
        return LLMClient()
    
    async def test_both_providers_work(self, client):
        """Verify both providers can handle same task."""
        prompt = "Say 'test response' in 3 words"
        
        ollama_result = await client.generate(prompt, provider="ollama", max_tokens=20)
        hf_result = await client.generate(prompt, provider="hf", max_tokens=20)
        
        assert len(ollama_result) > 0
        assert len(hf_result) > 0
    
    async def test_auto_provider_selection(self, client):
        """Test auto provider selection logic."""
        result = await client.generate(
            "Say hi",
            provider="auto",
            max_tokens=20
        )
        
        assert len(result) > 0
        
        if client.metrics:
            stats = client.metrics.get_stats()
            assert stats["total_requests"] >= 1
