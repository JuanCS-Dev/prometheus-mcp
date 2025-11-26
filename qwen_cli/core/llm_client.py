"""
LLM Client Module - Gemini API Integration
==========================================

Extracted from Bridge GOD CLASS (Nov 2025 Refactoring).

Features:
- GeminiClient: Streaming LLM with function calling support
- ToolCallParser: Extract tool calls from LLM responses
- Multi-turn conversation support
- SDK and httpx fallback modes
"""

from __future__ import annotations

import asyncio
import json
import os
import re
from typing import Any, AsyncIterator, Dict, List, Optional, Tuple


class ToolCallParser:
    """
    Parse tool calls from LLM responses.

    Handles multiple formats:
    1. Text markers [TOOL_CALL:name:args]
    2. Python-style function calls: function_name(arg='value', ...)
    3. Code blocks with function calls
    """

    # Pattern for explicit tool call markers
    MARKER_PATTERN = re.compile(r'\[TOOL_CALL:(\w+):(\{.*?\})\]', re.DOTALL)

    # Pattern for Python-style function calls in code blocks
    # Matches: write_file(path='test.txt', content='Hello')
    FUNC_PATTERN = re.compile(
        r'(\w+)\s*\(\s*'  # function_name(
        r'((?:[^()]*(?:\([^()]*\))?)*)'  # args (handles nested parens)
        r'\s*\)',
        re.DOTALL
    )

    # Known tool names to filter false positives
    KNOWN_TOOLS = {
        'write_file', 'read_file', 'edit_file', 'delete_file',
        'bash_command', 'list_directory', 'create_directory',
        'move_file', 'copy_file', 'search_files', 'get_directory_tree',
        'git_status', 'git_diff', 'web_search', 'fetch_url',
        'http_request', 'download_file', 'insert_lines',
        'read_multiple_files', 'restore_backup', 'save_session',
        'search_documentation', 'package_search', 'get_context',
        'cd', 'ls', 'pwd', 'mkdir', 'rm', 'cp', 'mv', 'touch', 'cat'
    }

    @staticmethod
    def _parse_python_args(args_str: str) -> Dict[str, Any]:
        """Parse Python-style keyword arguments."""
        args = {}
        if not args_str.strip():
            return args

        # Use ast to safely parse
        try:
            import ast
            # Wrap in function call to parse
            fake_call = f"f({args_str})"
            tree = ast.parse(fake_call, mode='eval')
            call = tree.body

            for keyword in call.keywords:
                key = keyword.arg
                value = keyword.value
                # Extract literal values
                if isinstance(value, ast.Constant):
                    args[key] = value.value
                elif isinstance(value, ast.Str):  # Python 3.7 compat
                    args[key] = value.s
                elif isinstance(value, ast.Num):
                    args[key] = value.n
                elif isinstance(value, (ast.List, ast.Dict)):
                    args[key] = ast.literal_eval(ast.unparse(value))
        except Exception:
            # Fallback: regex-based parsing
            # Match key='value' or key="value" or key=value
            kv_pattern = re.compile(r"(\w+)\s*=\s*(?:'([^']*)'|\"([^\"]*)\"|(\S+))")
            for match in kv_pattern.finditer(args_str):
                key = match.group(1)
                value = match.group(2) or match.group(3) or match.group(4)
                args[key] = value

        return args

    @staticmethod
    def extract(text: str) -> List[Tuple[str, Dict[str, Any]]]:
        """
        Extract tool calls from text.

        Returns:
            List of (tool_name, arguments) tuples
        """
        results = []

        # 1. Check for explicit markers first
        marker_matches = ToolCallParser.MARKER_PATTERN.findall(text)
        for name, args_str in marker_matches:
            try:
                args = json.loads(args_str)
                results.append((name, args))
            except json.JSONDecodeError:
                continue

        # 2. Check for Python-style function calls (in code blocks)
        # Extract code blocks first
        code_blocks = re.findall(r'```(?:\w+)?\n?(.*?)```', text, re.DOTALL)
        search_text = '\n'.join(code_blocks) if code_blocks else text

        for match in ToolCallParser.FUNC_PATTERN.finditer(search_text):
            func_name = match.group(1)
            args_str = match.group(2)

            # Only process known tools
            if func_name in ToolCallParser.KNOWN_TOOLS:
                args = ToolCallParser._parse_python_args(args_str)
                if args:  # Only add if we got valid args
                    # Avoid duplicates
                    if not any(r[0] == func_name and r[1] == args for r in results):
                        results.append((func_name, args))

        return results

    @staticmethod
    def remove(text: str) -> str:
        """Remove tool call markers from text for clean display."""
        text = ToolCallParser.MARKER_PATTERN.sub('', text)
        # Also remove code blocks containing only tool calls
        lines = text.split('\n')
        clean_lines = []
        in_tool_block = False
        for line in lines:
            if line.strip().startswith('```'):
                in_tool_block = not in_tool_block
                continue
            if in_tool_block:
                # Check if this line is just a tool call
                if any(tool in line for tool in ToolCallParser.KNOWN_TOOLS):
                    continue
            clean_lines.append(line)
        return '\n'.join(clean_lines).strip()

    @staticmethod
    def format_marker(name: str, args: Dict[str, Any]) -> str:
        """Create a tool call marker string."""
        return f"[TOOL_CALL:{name}:{json.dumps(args)}]"


class GeminiClient:
    """
    Optimized Gemini API client with streaming support.

    Best Practices (Nov 2025):
    - Temperature 1.0 for Gemini 3.x (optimized setting)
    - Streaming for UI responsiveness
    - System instructions for consistent behavior
    - Exponential backoff with jitter for rate limits

    Sources:
    - https://ai.google.dev/api
    - https://firebase.google.com/docs/ai-logic/live-api
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 1.0,  # Gemini 3 optimized
        max_output_tokens: int = 8192,
    ):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        self.model_name = model or os.getenv("GEMINI_MODEL") or "gemini-2.0-flash"
        self.temperature = temperature
        self.max_output_tokens = max_output_tokens
        self._model = None
        self._initialized = False
        self._generation_config = None
        # Function calling support
        self._tool_schemas: List[Dict[str, Any]] = []
        self._gemini_tools = None

    def set_tools(self, schemas: List[Dict[str, Any]]) -> None:
        """
        Configure tools for function calling.

        Args:
            schemas: List of tool schemas with name, description, parameters
        """
        self._tool_schemas = schemas
        self._gemini_tools = None  # Reset to force rebuild

    def _build_gemini_tools(self):
        """Convert tool schemas to Gemini Tool objects."""
        if not self._tool_schemas:
            return None

        try:
            from google.generativeai.types import FunctionDeclaration, Tool as GeminiTool

            declarations = []
            for schema in self._tool_schemas:
                # Ensure parameters has proper structure
                params = schema.get("parameters", {})
                if not params.get("type"):
                    params["type"] = "object"
                if "properties" not in params:
                    params["properties"] = {}

                declarations.append(
                    FunctionDeclaration(
                        name=schema["name"],
                        description=schema.get("description", ""),
                        parameters=params
                    )
                )

            self._gemini_tools = [GeminiTool(function_declarations=declarations)]
            return self._gemini_tools
        except ImportError:
            return None
        except Exception:
            return None

    async def _ensure_initialized(self) -> bool:
        """Lazy initialization of Gemini SDK with optimized config."""
        if self._initialized:
            return True

        if not self.api_key:
            return False

        try:
            import google.generativeai as genai
            genai.configure(api_key=self.api_key)

            # Optimized generation config (Nov 2025 best practices)
            self._generation_config = genai.GenerationConfig(
                temperature=self.temperature,
                max_output_tokens=self.max_output_tokens,
                top_p=0.95,
                top_k=40,
            )

            self._model = genai.GenerativeModel(
                self.model_name,
                generation_config=self._generation_config,
            )
            self._initialized = True
            return True
        except ImportError:
            # Fallback: try httpx direct API
            return await self._init_httpx()
        except Exception:
            # Log but don't crash
            return False

    async def _init_httpx(self) -> bool:
        """Fallback initialization using httpx."""
        try:
            import httpx
            self._httpx_client = httpx.AsyncClient(timeout=60.0)
            self._initialized = True
            self._use_httpx = True
            return True
        except ImportError:
            return False

    async def stream(
        self,
        prompt: str,
        system_prompt: str = "",
        context: Optional[List[Dict[str, str]]] = None,
        **kwargs: Any,  # FIX CRÍTICO: Aceita kwargs extras para compatibilidade com BaseAgent
    ) -> AsyncIterator[str]:
        """
        Stream response from Gemini with optimized settings.

        Args:
            prompt: User's message
            system_prompt: System instructions
            context: Optional conversation history
            **kwargs: Extra arguments (ignored for compatibility with BaseAgent._stream_llm)

        Yields:
            Text chunks for 60fps rendering
        """
        # Note: kwargs like max_tokens are ignored - Gemini uses max_output_tokens from config
        if not await self._ensure_initialized():
            yield "❌ Gemini not configured. Set GEMINI_API_KEY environment variable."
            return

        try:
            if hasattr(self, '_use_httpx') and self._use_httpx:
                async for chunk in self._stream_httpx(prompt, system_prompt, context):
                    yield chunk
            else:
                async for chunk in self._stream_sdk(prompt, system_prompt, context):
                    yield chunk
        except Exception as e:
            yield f"\n❌ Error: {str(e)}"

    async def _stream_sdk(
        self,
        prompt: str,
        system_prompt: str = "",
        context: Optional[List[Dict[str, str]]] = None,
    ) -> AsyncIterator[str]:
        """Stream using google-generativeai SDK with multi-turn and function calling support."""
        import google.generativeai as genai

        # Build contents for multi-turn conversation
        contents = []

        # Add system instruction if provided
        if system_prompt:
            contents.append({"role": "user", "parts": [{"text": f"[System]: {system_prompt}"}]})
            contents.append({"role": "model", "parts": [{"text": "Understood. I'll follow these instructions."}]})

        # Add conversation context if provided
        if context:
            for msg in context:
                role = "user" if msg.get("role") == "user" else "model"
                contents.append({"role": role, "parts": [{"text": msg.get("content", "")}]})

        # Add current prompt
        contents.append({"role": "user", "parts": [{"text": prompt}]})

        # Build tools for function calling
        tools = self._build_gemini_tools() if self._tool_schemas else None

        # Run in executor since SDK is sync
        loop = asyncio.get_event_loop()

        def _generate():
            kwargs = {
                "stream": True,
            }
            if tools:
                kwargs["tools"] = tools
            return self._model.generate_content(
                contents if len(contents) > 1 else prompt,
                **kwargs
            )

        response = await loop.run_in_executor(None, _generate)

        for chunk in response:
            # Check for function calls in the response
            if hasattr(chunk, 'candidates') and chunk.candidates:
                for candidate in chunk.candidates:
                    if hasattr(candidate, 'content') and candidate.content:
                        for part in candidate.content.parts:
                            # Handle function call
                            if hasattr(part, 'function_call') and part.function_call:
                                fc = part.function_call
                                name = fc.name
                                # Convert protobuf args to dict
                                args = dict(fc.args) if hasattr(fc.args, 'items') else {}
                                yield ToolCallParser.format_marker(name, args)
                            # Handle text
                            elif hasattr(part, 'text') and part.text:
                                yield part.text
            # Fallback: direct text access
            elif hasattr(chunk, 'text') and chunk.text:
                yield chunk.text

            await asyncio.sleep(0)  # Yield control for UI

    async def _stream_httpx(
        self,
        prompt: str,
        system_prompt: str = "",
        context: Optional[List[Dict[str, str]]] = None,
    ) -> AsyncIterator[str]:
        """Stream using httpx direct API call with SSE."""
        import httpx

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model_name}:streamGenerateContent?key={self.api_key}"

        # Build contents
        contents = []
        if system_prompt:
            contents.append({"role": "user", "parts": [{"text": f"[System]: {system_prompt}"}]})
            contents.append({"role": "model", "parts": [{"text": "Understood."}]})

        if context:
            for msg in context:
                role = "user" if msg.get("role") == "user" else "model"
                contents.append({"role": role, "parts": [{"text": msg.get("content", "")}]})

        contents.append({"role": "user", "parts": [{"text": prompt}]})

        payload = {
            "contents": contents,
            "generationConfig": {
                "temperature": self.temperature,
                "maxOutputTokens": self.max_output_tokens,
                "topP": 0.95,
                "topK": 40,
            }
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream("POST", url, json=payload) as response:
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
                                    if text:
                                        yield text
                            except json.JSONDecodeError:
                                continue

    async def generate(self, prompt: str, system_prompt: str = "") -> str:
        """Generate complete response (non-streaming)."""
        chunks = []
        async for chunk in self.stream(prompt, system_prompt):
            chunks.append(chunk)
        return "".join(chunks)

    @property
    def is_available(self) -> bool:
        """Check if Gemini is configured."""
        return bool(self.api_key)


__all__ = [
    'GeminiClient',
    'ToolCallParser',
]
