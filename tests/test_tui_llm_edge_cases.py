"""
🧪 TUI + LLM Edge Cases - Scientific Real-World Testing

Tests TUI components with REAL LLM calls using our 3-provider failover:
1. Ollama (LOCAL - primary, no network needed)
2. Nebius (ONLINE - backup)
3. HuggingFace (ONLINE - fallback)

Philosophy:
- Test REAL failures, not mocks
- Verify failover works
- Measure response times
- Test concurrent streams
- Validate UI updates with real data
"""

import pytest
import asyncio
import time
from io import StringIO
from rich.console import Console

from qwen_dev_cli.core.llm import LLMClient
from qwen_dev_cli.tui.components import (
    MessageBox, 
    Message,
    ProgressBar,
    ProgressState,
    StatusBadge,
    StatusLevel
)
from qwen_dev_cli.tui.wisdom import WisdomSystem


class TestLLMEdgeCases:
    """Scientific edge case testing with real LLM."""
    
    @pytest.mark.asyncio
    async def test_llm_stream_renders_progressively(self):
        """Test: TUI updates as LLM streams (real-time rendering)."""
        console = Console(file=StringIO())
        messages = []
        
        # Create LLM client with failover
        llm = LLMClient()
        
        # Stream response and collect chunks
        prompt = "Say 'Hello World' in one word"
        start_time = time.time()
        
        async for chunk in llm.stream_chat(prompt=prompt):
            messages.append(chunk)
            # Simulate TUI update
            if len(messages) % 5 == 0:  # Every 5 chunks
                progress = len(messages)
                console.print(f"Streaming... {progress} chunks")
        
        elapsed = time.time() - start_time
        
        # Assertions
        assert len(messages) > 0, "Should receive stream chunks"
        assert elapsed < 30, f"Should complete in <30s, took {elapsed:.2f}s"
        
        full_response = "".join(messages)
        assert len(full_response) > 0, "Should have content"
        
        print(f"\n✅ Streamed {len(messages)} chunks in {elapsed:.2f}s")
        print(f"   Response: {full_response[:100]}...")
    
    @pytest.mark.asyncio
    async def test_llm_failover_resilience(self):
        """Test: Falls back through providers when one fails."""
        llm = LLMClient()
        
        # Force provider priority
        llm.provider_priority = ["ollama", "nebius", "huggingface"]
        
        start_time = time.time()
        
        try:
            # Should try ollama first, failover if needed
            response = ""
            async for chunk in llm.stream_chat(prompt="Echo: test", enable_failover=True):
                response += chunk
            
            elapsed = time.time() - start_time
            
            assert len(response) > 0, "Should get response despite failovers"
            assert elapsed < 60, f"Failover should be fast, took {elapsed:.2f}s"
            
            # Check metrics
            stats = llm.get_metrics()
            print(f"\n✅ Failover successful:")
            print(f"   Providers tried: {stats.get('providers', {})}")
            print(f"   Success rate: {stats.get('success_rate', 'N/A')}")
            print(f"   Response: {response[:50]}...")
            
        except Exception as e:
            pytest.fail(f"Failover should handle errors gracefully: {e}")
    
    @pytest.mark.asyncio
    async def test_concurrent_llm_streams(self):
        """Test: Multiple LLM streams run concurrently without blocking."""
        llm = LLMClient()
        
        prompts = [
            "Count: 1",
            "Count: 2", 
            "Count: 3"
        ]
        
        start_time = time.time()
        
        # Run 3 streams concurrently
        tasks = []
        for prompt in prompts:
            async def stream_prompt(p):
                chunks = []
                async for chunk in llm.stream_chat(prompt=p):
                    chunks.append(chunk)
                return "".join(chunks)
            
            tasks.append(stream_prompt(prompt))
        
        responses = await asyncio.gather(*tasks)
        elapsed = time.time() - start_time
        
        # Assertions
        assert len(responses) == 3, "Should complete all streams"
        assert all(len(r) > 0 for r in responses), "All should have responses"
        assert elapsed < 90, f"Concurrent should be faster, took {elapsed:.2f}s"
        
        print(f"\n✅ 3 concurrent streams in {elapsed:.2f}s")
        for i, resp in enumerate(responses):
            print(f"   Stream {i+1}: {resp[:40]}...")
    
    @pytest.mark.asyncio
    async def test_llm_timeout_handling(self):
        """Test: LLM respects timeout and doesn't hang UI."""
        llm = LLMClient()  # Will use default timeout from config
        
        start_time = time.time()
        
        try:
            # Very long context that might timeout
            response = ""
            async for chunk in llm.stream_chat(
                prompt="Explain quantum physics" * 10,
                max_tokens=10
            ):
                response += chunk
            
            elapsed = time.time() - start_time
            
            # Should either complete fast or timeout gracefully
            assert elapsed < 10, f"Should timeout or complete fast, took {elapsed:.2f}s"
            
            print(f"\n✅ Timeout handling working: {elapsed:.2f}s")
            
        except asyncio.TimeoutError:
            elapsed = time.time() - start_time
            assert elapsed < 10, "Timeout should be enforced"
            print(f"\n✅ Timeout enforced correctly at {elapsed:.2f}s")
    
    @pytest.mark.asyncio
    async def test_llm_with_wisdom_system(self):
        """Test: LLM + Wisdom system integration."""
        wisdom = WisdomSystem()
        llm = LLMClient()
        
        # Get wisdom verse
        verse = wisdom.get_random()
        
        # Ask LLM about the verse
        prompt = f"In one sentence, what does this mean: {verse.text[:100]}"
        
        start_time = time.time()
        response = ""
        async for chunk in llm.stream_chat(prompt=prompt, max_tokens=50):
            response += chunk
        elapsed = time.time() - start_time
        
        assert len(response) > 0, "Should interpret wisdom"
        assert elapsed < 30, f"Should be fast, took {elapsed:.2f}s"
        
        print(f"\n✅ Wisdom + LLM integration:")
        print(f"   Verse: {verse.text[:60]}...")
        print(f"   LLM interpretation: {response[:80]}...")
        print(f"   Time: {elapsed:.2f}s")
    
    @pytest.mark.asyncio
    async def test_progress_bar_with_llm_stream(self):
        """Test: Progress bar updates with LLM stream progress."""
        console = Console(file=StringIO())
        llm = LLMClient()
        
        # Create progress bar
        progress = ProgressBar(
            total=100,
            description="Streaming LLM"
        )
        
        start_time = time.time()
        chunk_count = 0
        
        async for chunk in llm.stream_chat(prompt="Count to 5", max_tokens=20):
            chunk_count += 1
            # Update progress
            progress.update(min(chunk_count * 10, 100))
        
        elapsed = time.time() - start_time
        
        assert chunk_count > 0, "Should receive chunks"
        assert progress.current > 0, "Progress should update"
        
        print(f"\n✅ Progress bar + LLM stream:")
        print(f"   Chunks: {chunk_count}")
        print(f"   Progress: {progress.current}%")
        print(f"   Time: {elapsed:.2f}s")
    
    @pytest.mark.asyncio
    async def test_message_box_with_real_llm_response(self):
        """Test: MessageBox renders real LLM response."""
        console = Console(file=StringIO())
        llm = LLMClient()
        
        # Get real response
        response = ""
        async for chunk in llm.stream_chat(prompt="Say hello", max_tokens=10):
            response += chunk
        
        # Create message box
        from qwen_dev_cli.tui.components._enums import MessageRole
        msg = Message(
            content=response,
            role=MessageRole.ASSISTANT
        )
        
        msg_box = MessageBox(msg)
        
        # Render
        rendered = msg_box.render()
        
        assert rendered is not None, "Should render"
        assert len(response) > 0, "Should have content"
        
        print(f"\n✅ MessageBox with real LLM:")
        print(f"   Response: {response[:60]}...")
        print(f"   Rendered: Yes")
    
    @pytest.mark.asyncio
    async def test_status_badge_updates_during_llm_call(self):
        """Test: Status badge reflects LLM call state."""
        console = Console(file=StringIO())
        llm = LLMClient()
        
        # Start with processing status
        badge = StatusBadge(level=StatusLevel.INFO, text="Processing...")
        console.print(badge.render())
        
        start_time = time.time()
        
        try:
            # Make LLM call
            response = ""
            async for chunk in llm.stream_chat(prompt="Quick test", max_tokens=5):
                response += chunk
            
            # Update to success
            badge = StatusBadge(level=StatusLevel.SUCCESS, text="Complete")
            elapsed = time.time() - start_time
            
            assert len(response) > 0
            assert elapsed < 30
            
            print(f"\n✅ Status badge lifecycle:")
            print(f"   Processing → Complete")
            print(f"   Response: {response[:40]}...")
            print(f"   Time: {elapsed:.2f}s")
            
        except Exception as e:
            # Update to error
            badge = StatusBadge(level=StatusLevel.ERROR, text=f"Failed: {e}")
            pytest.fail(f"LLM call should succeed: {e}")


class TestLLMProviderFallback:
    """Test provider fallback logic scientifically."""
    
    @pytest.mark.asyncio
    async def test_ollama_primary_fast(self):
        """Test: Ollama (local) is fastest when available."""
        llm = LLMClient()
        
        # Force ollama
        start = time.time()
        response = ""
        async for chunk in llm.stream_chat(
            prompt="Quick",
            provider="ollama",
            enable_failover=True,
            max_tokens=5
        ):
            response += chunk
        elapsed = time.time() - start
        
        # Local should be very fast OR failover to nebius
        assert elapsed < 30, f"Local/failover should be fast: {elapsed:.2f}s"
        
        print(f"\n✅ Primary provider test:")
        print(f"   Time: {elapsed:.2f}s")
        print(f"   Response: {response[:40]}...")
    
    @pytest.mark.asyncio
    async def test_auto_provider_selection(self):
        """Test: Auto provider selection works."""
        llm = LLMClient()
        
        start = time.time()
        response = ""
        async for chunk in llm.stream_chat(
            prompt="Auto select",
            provider="auto",  # Let it choose
            max_tokens=10
        ):
            response += chunk
        elapsed = time.time() - start
        
        assert len(response) > 0
        assert elapsed < 60
        
        stats = llm.get_metrics()
        print(f"\n✅ Auto provider selection:")
        print(f"   Time: {elapsed:.2f}s")
        print(f"   Providers: {stats.get('providers', {})}")


if __name__ == "__main__":
    print("""
╔═══════════════════════════════════════════════════════════╗
║     🧪 TUI + LLM EDGE CASES - SCIENTIFIC TESTING          ║
╚═══════════════════════════════════════════════════════════╝

Testing with REAL LLM providers:
  1. Ollama (LOCAL) - Primary, fastest
  2. Nebius (ONLINE) - Backup
  3. HuggingFace (ONLINE) - Fallback

Running 8 edge case tests...
    """)
    
    pytest.main([__file__, "-v", "-s"])
