"""Tests for the enhanced response parser.

Tests all parsing strategies + new features:
- Multiple strategies (JSON, Markdown, Regex, Partial, Plain text)
- Retry with secondary LLM pass (Gemini strategy)
- Security sanitization (Codex strategy)
- Response logging (Codex strategy)
"""

import pytest
import json
from jdev_cli.core.parser import ResponseParser, ParseStrategy


@pytest.fixture
def parser():
    """Create parser instance for testing."""
    return ResponseParser(
        strict_mode=False,
        enable_retry=False,  # Disable for unit tests
        enable_logging=False,  # Disable for tests
        sanitize_args=True
    )


class TestStrictJSON:
    """Test Strategy 1: Strict JSON parsing."""

    def test_single_tool_call(self, parser):
        """Test single tool call parsing."""
        response = json.dumps({
            "tool": "read_file",
            "args": {"path": "main.py"}
        })

        result = parser.parse(response)

        assert result.success
        assert result.strategy == ParseStrategy.STRICT_JSON
        assert len(result.tool_calls) == 1
        assert result.tool_calls[0]["tool"] == "read_file"
        assert result.tool_calls[0]["args"]["path"] == "main.py"

    def test_multiple_tool_calls(self, parser):
        """Test multiple tool calls parsing."""
        response = json.dumps([
            {"tool": "read_file", "args": {"path": "main.py"}},
            {"tool": "write_file", "args": {"path": "test.py", "content": "print('hello')"}}
        ])

        result = parser.parse(response)

        assert result.success
        assert result.strategy == ParseStrategy.STRICT_JSON
        assert len(result.tool_calls) == 2

    def test_missing_args(self, parser):
        """Test tool call without args (should default to empty dict)."""
        response = json.dumps({
            "tool": "ls"
        })

        result = parser.parse(response)

        assert result.success
        assert result.tool_calls[0]["args"] == {}

    def test_invalid_json(self, parser):
        """Test invalid JSON (should fall back to other strategies)."""
        response = '{"tool": "read_file", "args": {"path": "main.py"'  # Missing closing braces

        result = parser.parse(response)

        # Should not use strict JSON
        assert result.strategy != ParseStrategy.STRICT_JSON


class TestMarkdownJSON:
    """Test Strategy 2: JSON extraction from markdown."""

    def test_json_code_block(self, parser):
        """Test extraction from ```json``` block."""
        response = """
Here are the tool calls:

```json
[
    {"tool": "read_file", "args": {"path": "main.py"}}
]
```
        """.strip()

        result = parser.parse(response)

        assert result.success
        assert result.strategy == ParseStrategy.MARKDOWN_JSON
        assert len(result.tool_calls) == 1

    def test_plain_code_block(self, parser):
        """Test extraction from ``` block without json tag."""
        response = """
```
{"tool": "ls", "args": {}}
```
        """.strip()

        result = parser.parse(response)

        assert result.success
        assert result.strategy == ParseStrategy.MARKDOWN_JSON

    def test_multiple_code_blocks(self, parser):
        """Test extraction from first code block."""
        response = """
```json
{"tool": "read_file", "args": {"path": "test.py"}}
```

Some text

```json
{"tool": "invalid"}
```
        """.strip()

        result = parser.parse(response)

        assert result.success
        # Should parse first valid block
        assert result.tool_calls[0]["tool"] == "read_file"


class TestRegexExtraction:
    """Test Strategy 3: Regex-based extraction."""

    def test_malformed_json(self, parser):
        """Test extraction from malformed JSON."""
        response = "{'tool': 'read_file', 'args': {'path': 'main.py'}}"

        result = parser.parse(response)

        # Should extract via regex since JSON parser fails
        assert result.success

    def test_missing_quotes(self, parser):
        """Test extraction when quotes are missing."""
        response = '{tool: "ls", args: {}}'

        result = parser.parse(response)

        assert result.success or result.strategy == ParseStrategy.PLAIN_TEXT


class TestPartialJSON:
    """Test Strategy 4: Partial JSON recovery."""

    def test_incomplete_array(self, parser):
        """Test recovery of incomplete JSON array."""
        response = '[{"tool": "read_file", "args": {"path": "main.py"}'

        result = parser.parse(response)

        # Should attempt to complete and parse
        assert result.success
        assert result.strategy == ParseStrategy.PARTIAL_JSON

    def test_truncated_response(self, parser):
        """Test recovery of truncated response."""
        response = '[{"tool": "write_file", "args": {"path": "test.py", "content": "prin'

        result = parser.parse(response)

        # May succeed with partial recovery or fall back to plain text
        assert result.success


class TestPlainTextFallback:
    """Test Strategy 5: Plain text fallback."""

    def test_plain_text(self, parser):
        """Test plain text response."""
        response = "I understand you want to read the file. Let me help with that."

        result = parser.parse(response)

        assert result.success
        assert result.strategy == ParseStrategy.PLAIN_TEXT
        assert result.text_response == response
        assert result.is_text_response()
        assert not result.is_tool_call()


class TestSecuritySanitization:
    """Test Codex-inspired security sanitization."""

    def test_path_traversal_blocked(self, parser):
        """Test path traversal attack is blocked."""
        response = json.dumps({
            "tool": "read_file",
            "args": {"path": "../../etc/passwd"}
        })

        result = parser.parse(response)

        assert result.success
        # Tool call should be blocked
        assert len(result.tool_calls) == 0
        assert parser.stats["security_blocks"] > 0

    def test_command_injection_blocked(self, parser):
        """Test command injection is blocked."""
        response = json.dumps({
            "tool": "bash_command",
            "args": {"command": "ls; rm -rf /"}
        })

        result = parser.parse(response)

        assert result.success
        # Tool call should be blocked
        assert len(result.tool_calls) == 0
        assert parser.stats["security_blocks"] > 0

    def test_safe_command_allowed(self, parser):
        """Test safe commands are allowed."""
        response = json.dumps({
            "tool": "read_file",
            "args": {"path": "main.py"}
        })

        result = parser.parse(response)

        assert result.success
        assert len(result.tool_calls) == 1
        assert parser.stats["security_blocks"] == 0


class TestRetryLogic:
    """Test Gemini-inspired retry logic."""

    def test_retry_with_callback(self):
        """Test retry with secondary LLM pass."""
        parser_with_retry = ResponseParser(
            strict_mode=False,
            enable_retry=True,
            max_retries=1,
            enable_logging=False
        )

        retry_called = False

        def mock_retry_callback(response: str, error: str) -> str:
            nonlocal retry_called
            retry_called = True
            # Return fixed response
            return json.dumps({"tool": "read_file", "args": {"path": "main.py"}})

        parser_with_retry.set_retry_callback(mock_retry_callback)

        # Invalid response that will trigger retry
        response = "invalid json {"

        result = parser_with_retry.parse(response)

        assert retry_called
        assert result.success
        assert parser_with_retry.stats["retries"] > 0

    def test_max_retries_limit(self):
        """Test max retries limit is respected."""
        parser_with_retry = ResponseParser(
            strict_mode=True,
            enable_retry=True,
            max_retries=2,
            enable_logging=False
        )

        retry_count = 0

        def mock_retry_callback(response: str, error: str) -> str:
            nonlocal retry_count
            retry_count += 1
            # Keep returning invalid
            return "invalid"

        parser_with_retry.set_retry_callback(mock_retry_callback)

        response = "invalid"
        result = parser_with_retry.parse(response)

        # Should retry max_retries times
        assert retry_count == 2
        assert not result.success


class TestToolCallValidation:
    """Test tool call validation against schemas."""

    def test_valid_tool_call(self, parser):
        """Test validation of valid tool call."""
        tool_call = {
            "tool": "read_file",
            "args": {"path": "main.py"}
        }

        tool_schemas = [
            {
                "name": "read_file",
                "parameters": {
                    "required": ["path"],
                    "properties": {
                        "path": {"type": "string"}
                    }
                }
            }
        ]

        is_valid, error = parser.validate_tool_call(tool_call, tool_schemas)

        assert is_valid
        assert error is None

    def test_missing_required_param(self, parser):
        """Test validation fails for missing required param."""
        tool_call = {
            "tool": "read_file",
            "args": {}
        }

        tool_schemas = [
            {
                "name": "read_file",
                "parameters": {
                    "required": ["path"],
                    "properties": {
                        "path": {"type": "string"}
                    }
                }
            }
        ]

        is_valid, error = parser.validate_tool_call(tool_call, tool_schemas)

        assert not is_valid
        assert "Missing required parameters" in error

    def test_unknown_tool(self, parser):
        """Test validation fails for unknown tool."""
        tool_call = {
            "tool": "unknown_tool",
            "args": {}
        }

        tool_schemas = [
            {
                "name": "read_file",
                "parameters": {"required": [], "properties": {}}
            }
        ]

        is_valid, error = parser.validate_tool_call(tool_call, tool_schemas)

        assert not is_valid
        assert "Unknown tool" in error


class TestStatistics:
    """Test parsing statistics tracking."""

    def test_statistics_tracking(self, parser):
        """Test that statistics are tracked correctly."""
        # Parse with strict JSON
        parser.parse('{"tool": "ls", "args": {}}')

        # Parse with markdown
        parser.parse('```json\n{"tool": "pwd", "args": {}}\n```')

        # Parse with plain text
        parser.parse("Hello world")

        stats = parser.get_statistics()

        assert stats["strict_json"] == 1
        assert stats["markdown_json"] == 1
        assert stats["plain_text"] == 1
        assert stats["total"] == 3

    def test_reset_statistics(self, parser):
        """Test statistics reset."""
        parser.parse('{"tool": "ls", "args": {}}')

        stats_before = parser.get_statistics()
        assert stats_before["total"] > 0

        parser.reset_statistics()

        stats_after = parser.get_statistics()
        assert stats_after["total"] == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
