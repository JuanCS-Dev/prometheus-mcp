"""
Gemini Streaming Module - Unified Streaming Strategies
======================================================

Extracted from llm_client.py as part of SCALE & SUSTAIN refactoring.

Provides streaming support for Gemini API with:
- SDK-based streaming (google-generativeai)
- HTTP-based streaming (httpx SSE fallback)
- Timeout protection with chunk stall detection
- Tool call marker generation

Author: JuanCS Dev
Date: 2025-11-27
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from dataclasses import dataclass
from typing import Any, AsyncIterator, Dict, List, Optional

logger = logging.getLogger(__name__)


# =============================================================================
# SHARED CONSTANTS
# =============================================================================

# Anti-repetition and table formatting suffix added to all system prompts
# Based on: https://ai.google.dev/gemini-api/docs/troubleshooting
# NOTE: This supplements the main agentic_prompt.py instructions
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


# =============================================================================
# CONFIGURATION
# =============================================================================

@dataclass
class GeminiStreamConfig:
    """Configuration for Gemini streaming."""
    model_name: str = "gemini-2.0-flash"
    api_key: str = ""
    temperature: float = 1.0
    max_output_tokens: int = 8192
    top_p: float = 0.95
    top_k: int = 40
    init_timeout: float = 10.0
    stream_timeout: float = 60.0
    chunk_timeout: float = 30.0

    def __post_init__(self) -> None:
        """Validate configuration."""
        if self.temperature < 0 or self.temperature > 2:
            raise ValueError("temperature must be between 0 and 2")
        if self.max_output_tokens < 1:
            raise ValueError("max_output_tokens must be >= 1")
        if self.init_timeout <= 0:
            raise ValueError("init_timeout must be > 0")


# =============================================================================
# BASE STREAMER PROTOCOL
# =============================================================================

class BaseStreamer:
    """Base class for streaming implementations."""

    def __init__(self, config: GeminiStreamConfig):
        self.config = config
        self._initialized = False

    async def initialize(self) -> bool:
        """Initialize the streamer. Returns True if successful."""
        raise NotImplementedError

    async def stream(
        self,
        prompt: str,
        system_prompt: str = "",
        context: Optional[List[Dict[str, str]]] = None,
        tools: Optional[List[Any]] = None,
    ) -> AsyncIterator[str]:
        """Stream response chunks."""
        raise NotImplementedError
        yield  # Make this a generator

    @property
    def is_initialized(self) -> bool:
        """Check if streamer is initialized."""
        return self._initialized


# =============================================================================
# SDK STREAMER - Optimized for Gemini 2.5+ (Nov 2025)
# =============================================================================
#
# CRITICAL FIXES based on Google DeepMind documentation:
# 1. Temperature MUST be 1.0 for Gemini 2.5+ to avoid looping/repetition
# 2. system_instruction MUST be passed natively to GenerativeModel
# 3. Never fake system prompts as [System] user messages
#
# Sources:
# - https://ai.google.dev/gemini-api/docs/text-generation
# - https://ai.google.dev/gemini-api/docs/troubleshooting
# =============================================================================

class GeminiSDKStreamer(BaseStreamer):
    """
    Streamer using google-generativeai SDK.

    OPTIMIZED for Gemini 2.5+ (Nov 2025):
    - Uses native system_instruction parameter
    - Temperature locked at 1.0 to prevent looping
    - Anti-repetition instructions embedded
    """

    def __init__(self, config: GeminiStreamConfig):
        super().__init__(config)
        self._genai = None  # google.generativeai module
        self._generation_config = None
        self._cached_system_prompt: Optional[str] = None
        self._model = None

    async def initialize(self) -> bool:
        """Initialize the Gemini SDK."""
        if self._initialized:
            return True

        try:
            import google.generativeai as genai
            self._genai = genai
            genai.configure(api_key=self.config.api_key)

            # CRITICAL: Temperature MUST be 1.0 for Gemini 2.5+
            # Setting below 1.0 causes looping/repetition per Google docs
            safe_temperature = 1.0
            if self.config.temperature != 1.0:
                logger.warning(
                    f"Temperature {self.config.temperature} overridden to 1.0 "
                    "to prevent Gemini 2.5+ looping behavior"
                )

            self._generation_config = genai.GenerationConfig(
                temperature=safe_temperature,
                max_output_tokens=self.config.max_output_tokens,
                top_p=self.config.top_p,
                top_k=self.config.top_k,
            )

            self._initialized = True
            logger.info(
                f"GeminiSDKStreamer initialized: model={self.config.model_name}, "
                f"temperature=1.0 (forced), max_tokens={self.config.max_output_tokens}"
            )
            return True

        except ImportError as e:
            logger.warning(f"google-generativeai not available: {e}")
            return False
        except Exception as e:
            logger.error(f"SDK initialization failed: {e}")
            return False

    def _get_model_with_system_instruction(self, system_prompt: str):
        """
        Get or create model with native system_instruction.

        Uses caching to avoid recreating model for same system prompt.
        """
        # Add anti-repetition instructions (use module-level constant)
        full_system_prompt = system_prompt + GEMINI_OUTPUT_RULES if system_prompt else ""

        # Check if we need to create new model (system prompt changed)
        if self._model is None or self._cached_system_prompt != full_system_prompt:
            self._cached_system_prompt = full_system_prompt

            # Create model with native system_instruction
            self._model = self._genai.GenerativeModel(
                self.config.model_name,
                generation_config=self._generation_config,
                system_instruction=full_system_prompt if full_system_prompt else None,
            )
            logger.debug(f"Created model with system_instruction ({len(full_system_prompt)} chars)")

        return self._model

    async def stream(
        self,
        prompt: str,
        system_prompt: str = "",
        context: Optional[List[Dict[str, str]]] = None,
        tools: Optional[List[Any]] = None,
    ) -> AsyncIterator[str]:
        """Stream using google-generativeai SDK with native system_instruction."""
        if not self._initialized:
            yield "❌ SDK not initialized"
            return

        from jdev_tui.core.streaming.soft_buffer import SoftBuffer
        soft_buffer = SoftBuffer()

        # Get model with proper system instruction
        model = self._get_model_with_system_instruction(system_prompt)

        # Build contents for conversation (WITHOUT system prompt - it's native now)
        contents = self._build_contents(prompt, context)

        # Run in executor since SDK is sync
        loop = asyncio.get_event_loop()

        def _generate():
            kwargs = {"stream": True}
            if tools:
                kwargs["tools"] = tools
            return model.generate_content(
                contents if len(contents) > 1 else prompt,
                **kwargs
            )

        try:
            # 1. Start Request (Threaded)
            response = await loop.run_in_executor(None, _generate)
            response_iterator = iter(response)

            # 2. Iterate Chunks (Threaded to prevent UI freeze)
            def _next_chunk():
                try:
                    return next(response_iterator)
                except StopIteration:
                    return None
                except Exception as e:
                    return e

            while True:
                # Offload the blocking next() call
                chunk = await loop.run_in_executor(None, _next_chunk)
                
                if chunk is None:
                    break
                if isinstance(chunk, Exception):
                    raise chunk

                # 3. Process Chunk
                async for text in self._process_chunk(chunk):
                    # Apply Soft Buffering
                    safe_text = soft_buffer.feed(text)
                    if safe_text:
                        yield safe_text
                
                await asyncio.sleep(0)  # Yield control for UI
            
            # Flush remaining buffer
            remaining = soft_buffer.flush()
            if remaining:
                yield remaining

        except Exception as e:
            logger.error(f"SDK streaming error: {e}")
            yield f"\n❌ Streaming error: {str(e)}"

    def _build_contents(
        self,
        prompt: str,
        context: Optional[List[Dict[str, str]]],
    ) -> List[Dict[str, Any]]:
        """
        Build contents array for multi-turn conversation.

        NOTE: System prompt is now passed via native system_instruction,
        NOT as a fake user message. This prevents repetition issues.
        """
        contents: List[Dict[str, Any]] = []

        # Add conversation context if provided
        if context:
            for msg in context:
                role = "user" if msg.get("role") == "user" else "model"
                contents.append({
                    "role": role,
                    "parts": [{"text": msg.get("content", "")}]
                })

        # Add current prompt
        contents.append({"role": "user", "parts": [{"text": prompt}]})

        return contents

    async def _process_chunk(self, chunk: Any) -> AsyncIterator[str]:
        """Process a single response chunk."""
        # Check for function calls and text in candidates
        if hasattr(chunk, 'candidates') and chunk.candidates:
            for candidate in chunk.candidates:
                if hasattr(candidate, 'content') and candidate.content:
                    for part in candidate.content.parts:
                        # Handle function call
                        if hasattr(part, 'function_call') and part.function_call:
                            fc = part.function_call
                            name = fc.name
                            args = dict(fc.args) if hasattr(fc.args, 'items') else {}
                            yield f"[TOOL_CALL:{name}:{json.dumps(args)}]"

                        # Handle text
                        elif hasattr(part, 'text') and part.text:
                            yield part.text

        # Fallback: direct text access
        elif hasattr(chunk, 'text') and chunk.text:
            yield chunk.text


# =============================================================================
# HTTPX STREAMER - Optimized for Gemini 2.5+ (Nov 2025)
# =============================================================================

class GeminiHTTPXStreamer(BaseStreamer):
    """
    Streamer using httpx direct API call with SSE.

    OPTIMIZED for Gemini 2.5+ (Nov 2025):
    - Uses systemInstruction in API payload (native)
    - Temperature locked at 1.0 to prevent looping
    - Anti-repetition instructions embedded
    """

    def __init__(self, config: GeminiStreamConfig):
        super().__init__(config)
        self._client = None

    async def initialize(self) -> bool:
        """Initialize httpx client."""
        if self._initialized:
            return True

        try:
            import httpx
            self._client = httpx.AsyncClient(timeout=self.config.stream_timeout)
            self._initialized = True
            logger.info("GeminiHTTPXStreamer initialized")
            return True

        except ImportError as e:
            logger.warning(f"httpx not available: {e}")
            return False
        except Exception as e:
            logger.error(f"HTTPX initialization failed: {e}")
            return False

    async def stream(
        self,
        prompt: str,
        system_prompt: str = "",
        context: Optional[List[Dict[str, str]]] = None,
        tools: Optional[List[Any]] = None,
    ) -> AsyncIterator[str]:
        """Stream using httpx direct API call with native systemInstruction."""
        if not self._initialized:
            yield "❌ HTTPX not initialized"
            return

        import httpx

        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self.config.model_name}:streamGenerateContent?key={self.config.api_key}"
        )

        # Build contents (WITHOUT system prompt - it goes in systemInstruction)
        contents = self._build_contents(prompt, context)

        # Build full system instruction with anti-repetition rules
        full_system_instruction = ""
        if system_prompt:
            full_system_instruction = system_prompt + GEMINI_OUTPUT_RULES

        # CRITICAL: Temperature MUST be 1.0 for Gemini 2.5+
        payload = {
            "contents": contents,
            "generationConfig": {
                "temperature": 1.0,  # FORCED to prevent looping
                "maxOutputTokens": self.config.max_output_tokens,
                "topP": self.config.top_p,
                "topK": self.config.top_k,
            }
        }

        # Add native systemInstruction if provided
        if full_system_instruction:
            payload["systemInstruction"] = {
                "parts": [{"text": full_system_instruction}]
            }

        try:
            async with httpx.AsyncClient(timeout=self.config.stream_timeout) as client:
                async with client.stream("POST", url, json=payload) as response:
                    if response.status_code != 200:
                        error_text = await response.aread()
                        yield f"❌ API error {response.status_code}: {error_text.decode()[:200]}"
                        return

                    buffer = ""
                    async for chunk in response.aiter_bytes():
                        buffer += chunk.decode("utf-8", errors="ignore")

                        # Parse SSE events
                        while "\n" in buffer:
                            line, buffer = buffer.split("\n", 1)
                            line = line.strip()

                            if not line:
                                continue

                            # Handle JSON array format from Gemini
                            if line.startswith("[") or line.startswith("{"):
                                text = self._parse_sse_line(line)
                                if text:
                                    yield text

        except httpx.TimeoutException:
            yield f"\n⚠️ Request timed out after {self.config.stream_timeout}s"
        except Exception as e:
            logger.error(f"HTTPX streaming error: {e}")
            yield f"\n❌ Streaming error: {str(e)}"

    def _build_contents(
        self,
        prompt: str,
        context: Optional[List[Dict[str, str]]],
    ) -> List[Dict[str, Any]]:
        """
        Build contents array for API request.

        NOTE: System prompt is now passed via systemInstruction in payload,
        NOT as a fake user message.
        """
        contents: List[Dict[str, Any]] = []

        if context:
            for msg in context:
                role = "user" if msg.get("role") == "user" else "model"
                contents.append({
                    "role": role,
                    "parts": [{"text": msg.get("content", "")}]
                })

        contents.append({"role": "user", "parts": [{"text": prompt}]})

        return contents

    def _parse_sse_line(self, line: str) -> Optional[str]:
        """Parse an SSE line and extract text."""
        try:
            data = json.loads(line.rstrip(","))
            if isinstance(data, list):
                data = data[0] if data else {}

            if "candidates" in data:
                text = (
                    data["candidates"][0]
                    .get("content", {})
                    .get("parts", [{}])[0]
                    .get("text", "")
                )
                return text if text else None

        except json.JSONDecodeError:
            pass

        return None


# =============================================================================
# UNIFIED STREAMER WITH TIMEOUT
# =============================================================================

class GeminiStreamer:
    """
    Unified Gemini streamer with automatic fallback.

    Tries SDK first, falls back to HTTPX if SDK unavailable.
    Includes timeout protection and chunk stall detection.

    Usage:
        config = GeminiStreamConfig(api_key="...", model_name="gemini-2.0-flash")
        streamer = GeminiStreamer(config)
        await streamer.initialize()

        async for chunk in streamer.stream("Hello!"):
            print(chunk, end="", flush=True)
    """

    def __init__(self, config: GeminiStreamConfig):
        self.config = config
        self._sdk_streamer = GeminiSDKStreamer(config)
        self._httpx_streamer = GeminiHTTPXStreamer(config)
        self._active_streamer: Optional[BaseStreamer] = None

    async def initialize(self) -> bool:
        """
        Initialize streamers with automatic fallback.

        Tries SDK first, falls back to HTTPX if unavailable.
        """
        try:
            # Apply timeout to initialization
            if await asyncio.wait_for(
                self._sdk_streamer.initialize(),
                timeout=self.config.init_timeout
            ):
                self._active_streamer = self._sdk_streamer
                logger.info("Using SDK streamer")
                return True
        except asyncio.TimeoutError:
            logger.warning("SDK initialization timed out")
        except Exception as e:
            logger.warning(f"SDK initialization failed: {e}")

        # Try HTTPX fallback
        try:
            if await asyncio.wait_for(
                self._httpx_streamer.initialize(),
                timeout=self.config.init_timeout
            ):
                self._active_streamer = self._httpx_streamer
                logger.info("Using HTTPX streamer (fallback)")
                return True
        except asyncio.TimeoutError:
            logger.warning("HTTPX initialization timed out")
        except Exception as e:
            logger.error(f"HTTPX initialization failed: {e}")

        return False

    @property
    def is_initialized(self) -> bool:
        """Check if any streamer is initialized."""
        return self._active_streamer is not None and self._active_streamer.is_initialized

    async def stream(
        self,
        prompt: str,
        system_prompt: str = "",
        context: Optional[List[Dict[str, str]]] = None,
        tools: Optional[List[Any]] = None,
    ) -> AsyncIterator[str]:
        """
        Stream response with timeout protection.

        Includes chunk stall detection - if no chunks received for
        chunk_timeout seconds, raises TimeoutError.
        """
        if not self._active_streamer:
            yield "❌ Streamer not initialized"
            return

        last_chunk_time = time.time()

        try:
            async for chunk in self._active_streamer.stream(
                prompt, system_prompt, context, tools
            ):
                current_time = time.time()

                # Check for chunk timeout (stall detection)
                if current_time - last_chunk_time > self.config.chunk_timeout:
                    raise asyncio.TimeoutError(
                        f"No response for {self.config.chunk_timeout}s"
                    )

                last_chunk_time = current_time
                yield chunk

        except asyncio.TimeoutError as e:
            yield f"\n⚠️ {str(e)}"
            raise


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    "GEMINI_OUTPUT_RULES",
    "GeminiStreamConfig",
    "BaseStreamer",
    "GeminiSDKStreamer",
    "GeminiHTTPXStreamer",
    "GeminiStreamer",
]
