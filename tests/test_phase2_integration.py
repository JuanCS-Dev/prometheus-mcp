"""Tests for Phase 2.1 - Parser → Shell Integration.

Tests the complete pipeline:
- Safety validation
- Session management  
- Shell bridge execution
- End-to-end integration
"""

import pytest
import os
import tempfile
from pathlib import Path

from jdev_cli.integration import (
    SafetyValidator,
    SessionManager,
    ShellBridge,
)


class TestSafetyValidator:
    """Test safety validation system (Claude Code strategy)."""

    def test_detects_dangerous_rm_rf(self):
        """Should block rm -rf /"""
        validator = SafetyValidator()

        tool_call = {
            "tool": "bash_command",
            "arguments": {"command": "rm -rf /"}
        }

        is_safe, reason = validator.is_safe(tool_call)
        assert not is_safe
        assert "root directory" in reason.lower()

    def test_detects_fork_bomb(self):
        """Should block fork bomb."""
        validator = SafetyValidator()

        tool_call = {
            "tool": "bash_command",
            "arguments": {"command": ":(){ :|:& };:"}
        }

        is_safe, reason = validator.is_safe(tool_call)
        assert not is_safe
        assert "fork bomb" in reason.lower()

    def test_allows_safe_commands(self):
        """Should allow safe commands."""
        validator = SafetyValidator()

        tool_call = {
            "tool": "bash_command",
            "arguments": {"command": "ls -la"}
        }

        is_safe, reason = validator.is_safe(tool_call)
        assert is_safe
        assert reason is None

    def test_blocks_path_traversal(self):
        """Should block path traversal attempts."""
        validator = SafetyValidator(allowed_paths=["/tmp/test"])

        tool_call = {
            "tool": "write_file",
            "arguments": {"path": "/etc/passwd", "content": "hack"}
        }

        is_safe, reason = validator.is_safe(tool_call)
        assert not is_safe

    def test_respects_whitelist(self):
        """Should respect command whitelist."""
        validator = SafetyValidator()

        # Git commands should be whitelisted
        tool_call = {
            "tool": "bash_command",
            "arguments": {"command": "git status"}
        }

        is_safe, reason = validator.is_safe(tool_call)
        assert is_safe

    def test_file_size_limit(self):
        """Should enforce file size limits."""
        # Create validator allowing /tmp
        validator = SafetyValidator(max_file_size=100, allowed_paths=["/tmp"])

        # Create a large temp file
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"x" * 200)
            large_file = f.name

        try:
            tool_call = {
                "tool": "read_file",
                "arguments": {"path": large_file}
            }

            is_safe, reason = validator.is_safe(tool_call)
            assert not is_safe
            assert "too large" in reason.lower()
        finally:
            os.unlink(large_file)

    def test_can_add_whitelist_command(self):
        """Should allow adding commands to whitelist."""
        validator = SafetyValidator()

        validator.add_whitelisted_command("my_custom_script")

        tool_call = {
            "tool": "bash_command",
            "arguments": {"command": "my_custom_script --flag"}
        }

        is_safe, reason = validator.is_safe(tool_call)
        assert is_safe


class TestSessionManager:
    """Test session management (Codex PTY strategy)."""

    def test_creates_session(self):
        """Should create new session."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = SessionManager(storage_dir=Path(tmpdir))

            session = manager.create_session("test_session")

            assert session.session_id == "test_session"
            assert session.cwd == os.getcwd()
            assert "test_session" in manager.sessions

    def test_get_or_create(self):
        """Should get existing or create new session."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = SessionManager(storage_dir=Path(tmpdir))

            session1 = manager.get_or_create_session("test")
            session2 = manager.get_or_create_session("test")

            assert session1 is session2

    def test_tracks_history(self):
        """Should track action history."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = SessionManager(storage_dir=Path(tmpdir))
            session = manager.create_session("test")

            session.add_history("tool_call", {"tool": "read_file"}, result="success")

            assert len(session.history) == 1
            assert session.history[0]["action"] == "tool_call"

    def test_tracks_file_operations(self):
        """Should track file read/write/delete."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = SessionManager(storage_dir=Path(tmpdir))
            session = manager.create_session("test")

            session.track_file_operation("read", "/tmp/file1.txt")
            session.track_file_operation("write", "/tmp/file2.txt")
            session.track_file_operation("delete", "/tmp/file3.txt")

            assert len(session.read_files) == 1
            assert len(session.modified_files) == 1
            assert len(session.deleted_files) == 1

    def test_saves_and_loads_session(self):
        """Should persist sessions to disk."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create and save session
            manager1 = SessionManager(storage_dir=Path(tmpdir))
            session1 = manager1.create_session("persist_test")
            session1.add_history("test", {"data": "value"})
            manager1.save_all_sessions()

            # Load in new manager
            manager2 = SessionManager(storage_dir=Path(tmpdir))
            session2 = manager2.get_session("persist_test")

            assert session2 is not None
            assert len(session2.history) == 1

    def test_lists_sessions(self):
        """Should list all sessions."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = SessionManager(storage_dir=Path(tmpdir))

            manager.create_session("session1")
            manager.create_session("session2")

            sessions = manager.list_sessions()

            assert len(sessions) == 2
            assert any(s["session_id"] == "session1" for s in sessions)

    def test_deletes_session(self):
        """Should delete session and its data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = SessionManager(storage_dir=Path(tmpdir))

            session = manager.create_session("to_delete")
            session_file = Path(tmpdir) / "to_delete.json"

            # Verify file exists
            manager.save_all_sessions()
            assert session_file.exists()

            # Delete
            manager.delete_session("to_delete")

            assert "to_delete" not in manager.sessions
            assert not session_file.exists()


class TestShellBridge:
    """Test shell bridge integration (full pipeline)."""

    @pytest.mark.asyncio
    async def test_initialization(self):
        """Should initialize with all components."""
        bridge = ShellBridge()

        assert bridge.parser is not None
        assert bridge.llm is not None
        assert bridge.registry is not None
        assert bridge.safety is not None
        assert bridge.sessions is not None

    @pytest.mark.asyncio
    async def test_blocks_unsafe_tools(self):
        """Should block unsafe tool calls."""
        # Create bridge with safety disabled for whitelist, enabled for blacklist
        safety = SafetyValidator(enable_whitelist=False, enable_blacklist=True)
        bridge = ShellBridge(safety_validator=safety)

        # Simulate dangerous LLM response
        llm_response = """
        I'll delete that for you.
        
        ```json
        {"tool": "bash_command", "arguments": {"command": "rm -rf /"}}
        ```
        """

        results = await bridge.execute_tool_calls(llm_response)

        # Should be blocked (defense in depth: safety validator OR tool's internal validation)
        assert len(results) > 0
        result = results[0]

        # Defense in depth: Either blocked by safety validator OR failed in tool
        is_blocked = result.blocked or (result.result and hasattr(result.result, 'success') and not result.result.success)
        assert is_blocked, f"Expected blocking but got: {result}"

        # Check error message contains dangerous keywords
        if result.blocked:
            # Blocked by safety validator
            assert ("root directory" in result.block_reason.lower() or "dangerous" in result.block_reason.lower())
        elif result.result and hasattr(result.result, 'error'):
            # Blocked by tool's internal validation
            error_msg = result.result.error.lower() if result.result.error else ""
            assert ("dangerous" in error_msg or "blocked" in error_msg or "rm -rf" in error_msg), \
                   f"Expected dangerous command error, got: {result.result.error}"

    @pytest.mark.asyncio
    async def test_executes_safe_tools(self):
        """Should execute safe tool calls."""
        bridge = ShellBridge()

        # Create temp file
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write("test content")
            temp_file = f.name

        try:
            # Simulate LLM response with tool call
            llm_response = f"""
            I'll read that file.
            
            ```json
            {{"tool": "read_file", "arguments": {{"path": "{temp_file}"}}}}
            ```
            """

            results = await bridge.execute_tool_calls(llm_response)

            # Should execute successfully
            assert len(results) == 1
            result = results[0]
            assert result.success
            assert not result.blocked
        finally:
            os.unlink(temp_file)

    @pytest.mark.asyncio
    async def test_handles_parse_errors(self):
        """Should handle parser errors gracefully."""
        bridge = ShellBridge()

        # Invalid JSON
        llm_response = "```json\n{invalid json}\n```"

        results = await bridge.execute_tool_calls(llm_response)

        # Should return empty results (parse failed)
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_tracks_session_context(self):
        """Should track operations in session."""
        with tempfile.TemporaryDirectory() as tmpdir:
            sessions = SessionManager(storage_dir=Path(tmpdir))
            bridge = ShellBridge(session_manager=sessions)

            # Execute a tool call
            with tempfile.NamedTemporaryFile(delete=False) as f:
                temp_file = f.name

            try:
                llm_response = f"""
                ```json
                {{"tool": "read_file", "arguments": {{"path": "{temp_file}"}}}}
                ```
                """

                results = await bridge.execute_tool_calls(llm_response, session_id="test")

                # Check session was updated
                session = sessions.get_session("test")
                assert session is not None
                assert len(session.history) > 0
            finally:
                if os.path.exists(temp_file):
                    os.unlink(temp_file)


@pytest.mark.asyncio
async def test_end_to_end_integration():
    """Integration test: full pipeline from input to execution."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Setup
        sessions = SessionManager(storage_dir=Path(tmpdir))
        bridge = ShellBridge(session_manager=sessions)

        # Create test file
        test_file = Path(tmpdir) / "test.txt"
        test_file.write_text("Hello, world!")

        # Simulate complete flow
        # (Note: This requires LLM to be available, so we skip actual LLM call)

        # Instead, test with pre-parsed response
        llm_response = f"""
        I'll read that file for you.
        
        ```json
        {{"tool": "read_file", "arguments": {{"path": "{test_file}"}}}}
        ```
        """

        results = await bridge.execute_tool_calls(llm_response, session_id="integration_test")

        # Verify
        assert len(results) == 1
        assert results[0].success
        assert "Hello, world!" in str(results[0].result)

        # Verify session tracking
        session = sessions.get_session("integration_test")
        assert session is not None
        assert len(session.history) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
