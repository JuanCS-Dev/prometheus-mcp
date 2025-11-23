"""Ollama local LLM provider implementation."""

import os
import asyncio
import logging
from typing import Dict, List, Optional, AsyncGenerator
import aiohttp

logger = logging.getLogger(__name__)


class OllamaProvider:
    """Ollama local LLM provider."""
    
    def __init__(self, base_url: Optional[str] = None, model: Optional[str] = None):
        """Initialize Ollama provider.
        
        Args:
            base_url: Ollama API base URL (defaults to http://localhost:11434)
            model: Model name (defaults to qwen2.5-coder:latest)
        """
        self.base_url = base_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.model_name = model or os.getenv("OLLAMA_MODEL", "qwen2.5-coder:latest")
        self._session: Optional[aiohttp.ClientSession] = None
        logger.info(f"Ollama provider initialized: {self.base_url} / {self.model_name}")
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session
    
    async def is_available(self) -> bool:
        """Check if Ollama is running and model is available."""
        try:
            session = await self._get_session()
            async with session.get(f"{self.base_url}/api/tags", timeout=aiohttp.ClientTimeout(total=2)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    models = [m.get("name", "") for m in data.get("models", [])]
                    # Check if our model exists
                    model_available = any(self.model_name in m for m in models)
                    if not model_available:
                        logger.warning(f"Model {self.model_name} not found. Available: {models[:5]}")
                    return model_available
                return False
        except Exception as e:
            logger.debug(f"Ollama not available: {e}")
            return False
    
    async def generate(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = 2048,
        temperature: float = 0.7,
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
        if not await self.is_available():
            raise RuntimeError("Ollama provider not available")
        
        try:
            session = await self._get_session()
            
            # Ollama chat API format
            payload = {
                "model": self.model_name,
                "messages": messages,
                "stream": False,
                "options": {
                    "num_predict": max_tokens,
                    "temperature": temperature,
                }
            }
            
            async with session.post(
                f"{self.base_url}/api/chat",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=120)
            ) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    raise RuntimeError(f"Ollama error {resp.status}: {error_text}")
                
                data = await resp.json()
                return data.get("message", {}).get("content", "")
        
        except Exception as e:
            logger.error(f"Ollama generation failed: {e}")
            raise
    
    async def stream_generate(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = 2048,
        temperature: float = 0.7,
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
        if not await self.is_available():
            raise RuntimeError("Ollama provider not available")
        
        try:
            session = await self._get_session()
            
            payload = {
                "model": self.model_name,
                "messages": messages,
                "stream": True,
                "options": {
                    "num_predict": max_tokens,
                    "temperature": temperature,
                }
            }
            
            async with session.post(
                f"{self.base_url}/api/chat",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=300)
            ) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    raise RuntimeError(f"Ollama error {resp.status}: {error_text}")
                
                # Stream line by line (NDJSON)
                async for line in resp.content:
                    if line:
                        import json
                        try:
                            chunk = json.loads(line)
                            content = chunk.get("message", {}).get("content", "")
                            if content:
                                yield content
                        except json.JSONDecodeError:
                            continue
        
        except Exception as e:
            logger.error(f"Ollama streaming failed: {e}")
            raise
    
    async def stream_chat(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = 2048,
        temperature: float = 0.7,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """
        Alias for stream_generate to maintain compatibility.
        """
        async for chunk in self.stream_generate(messages, max_tokens, temperature, **kwargs):
            yield chunk
    
    def get_model_info(self) -> Dict[str, str | bool | int]:
        """Get model information."""
        return {
            'provider': 'ollama',
            'model': self.model_name,
            'base_url': self.base_url,
            'supports_streaming': True
        }
    
    async def close(self):
        """Close aiohttp session."""
        if self._session and not self._session.closed:
            await self._session.close()
