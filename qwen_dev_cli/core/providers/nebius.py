"""Nebius AI provider integration.

Nebius provides access to various LLM models via OpenAI-compatible API.
API Base: https://api.studio.nebius.ai/v1/
"""

import os
import logging
from typing import AsyncGenerator, Optional, Dict, Any, List
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)


class NebiusProvider:
    """Nebius AI provider using OpenAI-compatible interface."""
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize Nebius client."""
        self.api_key = api_key or os.getenv("NEBIUS_API_KEY")
        if not self.api_key:
            raise ValueError("NEBIUS_API_KEY required")
        
        self.client = AsyncOpenAI(
            base_url="https://api.studio.nebius.ai/v1/",
            api_key=self.api_key
        )
        
        # Available models (updated with real Nebius models)
        self.models = {
            "qwen3-235b": "Qwen/Qwen3-235B-A22B-Instruct-2507",
            "qwen2.5-coder-7b": "Qwen/Qwen2.5-Coder-7B-fast",
            "llama-3.3-70b": "meta-llama/Llama-3.3-70B-Instruct-fast",
            "llama-3.1-8b": "meta-llama/Meta-Llama-3.1-8B-Instruct-fast",
            "deepseek-r1": "deepseek-ai/DeepSeek-R1-0528",
            "gemma-2-9b": "google/gemma-2-9b-it-fast"
        }
        self.default_model = "qwen3-235b"
    
    async def stream_chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        max_tokens: int = 2048,
        temperature: float = 0.7,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """Stream chat completion from Nebius."""
        model_id = self.models.get(model or self.default_model)
        if not model_id:
            raise ValueError(f"Unknown model: {model}. Available: {list(self.models.keys())}")
        
        try:
            stream = await self.client.chat.completions.create(
                model=model_id,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                stream=True,
                **kwargs
            )
            
            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        
        except Exception as e:
            logger.error(f"Nebius stream error: {e}")
            raise
    
    async def chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        max_tokens: int = 2048,
        temperature: float = 0.7,
        **kwargs
    ) -> str:
        """Non-streaming chat completion."""
        model_id = self.models.get(model or self.default_model)
        if not model_id:
            raise ValueError(f"Unknown model: {model}")
        
        try:
            response = await self.client.chat.completions.create(
                model=model_id,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                stream=False,
                **kwargs
            )
            return response.choices[0].message.content
        
        except Exception as e:
            logger.error(f"Nebius chat error: {e}")
            raise
