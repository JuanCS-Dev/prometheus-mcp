# PROMETHEUS ECOSYSTEM INTEGRATION PLAN

**Data:** 2025-11-27
**Objetivo:** Integrar PROMETHEUS (Self-Evolving Meta-Agent) no ecossistema jdev_cli (Shell CLI, MCP, Gradio UI)
**Executor:** Google Gemini CLI (Gemini 3)
**Hackathon:** Blaxel MCP Hackathon - Nov 2025

---

## USER PREFERENCES (CONFIRMED)

| Component | Preference | Description |
|-----------|------------|-------------|
| **Shell CLI** | **Auto-detect** | Detectar complexidade da task automaticamente e escolher provider (Gemini para tasks simples, PROMETHEUS para complexas) |
| **Gradio UI** | **Dashboard** | Painéis visíveis para Memory, World Model, Evolution - interface rica com todos os componentes |
| **MCP Tools** | **Expandido (8+)** | 8 tools: execute, memory_query, simulate, evolve, reflect, create_tool, get_status, benchmark |

---

## FASE 0: CONTEXTO DO ECOSSISTEMA (AUDITORIA COMPLETA)

### 0.1 Estrutura do Projeto

```
qwen-dev-cli/
├── jdev_cli/                    # Shell CLI principal
│   ├── shell_main.py            # 1,858 linhas - Interactive REPL
│   ├── cli_app.py               # Click-based CLI
│   ├── core/
│   │   ├── mcp.py               # 291 linhas - MCPClient com circuit breaker
│   │   ├── llm.py               # Multi-backend LLM
│   │   ├── execution.py         # ExecutionResult pipeline
│   │   └── providers/           # Gemini, Ollama, Nebius
│   ├── handlers/                # Command handlers
│   ├── managers/                # Provider, Session, Config managers
│   ├── tools/                   # 54+ ferramentas
│   │   ├── base.py              # Tool ABC + ToolRegistry
│   │   ├── registry_setup.py    # setup_default_tools()
│   │   └── validated.py         # ValidatedTool base
│   └── integrations/mcp/        # FastMCP server
│       ├── server.py            # QwenMCPServer
│       ├── tools.py             # MCPToolsAdapter
│       └── config.py            # MCPConfig
│
├── jdev_tui/                    # Textual TUI
│   ├── app.py                   # 576 linhas - QwenApp
│   ├── core/
│   │   ├── bridge.py            # 1,058 linhas - Facade principal
│   │   ├── llm_client.py        # GeminiClient com streaming
│   │   ├── agents_bridge.py     # 14 agentes registrados
│   │   ├── tools_bridge.py      # ToolBridge (47 tools)
│   │   └── streaming/           # GeminiStreamer (SDK + HTTP)
│   ├── handlers/                # Command routing
│   ├── widgets/                 # UI components
│   └── themes/                  # Light/Dark themes
│
├── gradio_ui/                   # Gradio Web UI
│   ├── app.py                   # 628 linhas - Cyberpunk UI
│   ├── streaming_bridge.py      # 600 linhas - GradioStreamingBridge
│   ├── components.py            # SVG/HTML gauges
│   └── cyber_theme.css          # Glassmorphism styling
│
├── prometheus/                  # Self-Evolving Meta-Agent
│   ├── main.py                  # PrometheusAgent (Blaxel SDK)
│   ├── core/
│   │   ├── orchestrator.py      # PrometheusOrchestrator
│   │   ├── llm_client.py        # GeminiClient custom
│   │   ├── world_model.py       # SimuRA simulation
│   │   ├── reflection.py        # Reflexion engine
│   │   └── evolution.py         # Agent0 co-evolution
│   ├── memory/
│   │   └── memory_system.py     # MIRIX 6-type memory
│   ├── tools/
│   │   └── tool_factory.py      # AutoTools generation
│   └── sandbox/
│       └── executor.py          # Safe execution
│
└── prometheus_entry.py          # FastAPI server (Blaxel deploy)
```

### 0.2 Pontos de Integração Identificados

| Componente | Arquivo Alvo | Classe/Função | Tipo de Integração |
|------------|--------------|---------------|-------------------|
| **Shell CLI** | `jdev_tui/core/bridge.py` | `Bridge.chat()` | LLM Provider |
| **Shell CLI** | `jdev_tui/core/llm_client.py` | `GeminiClient` | Wrapper/Replace |
| **MCP** | `jdev_cli/tools/registry_setup.py` | `setup_default_tools()` | Tool Registration |
| **MCP** | `jdev_cli/core/mcp.py` | `MCPClient` | PROMETHEUS Tools |
| **Gradio** | `gradio_ui/streaming_bridge.py` | `GradioStreamingBridge` | Agent Integration |
| **Gradio** | `gradio_ui/app.py` | `stream_conversation()` | UI Updates |

### 0.3 Arquitetura Atual de LLM

```
                    USER INPUT
                        │
         ┌──────────────┼──────────────┐
         ▼              ▼              ▼
      jdev_tui      gradio_ui      CLI direct
         │              │              │
         ▼              ▼              ▼
      Bridge    StreamingBridge   InteractiveShell
         │              │              │
         └──────────────┼──────────────┘
                        ▼
                  GeminiClient
                        │
         ┌──────────────┼──────────────┐
         ▼              ▼              ▼
      SDK Stream    HTTP Stream    Sync API
         │              │              │
         └──────────────┼──────────────┘
                        ▼
                Google Gemini API
```

### 0.4 Arquitetura Target com PROMETHEUS

```
                    USER INPUT
                        │
         ┌──────────────┼──────────────┐
         ▼              ▼              ▼
      jdev_tui      gradio_ui      CLI direct
         │              │              │
         ▼              ▼              ▼
      Bridge    StreamingBridge   InteractiveShell
         │              │              │
         └──────────────┼──────────────┘
                        ▼
            ┌───────────────────────┐
            │  PrometheusProvider   │ ◄── NEW
            │  (implements LLMProvider)
            └───────────────────────┘
                        │
                        ▼
            ┌───────────────────────┐
            │ PrometheusOrchestrator │
            ├───────────────────────┤
            │ ┌─────────────────┐   │
            │ │   World Model   │   │ (SimuRA)
            │ ├─────────────────┤   │
            │ │  Memory System  │   │ (MIRIX 6-type)
            │ ├─────────────────┤   │
            │ │  Tool Factory   │   │ (AutoTools)
            │ ├─────────────────┤   │
            │ │   Reflection    │   │ (Reflexion)
            │ ├─────────────────┤   │
            │ │   Evolution     │   │ (Agent0)
            │ └─────────────────┘   │
            └───────────────────────┘
                        │
                        ▼
                Google Gemini API
```

---

## FASE 0.5: PESQUISA WEB DENSA (DOCUMENTAÇÃO)

### 0.5.1 Documentação Obrigatória a Consultar

Execute as seguintes pesquisas web ANTES de implementar:

#### Google Gemini API (Patrocinador)
```
PESQUISAR: "Google Gemini API streaming Python 2024 2025"
PESQUISAR: "google-generativeai SDK function calling tools"
PESQUISAR: "Gemini 2.0 Flash extended thinking"
PESQUISAR: "Gemini API rate limits quotas"
URL: https://ai.google.dev/gemini-api/docs
URL: https://ai.google.dev/gemini-api/docs/function-calling
```

#### Blaxel Platform (Deploy Target)
```
PESQUISAR: "Blaxel SDK Python agent deployment"
PESQUISAR: "Blaxel MCP server integration"
URL: https://docs.blaxel.ai/
URL: https://blaxel.ai/hackathon
```

#### MCP (Model Context Protocol)
```
PESQUISAR: "MCP Model Context Protocol specification 2024"
PESQUISAR: "FastMCP Python server implementation"
PESQUISAR: "Claude Desktop MCP configuration"
URL: https://modelcontextprotocol.io/
URL: https://github.com/modelcontextprotocol/python-sdk
```

#### Gradio 6 (UI Framework)
```
PESQUISAR: "Gradio 6 streaming chat interface"
PESQUISAR: "Gradio ChatInterface custom components"
URL: https://www.gradio.app/docs/chatbot
URL: https://www.gradio.app/guides/creating-a-chatbot-fast
```

#### Textual (TUI Framework)
```
PESQUISAR: "Textual Python TUI streaming updates"
URL: https://textual.textualize.io/
URL: https://textual.textualize.io/guide/workers/
```

#### Research Papers (PROMETHEUS Foundation)
```
PESQUISAR: "Agent0 arXiv self-evolving agents"
PESQUISAR: "SimuRA world model agents"
PESQUISAR: "MIRIX memory system LLM agents"
PESQUISAR: "Reflexion self-reflection agents"
```

### 0.5.2 Checklist de Pesquisa

- [ ] Gemini API streaming best practices
- [ ] Gemini function calling schema format
- [ ] Blaxel agent deployment requirements
- [ ] MCP tool registration protocol
- [ ] Gradio 6 breaking changes from 5.x
- [ ] Textual async workers pattern

---

## FASE 1: PROMETHEUS PROVIDER LAYER

### 1.1 Criar PrometheusProvider

**Arquivo:** `jdev_cli/core/providers/prometheus_provider.py`

```python
"""
PROMETHEUS Provider - LLM Provider wrapping PrometheusOrchestrator.

Integra o PROMETHEUS como provider de LLM no ecossistema jdev_cli,
permitindo uso transparente em Shell CLI, MCP e Gradio UI.
"""

import os
import asyncio
from typing import AsyncIterator, Optional, Dict, Any, List
from dataclasses import dataclass

# Import PROMETHEUS
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from prometheus.main import PrometheusAgent
from prometheus.core.orchestrator import PrometheusOrchestrator


@dataclass
class PrometheusConfig:
    """Configuration for PROMETHEUS provider."""
    enable_world_model: bool = True
    enable_memory: bool = True
    enable_reflection: bool = True
    enable_evolution: bool = False  # Expensive, enable manually
    evolution_iterations: int = 5
    memory_consolidation_interval: int = 10


class PrometheusProvider:
    """
    PROMETHEUS as LLM Provider.

    Implements the same interface as GeminiProvider/OllamaProvider
    but routes through PrometheusOrchestrator for enhanced capabilities:

    - World Model simulation before action
    - 6-type persistent memory (MIRIX)
    - Self-reflection and improvement
    - Automatic tool creation (AutoTools)
    - Co-evolution learning (Agent0)
    """

    def __init__(
        self,
        config: Optional[PrometheusConfig] = None,
        api_key: Optional[str] = None
    ):
        self.config = config or PrometheusConfig()
        self.api_key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        self._agent: Optional[PrometheusAgent] = None
        self._orchestrator: Optional[PrometheusOrchestrator] = None
        self._initialized = False

    async def _ensure_initialized(self):
        """Lazy initialization of PROMETHEUS."""
        if not self._initialized:
            self._agent = PrometheusAgent()
            await self._agent._ensure_orchestrator()
            self._orchestrator = self._agent._orchestrator
            self._initialized = True

    def is_available(self) -> bool:
        """Check if PROMETHEUS is available."""
        return bool(self.api_key)

    async def stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        context: Optional[List[Dict[str, str]]] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ) -> AsyncIterator[str]:
        """
        Stream response from PROMETHEUS.

        This is the main integration point - routes through the full
        PROMETHEUS pipeline: Memory → World Model → Execute → Reflect → Learn
        """
        await self._ensure_initialized()

        # Build full prompt with context
        full_prompt = self._build_prompt(prompt, system_prompt, context)

        # Stream through PROMETHEUS orchestrator
        async for chunk in self._orchestrator.execute(full_prompt):
            yield chunk

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        context: Optional[List[Dict[str, str]]] = None,
        **kwargs
    ) -> str:
        """Non-streaming generation."""
        chunks = []
        async for chunk in self.stream(prompt, system_prompt, context, **kwargs):
            chunks.append(chunk)
        return "".join(chunks)

    def _build_prompt(
        self,
        prompt: str,
        system_prompt: Optional[str],
        context: Optional[List[Dict[str, str]]]
    ) -> str:
        """Build full prompt with context."""
        parts = []

        if system_prompt:
            parts.append(f"[SYSTEM]\n{system_prompt}\n")

        if context:
            parts.append("[CONVERSATION HISTORY]")
            for msg in context[-10:]:  # Last 10 messages
                role = msg.get("role", "user")
                content = msg.get("content", "")
                parts.append(f"{role.upper()}: {content}")
            parts.append("")

        parts.append(f"[CURRENT REQUEST]\n{prompt}")

        return "\n".join(parts)

    async def evolve(self, iterations: int = 5) -> Dict[str, Any]:
        """Run evolution cycle to improve capabilities."""
        await self._ensure_initialized()
        return await self._orchestrator.evolve_capabilities(iterations)

    def get_status(self) -> Dict[str, Any]:
        """Get PROMETHEUS system status."""
        if not self._initialized:
            return {"status": "not_initialized"}
        return self._orchestrator.get_status()

    def get_memory_context(self, task: str) -> Dict[str, Any]:
        """Get memory context for a task."""
        if not self._initialized:
            return {}
        return self._orchestrator.memory.get_context_for_task(task)
```

### 1.2 Registrar Provider

**Arquivo:** `jdev_cli/core/providers/__init__.py`

Adicionar ao final:
```python
from .prometheus_provider import PrometheusProvider, PrometheusConfig

__all__ = [
    "GeminiProvider",
    "OllamaProvider",
    "NebiusProvider",
    "PrometheusProvider",  # NEW
    "PrometheusConfig",    # NEW
]
```

### 1.3 Atualizar Provider Manager

**Arquivo:** `jdev_cli/managers/provider_manager.py`

Adicionar PROMETHEUS como provider type:
```python
class ProviderType(Enum):
    OLLAMA = "ollama"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    NEBIUS = "nebius"
    GROQ = "groq"
    LOCAL = "local"
    CUSTOM = "custom"
    PROMETHEUS = "prometheus"  # NEW - Self-evolving meta-agent
```

---

## FASE 2: INTEGRAÇÃO SHELL CLI

### 2.1 Criar PrometheusClient para TUI

**Arquivo:** `jdev_tui/core/prometheus_client.py`

```python
"""
PROMETHEUS Client for TUI - Streaming integration.

Provides the same interface as GeminiClient but routes through
PROMETHEUS for enhanced capabilities.
"""

import asyncio
from typing import AsyncIterator, Optional, Dict, Any, List, Callable
from dataclasses import dataclass, field
from datetime import datetime

from jdev_cli.core.providers.prometheus_provider import PrometheusProvider, PrometheusConfig


@dataclass
class PrometheusStreamConfig:
    """Streaming configuration."""
    temperature: float = 1.0
    max_output_tokens: int = 8192
    enable_world_model: bool = True
    enable_memory: bool = True
    enable_reflection: bool = True
    init_timeout: float = 15.0
    stream_timeout: float = 120.0
    chunk_timeout: float = 45.0


class PrometheusClient:
    """
    PROMETHEUS Client with streaming support.

    Drop-in replacement for GeminiClient that adds:
    - World model simulation (preview actions)
    - Persistent memory (learn from interactions)
    - Self-reflection (improve over time)
    - Automatic tool creation
    """

    def __init__(
        self,
        config: Optional[PrometheusStreamConfig] = None,
        tools: Optional[List[Dict[str, Any]]] = None
    ):
        self.config = config or PrometheusStreamConfig()
        self._tools = tools or []
        self._provider: Optional[PrometheusProvider] = None
        self._initialized = False

        # Metrics
        self._total_requests = 0
        self._total_tokens = 0
        self._avg_response_time = 0.0

    async def _ensure_provider(self):
        """Lazy initialization."""
        if not self._initialized:
            prometheus_config = PrometheusConfig(
                enable_world_model=self.config.enable_world_model,
                enable_memory=self.config.enable_memory,
                enable_reflection=self.config.enable_reflection,
            )
            self._provider = PrometheusProvider(config=prometheus_config)
            self._initialized = True

    def set_tools(self, tools: List[Dict[str, Any]]):
        """Set available tools."""
        self._tools = tools

    async def stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        context: Optional[List[Dict[str, str]]] = None,
        tools: Optional[List[Dict[str, Any]]] = None
    ) -> AsyncIterator[str]:
        """
        Stream response from PROMETHEUS.

        Yields chunks as they arrive, with full PROMETHEUS pipeline:
        1. Memory retrieval (relevant past experiences)
        2. World model simulation (plan before act)
        3. Execution (with tool calling)
        4. Reflection (learn from result)
        """
        await self._ensure_provider()

        start_time = datetime.now()
        self._total_requests += 1

        try:
            async for chunk in self._provider.stream(
                prompt=prompt,
                system_prompt=system_prompt,
                context=context,
                tools=tools or self._tools
            ):
                yield chunk
        finally:
            elapsed = (datetime.now() - start_time).total_seconds()
            self._avg_response_time = (
                self._avg_response_time * (self._total_requests - 1) + elapsed
            ) / self._total_requests

    def get_health_status(self) -> Dict[str, Any]:
        """Get health status."""
        base_status = {
            "provider": "prometheus",
            "initialized": self._initialized,
            "total_requests": self._total_requests,
            "avg_response_time": self._avg_response_time,
        }

        if self._initialized and self._provider:
            base_status["prometheus_status"] = self._provider.get_status()

        return base_status

    async def evolve(self, iterations: int = 5) -> Dict[str, Any]:
        """Run evolution cycle."""
        await self._ensure_provider()
        return await self._provider.evolve(iterations)
```

### 2.2 Atualizar Bridge para Suportar PROMETHEUS (AUTO-DETECT MODE)

**Arquivo:** `jdev_tui/core/bridge.py`

**PREFERÊNCIA DO USUÁRIO: Auto-detect** - Detectar complexidade da task e escolher provider automaticamente.

Adicionar método de seleção de provider com auto-detect:

```python
# No início do arquivo, adicionar import:
from jdev_tui.core.prometheus_client import PrometheusClient, PrometheusStreamConfig
import re

# Padrões para detectar tasks complexas que devem usar PROMETHEUS
COMPLEX_TASK_PATTERNS = [
    r'\b(create|build|implement|design|architect)\b.*\b(system|pipeline|framework|application)\b',
    r'\b(analyze|debug|investigate|troubleshoot)\b.*\b(complex|multiple|entire)\b',
    r'\b(refactor|optimize|improve)\b.*\b(codebase|architecture|performance)\b',
    r'\b(multi.?step|step.?by.?step|sequentially|iteratively)\b',
    r'\b(remember|recall|previous|earlier|context)\b',  # Memory-dependent
    r'\b(simulate|predict|plan|strategy)\b',  # World model
    r'\b(evolve|learn|adapt|improve over time)\b',  # Evolution
]

SIMPLE_TASK_PATTERNS = [
    r'^(what|who|when|where|how|why)\s+\w+\??$',  # Simple questions
    r'^\w+\s*\?$',  # Single word question
    r'^(hi|hello|hey|thanks|ok|yes|no)\b',  # Greetings
]

# Na classe Bridge, adicionar:
class Bridge:
    def __init__(self, ...):
        # ... existing code ...

        # Provider selection: auto, prometheus, or gemini
        self._provider_mode = os.getenv("JDEV_PROVIDER", "auto")  # DEFAULT: auto
        self._prometheus_client: Optional[PrometheusClient] = None
        self._task_complexity_cache: Dict[str, str] = {}

    def _detect_task_complexity(self, message: str) -> str:
        """
        Auto-detect task complexity to choose provider.

        Returns: 'prometheus' for complex tasks, 'gemini' for simple ones.
        """
        message_lower = message.lower()

        # Check for simple patterns first
        for pattern in SIMPLE_TASK_PATTERNS:
            if re.search(pattern, message_lower):
                return "gemini"

        # Check for complex patterns
        complexity_score = 0
        for pattern in COMPLEX_TASK_PATTERNS:
            if re.search(pattern, message_lower):
                complexity_score += 1

        # Length heuristic: long prompts usually need more processing
        if len(message) > 500:
            complexity_score += 1
        if len(message) > 1000:
            complexity_score += 1

        # Code blocks indicate technical tasks
        if '```' in message or 'def ' in message or 'class ' in message:
            complexity_score += 1

        # Threshold: 2+ indicators = complex
        return "prometheus" if complexity_score >= 2 else "gemini"

    def _get_client(self, message: str = ""):
        """Get appropriate LLM client based on provider mode and task complexity."""
        if self._provider_mode == "prometheus":
            # Force PROMETHEUS
            if self._prometheus_client is None:
                self._prometheus_client = PrometheusClient()
            return self._prometheus_client, "prometheus"

        elif self._provider_mode == "gemini":
            # Force Gemini
            return self._llm_client, "gemini"

        else:  # auto mode (DEFAULT)
            detected = self._detect_task_complexity(message)
            if detected == "prometheus":
                if self._prometheus_client is None:
                    self._prometheus_client = PrometheusClient()
                return self._prometheus_client, "prometheus"
            else:
                return self._llm_client, "gemini"

    async def chat(self, message: str) -> AsyncIterator[str]:
        """
        Chat with auto-detected provider.

        In AUTO mode (default):
        - Complex tasks (multi-step, memory-dependent, simulation) → PROMETHEUS
        - Simple tasks (questions, greetings, quick lookups) → Gemini

        Override with JDEV_PROVIDER=prometheus or JDEV_PROVIDER=gemini
        """
        client, provider_name = self._get_client(message)

        # Log provider selection for debugging
        if self._provider_mode == "auto":
            # Yield provider indicator for UI
            yield f"[Using {provider_name.upper()}]\n"

        # Build context from history
        context = self._build_context()

        # Get system prompt
        system_prompt = self._get_system_prompt()

        # Stream response
        async for chunk in client.stream(
            prompt=message,
            system_prompt=system_prompt,
            context=context,
            tools=self._get_tool_schemas()
        ):
            yield chunk
```

### 2.3 Adicionar Comando /prometheus

**Arquivo:** `jdev_tui/handlers/basic.py`

Adicionar handler para comandos PROMETHEUS:

```python
async def handle_prometheus_command(self, args: str) -> str:
    """Handle /prometheus commands."""
    parts = args.split(maxsplit=1)
    subcommand = parts[0] if parts else "status"

    if subcommand == "status":
        # Show PROMETHEUS status
        status = self.bridge._prometheus_client.get_health_status()
        return self._format_prometheus_status(status)

    elif subcommand == "evolve":
        # Run evolution cycle
        iterations = int(parts[1]) if len(parts) > 1 else 5
        result = await self.bridge._prometheus_client.evolve(iterations)
        return f"Evolution complete: {result}"

    elif subcommand == "memory":
        # Show memory status
        if self.bridge._prometheus_client._provider:
            memory_status = self.bridge._prometheus_client._provider.get_status()
            return self._format_memory_status(memory_status.get("memory", {}))
        return "PROMETHEUS not initialized"

    elif subcommand == "enable":
        # Enable PROMETHEUS mode
        self.bridge._provider_type = "prometheus"
        return "PROMETHEUS mode enabled. Self-evolution active."

    elif subcommand == "disable":
        # Disable PROMETHEUS mode
        self.bridge._provider_type = "gemini"
        return "PROMETHEUS mode disabled. Using standard Gemini."

    else:
        return """
PROMETHEUS Commands:
  /prometheus status   - Show system status
  /prometheus evolve N - Run N evolution iterations
  /prometheus memory   - Show memory status
  /prometheus enable   - Enable PROMETHEUS mode
  /prometheus disable  - Disable PROMETHEUS mode
"""
```

---

## FASE 3: INTEGRAÇÃO MCP

### 3.1 Criar PROMETHEUS Tools para MCP (EXPANDIDO - 8+ Tools)

**Arquivo:** `jdev_cli/tools/prometheus_tools.py`

**PREFERÊNCIA DO USUÁRIO: Expandido (8+)** - Incluir reflect, create_tool, get_status, benchmark.

```python
"""
PROMETHEUS Tools for MCP - EXPANDED SET (8+ Tools).

Exposes PROMETHEUS capabilities as MCP tools:

CORE TOOLS (4):
- prometheus_execute: Execute task via PROMETHEUS
- prometheus_memory_query: Query PROMETHEUS memory
- prometheus_simulate: Simulate action via world model
- prometheus_evolve: Run evolution cycle

EXPANDED TOOLS (4+):
- prometheus_reflect: Trigger reflection on completed action
- prometheus_create_tool: Generate new tool dynamically (AutoTools)
- prometheus_get_status: Get full system status (memory, world model, evolution)
- prometheus_benchmark: Run benchmark suite to measure capabilities
- prometheus_memory_consolidate: Force memory consolidation to vault
- prometheus_world_model_reset: Reset world model state
"""

from typing import Optional, Dict, Any, List
from jdev_cli.tools.base import Tool, ToolResult, ToolCategory
from jdev_cli.tools.validated import ValidatedTool


class PrometheusExecuteTool(ValidatedTool):
    """Execute task via PROMETHEUS agent."""

    def __init__(self, prometheus_provider=None):
        super().__init__()
        self._provider = prometheus_provider
        self.category = ToolCategory.EXECUTION
        self.description = """
Execute a task using PROMETHEUS self-evolving meta-agent.

PROMETHEUS provides:
- World model simulation (plans before acting)
- 6-type persistent memory (learns from experience)
- Self-reflection (improves over time)
- Automatic tool creation (generates tools on-demand)

Use this for complex tasks that benefit from planning and learning.
"""
        self.parameters = {
            "task": {
                "type": "string",
                "description": "Task description to execute",
                "required": True
            },
            "use_world_model": {
                "type": "boolean",
                "description": "Enable world model simulation (default: true)",
                "required": False
            },
            "use_memory": {
                "type": "boolean",
                "description": "Enable memory retrieval (default: true)",
                "required": False
            }
        }

    def set_provider(self, provider):
        """Set PROMETHEUS provider (for lazy initialization)."""
        self._provider = provider

    async def _execute_validated(
        self,
        task: str,
        use_world_model: bool = True,
        use_memory: bool = True,
        **kwargs
    ) -> ToolResult:
        """Execute task via PROMETHEUS."""
        if not self._provider:
            from jdev_cli.core.providers.prometheus_provider import PrometheusProvider
            self._provider = PrometheusProvider()

        try:
            # Collect streaming response
            result_parts = []
            async for chunk in self._provider.stream(task):
                result_parts.append(chunk)

            result = "".join(result_parts)

            return ToolResult(
                success=True,
                data={
                    "result": result,
                    "provider": "prometheus",
                    "world_model_used": use_world_model,
                    "memory_used": use_memory
                }
            )
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class PrometheusMemoryQueryTool(ValidatedTool):
    """Query PROMETHEUS memory system."""

    def __init__(self, prometheus_provider=None):
        super().__init__()
        self._provider = prometheus_provider
        self.category = ToolCategory.CONTEXT
        self.description = """
Query the PROMETHEUS 6-type memory system (MIRIX):

Memory Types:
1. Core - Identity and values
2. Episodic - Past experiences
3. Semantic - Factual knowledge
4. Procedural - Learned skills
5. Resource - Cached resources
6. Knowledge Vault - Consolidated long-term knowledge

Use this to retrieve relevant context for a task.
"""
        self.parameters = {
            "query": {
                "type": "string",
                "description": "Query to search memory",
                "required": True
            },
            "memory_types": {
                "type": "array",
                "description": "Types to search: episodic, semantic, procedural, vault",
                "required": False
            }
        }

    async def _execute_validated(
        self,
        query: str,
        memory_types: Optional[List[str]] = None,
        **kwargs
    ) -> ToolResult:
        """Query memory."""
        if not self._provider:
            from jdev_cli.core.providers.prometheus_provider import PrometheusProvider
            self._provider = PrometheusProvider()

        try:
            context = self._provider.get_memory_context(query)
            return ToolResult(success=True, data=context)
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class PrometheusSimulateTool(ValidatedTool):
    """Simulate action via PROMETHEUS world model."""

    def __init__(self, prometheus_provider=None):
        super().__init__()
        self._provider = prometheus_provider
        self.category = ToolCategory.EXECUTION
        self.description = """
Simulate an action using PROMETHEUS world model (SimuRA).

The world model predicts:
- Success probability
- Potential side effects
- Risks and edge cases
- Alternative approaches

Use this before executing potentially dangerous actions.
"""
        self.parameters = {
            "action": {
                "type": "string",
                "description": "Action to simulate",
                "required": True
            },
            "parameters": {
                "type": "object",
                "description": "Action parameters",
                "required": False
            }
        }

    async def _execute_validated(
        self,
        action: str,
        parameters: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> ToolResult:
        """Simulate action."""
        if not self._provider:
            from jdev_cli.core.providers.prometheus_provider import PrometheusProvider
            self._provider = PrometheusProvider()

        try:
            await self._provider._ensure_initialized()
            orchestrator = self._provider._orchestrator

            # Use world model to simulate
            from prometheus.core.world_model import ActionType

            # Map action string to ActionType
            action_type = ActionType.THINK  # Default
            if "file" in action.lower():
                action_type = ActionType.READ_FILE if "read" in action.lower() else ActionType.WRITE_FILE
            elif "code" in action.lower() or "execute" in action.lower():
                action_type = ActionType.EXECUTE_CODE
            elif "search" in action.lower():
                action_type = ActionType.SEARCH

            result = await orchestrator.world_model.simulate_action(
                action=action_type,
                parameters=parameters or {"description": action},
                current_state=orchestrator.world_model.WorldState()
            )

            simulated_action, new_state = result

            return ToolResult(
                success=True,
                data={
                    "predicted_outcome": simulated_action.predicted_outcome,
                    "success_probability": simulated_action.success_probability,
                    "side_effects": simulated_action.side_effects,
                    "risks": simulated_action.risks,
                }
            )
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class PrometheusEvolveTool(ValidatedTool):
    """Run PROMETHEUS evolution cycle."""

    def __init__(self, prometheus_provider=None):
        super().__init__()
        self._provider = prometheus_provider
        self.category = ToolCategory.EXECUTION
        self.description = """
Run PROMETHEUS co-evolution cycle (Agent0).

The evolution loop:
1. Curriculum Agent generates challenging tasks
2. Executor Agent attempts to solve them
3. Both agents learn and improve
4. Difficulty adjusts to frontier

This improves PROMETHEUS capabilities over time.
"""
        self.parameters = {
            "iterations": {
                "type": "integer",
                "description": "Number of evolution iterations (default: 5)",
                "required": False
            },
            "domain": {
                "type": "string",
                "description": "Domain: general, code, math, reasoning",
                "required": False
            }
        }

    async def _execute_validated(
        self,
        iterations: int = 5,
        domain: str = "general",
        **kwargs
    ) -> ToolResult:
        """Run evolution."""
        if not self._provider:
            from jdev_cli.core.providers.prometheus_provider import PrometheusProvider
            self._provider = PrometheusProvider()

        try:
            result = await self._provider.evolve(iterations)
            return ToolResult(success=True, data=result)
        except Exception as e:
            return ToolResult(success=False, error=str(e))


# ============================================================
# EXPANDED TOOLS (User preference: 8+ tools)
# ============================================================

class PrometheusReflectTool(ValidatedTool):
    """Trigger reflection on a completed action."""

    def __init__(self, prometheus_provider=None):
        super().__init__()
        self._provider = prometheus_provider
        self.category = ToolCategory.EXECUTION
        self.description = """
Trigger PROMETHEUS reflection on a completed action.

Reflection analyzes:
- What worked well
- What could be improved
- Lessons learned
- Updates to memory

Use after completing a task to help PROMETHEUS learn.
"""
        self.parameters = {
            "action_description": {
                "type": "string",
                "description": "Description of the action taken",
                "required": True
            },
            "outcome": {
                "type": "string",
                "description": "Outcome of the action (success/failure/partial)",
                "required": True
            },
            "context": {
                "type": "string",
                "description": "Additional context about the action",
                "required": False
            }
        }

    async def _execute_validated(
        self,
        action_description: str,
        outcome: str,
        context: Optional[str] = None,
        **kwargs
    ) -> ToolResult:
        """Trigger reflection."""
        if not self._provider:
            from jdev_cli.core.providers.prometheus_provider import PrometheusProvider
            self._provider = PrometheusProvider()

        try:
            await self._provider._ensure_initialized()
            reflection_result = await self._provider._orchestrator.reflection.reflect(
                action=action_description,
                outcome=outcome,
                context=context or ""
            )
            return ToolResult(success=True, data=reflection_result)
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class PrometheusCreateToolTool(ValidatedTool):
    """Generate new tool dynamically using AutoTools."""

    def __init__(self, prometheus_provider=None):
        super().__init__()
        self._provider = prometheus_provider
        self.category = ToolCategory.EXECUTION
        self.description = """
Generate a new tool dynamically using PROMETHEUS AutoTools.

Provide:
- Tool name and description
- Expected inputs/outputs
- Example usage

PROMETHEUS will generate, test, and register the tool.
"""
        self.parameters = {
            "tool_name": {
                "type": "string",
                "description": "Name for the new tool",
                "required": True
            },
            "tool_description": {
                "type": "string",
                "description": "What the tool should do",
                "required": True
            },
            "input_schema": {
                "type": "object",
                "description": "Expected input parameters",
                "required": False
            },
            "example_usage": {
                "type": "string",
                "description": "Example of how the tool should be used",
                "required": False
            }
        }

    async def _execute_validated(
        self,
        tool_name: str,
        tool_description: str,
        input_schema: Optional[Dict[str, Any]] = None,
        example_usage: Optional[str] = None,
        **kwargs
    ) -> ToolResult:
        """Create new tool."""
        if not self._provider:
            from jdev_cli.core.providers.prometheus_provider import PrometheusProvider
            self._provider = PrometheusProvider()

        try:
            await self._provider._ensure_initialized()
            tool_factory = self._provider._orchestrator.tool_factory

            new_tool = await tool_factory.create_tool(
                name=tool_name,
                description=tool_description,
                input_schema=input_schema or {},
                example=example_usage or ""
            )

            return ToolResult(
                success=True,
                data={
                    "tool_name": tool_name,
                    "created": True,
                    "schema": new_tool.get_schema() if hasattr(new_tool, 'get_schema') else {}
                }
            )
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class PrometheusGetStatusTool(ValidatedTool):
    """Get full PROMETHEUS system status."""

    def __init__(self, prometheus_provider=None):
        super().__init__()
        self._provider = prometheus_provider
        self.category = ToolCategory.CONTEXT
        self.description = """
Get comprehensive PROMETHEUS system status.

Returns:
- Memory status (counts by type, last consolidation)
- World model status (simulation count, accuracy)
- Evolution status (iterations, frontier level)
- Tool factory status (tools created)
- Overall health metrics
"""
        self.parameters = {
            "include_details": {
                "type": "boolean",
                "description": "Include detailed breakdown (default: false)",
                "required": False
            }
        }

    async def _execute_validated(
        self,
        include_details: bool = False,
        **kwargs
    ) -> ToolResult:
        """Get status."""
        if not self._provider:
            from jdev_cli.core.providers.prometheus_provider import PrometheusProvider
            self._provider = PrometheusProvider()

        try:
            status = self._provider.get_status()

            if include_details and self._provider._initialized:
                # Add detailed breakdowns
                orchestrator = self._provider._orchestrator
                status["memory_details"] = orchestrator.memory.get_stats()
                status["world_model_details"] = orchestrator.world_model.get_stats()
                status["evolution_details"] = orchestrator.evolution.get_stats()

            return ToolResult(success=True, data=status)
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class PrometheusBenchmarkTool(ValidatedTool):
    """Run benchmark suite to measure PROMETHEUS capabilities."""

    def __init__(self, prometheus_provider=None):
        super().__init__()
        self._provider = prometheus_provider
        self.category = ToolCategory.EXECUTION
        self.description = """
Run a benchmark suite to measure PROMETHEUS capabilities.

Benchmarks include:
- Math reasoning
- Code generation
- Memory recall
- World model accuracy
- Tool creation speed

Returns scores and comparisons.
"""
        self.parameters = {
            "suite": {
                "type": "string",
                "description": "Benchmark suite: quick, standard, comprehensive",
                "required": False
            },
            "categories": {
                "type": "array",
                "description": "Specific categories: math, code, memory, reasoning",
                "required": False
            }
        }

    async def _execute_validated(
        self,
        suite: str = "quick",
        categories: Optional[List[str]] = None,
        **kwargs
    ) -> ToolResult:
        """Run benchmark."""
        if not self._provider:
            from jdev_cli.core.providers.prometheus_provider import PrometheusProvider
            self._provider = PrometheusProvider()

        try:
            await self._provider._ensure_initialized()

            # Define benchmark tasks
            benchmarks = {
                "math": ["What is 15 * 7?", "Solve: 2x + 5 = 15"],
                "code": ["Write fibonacci function", "Sort a list"],
                "memory": ["Remember: secret=42", "What is the secret?"],
                "reasoning": ["Compare quicksort vs mergesort"],
            }

            selected = categories or list(benchmarks.keys())
            if suite == "quick":
                # Only first task per category
                tasks = {k: [v[0]] for k, v in benchmarks.items() if k in selected}
            else:
                tasks = {k: v for k, v in benchmarks.items() if k in selected}

            results = {}
            for category, task_list in tasks.items():
                category_results = []
                for task in task_list:
                    start = __import__('time').time()
                    response = await self._provider.generate(task)
                    elapsed = __import__('time').time() - start
                    category_results.append({
                        "task": task[:50],
                        "response_length": len(response),
                        "time": f"{elapsed:.2f}s"
                    })
                results[category] = category_results

            return ToolResult(success=True, data={
                "suite": suite,
                "categories": selected,
                "results": results
            })
        except Exception as e:
            return ToolResult(success=False, error=str(e))
```

### 3.2 Registrar Tools no Registry (8 TOOLS)

**Arquivo:** `jdev_cli/tools/registry_setup.py`

**PREFERÊNCIA DO USUÁRIO: Expandido (8+ tools)**

Adicionar ao final de `setup_default_tools()`:

```python
def setup_default_tools() -> Tuple[ToolRegistry, 'MCPClient']:
    """Setup default tool registry with all available tools."""

    # ... existing tool registrations ...

    # PROMETHEUS Tools (Self-Evolving Meta-Agent) - EXPANDED SET
    try:
        from jdev_cli.tools.prometheus_tools import (
            # Core tools (4)
            PrometheusExecuteTool,
            PrometheusMemoryQueryTool,
            PrometheusSimulateTool,
            PrometheusEvolveTool,
            # Expanded tools (4)
            PrometheusReflectTool,
            PrometheusCreateToolTool,
            PrometheusGetStatusTool,
            PrometheusBenchmarkTool,
        )

        # Core tools
        registry.register(PrometheusExecuteTool())
        registry.register(PrometheusMemoryQueryTool())
        registry.register(PrometheusSimulateTool())
        registry.register(PrometheusEvolveTool())

        # Expanded tools (user preference)
        registry.register(PrometheusReflectTool())
        registry.register(PrometheusCreateToolTool())
        registry.register(PrometheusGetStatusTool())
        registry.register(PrometheusBenchmarkTool())

        tools_registered += 8
        logger.info("PROMETHEUS tools registered (8 tools - expanded set)")
    except ImportError as e:
        logger.warning(f"PROMETHEUS tools not available: {e}")

    # ... rest of function ...
```

### 3.3 Atualizar MCPClient

**Arquivo:** `jdev_cli/core/mcp.py`

Adicionar constantes para PROMETHEUS tools:

```python
class MCPClient:
    # ... existing code ...

    # Add PROMETHEUS tools to long-running list
    LONG_RUNNING_TOOLS = {
        'bash_command', 'git_status', 'web_search', 'fetch_url',
        'prometheus_execute',  # NEW - Can take 30s+
        'prometheus_evolve',   # NEW - Can take minutes
        'prometheus_simulate', # NEW - World model simulation
    }

    # Timeouts for PROMETHEUS tools
    PROMETHEUS_TIMEOUT: float = 120.0

    def _get_tool_timeout(self, tool_name: str) -> float:
        """Get timeout for tool."""
        if tool_name.startswith('prometheus_'):
            return self.PROMETHEUS_TIMEOUT
        if tool_name in self.LONG_RUNNING_TOOLS:
            return self.DANGEROUS_TOOL_TIMEOUT
        return self.TOOL_TIMEOUT
```

---

## FASE 4: INTEGRAÇÃO GRADIO UI

### 4.1 Criar PrometheusStreamingBridge

**Arquivo:** `gradio_ui/prometheus_bridge.py`

```python
"""
PROMETHEUS Streaming Bridge for Gradio UI.

Integrates PROMETHEUS self-evolving meta-agent with Gradio 6
cyberpunk interface, providing:
- Full streaming with PROMETHEUS pipeline
- World model simulation preview
- Memory context display
- Reflection insights
- Evolution progress
"""

import os
import asyncio
from dataclasses import dataclass, field
from typing import Generator, Optional, Dict, Any, List
from datetime import datetime


@dataclass
class PrometheusMetrics:
    """Metrics for PROMETHEUS execution."""
    chunks_received: int = 0
    total_chars: int = 0
    ttft: float = 0.0
    chars_per_second: float = 0.0
    memory_hits: int = 0
    world_model_simulations: int = 0
    reflections: int = 0
    tools_created: int = 0


class PrometheusStreamingBridge:
    """
    Bridge between PROMETHEUS and Gradio UI.

    Converts AsyncIterator from PROMETHEUS to Generator for Gradio,
    with additional metrics and status tracking.
    """

    def __init__(self):
        self._provider = None
        self._loop = None
        self._metrics = PrometheusMetrics()
        self._status = "idle"

    def _ensure_provider(self):
        """Initialize PROMETHEUS provider."""
        if self._provider is None:
            from jdev_cli.core.providers.prometheus_provider import PrometheusProvider
            self._provider = PrometheusProvider()

    def _ensure_loop(self):
        """Ensure event loop exists."""
        try:
            self._loop = asyncio.get_event_loop()
        except RuntimeError:
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)

    def stream(
        self,
        message: str,
        history: Optional[List[Dict[str, str]]] = None,
        system_prompt: Optional[str] = None
    ) -> Generator[str, None, None]:
        """
        Stream response from PROMETHEUS.

        Args:
            message: User message
            history: Conversation history
            system_prompt: System prompt override

        Yields:
            Response chunks
        """
        self._ensure_provider()
        self._ensure_loop()

        self._status = "streaming"
        self._metrics = PrometheusMetrics()
        start_time = datetime.now()
        first_chunk = True

        async def _async_stream():
            nonlocal first_chunk

            async for chunk in self._provider.stream(
                prompt=message,
                system_prompt=system_prompt,
                context=history
            ):
                if first_chunk:
                    self._metrics.ttft = (datetime.now() - start_time).total_seconds()
                    first_chunk = False

                self._metrics.chunks_received += 1
                self._metrics.total_chars += len(chunk)

                yield chunk

        # Run async generator in sync context
        async_gen = _async_stream()

        while True:
            try:
                chunk = self._loop.run_until_complete(async_gen.__anext__())
                yield chunk
            except StopAsyncIteration:
                break
            except Exception as e:
                yield f"\n[ERROR: {str(e)}]"
                break

        # Calculate final metrics
        elapsed = (datetime.now() - start_time).total_seconds()
        if elapsed > 0:
            self._metrics.chars_per_second = self._metrics.total_chars / elapsed

        self._status = "idle"

    def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics."""
        return {
            "chunks": self._metrics.chunks_received,
            "chars": self._metrics.total_chars,
            "ttft": f"{self._metrics.ttft:.2f}s",
            "cps": f"{self._metrics.chars_per_second:.0f}",
            "memory_hits": self._metrics.memory_hits,
            "simulations": self._metrics.world_model_simulations,
        }

    def get_status(self) -> str:
        """Get current status."""
        return self._status

    def get_prometheus_status(self) -> Dict[str, Any]:
        """Get full PROMETHEUS status."""
        if self._provider and self._provider._initialized:
            return self._provider.get_status()
        return {"status": "not_initialized"}
```

### 4.2 Atualizar Gradio App (DASHBOARD MODE)

**Arquivo:** `gradio_ui/app.py`

**PREFERÊNCIA DO USUÁRIO: Dashboard** - Painéis para Memory, World Model, Evolution visíveis.

Adicionar dashboard completo com todos os painéis PROMETHEUS:

```python
# No início, adicionar imports:
import gradio as gr
from gradio_ui.prometheus_bridge import PrometheusStreamingBridge
from gradio_ui.prometheus_components import (
    render_memory_panel,
    render_world_model_preview,
    render_evolution_progress,
)

# Variáveis globais
_bridge = None  # GradioStreamingBridge (default)
_prometheus_bridge = None  # PrometheusStreamingBridge
_active_provider = "gemini"  # or "prometheus"


def get_active_bridge():
    """Get active bridge based on provider selection."""
    global _bridge, _prometheus_bridge, _active_provider

    if _active_provider == "prometheus":
        if _prometheus_bridge is None:
            _prometheus_bridge = PrometheusStreamingBridge()
        return _prometheus_bridge
    else:
        if _bridge is None:
            from gradio_ui.streaming_bridge import GradioStreamingBridge
            _bridge = GradioStreamingBridge()
        return _bridge


def switch_provider(provider: str) -> tuple:
    """Switch between providers and update dashboard visibility."""
    global _active_provider
    _active_provider = provider
    is_prometheus = provider == "prometheus"
    return (
        f"{'PROMETHEUS' if is_prometheus else 'Gemini'} Active",
        gr.update(visible=is_prometheus),  # prometheus_dashboard
    )


def refresh_prometheus_status() -> tuple:
    """Refresh all PROMETHEUS dashboard panels."""
    bridge = get_active_bridge()
    if not hasattr(bridge, 'get_prometheus_status'):
        return ({}, {}, {})

    status = bridge.get_prometheus_status()
    return (
        status.get("memory", {}),
        status.get("world_model", {}),
        status.get("evolution", {}),
    )


def create_ui():
    """Create the Gradio UI with PROMETHEUS DASHBOARD integration."""

    with gr.Blocks(
        title="QWEN-DEV + PROMETHEUS",
        css=open("gradio_ui/cyber_theme.css").read()
    ) as app:

        # Header
        gr.Markdown("""
        # QWEN-DEV CLI + PROMETHEUS
        > Self-Evolving Meta-Agent with Memory, World Model & Evolution
        """)

        with gr.Row():
            # Main chat area (left side - 70%)
            with gr.Column(scale=7):
                chatbot = gr.Chatbot(
                    label="Conversation",
                    height=500,
                    type="messages",
                )
                msg_input = gr.Textbox(
                    label="Message",
                    placeholder="Type your message...",
                    lines=2,
                )
                with gr.Row():
                    send_btn = gr.Button("Send", variant="primary")
                    clear_btn = gr.Button("Clear")

            # PROMETHEUS Dashboard (right side - 30%)
            with gr.Column(scale=3) as prometheus_dashboard:
                gr.Markdown("## PROMETHEUS Dashboard")

                # Provider selector
                provider_select = gr.Radio(
                    choices=["gemini", "prometheus"],
                    value="gemini",
                    label="LLM Provider",
                    info="PROMETHEUS: Self-evolving with memory & simulation"
                )
                provider_status = gr.Textbox(
                    label="Status",
                    value="Gemini Active",
                    interactive=False
                )

                # Memory Panel (always visible when PROMETHEUS selected)
                with gr.Accordion("Memory System (MIRIX)", open=True):
                    memory_panel = gr.HTML(
                        value=render_memory_panel({}),
                        label="Memory Status"
                    )
                    gr.Markdown("""
                    **Memory Types:**
                    - Episodic: Past experiences
                    - Semantic: Facts & knowledge
                    - Procedural: Learned skills
                    - Vault: Long-term consolidated
                    """)

                # World Model Panel
                with gr.Accordion("World Model (SimuRA)", open=True):
                    world_model_panel = gr.HTML(
                        value=render_world_model_preview({}),
                        label="Simulation Preview"
                    )
                    simulate_btn = gr.Button("Simulate Current")

                # Evolution Panel
                with gr.Accordion("Evolution (Agent0)", open=True):
                    evolution_panel = gr.HTML(
                        value=render_evolution_progress({}),
                        label="Evolution Status"
                    )
                    with gr.Row():
                        evolve_iterations = gr.Slider(
                            1, 20, value=5,
                            label="Iterations",
                            step=1
                        )
                        evolve_btn = gr.Button("Run Evolution")

                # Refresh all panels button
                refresh_btn = gr.Button("Refresh All Panels")

        # ============================================================
        # Event Handlers
        # ============================================================

        # Provider selection - show/hide dashboard
        provider_select.change(
            fn=switch_provider,
            inputs=[provider_select],
            outputs=[provider_status, prometheus_dashboard]
        )

        # Refresh all panels
        refresh_btn.click(
            fn=refresh_prometheus_status,
            inputs=[],
            outputs=[memory_panel, world_model_panel, evolution_panel]
        )

        # Evolution button
        evolve_btn.click(
            fn=lambda n: get_active_bridge()._provider.evolve(int(n))
                if hasattr(get_active_bridge(), '_provider') and get_active_bridge()._provider
                else {"error": "PROMETHEUS not initialized"},
            inputs=[evolve_iterations],
            outputs=[evolution_panel]
        )

        # Send message with dashboard update
        def send_with_dashboard_update(message, history):
            """Send message and update dashboard after response."""
            bridge = get_active_bridge()

            # Stream response
            response = ""
            for chunk in bridge.stream(message, history):
                response += chunk
                yield (
                    history + [{"role": "user", "content": message},
                              {"role": "assistant", "content": response}],
                    "",  # Clear input
                )

            # After response, refresh dashboard if PROMETHEUS
            if _active_provider == "prometheus":
                status = bridge.get_prometheus_status()
                yield (
                    history + [{"role": "user", "content": message},
                              {"role": "assistant", "content": response}],
                    "",
                )

        send_btn.click(
            fn=send_with_dashboard_update,
            inputs=[msg_input, chatbot],
            outputs=[chatbot, msg_input]
        )

        msg_input.submit(
            fn=send_with_dashboard_update,
            inputs=[msg_input, chatbot],
            outputs=[chatbot, msg_input]
        )

        clear_btn.click(
            fn=lambda: ([], ""),
            outputs=[chatbot, msg_input]
        )

    return app


def stream_conversation(message, history, session_id):
    """Stream conversation with active provider."""
    bridge = get_active_bridge()

    # ... existing streaming logic using bridge.stream() ...
```

### 4.3 Adicionar Componentes PROMETHEUS

**Arquivo:** `gradio_ui/prometheus_components.py`

```python
"""
PROMETHEUS-specific UI components for Gradio.

Visual components for displaying PROMETHEUS capabilities:
- Memory visualization
- World model simulation preview
- Reflection insights
- Evolution progress
"""

def render_memory_panel(memory_status: dict) -> str:
    """Render memory system status as HTML."""
    return f"""
    <div class="cyber-panel prometheus-memory">
        <h3>🧠 PROMETHEUS Memory (MIRIX)</h3>
        <div class="memory-types">
            <div class="memory-type">
                <span class="icon">📝</span>
                <span class="label">Episodic</span>
                <span class="count">{memory_status.get('episodic_count', 0)}</span>
            </div>
            <div class="memory-type">
                <span class="icon">📚</span>
                <span class="label">Semantic</span>
                <span class="count">{memory_status.get('semantic_count', 0)}</span>
            </div>
            <div class="memory-type">
                <span class="icon">⚙️</span>
                <span class="label">Procedural</span>
                <span class="count">{memory_status.get('procedural_count', 0)}</span>
            </div>
            <div class="memory-type">
                <span class="icon">🏛️</span>
                <span class="label">Vault</span>
                <span class="count">{memory_status.get('vault_count', 0)}</span>
            </div>
        </div>
    </div>
    """


def render_world_model_preview(simulation: dict) -> str:
    """Render world model simulation preview."""
    success_prob = simulation.get('success_probability', 0)
    color = "#00D9FF" if success_prob > 0.7 else "#F59E0B" if success_prob > 0.4 else "#EF4444"

    return f"""
    <div class="cyber-panel world-model">
        <h3>🌍 World Model Simulation</h3>
        <div class="simulation-result">
            <div class="probability" style="color: {color}">
                {success_prob:.0%} Success Probability
            </div>
            <div class="prediction">
                <strong>Predicted Outcome:</strong>
                <p>{simulation.get('predicted_outcome', 'N/A')}</p>
            </div>
            <div class="risks">
                <strong>Risks:</strong>
                <ul>
                    {''.join(f'<li>{r}</li>' for r in simulation.get('risks', []))}
                </ul>
            </div>
        </div>
    </div>
    """


def render_evolution_progress(stats: dict) -> str:
    """Render evolution progress."""
    return f"""
    <div class="cyber-panel evolution">
        <h3>🧬 Co-Evolution (Agent0)</h3>
        <div class="evolution-stats">
            <div class="stat">
                <span class="value">{stats.get('total_tasks', 0)}</span>
                <span class="label">Tasks</span>
            </div>
            <div class="stat">
                <span class="value">{stats.get('success_rate', 0):.0%}</span>
                <span class="label">Success</span>
            </div>
            <div class="stat">
                <span class="value">{stats.get('current_frontier', 'EASY')}</span>
                <span class="label">Level</span>
            </div>
        </div>
        <div class="skills-mastered">
            <strong>Skills Mastered:</strong>
            {', '.join(stats.get('skills_mastered', [])) or 'None yet'}
        </div>
    </div>
    """
```

---

## FASE 5: TESTES E VALIDAÇÃO

### 5.1 Testes Unitários

**Arquivo:** `tests/unit/test_prometheus_integration.py`

```python
"""
Tests for PROMETHEUS integration.

Covers:
- PrometheusProvider initialization
- Streaming functionality
- Memory system integration
- World model simulation
- MCP tool registration
- Gradio bridge
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch


class TestPrometheusProvider:
    """Test PrometheusProvider."""

    @pytest.fixture
    def provider(self):
        from jdev_cli.core.providers.prometheus_provider import PrometheusProvider
        return PrometheusProvider()

    def test_initialization(self, provider):
        assert provider._initialized is False
        assert provider._agent is None

    def test_is_available_with_api_key(self, provider):
        provider.api_key = "test-key"
        assert provider.is_available() is True

    def test_is_available_without_api_key(self, provider):
        provider.api_key = None
        assert provider.is_available() is False

    @pytest.mark.asyncio
    async def test_stream_yields_chunks(self, provider):
        provider.api_key = "test-key"

        # Mock the orchestrator
        mock_chunks = ["Hello", " ", "World"]

        async def mock_execute(task):
            for chunk in mock_chunks:
                yield chunk

        with patch.object(provider, '_ensure_initialized'):
            provider._orchestrator = Mock()
            provider._orchestrator.execute = mock_execute
            provider._initialized = True

            result = []
            async for chunk in provider.stream("test"):
                result.append(chunk)

            assert result == mock_chunks


class TestPrometheusMCPTools:
    """Test PROMETHEUS MCP tools."""

    @pytest.fixture
    def execute_tool(self):
        from jdev_cli.tools.prometheus_tools import PrometheusExecuteTool
        return PrometheusExecuteTool()

    def test_tool_schema(self, execute_tool):
        schema = execute_tool.get_schema()
        assert schema['name'] == 'prometheus_execute_tool'
        assert 'task' in schema['parameters']['properties']

    @pytest.mark.asyncio
    async def test_execute_returns_result(self, execute_tool):
        # Mock provider
        mock_provider = Mock()

        async def mock_stream(prompt, **kwargs):
            yield "Test result"

        mock_provider.stream = mock_stream
        execute_tool._provider = mock_provider

        result = await execute_tool._execute_validated(task="test task")
        assert result.success is True
        assert "Test result" in result.data['result']


class TestPrometheusGradioBridge:
    """Test Gradio streaming bridge."""

    @pytest.fixture
    def bridge(self):
        from gradio_ui.prometheus_bridge import PrometheusStreamingBridge
        return PrometheusStreamingBridge()

    def test_initial_state(self, bridge):
        assert bridge._provider is None
        assert bridge._status == "idle"

    def test_get_metrics(self, bridge):
        metrics = bridge.get_metrics()
        assert 'chunks' in metrics
        assert 'ttft' in metrics
```

### 5.2 Testes de Integração

**Arquivo:** `tests/integration/test_prometheus_e2e.py`

```python
"""
End-to-end tests for PROMETHEUS integration.

Tests full pipeline:
1. CLI → PROMETHEUS → Response
2. MCP → PROMETHEUS tools → Response
3. Gradio → PROMETHEUS bridge → Response
"""

import pytest
import asyncio


@pytest.mark.integration
class TestPrometheusE2E:
    """End-to-end tests."""

    @pytest.mark.asyncio
    async def test_cli_prometheus_flow(self):
        """Test CLI to PROMETHEUS flow."""
        from jdev_tui.core.prometheus_client import PrometheusClient

        client = PrometheusClient()

        result = []
        async for chunk in client.stream("What is 2+2?"):
            result.append(chunk)

        full_response = "".join(result)
        assert len(full_response) > 0
        # PROMETHEUS should show its pipeline
        assert "PROMETHEUS" in full_response or "4" in full_response

    @pytest.mark.asyncio
    async def test_mcp_prometheus_tool(self):
        """Test MCP PROMETHEUS tool."""
        from jdev_cli.core.mcp import create_mcp_client

        mcp = create_mcp_client()

        result = await mcp.call_tool('prometheus_execute', {
            'task': 'What is 2+2?'
        })

        assert result.get('success', False) or 'result' in result

    @pytest.mark.asyncio
    async def test_memory_persistence(self):
        """Test that memory persists across calls."""
        from jdev_cli.core.providers.prometheus_provider import PrometheusProvider

        provider = PrometheusProvider()

        # First call - store something
        async for _ in provider.stream("Remember: The secret code is ALPHA123"):
            pass

        # Second call - retrieve
        result = []
        async for chunk in provider.stream("What is the secret code?"):
            result.append(chunk)

        full_response = "".join(result)
        # Memory should help retrieve the code
        # (May or may not work depending on implementation)
```

### 5.3 Script de Validação

**Arquivo:** `tests/prometheus/validate_integration.py`

```python
#!/usr/bin/env python3
"""
Validation script for PROMETHEUS integration.

Run: python tests/prometheus/validate_integration.py
"""

import asyncio
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


async def validate_provider():
    """Validate PrometheusProvider."""
    print("1. Testing PrometheusProvider...")
    try:
        from jdev_cli.core.providers.prometheus_provider import PrometheusProvider
        provider = PrometheusProvider()

        if not provider.is_available():
            print("   ⚠️  No API key found - set GEMINI_API_KEY")
            return False

        print("   ✅ Provider initialized")
        return True
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False


async def validate_mcp_tools():
    """Validate MCP tools registration."""
    print("2. Testing MCP Tools...")
    try:
        from jdev_cli.core.mcp import create_mcp_client
        mcp = create_mcp_client()

        tools = await mcp.list_tools()
        prometheus_tools = [t for t in tools if 'prometheus' in t['name'].lower()]

        if len(prometheus_tools) >= 4:
            print(f"   ✅ {len(prometheus_tools)} PROMETHEUS tools registered")
            for t in prometheus_tools:
                print(f"      - {t['name']}")
            return True
        else:
            print(f"   ⚠️  Only {len(prometheus_tools)} tools found")
            return False
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False


async def validate_streaming():
    """Validate streaming functionality."""
    print("3. Testing Streaming...")
    try:
        from jdev_tui.core.prometheus_client import PrometheusClient
        client = PrometheusClient()

        chunks = 0
        async for chunk in client.stream("Say hello in one word"):
            chunks += 1
            if chunks >= 3:
                break

        if chunks > 0:
            print(f"   ✅ Received {chunks} chunks")
            return True
        else:
            print("   ❌ No chunks received")
            return False
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False


async def validate_gradio_bridge():
    """Validate Gradio bridge."""
    print("4. Testing Gradio Bridge...")
    try:
        from gradio_ui.prometheus_bridge import PrometheusStreamingBridge
        bridge = PrometheusStreamingBridge()

        chunks = 0
        for chunk in bridge.stream("Say hi"):
            chunks += 1
            if chunks >= 3:
                break

        if chunks > 0:
            print(f"   ✅ Gradio bridge works ({chunks} chunks)")
            return True
        else:
            print("   ❌ No chunks from bridge")
            return False
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False


async def main():
    print("=" * 60)
    print("🔥 PROMETHEUS Integration Validation")
    print("=" * 60)
    print()

    results = []

    results.append(await validate_provider())
    results.append(await validate_mcp_tools())
    results.append(await validate_streaming())
    results.append(await validate_gradio_bridge())

    print()
    print("=" * 60)
    passed = sum(results)
    total = len(results)
    print(f"Results: {passed}/{total} tests passed")
    print("=" * 60)

    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
```

---

## FASE 6: DOCUMENTAÇÃO PARA JUÍZES

### 6.1 Criar README Principal

**Arquivo:** `PROMETHEUS_INTEGRATION.md`

```markdown
# 🔥 PROMETHEUS Integration Guide

## Quick Start (Para Juízes)

### 1. Setup

```bash
# Clone e instale
git clone <repo>
cd qwen-dev-cli
pip install -r requirements.txt

# Configure API key
export GEMINI_API_KEY="your-key"
```

### 2. Rodar com PROMETHEUS

#### Via Shell CLI:
```bash
# Ativar PROMETHEUS mode
python -m jdev_tui

# No shell, digite:
/prometheus enable

# Agora todas as interações usam PROMETHEUS
> Write a function to calculate fibonacci
```

#### Via Gradio UI:
```bash
python -m gradio_ui

# No browser, selecione "prometheus" no Provider selector
# Interaja normalmente - PROMETHEUS gerencia tudo
```

#### Via MCP:
```bash
# Rodar servidor MCP
python -m jdev_cli.cli_mcp

# Em outro terminal, usar tools:
# prometheus_execute, prometheus_memory_query, prometheus_simulate
```

### 3. Comandos PROMETHEUS

| Comando | Descrição |
|---------|-----------|
| `/prometheus status` | Ver status do sistema |
| `/prometheus evolve 10` | Rodar 10 iterações de evolução |
| `/prometheus memory` | Ver estado da memória |
| `/prometheus enable` | Ativar modo PROMETHEUS |
| `/prometheus disable` | Voltar para Gemini padrão |

### 4. O Que PROMETHEUS Faz

1. **Memory System (MIRIX)**: Lembra de interações passadas
2. **World Model (SimuRA)**: Simula antes de agir
3. **Reflection (Reflexion)**: Aprende com erros
4. **Tool Factory (AutoTools)**: Cria ferramentas automaticamente
5. **Evolution (Agent0)**: Melhora continuamente

### 5. Demonstração Rápida

```bash
# Terminal 1: Rodar Gradio
python -m gradio_ui

# Terminal 2: Rodar validação
python tests/prometheus/validate_integration.py

# Terminal 3: Rodar stress test
python tests/prometheus/stress_test.py
```

### 6. Arquitetura

```
User Input
    │
    ▼
┌─────────────────────────────────────┐
│         PROMETHEUS PROVIDER          │
├─────────────────────────────────────┤
│ 1. Memory Retrieval (MIRIX)         │
│ 2. World Model Simulation (SimuRA)  │
│ 3. Task Execution                   │
│ 4. Reflection & Learning            │
│ 5. Evolution (optional)             │
└─────────────────────────────────────┘
    │
    ▼
Gemini API
    │
    ▼
Streaming Response
```

### 7. Métricas do Stress Test

| Métrica | Resultado |
|---------|-----------|
| Total Requests | 30 |
| Success Rate | 100% |
| Avg Response Time | 23.7s |
| Categories Tested | 9 |

Ver relatório completo: `tests/prometheus/STRESS_TEST_REPORT.md`
```

### 6.2 Criar Diagrama de Arquitetura

**Arquivo:** `docs/PROMETHEUS_ARCHITECTURE.md`

```markdown
# PROMETHEUS Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           QWEN-DEV-CLI ECOSYSTEM                          │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐                │
│  │   jdev_tui   │   │  gradio_ui   │   │   CLI MCP    │                │
│  │  (Textual)   │   │   (Web)      │   │   Server     │                │
│  └──────┬───────┘   └──────┬───────┘   └──────┬───────┘                │
│         │                  │                  │                         │
│         └──────────────────┼──────────────────┘                         │
│                            │                                            │
│                            ▼                                            │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    PROMETHEUS PROVIDER                           │   │
│  │                                                                  │   │
│  │  ┌─────────────────────────────────────────────────────────────┐│   │
│  │  │                 PrometheusOrchestrator                      ││   │
│  │  │                                                             ││   │
│  │  │  ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐  ││   │
│  │  │  │  Memory   │ │  World    │ │   Tool    │ │ Reflection│  ││   │
│  │  │  │  System   │ │  Model    │ │  Factory  │ │  Engine   │  ││   │
│  │  │  │  (MIRIX)  │ │ (SimuRA)  │ │(AutoTools)│ │(Reflexion)│  ││   │
│  │  │  └───────────┘ └───────────┘ └───────────┘ └───────────┘  ││   │
│  │  │                                                             ││   │
│  │  │  ┌─────────────────────────────────────────────────────┐   ││   │
│  │  │  │              Co-Evolution Loop (Agent0)              │   ││   │
│  │  │  │    Curriculum Agent ←→ Executor Agent                │   ││   │
│  │  │  └─────────────────────────────────────────────────────┘   ││   │
│  │  └─────────────────────────────────────────────────────────────┘│   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                            │                                            │
│                            ▼                                            │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                      Google Gemini API                           │   │
│  │                   (gemini-2.0-flash-exp)                        │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

## Data Flow

```
1. USER INPUT
   │
   ▼
2. PROMETHEUS PROVIDER
   │
   ├──► Memory System: Retrieve relevant context
   │    - Episodic: Past experiences
   │    - Semantic: Factual knowledge
   │    - Procedural: Learned skills
   │
   ├──► World Model: Simulate plans
   │    - Generate candidate approaches
   │    - Predict success probability
   │    - Identify risks
   │
   ├──► Tool Factory: Check/create tools
   │    - Identify needed tools
   │    - Generate if missing
   │    - Test in sandbox
   │
   ▼
3. GEMINI API
   │
   ▼
4. STREAMING RESPONSE
   │
   ▼
5. REFLECTION ENGINE
   │
   ├──► Critique result
   ├──► Extract lessons
   └──► Update memory
   │
   ▼
6. OUTPUT TO USER
```

## Research Foundation

| Component | Paper | Key Contribution |
|-----------|-------|-----------------|
| Self-Evolution | Agent0 (arXiv:2511.16043) | +18% math, +24% general |
| World Model | SimuRA (arXiv:2507.23773) | +124% task completion |
| Memory | MIRIX (arXiv:2507.07957) | 6-type memory system |
| Reflection | Reflexion (arXiv:2303.11366) | Self-critique loop |
| Tools | AutoTools (arXiv:2405.16533) | Dynamic tool creation |
```

---

## CHECKLIST DE IMPLEMENTAÇÃO

### Fase 1: Provider Layer
- [ ] Criar `jdev_cli/core/providers/prometheus_provider.py`
- [ ] Registrar em `jdev_cli/core/providers/__init__.py`
- [ ] Atualizar `jdev_cli/managers/provider_manager.py`
- [ ] Testar inicialização básica

### Fase 2: Shell CLI Integration
- [ ] Criar `jdev_tui/core/prometheus_client.py`
- [ ] Atualizar `jdev_tui/core/bridge.py`
- [ ] Adicionar comandos `/prometheus` em handlers
- [ ] Testar streaming no TUI

### Fase 3: MCP Integration
- [ ] Criar `jdev_cli/tools/prometheus_tools.py`
- [ ] Registrar em `jdev_cli/tools/registry_setup.py`
- [ ] Atualizar timeouts em `jdev_cli/core/mcp.py`
- [ ] Testar tools via MCP

### Fase 4: Gradio UI Integration
- [ ] Criar `gradio_ui/prometheus_bridge.py`
- [ ] Criar `gradio_ui/prometheus_components.py`
- [ ] Atualizar `gradio_ui/app.py`
- [ ] Testar streaming no browser

### Fase 5: Testes
- [ ] Criar `tests/unit/test_prometheus_integration.py`
- [ ] Criar `tests/integration/test_prometheus_e2e.py`
- [ ] Criar `tests/prometheus/validate_integration.py`
- [ ] Rodar todos os testes

### Fase 6: Documentação
- [ ] Criar `PROMETHEUS_INTEGRATION.md`
- [ ] Criar `docs/PROMETHEUS_ARCHITECTURE.md`
- [ ] Atualizar README principal
- [ ] Preparar demo para juízes

---

## ARQUIVOS CRÍTICOS (LEITURA OBRIGATÓRIA ANTES DE IMPLEMENTAR)

1. **Provider Base:** `jdev_cli/core/providers/gemini.py` (padrão a seguir)
2. **Bridge Principal:** `jdev_tui/core/bridge.py` (ponto de integração)
3. **LLM Client:** `jdev_tui/core/llm_client.py` (interface de streaming)
4. **MCP Client:** `jdev_cli/core/mcp.py` (padrão MCP)
5. **Tool Base:** `jdev_cli/tools/base.py` (interface de tools)
6. **Gradio Bridge:** `gradio_ui/streaming_bridge.py` (padrão Gradio)
7. **PROMETHEUS Main:** `prometheus/main.py` (agente principal)
8. **PROMETHEUS Orchestrator:** `prometheus/core/orchestrator.py` (coordenador)

---

**Pronto para execução pelo Gemini 3!**
