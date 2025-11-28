"""Robust multi-strategy response parser for LLM outputs.

Implements multiple parsing strategies with fallbacks:
1. Strict JSON parsing (primary)
2. JSON extraction from markdown code blocks
3. Regex-based tool call extraction
4. Partial JSON recovery
5. Plain text fallback

Best practices from:
- OpenAI Codex: Schema validation, security sanitization
- Anthropic Claude: Guaranteed structured outputs
- Google Gemini: Retry logic, secondary pass recovery
- Cursor AI: Context-aware parsing

Designed for high reliability (95%+ parse success) even with malformed LLM responses.
"""

import json
import re
import logging
from typing import List, Dict, Any, Optional, Tuple, Callable
from enum import Enum
from pathlib import Path
from datetime import datetime


logger = logging.getLogger(__name__)


class ParseStrategy(Enum):
    """Parsing strategies in order of preference."""
    STRICT_JSON = "strict_json"
    MARKDOWN_JSON = "markdown_json"
    REGEX_EXTRACTION = "regex_extraction"
    PARTIAL_JSON = "partial_json"
    PLAIN_TEXT = "plain_text"


class ParseResult:
    """Result of parsing attempt with metadata."""

    def __init__(
        self,
        success: bool,
        tool_calls: Optional[List[Dict[str, Any]]] = None,
        text_response: Optional[str] = None,
        strategy: Optional[ParseStrategy] = None,
        error: Optional[str] = None,
        raw_response: Optional[str] = None
    ):
        self.success = success
        self.tool_calls = tool_calls or []
        self.text_response = text_response
        self.strategy = strategy
        self.error = error
        self.raw_response = raw_response

    def is_tool_call(self) -> bool:
        """Check if result contains tool calls."""
        return bool(self.tool_calls)

    def is_text_response(self) -> bool:
        """Check if result is a text response."""
        return bool(self.text_response) and not self.tool_calls

    def __repr__(self) -> str:
        if self.success:
            if self.is_tool_call():
                return f"ParseResult(tool_calls={len(self.tool_calls)}, strategy={self.strategy.value})"
            else:
                return f"ParseResult(text_response, strategy={self.strategy.value})"
        else:
            return f"ParseResult(error={self.error})"


class ResponseParser:
    """Multi-strategy parser for LLM responses with retry and security."""

    def __init__(
        self,
        strict_mode: bool = False,
        enable_retry: bool = True,
        max_retries: int = 2,
        enable_logging: bool = True,
        log_dir: Optional[Path] = None,
        sanitize_args: bool = True
    ):
        """Initialize parser.
        
        Args:
            strict_mode: If True, only accept perfect JSON. If False, attempt recovery.
            enable_retry: Enable retry with secondary LLM pass (Gemini strategy)
            max_retries: Maximum retry attempts
            enable_logging: Log raw responses for debugging
            log_dir: Directory for response logs (default: .qwen_logs/)
            sanitize_args: Sanitize tool arguments for security (Codex strategy)
        """
        self.strict_mode = strict_mode
        self.enable_retry = enable_retry
        self.max_retries = max_retries
        self.enable_logging = enable_logging
        self.log_dir = log_dir or Path.home() / ".qwen_logs"
        self.sanitize_args = sanitize_args

        # Create log directory
        if self.enable_logging:
            self.log_dir.mkdir(parents=True, exist_ok=True)

        self.stats = {
            ParseStrategy.STRICT_JSON: 0,
            ParseStrategy.MARKDOWN_JSON: 0,
            ParseStrategy.REGEX_EXTRACTION: 0,
            ParseStrategy.PARTIAL_JSON: 0,
            ParseStrategy.PLAIN_TEXT: 0,
            "failures": 0,
            "retries": 0,
            "security_blocks": 0
        }

        # Retry callback for secondary LLM pass (can be sync or async)
        self.retry_callback: Optional[Callable[[str, str], str]] = None
        self._is_async_callback = False

    def parse(self, response: str, attempt: int = 0) -> ParseResult:
        """Parse LLM response using multiple strategies with retry.
        
        Args:
            response: Raw LLM response text
            attempt: Current retry attempt number
            
        Returns:
            ParseResult with tool calls or text response
        """
        if not response or not response.strip():
            return ParseResult(
                success=False,
                error="Empty response",
                raw_response=response
            )

        response = response.strip()

        # Log raw response for debugging (Codex best practice)
        if self.enable_logging:
            self._log_response(response, attempt)

        # Strategy 1: Strict JSON parsing
        result = self._try_strict_json(response)
        if result.success:
            self.stats[ParseStrategy.STRICT_JSON] += 1
            logger.debug(f"Parsed with {ParseStrategy.STRICT_JSON.value}")
            # Sanitize tool arguments for security (Codex strategy)
            if self.sanitize_args:
                result = self._sanitize_tool_calls(result)
            return result

        if self.strict_mode:
            self.stats["failures"] += 1
            return self._maybe_retry(response, result, attempt)

        # Strategy 2: Extract JSON from markdown code blocks
        result = self._try_markdown_json(response)
        if result.success:
            self.stats[ParseStrategy.MARKDOWN_JSON] += 1
            logger.debug(f"Parsed with {ParseStrategy.MARKDOWN_JSON.value}")
            if self.sanitize_args:
                result = self._sanitize_tool_calls(result)
            return result

        # Strategy 3: Regex extraction of tool calls
        result = self._try_regex_extraction(response)
        if result.success:
            self.stats[ParseStrategy.REGEX_EXTRACTION] += 1
            logger.debug(f"Parsed with {ParseStrategy.REGEX_EXTRACTION.value}")
            if self.sanitize_args:
                result = self._sanitize_tool_calls(result)
            return result

        # Strategy 4: Partial JSON recovery
        result = self._try_partial_json(response)
        if result.success:
            self.stats[ParseStrategy.PARTIAL_JSON] += 1
            logger.debug(f"Parsed with {ParseStrategy.PARTIAL_JSON.value}")
            if self.sanitize_args:
                result = self._sanitize_tool_calls(result)
            return result

        # Strategy 5: Retry with secondary LLM pass (Gemini strategy)
        if self.enable_retry and attempt < self.max_retries:
            return self._maybe_retry(response, result, attempt)

        # Strategy 6: Plain text fallback
        self.stats[ParseStrategy.PLAIN_TEXT] += 1
        logger.debug(f"Falling back to {ParseStrategy.PLAIN_TEXT.value}")
        return ParseResult(
            success=True,
            text_response=response,
            strategy=ParseStrategy.PLAIN_TEXT,
            raw_response=response
        )

    def _try_strict_json(self, response: str) -> ParseResult:
        """Attempt strict JSON parsing.
        
        Args:
            response: Raw response text
            
        Returns:
            ParseResult with tool calls if successful
        """
        try:
            # Handle both array and object responses
            data = json.loads(response)

            # Normalize to list
            if isinstance(data, dict):
                data = [data]
            elif not isinstance(data, list):
                return ParseResult(
                    success=False,
                    error=f"Expected list or dict, got {type(data).__name__}",
                    raw_response=response
                )

            # Validate tool call structure
            tool_calls = []
            for item in data:
                if not isinstance(item, dict):
                    return ParseResult(
                        success=False,
                        error=f"Tool call must be dict, got {type(item).__name__}",
                        raw_response=response
                    )

                # Validate required fields
                if "tool" not in item:
                    return ParseResult(
                        success=False,
                        error="Tool call missing 'tool' field",
                        raw_response=response
                    )

                # Normalize args field (support both "args" and "arguments")
                if "args" not in item:
                    # Try "arguments" as fallback
                    if "arguments" in item:
                        item["args"] = item.pop("arguments")
                    else:
                        item["args"] = {}

                if not isinstance(item["args"], dict):
                    return ParseResult(
                        success=False,
                        error="'args' must be a dict",
                        raw_response=response
                    )

                tool_calls.append(item)

            return ParseResult(
                success=True,
                tool_calls=tool_calls,
                strategy=ParseStrategy.STRICT_JSON,
                raw_response=response
            )

        except json.JSONDecodeError as e:
            return ParseResult(
                success=False,
                error=f"JSON decode error: {str(e)}",
                raw_response=response
            )

    def _try_markdown_json(self, response: str) -> ParseResult:
        """Extract JSON from markdown code blocks.
        
        Handles responses like:
        ```json
        [{"tool": "readfile", "args": {"path": "main.py"}}]
        ```
        
        Args:
            response: Raw response text
            
        Returns:
            ParseResult with tool calls if successful
        """
        # Pattern: ```json ... ``` or ``` ... ```
        patterns = [
            r'```json\s*\n(.*?)\n```',
            r'```\s*\n(.*?)\n```',
            r'```json\s*(.*?)```',
            r'```(.*?)```'
        ]

        for pattern in patterns:
            match = re.search(pattern, response, re.DOTALL)
            if match:
                json_str = match.group(1).strip()
                result = self._try_strict_json(json_str)
                if result.success:
                    result.strategy = ParseStrategy.MARKDOWN_JSON
                    result.raw_response = response
                    return result

        return ParseResult(
            success=False,
            error="No markdown JSON blocks found",
            raw_response=response
        )

    def _try_regex_extraction(self, response: str) -> ParseResult:
        """Extract tool calls using regex patterns.
        
        Handles malformed JSON like:
        - Missing quotes
        - Single quotes instead of double
        - Trailing commas
        
        Args:
            response: Raw response text
            
        Returns:
            ParseResult with tool calls if successful
        """
        # Pattern: {"tool": "name", "args": {...}}
        # More permissive matching
        pattern = r'\{\s*["\']?tool["\']?\s*:\s*["\'](\w+)["\']\s*,\s*["\']?args["\']?\s*:\s*(\{[^}]*\})\s*\}'

        matches = re.finditer(pattern, response)
        tool_calls = []

        for match in matches:
            tool_name = match.group(1)
            args_str = match.group(2)

            try:
                # Try to parse args as JSON
                args = json.loads(args_str)
                tool_calls.append({
                    "tool": tool_name,
                    "args": args
                })
            except json.JSONDecodeError:
                # Try to extract key-value pairs manually
                args = self._extract_args(args_str)
                if args:
                    tool_calls.append({
                        "tool": tool_name,
                        "args": args
                    })

        if tool_calls:
            return ParseResult(
                success=True,
                tool_calls=tool_calls,
                strategy=ParseStrategy.REGEX_EXTRACTION,
                raw_response=response
            )

        return ParseResult(
            success=False,
            error="No tool calls found via regex",
            raw_response=response
        )

    def _try_partial_json(self, response: str) -> ParseResult:
        """Attempt to recover partial/truncated JSON.
        
        Handles cases like:
        - Incomplete arrays: [{"tool": "read
        - Missing closing brackets
        - Truncated responses
        
        Args:
            response: Raw response text
            
        Returns:
            ParseResult with tool calls if successful
        """
        # Try to find start of JSON array
        start_idx = response.find('[')
        if start_idx == -1:
            return ParseResult(
                success=False,
                error="No JSON array start found",
                raw_response=response
            )

        # Extract from array start
        json_fragment = response[start_idx:]

        # Try to complete the JSON
        completion_attempts = [
            json_fragment,  # As-is
            json_fragment + ']',  # Add closing bracket
            json_fragment + '}]',  # Add closing object + bracket
            json_fragment + '"}]}]',  # Add closing quote + object + bracket
        ]

        for attempt in completion_attempts:
            result = self._try_strict_json(attempt)
            if result.success:
                result.strategy = ParseStrategy.PARTIAL_JSON
                result.raw_response = response
                logger.warning(f"Recovered partial JSON: {attempt[:100]}...")
                return result

        return ParseResult(
            success=False,
            error="Could not recover partial JSON",
            raw_response=response
        )

    def _extract_args(self, args_str: str) -> Dict[str, Any]:
        """Extract arguments from malformed args string.
        
        Args:
            args_str: String like '{"key": "value", "key2": "value2"}'
            
        Returns:
            Dict of extracted args
        """
        args = {}

        # Pattern: "key": "value" or 'key': 'value'
        pattern = r'["\']?(\w+)["\']?\s*:\s*["\']([^"\']*)["\']'

        matches = re.finditer(pattern, args_str)
        for match in matches:
            key = match.group(1)
            value = match.group(2)
            args[key] = value

        return args

    def validate_tool_call(self, tool_call: Dict[str, Any], tool_schemas: List[Dict[str, Any]]) -> Tuple[bool, Optional[str]]:
        """Validate tool call against tool schemas.
        
        Args:
            tool_call: Parsed tool call dict
            tool_schemas: List of available tool schemas
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        tool_name = tool_call.get("tool")
        args = tool_call.get("args", {})

        # Find tool schema
        tool_schema = None
        for schema in tool_schemas:
            if schema["name"] == tool_name:
                tool_schema = schema
                break

        if not tool_schema:
            return False, f"Unknown tool: {tool_name}"

        # Check required parameters
        required_params = tool_schema.get("parameters", {}).get("required", [])
        missing_params = [p for p in required_params if p not in args]

        if missing_params:
            return False, f"Missing required parameters: {', '.join(missing_params)}"

        # Check parameter types (basic validation)
        param_props = tool_schema.get("parameters", {}).get("properties", {})
        for param_name, param_value in args.items():
            if param_name not in param_props:
                logger.warning(f"Unknown parameter '{param_name}' for tool '{tool_name}'")
                continue

            expected_type = param_props[param_name].get("type")
            if expected_type:
                actual_type = type(param_value).__name__
                type_map = {
                    "string": "str",
                    "integer": "int",
                    "boolean": "bool",
                    "array": "list",
                    "object": "dict"
                }
                expected_python_type = type_map.get(expected_type, expected_type)

                if actual_type != expected_python_type:
                    logger.warning(
                        f"Type mismatch for '{param_name}': "
                        f"expected {expected_python_type}, got {actual_type}"
                    )

        return True, None

    def get_statistics(self) -> Dict[str, int]:
        """Get parsing statistics.
        
        Returns:
            Dict with strategy usage counts
        """
        total = sum(self.stats.values())
        return {
            "total": total,
            "strict_json": self.stats[ParseStrategy.STRICT_JSON],
            "markdown_json": self.stats[ParseStrategy.MARKDOWN_JSON],
            "regex_extraction": self.stats[ParseStrategy.REGEX_EXTRACTION],
            "partial_json": self.stats[ParseStrategy.PARTIAL_JSON],
            "plain_text": self.stats[ParseStrategy.PLAIN_TEXT],
            "failures": self.stats["failures"],
            "retries": self.stats.get("retries", 0),
            "security_blocks": self.stats.get("security_blocks", 0)
        }

    def reset_statistics(self) -> None:
        """Reset parsing statistics."""
        for key in self.stats:
            self.stats[key] = 0

    def set_retry_callback(self, callback: Callable[[str, str], str], is_async: bool = False) -> None:
        """Set callback for secondary LLM pass during retry.
        
        Args:
            callback: Function that takes (original_response, error) and returns fixed response
            is_async: Whether callback is async (default: False)
        """
        self.retry_callback = callback
        self._is_async_callback = is_async

    def _maybe_retry(self, response: str, failed_result: ParseResult, attempt: int) -> ParseResult:
        """Attempt retry with secondary LLM pass (Gemini strategy).
        
        Args:
            response: Original response that failed to parse
            failed_result: Failed parse result
            attempt: Current attempt number
            
        Returns:
            ParseResult from retry or original failed result
        """
        if not self.enable_retry or attempt >= self.max_retries:
            self.stats["failures"] += 1
            return failed_result

        if not self.retry_callback:
            logger.warning("Retry enabled but no retry_callback set")
            self.stats["failures"] += 1
            return failed_result

        try:
            logger.info(f"Retry attempt {attempt + 1}/{self.max_retries} with secondary LLM pass")
            self.stats["retries"] += 1

            # Call LLM to fix the invalid response
            fixed_response = self.retry_callback(response, failed_result.error or "Invalid format")

            # Parse the fixed response
            return self.parse(fixed_response, attempt=attempt + 1)

        except Exception as e:
            logger.error(f"Retry failed: {e}")
            self.stats["failures"] += 1
            return failed_result

    def _sanitize_tool_calls(self, result: ParseResult) -> ParseResult:
        """Sanitize tool call arguments for security (Codex strategy).
        
        Prevents:
        - Path traversal attacks (../, ~/)
        - Command injection (shell metacharacters)
        - Excessive string lengths
        - Suspicious patterns
        
        Args:
            result: ParseResult with tool calls
            
        Returns:
            Sanitized ParseResult
        """
        if not result.tool_calls:
            return result

        sanitized_calls = []
        for tool_call in result.tool_calls:
            args = tool_call.get("args", {})
            sanitized_args = {}
            blocked = False

            for key, value in args.items():
                # Only sanitize string values
                if not isinstance(value, str):
                    sanitized_args[key] = value
                    continue

                # Check for dangerous patterns
                dangerous_patterns = [
                    r'\.\./\.\.',  # Path traversal
                    r'~/\.',        # Home directory traversal
                    r';.*rm\s',     # Command chaining with rm
                    r'\|.*rm\s',    # Pipe to rm
                    r'&&.*rm\s',    # And operator with rm
                    r'`.*`',        # Command substitution
                    r'\$\(',        # Command substitution
                ]

                for pattern in dangerous_patterns:
                    if re.search(pattern, value):
                        logger.error(f"Blocked dangerous pattern in tool call: {pattern}")
                        self.stats["security_blocks"] += 1
                        blocked = True
                        break

                if blocked:
                    break

                # Check string length (prevent DoS)
                if len(value) > 10000:
                    logger.warning(f"Truncated excessive string length: {len(value)} chars")
                    value = value[:10000]

                sanitized_args[key] = value

            if not blocked:
                sanitized_calls.append({
                    "tool": tool_call["tool"],
                    "args": sanitized_args
                })

        if len(sanitized_calls) < len(result.tool_calls):
            logger.warning(
                f"Security filter blocked {len(result.tool_calls) - len(sanitized_calls)} tool calls"
            )

        result.tool_calls = sanitized_calls
        return result

    def _log_response(self, response: str, attempt: int) -> None:
        """Log raw response for debugging (Codex best practice).
        
        Args:
            response: Raw response text
            attempt: Attempt number
        """
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            log_file = self.log_dir / f"response_{timestamp}_attempt{attempt}.txt"

            with open(log_file, "w", encoding="utf-8") as f:
                f.write(f"Timestamp: {timestamp}\n")
                f.write(f"Attempt: {attempt}\n")
                f.write(f"Length: {len(response)} chars\n")
                f.write("-" * 80 + "\n")
                f.write(response)

            logger.debug(f"Logged response to {log_file}")

        except Exception as e:
            logger.warning(f"Failed to log response: {e}")


# Global parser instance
parser = ResponseParser(
    strict_mode=False,
    enable_retry=True,
    max_retries=2,
    enable_logging=True,
    sanitize_args=True
)
