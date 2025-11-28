"""Nebius API provider implementation."""

import os
from typing import Dict, List, Optional, AsyncGenerator
import logging

logger = logging.getLogger(__name__)

# REMOVED top-level import: import openai

class NebiusProvider:
    """Nebius AI Studio provider (OpenAI-compatible)."""

    def __init__(self, api_key: Optional[str] = None):
        """Initialize Nebius provider.
        
        Args:
            api_key: Nebius API key (defaults to NEBIUS_API_KEY env var)
        """
        self.api_key = api_key or os.getenv("NEBIUS_API_KEY")
        self.model_name = os.getenv("NEBIUS_MODEL", "Qwen/Qwen2.5-Coder-32B-Instruct")
        self._client = None
        self._openai = None

    def _ensure_openai(self):
        """Lazy load openai SDK."""
        if self._openai is None:
            try:
                import openai
                self._openai = openai
                logger.info("Lazy loaded openai")
            except ImportError:
                logger.error("openai not installed")
                raise RuntimeError("openai not installed")

    @property
    def client(self):
        """Lazy client initialization."""
        if self._client is None:
            if self.api_key:
                self._ensure_openai()
                try:
                    self._client = self._openai.AsyncOpenAI(
                        api_key=self.api_key,
                        base_url="https://api.studio.nebius.ai/v1/"
                    )
                    logger.info(f"Nebius provider initialized with model: {self.model_name}")
                except Exception as e:
                    logger.error(f"Failed to initialize Nebius: {e}")
                    self._client = None
        return self._client

    def is_available(self) -> bool:
        """Check if provider is available."""
        return self.client is not None

    async def generate(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = 2048,
        temperature: float = 0.6,
        **kwargs
    ) -> str:
        """Generate completion from messages.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            
        Returns:
            Generated text
        """
        if not self.is_available():
            raise RuntimeError("Nebius provider not available")

        try:
            response = await self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                extra_body={"top_p": 0.9}
            )

            return response.choices[0].message.content

        except Exception as e:
            logger.error(f"Nebius generation failed: {e}")
            raise

    async def stream_generate(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = 2048,
        temperature: float = 0.6,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """Stream generation from messages.
        
        Args:
            messages: List of message dicts
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            
        Yields:
            Generated text chunks
        """
        if not self.is_available():
            raise RuntimeError("Nebius provider not available")

        try:
            stream = await self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                stream=True,
                extra_body={"top_p": 0.9}
            )

            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

        except Exception as e:
            logger.error(f"Nebius chat error: {e}")
            raise

    async def stream_chat(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = 2048,
        temperature: float = 0.6,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """
        Alias for stream_generate to maintain compatibility.
        
        Some parts of the codebase call stream_chat() instead of stream_generate().
        This method delegates to stream_generate().
        """
        async for chunk in self.stream_generate(messages, max_tokens, temperature, **kwargs):
            yield chunk
