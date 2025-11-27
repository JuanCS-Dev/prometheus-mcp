"""
Gemini LLM Client for PROMETHEUS.

Supports:
- Gemini 2.0 Flash (default, fast)
- Gemini 2.0 Flash Thinking (extended reasoning)
- Streaming and non-streaming generation
- Retry with exponential backoff
"""

import os
import json
import asyncio
from dataclasses import dataclass, field
from typing import AsyncIterator, Optional, List, Dict, Any
from datetime import datetime
import httpx


@dataclass
class GenerationConfig:
    """Configuration for text generation."""
    temperature: float = 0.7
    top_p: float = 0.95
    top_k: int = 40
    max_output_tokens: int = 8192
    stop_sequences: List[str] = field(default_factory=list)


@dataclass
class Message:
    """A conversation message."""
    role: str  # "user" or "model"
    content: str
    timestamp: datetime = field(default_factory=datetime.now)


class GeminiClient:
    """
    Async Gemini API Client.

    Supports multiple models:
    - gemini-2.0-flash-exp: Fast, general purpose
    - gemini-2.0-flash-thinking-exp: Extended reasoning
    """

    BASE_URL = "https://generativelanguage.googleapis.com/v1beta"

    MODELS = {
        "flash": "gemini-2.0-flash-exp",
        "thinking": "gemini-2.0-flash-thinking-exp-1219",
        "pro": "gemini-1.5-pro",
    }

    def __init__(
        self,
        model: str = "flash",
        api_key: Optional[str] = None,
        config: Optional[GenerationConfig] = None,
    ):
        self.model_name = self.MODELS.get(model, model)
        self.api_key = api_key or os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
        self.config = config or GenerationConfig()
        self._client: Optional[httpx.AsyncClient] = None
        self.conversation_history: List[Message] = []

        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY or GEMINI_API_KEY environment variable required")

    async def _ensure_client(self):
        """Ensure HTTP client is initialized."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(120.0, connect=10.0),
                limits=httpx.Limits(max_connections=10),
            )

    async def close(self):
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    def _build_url(self, action: str = "generateContent") -> str:
        """Build API URL."""
        return f"{self.BASE_URL}/models/{self.model_name}:{action}?key={self.api_key}"

    def _build_payload(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        include_history: bool = False,
    ) -> dict:
        """Build request payload."""
        contents = []

        # Add conversation history if requested
        if include_history:
            for msg in self.conversation_history[-10:]:  # Last 10 messages
                contents.append({
                    "role": msg.role,
                    "parts": [{"text": msg.content}]
                })

        # Add current prompt
        contents.append({
            "role": "user",
            "parts": [{"text": prompt}]
        })

        payload = {
            "contents": contents,
            "generationConfig": {
                "temperature": self.config.temperature,
                "topP": self.config.top_p,
                "topK": self.config.top_k,
                "maxOutputTokens": self.config.max_output_tokens,
            }
        }

        # Add system instruction if provided
        if system_prompt:
            payload["systemInstruction"] = {
                "parts": [{"text": system_prompt}]
            }

        # Add stop sequences if any
        if self.config.stop_sequences:
            payload["generationConfig"]["stopSequences"] = self.config.stop_sequences

        return payload

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        include_history: bool = False,
        retry_count: int = 3,
    ) -> str:
        """
        Generate text completion.

        Args:
            prompt: The user prompt
            system_prompt: Optional system instructions
            include_history: Whether to include conversation history
            retry_count: Number of retries on failure

        Returns:
            Generated text
        """
        await self._ensure_client()

        url = self._build_url("generateContent")
        payload = self._build_payload(prompt, system_prompt, include_history)

        last_error = None
        for attempt in range(retry_count):
            try:
                response = await self._client.post(url, json=payload)

                if response.status_code == 200:
                    data = response.json()
                    text = self._extract_text(data)

                    # Store in history
                    self.conversation_history.append(Message(role="user", content=prompt))
                    self.conversation_history.append(Message(role="model", content=text))

                    return text

                elif response.status_code == 429:
                    # Rate limited, wait and retry
                    wait_time = 2 ** attempt
                    await asyncio.sleep(wait_time)
                    continue

                else:
                    last_error = f"API error {response.status_code}: {response.text}"

            except httpx.TimeoutException:
                last_error = "Request timeout"
                await asyncio.sleep(1)
                continue
            except Exception as e:
                last_error = str(e)
                await asyncio.sleep(1)
                continue

        raise RuntimeError(f"Failed after {retry_count} attempts: {last_error}")

    async def generate_stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        include_history: bool = False,
    ) -> AsyncIterator[str]:
        """
        Generate text with streaming.

        Yields text chunks as they are generated.
        """
        await self._ensure_client()

        url = self._build_url("streamGenerateContent")
        payload = self._build_payload(prompt, system_prompt, include_history)

        full_response = []

        async with self._client.stream("POST", url, json=payload) as response:
            if response.status_code != 200:
                error_text = await response.aread()
                raise RuntimeError(f"API error {response.status_code}: {error_text}")

            buffer = ""
            async for chunk in response.aiter_text():
                buffer += chunk

                # Parse SSE events
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    line = line.strip()

                    if line.startswith("data: "):
                        try:
                            data = json.loads(line[6:])
                            text = self._extract_text(data)
                            if text:
                                full_response.append(text)
                                yield text
                        except json.JSONDecodeError:
                            continue

        # Store complete response in history
        complete_text = "".join(full_response)
        self.conversation_history.append(Message(role="user", content=prompt))
        self.conversation_history.append(Message(role="model", content=complete_text))

    async def generate_with_thinking(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
    ) -> Dict[str, str]:
        """
        Generate with extended thinking (Gemini 2.0 Flash Thinking).

        Returns both the thinking process and final answer.
        """
        # Temporarily switch to thinking model
        original_model = self.model_name
        self.model_name = self.MODELS["thinking"]

        try:
            await self._ensure_client()

            url = self._build_url("generateContent")
            payload = self._build_payload(prompt, system_prompt)

            # Thinking model config
            payload["generationConfig"]["maxOutputTokens"] = 16384

            response = await self._client.post(url, json=payload)

            if response.status_code != 200:
                raise RuntimeError(f"API error {response.status_code}: {response.text}")

            data = response.json()

            # Extract thinking and response
            result = {"thinking": "", "response": ""}

            if "candidates" in data and data["candidates"]:
                candidate = data["candidates"][0]
                if "content" in candidate and "parts" in candidate["content"]:
                    for part in candidate["content"]["parts"]:
                        if "thought" in part:
                            result["thinking"] = part.get("thought", "")
                        elif "text" in part:
                            result["response"] = part.get("text", "")

            return result

        finally:
            self.model_name = original_model

    def _extract_text(self, data: dict) -> str:
        """Extract text from API response."""
        try:
            if "candidates" in data and data["candidates"]:
                candidate = data["candidates"][0]
                if "content" in candidate and "parts" in candidate["content"]:
                    parts = candidate["content"]["parts"]
                    texts = [p.get("text", "") for p in parts if "text" in p]
                    return "".join(texts)
        except (KeyError, IndexError):
            pass
        return ""

    def clear_history(self):
        """Clear conversation history."""
        self.conversation_history = []

    def get_history(self) -> List[Dict[str, str]]:
        """Get conversation history as list of dicts."""
        return [
            {"role": msg.role, "content": msg.content}
            for msg in self.conversation_history
        ]

    async def count_tokens(self, text: str) -> int:
        """Count tokens in text using Gemini API."""
        await self._ensure_client()

        url = f"{self.BASE_URL}/models/{self.model_name}:countTokens?key={self.api_key}"
        payload = {
            "contents": [{"parts": [{"text": text}]}]
        }

        response = await self._client.post(url, json=payload)

        if response.status_code == 200:
            data = response.json()
            return data.get("totalTokens", 0)

        return len(text) // 4  # Fallback estimate


# Convenience function
async def quick_generate(prompt: str, model: str = "flash") -> str:
    """Quick one-shot generation."""
    client = GeminiClient(model=model)
    try:
        return await client.generate(prompt)
    finally:
        await client.close()
