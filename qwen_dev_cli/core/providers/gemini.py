"""Gemini API provider implementation."""

import os
import asyncio
from typing import Dict, List, Optional, AsyncGenerator
import logging

logger = logging.getLogger(__name__)

# REMOVED top-level import: import google.generativeai as genai

class GeminiProvider:
    """Google Gemini API provider."""
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize Gemini provider.
        
        Args:
            api_key: Gemini API key (defaults to GEMINI_API_KEY env var)
        """
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.model_name = os.getenv("GEMINI_MODEL", "gemini-pro")
        self._client = None
        self._genai = None
        
    def _ensure_genai(self):
        """Lazy load genai SDK."""
        if self._genai is None:
            try:
                import google.generativeai as genai
                self._genai = genai
                self._genai.configure(api_key=self.api_key)
                logger.info("Lazy loaded google.generativeai")
            except ImportError:
                logger.error("google-generativeai not installed")
                raise RuntimeError("google-generativeai not installed")

    @property
    def client(self):
        """Lazy client initialization."""
        if self._client is None:
            if self.api_key:
                self._ensure_genai()
                try:
                    self._client = self._genai.GenerativeModel(self.model_name)
                    logger.info(f"Gemini provider initialized with model: {self.model_name}")
                except Exception as e:
                    logger.error(f"Failed to initialize Gemini: {e}")
                    self._client = None
        return self._client
    
    def is_available(self) -> bool:
        """Check if provider is available."""
        return self.client is not None
    
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
        if not self.is_available():
            raise RuntimeError("Gemini provider not available")
        
        try:
            # Convert messages to Gemini format
            prompt = self._format_messages(messages)
            
            # Generate in thread pool (Gemini SDK is sync)
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.client.generate_content(
                    prompt,
                    generation_config={
                        'max_output_tokens': max_tokens,
                        'temperature': temperature,
                    }
                )
            )
            
            return response.text
        
        except Exception as e:
            logger.error(f"Gemini generation failed: {e}")
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
        if not self.is_available():
            raise RuntimeError("Gemini provider not available")
        
        try:
            prompt = self._format_messages(messages)
            
            # Create generator function for streaming
            def _stream():
                return self.client.generate_content(
                    prompt,
                    generation_config={
                        'max_output_tokens': max_tokens,
                        'temperature': temperature,
                    },
                    stream=True
                )
            
            # Run streaming in thread pool and yield chunks
            loop = asyncio.get_event_loop()
            response_iterator = await loop.run_in_executor(None, _stream)
            
            # Yield chunks (run iteration in thread pool to avoid blocking)
            for chunk in response_iterator:
                if chunk.text:
                    yield chunk.text
                    # Small delay to allow other tasks
                    await asyncio.sleep(0)
        
        except Exception as e:
            logger.error(f"Gemini streaming failed: {e}")
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
        
        Some parts of the codebase call stream_chat() instead of stream_generate().
        This method delegates to stream_generate().
        """
        async for chunk in self.stream_generate(messages, max_tokens, temperature, **kwargs):
            yield chunk
    
    def _format_messages(self, messages: List[Dict[str, str]]) -> str:
        """Format messages for Gemini.
        
        Gemini uses a simpler prompt format than chat APIs.
        We concatenate messages with role prefixes.
        """
        formatted = []
        for msg in messages:
            role = msg.get('role', 'user')
            content = msg.get('content', '')
            
            if role == 'system':
                formatted.append(f"System: {content}")
            elif role == 'user':
                formatted.append(f"User: {content}")
            elif role == 'assistant':
                formatted.append(f"Assistant: {content}")
        
        return "\n\n".join(formatted)
    
    def get_model_info(self) -> Dict[str, str | bool | int]:
        """Get model information."""
        return {
            'provider': 'gemini',
            'model': self.model_name,
            'available': self.is_available(),
            'context_window': 32768,  # Gemini Pro context
            'supports_streaming': True
        }
    
    def count_tokens(self, text: str) -> int:
        """Estimate token count for text.
        
        Args:
            text: Text to count tokens for
            
        Returns:
            Approximate token count
        """
        # Simple estimation: ~4 chars per token (common for most models)
        return len(text) // 4

