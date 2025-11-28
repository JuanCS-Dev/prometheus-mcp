"""
SDK Client.

SCALE & SUSTAIN Phase 2.3 - SDK Client.

Main client for interacting with Juan Dev Code.

Author: JuanCS Dev
Date: 2025-11-26
"""

import logging
from typing import AsyncIterator, Optional, Dict, List, Any

from .types import Message, ToolResult, SDKConfig

logger = logging.getLogger(__name__)


class JuanDevClient:
    """
    SDK client for Juan Dev Code integration.

    Usage:
        # Async context manager (recommended)
        async with JuanDevClient() as client:
            async for chunk in client.chat("explain this code"):
                print(chunk, end="")

        # Manual lifecycle
        client = JuanDevClient(api_key="...")
        await client.connect()
        result = await client.execute_tool("read_file", path="main.py")
        await client.close()
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "http://localhost:8080",
        config: Optional[SDKConfig] = None,
    ):
        """
        Initialize client.

        Args:
            api_key: API key for authentication
            base_url: Base URL of Juan Dev server
            config: Full configuration object (overrides other args)
        """
        if config:
            self._config = config
        else:
            self._config = SDKConfig(
                api_key=api_key,
                base_url=base_url,
            )

        self._session = None
        self._connected = False

    async def __aenter__(self) -> 'JuanDevClient':
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.close()

    async def connect(self) -> None:
        """Establish connection to server."""
        try:
            import httpx
            self._session = httpx.AsyncClient(
                base_url=self._config.base_url,
                timeout=self._config.timeout,
                verify=self._config.verify_ssl,
            )
            self._connected = True
            logger.info(f"Connected to {self._config.base_url}")
        except ImportError:
            raise ImportError("httpx is required. Install with: pip install httpx")

    async def close(self) -> None:
        """Close connection."""
        if self._session:
            await self._session.aclose()
            self._session = None
        self._connected = False

    @property
    def is_connected(self) -> bool:
        """Check if connected."""
        return self._connected

    def _get_headers(self) -> Dict[str, str]:
        """Get request headers."""
        headers = {"Content-Type": "application/json"}
        if self._config.api_key:
            headers["Authorization"] = f"Bearer {self._config.api_key}"
        return headers

    async def chat(
        self,
        message: str,
        agent: Optional[str] = None,
        tools: Optional[List[str]] = None,
        history: Optional[List[Message]] = None,
    ) -> AsyncIterator[str]:
        """
        Stream chat with optional agent and tool selection.

        Args:
            message: User message
            agent: Specific agent to use (optional)
            tools: List of tools to enable (optional)
            history: Conversation history (optional)

        Yields:
            Response text chunks
        """
        if not self._connected:
            await self.connect()

        payload = {
            "message": message,
            "stream": True,
        }
        if agent:
            payload["agent"] = agent
        if tools:
            payload["tools"] = tools
        if history:
            payload["history"] = [
                {"role": m.role.value, "content": m.content}
                for m in history
            ]

        try:
            async with self._session.stream(
                "POST",
                "/api/v1/chat",
                json=payload,
                headers=self._get_headers(),
            ) as response:
                response.raise_for_status()
                async for chunk in response.aiter_text():
                    yield chunk
        except Exception as e:
            logger.error(f"Chat error: {e}")
            raise

    async def chat_complete(
        self,
        message: str,
        **kwargs
    ) -> str:
        """
        Get complete chat response (non-streaming).

        Args:
            message: User message
            **kwargs: Additional arguments for chat()

        Returns:
            Complete response text
        """
        chunks = []
        async for chunk in self.chat(message, **kwargs):
            chunks.append(chunk)
        return "".join(chunks)

    async def execute_tool(
        self,
        tool_name: str,
        **params
    ) -> ToolResult:
        """
        Execute a tool directly.

        Args:
            tool_name: Name of tool to execute
            **params: Tool parameters

        Returns:
            Tool execution result
        """
        if not self._connected:
            await self.connect()

        payload = {
            "tool": tool_name,
            "parameters": params,
        }

        try:
            response = await self._session.post(
                "/api/v1/tools/execute",
                json=payload,
                headers=self._get_headers(),
            )
            response.raise_for_status()
            data = response.json()
            return ToolResult(
                success=data.get("success", False),
                data=data.get("data", {}),
                error=data.get("error"),
            )
        except Exception as e:
            logger.error(f"Tool execution error: {e}")
            return ToolResult(success=False, error=str(e))

    async def list_tools(self) -> List[str]:
        """Get list of available tools."""
        if not self._connected:
            await self.connect()

        try:
            response = await self._session.get(
                "/api/v1/tools",
                headers=self._get_headers(),
            )
            response.raise_for_status()
            return response.json().get("tools", [])
        except Exception as e:
            logger.error(f"List tools error: {e}")
            return []

    async def list_agents(self) -> List[Dict[str, Any]]:
        """Get list of available agents."""
        if not self._connected:
            await self.connect()

        try:
            response = await self._session.get(
                "/api/v1/agents",
                headers=self._get_headers(),
            )
            response.raise_for_status()
            return response.json().get("agents", [])
        except Exception as e:
            logger.error(f"List agents error: {e}")
            return []

    async def health_check(self) -> bool:
        """Check server health."""
        if not self._connected:
            await self.connect()

        try:
            response = await self._session.get("/health")
            return response.status_code == 200
        except Exception:
            return False


__all__ = ['JuanDevClient']
