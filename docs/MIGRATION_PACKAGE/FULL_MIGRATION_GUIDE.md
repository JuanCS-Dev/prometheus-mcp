# 🚀 MEGA RELATÓRIO DE MIGRAÇÃO: Simplificação do CLI

## Objetivo: De 3 Sistemas → 1 Sistema (Estilo Gemini CLI)

**Data:** 2025-11-24
**Versão Atual:** qwen-dev-cli v10.0 (Maestro)
**Versão Alvo:** qwen-dev-cli v11.0 (Simplified)

---

## 📸 Conceito Visual: Estilo Gemini CLI

```
┌─────────────────────────────────────────────────────────────────────┐
│                                                                     │
│  ✦ Gemini CLI                                              v1.0.2  │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ > create a beautiful calculator in HTML                     │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ● Reading project structure...                                    │
│  ● Thinking about implementation...                                │
│                                                                     │
│  ┌─ 📄 Creating calculator.html ───────────────────────────────┐   │
│  │                                                              │   │
│  │  <!DOCTYPE html>                                            │   │
│  │  <html>                                                     │   │
│  │  <head>                                                     │   │
│  │      <title>Calculator</title>                              │   │
│  │      <style>                                                │   │
│  │          .calculator { ... }                                │   │
│  │      </style>                                                │   │
│  │  </head>                                                    │   │
│  │  ...                                                        │   │
│  │                                                              │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ✓ Created calculator.html (2.3 KB)                                │
│  ✓ Done in 3.2s                                                    │
│                                                                     │
│  ─────────────────────────────────────────────────────────────────  │
│  /help  /clear  /config                          Tokens: 1.2K ↓   │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### Características Visuais Chave:

1. **Header minimalista** - Logo + versão, sem painéis complexos
2. **Input limpo** - Prompt simples com `>`
3. **Stream sequencial** - Ações aparecem uma por vez com `●`
4. **Code blocks** - Syntax highlighting em painéis com título
5. **Status final** - Checkmarks `✓` para ações completadas
6. **Footer simples** - Comandos disponíveis + métricas básicas

---

## 🏗️ ARQUITETURA ATUAL (Complexa)

### Visão Geral

```
qwen-dev-cli/
├── 93.683 linhas de Python
├── 251 arquivos .py
├── 27 pacotes
├── 19 agents
├── 3 sistemas de roteamento (BUG!)
├── 5 implementações de shell
└── 5 implementações de REPL
```

### Estrutura de Diretórios

```
qwen_dev_cli/                          # 93K linhas total
│
├── __main__.py                        # Entry point 1
├── cli.py                             # Entry point 2 (742 linhas)
├── maestro.py                         # Entry point 3 (692 linhas)
├── shell_main.py                      # Entry point 4 (2528 linhas!) ⚠️
├── shell_fast.py                      # Entry point 5
├── ui.py                              # Entry point 6 (619 linhas)
│
├── agents/                            # 19 agents (12K+ linhas)
│   ├── base.py                        # BaseAgent protocol
│   ├── executor.py                    # Legacy executor (890 linhas)
│   ├── executor_nextgen.py            # Current executor (890 linhas)
│   ├── planner.py                     # PlannerAgent (1298 linhas)
│   ├── reviewer.py                    # ReviewerAgent (975 linhas)
│   ├── refactorer.py                  # RefactorerAgent (849 linhas)
│   ├── refactorer_v8.py               # Duplicate! (849 linhas)
│   ├── explorer.py                    # ExplorerAgent
│   ├── architect.py                   # ArchitectAgent
│   ├── security.py                    # SecurityAgent (702 linhas)
│   ├── testing.py                     # TestingAgent (1005 linhas)
│   ├── documentation.py               # DocumentationAgent (908 linhas)
│   ├── devops_agent.py                # DevOpsAgent (1197 linhas)
│   ├── data_agent_production.py       # DataAgent (662 linhas)
│   ├── performance_agent.py           # PerformanceAgent
│   ├── sofia_agent.py                 # SofiaAgent (945 linhas)
│   ├── justica_agent.py               # JusticaAgent (710 linhas)
│   └── legacy/                        # Legacy agents
│       └── refactor.py                # Old refactor (941 linhas)
│
├── cli/                               # 5 REPLs! (5K+ linhas)
│   ├── __init__.py
│   ├── repl_masterpiece.py            # REPL atual (1202 linhas)
│   ├── repl_enhanced.py               # REPL alternativo (1887 linhas!)
│   ├── repl_adapted.py                # REPL adaptado (677 linhas)
│   ├── repl_ultimate.py               # REPL ultimate (666 linhas)
│   ├── intent_detector.py             # Intent detection (183 linhas)
│   └── ...
│
├── tui/                               # TUI complexa (8K+ linhas)
│   ├── components/
│   │   ├── workflow_visualizer.py     # (921 linhas)
│   │   ├── preview.py                 # (822 linhas)
│   │   ├── context_awareness.py       # (769 linhas)
│   │   ├── palette.py                 # (621 linhas)
│   │   ├── dashboard.py               # (551 linhas)
│   │   ├── maestro_shell_ui.py        # (534 linhas)
│   │   ├── pills.py                   # (504 linhas)
│   │   ├── progress.py                # (503 linhas)
│   │   ├── enhanced_progress.py       # (432 linhas)
│   │   ├── toasts.py                  # (428 linhas)
│   │   ├── code.py                    # (410 linhas)
│   │   └── ... (20+ mais componentes)
│   └── ...
│
├── core/                              # Core infrastructure (15K+ linhas)
│   ├── llm.py                         # LLM client (741 linhas)
│   ├── workflow.py                    # Workflow engine (1215 linhas)
│   ├── recovery.py                    # Recovery system (920 linhas)
│   ├── session_manager.py             # Sessions (753 linhas)
│   ├── undo_manager.py                # Undo system (693 linhas)
│   ├── atomic_ops.py                  # Atomic operations (675 linhas)
│   ├── parser.py                      # Parser (667 linhas)
│   ├── resilience.py                  # Resilience (654 linhas)
│   ├── python_sandbox.py              # Python sandbox (653 linhas)
│   ├── conversation.py                # Conversation (653 linhas)
│   ├── sandbox.py                     # Bash sandbox (643 linhas)
│   ├── errors.py                      # Error handling (610 linhas)
│   ├── integration_coordinator.py     # Intent routing (500+ linhas)
│   └── ... (30+ mais módulos)
│
├── third_party/                       # Governance (5K+ linhas)
│   ├── justica/                       # Constitutional rules
│   │   ├── agent.py                   # (828 linhas)
│   │   ├── audit.py                   # (777 linhas)
│   │   ├── enforcement.py             # (723 linhas)
│   │   ├── monitor.py                 # (700 linhas)
│   │   ├── classifiers.py             # (694 linhas)
│   │   └── constitution.py            # (591 linhas)
│   └── sofia/                         # Philosophical wisdom
│       ├── deliberation.py            # (1113 linhas)
│       ├── agent.py                   # (711 linhas)
│       └── virtues.py                 # (607 linhas)
│
├── tools/                             # 17 tools (3K+ linhas)
│   ├── exec_hardened.py               # (608 linhas)
│   ├── registry.py
│   ├── file_ops.py
│   ├── bash_exec.py
│   └── ...
│
├── streaming/                         # Streaming engine
├── integration/                       # Integration layer
├── orchestration/                     # Task orchestration
├── intelligence/                      # LSP, analysis
├── session/                           # Session management
├── config/                            # Configuration
├── prompts/                           # System prompts
├── hooks/                             # Event hooks
└── plugins/                           # Plugin system
```

---

## 🔴 PROBLEMAS ATUAIS

### 1. Três Sistemas de Roteamento (Bug #5)

```
                    USER INPUT
                         │
         ┌───────────────┼───────────────┐
         ▼               ▼               ▼
    ┌─────────┐    ┌──────────┐    ┌──────────┐
    │maestro.py│   │repl_*.py │    │shell_main│
    │         │    │          │    │          │
    │ Typer   │    │ Commands │    │ System   │
    │ CLI     │    │ Dict     │    │ Commands │
    └────┬────┘    └────┬─────┘    └────┬─────┘
         │              │               │
         │              │               │
    FUNCIONA ✅    BYPASS GOV ⚠️   BUG ❌
```

### 2. Intent Detection com Falsos Positivos (Bug #6)

```python
# integration_coordinator.py:155-157
IntentType.TESTING: [
    "test",  # ← MUITO GENÉRICO! "test.html" dispara isso
]

# Resultado:
# "cria calculadora test.html" → TestingAgent ❌
# Deveria ir para → ExecutorAgent ✅
```

### 3. Duplicação Massiva

| Componente | Duplicatas | Linhas Desperdiçadas |
|------------|------------|----------------------|
| REPL | 5 versões | ~4.400 linhas |
| Shell | 5 versões | ~4.000 linhas |
| Executor | 3 versões | ~2.600 linhas |
| Refactorer | 3 versões | ~2.600 linhas |
| Context | 5 módulos | ~1.500 linhas |
| **TOTAL** | | **~15.000 linhas** |

### 4. TUI Over-Engineered

- 30+ componentes visuais
- Painéis que mostram nada útil
- 8.000+ linhas de UI code
- Atualização a 30 FPS para dados estáticos

---

## 🎯 ARQUITETURA ALVO (Simplificada)

### Modelo Gemini CLI

```
qwen_dev_cli_v11/                      # ~15K linhas (↓85%)
│
├── __main__.py                        # Único entry point
├── cli.py                             # CLI simples (~200 linhas)
│
├── agent.py                           # Agente único com tools (~500 linhas)
│   │
│   │  ┌──────────────────────────────────────────┐
│   │  │  class Agent:                            │
│   │  │      def __init__(self, llm, tools):     │
│   │  │          self.llm = llm                  │
│   │  │          self.tools = tools              │
│   │  │                                          │
│   │  │      async def run(self, prompt):        │
│   │  │          """Single loop - LLM decides""" │
│   │  │          while True:                     │
│   │  │              response = await llm.chat() │
│   │  │              if response.tool_call:      │
│   │  │                  yield execute_tool()    │
│   │  │              else:                       │
│   │  │                  yield response.text     │
│   │  │                  break                   │
│   │  └──────────────────────────────────────────┘
│   │
├── llm/                               # LLM client (~400 linhas)
│   ├── client.py                      # Multi-backend client
│   └── streaming.py                   # Token streaming
│
├── tools/                             # Tools (~1000 linhas)
│   ├── registry.py                    # Tool registry
│   ├── file_ops.py                    # Read/Write/Edit
│   ├── bash_exec.py                   # Shell execution
│   ├── search.py                      # Grep/Glob
│   └── web.py                         # Web fetch
│
├── ui/                                # UI simples (~800 linhas)
│   ├── console.py                     # Rich console wrapper
│   ├── streaming.py                   # Stream display
│   ├── code_block.py                  # Syntax highlighting
│   └── status.py                      # Status indicators
│
├── core/                              # Core (~500 linhas)
│   ├── config.py                      # Configuration
│   ├── context.py                     # Conversation context
│   └── sandbox.py                     # Security sandbox
│
└── prompts/                           # System prompts
    └── system.py                      # Single prompt file
```

### Fluxo Simplificado

```
┌─────────────────────────────────────────────────────────────────┐
│                         USER INPUT                              │
│                              │                                  │
│                              ▼                                  │
│                    ┌─────────────────┐                         │
│                    │   cli.py        │                         │
│                    │                 │                         │
│                    │ • Parse input   │                         │
│                    │ • Check /cmd    │                         │
│                    │ • Route to agent│                         │
│                    └────────┬────────┘                         │
│                              │                                  │
│                              ▼                                  │
│                    ┌─────────────────┐                         │
│                    │   agent.py      │                         │
│                    │                 │                         │
│                    │ • Send to LLM   │                         │
│                    │ • LLM decides   │                         │
│                    │   tool or text  │                         │
│                    └────────┬────────┘                         │
│                              │                                  │
│              ┌───────────────┼───────────────┐                 │
│              ▼               ▼               ▼                 │
│        ┌──────────┐   ┌──────────┐   ┌──────────┐             │
│        │ Tool A   │   │ Tool B   │   │ Tool C   │             │
│        │ file_ops │   │ bash     │   │ search   │             │
│        └────┬─────┘   └────┬─────┘   └────┬─────┘             │
│              │               │               │                  │
│              └───────────────┼───────────────┘                 │
│                              │                                  │
│                              ▼                                  │
│                    ┌─────────────────┐                         │
│                    │   ui/console    │                         │
│                    │                 │                         │
│                    │ • Stream output │                         │
│                    │ • Code blocks   │                         │
│                    │ • Status ✓      │                         │
│                    └─────────────────┘                         │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📦 ARQUIVOS A MANTER (Núcleo Funcional)

### ✅ MANTER - Core Essencial

```
qwen_dev_cli/
├── core/
│   ├── llm.py                    # ✅ LLM client (adaptar)
│   ├── sandbox.py                # ✅ Bash sandbox
│   ├── python_sandbox.py         # ✅ Python sandbox
│   └── config.py                 # ✅ Configuration
│
├── tools/
│   ├── registry.py               # ✅ Tool registry
│   ├── file_ops.py               # ✅ File operations
│   ├── bash_exec.py              # ✅ Bash execution
│   └── exec_hardened.py          # ✅ Hardened exec
│
├── streaming/
│   └── engine.py                 # ✅ Streaming (adaptar)
│
└── prompts/
    └── (criar novo system.py)    # ✅ System prompts
```

### ⚠️ ADAPTAR - Funcionalidades Úteis

```
qwen_dev_cli/
├── cli/
│   ├── intent_detector.py        # ⚠️ Simplificar para /commands
│   └── (partes do repl_masterpiece.py)
│       ├── Fuzzy completion      # ⚠️ Manter
│       ├── Slash commands        # ⚠️ Manter
│       └── History               # ⚠️ Manter
│
├── tui/
│   └── components/
│       ├── code.py               # ⚠️ Syntax highlighting
│       ├── autocomplete.py       # ⚠️ Autocomplete
│       └── streaming_display.py  # ⚠️ Stream display
│
└── agents/
    └── executor_nextgen.py       # ⚠️ Tool execution logic
```

### ❌ REMOVER - Complexidade Desnecessária

```
qwen_dev_cli/
├── maestro.py                    # ❌ Substituir por cli.py simples
├── shell_main.py                 # ❌ 2528 linhas → não necessário
├── shell_fast.py                 # ❌ Duplicata
├── ui.py                         # ❌ Old UI
│
├── cli/
│   ├── repl_enhanced.py          # ❌ 1887 linhas duplicadas
│   ├── repl_adapted.py           # ❌ Duplicata
│   └── repl_ultimate.py          # ❌ Duplicata
│
├── agents/
│   ├── executor.py               # ❌ Legacy
│   ├── refactorer_v8.py          # ❌ Duplicata
│   ├── planner.py                # ❌ LLM decide (não precisa agent)
│   ├── reviewer.py               # ❌ LLM decide
│   ├── architect.py              # ❌ LLM decide
│   ├── explorer.py               # ❌ LLM decide
│   ├── documentation.py          # ❌ LLM decide
│   ├── testing.py                # ❌ LLM decide
│   ├── security.py               # ❌ LLM decide
│   ├── performance_agent.py      # ❌ LLM decide
│   ├── devops_agent.py           # ❌ LLM decide
│   ├── data_agent_production.py  # ❌ LLM decide
│   ├── sofia_agent.py            # ❌ Over-engineering
│   ├── justica_agent.py          # ❌ Over-engineering
│   └── legacy/                   # ❌ Tudo
│
├── third_party/
│   ├── justica/                  # ❌ Governance over-engineering
│   └── sofia/                    # ❌ Philosophy over-engineering
│
├── tui/
│   └── components/
│       ├── workflow_visualizer.py # ❌ 921 linhas não usadas
│       ├── preview.py             # ❌ 822 linhas
│       ├── context_awareness.py   # ❌ 769 linhas
│       ├── dashboard.py           # ❌ 551 linhas
│       ├── maestro_shell_ui.py    # ❌ 534 linhas
│       ├── pills.py               # ❌ 504 linhas
│       ├── metrics_dashboard.py   # ❌ Over-engineering
│       └── ... (maioria)          # ❌
│
├── core/
│   ├── workflow.py               # ❌ 1215 linhas (over-engineering)
│   ├── recovery.py               # ❌ 920 linhas
│   ├── undo_manager.py           # ❌ 693 linhas
│   ├── integration_coordinator.py # ❌ Intent routing bugado
│   └── ... (vários)
│
├── orchestration/                # ❌ Tudo (LLM decide)
├── intelligence/                 # ❌ LSP not needed now
├── session/                      # ❌ Simplificar
├── hooks/                        # ❌ Not needed now
└── plugins/                      # ❌ Not needed now
```

---

## 🔧 PLANO DE MIGRAÇÃO

### Fase 1: Criar Nova Estrutura (1 dia)

```bash
# Criar diretório para nova versão
mkdir qwen_dev_cli_v11

# Estrutura inicial
qwen_dev_cli_v11/
├── __init__.py
├── __main__.py
├── cli.py
├── agent.py
├── llm/
├── tools/
├── ui/
├── core/
└── prompts/
```

### Fase 2: Portar Core (1-2 dias)

1. **LLM Client** - Extrair de `core/llm.py`
2. **Tools** - Copiar `tools/` com simplificações
3. **Sandbox** - Copiar `core/sandbox.py` e `python_sandbox.py`
4. **Streaming** - Simplificar de `streaming/engine.py`

### Fase 3: Criar Agent Único (1 dia)

```python
# agent.py (~500 linhas)
class Agent:
    """Single agent that uses LLM + Tools."""

    def __init__(self, llm_client, tools: list[Tool]):
        self.llm = llm_client
        self.tools = {t.name: t for t in tools}

    async def run(self, user_prompt: str) -> AsyncIterator[StreamEvent]:
        """Main loop - LLM decides everything."""
        messages = self._build_messages(user_prompt)

        while True:
            # Stream LLM response
            async for chunk in self.llm.stream(messages, tools=self.tools):
                if chunk.is_tool_call:
                    # Execute tool
                    yield StreamEvent("tool_start", chunk.tool_name)
                    result = await self._execute_tool(chunk)
                    yield StreamEvent("tool_result", result)
                    messages.append({"role": "tool", "content": result})
                else:
                    yield StreamEvent("text", chunk.text)

            # Check if done (no more tool calls)
            if not self._has_pending_tools(messages):
                break

        yield StreamEvent("done")
```

### Fase 4: UI Simplificada (1 dia)

```python
# ui/console.py
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.live import Live

class SimpleUI:
    """Gemini CLI style UI."""

    def __init__(self):
        self.console = Console()

    def show_thinking(self, text: str):
        """Show thinking indicator."""
        self.console.print(f"[dim]● {text}...[/dim]")

    def show_tool_start(self, tool: str, args: dict):
        """Show tool execution start."""
        self.console.print(f"[cyan]● Running {tool}...[/cyan]")

    def show_code_block(self, code: str, language: str, title: str = None):
        """Show code with syntax highlighting."""
        syntax = Syntax(code, language, theme="monokai")
        panel = Panel(syntax, title=title, border_style="dim")
        self.console.print(panel)

    def show_success(self, message: str):
        """Show success indicator."""
        self.console.print(f"[green]✓ {message}[/green]")

    def show_error(self, message: str):
        """Show error indicator."""
        self.console.print(f"[red]✗ {message}[/red]")
```

### Fase 5: CLI Principal (1 dia)

```python
# cli.py
import asyncio
from prompt_toolkit import PromptSession
from prompt_toolkit.completion import FuzzyWordCompleter

class CLI:
    """Simple CLI with fuzzy completion."""

    COMMANDS = {
        "/help": "Show help",
        "/clear": "Clear screen",
        "/config": "Show configuration",
        "/exit": "Exit CLI",
    }

    def __init__(self, agent: Agent, ui: SimpleUI):
        self.agent = agent
        self.ui = ui
        self.session = PromptSession(
            completer=FuzzyWordCompleter(list(self.COMMANDS.keys()))
        )

    async def run(self):
        """Main REPL loop."""
        self.ui.show_header()

        while True:
            try:
                user_input = await self.session.prompt_async("> ")

                if user_input.startswith("/"):
                    await self._handle_command(user_input)
                else:
                    await self._handle_prompt(user_input)

            except KeyboardInterrupt:
                continue
            except EOFError:
                break

    async def _handle_prompt(self, prompt: str):
        """Handle user prompt through agent."""
        async for event in self.agent.run(prompt):
            if event.type == "thinking":
                self.ui.show_thinking(event.data)
            elif event.type == "tool_start":
                self.ui.show_tool_start(event.tool, event.args)
            elif event.type == "code":
                self.ui.show_code_block(event.code, event.language)
            elif event.type == "text":
                self.ui.stream_text(event.data)
            elif event.type == "done":
                self.ui.show_success("Done")
```

---

## 📋 ARQUIVOS PARA O ZIP

### Arquivos Essenciais para Análise

```
INCLUIR NO ZIP:
├── docs/
│   └── MIGRATION_PACKAGE/
│       └── MEGA_MIGRATION_REPORT.md    # Este arquivo
│
├── CORE_FILES/                          # Arquivos a manter/adaptar
│   ├── core/
│   │   ├── llm.py
│   │   ├── sandbox.py
│   │   └── python_sandbox.py
│   ├── tools/
│   │   ├── registry.py
│   │   ├── file_ops.py
│   │   ├── bash_exec.py
│   │   └── exec_hardened.py
│   ├── streaming/
│   │   └── engine.py
│   └── cli/
│       ├── repl_masterpiece.py         # Para extrair fuzzy/completion
│       └── intent_detector.py
│
├── REFERENCE_FILES/                     # Para entender o que remover
│   ├── maestro.py
│   ├── shell_main.py
│   └── integration_coordinator.py
│
└── UI_COMPONENTS/                       # Componentes UI úteis
    └── tui/components/
        ├── code.py
        ├── autocomplete.py
        └── streaming_display.py
```

---

## 📊 MÉTRICAS DE SIMPLIFICAÇÃO

| Métrica | Atual | Alvo | Redução |
|---------|-------|------|---------|
| Linhas de código | 93.683 | ~15.000 | **84%** |
| Arquivos Python | 251 | ~30 | **88%** |
| Agents | 19 | 1 | **95%** |
| REPLs | 5 | 1 | **80%** |
| Shells | 5 | 1 | **80%** |
| Sistemas de roteamento | 3 | 1 | **67%** |
| Componentes TUI | 30+ | ~5 | **83%** |

---

## ✅ CHECKLIST DE MIGRAÇÃO

### Preparação
- [ ] Criar branch `feature/v11-simplified`
- [ ] Criar estrutura de diretórios v11
- [ ] Backup da versão atual

### Core
- [ ] Portar `core/llm.py` (simplificar)
- [ ] Portar `core/sandbox.py`
- [ ] Portar `core/python_sandbox.py`
- [ ] Criar `core/config.py` simplificado

### Tools
- [ ] Portar `tools/registry.py`
- [ ] Portar `tools/file_ops.py`
- [ ] Portar `tools/bash_exec.py`
- [ ] Simplificar `tools/exec_hardened.py`

### Agent
- [ ] Criar `agent.py` único
- [ ] Implementar tool calling loop
- [ ] Implementar streaming

### UI
- [ ] Criar `ui/console.py` (estilo Gemini)
- [ ] Criar `ui/streaming.py`
- [ ] Criar `ui/code_block.py`
- [ ] Portar fuzzy completion

### CLI
- [ ] Criar `cli.py` principal
- [ ] Implementar slash commands
- [ ] Implementar history
- [ ] Testar end-to-end

### Cleanup
- [ ] Remover arquivos não utilizados
- [ ] Atualizar imports
- [ ] Atualizar pyproject.toml
- [ ] Documentação

---

## 🎯 RESULTADO ESPERADO

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│  ✦ qwen-dev v11.0                                      Simple  │
│                                                                 │
│  > cria uma calculadora em html e salva em /home/juan/Videos   │
│                                                                 │
│  ● Thinking about the calculator design...                     │
│  ● Creating calculator.html...                                 │
│                                                                 │
│  ┌─ 📄 /home/juan/Videos/test.html ────────────────────────┐   │
│  │                                                          │   │
│  │  <!DOCTYPE html>                                        │   │
│  │  <html lang="pt-BR">                                    │   │
│  │  <head>                                                 │   │
│  │    <meta charset="UTF-8">                              │   │
│  │    <title>Calculadora</title>                          │   │
│  │    <style>                                              │   │
│  │      * { margin: 0; padding: 0; box-sizing: border-box }│   │
│  │      .calculator {                                      │   │
│  │        width: 320px;                                    │   │
│  │        background: linear-gradient(145deg, #1a1a2e...  │   │
│  │      ...                                                │   │
│  │                                                          │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ✓ Created /home/juan/Videos/test.html (3.2 KB)                │
│  ✓ Done in 2.8s                                                │
│                                                                 │
│  ─────────────────────────────────────────────────────────────  │
│  /help  /clear  /config  /model                  Tokens: 847   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📚 REFERÊNCIAS

- **Gemini CLI**: Referência visual do print fornecido
- **Claude Code**: Modelo de agente único com tools
- **Arquitetura atual**: `docs/ROUTING_ARCHITECTURE_REPORT.md`
- **Bugs conhecidos**: Bug #5 (routing), Bug #6 (intent detection)
# 🔀 Relatório de Arquitetura de Roteamento

## Bug #5: Conflito de Roteamento com /plan

**Status:** 🔴 CRÍTICO
**Score Atual:** Routing Logic 60%
**Impacto:** Comandos especiais (`/plan`, `/help`) não funcionam corretamente

---

## 📊 Visão Geral da Arquitetura

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           ENTRADA DO USUÁRIO                                │
│                                                                             │
│   ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────────┐    │
│   │ Terminal CLI    │  │ REPL Shell      │  │ Shell Main (Interativo)│    │
│   │ maestro agent X │  │ /comando msg    │  │ /comando msg            │    │
│   └────────┬────────┘  └────────┬────────┘  └───────────┬─────────────┘    │
└────────────┼────────────────────┼───────────────────────┼──────────────────┘
             │                    │                       │
             ▼                    ▼                       ▼
┌────────────────────┐  ┌────────────────────┐  ┌────────────────────────────┐
│    maestro.py      │  │ repl_masterpiece.py│  │     shell_main.py          │
│                    │  │                    │  │                            │
│ @agent_app.command │  │ self.commands[]    │  │ _handle_system_command()   │
│ "plan" → agent_plan│  │ "/plan" → handler  │  │ "/plan" → ❌ NÃO EXISTE    │
└─────────┬──────────┘  └─────────┬──────────┘  └────────────┬───────────────┘
          │                       │                          │
          │ ✅                    │ ⚠️                       │ ❌
          │                       │                          │
          ▼                       ▼                          ▼
┌────────────────────┐  ┌────────────────────┐  ┌────────────────────────────┐
│ execute_agent_task │  │ _invoke_agent()    │  │ COMANDO NÃO RECONHECIDO    │
│                    │  │                    │  │                            │
│ • AgentTask struct │  │ • LLM direto       │  │ • Erro ou fallthrough      │
│ • Governance ✅    │  │ • Sem governance ⚠️│  │ • Tenta como path ❌       │
│ • Agent.execute()  │  │ • stream_chat()    │  │                            │
└─────────┬──────────┘  └─────────┬──────────┘  └────────────────────────────┘
          │                       │
          ▼                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              AGENTS LAYER                                   │
│                                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │ PlannerAgent │  │ CoderAgent   │  │ExplorerAgent │  │ RefactorAgent│    │
│  │              │  │              │  │              │  │              │    │
│  │ base.py      │  │ coder.py     │  │ explorer.py  │  │ refactorer.py│    │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘    │
│                                                                             │
│                         executor_nextgen.py                                 │
│                    (ReAct Pattern + Streaming)                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 🗂️ Arquivos Envolvidos no Roteamento

### Camada 1: Entry Points

| Arquivo | Localização | Responsabilidade | Status |
|---------|-------------|------------------|--------|
| `maestro.py` | `qwen_dev_cli/maestro.py` | CLI Typer principal | ✅ Funciona |
| `cli.py` | `qwen_dev_cli/cli.py` | Entry point `qwen-dev` | ✅ Funciona |
| `repl_masterpiece.py` | `qwen_dev_cli/cli/repl_masterpiece.py` | Shell REPL interativo | ⚠️ Parcial |
| `shell_main.py` | `qwen_dev_cli/shell_main.py` | Shell principal | ❌ Bug |

### Camada 2: Roteamento de Comandos

| Arquivo | Linhas Críticas | O que faz |
|---------|-----------------|-----------|
| `maestro.py` | 347-369 | `@agent_app.async_command("plan")` |
| `repl_masterpiece.py` | 514-519 | Registro de `/plan` no dicionário |
| `repl_masterpiece.py` | 952-986 | `_process_command()` |
| `shell_main.py` | 972-1031 | `_handle_system_command()` |

### Camada 3: Execução de Agents

| Arquivo | Localização | Responsabilidade |
|---------|-------------|------------------|
| `base.py` | `qwen_dev_cli/agents/base.py` | Protocolo BaseAgent |
| `executor_nextgen.py` | `qwen_dev_cli/agents/executor_nextgen.py` | ReAct + Streaming |
| `planner.py` | `qwen_dev_cli/agents/planner.py` | PlannerAgent |

---

## 🔍 Análise Detalhada do Bug

### O Problema

Existem **TRÊS sistemas de roteamento separados** que não se comunicam:

```
┌─────────────────────────────────────────────────────────────────┐
│                    SISTEMA 1: MAESTRO.PY                        │
│                                                                 │
│  Comando: maestro agent plan "criar autenticação"               │
│                                                                 │
│  Flow:                                                          │
│  1. Typer parseia argumentos                                    │
│  2. @agent_app.async_command("plan") é invocado                │
│  3. agent_plan() chama execute_agent_task("planner", goal)     │
│  4. Cria AgentTask estruturado                                  │
│  5. Aplica Governance Pipeline                                  │
│  6. Chama PlannerAgent.execute(task)                           │
│  7. Retorna AgentResponse formatado                             │
│                                                                 │
│  ✅ FUNCIONA CORRETAMENTE                                       │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                 SISTEMA 2: REPL_MASTERPIECE.PY                  │
│                                                                 │
│  Comando: /plan criar autenticação                              │
│                                                                 │
│  Flow:                                                          │
│  1. _process_command() detecta /plan                           │
│  2. Busca handler em self.commands["/plan"]                    │
│  3. Executa: lambda msg: asyncio.run(_invoke_agent("planner")) │
│  4. _invoke_agent() chama LLM diretamente via stream_chat()    │
│  5. ⚠️ NÃO cria AgentTask                                       │
│  6. ⚠️ NÃO aplica Governance                                    │
│  7. Retorna resposta raw do LLM                                │
│                                                                 │
│  ⚠️ FUNCIONA MAS BYPASS GOVERNANCE                              │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                   SISTEMA 3: SHELL_MAIN.PY                      │
│                                                                 │
│  Comando: /plan criar autenticação                              │
│                                                                 │
│  Flow:                                                          │
│  1. _handle_system_command() recebe "/plan ..."                │
│  2. Verifica: if cmd == "/help"? NO                            │
│  3. Verifica: if cmd == "/exit"? NO                            │
│  4. Verifica: if cmd == "/tools"? NO                           │
│  5. ... (nenhum match)                                         │
│  6. ❌ COMANDO NÃO TRATADO                                      │
│  7. Fallthrough → erro ou tenta processar como path            │
│                                                                 │
│  ❌ BUG: HANDLER AUSENTE                                        │
└─────────────────────────────────────────────────────────────────┘
```

### Código do Bug

**Arquivo:** `qwen_dev_cli/shell_main.py`
**Linhas:** 972-1031

```python
async def _handle_system_command(self, cmd: str) -> tuple[bool, Optional[str]]:
    """Handle system commands (/help, /exit, etc.)."""
    cmd = cmd.strip()

    if cmd in ["/exit", "/quit"]:
        # ... handles exit
    elif cmd == "/help":
        # ... handles help
    elif cmd == "/tools":
        # ... handles tools listing
    elif cmd == "/context":
        # ... handles context
    # ... mais comandos do sistema ...

    # ❌ NÃO EXISTE CASE PARA /plan !
    # O comando cai no fallthrough e gera erro
```

---

## 📋 Arquivos que Precisam ser Modificados

### Prioridade 1: CRÍTICA (Fix do Bug)

#### 1. `qwen_dev_cli/shell_main.py`

**Problema:** Não tem handler para `/plan`

**Modificação Necessária:**
```python
# Adicionar em _handle_system_command() (após linha ~1020)

elif cmd.startswith("/plan"):
    # Extrair goal do comando
    goal = cmd[5:].strip()  # Remove "/plan "
    if not goal:
        self.console.print("[yellow]Usage: /plan <goal>[/yellow]")
        return False, None

    # Rotear para PlannerAgent via execute_agent_task
    from qwen_dev_cli.maestro import execute_agent_task
    result = await execute_agent_task("planner", goal, {})
    self._render_plan_result(result)
    return False, None
```

**Linhas a modificar:** ~1020-1031

---

#### 2. `qwen_dev_cli/cli/repl_masterpiece.py`

**Problema:** Handler usa LLM direto, bypassa governance

**Modificação Necessária:**
```python
# Modificar em self.commands (linhas 514-519)

"/plan": {
    "icon": "📋",
    "description": "Planner agent - strategic planning",
    "category": CommandCategory.AGENT,
    # ANTES: lambda msg: asyncio.run(self._invoke_agent("planner", msg))
    # DEPOIS: Usar execute_agent_task para consistência
    "handler": lambda msg: asyncio.run(self._execute_with_governance("planner", msg))
},

# Adicionar método _execute_with_governance (após linha ~880)
async def _execute_with_governance(self, agent_name: str, goal: str):
    """Execute agent with proper governance pipeline."""
    from qwen_dev_cli.maestro import execute_agent_task
    result = await execute_agent_task(agent_name, goal, {})
    self._display_agent_result(result)
```

**Linhas a modificar:** 514-519, adicionar método ~880

---

### Prioridade 2: ALTA (Unificação)

#### 3. `qwen_dev_cli/maestro.py`

**Problema:** Lógica de governance está acoplada ao CLI

**Modificação Recomendada:**
```python
# Extrair execute_agent_task para módulo separado
# para que possa ser reutilizado em shell_main.py e repl_masterpiece.py

# Criar: qwen_dev_cli/core/agent_router.py
```

**Linhas relevantes:** 191-282 (execute_agent_task)

---

#### 4. Criar novo arquivo: `qwen_dev_cli/core/command_router.py`

**Propósito:** Centralizar roteamento de comandos

```python
"""
Centralized Command Router
==========================

Single source of truth for all command routing.
"""

from typing import Dict, Callable, Optional
from dataclasses import dataclass
from enum import Enum

class CommandType(Enum):
    SYSTEM = "system"      # /help, /exit, /clear
    AGENT = "agent"        # /plan, /explore, /review
    TOOL = "tool"          # /bash, /file, /search
    META = "meta"          # /config, /status

@dataclass
class CommandSpec:
    name: str
    type: CommandType
    handler: Callable
    description: str
    usage: str
    requires_arg: bool = False

class CommandRouter:
    """Unified command router for all entry points."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init_commands()
        return cls._instance

    def _init_commands(self):
        self.commands: Dict[str, CommandSpec] = {}
        self._register_system_commands()
        self._register_agent_commands()

    def _register_system_commands(self):
        """Register system commands (/help, /exit, etc.)."""
        self.register(CommandSpec(
            name="/help",
            type=CommandType.SYSTEM,
            handler=self._handle_help,
            description="Show help",
            usage="/help [command]"
        ))
        # ... mais comandos

    def _register_agent_commands(self):
        """Register agent commands (/plan, /explore, etc.)."""
        self.register(CommandSpec(
            name="/plan",
            type=CommandType.AGENT,
            handler=self._handle_plan,
            description="Generate execution plan",
            usage="/plan <goal>",
            requires_arg=True
        ))
        # ... mais comandos

    def register(self, spec: CommandSpec):
        self.commands[spec.name] = spec

    async def route(self, input_text: str) -> Optional[str]:
        """Route command to appropriate handler."""
        if not input_text.startswith("/"):
            return None  # Not a command

        parts = input_text.split(maxsplit=1)
        cmd = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""

        if cmd not in self.commands:
            return f"Unknown command: {cmd}. Type /help for available commands."

        spec = self.commands[cmd]
        if spec.requires_arg and not args:
            return f"Usage: {spec.usage}"

        return await spec.handler(args)

    async def _handle_plan(self, goal: str) -> str:
        """Handle /plan command with governance."""
        from qwen_dev_cli.maestro import execute_agent_task
        result = await execute_agent_task("planner", goal, {})
        return self._format_result(result)
```

---

### Prioridade 3: MÉDIA (Limpeza)

#### 5. `qwen_dev_cli/agents/executor.py`

**Problema:** Executor legado causa confusão

**Recomendação:** Deprecar ou remover em favor de `executor_nextgen.py`

---

## 🎯 Plano de Correção

### Fase 1: Fix Imediato (Bug #5)

```bash
# Arquivos a modificar:
1. qwen_dev_cli/shell_main.py          # Adicionar /plan handler
2. qwen_dev_cli/cli/repl_masterpiece.py # Unificar com governance
```

### Fase 2: Refatoração (Unificação)

```bash
# Novos arquivos a criar:
1. qwen_dev_cli/core/command_router.py  # Router centralizado
2. qwen_dev_cli/core/agent_dispatcher.py # Dispatcher unificado

# Arquivos a refatorar:
3. qwen_dev_cli/maestro.py              # Extrair execute_agent_task
4. qwen_dev_cli/shell_main.py           # Usar CommandRouter
5. qwen_dev_cli/cli/repl_masterpiece.py # Usar CommandRouter
```

### Fase 3: Testes

```bash
# Testes a adicionar:
1. tests/unit/test_command_router.py
2. tests/integration/test_routing_consistency.py
3. tests/e2e/test_slash_commands.py
```

---

## 📐 Diagrama de Fluxo Corrigido (Proposta)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           ENTRADA DO USUÁRIO                                │
│                                                                             │
│   ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────────┐    │
│   │ Terminal CLI    │  │ REPL Shell      │  │ Shell Main              │    │
│   │ maestro agent X │  │ /plan msg       │  │ /plan msg               │    │
│   └────────┬────────┘  └────────┬────────┘  └───────────┬─────────────┘    │
└────────────┼────────────────────┼───────────────────────┼──────────────────┘
             │                    │                       │
             │                    ▼                       │
             │         ┌──────────────────────┐           │
             │         │   CommandRouter      │◄──────────┘
             │         │   (Centralizado)     │
             │         │                      │
             │         │ • Detecta /comando   │
             │         │ • Valida argumentos  │
             │         │ • Roteia p/ handler  │
             │         └──────────┬───────────┘
             │                    │
             ▼                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         AGENT DISPATCHER                                    │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                    execute_agent_task()                               │  │
│  │                                                                       │  │
│  │  1. Cria AgentTask estruturado                                       │  │
│  │  2. Aplica Governance Pipeline                                        │  │
│  │  3. Seleciona Agent correto                                          │  │
│  │  4. Chama Agent.execute(task)                                        │  │
│  │  5. Processa AgentResponse                                           │  │
│  │  6. Retorna resultado formatado                                      │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              AGENTS LAYER                                   │
│                                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │ PlannerAgent │  │ CoderAgent   │  │ExplorerAgent │  │ RefactorAgent│    │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘    │
│                                                                             │
│                         executor_nextgen.py                                 │
│                    (ReAct Pattern + Streaming)                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

---

## 🐛 Bug #6: Falso Positivo no Intent Detection

**Status:** 🔴 CRÍTICO
**Descoberto:** Durante teste de "cria uma calculadora... test.html"

### O Problema

A mensagem:
```
cria uma calculadora em html e salva na pasta /home/juan/Videos com o nome test.html
```

Foi roteada para **TestingAgent** em vez de **Executor/Coder** porque:

1. A palavra `"test"` no nome do arquivo `test.html`
2. É um keyword para `IntentType.TESTING` (linha 156 de `integration_coordinator.py`)
3. O sistema não diferencia "test" como **intenção** vs "test" como **dado** (nome de arquivo)

### Fluxo do Bug

```
User: "cria uma calculadora... test.html"
         │
         ▼
┌────────────────────────────────────┐
│   integration_coordinator.py       │
│   detect_intent()                  │
│                                    │
│   message_lower.contains("test")   │
│   → TRUE (nome do arquivo)         │
│                                    │
│   IntentType.TESTING matches!      │
│   confidence = 0.5 (1 keyword)     │
└────────────────────────────────────┘
         │
         ▼ (confidence 0.5 >= 0.3)
┌────────────────────────────────────┐
│   Route to TestingAgent            │
│                                    │
│   TestingAgent.execute() expects:  │
│   - source_code OR                 │
│   - file_path                      │
│                                    │
│   Neither provided → ERROR         │
└────────────────────────────────────┘
         │
         ▼
❌ "source_code or file_path required in task context"
```

### Arquivos Afetados

| Arquivo | Problema |
|---------|----------|
| `qwen_dev_cli/core/integration_coordinator.py:155-157` | Keywords muito genéricos |
| `qwen_dev_cli/cli/intent_detector.py:56-66` | Mesmo problema |
| `qwen_dev_cli/agents/testing.py:296-302` | Erro não informativo |

### Código Problemático

**integration_coordinator.py:155-157**
```python
IntentType.TESTING: [
    "test", "coverage", "unit", "integration", "e2e"  # ← "test" muito genérico!
],
```

**intent_detector.py:56-66**
```python
"test": {
    "keywords": [
        "test", "teste", "testes", "testing",  # ← Mesmos problemas
        "unit test", "integration test", "e2e",
        "coverage", "cobertura", "pytest", "jest"
    ],
    ...
}
```

### Solução Proposta

#### 1. Keywords mais específicos (não match parcial)

```python
IntentType.TESTING: [
    # Remover "test" sozinho - muito genérico
    "create test", "write test", "add test",
    "unit test", "integration test", "e2e test",
    "test coverage", "pytest", "jest",
    "criar teste", "escrever teste", "testar código"
],
```

#### 2. Negative matching (excluir falsos positivos)

```python
def detect_intent(self, message: str) -> Intent:
    message_lower = message.lower()

    # NOVO: Excluir matches em nomes de arquivos
    # Remove .html, .py, .js etc do matching
    clean_message = re.sub(r'\b\w+\.(html|py|js|ts|css|json)\b', '', message_lower)

    # Agora match em clean_message em vez de message_lower
    for intent_type, keywords in self._intent_keywords.items():
        matches = sum(1 for kw in keywords if kw in clean_message)
        ...
```

#### 3. Contexto semântico

```python
# Verificar se "test" aparece em contexto de testing vs como dado
def _is_testing_context(self, message: str) -> bool:
    testing_verbs = ["criar teste", "escrever teste", "testar", "add test"]
    return any(verb in message.lower() for verb in testing_verbs)
```

#### 4. Fallback para Executor

Se nenhum agent específico for detectado com alta confiança, a mensagem deveria ir para o **ExecutorAgent** (que pode criar arquivos, código, etc):

```python
# Em process_message()
if intent.type == IntentType.GENERAL or intent.confidence < 0.5:
    # Fallback to executor for general tasks
    return await self._executor_agent.execute(message)
```

### Arquivos a Modificar

1. **`qwen_dev_cli/core/integration_coordinator.py`**
   - Linhas 155-157: Keywords mais específicos
   - Linhas 357-389: Adicionar negative matching
   - Linhas 425-453: Fallback para executor

2. **`qwen_dev_cli/cli/intent_detector.py`**
   - Linhas 56-66: Keywords mais específicos
   - Método `detect()`: Adicionar limpeza de nomes de arquivos

3. **`qwen_dev_cli/agents/testing.py`**
   - Linhas 296-302: Mensagem de erro mais útil
   - Sugerir agent correto quando contexto inválido

---

## ✅ Checklist de Correção

### Bug #5: /plan routing
- [ ] Adicionar handler `/plan` em `shell_main.py`
- [ ] Modificar handler `/plan` em `repl_masterpiece.py` para usar governance
- [ ] Criar `CommandRouter` centralizado
- [ ] Extrair `execute_agent_task` para módulo reutilizável

### Bug #6: False positive intent detection
- [ ] Refatorar keywords em `integration_coordinator.py` (remover "test" sozinho)
- [ ] Refatorar keywords em `intent_detector.py` (remover "test" sozinho)
- [ ] Adicionar negative matching para nomes de arquivos
- [ ] Implementar fallback para Executor quando intent incerto
- [ ] Melhorar mensagem de erro em `testing.py`

### Geral
- [ ] Adicionar testes de integração para roteamento
- [ ] Documentar fluxo de roteamento para desenvolvedores
- [ ] Deprecar `executor.py` legado

---

## 📚 Referências

- `qwen_dev_cli/maestro.py:191-282` - execute_agent_task atual
- `qwen_dev_cli/maestro.py:347-369` - agent_plan CLI handler
- `qwen_dev_cli/cli/repl_masterpiece.py:514-539` - command registry
- `qwen_dev_cli/cli/repl_masterpiece.py:952-986` - _process_command
- `qwen_dev_cli/shell_main.py:972-1031` - _handle_system_command
- `qwen_dev_cli/agents/base.py:220-224` - BaseAgent.execute protocol
