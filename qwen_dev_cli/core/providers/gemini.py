"""Gemini API provider implementation."""

import os
import asyncio
from typing import Dict, List, Optional, AsyncGenerator
import logging

logger = logging.getLogger(__name__)

# REMOVED top-level import: import google.generativeai as genai

class GeminiProvider:
    """Google Gemini API provider."""
    
    def __init__(self, api_key: Optional[str] = None, model_name: str = None):
        """Initialize Gemini provider.
        
        Args:
            api_key: Gemini API key (defaults to GEMINI_API_KEY env var)
            model_name: Model name override
        """
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        # Respect GEMINI_MODEL from .env unconditionally (Constitutional compliance)
        default_model = "gemini-2.5-flash"  # Stable production model
        self.model_name = model_name or os.getenv("GEMINI_MODEL", default_model)
        self._client = None
        self._genai = None
        self.generation_config = None
        
    def _ensure_genai(self):
        """Lazy load genai SDK."""
        if self._genai is None:
            try:
                # Suppress gRPC warnings during import
                import sys
                import io
                _original_stderr = sys.stderr
                sys.stderr = io.StringIO()
                
                import google.generativeai as genai
                
                # Restore stderr
                sys.stderr = _original_stderr
                
                self._genai = genai
                self._genai.configure(api_key=self.api_key)
                self.generation_config = self._genai.GenerationConfig(
                    temperature=0.7,
                    max_output_tokens=8192,
                )
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
                    # FORCE visible confirmation
                    print(f"✅ Gemini: {self.model_name}")
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
            
            # Create generator function for streaming (suppress stderr for gRPC)
            def _stream():
                import sys
                import io
                _original_stderr = sys.stderr
                sys.stderr = io.StringIO()
                try:
                    result = self.client.generate_content(
                        prompt,
                        generation_config={
                            'max_output_tokens': max_tokens,
                            'temperature': temperature,
                        },
                        stream=True
                    )
                    return result
                finally:
                    sys.stderr = _original_stderr
            
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
        system_prompt: Optional[str] = None,
        max_tokens: int = 8192,
        temperature: float = 0.7,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """
        Streaming VERDADEIRO e seguro com suporte a system_prompt.
        """
        if not self.is_available():
            raise RuntimeError("Gemini provider not available")
        
        try:
            # Converte formato OpenAI/Standard para Gemini History
            history = []
            last_user_msg = ""
            
            if system_prompt:
                # Hack funcional para Gemini: System instruction como primeira user message
                history.append({"role": "user", "parts": [f"System Instruction: {system_prompt}"]})
                history.append({"role": "model", "parts": ["Understood. I will follow these instructions."]})

            for msg in messages[:-1]:  # Todos exceto o último (que é o prompt atual)
                role = "user" if msg["role"] == "user" else "model"
                content = msg.get("content", "")
                history.append({"role": role, "parts": [content]})
            
            last_user_msg = messages[-1]["content"] if messages else ""

            chat = self.client.start_chat(history=history)
            
            # AQUI ESTAVA O BUG: O método send_message com stream=True precisa ser iterado corretamente
            def _stream():
                return chat.send_message(
                    last_user_msg,
                    generation_config=self.generation_config or {
                        'max_output_tokens': max_tokens,
                        'temperature': temperature,
                    },
                    stream=True
                )
            
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(None, _stream)
            
            for chunk in response:
                if chunk.text:
                    yield chunk.text
                await asyncio.sleep(0)  # Yield control
                    
        except Exception as e:
            logger.error(f"Gemini streaming error: {e}")
            yield f"\n[System Error: {str(e)}]"
    
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

