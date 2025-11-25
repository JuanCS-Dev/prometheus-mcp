"""
Bridge - Integration Layer between TUI and Agent System
========================================================

Connects qwen_cli (733 LOC TUI) to qwen_dev_cli (93K LOC agent system).

Design Principles:
- Lazy loading: Import heavy modules only when needed
- Async-first: All operations are async for 60fps
- Observer governance: Alerts via ELP, never blocks
- Minimal surface: Only expose what TUI needs
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import subprocess
from dataclasses import dataclass, field
from enum import Enum
from typing import AsyncIterator, Optional, Dict, Any, Callable, List, Tuple
from pathlib import Path

# Load .env file if exists (check multiple locations)
try:
    from dotenv import load_dotenv
    from pathlib import Path

    # Load from current working directory
    load_dotenv()

    # Also try to load from script directory (for when run from different location)
    script_dir = Path(__file__).parent.parent.parent
    env_file = script_dir / ".env"
    if env_file.exists():
        load_dotenv(env_file)

    # Also load from global credentials file if exists
    global_creds = Path.home() / ".config" / "juancs" / "credentials.json"
    if global_creds.exists():
        try:
            import json
            creds = json.loads(global_creds.read_text())
            for key, value in creds.items():
                if key not in os.environ:  # Don't override existing env vars
                    os.environ[key] = value
        except (json.JSONDecodeError, Exception):
            pass  # Invalid credentials file, ignore

except ImportError:
    pass  # dotenv not installed, use environment variables directly


# =============================================================================
# RISK LEVELS & GOVERNANCE CONFIG
# =============================================================================

class RiskLevel(Enum):
    """Risk levels for governance assessment."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class GovernanceConfig:
    """Governance configuration - Observer mode by default."""
    mode: str = "observer"  # observer | enforcer | off
    block_on_violation: bool = False
    report_format: str = "elp"  # emoji language protocol
    verbosity: str = "minimal"
    alerts: bool = True


# ELP (Emoji Language Protocol) symbols
ELP = {
    "approved": "✅",
    "warning": "⚠️",
    "alert": "🔴",
    "observed": "👀",
    "blocked": "🚫",
    "low": "🟢",
    "medium": "🟡",
    "high": "🟠",
    "critical": "🔴",
    "agent": "🤖",
    "tool": "🔧",
    "thinking": "💭",
    "done": "✓",
    "error": "✗",
}


# =============================================================================
# TOOL CALL PARSER - Extract function calls from LLM responses
# =============================================================================

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


# =============================================================================
# GEMINI CLIENT - Streaming LLM with Function Calling
# =============================================================================

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
        except Exception as e:
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
    ) -> AsyncIterator[str]:
        """
        Stream response from Gemini with optimized settings.

        Args:
            prompt: User's message
            system_prompt: System instructions
            context: Optional conversation history

        Yields:
            Text chunks for 60fps rendering
        """
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
        import json

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


# =============================================================================
# GOVERNANCE OBSERVER - ELP Alerts Without Blocking
# =============================================================================

class GovernanceObserver:
    """
    Governance in Observer mode.

    - Monitors all actions
    - Reports via ELP (Emoji Language Protocol)
    - NEVER blocks (observer mode)
    - Logs for later review
    """

    # Patterns that indicate higher risk
    HIGH_RISK_PATTERNS = [
        r"rm\s+-rf",
        r"sudo\s+",
        r"chmod\s+777",
        r">\s*/dev/",
        r"mkfs\.",
        r"dd\s+if=",
        r"curl.*\|\s*bash",
        r"wget.*\|\s*sh",
    ]

    CRITICAL_PATTERNS = [
        r"rm\s+-rf\s+/",
        r":(){ :\|:& };:",  # Fork bomb
        r">\s*/dev/sda",
        r"/etc/passwd",
        r"/etc/shadow",
    ]

    MEDIUM_RISK_KEYWORDS = [
        "delete", "remove", "drop", "truncate",
        "production", "deploy", "migrate",
        "secret", "password", "token", "key",
        "database", "db", "sql",
    ]

    def __init__(self, config: Optional[GovernanceConfig] = None):
        self.config = config or GovernanceConfig()
        self.observations: List[Dict[str, Any]] = []

    def assess_risk(self, content: str) -> tuple[RiskLevel, str]:
        """
        Assess risk level of content.

        Returns (risk_level, reason).
        """
        content_lower = content.lower()

        # Check critical patterns
        for pattern in self.CRITICAL_PATTERNS:
            if re.search(pattern, content, re.IGNORECASE):
                return RiskLevel.CRITICAL, f"Critical pattern detected: {pattern}"

        # Check high risk patterns
        for pattern in self.HIGH_RISK_PATTERNS:
            if re.search(pattern, content, re.IGNORECASE):
                return RiskLevel.HIGH, f"High-risk pattern: {pattern}"

        # Check medium risk keywords
        for keyword in self.MEDIUM_RISK_KEYWORDS:
            if keyword in content_lower:
                return RiskLevel.MEDIUM, f"Contains sensitive keyword: {keyword}"

        return RiskLevel.LOW, "Standard operation"

    def observe(self, action: str, content: str, agent: str = "user") -> str:
        """
        Observe an action and return ELP report.

        Never blocks - only reports.
        """
        risk, reason = self.assess_risk(content)

        observation = {
            "action": action,
            "content": content[:100],  # Truncate for log
            "agent": agent,
            "risk": risk.value,
            "reason": reason,
        }
        self.observations.append(observation)

        # Generate ELP report
        risk_emoji = ELP.get(risk.value, "❓")

        if risk == RiskLevel.CRITICAL:
            return f"{risk_emoji} CRITICAL - {reason}"
        elif risk == RiskLevel.HIGH:
            return f"{risk_emoji} HIGH RISK - {reason}"
        elif risk == RiskLevel.MEDIUM:
            return f"{ELP['warning']} MEDIUM - {reason}"
        else:
            return f"{ELP['approved']} LOW RISK"

    def get_status_emoji(self) -> str:
        """Get current governance status as emoji."""
        if not self.observations:
            return f"{ELP['observed']} Observer"

        # Check recent observations
        recent = self.observations[-5:] if len(self.observations) > 5 else self.observations
        risks = [obs["risk"] for obs in recent]

        if "critical" in risks:
            return f"{ELP['critical']} Critical"
        elif "high" in risks:
            return f"{ELP['high']} High Risk"
        elif "medium" in risks:
            return f"{ELP['warning']} Caution"
        else:
            return f"{ELP['approved']} Clear"


# =============================================================================
# AGENT MANAGER - Lazy Loading
# =============================================================================

@dataclass
class AgentInfo:
    """Metadata about an agent."""
    name: str
    role: str
    description: str
    capabilities: List[str]
    module_path: str
    class_name: str


# Agent registry - lazy loaded
AGENT_REGISTRY: Dict[str, AgentInfo] = {
    "planner": AgentInfo(
        name="planner",
        role="PLANNER",
        description="Goal-Oriented Action Planning (GOAP)",
        capabilities=["planning", "coordination", "decomposition"],
        module_path="qwen_dev_cli.agents.planner",
        class_name="PlannerAgent",
    ),
    "executor": AgentInfo(
        name="executor",
        role="EXECUTOR",
        description="Secure code execution with sandbox",
        capabilities=["bash", "python", "tools"],
        module_path="qwen_dev_cli.agents.executor_nextgen",
        class_name="ExecutorAgentNextGen",
    ),
    "architect": AgentInfo(
        name="architect",
        role="ARCHITECT",
        description="Architecture analysis and feasibility",
        capabilities=["design", "analysis", "veto"],
        module_path="qwen_dev_cli.agents.architect",
        class_name="ArchitectAgent",
    ),
    "reviewer": AgentInfo(
        name="reviewer",
        role="REVIEWER",
        description="Enterprise code review",
        capabilities=["review", "analysis", "suggestions"],
        module_path="qwen_dev_cli.agents.reviewer",
        class_name="ReviewerAgent",
    ),
    "explorer": AgentInfo(
        name="explorer",
        role="EXPLORER",
        description="Codebase exploration and navigation",
        capabilities=["search", "navigate", "understand"],
        module_path="qwen_dev_cli.agents.explorer",
        class_name="ExplorerAgent",
    ),
    "refactorer": AgentInfo(
        name="refactorer",
        role="REFACTORER",
        description="Code refactoring and improvement",
        capabilities=["refactor", "improve", "transform"],
        module_path="qwen_dev_cli.agents.refactorer",
        class_name="RefactorerAgent",
    ),
    "testing": AgentInfo(
        name="testing",
        role="TESTING",
        description="Test generation and execution",
        capabilities=["generate_tests", "run_tests", "coverage"],
        module_path="qwen_dev_cli.agents.testing",
        class_name="TestingAgent",
    ),
    "security": AgentInfo(
        name="security",
        role="SECURITY",
        description="Security analysis (OWASP)",
        capabilities=["scan", "audit", "vulnerabilities"],
        module_path="qwen_dev_cli.agents.security",
        class_name="SecurityAgent",
    ),
    "documentation": AgentInfo(
        name="documentation",
        role="DOCUMENTATION",
        description="Documentation generation",
        capabilities=["docstrings", "readme", "api_docs"],
        module_path="qwen_dev_cli.agents.documentation",
        class_name="DocumentationAgent",
    ),
    "performance": AgentInfo(
        name="performance",
        role="PERFORMANCE",
        description="Performance profiling and optimization",
        capabilities=["profile", "optimize", "benchmark"],
        module_path="qwen_dev_cli.agents.performance",
        class_name="PerformanceAgent",
    ),
    "devops": AgentInfo(
        name="devops",
        role="DEVOPS",
        description="Infrastructure and deployment",
        capabilities=["docker", "kubernetes", "ci_cd"],
        module_path="qwen_dev_cli.agents.devops_agent",
        class_name="DevOpsAgent",
    ),
    "justica": AgentInfo(
        name="justica",
        role="GOVERNANCE",
        description="Constitutional governance",
        capabilities=["evaluate", "approve", "block"],
        module_path="qwen_dev_cli.agents.justica_agent",
        class_name="JusticaIntegratedAgent",
    ),
    "sofia": AgentInfo(
        name="sofia",
        role="COUNSELOR",
        description="Ethical counsel and wisdom",
        capabilities=["counsel", "ethics", "reflection"],
        module_path="qwen_dev_cli.agents.sofia_agent",
        class_name="SofiaIntegratedAgent",
    ),
    "data": AgentInfo(
        name="data",
        role="DATABASE",
        description="Database optimization and analysis",
        capabilities=["schema_analysis", "query_optimization", "migration"],
        module_path="qwen_dev_cli.agents.data_agent_production",
        class_name="DataAgent",
    ),
}


# =============================================================================
# AGENT ROUTER - Automatic Intent Detection & Routing (Claude Code Parity)
# =============================================================================

class AgentRouter:
    """
    Intelligent request router that detects user intent and routes to agents.

    Claude Code Parity: Implements automatic agent invocation like Claude Code's
    subagent system - users can naturally describe tasks and the router decides
    which specialized agent should handle it.

    Philosophy:
        "The user shouldn't need to know which agent does what - just ask."

    Routing Strategy:
        1. Keyword matching (fast, deterministic)
        2. Intent patterns (regex-based)
        3. Confidence scoring (multiple matches = ask user)
    """

    # Intent patterns → agent mapping with confidence weights
    # Enhanced for PT-BR and EN detection
    INTENT_PATTERNS: Dict[str, List[tuple]] = {
        "planner": [
            (r"\b(plan[oe]?|planeja[r]?|planejamento|cri[ae]\s*(um\s*)?plano)\b", 0.9),
            (r"\b(break\s*down|decompo[ns]|roadmap|estratégia)\b", 0.9),
            (r"\b(como\s*(fa[zç]o|implement|começ)|how\s*(to|do\s*i|should)|steps?\s*to)\b", 0.75),
            (r"\b(preciso\s*(de\s*)?(um\s*)?plano|help\s*me\s*(plan|with))\b", 0.8),
            (r"\bimplementa[rç].*passo\b", 0.85),
        ],
        "executor": [
            (r"\b(execut[ae]|run|roda[r]?|execute|bash|shell|terminal)\b", 0.9),
            (r"\b(comando?s?|command)\b", 0.75),
            (r"\b(pip\s+install|npm\s+(install|run)|make|cargo|go\s+(run|build))\b", 0.95),
            (r"\b(git\s+(status|diff|add|commit|push|pull|clone|log))\b", 0.9),
            (r"\b(pytest|unittest|jest|npm\s+test|testa[r]?\s+)\b", 0.85),
        ],
        "architect": [
            (r"\b(arquitetur[a]?|architect(ure)?|design\s*(pattern)?)\b", 0.9),
            (r"\b(estrutur[ae]|system\s*design|analisa[r]?\s*(a\s*)?arquitetura)\b", 0.85),
            (r"\b(diagrama?|uml|flowchart|fluxo(grama)?)\b", 0.85),
            (r"\b(clean\s*architect|hexagonal|onion|layered|microservice)\b", 0.95),
            (r"\b(trade-?off|decision|escolh[ae]\s*(entre|de\s*design))\b", 0.7),
        ],
        "reviewer": [
            (r"\b(review|revis[ae]|code\s*review)\b", 0.9),
            (r"\b(analys[ei]s?\s*(de\s*)?(c[oó]digo)?|análise)\b", 0.8),
            (r"\b(qualidade|quality|best\s*practice|boas\s*pr[aá]ticas)\b", 0.8),
            (r"\b(pr\s*review|pull\s*request|merge\s*request)\b", 0.95),
            (r"\b(code\s*smell|technical\s*debt|d[ií]vida\s*t[eé]cnica)\b", 0.85),
        ],
        "explorer": [
            (r"\b(explor[ae]|search|busc[ae]|find|encontr[ae]|localiz[ae])\b", 0.85),
            (r"\b(onde\s*(est[aá]|fica)|where\s*(is|are)|acha[re]?)\b", 0.8),
            (r"\b(naveg[ae]|codebase|estrutura\s*(do\s*)?(projeto|c[oó]digo))\b", 0.75),
            (r"\b(grep|ripgrep|ag\s|search\s*for|procur[ae])\b", 0.9),
        ],
        "refactorer": [
            (r"\b(refactor|refatora|refactoring|melhora[re]?\s*(o\s*)?(c[oó]digo)?)\b", 0.9),
            (r"\b(clean\s*(up)?|limp[ae]|simplif[iy])\b", 0.75),
            (r"\b(extract|extrai|mover?\s*para|move\s*to)\b", 0.7),
            (r"\b(rename|renomea|dry|don'?t\s*repeat)\b", 0.8),
        ],
        "testing": [
            (r"\b(test[aes]?|testa[re]?|unittest|pytest|coverage|cobertura)\b", 0.9),
            (r"\b(tdd|bdd|test\s*driven|behavior\s*driven)\b", 0.95),
            (r"\b(mock|stub|fixture|parametriz[ae])\b", 0.85),
            (r"\b(integration\s*test|unit\s*test|e2e|end.to.end)\b", 0.9),
            (r"\b(unit[aá]rio|cria[r]?\s*testes?|write\s*tests?)\b", 0.9),  # PT-BR fix
        ],
        "security": [
            (r"\b(security|seguran[çc]a|owasp|vulnerabil\w*|cve)\b", 0.95),
            (r"\b(injection|xss|csrf|sqli|auth[nz]?|exploit)\b", 0.9),
            (r"\b(audit|auditoria|pentest|penetration|scan)\b", 0.85),
            (r"\b(sanitiz|escap[ae]|valid[ae]|malware|trojan)\b", 0.75),
            (r"\bquais\s*(vulner|falh|brech)\w*", 0.9),
        ],
        "documentation": [
            (r"\b(document[ae]?|documenta[çc][aã]o|docs?|readme)\b", 0.9),
            (r"\b(docstring|jsdoc|pydoc|api\s*doc)\b", 0.95),
            (r"\b(coment[aá]rio|comment|explain|explic[ae])\b", 0.7),
            (r"\b(changelog|release\s*notes)\b", 0.85),
        ],
        "performance": [
            (r"\b(perform|performance|desempenho|otimiz[ae]|optim[iz])\b", 0.9),
            (r"\b(profil[ae]|profiling|benchmark|cprofile|perf)\b", 0.95),
            (r"\b(lento|slow|fast|r[aá]pido|speed\s*up|acelera)\b", 0.75),
            (r"\b(memory|mem[oó]ria|leak|cpu|io\s*bound)\b", 0.8),
        ],
        "devops": [
            (r"\b(devops|docker|kubernetes|k8s|ci\s*/?\s*cd|pipeline)\b", 0.95),
            (r"\b(deploy|implant[ae]|infra|terraform|ansible)\b", 0.9),
            (r"\b(container|imagem|image|pod|service)\b", 0.8),
            (r"\b(github\s*actions?|gitlab\s*ci|jenkins|circleci)\b", 0.95),
        ],
        "data": [
            (r"\b(database|banco\s*de\s*dados)\b", 0.9),
            (r"\b(sql|query|consulta)\b", 0.92),  # Higher priority for SQL-specific
            (r"\b(schema|esquema|migration|migra[çc][aã]o)\b", 0.85),
            (r"\b(orm|sqlalchemy|django\s*orm|prisma|sequelize)\b", 0.9),
            (r"\b(index|[ií]ndice|foreign\s*key|constraint)\b", 0.8),
            (r"\botimiza.*\b(query|sql|consulta)\b", 0.95),  # "otimiza query" → data
        ],
        "justica": [
            (r"\b(justi[çc]a|governance|governan[çc]a|constitu[çi])\b", 0.95),
            (r"\b(compliance|conformidade|regulat[oó]rio)\b", 0.85),
            (r"\b(v[eé]rtice|article|artigo)\b", 0.7),
        ],
        "sofia": [
            (r"\b(sofia|counsel|conselho|[eé]tic[ao]|ethical|sabedoria|wisdom)\b", 0.95),
            (r"\b(filosof|philosophy|moral|virtue|virtude)\b", 0.85),
            (r"\b(socrat|dile[mn]ma|reflection|reflex[aã]o)\b", 0.8),
        ],
    }

    # Keywords that indicate NOT to route (general chat)
    NO_ROUTE_PATTERNS = [
        r"^(oi|ol[aá]|hi|hello|hey|e\s*a[ií])\b",  # Greetings
        r"^(obrigad[oa]|thanks?|valeu|vlw)\b",      # Thanks
        r"^(ok|certo|entend[io]|got\s*it)\b",      # Acknowledgments
        # Removed \?$ - questions can still be routed based on intent
    ]

    # Minimum confidence to auto-route (below this, ask user)
    MIN_CONFIDENCE = 0.7

    def __init__(self):
        import re
        self._compiled_patterns: Dict[str, List[tuple]] = {}
        self._no_route_patterns = [re.compile(p, re.IGNORECASE) for p in self.NO_ROUTE_PATTERNS]

        # Pre-compile all patterns
        for agent, patterns in self.INTENT_PATTERNS.items():
            self._compiled_patterns[agent] = [
                (re.compile(pattern, re.IGNORECASE), weight)
                for pattern, weight in patterns
            ]

    def should_route(self, message: str) -> bool:
        """Check if message should be considered for routing."""
        # Skip very short messages
        if len(message.strip()) < 5:
            return False

        # Skip messages that look like general chat
        for pattern in self._no_route_patterns:
            if pattern.search(message):
                return False

        return True

    def detect_intent(self, message: str) -> List[tuple]:
        """
        Detect which agent(s) should handle this message.

        Returns:
            List of (agent_name, confidence) tuples, sorted by confidence desc
        """
        if not self.should_route(message):
            return []

        scores: Dict[str, float] = {}

        for agent, patterns in self._compiled_patterns.items():
            max_score = 0.0
            for compiled_pattern, weight in patterns:
                if compiled_pattern.search(message):
                    max_score = max(max_score, weight)

            if max_score > 0:
                scores[agent] = max_score

        # Sort by confidence
        sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return sorted_scores

    def route(self, message: str) -> Optional[tuple]:
        """
        Route message to best agent.

        Returns:
            (agent_name, confidence) if confident routing found
            None if no clear routing (let LLM handle naturally)
        """
        intents = self.detect_intent(message)

        if not intents:
            return None

        best_agent, best_confidence = intents[0]

        # Only route if confidence is high enough
        if best_confidence >= self.MIN_CONFIDENCE:
            return (best_agent, best_confidence)

        return None

    def get_routing_suggestion(self, message: str) -> Optional[str]:
        """
        Get a suggestion message for ambiguous routing.

        Returns markdown message if multiple agents could handle this.
        """
        intents = self.detect_intent(message)

        # If multiple high-confidence matches, suggest options
        high_conf = [(a, c) for a, c in intents if c >= 0.6]

        if len(high_conf) > 1:
            suggestions = [f"- `/{a}` ({int(c*100)}%)" for a, c in high_conf[:3]]
            return (
                "🤔 Multiple agents could help:\n" +
                "\n".join(suggestions) +
                "\n\nType one of the commands or ask naturally."
            )

        return None


class AgentManager:
    """
    Lazy-loading agent manager.

    Only imports agents when first used to keep startup fast.
    """

    def __init__(self, llm_client: Optional[GeminiClient] = None):
        self.llm_client = llm_client or GeminiClient()
        self._agents: Dict[str, Any] = {}
        self._load_errors: Dict[str, str] = {}
        self.router = AgentRouter()  # Add router instance

    @property
    def available_agents(self) -> List[str]:
        """List of available agent names."""
        return list(AGENT_REGISTRY.keys())

    def get_agent_info(self, name: str) -> Optional[AgentInfo]:
        """Get agent metadata."""
        return AGENT_REGISTRY.get(name)

    async def get_agent(self, name: str) -> Optional[Any]:
        """
        Get or create agent instance.

        Lazy loads the agent module on first use.
        """
        if name in self._agents:
            return self._agents[name]

        if name in self._load_errors:
            return None

        info = AGENT_REGISTRY.get(name)
        if not info:
            self._load_errors[name] = f"Unknown agent: {name}"
            return None

        try:
            # Dynamic import
            import importlib
            module = importlib.import_module(info.module_path)
            agent_class = getattr(module, info.class_name)

            # Create instance - pass LLM client if supported
            agent = agent_class()
            self._agents[name] = agent
            return agent

        except ImportError as e:
            self._load_errors[name] = f"Import error: {e}"
            return None
        except Exception as e:
            self._load_errors[name] = f"Init error: {e}"
            return None

    async def invoke_agent(
        self,
        name: str,
        task: str,
        context: Optional[Dict[str, Any]] = None
    ) -> AsyncIterator[str]:
        """
        Invoke an agent and stream response.

        Falls back to LLM if agent unavailable.
        """
        agent = await self.get_agent(name)

        if agent is None:
            # Fallback: use LLM directly with agent-specific prompt
            info = AGENT_REGISTRY.get(name)
            if info:
                system_prompt = f"You are a {info.role}. {info.description}. Capabilities: {', '.join(info.capabilities)}."
                async for chunk in self.llm_client.stream(task, system_prompt):
                    yield chunk
            else:
                yield f"❌ Agent '{name}' not available"
            return

        # Try streaming interface first
        if hasattr(agent, 'execute_streaming'):
            try:
                async for chunk in agent.execute_streaming(task, context or {}):
                    yield chunk
                return
            except Exception as e:
                yield f"⚠️ Streaming failed: {e}\n"

        # Fallback to sync execute
        if hasattr(agent, 'execute'):
            try:
                from dataclasses import dataclass

                @dataclass
                class SimpleTask:
                    request: str
                    context: Dict[str, Any]

                result = await agent.execute(SimpleTask(request=task, context=context or {}))
                if hasattr(result, 'data'):
                    yield str(result.data)
                else:
                    yield str(result)
                return
            except Exception as e:
                yield f"❌ Agent error: {e}"
                return

        yield f"❌ Agent '{name}' has no execute method"




# =============================================================================
# TOOL REGISTRY - 47 Tools Integration
# =============================================================================

class ToolBridge:
    """
    Bridge to 47 tools from qwen_dev_cli.

    Lazy loading to keep startup fast.

    Categories:
    - File Operations (12): read, write, edit, list, delete, move, copy, mkdir, insert
    - Terminal (9): cd, ls, pwd, mkdir, rm, cp, mv, touch, cat
    - Execution (2): bash, bash_hardened
    - Search (2): search_files, get_directory_tree
    - Git (2): git_status, git_diff
    - Context (3): get_context, save_session, restore_backup
    - Web (6): web_search, fetch_url, download_file, http_request, package_search, search_docs
    """

    def __init__(self):
        self._registry = None
        self._load_errors: List[str] = []

    @property
    def registry(self):
        """Lazy load tool registry."""
        if self._registry is None:
            self._registry = self._create_registry()
        return self._registry

    def _create_registry(self):
        """Create and populate tool registry."""
        try:
            from qwen_dev_cli.tools.base import ToolRegistry

            registry = ToolRegistry()

            # File Operations (12 tools)
            try:
                from qwen_dev_cli.tools.file_ops import (
                    ReadFileTool, WriteFileTool, EditFileTool,
                    ListDirectoryTool, DeleteFileTool
                )
                from qwen_dev_cli.tools.file_mgmt import (
                    MoveFileTool, CopyFileTool, CreateDirectoryTool,
                    ReadMultipleFilesTool, InsertLinesTool
                )

                for tool_cls in [
                    ReadFileTool, WriteFileTool, EditFileTool,
                    ListDirectoryTool, DeleteFileTool,
                    MoveFileTool, CopyFileTool, CreateDirectoryTool,
                    ReadMultipleFilesTool, InsertLinesTool
                ]:
                    try:
                        registry.register(tool_cls())
                    except Exception as e:
                        self._load_errors.append(f"file_ops: {e}")
            except ImportError as e:
                self._load_errors.append(f"file_ops import: {e}")

            # Terminal (9 tools)
            try:
                from qwen_dev_cli.tools.terminal import (
                    CdTool, LsTool, PwdTool, MkdirTool, RmTool,
                    CpTool, MvTool, TouchTool, CatTool
                )

                for tool_cls in [
                    CdTool, LsTool, PwdTool, MkdirTool, RmTool,
                    CpTool, MvTool, TouchTool, CatTool
                ]:
                    try:
                        registry.register(tool_cls())
                    except Exception as e:
                        self._load_errors.append(f"terminal: {e}")
            except ImportError as e:
                self._load_errors.append(f"terminal import: {e}")

            # Execution (2 tools)
            try:
                from qwen_dev_cli.tools.exec_hardened import BashCommandTool
                registry.register(BashCommandTool())
            except ImportError as e:
                self._load_errors.append(f"exec import: {e}")

            # Search (2 tools)
            try:
                from qwen_dev_cli.tools.search import SearchFilesTool, GetDirectoryTreeTool
                registry.register(SearchFilesTool())
                registry.register(GetDirectoryTreeTool())
            except ImportError as e:
                self._load_errors.append(f"search import: {e}")

            # Git (2 tools)
            try:
                from qwen_dev_cli.tools.git_ops import GitStatusTool, GitDiffTool
                registry.register(GitStatusTool())
                registry.register(GitDiffTool())
            except ImportError as e:
                self._load_errors.append(f"git import: {e}")

            # Context (3 tools)
            try:
                from qwen_dev_cli.tools.context import (
                    GetContextTool, SaveSessionTool, RestoreBackupTool
                )
                registry.register(GetContextTool())
                registry.register(SaveSessionTool())
                registry.register(RestoreBackupTool())
            except ImportError as e:
                self._load_errors.append(f"context import: {e}")

            # Web (6 tools)
            try:
                from qwen_dev_cli.tools.web_search import WebSearchTool, SearchDocumentationTool
                from qwen_dev_cli.tools.web_access import (
                    FetchURLTool, DownloadFileTool, HTTPRequestTool, PackageSearchTool
                )

                for tool_cls in [
                    WebSearchTool, SearchDocumentationTool,
                    FetchURLTool, DownloadFileTool, HTTPRequestTool, PackageSearchTool
                ]:
                    try:
                        registry.register(tool_cls())
                    except Exception as e:
                        self._load_errors.append(f"web: {e}")
            except ImportError as e:
                self._load_errors.append(f"web import: {e}")

            # Claude Code Parity Tools (7 tools: glob, ls, multi_edit, web_fetch, web_search, todo_read, todo_write)
            try:
                from qwen_dev_cli.tools.claude_parity_tools import get_claude_parity_tools

                for tool in get_claude_parity_tools():
                    try:
                        registry.register(tool)
                    except Exception as e:
                        self._load_errors.append(f"parity: {e}")
            except ImportError as e:
                self._load_errors.append(f"claude_parity import: {e}")

            return registry

        except ImportError:
            # Return empty registry if qwen_dev_cli not available
            from dataclasses import dataclass

            @dataclass
            class MinimalRegistry:
                tools: Dict[str, Any] = None

                def __post_init__(self):
                    self.tools = self.tools or {}

                def get_all(self):
                    return self.tools

                def get(self, name):
                    return self.tools.get(name)

                def get_schemas(self):
                    return []

            return MinimalRegistry()

    def get_tool(self, name: str):
        """Get tool by name."""
        return self.registry.get(name)

    def list_tools(self) -> List[str]:
        """List all available tool names."""
        return list(self.registry.get_all().keys())

    def get_tool_count(self) -> int:
        """Get number of loaded tools."""
        return len(self.registry.get_all())

    async def execute_tool(self, name: str, **kwargs) -> Dict[str, Any]:
        """Execute a tool by name with given parameters."""
        tool = self.get_tool(name)
        if not tool:
            return {"success": False, "error": f"Tool not found: {name}"}

        try:
            result = await tool._execute_validated(**kwargs)
            return {
                "success": result.success,
                "data": result.data,
                "error": result.error,
                "metadata": result.metadata
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_schemas_for_llm(self) -> List[Dict]:
        """Get tool schemas formatted for LLM function calling."""
        return self.registry.get_schemas()


# =============================================================================
# COMMAND PALETTE - Fuzzy Search Commands
# =============================================================================

class CommandPaletteBridge:
    """
    Bridge to CommandPalette with fuzzy search.

    Provides command discovery and execution.
    """

    def __init__(self):
        self._palette = None

    @property
    def palette(self):
        """Lazy load command palette."""
        if self._palette is None:
            try:
                from qwen_dev_cli.ui.command_palette import CommandPalette, Command
                self._palette = CommandPalette()

                # Register agent commands
                agent_commands = [
                    ("plan", "Plan Task", "Create a plan using GOAP", "agent"),
                    ("execute", "Execute Code", "Run code safely in sandbox", "agent"),
                    ("architect", "Architecture", "Analyze architecture", "agent"),
                    ("review", "Code Review", "Enterprise code review", "agent"),
                    ("explore", "Explore", "Search and navigate codebase", "agent"),
                    ("refactor", "Refactor", "Improve code structure", "agent"),
                    ("test", "Test", "Generate and run tests", "agent"),
                    ("security", "Security", "OWASP security scan", "agent"),
                    ("docs", "Documentation", "Generate documentation", "agent"),
                    ("perf", "Performance", "Profile and optimize", "agent"),
                    ("devops", "DevOps", "Infrastructure management", "agent"),
                ]

                for cmd_id, label, desc, category in agent_commands:
                    self._palette.register_command(Command(
                        id=f"agent.{cmd_id}",
                        label=label,
                        description=desc,
                        category=category,
                        keybinding=f"/{cmd_id}"
                    ))

            except ImportError:
                # Minimal fallback
                self._palette = MinimalCommandPalette()

        return self._palette

    def search(self, query: str, max_results: int = 10) -> List[Dict]:
        """Fuzzy search commands."""
        return self.palette.get_suggestions(query, max_results)

    def execute(self, command_id: str):
        """Execute command by ID."""
        return self.palette.execute(command_id)


class MinimalCommandPalette:
    """Minimal fallback command palette."""

    def __init__(self):
        self.commands = []
        self.recent_commands = []

    def get_suggestions(self, query: str, max_results: int = 10) -> List[Dict]:
        return []

    def execute(self, command_id: str):
        return {"status": "no_handler", "message": "Minimal palette"}

    def register_command(self, command):
        self.commands.append(command)


# =============================================================================
# AUTOCOMPLETE - Fuzzy Matching with @ File Picker
# =============================================================================

class AutocompleteBridge:
    """
    Bridge to ContextAwareCompleter with fuzzy matching.

    Features:
    - Slash command completion (/)
    - File path completion (@) - Claude Code style
    - Tool name completion
    - History-based suggestions
    """

    # Default ignore patterns for file scanning
    IGNORE_PATTERNS = {
        '__pycache__', '.git', '.svn', '.hg', 'node_modules',
        '.venv', 'venv', 'env', '.tox', '.mypy_cache',
        '.pytest_cache', '.coverage', 'htmlcov', 'dist', 'build',
        '*.egg-info', '.eggs', '.idea', '.vscode', '*.pyc', '*.pyo',
        '.DS_Store', 'Thumbs.db', '*.swp', '*.swo', '*~',
        '.archive', '.backup', '.bak',
    }

    # File type icons
    FILE_ICONS = {
        '.py': '🐍', '.js': '📜', '.ts': '💠', '.jsx': '📜', '.tsx': '💠',
        '.rs': '🦀', '.go': '🔵', '.md': '📝', '.json': '📋',
        '.yaml': '⚙️', '.yml': '⚙️', '.toml': '⚙️', '.html': '🌐',
        '.css': '🎨', '.sql': '🗃️', '.sh': '💻', '.bash': '💻',
    }

    def __init__(self, tool_bridge: Optional['ToolBridge'] = None):
        self.tool_bridge = tool_bridge
        self._completer = None
        self._suggestion_cache: Dict[str, str] = {}
        self._file_cache: List[str] = []
        self._file_cache_valid = False
        self._recent_files: List[str] = []

    def add_recent_file(self, file_path: str) -> None:
        """Track a recently accessed file for priority in @ completions."""
        if file_path in self._recent_files:
            self._recent_files.remove(file_path)
        self._recent_files.insert(0, file_path)
        self._recent_files = self._recent_files[:50]  # Keep last 50

    def _scan_files(self, root: Path = None, max_files: int = 2000) -> List[str]:
        """Scan project files for @ completion."""
        if self._file_cache_valid and self._file_cache:
            return self._file_cache

        import fnmatch
        root = root or Path.cwd()
        files = []

        def should_ignore(path: Path) -> bool:
            name = path.name
            for pattern in self.IGNORE_PATTERNS:
                if fnmatch.fnmatch(name, pattern):
                    return True
            return False

        def scan_dir(dir_path: Path, depth: int = 0):
            if depth > 8 or len(files) >= max_files:
                return
            try:
                for entry in sorted(dir_path.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower())):
                    if len(files) >= max_files:
                        break
                    if should_ignore(entry):
                        continue
                    if entry.is_dir():
                        scan_dir(entry, depth + 1)
                    elif entry.is_file():
                        try:
                            rel_path = str(entry.relative_to(root))
                            files.append(rel_path)
                        except ValueError:
                            pass
            except (PermissionError, OSError):
                pass

        scan_dir(root)
        self._file_cache = files
        self._file_cache_valid = True
        return files

    def _get_file_icon(self, filename: str) -> str:
        """Get icon for file based on extension."""
        suffix = Path(filename).suffix.lower()
        return self.FILE_ICONS.get(suffix, '📄')

    def _get_file_completions(self, query: str, max_results: int = 15) -> List[Dict]:
        """Get file completions for @ query."""
        files = self._scan_files()
        query_lower = query.lower()

        scored = []
        for file_path in files:
            filename = Path(file_path).name.lower()

            # Calculate score
            score = 0.0
            is_recent = file_path in self._recent_files

            if not query:
                # Empty query - show recent files first, then alphabetically
                score = 100.0 if is_recent else 1.0  # Small score for non-recent
            elif query_lower == filename:
                score = 100.0
            elif filename.startswith(query_lower):
                score = 90.0 * (len(query) / len(filename))
            elif query_lower in filename:
                score = 70.0 * (len(query) / len(filename))
            elif query_lower in file_path.lower():
                score = 50.0 * (len(query) / len(file_path))
            else:
                # Fuzzy match
                qi = 0
                for c in filename:
                    if qi < len(query_lower) and c == query_lower[qi]:
                        score += 1.0
                        qi += 1
                if qi == len(query_lower):
                    score = 30.0 * (score / len(filename))
                else:
                    continue  # No match

            # Boost recent files
            if is_recent:
                score *= 1.5

            if score > 0:
                scored.append((score, file_path))

        # Sort by score descending
        scored.sort(key=lambda x: x[0], reverse=True)

        completions = []
        for score, file_path in scored[:max_results]:
            filename = Path(file_path).name
            parent = str(Path(file_path).parent)
            icon = self._get_file_icon(filename)
            is_recent = file_path in self._recent_files

            completions.append({
                "text": f"@{file_path}",
                "display": f"{icon} {'★ ' if is_recent else ''}{filename}",
                "description": parent if parent != '.' else '',
                "type": "file",
                "score": score,
            })

        return completions

    def get_completions(self, text: str, max_results: int = 10) -> List[Dict]:
        """Get completions for text with fuzzy matching."""
        if not text:
            return []

        # Check for @ file picker trigger
        at_pos = None
        for i in range(len(text) - 1, -1, -1):
            if text[i] == '@' and (i == 0 or text[i-1].isspace()):
                at_pos = i
                break

        if at_pos is not None:
            # @ file picker mode
            query = text[at_pos + 1:]
            return self._get_file_completions(query, max_results)

        completions = []
        text_lower = text.lower()

        # Tool completions
        if self.tool_bridge:
            for tool_name in self.tool_bridge.list_tools():
                score = self._fuzzy_score(text_lower, tool_name)
                if score > 0:
                    completions.append({
                        "text": tool_name,
                        "display": f"🔧 {tool_name}",
                        "type": "tool",
                        "score": score + 10,  # Boost tools
                    })

        # Command completions - Claude Code parity (37 commands)
        slash_commands = [
            # Navigation & Help
            ("/help", "Show help"),
            ("/clear", "Clear screen"),
            ("/quit", "Exit"),
            ("/exit", "Exit"),

            # Execution
            ("/run", "Execute bash"),
            ("/read", "Read file"),

            # Discovery
            ("/agents", "List agents"),
            ("/status", "Show status"),
            ("/tools", "List tools"),
            ("/palette", "Command palette"),
            ("/history", "Command history"),

            # Context Management (Claude Code parity)
            ("/context", "Show context"),
            ("/context-clear", "Clear context"),
            ("/compact", "Compact context"),
            ("/cost", "Token usage stats"),
            ("/tokens", "Token usage"),

            # Session Management (Claude Code parity)
            ("/save", "Save session"),
            ("/resume", "Resume session"),
            ("/sessions", "List sessions"),
            ("/checkpoint", "Create checkpoint"),
            ("/rewind", "Rewind to checkpoint"),
            ("/export", "Export conversation"),

            # Project (Claude Code parity)
            ("/init", "Initialize project"),
            ("/model", "Select model"),
            ("/doctor", "Check health"),
            ("/permissions", "Manage permissions"),

            # Todo Management (Claude Code parity)
            ("/todos", "List todos"),
            ("/todo", "Add todo"),

            # Agent Commands
            ("/plan", "Plan task"),
            ("/execute", "Execute code"),
            ("/architect", "Architecture"),
            ("/review", "Code review"),
            ("/explore", "Explore code"),
            ("/refactor", "Refactor"),
            ("/test", "Run tests"),
            ("/security", "Security scan"),
            ("/docs", "Generate docs"),
            ("/perf", "Performance"),
            ("/devops", "DevOps"),

            # Governance & Counsel Agents
            ("/justica", "Constitutional governance"),
            ("/sofia", "Ethical counsel"),

            # Data Agent
            ("/data", "Database analysis"),

            # Advanced (Claude Code parity)
            ("/sandbox", "Enable sandbox"),
            ("/hooks", "Manage hooks"),
            ("/mcp", "MCP servers"),

            # Agent Router (NEW)
            ("/router", "Toggle auto-routing"),
            ("/router-status", "Show routing config"),
            ("/route", "Manually route message"),

            # Background Tasks (Claude Code /bashes parity)
            ("/bashes", "List background tasks"),
            ("/bg", "Start background task"),
            ("/kill", "Kill background task"),

            # Notebook Tools (Claude Code parity)
            ("/notebook", "Read notebook file"),

            # Plan Mode (Claude Code parity - WAVE 4)
            ("/plan-mode", "Enter plan mode"),
            ("/plan-status", "Plan mode status"),
            ("/plan-note", "Add plan note"),
            ("/plan-exit", "Exit plan mode"),
            ("/plan-approve", "Approve plan"),

            # PR Creation (Claude Code parity - WAVE 4)
            ("/pr", "Create pull request"),
            ("/pr-draft", "Create draft PR"),

            # Auth Management (Claude Code parity - WAVE 5)
            ("/login", "Login to provider"),
            ("/logout", "Logout from provider"),
            ("/auth", "Show auth status"),

            # Memory (Claude Code parity - WAVE 5)
            ("/memory", "View/manage memory"),
            ("/remember", "Add note to memory"),

            # Image/PDF Reading (Claude Code parity - WAVE 5)
            ("/image", "Read image file"),
            ("/pdf", "Read PDF file"),

            # WAVE 6: Beyond Claude Code Parity
            ("/audit", "View audit log"),
            ("/diff", "Diff preview"),
            ("/backup", "Create/list backups"),
            ("/restore", "Restore from backup"),
            ("/undo", "Undo last operation"),
            ("/redo", "Redo operation"),
            ("/undo-stack", "View undo stack"),
            ("/secrets", "Scan for secrets"),
            ("/secrets-staged", "Scan staged files"),
        ]

        for cmd, desc in slash_commands:
            score = self._fuzzy_score(text_lower, cmd)
            if score > 0:
                completions.append({
                    "text": cmd,
                    "display": f"⚡ {cmd}",
                    "description": desc,
                    "type": "command",
                    "score": score + 20,  # Boost commands
                })

        # Sort by score
        completions.sort(key=lambda x: x["score"], reverse=True)
        return completions[:max_results]

    def _fuzzy_score(self, query: str, target: str) -> float:
        """Calculate fuzzy match score."""
        if not query:
            return 0.0

        target_lower = target.lower()

        # Exact match
        if query == target_lower:
            return 100.0

        # Prefix match (highest non-exact score)
        if target_lower.startswith(query):
            return 90.0 * (len(query) / len(target))

        # Substring match
        if query in target_lower:
            return 70.0 * (len(query) / len(target))

        # Character sequence match (fuzzy)
        score = 0.0
        query_idx = 0
        for char in target_lower:
            if query_idx < len(query) and char == query[query_idx]:
                score += 1.0
                query_idx += 1

        if query_idx == len(query):
            return 50.0 * (score / len(target))

        return 0.0

    def get_suggestion(self, text: str) -> Optional[str]:
        """Get inline suggestion (Fish-style)."""
        if text in self._suggestion_cache:
            return self._suggestion_cache[text]

        completions = self.get_completions(text, max_results=1)
        if completions and completions[0]["score"] > 50:
            suggestion = completions[0]["text"]
            if suggestion.startswith(text):
                result = suggestion[len(text):]
                self._suggestion_cache[text] = result
                return result

        return None


# =============================================================================
# HISTORY MANAGEMENT
# =============================================================================

class HistoryManager:
    """
    Command and conversation history management.

    Features:
    - Persistent command history
    - Session-based conversation context
    - Smart history search
    """

    def __init__(self, max_commands: int = 1000, max_context: int = 50):
        self.max_commands = max_commands
        self.max_context = max_context
        self.commands: List[str] = []
        self.context: List[Dict[str, str]] = []  # For multi-turn conversations
        self._history_file = Path.home() / ".qwen_cli_history"
        self._load_history()

    def _load_history(self):
        """Load history from file."""
        try:
            if self._history_file.exists():
                lines = self._history_file.read_text().strip().split("\n")
                self.commands = lines[-self.max_commands:]
        except Exception:
            pass

    def _save_history(self):
        """Save history to file."""
        try:
            self._history_file.write_text("\n".join(self.commands[-self.max_commands:]))
        except Exception:
            pass

    def add_command(self, command: str):
        """Add command to history."""
        if command and command != self.commands[-1] if self.commands else True:
            self.commands.append(command)
            self._save_history()

    def add_context(self, role: str, content: str):
        """Add message to conversation context."""
        self.context.append({"role": role, "content": content})
        # Keep context within limits
        if len(self.context) > self.max_context:
            self.context = self.context[-self.max_context:]

    def get_context(self) -> List[Dict[str, str]]:
        """Get conversation context for LLM."""
        return self.context.copy()

    def clear_context(self):
        """Clear conversation context."""
        self.context.clear()

    def search_history(self, query: str) -> List[str]:
        """Search command history."""
        if not query:
            return self.commands[-10:]

        results = []
        query_lower = query.lower()

        for cmd in reversed(self.commands):
            if query_lower in cmd.lower():
                results.append(cmd)
                if len(results) >= 10:
                    break

        return results

    def get_recent(self, count: int = 10) -> List[str]:
        """Get recent commands."""
        return self.commands[-count:]

    # =========================================================================
    # SESSION PERSISTENCE (Claude Code Parity - /resume, /rewind)
    # =========================================================================

    def save_session(self, session_id: str = None) -> str:
        """
        Save current session to disk.

        Returns the session_id used for saving.
        """
        import json
        from datetime import datetime

        session_dir = Path.home() / ".juancs" / "sessions"
        session_dir.mkdir(parents=True, exist_ok=True)

        if not session_id:
            session_id = datetime.now().strftime("%Y%m%d_%H%M%S")

        session_file = session_dir / f"{session_id}.json"

        session_data = {
            "session_id": session_id,
            "timestamp": datetime.now().isoformat(),
            "context": self.context,
            "commands": self.commands[-100:],  # Last 100 commands
            "version": "1.0"
        }

        session_file.write_text(json.dumps(session_data, indent=2, ensure_ascii=False))
        return session_id

    def load_session(self, session_id: str = None) -> Dict[str, Any]:
        """
        Load a session from disk.

        If session_id is None, loads the most recent session.
        """
        import json

        session_dir = Path.home() / ".juancs" / "sessions"
        if not session_dir.exists():
            raise ValueError("No sessions found")

        if session_id:
            session_file = session_dir / f"{session_id}.json"
            if not session_file.exists():
                raise ValueError(f"Session not found: {session_id}")
        else:
            # Get most recent session
            sessions = sorted(session_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
            if not sessions:
                raise ValueError("No sessions found")
            session_file = sessions[0]

        data = json.loads(session_file.read_text())
        self.context = data.get("context", [])
        self.commands = data.get("commands", [])

        return {
            "session_id": data.get("session_id"),
            "timestamp": data.get("timestamp"),
            "message_count": len(self.context)
        }

    def list_sessions(self, limit: int = 10) -> List[Dict[str, Any]]:
        """List available sessions."""
        import json

        session_dir = Path.home() / ".juancs" / "sessions"
        if not session_dir.exists():
            return []

        sessions = sorted(session_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
        result = []

        for session_file in sessions[:limit]:
            try:
                data = json.loads(session_file.read_text())
                result.append({
                    "session_id": data.get("session_id", session_file.stem),
                    "timestamp": data.get("timestamp"),
                    "message_count": len(data.get("context", [])),
                    "file": str(session_file)
                })
            except Exception:
                pass

        return result

    # Maximum checkpoints to prevent memory leak (AIR GAP FIX)
    MAX_CHECKPOINTS = 20

    def create_checkpoint(self, label: str = None) -> Dict[str, Any]:
        """
        Create a checkpoint of current conversation state.

        Used for /rewind functionality.

        Note: Limited to MAX_CHECKPOINTS (20) to prevent memory leak.
              Oldest checkpoints are removed when limit is reached.
        """
        from datetime import datetime

        if not hasattr(self, '_checkpoints'):
            self._checkpoints = []

        checkpoint = {
            "index": len(self._checkpoints),
            "label": label or f"Checkpoint {len(self._checkpoints) + 1}",
            "timestamp": datetime.now().isoformat(),
            "context": self.context.copy(),
            "message_count": len(self.context)
        }

        self._checkpoints.append(checkpoint)

        # AIR GAP FIX: Limit checkpoint count to prevent memory leak
        if len(self._checkpoints) > self.MAX_CHECKPOINTS:
            # Remove oldest checkpoints, keeping most recent
            self._checkpoints = self._checkpoints[-self.MAX_CHECKPOINTS:]
            # Re-index remaining checkpoints
            for i, cp in enumerate(self._checkpoints):
                cp["index"] = i

        return checkpoint

    def get_checkpoints(self) -> List[Dict[str, Any]]:
        """Get all checkpoints for current session."""
        if not hasattr(self, '_checkpoints'):
            self._checkpoints = []

        return [
            {
                "index": cp["index"],
                "label": cp["label"],
                "timestamp": cp["timestamp"],
                "message_count": cp["message_count"]
            }
            for cp in self._checkpoints
        ]

    def rewind_to_checkpoint(self, index: int) -> Dict[str, Any]:
        """Rewind conversation to a specific checkpoint."""
        if not hasattr(self, '_checkpoints'):
            raise ValueError("No checkpoints available")

        if not 0 <= index < len(self._checkpoints):
            raise ValueError(f"Invalid checkpoint index: {index}. Available: 0-{len(self._checkpoints)-1}")

        checkpoint = self._checkpoints[index]
        self.context = checkpoint["context"].copy()

        return {
            "success": True,
            "rewound_to": checkpoint["label"],
            "message_count": len(self.context)
        }


# =============================================================================
# BRIDGE - Main Integration Point (Enhanced)
# =============================================================================

class Bridge:
    """
    Main integration bridge between TUI and agent system.

    Enhanced with:
    - 47 tools via ToolBridge
    - Command palette with fuzzy search
    - Autocomplete with fuzzy matching
    - History management with context

    Usage in app.py:
        bridge = Bridge()
        async for chunk in bridge.chat(message):
            view.append_chunk(chunk)
    """

    # Maximum iterations for agentic tool loop
    MAX_TOOL_ITERATIONS = 5

    def __init__(self):
        self.llm = GeminiClient()
        self.governance = GovernanceObserver()
        self.agents = AgentManager(self.llm)
        self.tools = ToolBridge()
        self.palette = CommandPaletteBridge()
        self.autocomplete = AutocompleteBridge(self.tools)
        self.history = HistoryManager()
        self._session_tokens = 0
        self._tools_configured = False

    def _configure_llm_tools(self) -> None:
        """Configure LLM with tool schemas for function calling."""
        if self._tools_configured:
            return

        schemas = self.tools.get_schemas_for_llm()
        if schemas:
            self.llm.set_tools(schemas)
            self._tools_configured = True

    def _get_system_prompt(self) -> str:
        """
        Get system prompt optimized for agentic, symbiotic interaction.

        Uses Claude Code-style agentic prompt for natural language understanding
        and autonomous task execution.
        """
        # Try to use the new agentic prompt system
        try:
            from qwen_cli.core.agentic_prompt import (
                build_agentic_system_prompt,
                load_project_memory,
                get_dynamic_context
            )

            # Get tool schemas
            tool_schemas = self.tools.get_schemas_for_llm()

            # Get dynamic context
            context = get_dynamic_context()

            # Load project memory (JUANCS.md)
            project_memory = load_project_memory()

            # Load user memory
            user_memory = None
            memory_result = self.read_memory(scope="project")
            if memory_result.get("success"):
                user_memory = memory_result.get("content")

            # Build agentic prompt
            return build_agentic_system_prompt(
                tools=tool_schemas,
                context=context,
                project_memory=project_memory,
                user_memory=user_memory
            )

        except Exception as e:
            # Fallback to simple prompt if agentic fails
            pass

        # Fallback: Simple but effective prompt
        tool_names = self.tools.list_tools()[:25]
        tool_list = ", ".join(tool_names) if tool_names else "none loaded"

        return f"""You are juancs-code, an AI coding assistant with direct tool access.

CRITICAL RULES:
1. PREFER ACTIONS OVER EXPLANATIONS - When user asks to create/modify/delete files, USE TOOLS immediately
2. CODE FIRST - Show code, then 1-2 sentence explanation max
3. BE CONCISE - No verbose introductions or unnecessary elaboration
4. EXECUTE, DON'T DESCRIBE - "Create HTML file" = USE write_file tool, NOT print code

Available tools: {tool_list}

IMPORTANT: When user asks to create a file, call write_file(path, content).
When user asks to edit a file, call edit_file(path, ...).
When user asks to run a command, call bash_command(command).

Current working directory: {os.getcwd()}
"""

    @property
    def is_connected(self) -> bool:
        """Check if LLM is available."""
        return self.llm.is_available

    @property
    def status_line(self) -> str:
        """Get status line for TUI."""
        llm_status = f"{ELP['approved']} Gemini" if self.is_connected else f"{ELP['error']} No LLM"
        gov_status = self.governance.get_status_emoji()
        agent_count = len(self.agents.available_agents)
        tool_count = self.tools.get_tool_count()

        return f"{llm_status} | {gov_status} | {ELP['agent']} {agent_count} agents | {ELP['tool']} {tool_count} tools"

    async def chat(self, message: str, auto_route: bool = True) -> AsyncIterator[str]:
        """
        Handle chat message with streaming response and agentic tool execution.

        Enhanced with:
        - Conversation context
        - History tracking
        - Agentic tool loop (detects and executes tool calls)
        - **NEW**: Agent Router - auto-routes to specialized agents (Claude Code parity)

        Args:
            message: User message
            auto_route: If True, automatically route to agents based on intent
        """
        # Configure LLM with tools on first chat
        self._configure_llm_tools()

        # Add to history
        self.history.add_command(message)
        self.history.add_context("user", message)

        # Governance observation (never blocks)
        gov_report = self.governance.observe("chat", message)
        if self.governance.config.alerts and ("CRITICAL" in gov_report or "HIGH" in gov_report):
            yield f"{gov_report}\n\n"

        # =====================================================================
        # AGENT ROUTER - Automatic Intent Detection (Claude Code Parity)
        # =====================================================================
        if auto_route and self.is_auto_routing_enabled():
            routing = self.agents.router.route(message)
            if routing:
                agent_name, confidence = routing
                agent_info = AGENT_REGISTRY.get(agent_name)

                # Show routing decision
                yield f"🎯 **Auto-routing to {agent_name.title()}Agent** (confidence: {int(confidence*100)}%)\n"
                if agent_info:
                    yield f"   *{agent_info.description}*\n\n"

                # Delegate to agent
                async for chunk in self.invoke_agent(agent_name, message):
                    yield chunk
                return

            # Check for ambiguous routing suggestion
            suggestion = self.agents.router.get_routing_suggestion(message)
            if suggestion:
                yield f"{suggestion}\n\n"

        # Get system prompt
        system_prompt = self._get_system_prompt()

        # Agentic loop - process tool calls iteratively
        current_message = message
        full_response_parts = []

        for iteration in range(self.MAX_TOOL_ITERATIONS):
            # Stream from LLM with context
            response_chunks = []
            async for chunk in self.llm.stream(
                current_message,
                system_prompt=system_prompt,
                context=self.history.get_context()
            ):
                response_chunks.append(chunk)
                # Don't yield tool call markers directly - process them
                if not chunk.startswith("[TOOL_CALL:"):
                    yield chunk

            # Accumulate response
            accumulated = "".join(response_chunks)

            # Check for tool calls
            tool_calls = ToolCallParser.extract(accumulated)

            if not tool_calls:
                # No tool calls - we're done
                clean_response = ToolCallParser.remove(accumulated)
                full_response_parts.append(clean_response)
                break

            # Execute tool calls
            tool_results = []
            for tool_name, args in tool_calls:
                # Yield execution indicator
                yield f"\n[dim]● Executing: {tool_name}[/dim]\n"

                # Execute tool
                result = await self.tools.execute_tool(tool_name, **args)

                if result.get("success"):
                    yield f"[green]✓ {tool_name}: Success[/green]\n"
                    tool_results.append(f"Tool {tool_name} succeeded: {result.get('data', 'OK')}")
                else:
                    error = result.get("error", "Unknown error")
                    yield f"[red]✗ {tool_name}: {error}[/red]\n"
                    tool_results.append(f"Tool {tool_name} failed: {error}")

            # Prepare next iteration message with tool results
            clean_text = ToolCallParser.remove(accumulated)
            full_response_parts.append(clean_text)

            # Feed tool results back to LLM for continuation
            current_message = f"Tool execution results:\n" + "\n".join(tool_results) + "\n\nContinue or summarize."

            yield "\n"  # Spacing between iterations

        # Add full response to context
        full_response = "\n".join(full_response_parts)
        self.history.add_context("assistant", full_response)

    async def invoke_agent(
        self,
        agent_name: str,
        task: str,
        context: Optional[Dict[str, Any]] = None
    ) -> AsyncIterator[str]:
        """
        Invoke a specific agent with streaming response.

        Enhanced with history tracking.
        """
        # Add to history
        self.history.add_command(f"/{agent_name} {task}")

        # Governance observation
        gov_report = self.governance.observe(f"agent:{agent_name}", task, agent_name)
        yield f"{gov_report}\n"
        yield f"{ELP['agent']} Routing to {agent_name.title()}Agent...\n\n"

        # Invoke agent
        async for chunk in self.agents.invoke_agent(agent_name, task, context):
            yield chunk

    async def execute_tool(self, tool_name: str, **kwargs) -> Dict[str, Any]:
        """Execute a tool by name."""
        # Governance observation
        gov_report = self.governance.observe(f"tool:{tool_name}", str(kwargs))

        # Execute tool
        result = await self.tools.execute_tool(tool_name, **kwargs)
        result["governance"] = gov_report

        return result

    def get_agent_commands(self) -> Dict[str, str]:
        """Get mapping of slash commands to agents."""
        return {
            "/plan": "planner",
            "/execute": "executor",
            "/architect": "architect",
            "/review": "reviewer",
            "/explore": "explorer",
            "/refactor": "refactorer",
            "/test": "testing",
            "/security": "security",
            "/docs": "documentation",
            "/perf": "performance",
            "/devops": "devops",
            # Governance & Counsel
            "/justica": "justica",
            "/sofia": "sofia",
            # Data
            "/data": "data",
        }

    def get_command_help(self) -> str:
        """Get help text for agent commands."""
        lines = ["## Agent Commands\n"]
        for cmd, agent in self.get_agent_commands().items():
            info = AGENT_REGISTRY.get(agent)
            if info:
                lines.append(f"| `{cmd}` | {info.description} |")
        return "\n".join(lines)

    def get_tool_list(self) -> str:
        """Get formatted list of tools."""
        tools = self.tools.list_tools()
        if not tools:
            return "No tools loaded."

        # Group by category
        categories = {
            "File": ["read_file", "write_file", "edit_file", "list_directory", "delete_file",
                    "move_file", "copy_file", "create_directory", "read_multiple_files", "insert_lines"],
            "Terminal": ["cd", "ls", "pwd", "mkdir", "rm", "cp", "mv", "touch", "cat"],
            "Execution": ["bash_command"],
            "Search": ["search_files", "get_directory_tree"],
            "Git": ["git_status", "git_diff"],
            "Context": ["get_context", "save_session", "restore_backup"],
            "Web": ["web_search", "search_documentation", "fetch_url", "download_file",
                   "http_request", "package_search"],
        }

        lines = [f"## {ELP['tool']} Tools ({len(tools)} available)\n"]

        for category, expected_tools in categories.items():
            available = [t for t in expected_tools if t in tools]
            if available:
                lines.append(f"### {category}")
                lines.append(", ".join(f"`{t}`" for t in available))
                lines.append("")

        # Any uncategorized tools
        all_categorized = set()
        for cat_tools in categories.values():
            all_categorized.update(cat_tools)

        uncategorized = [t for t in tools if t not in all_categorized]
        if uncategorized:
            lines.append("### Other")
            lines.append(", ".join(f"`{t}`" for t in uncategorized))

        return "\n".join(lines)

    # =========================================================================
    # Claude Code Parity Methods
    # =========================================================================

    def compact_context(self, focus: Optional[str] = None) -> Dict[str, Any]:
        """Compact conversation context, optionally focusing on specific topic."""
        before = len(self.history.context)
        # Keep only last N messages, summarize if needed
        if len(self.history.context) > 10:
            # Keep first 2 (system context) and last 8
            self.history.context = self.history.context[:2] + self.history.context[-8:]
        after = len(self.history.context)
        tokens_saved = (before - after) * 500  # Rough estimate
        return {
            "before": before,
            "after": after,
            "tokens_saved": tokens_saved,
            "focus": focus
        }

    def get_token_stats(self) -> Dict[str, Any]:
        """Get token usage statistics."""
        return {
            "session_tokens": self._session_tokens,
            "total_tokens": self._session_tokens,
            "input_tokens": int(self._session_tokens * 0.6),
            "output_tokens": int(self._session_tokens * 0.4),
            "context_tokens": len(str(self.history.context)) // 4,
            "max_tokens": 128000,
            "cost": self._session_tokens * 0.000001  # Rough Gemini pricing
        }

    def get_todos(self) -> List[Dict[str, Any]]:
        """Get current todo list."""
        if not hasattr(self, '_todos'):
            self._todos = []
        return self._todos

    def add_todo(self, text: str) -> None:
        """Add a todo item."""
        if not hasattr(self, '_todos'):
            self._todos = []
        self._todos.append({"text": text, "done": False})

    def set_model(self, model_name: str) -> None:
        """Change the LLM model."""
        self.llm.model = model_name

    def get_current_model(self) -> str:
        """Get current model name."""
        return getattr(self.llm, 'model', 'gemini-2.5-flash')

    def get_available_models(self) -> List[str]:
        """Get list of available models."""
        return [
            "gemini-2.5-flash",
            "gemini-2.5-pro",
            "gemini-2.0-flash",
            "gemini-1.5-pro",
        ]

    def init_project(self) -> Dict[str, Any]:
        """Initialize project with JUANCS.md file."""
        from pathlib import Path
        import datetime

        juancs_content = f"""# JUANCS.md - Project Context

Generated: {datetime.datetime.now().isoformat()}

## Project Overview
This file helps JuanCS Dev-Code understand your project context.

## Key Files
<!-- Add important files here -->

## Architecture
<!-- Describe your architecture -->

## Conventions
<!-- Your coding conventions -->

## Notes
<!-- Additional context for the AI -->
"""
        juancs_path = Path.cwd() / "JUANCS.md"
        if not juancs_path.exists():
            juancs_path.write_text(juancs_content)
            return {"summary": "Created JUANCS.md - edit to add project context"}
        return {"summary": "JUANCS.md already exists"}

    def resume_session(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        """Resume a previous session using HistoryManager."""
        return self.history.load_session(session_id)

    def save_session(self, session_id: Optional[str] = None) -> str:
        """Save current session using HistoryManager."""
        return self.history.save_session(session_id)

    def list_sessions(self, limit: int = 10) -> List[Dict[str, Any]]:
        """List available sessions."""
        return self.history.list_sessions(limit)

    def create_checkpoint(self, label: str = None) -> Dict[str, Any]:
        """Create a checkpoint of current conversation state."""
        return self.history.create_checkpoint(label)

    def get_checkpoints(self) -> List[Dict[str, Any]]:
        """Get available checkpoints for current session."""
        return self.history.get_checkpoints()

    def rewind_to(self, index: int) -> Dict[str, Any]:
        """Rewind conversation to a specific checkpoint."""
        return self.history.rewind_to_checkpoint(index)

    def export_conversation(self, filepath: str = "conversation.md") -> str:
        """Export conversation to file."""
        from pathlib import Path
        lines = ["# Conversation Export\n"]
        for msg in self.history.context:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            lines.append(f"## {role.title()}\n{content}\n")
        Path(filepath).write_text("\n".join(lines))
        return filepath

    def check_health(self) -> Dict[str, Dict[str, Any]]:
        """Check system health."""
        health = {}
        # Check LLM
        health["LLM"] = {
            "ok": self.is_connected,
            "message": "Connected" if self.is_connected else "Not connected"
        }
        # Check tools
        tool_count = self.tools.get_tool_count()
        health["Tools"] = {
            "ok": tool_count > 0,
            "message": f"{tool_count} tools loaded"
        }
        # Check agents
        agent_count = len(self.agents.available_agents)
        health["Agents"] = {
            "ok": agent_count > 0,
            "message": f"{agent_count} agents available"
        }
        return health

    def get_permissions(self) -> Dict[str, bool]:
        """Get current permissions."""
        return {
            "read_files": True,
            "write_files": True,
            "execute_commands": True,
            "network_access": True,
            "sandbox_mode": getattr(self, '_sandbox', False)
        }

    def set_sandbox(self, enabled: bool) -> None:
        """Enable or disable sandbox mode."""
        self._sandbox = enabled

    # =========================================================================
    # HOOKS SYSTEM (Claude Code Parity)
    # =========================================================================

    def _init_hooks(self) -> None:
        """Initialize hooks system with persistence."""
        if not hasattr(self, '_hooks_config'):
            self._hooks_config = {
                "post_write": {
                    "enabled": False,
                    "description": "Run after file write",
                    "commands": []
                },
                "pre_commit": {
                    "enabled": False,
                    "description": "Run before git commit",
                    "commands": []
                },
                "post_edit": {
                    "enabled": False,
                    "description": "Run after file edit",
                    "commands": []
                },
                "post_delete": {
                    "enabled": False,
                    "description": "Run after file delete",
                    "commands": []
                }
            }
            self._hooks_executor = None
            # Load from config file if exists
            self._load_hooks_config()

    def _load_hooks_config(self) -> None:
        """Load hooks configuration from file."""
        config_path = Path.home() / ".juancs" / "hooks.json"
        if config_path.exists():
            try:
                with open(config_path, "r") as f:
                    saved = json.load(f)
                for hook_name, hook_data in saved.items():
                    if hook_name in self._hooks_config:
                        self._hooks_config[hook_name].update(hook_data)
            except Exception:
                pass  # Use defaults on error

    def _save_hooks_config(self) -> None:
        """Save hooks configuration to file."""
        config_dir = Path.home() / ".juancs"
        config_dir.mkdir(exist_ok=True)
        config_path = config_dir / "hooks.json"
        try:
            with open(config_path, "w") as f:
                json.dump(self._hooks_config, f, indent=2)
        except Exception:
            pass  # Silent fail on save error

    def get_hooks(self) -> Dict[str, Dict[str, Any]]:
        """Get configured hooks."""
        self._init_hooks()
        return self._hooks_config

    def set_hook(self, hook_name: str, commands: List[str]) -> bool:
        """
        Set commands for a specific hook.

        Args:
            hook_name: Name of the hook (post_write, pre_commit, etc.)
            commands: List of command templates to execute

        Returns:
            True if successful
        """
        self._init_hooks()
        if hook_name not in self._hooks_config:
            return False

        self._hooks_config[hook_name]["commands"] = commands
        self._hooks_config[hook_name]["enabled"] = len(commands) > 0
        self._save_hooks_config()
        return True

    def enable_hook(self, hook_name: str, enabled: bool = True) -> bool:
        """Enable or disable a hook."""
        self._init_hooks()
        if hook_name not in self._hooks_config:
            return False

        self._hooks_config[hook_name]["enabled"] = enabled
        self._save_hooks_config()
        return True

    def add_hook_command(self, hook_name: str, command: str) -> bool:
        """Add a command to a hook."""
        self._init_hooks()
        if hook_name not in self._hooks_config:
            return False

        if command not in self._hooks_config[hook_name]["commands"]:
            self._hooks_config[hook_name]["commands"].append(command)
            self._hooks_config[hook_name]["enabled"] = True
            self._save_hooks_config()
        return True

    def remove_hook_command(self, hook_name: str, command: str) -> bool:
        """Remove a command from a hook."""
        self._init_hooks()
        if hook_name not in self._hooks_config:
            return False

        if command in self._hooks_config[hook_name]["commands"]:
            self._hooks_config[hook_name]["commands"].remove(command)
            if not self._hooks_config[hook_name]["commands"]:
                self._hooks_config[hook_name]["enabled"] = False
            self._save_hooks_config()
        return True

    async def execute_hook(self, hook_name: str, file_path: str) -> Dict[str, Any]:
        """
        Execute a hook for a specific file.

        Args:
            hook_name: Name of the hook to execute
            file_path: Path to the file that triggered the hook

        Returns:
            Dictionary with execution results
        """
        self._init_hooks()

        if hook_name not in self._hooks_config:
            return {"success": False, "error": f"Unknown hook: {hook_name}"}

        hook = self._hooks_config[hook_name]
        if not hook["enabled"] or not hook["commands"]:
            return {"success": True, "skipped": True, "reason": "Hook disabled or no commands"}

        # Lazy import of hook executor
        if self._hooks_executor is None:
            try:
                from qwen_dev_cli.hooks import HookExecutor, HookContext, HookEvent
                self._hooks_executor = HookExecutor(timeout_seconds=30)
            except ImportError:
                return {"success": False, "error": "Hooks system not available"}

        # Map hook name to event
        from qwen_dev_cli.hooks import HookEvent, HookContext
        event_map = {
            "post_write": HookEvent.POST_WRITE,
            "post_edit": HookEvent.POST_EDIT,
            "post_delete": HookEvent.POST_DELETE,
            "pre_commit": HookEvent.PRE_COMMIT
        }

        event = event_map.get(hook_name)
        if not event:
            return {"success": False, "error": f"Invalid hook event: {hook_name}"}

        # Create context and execute
        context = HookContext(
            file_path=Path(file_path),
            event_name=hook_name,
            cwd=Path.cwd()
        )

        results = await self._hooks_executor.execute_hooks(
            event, context, hook["commands"]
        )

        return {
            "success": all(r.success for r in results),
            "results": [
                {
                    "command": r.command,
                    "success": r.success,
                    "stdout": r.stdout,
                    "stderr": r.stderr,
                    "error": r.error,
                    "execution_time_ms": r.execution_time_ms
                }
                for r in results
            ]
        }

    def get_hook_stats(self) -> Dict[str, Any]:
        """Get hook execution statistics."""
        self._init_hooks()
        if self._hooks_executor is None:
            return {"total_executions": 0, "no_executor": True}

        return self._hooks_executor.get_stats()

    def get_mcp_status(self) -> Dict[str, Any]:
        """Get MCP server status."""
        return {"servers": []}  # No MCP servers configured by default

    # =========================================================================
    # AGENT ROUTER CONTROL (Claude Code Parity - Subagent System)
    # =========================================================================

    # Thread lock for router toggle (AIR GAP FIX)
    import threading
    _router_lock = threading.Lock()

    def toggle_auto_routing(self) -> bool:
        """Toggle automatic agent routing on/off (thread-safe)."""
        with self._router_lock:
            if not hasattr(self, '_auto_route_enabled'):
                self._auto_route_enabled = True

            self._auto_route_enabled = not self._auto_route_enabled
            return self._auto_route_enabled

    def is_auto_routing_enabled(self) -> bool:
        """Check if auto-routing is enabled (thread-safe read)."""
        with self._router_lock:
            return getattr(self, '_auto_route_enabled', True)

    def get_router_status(self) -> Dict[str, Any]:
        """Get router status and statistics."""
        router = self.agents.router
        return {
            "enabled": self.is_auto_routing_enabled(),
            "min_confidence": router.MIN_CONFIDENCE,
            "agents_configured": len(router.INTENT_PATTERNS),
            "pattern_count": sum(len(p) for p in router.INTENT_PATTERNS.values()),
            "available_agents": list(router.INTENT_PATTERNS.keys())
        }

    def test_routing(self, message: str) -> Dict[str, Any]:
        """
        Test routing for a message without executing.

        Returns detailed routing analysis.
        """
        router = self.agents.router

        intents = router.detect_intent(message)
        routing = router.route(message)
        suggestion = router.get_routing_suggestion(message)

        return {
            "message": message,
            "should_route": router.should_route(message),
            "detected_intents": [
                {"agent": a, "confidence": f"{c*100:.0f}%"}
                for a, c in intents
            ],
            "selected_route": {
                "agent": routing[0] if routing else None,
                "confidence": f"{routing[1]*100:.0f}%" if routing else None
            } if routing else None,
            "suggestion": suggestion,
            "would_auto_route": routing is not None and self.is_auto_routing_enabled()
        }

    def manually_route(self, message: str, agent_name: str) -> AsyncIterator[str]:
        """Manually route a message to a specific agent."""
        if agent_name not in AGENT_REGISTRY:
            raise ValueError(f"Unknown agent: {agent_name}. Available: {list(AGENT_REGISTRY.keys())}")

        return self.invoke_agent(agent_name, message)

    # =========================================================================
    # CUSTOM SLASH COMMANDS (Claude Code Parity)
    # =========================================================================

    def _init_custom_commands(self) -> None:
        """Initialize custom commands system."""
        if not hasattr(self, '_custom_commands'):
            self._custom_commands = {}
            self._commands_loaded = False

    def _get_commands_dir(self) -> Path:
        """Get the directory for custom commands."""
        # Check project-local first
        project_dir = Path.cwd() / ".juancs" / "commands"
        if project_dir.exists():
            return project_dir

        # Fall back to global
        global_dir = Path.home() / ".juancs" / "commands"
        return global_dir

    def load_custom_commands(self) -> Dict[str, Dict[str, Any]]:
        """
        Load custom commands from .juancs/commands/ directory.

        Commands are .md files where:
        - Filename (without .md) becomes the command name
        - File contents becomes the prompt template

        Returns:
            Dictionary of command_name -> {prompt, description, path}
        """
        self._init_custom_commands()

        if self._commands_loaded:
            return self._custom_commands

        commands_dir = self._get_commands_dir()

        if not commands_dir.exists():
            self._commands_loaded = True
            return self._custom_commands

        # Load all .md files as commands
        for md_file in commands_dir.glob("*.md"):
            command_name = md_file.stem  # filename without .md

            try:
                content = md_file.read_text(encoding="utf-8")

                # Extract description from first line if it's a comment
                lines = content.strip().split("\n")
                description = ""
                prompt = content

                if lines and lines[0].startswith("#"):
                    # First line is a heading - use as description
                    description = lines[0].lstrip("# ").strip()
                elif lines and lines[0].startswith("<!--"):
                    # HTML comment style description
                    if "-->" in lines[0]:
                        description = lines[0].replace("<!--", "").replace("-->", "").strip()

                self._custom_commands[command_name] = {
                    "name": command_name,
                    "prompt": prompt,
                    "description": description or f"Custom command: {command_name}",
                    "path": str(md_file),
                    "type": "project" if ".juancs" in str(md_file) else "global"
                }

            except Exception:
                continue  # Skip files that can't be read

        self._commands_loaded = True
        return self._custom_commands

    def get_custom_commands(self) -> Dict[str, Dict[str, Any]]:
        """Get all loaded custom commands."""
        return self.load_custom_commands()

    def get_custom_command(self, name: str) -> Optional[Dict[str, Any]]:
        """Get a specific custom command by name."""
        commands = self.load_custom_commands()
        return commands.get(name)

    def execute_custom_command(self, name: str, args: str = "") -> Optional[str]:
        """
        Execute a custom command and return its expanded prompt.

        Args:
            name: Command name (without /)
            args: Arguments to substitute in the prompt

        Returns:
            Expanded prompt string or None if command not found
        """
        command = self.get_custom_command(name)
        if not command:
            return None

        prompt = command["prompt"]

        # Substitute arguments: $ARGUMENTS or {args} or $1, $2, etc.
        if args:
            prompt = prompt.replace("$ARGUMENTS", args)
            prompt = prompt.replace("{args}", args)

            # Support positional args $1, $2, etc.
            arg_parts = args.split()
            for i, arg in enumerate(arg_parts, 1):
                prompt = prompt.replace(f"${i}", arg)

        return prompt

    def _sanitize_command_name(self, name: str) -> str:
        """
        Sanitize command name to prevent path traversal and injection.

        Only allows alphanumeric, hyphens, and underscores.
        """
        import re
        # Remove any path separators and special characters
        sanitized = re.sub(r'[^a-zA-Z0-9_-]', '', name)
        # Ensure not empty
        if not sanitized:
            sanitized = "unnamed_command"
        # Limit length
        return sanitized[:50]

    def create_custom_command(
        self,
        name: str,
        prompt: str,
        description: str = "",
        scope: str = "project"
    ) -> Dict[str, Any]:
        """
        Create a new custom command.

        Args:
            name: Command name (without /)
            prompt: The prompt template
            description: Optional description
            scope: "project" or "global"

        Returns:
            Created command info
        """
        # SECURITY: Sanitize command name to prevent path traversal
        safe_name = self._sanitize_command_name(name)

        if scope == "project":
            commands_dir = Path.cwd() / ".juancs" / "commands"
        else:
            commands_dir = Path.home() / ".juancs" / "commands"

        commands_dir.mkdir(parents=True, exist_ok=True)

        # Create the command file with sanitized name
        command_file = commands_dir / f"{safe_name}.md"

        # SECURITY: Verify the file is within the commands directory
        try:
            command_file.resolve().relative_to(commands_dir.resolve())
        except ValueError:
            raise ValueError(f"Invalid command name: path traversal detected")

        content = prompt
        if description:
            content = f"# {description}\n\n{prompt}"

        command_file.write_text(content, encoding="utf-8")

        # Update cache with sanitized name
        self._init_custom_commands()
        self._custom_commands[safe_name] = {
            "name": safe_name,
            "prompt": prompt,
            "description": description or f"Custom command: {safe_name}",
            "path": str(command_file),
            "type": scope
        }

        return self._custom_commands[safe_name]

    def delete_custom_command(self, name: str) -> bool:
        """Delete a custom command."""
        command = self.get_custom_command(name)
        if not command:
            return False

        try:
            Path(command["path"]).unlink()
            self._init_custom_commands()
            if name in self._custom_commands:
                del self._custom_commands[name]
            return True
        except Exception:
            return False

    def refresh_custom_commands(self) -> Dict[str, Dict[str, Any]]:
        """Force reload of custom commands."""
        self._init_custom_commands()
        self._commands_loaded = False
        return self.load_custom_commands()

    # =========================================================================
    # PLAN MODE (Claude Code Parity)
    # =========================================================================

    # Thread lock for plan mode (AIR GAP FIX - race condition prevention)
    import threading
    _plan_mode_lock = threading.Lock()

    def _init_plan_mode(self) -> None:
        """Initialize plan mode state."""
        if not hasattr(self, '_plan_mode'):
            self._plan_mode = {
                "active": False,
                "plan_file": None,
                "task": None,
                "exploration_log": [],
                "read_only": True,  # No writes in plan mode
                "started_at": None
            }

    def enter_plan_mode(self, task: str = None) -> Dict[str, Any]:
        """
        Enter plan mode for careful task planning.

        In plan mode:
        - Read-only operations are allowed
        - Write operations are blocked
        - A plan file is created for documentation
        - User must approve before exiting

        Args:
            task: Optional task description

        Returns:
            Plan mode state
        """
        # Thread-safe plan mode entry
        with self._plan_mode_lock:
            self._init_plan_mode()

            if self._plan_mode["active"]:
                return {
                    "success": False,
                    "error": "Already in plan mode",
                    "state": self._plan_mode
                }

            import datetime

            # Create plan file
            plan_dir = Path.cwd() / ".juancs" / "plans"
            plan_dir.mkdir(parents=True, exist_ok=True)

            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            plan_file = plan_dir / f"plan_{timestamp}.md"

            plan_content = f"""# Plan Mode - {timestamp}

## Task
{task or 'No task specified'}

## Status
- Started: {datetime.datetime.now().isoformat()}
- Status: IN PROGRESS

## Exploration Notes
<!-- Notes from codebase exploration -->

## Implementation Plan
<!-- Detailed plan steps -->

## Files to Modify
<!-- List files that will be changed -->

## Approval
- [ ] Plan reviewed
- [ ] Ready to implement
"""
            plan_file.write_text(plan_content, encoding="utf-8")

            self._plan_mode = {
                "active": True,
                "plan_file": str(plan_file),
                "task": task,
                "exploration_log": [],
                "read_only": True,
                "started_at": datetime.datetime.now().isoformat()
            }

            return {
                "success": True,
                "message": "Entered plan mode",
                "plan_file": str(plan_file),
                "task": task,
                "restrictions": "Write operations blocked until plan approved"
            }

    def exit_plan_mode(self, approved: bool = False) -> Dict[str, Any]:
        """
        Exit plan mode.

        Args:
            approved: Whether the plan was approved by user

        Returns:
            Exit status
        """
        self._init_plan_mode()

        if not self._plan_mode["active"]:
            return {
                "success": False,
                "error": "Not in plan mode"
            }

        plan_file = self._plan_mode["plan_file"]

        if approved and plan_file:
            # Update plan file with approval
            try:
                import datetime
                plan_path = Path(plan_file)
                if plan_path.exists():
                    content = plan_path.read_text()
                    content = content.replace(
                        "- [ ] Plan reviewed",
                        "- [x] Plan reviewed"
                    ).replace(
                        "- [ ] Ready to implement",
                        "- [x] Ready to implement"
                    ).replace(
                        "Status: IN PROGRESS",
                        f"Status: APPROVED ({datetime.datetime.now().isoformat()})"
                    )
                    plan_path.write_text(content)
            except Exception:
                pass

        result = {
            "success": True,
            "approved": approved,
            "plan_file": plan_file,
            "exploration_count": len(self._plan_mode["exploration_log"]),
            "message": "Plan approved - ready to implement" if approved else "Plan mode exited without approval"
        }

        # Reset state
        self._plan_mode = {
            "active": False,
            "plan_file": None,
            "task": None,
            "exploration_log": [],
            "read_only": True,
            "started_at": None
        }

        return result

    def is_plan_mode(self) -> bool:
        """Check if currently in plan mode."""
        self._init_plan_mode()
        return self._plan_mode["active"]

    def get_plan_mode_state(self) -> Dict[str, Any]:
        """Get current plan mode state."""
        self._init_plan_mode()
        return self._plan_mode.copy()

    def add_plan_note(self, note: str, category: str = "exploration") -> bool:
        """
        Add a note to the current plan.

        Args:
            note: Note content
            category: Category (exploration, plan, files)

        Returns:
            Success status
        """
        self._init_plan_mode()

        if not self._plan_mode["active"]:
            return False

        self._plan_mode["exploration_log"].append({
            "category": category,
            "note": note,
            "timestamp": __import__("datetime").datetime.now().isoformat()
        })

        # Also append to plan file
        plan_file = self._plan_mode["plan_file"]
        if plan_file:
            try:
                plan_path = Path(plan_file)
                if plan_path.exists():
                    content = plan_path.read_text()

                    if category == "exploration":
                        marker = "## Exploration Notes"
                    elif category == "plan":
                        marker = "## Implementation Plan"
                    elif category == "files":
                        marker = "## Files to Modify"
                    else:
                        marker = "## Exploration Notes"

                    # Find marker and append after it
                    if marker in content:
                        parts = content.split(marker)
                        if len(parts) >= 2:
                            parts[1] = f"\n- {note}" + parts[1]
                            content = marker.join(parts)
                            plan_path.write_text(content)
            except Exception:
                pass

        return True

    def check_plan_mode_restriction(self, operation: str) -> Tuple[bool, Optional[str]]:
        """
        Check if an operation is allowed in plan mode.

        Args:
            operation: Operation name (write, edit, delete, execute)

        Returns:
            (allowed, error_message)
        """
        self._init_plan_mode()

        if not self._plan_mode["active"]:
            return True, None  # Not in plan mode, allow all

        # Read-only operations always allowed
        read_only_ops = {"read", "glob", "grep", "ls", "search", "list", "get", "check"}

        if any(op in operation.lower() for op in read_only_ops):
            return True, None

        # Write operations blocked in plan mode
        write_ops = {"write", "edit", "delete", "create", "execute", "run", "bash"}

        if any(op in operation.lower() for op in write_ops):
            return False, f"Operation '{operation}' blocked in plan mode. Exit plan mode with /plan-exit to enable writes."

        return True, None

    # =========================================================================
    # PR CREATION (Claude Code Parity)
    # =========================================================================

    async def create_pull_request(
        self,
        title: str,
        body: str = None,
        base: str = "main",
        draft: bool = False
    ) -> Dict[str, Any]:
        """
        Create a GitHub pull request using gh CLI.

        Args:
            title: PR title
            body: PR body/description
            base: Base branch (default: main)
            draft: Create as draft PR

        Returns:
            PR creation result
        """
        import subprocess
        import shutil

        # Check if gh is available
        if not shutil.which("gh"):
            return {
                "success": False,
                "error": "GitHub CLI (gh) not installed. Install with: brew install gh"
            }

        # Check if authenticated
        try:
            auth_check = subprocess.run(
                ["gh", "auth", "status"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if auth_check.returncode != 0:
                return {
                    "success": False,
                    "error": "Not authenticated with GitHub. Run: gh auth login"
                }
        except Exception as e:
            return {"success": False, "error": f"Auth check failed: {e}"}

        # Get current branch
        try:
            branch_result = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                capture_output=True,
                text=True,
                timeout=5
            )
            current_branch = branch_result.stdout.strip()
        except Exception:
            current_branch = "unknown"

        # Build PR body if not provided
        if not body:
            body = f"""## Summary
{title}

## Changes
- See commit history for details

## Test Plan
- [ ] Tests pass
- [ ] Manual testing done

---
🤖 Generated with [JuanCS Dev-Code](https://github.com/juancs/dev-code)
"""

        # Create PR command
        cmd = ["gh", "pr", "create", "--title", title, "--body", body, "--base", base]

        if draft:
            cmd.append("--draft")

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                pr_url = result.stdout.strip()
                return {
                    "success": True,
                    "url": pr_url,
                    "branch": current_branch,
                    "base": base,
                    "draft": draft,
                    "message": f"PR created: {pr_url}"
                }
            else:
                return {
                    "success": False,
                    "error": result.stderr.strip() or "PR creation failed",
                    "stdout": result.stdout
                }
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "PR creation timed out"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_pr_template(self) -> str:
        """Get PR template if exists."""
        templates = [
            Path.cwd() / ".github" / "pull_request_template.md",
            Path.cwd() / ".github" / "PULL_REQUEST_TEMPLATE.md",
            Path.cwd() / "pull_request_template.md",
        ]

        for template in templates:
            if template.exists():
                try:
                    return template.read_text()
                except Exception:
                    continue

        return ""

    # =========================================================================
    # API KEY MANAGEMENT - /login, /logout (Claude Code Parity)
    # =========================================================================

    def _get_credentials_file(self) -> Path:
        """Get credentials file path."""
        config_dir = Path.home() / ".config" / "juancs"
        config_dir.mkdir(parents=True, exist_ok=True)
        return config_dir / "credentials.json"

    def _get_env_file(self) -> Path:
        """Get .env file path in current project."""
        return Path.cwd() / ".env"

    def login(self, provider: str = "gemini", api_key: str = None, scope: str = "global") -> Dict[str, Any]:
        """
        Login/configure API key for a provider.

        Args:
            provider: Provider name (gemini, openai, anthropic, nebius)
            api_key: API key (if None, will prompt or check env)
            scope: 'global' (saves to ~/.config) or 'project' (saves to .env)

        Returns:
            Login result with status
        """
        import json

        valid_providers = {
            "gemini": "GEMINI_API_KEY",
            "google": "GEMINI_API_KEY",
            "openai": "OPENAI_API_KEY",
            "anthropic": "ANTHROPIC_API_KEY",
            "nebius": "NEBIUS_API_KEY",
            "groq": "GROQ_API_KEY",
        }

        provider_lower = provider.lower()
        if provider_lower not in valid_providers:
            return {
                "success": False,
                "error": f"Unknown provider: {provider}. Valid: {', '.join(valid_providers.keys())}"
            }

        env_var = valid_providers[provider_lower]

        # If no key provided, check environment
        if not api_key:
            existing = os.environ.get(env_var)
            if existing:
                return {
                    "success": True,
                    "message": f"Already logged in to {provider} (key from environment)",
                    "provider": provider,
                    "source": "environment"
                }
            return {
                "success": False,
                "error": f"No API key provided. Use: /login {provider} YOUR_API_KEY"
            }

        # Validate key format (basic check)
        if len(api_key) < 10:
            return {
                "success": False,
                "error": "API key too short. Please provide a valid key."
            }

        # AIR GAP FIX: Sanitize API key - prevent injection attacks
        # Remove newlines, carriage returns, null bytes, and control characters
        import re
        sanitized_key = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', api_key)
        if sanitized_key != api_key:
            # Key contained dangerous characters
            return {
                "success": False,
                "error": "API key contains invalid characters (newlines, control chars not allowed)"
            }

        # Limit key length to prevent DoS
        if len(api_key) > 500:
            return {
                "success": False,
                "error": "API key too long (max 500 characters)"
            }

        try:
            if scope == "global":
                # Save to global credentials
                creds_file = self._get_credentials_file()
                creds = {}
                if creds_file.exists():
                    try:
                        creds = json.loads(creds_file.read_text())
                    except json.JSONDecodeError:
                        creds = {}

                creds[env_var] = api_key
                creds_file.write_text(json.dumps(creds, indent=2))
                creds_file.chmod(0o600)  # Secure permissions

                # Also set in environment for current session
                os.environ[env_var] = api_key

                return {
                    "success": True,
                    "message": f"Logged in to {provider} (global)",
                    "provider": provider,
                    "scope": "global",
                    "file": str(creds_file)
                }

            elif scope == "project":
                # Save to project .env
                env_file = self._get_env_file()
                lines = []
                key_found = False

                if env_file.exists():
                    for line in env_file.read_text().splitlines():
                        if line.startswith(f"{env_var}="):
                            lines.append(f"{env_var}={api_key}")
                            key_found = True
                        else:
                            lines.append(line)

                if not key_found:
                    lines.append(f"{env_var}={api_key}")

                env_file.write_text("\n".join(lines) + "\n")

                # Set in environment for current session
                os.environ[env_var] = api_key

                return {
                    "success": True,
                    "message": f"Logged in to {provider} (project)",
                    "provider": provider,
                    "scope": "project",
                    "file": str(env_file)
                }

            else:
                return {
                    "success": False,
                    "error": f"Invalid scope: {scope}. Use 'global' or 'project'"
                }

        except Exception as e:
            return {"success": False, "error": f"Login failed: {e}"}

    def logout(self, provider: str = None, scope: str = "all") -> Dict[str, Any]:
        """
        Logout/remove API key for a provider.

        Args:
            provider: Provider name (or None for all)
            scope: 'global', 'project', or 'all'

        Returns:
            Logout result
        """
        import json

        valid_providers = {
            "gemini": "GEMINI_API_KEY",
            "google": "GEMINI_API_KEY",
            "openai": "OPENAI_API_KEY",
            "anthropic": "ANTHROPIC_API_KEY",
            "nebius": "NEBIUS_API_KEY",
            "groq": "GROQ_API_KEY",
        }

        removed = []

        try:
            # Determine which keys to remove
            if provider:
                provider_lower = provider.lower()
                if provider_lower not in valid_providers:
                    return {
                        "success": False,
                        "error": f"Unknown provider: {provider}"
                    }
                keys_to_remove = [valid_providers[provider_lower]]
            else:
                keys_to_remove = list(valid_providers.values())

            # Remove from global credentials
            if scope in ("global", "all"):
                creds_file = self._get_credentials_file()
                if creds_file.exists():
                    try:
                        creds = json.loads(creds_file.read_text())
                        for key in keys_to_remove:
                            if key in creds:
                                del creds[key]
                                removed.append(f"{key} (global)")
                        creds_file.write_text(json.dumps(creds, indent=2))
                    except Exception:
                        pass

            # Remove from project .env
            if scope in ("project", "all"):
                env_file = self._get_env_file()
                if env_file.exists():
                    try:
                        lines = []
                        original = env_file.read_text().splitlines()
                        for line in original:
                            should_keep = True
                            for key in keys_to_remove:
                                if line.startswith(f"{key}="):
                                    removed.append(f"{key} (project)")
                                    should_keep = False
                                    break
                            if should_keep:
                                lines.append(line)
                        if len(lines) != len(original):
                            env_file.write_text("\n".join(lines) + "\n" if lines else "")
                    except Exception:
                        pass

            # Remove from current environment
            for key in keys_to_remove:
                if key in os.environ:
                    del os.environ[key]
                    if f"{key} (env)" not in removed:
                        removed.append(f"{key} (session)")

            if removed:
                return {
                    "success": True,
                    "message": f"Logged out: {', '.join(removed)}",
                    "removed": removed
                }
            else:
                return {
                    "success": True,
                    "message": "No credentials found to remove",
                    "removed": []
                }

        except Exception as e:
            return {"success": False, "error": f"Logout failed: {e}"}

    def get_auth_status(self) -> Dict[str, Any]:
        """Get authentication status for all providers."""
        import json

        providers = {
            "gemini": "GEMINI_API_KEY",
            "openai": "OPENAI_API_KEY",
            "anthropic": "ANTHROPIC_API_KEY",
            "nebius": "NEBIUS_API_KEY",
            "groq": "GROQ_API_KEY",
        }

        status = {}

        # Check global credentials
        creds_file = self._get_credentials_file()
        global_creds = {}
        if creds_file.exists():
            try:
                global_creds = json.loads(creds_file.read_text())
            except Exception:
                pass

        # Check project .env
        env_file = self._get_env_file()
        project_creds = {}
        if env_file.exists():
            try:
                for line in env_file.read_text().splitlines():
                    if "=" in line and not line.startswith("#"):
                        key, value = line.split("=", 1)
                        project_creds[key.strip()] = value.strip()
            except Exception:
                pass

        for provider, env_var in providers.items():
            sources = []
            if env_var in os.environ:
                sources.append("environment")
            if env_var in global_creds:
                sources.append("global")
            if env_var in project_creds:
                sources.append("project")

            status[provider] = {
                "logged_in": len(sources) > 0,
                "sources": sources,
                "env_var": env_var
            }

        return {
            "providers": status,
            "global_file": str(creds_file),
            "project_file": str(env_file)
        }

    # =========================================================================
    # MEMORY PERSISTENCE - MEMORY.md (Claude Code Parity with CLAUDE.md)
    # =========================================================================

    def _get_memory_file(self, scope: str = "project") -> Path:
        """Get memory file path."""
        if scope == "global":
            config_dir = Path.home() / ".config" / "juancs"
            config_dir.mkdir(parents=True, exist_ok=True)
            return config_dir / "MEMORY.md"
        else:
            return Path.cwd() / "MEMORY.md"

    def read_memory(self, scope: str = "project") -> Dict[str, Any]:
        """
        Read memory/context from MEMORY.md file.

        This is similar to Claude Code's CLAUDE.md - persistent instructions
        and context that persists across sessions.

        Args:
            scope: 'project' (./MEMORY.md) or 'global' (~/.config/juancs/MEMORY.md)

        Returns:
            Memory content and metadata
        """
        memory_file = self._get_memory_file(scope)

        if not memory_file.exists():
            return {
                "success": True,
                "content": "",
                "exists": False,
                "file": str(memory_file),
                "scope": scope
            }

        try:
            content = memory_file.read_text()
            return {
                "success": True,
                "content": content,
                "exists": True,
                "file": str(memory_file),
                "scope": scope,
                "size": len(content),
                "lines": content.count("\n") + 1
            }
        except Exception as e:
            return {"success": False, "error": f"Failed to read memory: {e}"}

    def write_memory(self, content: str, scope: str = "project", append: bool = False) -> Dict[str, Any]:
        """
        Write to memory/context file.

        Args:
            content: Content to write
            scope: 'project' or 'global'
            append: If True, append to existing content

        Returns:
            Write result
        """
        memory_file = self._get_memory_file(scope)

        try:
            if append and memory_file.exists():
                existing = memory_file.read_text()
                content = existing + "\n" + content

            # Ensure parent directory exists
            memory_file.parent.mkdir(parents=True, exist_ok=True)

            memory_file.write_text(content)

            return {
                "success": True,
                "message": f"Memory {'updated' if append else 'written'} to {memory_file}",
                "file": str(memory_file),
                "scope": scope,
                "size": len(content)
            }
        except Exception as e:
            return {"success": False, "error": f"Failed to write memory: {e}"}

    def add_memory_note(self, note: str, category: str = "general", scope: str = "project") -> Dict[str, Any]:
        """
        Add a note to memory file.

        Args:
            note: Note content
            category: Category (general, preferences, patterns, todos)
            scope: 'project' or 'global'

        Returns:
            Result
        """
        import datetime
        import re

        # AIR GAP FIX: Sanitize note content to prevent header injection
        # Remove markdown headers (# ## ###) from user input
        sanitized_note = re.sub(r'^#{1,6}\s+', '', note, flags=re.MULTILINE)
        # Replace newlines with spaces to prevent multi-line injection
        sanitized_note = sanitized_note.replace('\n', ' ').replace('\r', '')
        note = sanitized_note.strip()

        memory_file = self._get_memory_file(scope)

        # Category headers
        category_headers = {
            "general": "## General Notes",
            "preferences": "## Preferences",
            "patterns": "## Code Patterns",
            "todos": "## TODOs",
            "context": "## Context",
        }

        header = category_headers.get(category, "## Notes")
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

        try:
            if memory_file.exists():
                content = memory_file.read_text()
            else:
                content = f"""# Project Memory

This file stores persistent context and notes for the AI assistant.
Similar to Claude Code's CLAUDE.md functionality.

"""

            # Find or create category section
            if header in content:
                # Append under existing header
                lines = content.split("\n")
                new_lines = []
                found = False
                for i, line in enumerate(lines):
                    new_lines.append(line)
                    if line.strip() == header and not found:
                        found = True
                        new_lines.append(f"- [{timestamp}] {note}")
                content = "\n".join(new_lines)
            else:
                # Add new section
                content += f"\n{header}\n- [{timestamp}] {note}\n"

            memory_file.write_text(content)

            return {
                "success": True,
                "message": f"Note added to {category}",
                "file": str(memory_file),
                "category": category
            }
        except Exception as e:
            return {"success": False, "error": f"Failed to add note: {e}"}

    def get_memory_context(self) -> str:
        """
        Get combined memory context for AI prompt injection.

        Returns both project and global memory for context.
        """
        context_parts = []

        # Global memory
        global_mem = self.read_memory(scope="global")
        if global_mem.get("exists") and global_mem.get("content"):
            context_parts.append("=== Global Memory ===\n" + global_mem["content"])

        # Project memory
        project_mem = self.read_memory(scope="project")
        if project_mem.get("exists") and project_mem.get("content"):
            context_parts.append("=== Project Memory ===\n" + project_mem["content"])

        return "\n\n".join(context_parts) if context_parts else ""

    # =========================================================================
    # IMAGE READING (Claude Code Parity)
    # =========================================================================

    def read_image(self, path: str, resize: bool = True, max_size: int = 1024) -> Dict[str, Any]:
        """
        Read an image file and return base64 encoded data for AI vision.

        Args:
            path: Path to image file
            resize: Whether to resize large images
            max_size: Maximum dimension (width or height) when resizing

        Returns:
            Image data and metadata
        """
        import base64
        import mimetypes

        image_path = Path(path)

        # AIR GAP FIX: Wrap exists() in try/catch to handle permission errors
        try:
            if not image_path.exists():
                return {"success": False, "error": f"Image not found: {path}"}
        except PermissionError:
            return {"success": False, "error": f"Permission denied: {path}"}
        except OSError as e:
            return {"success": False, "error": f"Cannot access path: {path} ({e})"}

        # Check if it's an image
        mime_type, _ = mimetypes.guess_type(str(image_path))
        if not mime_type or not mime_type.startswith("image/"):
            return {"success": False, "error": f"Not an image file: {path}"}

        supported_types = ["image/png", "image/jpeg", "image/gif", "image/webp"]
        if mime_type not in supported_types:
            return {
                "success": False,
                "error": f"Unsupported image type: {mime_type}. Supported: {supported_types}"
            }

        try:
            # Try to use PIL for better handling
            try:
                from PIL import Image
                has_pil = True
            except ImportError:
                has_pil = False

            if has_pil and resize:
                # Open and optionally resize with PIL
                img = Image.open(image_path)
                original_size = img.size

                # Resize if too large
                if max(img.size) > max_size:
                    ratio = max_size / max(img.size)
                    new_size = (int(img.size[0] * ratio), int(img.size[1] * ratio))
                    img = img.resize(new_size, Image.Resampling.LANCZOS)

                # Convert to bytes
                import io
                buffer = io.BytesIO()
                format_map = {
                    "image/png": "PNG",
                    "image/jpeg": "JPEG",
                    "image/gif": "GIF",
                    "image/webp": "WEBP"
                }
                img.save(buffer, format=format_map.get(mime_type, "PNG"))
                image_data = buffer.getvalue()

                return {
                    "success": True,
                    "data": base64.b64encode(image_data).decode("utf-8"),
                    "mime_type": mime_type,
                    "original_size": original_size,
                    "final_size": img.size,
                    "resized": img.size != original_size,
                    "file": str(image_path)
                }
            else:
                # Read raw file
                image_data = image_path.read_bytes()

                # Check file size (limit to 10MB)
                if len(image_data) > 10 * 1024 * 1024:
                    return {
                        "success": False,
                        "error": "Image too large (>10MB). Install PIL for automatic resizing: pip install Pillow"
                    }

                return {
                    "success": True,
                    "data": base64.b64encode(image_data).decode("utf-8"),
                    "mime_type": mime_type,
                    "file_size": len(image_data),
                    "file": str(image_path),
                    "resized": False
                }

        except Exception as e:
            return {"success": False, "error": f"Failed to read image: {e}"}

    def read_pdf(self, path: str, max_pages: int = 50) -> Dict[str, Any]:
        """
        Read a PDF file and extract text content.

        Args:
            path: Path to PDF file
            max_pages: Maximum pages to extract

        Returns:
            PDF text content and metadata
        """
        pdf_path = Path(path)

        # AIR GAP FIX: Wrap exists() in try/catch to handle permission errors
        try:
            if not pdf_path.exists():
                return {"success": False, "error": f"PDF not found: {path}"}
        except PermissionError:
            return {"success": False, "error": f"Permission denied: {path}"}
        except OSError as e:
            return {"success": False, "error": f"Cannot access path: {path} ({e})"}

        if not pdf_path.suffix.lower() == ".pdf":
            return {"success": False, "error": f"Not a PDF file: {path}"}

        try:
            # Try PyMuPDF first (best quality)
            try:
                import fitz  # PyMuPDF
                doc = fitz.open(pdf_path)
                pages = []
                for i, page in enumerate(doc):
                    if i >= max_pages:
                        break
                    text = page.get_text()
                    pages.append({
                        "page": i + 1,
                        "text": text
                    })
                doc.close()

                return {
                    "success": True,
                    "pages": pages,
                    "total_pages": len(pages),
                    "truncated": len(doc) > max_pages,
                    "file": str(pdf_path),
                    "extractor": "PyMuPDF"
                }
            except ImportError:
                pass

            # Try pypdf as fallback
            try:
                from pypdf import PdfReader
                reader = PdfReader(pdf_path)
                pages = []
                for i, page in enumerate(reader.pages):
                    if i >= max_pages:
                        break
                    text = page.extract_text() or ""
                    pages.append({
                        "page": i + 1,
                        "text": text
                    })

                return {
                    "success": True,
                    "pages": pages,
                    "total_pages": len(pages),
                    "truncated": len(reader.pages) > max_pages,
                    "file": str(pdf_path),
                    "extractor": "pypdf"
                }
            except ImportError:
                pass

            return {
                "success": False,
                "error": "No PDF library available. Install: pip install PyMuPDF or pip install pypdf"
            }

        except Exception as e:
            return {"success": False, "error": f"Failed to read PDF: {e}"}

    # =========================================================================
    # WAVE 6: AUDIT LOGGING (Beyond Claude Code Parity)
    # =========================================================================

    def _get_audit_log_file(self) -> Path:
        """Get audit log file path."""
        log_dir = Path.cwd() / ".juancs" / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        return log_dir / "audit.jsonl"

    def _init_audit_log(self) -> None:
        """Initialize audit logging system."""
        if not hasattr(self, '_audit_enabled'):
            self._audit_enabled = True
            self._audit_session_id = None

    def audit_log(
        self,
        action: str,
        tool: str = None,
        params: Dict[str, Any] = None,
        result: str = "success",
        details: str = None
    ) -> None:
        """
        Log an action to the audit log.

        Args:
            action: Action type (tool_call, command, file_write, etc.)
            tool: Tool name if applicable
            params: Parameters used (sanitized - no secrets)
            result: Result status (success, failure, blocked)
            details: Additional details
        """
        import datetime
        import json

        self._init_audit_log()

        if not self._audit_enabled:
            return

        # Sanitize params - remove potential secrets
        safe_params = {}
        if params:
            secret_keys = {'api_key', 'key', 'password', 'token', 'secret', 'credential'}
            for k, v in params.items():
                if any(s in k.lower() for s in secret_keys):
                    safe_params[k] = "***REDACTED***"
                elif isinstance(v, str) and len(v) > 500:
                    safe_params[k] = v[:100] + "...[truncated]"
                else:
                    safe_params[k] = v

        entry = {
            "timestamp": datetime.datetime.now().isoformat(),
            "session_id": self._audit_session_id,
            "action": action,
            "tool": tool,
            "params": safe_params,
            "result": result,
            "details": details,
            "cwd": str(Path.cwd()),
        }

        try:
            log_file = self._get_audit_log_file()
            with open(log_file, 'a') as f:
                f.write(json.dumps(entry) + "\n")
        except Exception:
            pass  # Don't fail on logging errors

    def get_audit_log(self, limit: int = 100, action_filter: str = None) -> Dict[str, Any]:
        """
        Read audit log entries.

        Args:
            limit: Maximum entries to return
            action_filter: Filter by action type

        Returns:
            Audit log entries
        """
        import json

        log_file = self._get_audit_log_file()

        if not log_file.exists():
            return {"success": True, "entries": [], "total": 0}

        try:
            entries = []
            with open(log_file, 'r') as f:
                for line in f:
                    try:
                        entry = json.loads(line.strip())
                        if action_filter and entry.get("action") != action_filter:
                            continue
                        entries.append(entry)
                    except json.JSONDecodeError:
                        continue

            # Return most recent first
            entries.reverse()
            return {
                "success": True,
                "entries": entries[:limit],
                "total": len(entries),
                "file": str(log_file)
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def set_audit_enabled(self, enabled: bool) -> Dict[str, Any]:
        """Enable or disable audit logging."""
        self._init_audit_log()
        self._audit_enabled = enabled
        return {
            "success": True,
            "enabled": enabled,
            "message": f"Audit logging {'enabled' if enabled else 'disabled'}"
        }

    # =========================================================================
    # WAVE 6: DIFF PREVIEW (Beyond Claude Code Parity)
    # =========================================================================

    def preview_diff(self, file_path: str, old_string: str, new_string: str) -> Dict[str, Any]:
        """
        Preview a diff before applying an edit.

        Args:
            file_path: Path to file
            old_string: String to replace
            new_string: Replacement string

        Returns:
            Unified diff preview
        """
        import difflib

        path = Path(file_path)

        if not path.exists():
            return {"success": False, "error": f"File not found: {file_path}"}

        try:
            content = path.read_text()

            if old_string not in content:
                return {
                    "success": False,
                    "error": "String not found in file",
                    "file": file_path
                }

            # Count occurrences
            count = content.count(old_string)

            # Generate new content
            new_content = content.replace(old_string, new_string, 1)

            # Generate unified diff
            diff = list(difflib.unified_diff(
                content.splitlines(keepends=True),
                new_content.splitlines(keepends=True),
                fromfile=f"a/{path.name}",
                tofile=f"b/{path.name}",
                lineterm=""
            ))

            return {
                "success": True,
                "diff": "".join(diff),
                "occurrences": count,
                "file": file_path,
                "old_length": len(old_string),
                "new_length": len(new_string),
                "lines_changed": len([l for l in diff if l.startswith('+') or l.startswith('-')]) - 2
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    # =========================================================================
    # WAVE 6: AUTO-BACKUP (Beyond Claude Code Parity)
    # =========================================================================

    def _get_backup_dir(self) -> Path:
        """Get backup directory path."""
        backup_dir = Path.cwd() / ".juancs" / "backups"
        backup_dir.mkdir(parents=True, exist_ok=True)
        return backup_dir

    def create_backup(self, file_path: str, reason: str = "manual") -> Dict[str, Any]:
        """
        Create a backup of a file.

        Args:
            file_path: Path to file to backup
            reason: Reason for backup (manual, pre-edit, pre-delete)

        Returns:
            Backup result with backup path
        """
        import datetime
        import shutil

        path = Path(file_path)

        # AIR GAP FIX: Block backup of system files
        # Prevent data exfiltration from sensitive system directories
        forbidden_prefixes = ['/etc/', '/root/', '/proc/', '/sys/', '/dev/', '/boot/', '/var/log/']
        try:
            resolved_path = str(path.resolve())
        except (PermissionError, OSError):
            return {"success": False, "error": "Cannot access file path"}

        if any(resolved_path.startswith(prefix) for prefix in forbidden_prefixes):
            return {"success": False, "error": "Cannot backup system files for security reasons"}

        if not path.exists():
            return {"success": False, "error": f"File not found: {file_path}"}

        try:
            backup_dir = self._get_backup_dir()
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

            # Create backup filename
            safe_name = path.name.replace("/", "_").replace("\\", "_")
            backup_name = f"{timestamp}_{reason}_{safe_name}"
            backup_path = backup_dir / backup_name

            # Copy file
            shutil.copy2(path, backup_path)

            # Log to audit
            self.audit_log(
                action="backup_created",
                params={"file": file_path, "reason": reason},
                details=str(backup_path)
            )

            return {
                "success": True,
                "original": str(path),
                "backup": str(backup_path),
                "reason": reason,
                "size": backup_path.stat().st_size
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def list_backups(self, file_filter: str = None, limit: int = 50) -> Dict[str, Any]:
        """
        List available backups.

        Args:
            file_filter: Filter by original filename
            limit: Maximum backups to return

        Returns:
            List of backups
        """
        backup_dir = self._get_backup_dir()

        if not backup_dir.exists():
            return {"success": True, "backups": [], "total": 0}

        try:
            backups = []
            for backup_file in sorted(backup_dir.iterdir(), reverse=True):
                if not backup_file.is_file():
                    continue

                # Parse backup filename: timestamp_reason_filename
                parts = backup_file.name.split("_", 2)
                if len(parts) >= 3:
                    timestamp, reason, original = parts[0], parts[1], parts[2]
                else:
                    timestamp, reason, original = "", "unknown", backup_file.name

                if file_filter and file_filter not in original:
                    continue

                backups.append({
                    "backup_file": str(backup_file),
                    "original_name": original,
                    "reason": reason,
                    "timestamp": timestamp,
                    "size": backup_file.stat().st_size
                })

                if len(backups) >= limit:
                    break

            return {
                "success": True,
                "backups": backups,
                "total": len(backups),
                "backup_dir": str(backup_dir)
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def restore_backup(self, backup_path: str, target_path: str = None) -> Dict[str, Any]:
        """
        Restore a file from backup.

        Args:
            backup_path: Path to backup file
            target_path: Target path (defaults to original location)

        Returns:
            Restore result
        """
        import shutil

        backup = Path(backup_path)

        if not backup.exists():
            return {"success": False, "error": f"Backup not found: {backup_path}"}

        try:
            # Parse original name from backup filename
            parts = backup.name.split("_", 2)
            original_name = parts[2] if len(parts) >= 3 else backup.name

            target = Path(target_path) if target_path else Path.cwd() / original_name

            # Create backup of current file before restore
            if target.exists():
                self.create_backup(str(target), reason="pre-restore")

            # Restore
            shutil.copy2(backup, target)

            self.audit_log(
                action="backup_restored",
                params={"backup": backup_path, "target": str(target)}
            )

            return {
                "success": True,
                "restored_from": str(backup),
                "restored_to": str(target),
                "size": target.stat().st_size
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    # =========================================================================
    # WAVE 6: UNDO STACK (Beyond Claude Code Parity)
    # =========================================================================

    def _init_undo_stack(self) -> None:
        """Initialize undo stack."""
        if not hasattr(self, '_undo_stack'):
            self._undo_stack = []
            self._redo_stack = []
            self._max_undo = 50

    def push_undo(self, operation: str, file_path: str, old_content: str, new_content: str) -> None:
        """
        Push an operation to the undo stack.

        Args:
            operation: Operation type (edit, write, delete)
            file_path: File path
            old_content: Content before change
            new_content: Content after change
        """
        import datetime

        self._init_undo_stack()

        entry = {
            "timestamp": datetime.datetime.now().isoformat(),
            "operation": operation,
            "file_path": file_path,
            "old_content": old_content,
            "new_content": new_content,
        }

        self._undo_stack.append(entry)
        self._redo_stack.clear()  # Clear redo on new operation

        # Limit stack size
        if len(self._undo_stack) > self._max_undo:
            self._undo_stack.pop(0)

    def undo(self) -> Dict[str, Any]:
        """
        Undo the last operation.

        Returns:
            Undo result
        """
        self._init_undo_stack()

        if not self._undo_stack:
            return {"success": False, "error": "Nothing to undo"}

        entry = self._undo_stack.pop()

        try:
            path = Path(entry["file_path"])

            # Restore old content
            if entry["old_content"] is None:
                # File was created - delete it
                if path.exists():
                    path.unlink()
            else:
                path.write_text(entry["old_content"])

            # Push to redo stack
            self._redo_stack.append(entry)

            self.audit_log(
                action="undo",
                params={"file": entry["file_path"], "operation": entry["operation"]}
            )

            return {
                "success": True,
                "undone": entry["operation"],
                "file": entry["file_path"],
                "remaining_undos": len(self._undo_stack)
            }

        except Exception as e:
            # Put it back on the stack
            self._undo_stack.append(entry)
            return {"success": False, "error": str(e)}

    def redo(self) -> Dict[str, Any]:
        """
        Redo the last undone operation.

        Returns:
            Redo result
        """
        self._init_undo_stack()

        if not self._redo_stack:
            return {"success": False, "error": "Nothing to redo"}

        entry = self._redo_stack.pop()

        try:
            path = Path(entry["file_path"])

            # Apply new content
            if entry["new_content"] is None:
                # File was deleted
                if path.exists():
                    path.unlink()
            else:
                path.write_text(entry["new_content"])

            # Push back to undo stack
            self._undo_stack.append(entry)

            self.audit_log(
                action="redo",
                params={"file": entry["file_path"], "operation": entry["operation"]}
            )

            return {
                "success": True,
                "redone": entry["operation"],
                "file": entry["file_path"],
                "remaining_redos": len(self._redo_stack)
            }

        except Exception as e:
            self._redo_stack.append(entry)
            return {"success": False, "error": str(e)}

    def get_undo_stack(self) -> Dict[str, Any]:
        """Get current undo/redo stack status."""
        self._init_undo_stack()

        return {
            "success": True,
            "undo_count": len(self._undo_stack),
            "redo_count": len(self._redo_stack),
            "undo_operations": [
                {"operation": e["operation"], "file": e["file_path"], "timestamp": e["timestamp"]}
                for e in reversed(self._undo_stack[-10:])
            ],
            "redo_operations": [
                {"operation": e["operation"], "file": e["file_path"], "timestamp": e["timestamp"]}
                for e in reversed(self._redo_stack[-10:])
            ]
        }

    # =========================================================================
    # WAVE 6: SECRETS SCANNER (Beyond Claude Code Parity)
    # =========================================================================

    def scan_secrets(self, path: str = ".", patterns: List[str] = None) -> Dict[str, Any]:
        """
        Scan files for potential secrets/credentials.

        Args:
            path: Directory or file to scan
            patterns: Additional regex patterns to search

        Returns:
            Scan results with findings
        """
        import re

        # Default secret patterns
        default_patterns = {
            "AWS Access Key": r'AKIA[0-9A-Z]{16}',
            "AWS Secret Key": r'(?i)aws.{0,20}secret.{0,20}[\'"][0-9a-zA-Z/+]{40}[\'"]',
            "GitHub Token": r'ghp_[0-9a-zA-Z]{36}',
            "GitHub OAuth": r'gho_[0-9a-zA-Z]{36}',
            "Generic API Key": r'(?i)(api[_-]?key|apikey).{0,20}[\'"][0-9a-zA-Z]{20,}[\'"]',
            "Generic Secret": r'(?i)(secret|password|passwd|pwd).{0,20}[\'"][^\'"]{8,}[\'"]',
            "Private Key": r'-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----',
            "JWT Token": r'eyJ[A-Za-z0-9-_=]+\.eyJ[A-Za-z0-9-_=]+\.[A-Za-z0-9-_.+/=]*',
            "Slack Token": r'xox[baprs]-[0-9]{10,13}-[0-9]{10,13}-[a-zA-Z0-9]{24}',
            "Google API Key": r'AIza[0-9A-Za-z-_]{35}',
            "Stripe Key": r'(?:sk|pk)_(?:test|live)_[0-9a-zA-Z]{24,}',
            "Database URL": r'(?i)(mysql|postgres|mongodb|redis):\/\/[^\s\'\"]+',
        }

        # Add custom patterns
        if patterns:
            for i, p in enumerate(patterns):
                default_patterns[f"Custom_{i}"] = p

        # AIR GAP FIX: Handle empty/whitespace path
        if not path or not path.strip():
            return {"success": False, "error": "Path cannot be empty"}

        scan_path = Path(path.strip())

        if not scan_path.exists():
            return {"success": False, "error": f"Path not found: {path}"}

        findings = []
        files_scanned = 0
        errors = []

        # Files to skip
        skip_patterns = {'.git', 'node_modules', '__pycache__', '.venv', 'venv', '.env.example'}
        skip_extensions = {'.pyc', '.pyo', '.so', '.dll', '.exe', '.bin', '.png', '.jpg', '.gif'}

        def scan_file(file_path: Path):
            nonlocal files_scanned

            if file_path.suffix in skip_extensions:
                return

            try:
                content = file_path.read_text(errors='ignore')
                files_scanned += 1

                for secret_type, pattern in default_patterns.items():
                    matches = re.finditer(pattern, content)
                    for match in matches:
                        # Get line number
                        line_num = content[:match.start()].count('\n') + 1
                        # Get context (redacted)
                        start = max(0, match.start() - 20)
                        end = min(len(content), match.end() + 20)
                        context = content[start:end]
                        # Redact the actual secret
                        redacted = context[:20] + "***REDACTED***" + context[-20:]

                        findings.append({
                            "file": str(file_path),
                            "line": line_num,
                            "type": secret_type,
                            "context": redacted,
                        })
            except Exception as e:
                errors.append({"file": str(file_path), "error": str(e)})

        try:
            if scan_path.is_file():
                scan_file(scan_path)
            else:
                for item in scan_path.rglob("*"):
                    if any(skip in str(item) for skip in skip_patterns):
                        continue
                    if item.is_file():
                        scan_file(item)

            self.audit_log(
                action="secrets_scan",
                params={"path": path, "files_scanned": files_scanned},
                result="success" if not findings else "findings",
                details=f"{len(findings)} potential secrets found"
            )

            return {
                "success": True,
                "findings": findings,
                "findings_count": len(findings),
                "files_scanned": files_scanned,
                "errors": errors[:10] if errors else [],
                "severity": "HIGH" if findings else "CLEAN"
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def scan_staged_secrets(self) -> Dict[str, Any]:
        """
        Scan git staged files for secrets (pre-commit hook helper).

        Returns:
            Scan results for staged files only
        """
        import subprocess

        try:
            # Get staged files
            result = subprocess.run(
                ["git", "diff", "--cached", "--name-only"],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode != 0:
                return {"success": False, "error": "Not a git repository or git error"}

            staged_files = [f.strip() for f in result.stdout.strip().split("\n") if f.strip()]

            if not staged_files:
                return {
                    "success": True,
                    "findings": [],
                    "files_scanned": 0,
                    "message": "No staged files to scan"
                }

            # Scan each staged file
            all_findings = []
            for file_path in staged_files:
                if Path(file_path).exists():
                    scan_result = self.scan_secrets(file_path)
                    if scan_result.get("findings"):
                        all_findings.extend(scan_result["findings"])

            return {
                "success": True,
                "findings": all_findings,
                "findings_count": len(all_findings),
                "files_scanned": len(staged_files),
                "staged_files": staged_files,
                "can_commit": len(all_findings) == 0,
                "severity": "HIGH" if all_findings else "CLEAN"
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    # =========================================================================
    # WAVE 7: GITHUB PR/ISSUE INTEGRATION (Beyond Claude Code Parity)
    # =========================================================================

    def _check_gh_cli(self) -> bool:
        """Check if GitHub CLI is installed and authenticated."""
        try:
            result = subprocess.run(
                ["gh", "auth", "status"],
                capture_output=True,
                text=True,
                timeout=10
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    def create_pull_request(
        self,
        title: str,
        body: str = "",
        base: str = None,
        head: str = None,
        draft: bool = False
    ) -> Dict[str, Any]:
        """
        Create a GitHub Pull Request.

        Args:
            title: PR title
            body: PR description (markdown supported)
            base: Base branch (default: main/master)
            head: Head branch (default: current branch)
            draft: Create as draft PR

        Returns:
            PR creation result with URL
        """
        if not self._check_gh_cli():
            return {
                "success": False,
                "error": "GitHub CLI not installed or not authenticated. Run 'gh auth login'"
            }

        try:
            # Build command
            cmd = ["gh", "pr", "create", "--title", title]

            if body:
                cmd.extend(["--body", body])
            if base:
                cmd.extend(["--base", base])
            if head:
                cmd.extend(["--head", head])
            if draft:
                cmd.append("--draft")

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60
            )

            if result.returncode == 0:
                pr_url = result.stdout.strip()
                self.audit_log(
                    action="pr_created",
                    tool="github",
                    params={"title": title, "base": base, "draft": draft},
                    result="success",
                    details=pr_url
                )
                return {
                    "success": True,
                    "url": pr_url,
                    "title": title,
                    "draft": draft
                }
            else:
                return {
                    "success": False,
                    "error": result.stderr.strip() or "Failed to create PR"
                }

        except subprocess.TimeoutExpired:
            return {"success": False, "error": "PR creation timed out"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def list_pull_requests(
        self,
        state: str = "open",
        limit: int = 10,
        author: str = None
    ) -> Dict[str, Any]:
        """
        List GitHub Pull Requests.

        Args:
            state: PR state (open, closed, merged, all)
            limit: Maximum PRs to return
            author: Filter by author

        Returns:
            List of PRs with metadata
        """
        if not self._check_gh_cli():
            return {"success": False, "error": "GitHub CLI not available"}

        try:
            cmd = [
                "gh", "pr", "list",
                "--state", state,
                "--limit", str(limit),
                "--json", "number,title,state,author,createdAt,url,isDraft"
            ]

            if author:
                cmd.extend(["--author", author])

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if result.returncode == 0:
                import json
                prs = json.loads(result.stdout) if result.stdout.strip() else []
                return {
                    "success": True,
                    "pull_requests": prs,
                    "count": len(prs),
                    "state": state
                }
            else:
                return {"success": False, "error": result.stderr.strip()}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def create_issue(
        self,
        title: str,
        body: str = "",
        labels: List[str] = None,
        assignees: List[str] = None
    ) -> Dict[str, Any]:
        """
        Create a GitHub Issue.

        Args:
            title: Issue title
            body: Issue description
            labels: List of labels
            assignees: List of assignees

        Returns:
            Issue creation result with URL
        """
        if not self._check_gh_cli():
            return {"success": False, "error": "GitHub CLI not available"}

        try:
            cmd = ["gh", "issue", "create", "--title", title]

            if body:
                cmd.extend(["--body", body])
            if labels:
                for label in labels:
                    cmd.extend(["--label", label])
            if assignees:
                for assignee in assignees:
                    cmd.extend(["--assignee", assignee])

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

            if result.returncode == 0:
                issue_url = result.stdout.strip()
                self.audit_log(
                    action="issue_created",
                    tool="github",
                    params={"title": title, "labels": labels},
                    result="success",
                    details=issue_url
                )
                return {
                    "success": True,
                    "url": issue_url,
                    "title": title
                }
            else:
                return {"success": False, "error": result.stderr.strip()}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def list_issues(
        self,
        state: str = "open",
        limit: int = 10,
        labels: List[str] = None
    ) -> Dict[str, Any]:
        """
        List GitHub Issues.

        Args:
            state: Issue state (open, closed, all)
            limit: Maximum issues to return
            labels: Filter by labels

        Returns:
            List of issues
        """
        if not self._check_gh_cli():
            return {"success": False, "error": "GitHub CLI not available"}

        try:
            cmd = [
                "gh", "issue", "list",
                "--state", state,
                "--limit", str(limit),
                "--json", "number,title,state,author,createdAt,url,labels"
            ]

            if labels:
                cmd.extend(["--label", ",".join(labels)])

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if result.returncode == 0:
                import json
                issues = json.loads(result.stdout) if result.stdout.strip() else []
                return {
                    "success": True,
                    "issues": issues,
                    "count": len(issues),
                    "state": state
                }
            else:
                return {"success": False, "error": result.stderr.strip()}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_repo_info(self) -> Dict[str, Any]:
        """Get current repository information."""
        if not self._check_gh_cli():
            return {"success": False, "error": "GitHub CLI not available"}

        try:
            result = subprocess.run(
                ["gh", "repo", "view", "--json",
                 "name,owner,description,url,defaultBranchRef,isPrivate,stargazerCount"],
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                import json
                repo = json.loads(result.stdout)
                return {
                    "success": True,
                    "repo": repo,
                    "full_name": f"{repo.get('owner', {}).get('login', '')}/{repo.get('name', '')}",
                    "url": repo.get("url", "")
                }
            else:
                return {"success": False, "error": result.stderr.strip()}

        except Exception as e:
            return {"success": False, "error": str(e)}

    # =========================================================================
    # WAVE 7: FRAMEWORK DETECTION (Project Intelligence)
    # =========================================================================

    def detect_project_framework(self, path: str = ".") -> Dict[str, Any]:
        """
        Auto-detect project framework and technology stack.

        Args:
            path: Project root path

        Returns:
            Detected frameworks and recommendations
        """
        project_path = Path(path)
        if not project_path.exists():
            return {"success": False, "error": f"Path not found: {path}"}

        detections = {
            "primary_language": None,
            "frameworks": [],
            "package_managers": [],
            "build_tools": [],
            "testing_frameworks": [],
            "ci_cd": [],
            "containerization": [],
            "recommendations": []
        }

        # Language detection patterns
        language_files = {
            "python": ["*.py", "requirements.txt", "pyproject.toml", "setup.py", "Pipfile"],
            "javascript": ["*.js", "*.jsx", "package.json"],
            "typescript": ["*.ts", "*.tsx", "tsconfig.json"],
            "go": ["*.go", "go.mod", "go.sum"],
            "rust": ["*.rs", "Cargo.toml"],
            "java": ["*.java", "pom.xml", "build.gradle"],
            "ruby": ["*.rb", "Gemfile"],
            "php": ["*.php", "composer.json"],
        }

        # Framework detection patterns
        framework_patterns = {
            # Python
            "django": ["manage.py", "django", "settings.py"],
            "flask": ["flask", "app.py"],
            "fastapi": ["fastapi", "main.py"],
            "pytorch": ["torch", "pytorch"],
            "tensorflow": ["tensorflow", "keras"],

            # JavaScript/TypeScript
            "react": ["react", "jsx", "tsx"],
            "nextjs": ["next.config", "pages/", "app/"],
            "vue": ["vue", ".vue"],
            "angular": ["angular.json", "@angular"],
            "express": ["express"],
            "nestjs": ["@nestjs"],

            # Other
            "rails": ["rails", "Gemfile"],
            "spring": ["spring", "application.properties"],
        }

        # Check for configuration files
        config_checks = {
            # Package managers
            "npm": "package.json",
            "yarn": "yarn.lock",
            "pnpm": "pnpm-lock.yaml",
            "pip": "requirements.txt",
            "poetry": "pyproject.toml",
            "pipenv": "Pipfile",
            "cargo": "Cargo.toml",
            "go_modules": "go.mod",

            # Build tools
            "webpack": "webpack.config.js",
            "vite": "vite.config.js",
            "rollup": "rollup.config.js",
            "esbuild": "esbuild.config.js",
            "makefile": "Makefile",

            # Testing
            "jest": "jest.config.js",
            "pytest": "pytest.ini",
            "mocha": ".mocharc",
            "vitest": "vitest.config",

            # CI/CD
            "github_actions": ".github/workflows",
            "gitlab_ci": ".gitlab-ci.yml",
            "jenkins": "Jenkinsfile",
            "circleci": ".circleci/config.yml",

            # Containerization
            "docker": "Dockerfile",
            "docker_compose": "docker-compose.yml",
            "kubernetes": "k8s/",
        }

        try:
            # Detect primary language by file count
            lang_counts = {}
            for lang, patterns in language_files.items():
                count = 0
                for pattern in patterns:
                    if "*" in pattern:
                        count += len(list(project_path.rglob(pattern)))
                    elif (project_path / pattern).exists():
                        count += 10  # Config files weighted higher
                lang_counts[lang] = count

            if lang_counts:
                detections["primary_language"] = max(lang_counts, key=lang_counts.get)
                detections["language_confidence"] = lang_counts

            # Check config files
            for tool, file_pattern in config_checks.items():
                check_path = project_path / file_pattern
                if check_path.exists():
                    category = None
                    if tool in ["npm", "yarn", "pnpm", "pip", "poetry", "pipenv", "cargo", "go_modules"]:
                        category = "package_managers"
                    elif tool in ["webpack", "vite", "rollup", "esbuild", "makefile"]:
                        category = "build_tools"
                    elif tool in ["jest", "pytest", "mocha", "vitest"]:
                        category = "testing_frameworks"
                    elif tool in ["github_actions", "gitlab_ci", "jenkins", "circleci"]:
                        category = "ci_cd"
                    elif tool in ["docker", "docker_compose", "kubernetes"]:
                        category = "containerization"

                    if category:
                        detections[category].append(tool)

            # Detect frameworks by reading package.json or pyproject.toml
            package_json = project_path / "package.json"
            if package_json.exists():
                import json
                try:
                    with open(package_json) as f:
                        pkg = json.load(f)
                    deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}

                    if "react" in deps:
                        detections["frameworks"].append("react")
                    if "next" in deps:
                        detections["frameworks"].append("nextjs")
                    if "vue" in deps:
                        detections["frameworks"].append("vue")
                    if "@angular/core" in deps:
                        detections["frameworks"].append("angular")
                    if "express" in deps:
                        detections["frameworks"].append("express")
                    if "@nestjs/core" in deps:
                        detections["frameworks"].append("nestjs")
                except (json.JSONDecodeError, IOError, OSError) as e:
                    import logging
                    logging.debug(f"Failed to parse package.json: {e}")

            pyproject = project_path / "pyproject.toml"
            if pyproject.exists():
                try:
                    content = pyproject.read_text()
                    if "django" in content.lower():
                        detections["frameworks"].append("django")
                    if "flask" in content.lower():
                        detections["frameworks"].append("flask")
                    if "fastapi" in content.lower():
                        detections["frameworks"].append("fastapi")
                    if "pytest" in content.lower():
                        detections["testing_frameworks"].append("pytest")
                except (IOError, OSError) as e:
                    import logging
                    logging.debug(f"Failed to read pyproject.toml: {e}")

            # Generate recommendations
            if "nextjs" in detections["frameworks"]:
                detections["recommendations"].append("Use 'npm run dev' for development")
                detections["recommendations"].append("Check app/ or pages/ for routing")
            elif "react" in detections["frameworks"]:
                detections["recommendations"].append("Use 'npm start' or 'npm run dev'")
            if "django" in detections["frameworks"]:
                detections["recommendations"].append("Use 'python manage.py runserver'")
            if "fastapi" in detections["frameworks"]:
                detections["recommendations"].append("Use 'uvicorn main:app --reload'")
            if "docker" in detections["containerization"]:
                detections["recommendations"].append("Use 'docker-compose up' for local dev")

            return {
                "success": True,
                **detections
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    # =========================================================================
    # WAVE 7: MCP TOOL DISCOVERY
    # =========================================================================

    def discover_mcp_servers(self) -> Dict[str, Any]:
        """
        Discover available MCP servers and their tools.

        Returns:
            List of discovered MCP servers and their capabilities
        """
        discovered = {
            "servers": [],
            "total_tools": 0
        }

        # Check for MCP config files
        mcp_config_locations = [
            Path.home() / ".config" / "mcp" / "servers.json",
            Path.cwd() / ".mcp" / "config.json",
            Path.cwd() / "mcp.json",
        ]

        for config_path in mcp_config_locations:
            if config_path.exists():
                try:
                    import json
                    with open(config_path) as f:
                        config = json.load(f)

                    servers = config.get("servers", config.get("mcpServers", []))
                    for server in servers:
                        server_info = {
                            "name": server.get("name", "unknown"),
                            "command": server.get("command", ""),
                            "args": server.get("args", []),
                            "tools": server.get("tools", []),
                            "status": "configured"
                        }
                        discovered["servers"].append(server_info)
                        discovered["total_tools"] += len(server_info["tools"])
                except Exception as e:
                    discovered["errors"] = discovered.get("errors", [])
                    discovered["errors"].append(f"Failed to parse {config_path}: {e}")

        # Check for common MCP servers
        common_servers = [
            {"name": "filesystem", "check": "mcp-server-filesystem"},
            {"name": "github", "check": "mcp-server-github"},
            {"name": "postgres", "check": "mcp-server-postgres"},
            {"name": "sqlite", "check": "mcp-server-sqlite"},
        ]

        for server in common_servers:
            try:
                result = subprocess.run(
                    ["which", server["check"]],
                    capture_output=True,
                    timeout=5
                )
                if result.returncode == 0:
                    discovered["servers"].append({
                        "name": server["name"],
                        "command": server["check"],
                        "status": "installed",
                        "path": result.stdout.decode().strip()
                    })
            except (subprocess.SubprocessError, FileNotFoundError, OSError) as e:
                import logging
                logging.debug(f"MCP server check failed for {server.get('name', 'unknown')}: {e}")

        return {
            "success": True,
            **discovered
        }

    def get_mcp_status(self) -> Dict[str, Any]:
        """Get MCP server status and available tools."""
        discovery = self.discover_mcp_servers()

        return {
            "success": True,
            "mcp_enabled": len(discovery.get("servers", [])) > 0,
            "servers": discovery.get("servers", []),
            "total_tools": discovery.get("total_tools", 0),
            "config_locations_checked": [
                str(Path.home() / ".config" / "mcp" / "servers.json"),
                str(Path.cwd() / ".mcp" / "config.json"),
                str(Path.cwd() / "mcp.json"),
            ]
        }

    # =========================================================================
    # WAVE 7: MEMORY CONTEXT INJECTION
    # =========================================================================

    def get_memory_context(self, scope: str = "project") -> str:
        """
        Get memory content formatted for injection into system prompts.

        Args:
            scope: 'project' or 'global'

        Returns:
            Formatted memory context string
        """
        memory_result = self.read_memory(scope=scope)

        if not memory_result.get("success") or not memory_result.get("content"):
            return ""

        content = memory_result["content"].strip()
        if not content:
            return ""

        return f"""
<user_memory scope="{scope}">
{content}
</user_memory>
"""

    def get_full_context(self) -> Dict[str, Any]:
        """
        Get full context including memory, project info, and recent files.

        Returns:
            Complete context for LLM injection
        """
        context_parts = []

        # Add project memory
        project_memory = self.get_memory_context("project")
        if project_memory:
            context_parts.append(project_memory)

        # Add global memory
        global_memory = self.get_memory_context("global")
        if global_memory:
            context_parts.append(global_memory)

        # Add project detection
        framework_info = self.detect_project_framework()
        if framework_info.get("success"):
            lang = framework_info.get("primary_language", "unknown")
            frameworks = framework_info.get("frameworks", [])
            if lang or frameworks:
                context_parts.append(f"""
<project_context>
Primary Language: {lang}
Frameworks: {', '.join(frameworks) if frameworks else 'None detected'}
</project_context>
""")

        return {
            "success": True,
            "context": "\n".join(context_parts),
            "has_memory": bool(project_memory or global_memory),
            "has_project_info": framework_info.get("success", False)
        }

    # =========================================================================
    # WAVE 7: CUSTOM SLASH COMMANDS EXECUTION
    # =========================================================================

    def execute_custom_command(
        self,
        command_name: str,
        args: List[str] = None
    ) -> Dict[str, Any]:
        """
        Execute a custom slash command from .juancs/commands/.

        Args:
            command_name: Name of the command (without slash)
            args: Arguments to pass to the command

        Returns:
            Command execution result with expanded prompt
        """
        commands_dir = Path.cwd() / ".juancs" / "commands"

        if not commands_dir.exists():
            return {
                "success": False,
                "error": "No custom commands directory found. Create .juancs/commands/"
            }

        # Find command file
        command_file = commands_dir / f"{command_name}.md"
        if not command_file.exists():
            # Try without extension
            for ext in [".md", ".txt", ""]:
                test_file = commands_dir / f"{command_name}{ext}"
                if test_file.exists():
                    command_file = test_file
                    break
            else:
                # List available commands
                available = [f.stem for f in commands_dir.glob("*.md")]
                return {
                    "success": False,
                    "error": f"Command '{command_name}' not found",
                    "available_commands": available
                }

        try:
            # Read command template
            template = command_file.read_text()

            # Substitute arguments
            expanded = template
            args = args or []

            # Replace $1, $2, etc.
            for i, arg in enumerate(args, 1):
                expanded = expanded.replace(f"${i}", arg)

            # Replace $@ with all args
            expanded = expanded.replace("$@", " ".join(args))

            # Replace {args} with all args
            expanded = expanded.replace("{args}", " ".join(args))

            # Clean up unused placeholders
            import re
            expanded = re.sub(r'\$\d+', '', expanded)

            self.audit_log(
                action="custom_command",
                tool="slash_commands",
                params={"command": command_name, "args": args},
                result="success",
                details=f"Executed /{command_name}"
            )

            return {
                "success": True,
                "command": command_name,
                "expanded_prompt": expanded.strip(),
                "args_used": args,
                "source_file": str(command_file)
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def list_custom_commands(self) -> Dict[str, Any]:
        """List all available custom slash commands."""
        commands_dir = Path.cwd() / ".juancs" / "commands"

        if not commands_dir.exists():
            return {
                "success": True,
                "commands": [],
                "message": "No custom commands directory. Create .juancs/commands/"
            }

        commands = []
        for cmd_file in commands_dir.glob("*.md"):
            try:
                content = cmd_file.read_text()
                # Extract first line as description
                first_line = content.split("\n")[0].strip()
                if first_line.startswith("#"):
                    first_line = first_line.lstrip("#").strip()

                commands.append({
                    "name": cmd_file.stem,
                    "file": cmd_file.name,
                    "description": first_line[:100]
                })
            except (IOError, OSError, UnicodeDecodeError) as e:
                import logging
                logging.warning(f"Failed to read slash command file {cmd_file}: {e}")
                commands.append({
                    "name": cmd_file.stem,
                    "file": cmd_file.name,
                    "description": f"(error: {type(e).__name__})"
                })

        return {
            "success": True,
            "commands": commands,
            "count": len(commands),
            "commands_dir": str(commands_dir)
        }


# =============================================================================
# SINGLETON INSTANCE
# =============================================================================

_bridge_instance: Optional[Bridge] = None


def get_bridge() -> Bridge:
    """Get or create bridge singleton."""
    global _bridge_instance
    if _bridge_instance is None:
        _bridge_instance = Bridge()
    return _bridge_instance
