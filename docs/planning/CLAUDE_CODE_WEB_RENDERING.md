# Plan: Renderização Estilo Claude Code Web no TUI

**Data:** 2025-11-25
**Objetivo:** Implementar streaming markdown espetacular como Claude Code Web no JuanCS Dev-Code TUI

---

## DECISÕES DO USUÁRIO

| Decisão | Escolha |
|---------|---------|
| **Escopo** | MVP Completo (todas as 5 fases) |
| **Target** | TUI (Textual) primeiro |
| **Fallback** | Plain text automático quando FPS < 25 |

---

## 1. VISÃO GERAL

### O que o Claude Code Web faz (screenshots analisados):
- ✅ Tabelas Markdown renderizadas AO VIVO durante streaming
- ✅ Checklists com strikethrough animado (~~task~~)
- ✅ Badges coloridos (🔴 BLOCKER, 🟡 IMPORTANTE, 🟢 SUGESTÃO)
- ✅ Diff de código com syntax highlighting
- ✅ Streaming progressivo de conteúdo estruturado

### Tecnologias-chave descobertas (Deep Research Nov/2025):
| Tecnologia | Uso | Fonte |
|------------|-----|-------|
| **Streamdown** (Vercel) | Parser markdown para streaming incompleto | [GitHub](https://github.com/vercel/streamdown) |
| **Textual v4.0+** | `MarkdownStream` widget nativo | [Release Notes](https://simonwillison.net/2025/Jul/22/textual-v4/) |
| **Optimistic Parsing** | Renderiza `**bold` antes do fechamento | Chrome DevTools Blog |
| **Block-Level Optimization** | Re-parse apenas último bloco | Will McGugan |

---

## 2. ARQUITETURA PROPOSTA

```
┌─────────────────────────────────────────────────────────────────┐
│                    StreamingMarkdownRenderer                     │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐   ┌─────────────────┐   ┌─────────────────┐   │
│  │TokenBuffer  │──▶│ BlockDetector   │──▶│ MarkdownStream  │   │
│  │(batching)   │   │ (state machine) │   │ (Textual v4.0)  │   │
│  └─────────────┘   └─────────────────┘   └─────────────────┘   │
│         │                  │                      │             │
│         ▼                  ▼                      ▼             │
│  ┌─────────────┐   ┌─────────────────┐   ┌─────────────────┐   │
│  │ 30 FPS      │   │ BlockTypeState  │   │ Widget Factory  │   │
│  │ Throttle    │   │ Machine         │   │ (code,table,..) │   │
│  └─────────────┘   └─────────────────┘   └─────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### Princípios fundamentais:
1. **Blocos finalizados NUNCA são re-parseados** (apenas append)
2. **Apenas o último bloco é re-avaliado** a cada chunk
3. **Optimistic rendering** - `**bold` renderiza como bold mesmo incompleto
4. **30 FPS máximo** - frame budget de 33.33ms

---

## 3. ESTADO ATUAL DO CÓDIGO

### Arquivos existentes relevantes:

| Arquivo | Função | Gap |
|---------|--------|-----|
| `tui/components/streaming_display.py` | 30 FPS streaming | Texto raw, sem markdown |
| `tui/components/markdown_enhanced.py` | Markdown rico | Batch completo, não streaming |
| `tui/components/agent_stream_panel.py` | Panel de agente | Plain text via `Text()` |
| `tui/components/code.py` | Syntax highlighting | Não incremental |

### Dependência crítica:
```toml
# pyproject.toml (linha 37) - DESATUALIZADO
"textual>=0.47.0"  # Atual instalado: 6.2.1, mas spec baixa

# PRECISA ATUALIZAR PARA:
"textual>=4.0.0"  # Habilita MarkdownStream
```

---

## 4. NOVOS ARQUIVOS A CRIAR

### 4.1 `tui/components/streaming_markdown.py` (CORE)

```python
"""
Widget principal de streaming markdown.
Combina MarkdownStream do Textual v4.0+ com detecção de blocos customizada.
"""

from textual.widgets import Markdown
from textual.widget import Widget
from textual.reactive import reactive

class StreamingMarkdownWidget(Widget):
    is_streaming = reactive(False)
    current_block_type = reactive("unknown")

    async def start_stream(self):
        """Inicia streaming session."""
        self.is_streaming = True
        self._stream = Markdown.get_stream(self._markdown)

    async def append_stream(self, chunk: str):
        """Adiciona chunk - MarkdownStream cuida do batching."""
        await self._stream.write(chunk)

    async def end_stream(self):
        """Finaliza streaming."""
        await self._stream.stop()
        self.is_streaming = False
```

### 4.2 `tui/components/block_detector.py`

```python
"""
State machine para detecção de blocos durante streaming.
Identifica code fences, tabelas, checklists enquanto tokens chegam.
"""

class BlockType(Enum):
    UNKNOWN = "unknown"
    PARAGRAPH = "paragraph"
    CODE_FENCE = "code_fence"
    TABLE = "table"
    CHECKLIST = "checklist"
    HEADING = "heading"
    LIST = "list"

class BlockDetector:
    PATTERNS = {
        BlockType.CODE_FENCE: r'^```(\w*)',
        BlockType.TABLE: r'^\|.*\|',
        BlockType.CHECKLIST: r'^[-*]\s+\[[ x]\]',
        BlockType.HEADING: r'^#{1,6}\s',
    }

    def detect(self, text: str) -> BlockType:
        """Detecta tipo de bloco a partir de texto parcial."""
```

### 4.3 `tui/components/streaming_table.py`

```python
"""
Renderização progressiva de tabelas durante streaming.
Renderiza após primeira row, adapta largura dinamicamente.
"""

class StreamingTableRenderer:
    class TableState(Enum):
        WAITING_HEADER = 1
        WAITING_SEPARATOR = 2
        READY_FOR_ROWS = 3

    def process_chunk(self, chunk: str) -> Optional[Table]:
        """Processa chunk e retorna Table atualizado."""
```

### 4.4 `tui/components/interactive_checklist.py`

```python
"""
Checklist interativo com animação de strikethrough.
Click para toggle, animação ease-out de 200ms.
"""

@dataclass
class ChecklistItem:
    text: str
    checked: bool = False
    animation_state: str = "idle"

class StrikethroughAnimation:
    DURATION_MS = 200

    async def animate(self, text: str, on_frame: Callable):
        """Anima strikethrough da esquerda para direita."""
```

### 4.5 `tui/components/streaming_code_block.py`

```python
"""
Code block que cresce durante streaming com syntax highlighting incremental.
"""

class IncrementalSyntaxHighlighter:
    def highlight_incremental(self, full_code: str) -> List[Token]:
        """Retorna tokens - apenas parseia código novo."""
```

---

## 5. ARQUIVOS A MODIFICAR

### 5.1 `pyproject.toml`
```diff
- "textual>=0.47.0",
+ "textual>=4.0.0",
```

### 5.2 `tui/components/agent_stream_panel.py`
```diff
# Substituir renderização plain text por markdown streaming
- content.append(line + "\n", style=text_color)
+ await self.markdown_widget.append_stream(line + "\n")
```

### 5.3 `tui/components/maestro_shell_ui.py`
- Integrar `StreamingMarkdownWidget` no layout principal
- Substituir `Text()` por markdown renderizado

---

## 6. ORDEM DE IMPLEMENTAÇÃO

### FASE 1: FUNDAÇÃO (Dia 1-2)
```
1.1 Atualizar pyproject.toml (textual>=4.0.0)
1.2 Criar block_detector.py
1.3 Criar streaming_markdown.py (widget básico)
1.4 Testes unitários de detecção de blocos
```

### FASE 2: CODE BLOCKS (Dia 3)
```
2.1 Criar streaming_code_block.py
2.2 IncrementalSyntaxHighlighter com Pygments
2.3 Cursor pulsante no final do código
```

### FASE 3: TABELAS (Dia 4)
```
3.1 Criar streaming_table.py
3.2 AdaptiveTableWidth para colunas dinâmicas
3.3 Integrar com Rich.Table
```

### FASE 4: CHECKLISTS (Dia 5)
```
4.1 Criar interactive_checklist.py
4.2 StrikethroughAnimation (ease-out 200ms)
4.3 Eventos de click com toggle
```

### FASE 5: INTEGRAÇÃO (Dia 6-7)
```
5.1 Modificar agent_stream_panel.py
5.2 Modificar maestro_shell_ui.py
5.3 Testes end-to-end
5.4 Performance profiling (target: 30 FPS)
```

---

## 7. MÉTRICAS DE SUCESSO

| Métrica | Target | Como Medir |
|---------|--------|------------|
| FPS durante streaming | ≥ 30 | `PerformanceMonitor.get_current_fps()` |
| Latência append→render | < 50ms | `time.perf_counter()` |
| Memory por 1000 tokens | < 10MB | `tracemalloc` |
| Block detection accuracy | > 99% | Unit tests |

---

## 8. ARQUIVOS CRÍTICOS PARA LER ANTES DE IMPLEMENTAR

1. **`tui/components/agent_stream_panel.py`** - Core panel que precisa integração
2. **`tui/components/streaming_display.py`** - Lógica de 30 FPS existente
3. **`tui/components/markdown_enhanced.py`** - Padrões de markdown a reusar
4. **`tui/components/maestro_shell_ui.py`** - Shell principal onde integrar
5. **`tui/theme.py`** - Cores para syntax highlighting

---

## 9. SISTEMA DE FALLBACK AUTOMÁTICO

```python
class AdaptiveFPSController:
    """
    Monitora FPS e alterna para plain text automaticamente.

    Comportamento:
    - FPS >= 30: Markdown completo
    - FPS 25-29: Warning visual, continua markdown
    - FPS < 25: Fallback para plain text
    """

    FPS_THRESHOLD_WARNING = 29
    FPS_THRESHOLD_FALLBACK = 25
    RECOVERY_FRAMES = 60  # Frames para tentar voltar ao markdown

    def __init__(self):
        self.mode = "markdown"  # markdown | plain_text
        self.frames_in_plain = 0

    def check_and_adapt(self, current_fps: float) -> str:
        if self.mode == "markdown":
            if current_fps < self.FPS_THRESHOLD_FALLBACK:
                self.mode = "plain_text"
                self.frames_in_plain = 0
                return "FALLBACK_TO_PLAIN"
        else:
            self.frames_in_plain += 1
            if self.frames_in_plain >= self.RECOVERY_FRAMES:
                self.mode = "markdown"
                return "TRY_MARKDOWN_AGAIN"
        return self.mode
```

**Integração no StreamingMarkdownWidget:**
- Monitora `PerformanceMonitor.get_current_fps()` a cada frame
- Quando FPS < 25 por 5 frames consecutivos → switch para `Text()` plain
- A cada 60 frames em plain text → tenta voltar para markdown
- Visual: Mostra "⚡ Performance mode" quando em plain text

---

## 10. RISCOS E MITIGAÇÕES

| Risco | Mitigação |
|-------|-----------|
| Textual v4.0+ breaking changes | Testar em branch separado |
| Performance com markdown complexo | Fallback automático para plain text (FPS < 25) |
| Conflitos com MaestroShellUI | Feature flag para rollback |

---

## 11. FONTES DA PESQUISA

- [Streamdown - Vercel](https://github.com/vercel/streamdown)
- [Textual v4.0.0: The Streaming Release](https://simonwillison.net/2025/Jul/22/textual-v4/)
- [Chrome DevTools: Render LLM responses](https://developer.chrome.com/docs/ai/render-llm-responses)
- [Claude Code on the web](https://www.anthropic.com/news/claude-code-on-the-web)
- [Rich library - Textualize](https://github.com/Textualize/rich)
