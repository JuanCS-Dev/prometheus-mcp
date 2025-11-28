"""
Soft Buffer for Streaming Markdown.

Accumulates partial chunks to prevent "janky" rendering of incomplete Markdown syntax.
"""

import re

class SoftBuffer:
    """
    Buffers streaming text until safe render boundaries.
    
    Prevents flickering of:
    - Incomplete bold/italic markers (*, **)
    - Incomplete code block fences (`, ``)
    - Incomplete headers (#)
    - Trailing backslashes
    """

    # Patterns that indicate we might be in the middle of a markdown token
    # Only match if the buffer ENDS with these characters
    UNSAFE_SUFFIXES = [
        r"\*$",      # Ends with * (could be **)
        r"\_$",      # Ends with _ (could be __)
        r"\`$",      # Ends with ` (could be `` or ```)
        r"\`\`$",    # Ends with `` (could be ```)
        r"\#$",      # Ends with # (could be ##)
        r"\\$"       # Ends with \ (escape)
    ]

    def __init__(self):
        self._buffer = ""

    def feed(self, chunk: str) -> str:
        """
        Feed a chunk and return safe-to-render text.
        Returns empty string if content is buffered.
        """
        self._buffer += chunk

        # Check if buffer ends with unsafe characters
        for pattern in self.UNSAFE_SUFFIXES:
            if re.search(pattern, self._buffer):
                return ""

        # If safe, return entire buffer and clear
        result = self._buffer
        self._buffer = ""
        return result

    def flush(self) -> str:
        """Force return remaining buffer."""
        result = self._buffer
        self._buffer = ""
        return result
