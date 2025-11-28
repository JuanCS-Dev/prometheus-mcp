"""
Test suite for CLIStreamBridge async adapter.

Validates async streaming patterns, error handling, and backend fallback logic.
"""
from __future__ import annotations

import pytest

from gradio_ui.cli_bridge import CLIStreamBridge


class TestCLIStreamBridgeInitialization:
    """Test bridge initialization and availability checks."""

    def test_bridge_initializes(self) -> None:
        """Bridge can be instantiated without errors."""
        bridge = CLIStreamBridge()
        assert bridge is not None

    def test_backend_label_property(self) -> None:
        """Backend label returns valid string."""
        bridge = CLIStreamBridge()
        label = bridge.backend_label

        assert isinstance(label, str)
        assert label in {"fastapi", "shell", "demo"}

    def test_api_base_display_property(self) -> None:
        """API base display returns descriptive string."""
        bridge = CLIStreamBridge()
        display = bridge.api_base_display

        assert isinstance(display, str)
        assert len(display) > 0


class TestStreamCommandFallback:
    """Test fallback streaming when no backend is available."""

    @pytest.mark.asyncio
    async def test_fallback_stream_returns_chunks(self) -> None:
        """Fallback stream yields text chunks."""
        bridge = CLIStreamBridge()

        chunks = []
        async for chunk in bridge.stream_command("test command", None):
            chunks.append(chunk)

        # Should yield multiple chunks
        assert len(chunks) > 0

        # Chunks should be non-empty strings
        assert all(isinstance(c, str) for c in chunks)
        assert all(len(c) > 0 for c in chunks)

    @pytest.mark.asyncio
    async def test_stream_produces_output(self) -> None:
        """Stream produces non-empty output for valid command."""
        bridge = CLIStreamBridge()

        test_cmd = "echo test"  # Simple command
        full_output = ""

        async for chunk in bridge.stream_command(test_cmd, None):
            full_output += chunk

        # Should produce SOME output (fallback or real backend)
        assert len(full_output) > 0
        assert isinstance(full_output, str)

    @pytest.mark.asyncio
    async def test_empty_command_warning(self) -> None:
        """Empty or whitespace-only commands produce warning."""
        bridge = CLIStreamBridge()

        # Test empty string
        chunks_empty = []
        async for chunk in bridge.stream_command("", None):
            chunks_empty.append(chunk)

        assert len(chunks_empty) > 0
        assert "⚠️" in "".join(chunks_empty)

        # Test whitespace
        chunks_ws = []
        async for chunk in bridge.stream_command("   ", None):
            chunks_ws.append(chunk)

        assert len(chunks_ws) > 0
        assert "⚠️" in "".join(chunks_ws)


class TestParseHTTPChunk:
    """Test SSE/JSON parsing logic."""

    def test_parse_sse_data_prefix(self) -> None:
        """SSE lines with 'data:' prefix are parsed correctly."""
        bridge = CLIStreamBridge()

        # SSE format with JSON payload
        raw_line = 'data: {"message": "Hello world"}'
        result = bridge._parse_http_chunk(raw_line)

        assert "Hello world" in result

    def test_parse_plain_json(self) -> None:
        """Plain JSON lines are parsed correctly."""
        bridge = CLIStreamBridge()

        raw_line = '{"message": "Test message", "status": "ok"}'
        result = bridge._parse_http_chunk(raw_line)

        assert "Test message" in result

    def test_parse_non_json(self) -> None:
        """Non-JSON text is returned as-is."""
        bridge = CLIStreamBridge()

        raw_line = "Plain text output"
        result = bridge._parse_http_chunk(raw_line)

        assert result == "Plain text output"

    def test_parse_empty_line(self) -> None:
        """Empty lines return empty string."""
        bridge = CLIStreamBridge()

        result = bridge._parse_http_chunk("")
        assert result == ""

        result_ws = bridge._parse_http_chunk("   ")
        assert result_ws == ""

    def test_parse_multiple_fields(self) -> None:
        """Multiple message fields are combined."""
        bridge = CLIStreamBridge()

        raw_line = '{"message": "Line 1", "stdout": "Line 2"}'
        result = bridge._parse_http_chunk(raw_line)

        assert "Line 1" in result
        assert "Line 2" in result

    def test_parse_status_fallback(self) -> None:
        """Status field used when no content fields present."""
        bridge = CLIStreamBridge()

        raw_line = '{"status": "processing"}'
        result = bridge._parse_http_chunk(raw_line)

        assert "status" in result.lower()
        assert "processing" in result


@pytest.mark.asyncio
class TestAsyncSafety:
    """Test async patterns are safe for Gradio/Uvicorn."""

    async def test_stream_is_async_generator(self) -> None:
        """stream_command returns proper AsyncGenerator."""
        bridge = CLIStreamBridge()

        stream = bridge.stream_command("test", None)

        # Should be an async generator
        assert hasattr(stream, "__anext__")
        assert hasattr(stream, "asend")

    async def test_multiple_concurrent_streams(self) -> None:
        """Bridge supports multiple concurrent streams (session isolation)."""
        bridge = CLIStreamBridge()

        # Start two streams with different sessions
        stream1 = bridge.stream_command("cmd1", "session-1")
        stream2 = bridge.stream_command("cmd2", "session-2")

        # Both should yield independently
        chunk1 = await stream1.__anext__()
        chunk2 = await stream2.__anext__()

        assert isinstance(chunk1, str)
        assert isinstance(chunk2, str)
