"""
Stream Filter - Output Sanitization
===================================

Provides real-time filtering of streaming output to prevent raw JSON tool calls
from leaking to the user interface.

Author: JuanCS Dev
Date: 2025-11-28
"""

import re

class StreamFilter:
    """
    Filters streaming text to remove raw JSON tool calls.
    
    Implements a buffering state machine that detects potential JSON blocks
    and suppresses them until they are confirmed as tool calls or invalidated.
    """

    def __init__(self):
        self._buffer = ""
        self._in_potential_json = False
        self._brace_count = 0

        # Regex to detect start of potential tool call JSON
        # Matches: {"tool": ... or { "tool": ...
        self._json_start_pattern = re.compile(r'\{\s*"tool"')

        # ENHANCED: Also detect common tool argument patterns
        # These are JSON objects that Gemini sometimes outputs when describing tool calls
        # Examples: {"query": "...", {"path": "...", {"command": "...
        self._tool_arg_patterns = re.compile(
            r'\{\s*"(query|path|command|file|url|pattern|search|prompt|message|data)"'
        )

    def process_chunk(self, chunk: str) -> str:
        """
        Process a text chunk and return sanitized text.
        
        Args:
            chunk: Incoming text chunk
            
        Returns:
            Sanitized text to display (may be empty if buffering)
        """
        if not chunk:
            return ""

        # If we are already buffering, append to buffer
        if self._in_potential_json:
            self._buffer += chunk
            return self._check_buffer()

        # Check if this chunk starts a potential JSON block
        # We look for '{' which might be the start
        if '{' in chunk:
            # Split text before and after the first '{'
            pre_json, post_json = chunk.split('{', 1)

            # Check if the '{' + post_json looks like it could be our JSON
            # We need enough context. If post_json is very short, we might need to buffer.
            potential_start = '{' + post_json

            # Buffer if:
            # 1. It matches the pattern ({"tool")
            # 2. It matches tool arg patterns ({"query", {"path", etc.)
            # 3. It's too short to tell (just { or { "...)
            # 4. It looks like it might start a key ("...)
            if (
                self._json_start_pattern.match(potential_start) or
                self._tool_arg_patterns.match(potential_start) or
                len(post_json) < 10 or
                post_json.strip().startswith('"')
            ):
                # Start buffering
                self._in_potential_json = True
                self._buffer = potential_start
                self._brace_count = 1 + post_json.count('{') - post_json.count('}')

                # Return the text BEFORE the JSON
                return pre_json

        # Normal text
        return chunk

    def _check_buffer(self) -> str:
        """
        Check the current buffer state.
        
        Returns:
            Text to release (if invalid JSON), or empty string (if still buffering/valid JSON)
        """
        # Update brace count
        # We need to be careful not to double count if we just added to buffer
        # Ideally we'd track incremental updates, but for now let's re-scan buffer
        # This is simple but O(N) on buffer size. Buffer shouldn't be huge.
        self._brace_count = self._buffer.count('{') - self._buffer.count('}')

        # If braces balanced (count == 0), we have a complete block
        if self._brace_count <= 0:
            # Check if it's actually a tool call JSON or tool argument JSON
            if (self._json_start_pattern.match(self._buffer) or
                self._tool_arg_patterns.match(self._buffer)):
                # It IS a tool-related JSON. Suppress it.
                # We might have trailing text after the closing brace
                # Find the closing brace
                # Simple approach: assume the last '}' closes it if count is 0
                # But count could be < 0 if extra '}'

                # Reset state
                self._in_potential_json = False
                remaining = ""

                # If we have extra text after the JSON, return it
                # This is tricky without a full parser, but let's try to be safe
                # If we suppressed it, we return nothing.
                # If there was text AFTER the JSON in the buffer, we should return it.
                # For now, let's just suppress the whole buffer if it matches the pattern
                # and assume the model outputs clean blocks.

                buffer_content = self._buffer
                self._buffer = ""
                return ""
            else:
                # It was a JSON block but NOT a tool call (e.g. just code)
                # Release the buffer
                content = self._buffer
                self._buffer = ""
                self._in_potential_json = False
                return content

        # If buffer gets too large without confirming "tool" or tool args pattern, abort
        if len(self._buffer) > 50 and not (
            self._json_start_pattern.search(self._buffer) or
            self._tool_arg_patterns.search(self._buffer)
        ):
             content = self._buffer
             self._buffer = ""
             self._in_potential_json = False
             return content

        # Still buffering
        return ""

    def flush(self) -> str:
        """Flush any remaining buffer content."""
        content = self._buffer
        self._buffer = ""
        self._in_potential_json = False
        return content
