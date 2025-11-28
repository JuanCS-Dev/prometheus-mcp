"""Gemini API provider implementation."""

import os
import asyncio
from typing import Dict, List, Optional, AsyncGenerator
import logging

logger = logging.getLogger(__name__)

# REMOVED top-level import: import google.generativeai as genai

# Anti-repetition and table formatting suffix added to all system prompts
# Based on: https://ai.google.dev/gemini-api/docs/troubleshooting
GEMINI_OUTPUT_RULES = """

CRITICAL OUTPUT RULES:
- Be concise and direct
- Never repeat yourself
- Never duplicate content horizontally or vertically
- Provide each answer only once
- If you find yourself repeating, STOP and move on

MARKDOWN TABLES - CRITICAL:
- Use EXACTLY 3 hyphens per column: |---|---|---|
- NO extra spaces or padding for visual alignment
- NO tabs - only single spaces
- FOR TABLE HEADINGS, IMMEDIATELY ADD ' |' AFTER THE HEADING
- Keep cell content short (under 30 chars)
"""

class GeminiProvider:
    """Google Gemini API provider."""
    
    def __init__(
        self, 
        api_key: Optional[str] = None, 
        model_name: str = None,
        enable_code_execution: bool = False,
        enable_search: bool = False,
        enable_caching: bool = True
    ):
        """Initialize Gemini provider.
        
        Args:
            api_key: Gemini API key (defaults to GEMINI_API_KEY env var)
            model_name: Model name override
            enable_code_execution: Enable native Python sandbox
            enable_search: Enable Google Search grounding
            enable_caching: Enable Context Caching for large contexts
        """
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        # Respect GEMINI_MODEL from .env unconditionally (Constitutional compliance)
        default_model = "gemini-2.5-flash"  # Stable production model
        self.model_name = model_name or os.getenv("GEMINI_MODEL", default_model)
        
        # Native Capabilities
        self.enable_code_execution = enable_code_execution
        self.enable_search = enable_search
        self.enable_caching = enable_caching
        
        self._client = None
        self._genai = None
        self.generation_config = None
        self._cached_content = None
        
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
                    # Configure Tools
                    tools = []
                    if self.enable_code_execution:
                        tools.append("code_execution")
                    if self.enable_search:
                        tools.append("google_search_retrieval")
                    
                    # Initialize Model with Tools
                    self._client = self._genai.GenerativeModel(
                        self.model_name,
                        tools=tools if tools else None
                    )
                    
                    # FORCE visible confirmation
                    print(f"✅ Gemini Native: {self.model_name}")
                    if self.enable_code_execution:
                        print("   └── 🐍 Native Code Execution: ENABLED")
                    if self.enable_search:
                        print("   └── 🌍 Google Search: ENABLED")
                        
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
        Native Streaming with System Instruction and Tools.
        """
        if not self.is_available():
            raise RuntimeError("Gemini provider not available")
        
        try:
            # 1. Prepare Tools
            tools = []
            if self.enable_code_execution:
                tools.append("code_execution")
            if self.enable_search:
                tools.append("google_search_retrieval")
            
            # 2. Initialize Model (with System Instruction)
            # We create a specific instance for this chat to support dynamic system prompt
            # This is lightweight and ensures we use the native system_instruction
            
            # Add anti-repetition instructions
            full_system_prompt = (system_prompt or "") + GEMINI_OUTPUT_RULES
            
            # CRITICAL: Temperature MUST be 1.0 for Gemini 2.5+ to prevent looping
            safe_temperature = 1.0
            if temperature != 1.0:
                 # We silently enforce 1.0 for stability as per DeepMind docs
                 safe_temperature = 1.0

            model = self._genai.GenerativeModel(
                self.model_name,
                tools=tools if tools else None,
                system_instruction=full_system_prompt
            )

            # 3. Prepare History
            history = []
            for msg in messages[:-1]:
                role = "user" if msg["role"] == "user" else "model"
                content = msg.get("content", "")
                history.append({"role": role, "parts": [content]})
            
            last_user_msg = messages[-1]["content"] if messages else ""

            # 4. Start Chat
            chat = model.start_chat(history=history)
            
            # 5. Send Message (Async Wrapper)
            # Use automatic_function_calling=True by default if tools are enabled
            def _send():
                return chat.send_message(
                    last_user_msg,
                    generation_config={
                        'max_output_tokens': max_tokens,
                        'temperature': safe_temperature,
                    },
                    stream=True
                )
            
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(None, _send)
            
            # FIX: Convert iterable response to iterator
            response_iterator = iter(response)
            
            # 6. Stream Response
            # We iterate manually to avoid blocking the event loop
            def _next_chunk():
                try:
                    return next(response_iterator)
                except StopIteration:
                    return None
                except Exception as e:
                    return e

            while True:
                chunk = await loop.run_in_executor(None, _next_chunk)
                
                if chunk is None:
                    break
                if isinstance(chunk, Exception):
                    raise chunk

                try:
                    # Handle Code Execution Parts
                    if hasattr(chunk, 'parts'):
                        for part in chunk.parts:
                            if hasattr(part, 'executable_code'):
                                # Notify user about code execution (optional, or yield a marker)
                                pass
                            if hasattr(part, 'code_execution_result'):
                                # Notify user about result
                                pass
                            if hasattr(part, 'text') and part.text:
                                yield part.text
                    elif hasattr(chunk, 'text') and chunk.text:
                        yield chunk.text
                except Exception as chunk_error:
                    # Some chunks might be pure metadata or function calls without text
                    continue
                
                await asyncio.sleep(0)

                    
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
        """Count tokens using native API.
        
        Args:
            text: Text to count tokens for
            
        Returns:
            Exact token count from Gemini API
        """
        if not self.is_available():
            return len(text) // 4
            
        try:
            # Use native count_tokens
            return self.client.count_tokens(text).total_tokens
        except Exception as e:
            logger.warning(f"Native token count failed, falling back to estimation: {e}")
            return len(text) // 4

