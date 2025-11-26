# JUANCS-DEV: Plano Mestre de Paridade com Claude Code

**Data**: 2025-11-25
**Versão**: 1.2 (ATUALIZADO APÓS WAVE 2)
**Status**: ✅ WAVE 1+2 COMPLETAS - 70% PARIDADE
**Autor**: Arquiteto-Chefe + Claude Opus 4.5

---

## 🎉 PROGRESSO - WAVE 2 COMPLETA

### Status Atual (Pós-Wave 2)

| Métrica | Wave 0 | Wave 1 | Wave 2 | Melhoria Total |
|---------|--------|--------|--------|----------------|
| **Tools Funcionais** | 31 | 38 | 38 | +7 ✅ |
| **Slash Commands** | 24 | 43 | 52 | +28 ✅ |
| **@ File Picker** | ❌ | ✅ | ✅ | Integrado |
| **Agents Ativos** | 14 | 14 | 14 | Conectados ✅ |
| **Agent Router** | ❌ | ❌ | ✅ | **NOVO** |
| **Session Persistence** | ❌ | ❌ | ✅ | **NOVO** |
| **Checkpoint System** | ❌ | ❌ | ✅ | **NOVO** |
| **Paridade Claude Code** | 32% | 55% | ~70% | +38% 🚀 |

### Implementações Wave 2

**AgentRouter (NEW - Claude Code Parity):**
- ✅ 14 agents com routing automático por intent
- ✅ 59 patterns (PT-BR + EN) para detecção
- ✅ Confidence scoring (70%+ para auto-route)
- ✅ Sugestões quando há ambiguidade
- ✅ `/router` - Toggle on/off
- ✅ `/router-status` - Show config
- ✅ `/route` - Test routing

**Session Persistence (NEW):**
- ✅ `/save [id]` - Salvar sessão
- ✅ `/resume [id]` - Restaurar sessão
- ✅ `/sessions` - Listar sessões
- ✅ Armazenamento em `~/.juancs/sessions/`

**Checkpoint System (NEW - Claude Code /rewind):**
- ✅ `/checkpoint [label]` - Criar checkpoint
- ✅ `/rewind [idx]` - Voltar ao checkpoint
- ✅ Memória em RAM + persistência opcional

**Auto-Routing Examples:**
```
"Cria um plano de testes" → PlannerAgent (90%)
"Roda pytest" → ExecutorAgent (90%)
"Analisa a arquitetura" → ArchitectAgent (90%)
"Security scan" → SecurityAgent (95%)
"Otimiza essa query" → PerformanceAgent (90%)
```

---

## 🎉 PROGRESSO - WAVE 1 COMPLETA

### Status Atual (Pós-Wave 1)

| Métrica | Antes | Depois | Melhoria |
|---------|-------|--------|----------|
| **Tools Funcionais** | 31 | 38 | +7 ✅ |
| **Slash Commands** | 24 | 43 | +19 ✅ |
| **@ File Picker** | ❌ | ✅ | Integrado |
| **Agents Ativos** | 14 | 14 | Mantido |

### Implementações Wave 1

**Novos Tools (7):**
- ✅ GlobTool - Pattern matching (9550 arquivos testado)
- ✅ LSTool - Directory listing
- ✅ MultiEditTool - Edições atômicas
- ✅ WebFetchTool - URL fetching
- ✅ WebSearchTool - Web search DuckDuckGo
- ✅ TodoReadTool - Leitura de todos
- ✅ TodoWriteTool - Gerenciamento de todos

**Novos Comandos (19):**
- ✅ /compact, /cost, /tokens - Context management
- ✅ /todos, /todo - Task management
- ✅ /model - Model selection
- ✅ /init - Project initialization
- ✅ /resume, /rewind - Session management
- ✅ /export - Conversation export
- ✅ /doctor - Health check
- ✅ /permissions - Permission management
- ✅ /sandbox - Sandbox toggle
- ✅ /hooks - Hook management
- ✅ /mcp - MCP status

---

## SUMÁRIO EXECUTIVO

Este documento consolida a análise profunda do projeto `qwen-dev-cli` e estabelece o plano definitivo para atingir **100% de paridade funcional com Claude Code** (Anthropic), incorporando best practices do Gemini CLI (Google) e Codex CLI (OpenAI).

### Diagnóstico Inicial (Pré-Wave 1)

| Métrica | Antes | Atual | Alvo | Gap |
|---------|-------|-------|------|-----|
| **Paridade Claude Code** | 32% | ~55% | 100% | -45% |
| **Componentes Integrados** | 35% | ~50% | 100% | -50% |
| **Tools Funcionais** | 31 | 38 | 50+ | -12 |
| **Slash Commands** | 24 | 43 | 43 | ✅ |
| **Agents Ativos** | 14 | 14 | 14 | ✅ |

### Problema Central

> **"Construímos uma Ferrari com pintura, bancos, AC, rádio... mas está na garagem e ninguém tem a chave."**

O projeto possui **~51.000 linhas de código**, mas apenas **~18.000 (35%)** estão efetivamente integradas e funcionais. Os componentes existem, foram testados, mas **não estão conectados ao shell principal**.

---

## PARTE 1: AUDITORIA DE COMPONENTES NÃO INTEGRADOS

### 1.1 Componentes TUI (28 arquivos, ~67% não integrados)

| Componente | Arquivo | Status | Impacto |
|------------|---------|--------|---------|
| **FilePickerCompleter** | `tui/components/file_picker.py` | ❌ NÃO INTEGRADO | @ mentions quebrado |
| **SlashCommandCompleter** | `tui/components/slash_completer.py` | ❌ NÃO INTEGRADO | Autocomplete / quebrado |
| **CommandPaletteBar** | `tui/components/command_palette_bar.py` | ❌ NÃO INTEGRADO | Ctrl+K não funciona |
| **MaestroShellUI** | `tui/components/maestro_shell_ui.py` | ❌ NÃO INTEGRADO | Shell completo órfão |
| **AgentStreamPanel** | `tui/components/agent_stream_panel.py` | ❌ NÃO INTEGRADO | Streaming de agents |
| **FileOperationsPanel** | `tui/components/file_operations_panel.py` | ❌ NÃO INTEGRADO | Status de operações |
| **MetricsDashboard** | `tui/components/metrics_dashboard.py` | ❌ NÃO INTEGRADO | Dashboard offline |
| **ContextAwarenessEngine** | `tui/components/context_awareness.py` | ❌ NÃO INTEGRADO | Token tracking offline |
| **AgentRoutingDisplay** | `tui/components/agent_routing.py` | ❌ NÃO INTEGRADO | Seleção de agent |
| **StreamingDisplay** | `tui/components/streaming_display.py` | ❌ NÃO INTEGRADO | Output streaming |
| **EnhancedMarkdown** | `tui/components/markdown_enhanced.py` | ❌ NÃO INTEGRADO | Markdown rendering |
| **EditPreview** | `tui/components/preview.py` | ⚠️ PARCIAL | Preview de edições |
| **FileTree** | `tui/components/file_tree.py` | ⚠️ PARCIAL | Árvore de arquivos |
| **ContextPill** | `tui/components/pills.py` | ❌ NÃO INTEGRADO | Pills de contexto |
| **Toast** | `tui/components/toasts.py` | ❌ NÃO INTEGRADO | Notificações |
| **Autocomplete** | `tui/components/autocomplete.py` | ❌ NÃO INTEGRADO | Autocomplete contextual |
| **Animations** | `tui/animations.py` | ❌ NÃO INTEGRADO | Código morto |

### 1.2 Agents (13 agents, 0% integrados no shell principal)

| Agent | Arquivo | LOC | Status no Shell |
|-------|---------|-----|-----------------|
| **ArchitectAgent** | `agents/architect.py` | ~800 | ❌ Só em cli.py |
| **ExplorerAgent** | `agents/explorer.py` | ~600 | ❌ Só em cli.py |
| **PlannerAgent** | `agents/planner.py` | 1298 | ❌ Só em cli.py |
| **ExecutorAgent** | `agents/executor.py` | ~900 | ❌ Não ativo |
| **RefactorerAgent** | `agents/refactorer.py` | ~700 | ❌ 0 testes |
| **ReviewerAgent** | `agents/reviewer.py` | 975 | ❌ Só em cli.py |
| **SecurityAgent** | `agents/security.py` | ~800 | ❌ Isolado |
| **PerformanceAgent** | `agents/performance.py` | ~600 | ❌ Isolado |
| **TestingAgent** | `agents/testing.py` | 1005 | ❌ Só em cli.py |
| **DocumentationAgent** | `agents/documentation.py` | 908 | ❌ Só em cli.py |
| **DevOpsAgent** | `agents/devops_agent.py` | 1197 | ❌ Só em cli.py |
| **DataAgent** | `agents/data_agent.py` | ~700 | ❌ Só em cli.py |
| **JusticaAgent** | `agents/justica_agent.py` | ~800 | ❌ Governança off |
| **SofiaAgent** | `agents/sofia_agent.py` | ~900 | ❌ Counsel off |

### 1.3 Tools (47+ tools, ~30% integrados)

| Categoria | Tools | Status |
|-----------|-------|--------|
| **File Ops** | read, write, edit, delete | ✅ Parcial |
| **File Mgmt** | move, copy, mkdir | ❌ Não integrado |
| **Search** | search_files, directory_tree | ❌ Não integrado |
| **Git** | git_status, git_diff | ❌ Não integrado |
| **Terminal** | cd, ls, pwd, bash | ⚠️ Parcial |
| **Web** | web_search, fetch_url | ❌ Não integrado |
| **Context** | get_context, save_session | ❌ Não integrado |

### 1.4 Sistemas Órfãos

| Sistema | Arquivo | Status |
|---------|---------|--------|
| **Plugin System** | `plugins/` | ❌ Nunca inicializado |
| **LSP Client** | `intelligence/lsp_client.py` | ❌ 741 LOC mortas |
| **Semantic Indexer** | `intelligence/indexer.py` | ❌ Não usado |
| **Error Recovery** | `core/recovery.py` | ⚠️ 920 LOC, parcial |
| **Token Tracker** | `core/token_tracker.py` | ❌ Não usado |
| **Governance** | `maestro_governance.py` | ❌ Não conectado |
| **Permissions** | `permissions.py` | ❌ Não conectado |

---

## PARTE 2: ANÁLISE COMPETITIVA (Nov 2025)

### 2.1 Claude Code (Anthropic) - BENCHMARK PRINCIPAL

**Fonte**: [Claude Code Docs](https://code.claude.com/docs/en/overview)

#### Tools Nativos (16 ferramentas)
| Tool | Descrição | JuanCS Status |
|------|-----------|---------------|
| **Read** | Lê arquivos (suporta imagens, 2000 linhas) | ✅ Existe |
| **Write** | Cria/sobrescreve arquivos | ✅ Existe |
| **Edit** | Find-and-replace em arquivos | ✅ Existe |
| **MultiEdit** | Múltiplas edições atômicas | ❌ FALTANDO |
| **Bash** | Executa comandos shell | ✅ Existe |
| **Glob** | Pattern matching de arquivos | ❌ FALTANDO |
| **Grep** | Busca regex em conteúdo | ✅ Existe |
| **LS** | Lista diretórios | ❌ FALTANDO (usa bash) |
| **Task/Agent** | Lança sub-agents | ⚠️ Existe mas off |
| **WebFetch** | Busca URLs com AI | ❌ FALTANDO |
| **WebSearch** | Busca na web | ❌ FALTANDO |
| **TodoRead** | Lê lista de tarefas | ❌ FALTANDO |
| **TodoWrite** | Gerencia tarefas | ❌ FALTANDO |
| **NotebookRead** | Lê Jupyter notebooks | ❌ FALTANDO |
| **NotebookEdit** | Edita células de notebooks | ❌ FALTANDO |
| **exit_plan_mode** | Sai do modo planejamento | ❌ FALTANDO |

#### Slash Commands (37 comandos)
| Comando | Descrição | JuanCS |
|---------|-----------|--------|
| `/add-dir` | Adiciona diretórios de trabalho | ❌ |
| `/agents` | Gerencia sub-agents | ❌ |
| `/bashes` | Lista tasks em background | ❌ |
| `/bug` | Reporta bugs | ❌ |
| `/clear` | Limpa histórico | ✅ |
| `/compact` | Compacta contexto | ❌ |
| `/config` | Abre configurações | ❌ |
| `/context` | Visualiza uso de contexto | ❌ |
| `/cost` | Mostra uso de tokens | ❌ |
| `/doctor` | Verifica saúde da instalação | ❌ |
| `/exit` | Sai do REPL | ✅ |
| `/export` | Exporta conversa | ❌ |
| `/help` | Mostra ajuda | ✅ |
| `/hooks` | Gerencia hooks | ❌ |
| `/ide` | Gerencia integrações IDE | ❌ |
| `/init` | Inicializa projeto | ❌ |
| `/install-github-app` | Instala GitHub app | ❌ |
| `/login` | Troca conta | ❌ |
| `/logout` | Faz logout | ❌ |
| `/mcp` | Gerencia conexões MCP | ❌ |
| `/memory` | Edita CLAUDE.md | ❌ |
| `/model` | Seleciona modelo | ✅ |
| `/output-style` | Define estilo de output | ❌ |
| `/permissions` | Gerencia permissões | ⚠️ Parcial |
| `/plugin` | Gerencia plugins | ❌ |
| `/pr-comments` | Vê comentários de PR | ❌ |
| `/privacy-settings` | Configurações de privacidade | ❌ |
| `/release-notes` | Notas de versão | ❌ |
| `/resume` | Retoma conversa | ❌ |
| `/review` | Solicita code review | ❌ |
| `/rewind` | Volta no histórico | ❌ |
| `/sandbox` | Ativa sandbox | ❌ |
| `/security-review` | Review de segurança | ❌ |
| `/status` | Mostra status | ✅ |
| `/statusline` | Configura statusline | ❌ |
| `/terminal-setup` | Configura terminal | ❌ |
| `/todos` | Lista tarefas | ❌ |
| `/usage` | Mostra limites | ❌ |
| `/vim` | Modo vim | ❌ |

#### Features Avançadas
| Feature | Status JuanCS |
|---------|---------------|
| **Subagents** (tarefas paralelas) | ⚠️ Existe mas off |
| **Hooks** (ações automáticas) | ❌ Não implementado |
| **Background Tasks** | ❌ Não implementado |
| **Checkpoints** (rewind) | ❌ Não implementado |
| **MCP Client/Server** | ⚠️ Parcial |
| **@ File Mentions** | ⚠️ Existe mas off |
| **Custom Slash Commands** | ❌ Não implementado |
| **Session Resume** | ❌ Não implementado |

### 2.2 Gemini CLI (Google) - Nov 2025

**Fonte**: [Gemini CLI Docs](https://developers.google.com/gemini-code-assist/docs/gemini-cli)

| Feature | Descrição |
|---------|-----------|
| **ReAct Loop** | Reason and Act com tools |
| **Google Search Grounding** | Busca em tempo real |
| **MCP Support** | Integrações custom |
| **Agent Mode** | VS Code integration |
| **1M Token Context** | Janela gigante |
| **Multimodal** | Imagens, PDFs, sketches |
| **Checkpointing** | Save/resume sessões |
| **GEMINI.md** | Arquivo de contexto projeto |

### 2.3 Codex CLI (OpenAI) - Nov 2025

**Fonte**: [Codex CLI Docs](https://developers.openai.com/codex/cli/)

| Feature | Descrição |
|---------|-----------|
| **Full-screen TUI** | Interface terminal rica |
| **GPT-5-Codex** | Modelo otimizado para código |
| **Image Support** | Screenshots, wireframes |
| **Cloud Tasks** | `codex cloud` |
| **Session Resume** | Retoma sessões |
| **Todo List** | Tracking de progresso |
| **Web Search** | Busca integrada |
| **MCP Support** | Model Context Protocol |
| **Approval Modes** | 3 níveis de segurança |
| **Citations** | Evidências verificáveis |

---

## PARTE 3: GAP ANALYSIS - O QUE FALTA

### 3.1 Tools Críticos Faltando

| Tool | Prioridade | Complexidade | LOC Est. |
|------|------------|--------------|----------|
| **Glob** | P0 | Baixa | ~100 |
| **LS** | P0 | Baixa | ~50 |
| **MultiEdit** | P0 | Média | ~150 |
| **WebFetch** | P0 | Média | ~200 |
| **WebSearch** | P0 | Média | ~150 |
| **TodoRead/Write** | P0 | Baixa | ~100 |
| **NotebookRead/Edit** | P1 | Média | ~200 |
| **Task (Subagent)** | P1 | Alta | ~300 |

### 3.2 Slash Commands Críticos

| Comando | Prioridade | Complexidade |
|---------|------------|--------------|
| `/compact` | P0 | Média |
| `/context` | P0 | Baixa |
| `/cost` | P0 | Baixa |
| `/todos` | P0 | Baixa |
| `/resume` | P1 | Alta |
| `/rewind` | P1 | Alta |
| `/review` | P1 | Média |
| `/init` | P1 | Média |
| `/hooks` | P2 | Alta |
| `/mcp` | P2 | Alta |

### 3.3 Features Estruturais

| Feature | Prioridade | Complexidade |
|---------|------------|--------------|
| **@ File Mentions** (integrar file_picker.py) | P0 | Baixa |
| **/ Autocomplete** (integrar slash_completer.py) | P0 | Baixa |
| **Agent Routing** (conectar agents ao shell) | P0 | Média |
| **Dashboard** (conectar metrics_dashboard.py) | P0 | Baixa |
| **Token Tracking UI** | P0 | Baixa |
| **Session Persistence** | P1 | Média |
| **Hooks System** | P2 | Alta |
| **Background Tasks** | P2 | Alta |

---

## PARTE 4: PLANO DE IMPLEMENTAÇÃO

### FASE 0: INTEGRAÇÃO IMEDIATA (2-3 horas)
**Objetivo**: Conectar componentes já existentes

#### 0.1 Integrar File Picker (@ mentions)
```
Arquivo: qwen_cli/app.py
Ação: Importar e conectar FilePickerCompleter ao input
LOC: ~30 linhas
```

#### 0.2 Integrar Slash Completer
```
Arquivo: qwen_cli/app.py
Ação: Importar e conectar SlashCommandCompleter
LOC: ~30 linhas
```

#### 0.3 Ativar Dashboard de Métricas
```
Arquivo: qwen_cli/app.py
Ação: Adicionar MetricsDashboard ao layout
LOC: ~50 linhas
```

#### 0.4 Conectar Token Tracking
```
Arquivo: qwen_cli/core/bridge.py
Ação: Inicializar TokenTracker e atualizar UI
LOC: ~40 linhas
```

### FASE 1: TOOLS CRÍTICOS (4-6 horas)
**Objetivo**: Implementar tools faltantes para paridade

#### 1.1 Implementar GlobTool
```python
# qwen_dev_cli/tools/glob_tool.py
class GlobTool(BaseTool):
    """Fast file pattern matching using glob."""
    name = "glob"

    async def execute(self, pattern: str, path: str = ".") -> List[str]:
        """Match files against glob pattern."""
        from pathlib import Path
        results = sorted(Path(path).glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)
        return [str(p) for p in results]
```

#### 1.2 Implementar LSTool
```python
# qwen_dev_cli/tools/ls_tool.py
class LSTool(BaseTool):
    """List directory contents with details."""
    name = "ls"

    async def execute(self, path: str, ignore: List[str] = None) -> Dict:
        """List directory with file details."""
```

#### 1.3 Implementar MultiEditTool
```python
# qwen_dev_cli/tools/multi_edit_tool.py
class MultiEditTool(BaseTool):
    """Atomic multiple edits on a single file."""
    name = "multi_edit"

    async def execute(self, file_path: str, edits: List[Dict]) -> bool:
        """Apply multiple edits atomically."""
```

#### 1.4 Implementar WebFetchTool
```python
# qwen_dev_cli/tools/web_fetch_tool.py
class WebFetchTool(BaseTool):
    """Fetch URL and process with AI."""
    name = "web_fetch"

    async def execute(self, url: str, prompt: str) -> str:
        """Fetch URL, convert to markdown, process with LLM."""
```

#### 1.5 Implementar WebSearchTool
```python
# qwen_dev_cli/tools/web_search_tool.py
class WebSearchTool(BaseTool):
    """Search the web using SerpAPI or similar."""
    name = "web_search"

    async def execute(self, query: str, num_results: int = 10) -> List[Dict]:
        """Search web and return results."""
```

#### 1.6 Implementar TodoTools
```python
# qwen_dev_cli/tools/todo_tools.py
class TodoReadTool(BaseTool):
    name = "todo_read"

class TodoWriteTool(BaseTool):
    name = "todo_write"
```

### FASE 2: SLASH COMMANDS (3-4 horas)
**Objetivo**: Implementar comandos essenciais

#### 2.1 Comandos de Contexto
```python
# /compact - Compacta contexto com foco opcional
# /context - Visualiza uso de contexto (grid colorido)
# /cost - Mostra estatísticas de tokens
# /todos - Lista tarefas atuais
```

#### 2.2 Comandos de Sessão
```python
# /resume - Retoma sessão anterior
# /rewind - Volta a ponto anterior
# /export - Exporta conversa
```

#### 2.3 Comandos de Projeto
```python
# /init - Inicializa projeto com JUANCS.md
# /review - Solicita code review
# /doctor - Verifica saúde da instalação
```

### FASE 3: AGENT ORCHESTRATION (4-5 horas)
**Objetivo**: Conectar agents ao shell principal

#### 3.1 Agent Router
```python
# qwen_cli/core/agent_router.py
class AgentRouter:
    """Routes requests to appropriate agent."""

    ROUTES = {
        "architect": ["design", "architecture", "structure"],
        "explorer": ["find", "search", "where", "locate"],
        "planner": ["plan", "decompose", "strategy"],
        "executor": ["run", "execute", "bash", "command"],
        "reviewer": ["review", "check", "analyze"],
        "security": ["security", "vulnerability", "owasp"],
        "testing": ["test", "coverage", "pytest"],
        "refactorer": ["refactor", "improve", "clean"],
        "documentation": ["document", "docstring", "readme"],
        "devops": ["docker", "kubernetes", "ci", "deploy"],
        "data": ["database", "sql", "migration", "schema"],
    }
```

#### 3.2 Agent Stream Panel Integration
```python
# Conectar AgentStreamPanel ao output do agent
# Mostrar qual agent está processando
# Exibir progresso em tempo real
```

### FASE 4: FEATURES AVANÇADAS (6-8 horas)
**Objetivo**: Paridade completa com Claude Code

#### 4.1 Hooks System
```python
# qwen_dev_cli/hooks/
# - post_write_hook.py
# - pre_commit_hook.py
# - post_edit_hook.py
```

#### 4.2 Background Tasks
```python
# qwen_dev_cli/tasks/
# - background_runner.py
# - task_manager.py
```

#### 4.3 Session Persistence
```python
# qwen_dev_cli/session/
# - session_store.py
# - checkpoint_manager.py
```

#### 4.4 MCP Server/Client
```python
# Completar implementação MCP
# Expor tools via MCP
# Conectar a MCP servers externos
```

---

## PARTE 5: ARQUIVOS CRÍTICOS A MODIFICAR

### 5.1 Entry Point Principal
```
qwen_cli/app.py (49KB)
- Integrar FilePickerCompleter
- Integrar SlashCommandCompleter
- Adicionar MetricsDashboard
- Conectar TokenTracker
- Implementar novos slash commands
```

### 5.2 Bridge de Integração
```
qwen_cli/core/bridge.py (63KB)
- Adicionar AgentRouter
- Implementar tool registration
- Conectar governance
- Adicionar session persistence
```

### 5.3 Novos Arquivos a Criar
```
qwen_dev_cli/tools/glob_tool.py
qwen_dev_cli/tools/ls_tool.py
qwen_dev_cli/tools/multi_edit_tool.py
qwen_dev_cli/tools/web_fetch_tool.py
qwen_dev_cli/tools/web_search_tool.py
qwen_dev_cli/tools/todo_tools.py
qwen_dev_cli/tools/notebook_tools.py
qwen_cli/core/agent_router.py
qwen_cli/core/session_manager.py
qwen_dev_cli/hooks/hook_manager.py
```

### 5.4 Componentes a Integrar (já existem)
```
qwen_dev_cli/tui/components/file_picker.py → app.py
qwen_dev_cli/tui/components/slash_completer.py → app.py
qwen_dev_cli/tui/components/metrics_dashboard.py → app.py
qwen_dev_cli/tui/components/context_awareness.py → bridge.py
qwen_dev_cli/tui/components/agent_stream_panel.py → app.py
qwen_dev_cli/core/token_tracker.py → bridge.py
```

---

## PARTE 6: CRONOGRAMA DE EXECUÇÃO

### Sprint 1: Integração Imediata (Dia 1)
| Task | Tempo | Prioridade |
|------|-------|------------|
| Integrar file_picker.py | 30min | P0 |
| Integrar slash_completer.py | 30min | P0 |
| Conectar MetricsDashboard | 45min | P0 |
| Ativar TokenTracker | 30min | P0 |
| **TOTAL** | **2h15min** | |

### Sprint 2: Tools Críticos (Dia 1-2)
| Task | Tempo | Prioridade |
|------|-------|------------|
| Implementar GlobTool | 45min | P0 |
| Implementar LSTool | 30min | P0 |
| Implementar MultiEditTool | 1h | P0 |
| Implementar WebFetchTool | 1h30min | P0 |
| Implementar WebSearchTool | 1h | P0 |
| Implementar TodoTools | 45min | P0 |
| **TOTAL** | **5h30min** | |

### Sprint 3: Slash Commands (Dia 2)
| Task | Tempo | Prioridade |
|------|-------|------------|
| /compact, /context, /cost | 1h30min | P0 |
| /todos, /resume, /rewind | 2h | P1 |
| /init, /review, /doctor | 1h30min | P1 |
| **TOTAL** | **5h** | |

### Sprint 4: Agent Integration (Dia 2-3)
| Task | Tempo | Prioridade |
|------|-------|------------|
| AgentRouter | 2h | P0 |
| Agent Stream Panel | 1h30min | P0 |
| Agent Selection UI | 1h | P1 |
| **TOTAL** | **4h30min** | |

### Sprint 5: Features Avançadas (Dia 3-4)
| Task | Tempo | Prioridade |
|------|-------|------------|
| Hooks System | 3h | P2 |
| Background Tasks | 2h | P2 |
| Session Persistence | 2h | P1 |
| MCP Completion | 2h | P2 |
| **TOTAL** | **9h** | |

---

## PARTE 7: CRITÉRIOS DE SUCESSO

### 7.1 Paridade Funcional (100%)
- [ ] Todos os 16 tools do Claude Code implementados
- [ ] Todos os 37 slash commands implementados
- [ ] @ file mentions funcionando
- [ ] / autocomplete funcionando
- [ ] Dashboard de métricas visível
- [ ] Token tracking em tempo real
- [ ] Agents roteados automaticamente

### 7.2 Confiabilidade
- [ ] Zero crashes em operações normais
- [ ] Error recovery funcional
- [ ] Session persistence funcional
- [ ] Timeout handling em todas as operações

### 7.3 Performance
- [ ] Startup < 2s
- [ ] Latência de resposta < 100ms (UI)
- [ ] Streaming a 60fps
- [ ] Memory footprint < 500MB

### 7.4 UX
- [ ] Fluxo fluido sem interrupções
- [ ] Feedback visual em todas as operações
- [ ] Help system completo
- [ ] Mensagens de erro claras

---

## PARTE 8: RISCOS E MITIGAÇÕES

| Risco | Probabilidade | Impacto | Mitigação |
|-------|---------------|---------|-----------|
| Textual buga com componentes complexos | Alta | Alto | Testar incrementalmente, evitar Live() |
| WebSearch API key faltando | Média | Médio | Fallback para DuckDuckGo |
| Performance degradada com muitos tools | Baixa | Alto | Lazy loading, caching |
| Conflito entre agents | Média | Médio | Priority routing, mutex |

---

## PARTE 9: SOURCES E REFERÊNCIAS

### Documentação Oficial
- [Claude Code Docs](https://code.claude.com/docs/en/overview)
- [Claude Code Slash Commands](https://code.claude.com/docs/en/slash-commands)
- [Gemini CLI Docs](https://developers.google.com/gemini-code-assist/docs/gemini-cli)
- [Codex CLI Docs](https://developers.openai.com/codex/cli/)

### Repositórios
- [Claude Code GitHub](https://github.com/anthropics/claude-code)
- [Gemini CLI GitHub](https://github.com/google-gemini/gemini-cli/)
- [OpenAI Codex GitHub](https://github.com/openai/codex)

### Análise de Tools
- [Claude Code Tools Reference](https://www.vtrivedy.com/posts/claudecode-tools-reference)
- [Claude Code System Prompt](https://gist.github.com/wong2/e0f34aac66caf890a332f7b6f9e2ba8f)

---

## APROVAÇÃO

**Este plano foi elaborado com base em:**
1. Análise profunda de 255 arquivos Python do projeto
2. Auditoria de 51.000+ linhas de código
3. Pesquisa de documentação oficial Nov 2025 (Anthropic, Google, OpenAI)
4. Comparação feature-by-feature com Claude Code, Gemini CLI, Codex CLI

**Próximo passo**: Executar FASE 0 (Integração Imediata)

---

*Documento gerado em 2025-11-25 por Claude Opus 4.5 sob Constituição Vértice v3.0*
