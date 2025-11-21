"""
Gradio ↔ CLI bridge with graceful fallbacks.

This module wraps the existing ShellBridge streaming API so the web UI can
display real-time output from the CLI without duplicating business logic.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, AsyncGenerator, Dict, Optional

import httpx

from .config import load_api_settings

try:
    from qwen_dev_cli.integration.shell_bridge import ShellBridge
except Exception:  # pragma: no cover - optional dependency during UI dev
    ShellBridge = None  # type: ignore

logger = logging.getLogger(__name__)


class CLIStreamBridge:
    """Adapter that exposes a simple async streaming interface."""

    def __init__(self) -> None:
        self._shell: Optional[ShellBridge] = None
        self._init_error: Optional[str] = None
        self._last_event: Optional[dict] = None

        self._api_settings = load_api_settings()
        self._api_client: Optional[httpx.AsyncClient] = None

        if self._api_settings.base_url:
            headers = {
                "User-Agent": "qwen-dev-cli-ui",
                "Accept": "text/event-stream, application/json",
            }
            if self._api_settings.api_token:
                headers["Authorization"] = f"Bearer {self._api_settings.api_token}"
            self._api_client = httpx.AsyncClient(
                base_url=self._api_settings.base_url,
                headers=headers,
                timeout=self._api_settings.request_timeout,
            )
            logger.info("Gradio UI configured for FastAPI backend at %s", self._api_settings.base_url)

        if ShellBridge is None and not self._api_settings.base_url:
            self._init_error = (
                "ShellBridge import failed – core CLI dependencies missing."
            )
            logger.warning(self._init_error)
            return

        if ShellBridge is not None:
            try:
                self._shell = ShellBridge()
                logger.info("ShellBridge initialized for Gradio UI")
            except Exception as exc:  # pragma: no cover - defensive
                self._init_error = f"ShellBridge init error: {exc}"
                logger.exception(self._init_error)

    @property
    def available(self) -> bool:
        """Return True when either FastAPI or local ShellBridge is ready."""
        return bool(self._api_client or self._shell)

    @property
    def backend_label(self) -> str:
        if self._api_client:
            return "fastapi"
        if self._shell:
            return "shell"
        return "demo"

    @property
    def api_base_display(self) -> str:
        if self._api_client:
            return self._api_settings.base_url or "FastAPI bridge"
        if self._shell:
            return "local shell"
        return "fallback"

    async def stream_command(
        self,
        command: str,
        session_id: Optional[str] = None,
    ) -> AsyncGenerator[str, None]:
        """
        Stream command execution output.

        Prefers the FastAPI backend when configured, falls back to local shell,
        and ultimately to an echo mode so the UI remains testable without the
        backend.
        """
        trimmed = (command or "").strip()
        if not trimmed:
            yield "⚠️  Please enter a command."
            return

        if self._api_client:
            try:
                async for chunk in self._stream_via_http(trimmed, session_id):
                    yield chunk
                return
            except Exception as exc:
                logger.error("HTTP backend stream failed: %s", exc)
                yield f"⚠️ FastAPI backend unavailable: {exc}\n"
                if not self._shell:
                    async for chunk in self._fallback_stream(trimmed):
                        yield chunk
                    return

        if self._shell is not None:
            async for chunk in self._shell.process_input(
                user_input=trimmed,
                session_id=session_id,
                context=None,
            ):
                yield chunk
            return

        async for chunk in self._fallback_stream(trimmed):
            yield chunk

    async def get_status(self, session_id: Optional[str]) -> Optional[Dict[str, Any]]:
        """Fetch latest status/metrics from whichever backend is active."""
        if self._api_client:
            params = {}
            if session_id:
                params["session_id"] = session_id
            try:
                resp = await self._api_client.get("/api/status", params=params or None)
                resp.raise_for_status()
                data = resp.json()
            except Exception as exc:
                logger.debug("FastAPI status fetch failed: %s", exc)
                return None
            data.setdefault("backend", "fastapi")
            return data

        if self._shell:
            usage = (
                self._shell.token_tracker.get_usage()
                if hasattr(self._shell, "token_tracker")
                else None
            )
            return {
                "backend": "shell",
                "status": "ready" if self._shell else "unknown",
                "tokens": usage,
                "session_id": session_id,
            }

        return None

    async def _stream_via_http(
        self,
        command: str,
        session_id: Optional[str],
    ) -> AsyncGenerator[str, None]:
        """Stream command output from FastAPI /api/execute endpoint."""
        if not self._api_client:
            raise RuntimeError("HTTP client not configured")

        payload = {"command": command}
        if session_id:
            payload["session_id"] = session_id

        async with self._api_client.stream("POST", "/api/execute", json=payload) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if not line:
                    continue

                message = self._parse_http_chunk(line)
                if message:
                    yield message

    def _parse_http_chunk(self, raw_line: str) -> str:
        """Normalize SSE/JSON chunks to plain text for the UI."""
        line = raw_line.strip()
        if not line:
            return ""

        if line.startswith("data:"):
            line = line[5:].strip()

        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            return line

        self._last_event = payload
        segments: list[str] = []

        for key in ("message", "stdout", "stderr", "tool_output", "result"):
            value = payload.get(key)
            if value:
                segments.append(str(value))

        if not segments and "status" in payload:
            segments.append(f"status: {payload['status']}")

        if not segments:
            return json.dumps(payload, ensure_ascii=False)

        return "\n".join(segments).strip()

    async def _fallback_stream(self, command: str) -> AsyncGenerator[str, None]:
        """Development fallback when no backend is available."""
        if self._init_error:
            yield f"ℹ️  CLI backend offline: {self._init_error}\n"
        yield f"🚀 Executing: {command}\n"
        await asyncio.sleep(0.15)
        yield "🧠 Thinking about the best strategy...\n"
        await asyncio.sleep(0.2)
        yield (
            "✅ Done! (demo mode)\n\n"
            "When the full CLI backend is wired, this stream will show\n"
            "real-time output from the InteractiveShell."
        )

