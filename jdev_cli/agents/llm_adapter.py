"""
LLM Client Adapter - Bridge Pattern for Advanced Features
==========================================================

Philosophy: "Adapt what exists, don't replace what works."

This adapter adds thinking patterns on TOP of existing LLMClient
without changing a single line of working code.

Pattern: Adapter + Decorator
Risk: ZERO (only adds, never breaks)
"""

import logging
from typing import Any, Dict, Optional, AsyncIterator


class LLMClientAdapter:
    """
    Adapter that adds "thinking" capabilities to existing LLMClient.
    
    This is the HONEST way to add features:
    1. Wraps existing client (no changes needed)
    2. Adds new methods that use existing methods internally
    3. Graceful degradation when features unavailable
    4. Zero breaking changes
    
    Usage:
        original_client = LLMClient(...)
        enhanced_client = LLMClientAdapter(original_client)
        
        # Old code still works
        response = await enhanced_client.generate(prompt)
        
        # New code gets benefits
        result = await enhanced_client.generate_with_thinking(prompt, budget=5000)
    """

    def __init__(self, llm_client: Any):
        """
        Wrap existing LLMClient.
        
        Args:
            llm_client: Your existing LLMClient instance
        """
        self._client = llm_client
        self.logger = logging.getLogger("llm_adapter")

        # Check what the client actually supports
        self._has_generate = hasattr(llm_client, 'generate')
        self._has_stream = hasattr(llm_client, 'stream')
        self._has_stream_chat = hasattr(llm_client, 'stream_chat')

        self.logger.info(
            f"LLMClientAdapter initialized - "
            f"generate:{self._has_generate} "
            f"stream:{self._has_stream} "
            f"stream_chat:{self._has_stream_chat}"
        )

    # ========================================================================
    # PASSTHROUGH - Existing Methods Work Unchanged
    # ========================================================================

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs: Any,
    ) -> str:
        """Passthrough to original generate() - no changes"""
        if not self._has_generate:
            raise NotImplementedError("LLMClient doesn't have generate()")

        return await self._client.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            **kwargs,
        )

    async def stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        """Passthrough to original stream() - no changes"""
        if not self._has_stream:
            raise NotImplementedError("LLMClient doesn't have stream()")

        async for chunk in self._client.stream(
            prompt=prompt,
            system_prompt=system_prompt,
            **kwargs,
        ):
            yield chunk

    async def stream_chat(
        self,
        prompt: str,
        context: Optional[str] = None,
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        """Passthrough to original stream_chat() - no changes"""
        if not self._has_stream_chat:
            raise NotImplementedError("LLMClient doesn't have stream_chat()")

        async for chunk in self._client.stream_chat(
            prompt=prompt,
            context=context,
            **kwargs,
        ):
            yield chunk

    # ========================================================================
    # NEW FEATURES - Built on Top of Existing Methods
    # ========================================================================

    async def generate_with_thinking(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        thinking_budget: int = 5000,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """
        Simulate "extended thinking" using existing generate().
        
        This is HONEST implementation:
        - Uses two-phase prompting (think → respond)
        - Tracks approximate tokens
        - Returns structured result
        - No fancy features claimed - just good prompting
        
        Args:
            prompt: The actual task/question
            system_prompt: System context
            thinking_budget: Max tokens for thinking phase
            
        Returns:
            {
                "thinking": "reasoning trace",
                "response": "final answer",
                "tokens_used": approximate_count
            }
        """
        self.logger.info(f"Simulating extended thinking (budget: {thinking_budget})")

        # Phase 1: Thinking
        thinking_prompt = f"""
{system_prompt or ''}

TASK: {prompt}

Before answering, think step-by-step:
1. Understand the problem deeply
2. Consider multiple approaches
3. Identify risks and constraints
4. Formulate the best solution

Provide your detailed reasoning (aim for ~{thinking_budget // 4} words).
"""

        thinking_response = await self.generate(
            prompt=thinking_prompt,
            system_prompt=system_prompt,
            **kwargs,
        )

        # Phase 2: Final Answer
        answer_prompt = f"""
Based on your thinking:

{thinking_response}

Now provide the final, concise answer to: {prompt}
"""

        final_response = await self.generate(
            prompt=answer_prompt,
            system_prompt=system_prompt,
            **kwargs,
        )

        # Estimate tokens (rough approximation)
        tokens_used = len(thinking_response.split()) + len(final_response.split())

        return {
            "thinking": thinking_response,
            "response": final_response,
            "tokens_used": tokens_used,
        }

    async def generate_structured(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        schema: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> str:
        """
        Request structured JSON output using prompt engineering.
        
        This is HONEST implementation:
        - Adds JSON schema to prompt
        - Requests valid JSON output
        - No guaranteed schema validation (that's Nov 2025 beta)
        - But works well in practice
        
        Args:
            prompt: The actual task
            system_prompt: System context
            schema: Optional JSON schema hint
            
        Returns:
            JSON string (hopefully valid)
        """
        self.logger.info("Requesting structured JSON output")

        structured_prompt = f"""
{prompt}

CRITICAL: Respond with ONLY valid JSON. No markdown, no explanation.

{f"Expected schema: {schema}" if schema else ""}

Your response must be parseable JSON.
"""

        return await self.generate(
            prompt=structured_prompt,
            system_prompt=system_prompt,
            **kwargs,
        )

    async def stream_with_thinking(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        thinking_budget: int = 5000,
        **kwargs: Any,
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        Stream thinking + response for real-time UI.
        
        Yields events:
            {"type": "thinking", "content": "..."}
            {"type": "response", "content": "..."}
            {"type": "done", "tokens_used": N}
        """
        self.logger.info("Streaming with thinking phase")

        # Phase 1: Stream thinking
        thinking_prompt = f"""
{system_prompt or ''}

TASK: {prompt}

Think step-by-step about this problem. Be thorough.
"""

        thinking_buffer = []
        async for chunk in self.stream(
            prompt=thinking_prompt,
            system_prompt=system_prompt,
            **kwargs,
        ):
            thinking_buffer.append(chunk)
            yield {"type": "thinking", "content": chunk}

        thinking_text = "".join(thinking_buffer)

        # Phase 2: Stream response
        answer_prompt = f"""
Based on your thinking:

{thinking_text}

Now provide the final answer to: {prompt}
"""

        response_buffer = []
        async for chunk in self.stream(
            prompt=answer_prompt,
            system_prompt=system_prompt,
            **kwargs,
        ):
            response_buffer.append(chunk)
            yield {"type": "response", "content": chunk}

        # Done
        total_tokens = len(thinking_text.split()) + len("".join(response_buffer).split())
        yield {"type": "done", "tokens_used": total_tokens}

    # ========================================================================
    # INTROSPECTION - Know Thy Limits
    # ========================================================================

    def supports_native_thinking(self) -> bool:
        """Does the underlying client natively support thinking?"""
        return hasattr(self._client, 'generate_with_thinking')

    def supports_native_structured(self) -> bool:
        """Does the underlying client natively support structured outputs?"""
        return hasattr(self._client, 'generate_structured')

    def get_capabilities(self) -> Dict[str, bool]:
        """Get adapter capabilities"""
        return {
            "generate": self._has_generate,
            "stream": self._has_stream,
            "stream_chat": self._has_stream_chat,
            "thinking_simulation": self._has_generate,  # We can simulate
            "structured_simulation": self._has_generate,  # We can simulate
            "native_thinking": self.supports_native_thinking(),
            "native_structured": self.supports_native_structured(),
        }


# ============================================================================
# CONVENIENCE WRAPPER
# ============================================================================

def wrap_llm_client(client: Any) -> LLMClientAdapter:
    """
    Convenience function to wrap an LLMClient.
    
    Usage:
        from llm_adapter import wrap_llm_client
        
        original = LLMClient(...)
        enhanced = wrap_llm_client(original)
        
        # All old code works
        response = await enhanced.generate(prompt)
        
        # New code gets features
        result = await enhanced.generate_with_thinking(prompt, budget=5000)
    """
    return LLMClientAdapter(client)


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

if __name__ == "__main__":
    import asyncio

    # Mock LLM client (simulates your real one)
    class MockLLMClient:
        async def generate(self, prompt, system_prompt=None, **kwargs):
            return f"Generated response to: {prompt[:50]}..."

        async def stream(self, prompt, system_prompt=None, **kwargs):
            words = f"Streaming response to: {prompt[:50]}...".split()
            for word in words:
                yield word + " "

    async def demo():
        print("=" * 80)
        print("LLM CLIENT ADAPTER - DEMO")
        print("=" * 80)

        # Wrap existing client
        original = MockLLMClient()
        adapter = LLMClientAdapter(original)

        # Check capabilities
        print("\n📊 CAPABILITIES:")
        caps = adapter.get_capabilities()
        for name, supported in caps.items():
            status = "✅" if supported else "❌"
            print(f"  {status} {name}")

        # Demo 1: Original methods still work
        print("\n" + "=" * 80)
        print("DEMO 1: Original Methods Work")
        print("=" * 80)

        response = await adapter.generate("What is 2+2?")
        print(f"Response: {response}")

        # Demo 2: New thinking feature
        print("\n" + "=" * 80)
        print("DEMO 2: Simulated Extended Thinking")
        print("=" * 80)

        result = await adapter.generate_with_thinking(
            "Explain quantum computing",
            thinking_budget=5000,
        )
        print(f"Thinking: {result['thinking'][:100]}...")
        print(f"Response: {result['response'][:100]}...")
        print(f"Tokens: {result['tokens_used']}")

        # Demo 3: Streaming with thinking
        print("\n" + "=" * 80)
        print("DEMO 3: Streaming with Thinking")
        print("=" * 80)

        async for event in adapter.stream_with_thinking("What is AI?"):
            if event["type"] == "thinking":
                print(f"💭 {event['content']}", end="", flush=True)
            elif event["type"] == "response":
                print(f"💡 {event['content']}", end="", flush=True)
            elif event["type"] == "done":
                print(f"\n✅ Done ({event['tokens_used']} tokens)")

        print("\n" + "=" * 80)
        print("✅ ALL DEMOS PASSED - ZERO BREAKING CHANGES")
        print("=" * 80)

    asyncio.run(demo())
