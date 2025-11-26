# Plan: Refatoração Gradio UI - Hackathon Visual Futurista

## Resumo Executivo

Refatorar a interface Gradio para replicar o design futurista da imagem de referência. O objetivo é criar uma UI de hackathon-quality com layout 3 colunas, glassmorphism, neon effects e dashboard em tempo real.

**Nome:** JuanCS Dev-Code
**Progress Bar:** Real (conectada ao backend)
**Dashboard:** Expandido (todos os painéis + MCP Tools list)

**Estado Atual:** ~95% implementado, precisa refinamentos visuais e correções de CSS/Gradio 6.

---

## Arquivos Críticos

| Arquivo | LOC | Função | Mudanças |
|---------|-----|--------|----------|
| `gradio_ui/app.py` | 565 | UI principal | Layout refinado, header, progress bar |
| `gradio_ui/components.py` | 290 | SVG/HTML gauges | Aprimorar visual dos componentes |
| `gradio_ui/cyber_theme.css` | 463 | Estilos CSS | Refinar glassmorphism, cores, animações |
| `gradio_ui/cli_bridge.py` | 227 | Backend bridge | Manter, já funcional |

---

## Análise da Imagem de Referência

### Layout Alvo
```
┌─────────────────────────────────────────────────────────────────────┐
│  GEMINI-CLI-2                                          [─] [□] [×]  │
├────────────────┬─────────────────────────────┬──────────────────────┤
│ 📁 project-alpha│  User: generate a python...│  Constitutional AI   │
│   > 📁 src      │  ┌─────────────────────┐   │  ┌──────────────────┐│
│     🐍 main.py  │  │ ```python           │   │  │   ◐ 75%         ││
│     🐍 utils.py │  │ from Flask import...│   │  │  Token Budget   ││
│   > 📁 .docker  │  │ app = Flask(...)    │   │  │  750,080/1M     ││
│     🐳 Dockerfile  └─────────────────────┘   │  └──────────────────┘│
│     📄 compose.yml                           │  ┌──────────────────┐│
│                 │  [INFO] Building Docker... │  │ ▃▅▇▅▃▁  98.5%   ││
│                 │  [INFO] Step 1/5: FROM...  │  │ Safety Index     ││
│                 │  [INFO] Step 2/5: WORKDIR  │  └──────────────────┘│
│                 │  ━━━━━━━━━━━━━━░░░░ 68%    │  ┌────────┬─────────┐│
│                 │  Docker Build              │  │Model:  │Environ: ││
│                 │                            │  │Pro 1.5 │Production│
└─────────────────┴────────────────────────────┴──────────────────────┘
```

### Elementos Visuais Chave
1. **Header escuro** com título neon e window controls
2. **Sidebar esquerda** com file tree (ícones por tipo)
3. **Centro** com chat + syntax highlighting + progress bar
4. **Sidebar direita** com dashboard de métricas (gauges, charts)
5. **Cores**: Fundo #0A0E14, Accent cyan #00D9FF, magenta/purple accents
6. **Efeitos**: Glassmorphism, neon glow, gradientes

---

## Fase 1: Estrutura CSS Aprimorada

### 1.1 Atualizar `cyber_theme.css`

```css
/* ADICIONAR: Window-style header bar */
.window-header {
  background: linear-gradient(90deg, #1a1f2e 0%, #0d1117 100%);
  border-bottom: 1px solid rgba(0, 217, 255, 0.3);
  padding: 8px 16px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.window-title {
  font-family: 'Segoe UI', monospace;
  font-size: 14px;
  color: #E6E6E6;
  letter-spacing: 0.05em;
}

.window-controls {
  display: flex;
  gap: 8px;
}

.window-controls span {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  cursor: pointer;
}

.ctrl-minimize { background: #f1fa8c; }
.ctrl-maximize { background: #50fa7b; }
.ctrl-close { background: #ff5555; }

/* ADICIONAR: Progress bar estilo Docker */
.docker-progress {
  background: rgba(0, 217, 255, 0.1);
  border: 1px solid rgba(0, 217, 255, 0.3);
  border-radius: 4px;
  height: 24px;
  overflow: hidden;
  position: relative;
}

.docker-progress-bar {
  height: 100%;
  background: linear-gradient(90deg, #00D9FF 0%, #00A8CC 100%);
  transition: width 0.5s ease;
  box-shadow: 0 0 10px rgba(0, 217, 255, 0.5);
}

.docker-progress-text {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 600;
  color: white;
  text-shadow: 0 0 4px rgba(0, 0, 0, 0.8);
}

/* REFINAR: File tree icons */
.file-explorer-cyber .file-icon::before {
  margin-right: 6px;
}

.file-explorer-cyber [data-path$=".py"]::before { content: "🐍"; }
.file-explorer-cyber [data-path$=".js"]::before { content: "📜"; }
.file-explorer-cyber [data-path$=".html"]::before { content: "🌐"; }
.file-explorer-cyber [data-path$=".css"]::before { content: "🎨"; }
.file-explorer-cyber [data-path$=".json"]::before { content: "📋"; }
.file-explorer-cyber [data-path$=".yml"]::before,
.file-explorer-cyber [data-path$=".yaml"]::before { content: "⚙️"; }
.file-explorer-cyber [data-path*="Dockerfile"]::before { content: "🐳"; }
.file-explorer-cyber .folder-icon::before { content: "📁"; }

/* ADICIONAR: Latency sparkline area */
.latency-chart {
  height: 48px;
  display: flex;
  align-items: flex-end;
  gap: 2px;
  padding: 8px;
  background: rgba(0, 217, 255, 0.05);
  border-radius: 4px;
}

.latency-bar {
  flex: 1;
  background: linear-gradient(180deg, #f59e0b 0%, #f97316 100%);
  border-radius: 2px 2px 0 0;
  min-height: 4px;
  transition: height 0.3s ease;
}
```

### 1.2 Gradio 6 CSS Injection (Método Correto)

```python
# Em app.py - launch() com CSS externo
def launch_ui():
    css_path = Path(__file__).parent / "cyber_theme.css"
    with open(css_path) as f:
        custom_css = f.read()

    with gr.Blocks(
        title="GEMINI-CLI-2",
        css=custom_css,  # CSS inline (Gradio 6 preferred)
        theme=gr.themes.Base(
            primary_hue="cyan",
            secondary_hue="purple",
        ).set(
            body_background_fill="#0A0E14",
            block_background_fill="#141922",
            border_color_primary="#00D9FF40",
        )
    ) as demo:
        # ...
```

---

## Fase 2: Layout 3-Colunas Refinado

### 2.1 Header Window-Style

```python
# SUBSTITUIR header atual por:
with gr.Row(elem_classes="window-header"):
    gr.HTML("""
        <div style="display: flex; align-items: center; gap: 12px;">
            <div class="window-controls">
                <span class="ctrl-close"></span>
                <span class="ctrl-minimize"></span>
                <span class="ctrl-maximize"></span>
            </div>
            <span class="window-title">JuanCS Dev-Code</span>
        </div>
    """)
    gr.HTML("""
        <div style="display: flex; align-items: center; gap: 16px;">
            <span style="color: #6272a4; font-size: 12px;">v0.0.2</span>
            <span style="color: #6272a4; font-size: 12px;">─ □ ×</span>
        </div>
    """)
```

### 2.2 Sidebar Esquerda (File Tree Aprimorado)

```python
with gr.Column(scale=1, min_width=220, elem_classes="cyber-glass-bright"):
    gr.Markdown("### 📁 project-alpha", elem_classes="text-sm font-mono text-gray-300")

    file_explorer = gr.FileExplorer(
        glob="**/*",
        root_dir=str(PROJECT_ROOT),
        height=400,
        label=None,
        file_count="multiple",
        elem_classes="file-explorer-cyber",
        ignore_glob=["**/__pycache__/**", "**/.git/**", "**/node_modules/**"]
    )
```

### 2.3 Centro (Chat + Terminal + Progress)

```python
with gr.Column(scale=3, elem_classes="space-y-3"):
    # Chat
    chatbot = gr.Chatbot(
        label=None,
        height=350,
        render_markdown=True,
        elem_classes="cyber-glass chat-container",
        show_copy_button=True,
        bubble_full_width=False,
    )

    # Input
    with gr.Group(elem_classes="cyber-glass p-2"):
        msg_input = gr.Textbox(
            placeholder="User: type your command...",
            show_label=False,
            lines=1,
            elem_classes="cyber-input",
            autofocus=True,
        )

    # Terminal Logs (estilo imagem)
    log_display = gr.HTML(
        value=render_terminal_logs(_monitor.logs[-6:]),
        elem_classes="terminal-display"
    )

    # Docker Progress Bar (NOVO)
    progress_html = gr.HTML(
        value=render_docker_progress(68, "Docker Build"),
        elem_classes="docker-progress-container"
    )
```

### 2.4 Sidebar Direita (Dashboard Métricas)

```python
with gr.Column(scale=1, min_width=220, elem_classes="space-y-3"):
    gr.Markdown("### Constitutional AI", elem_classes="text-sm font-bold text-center text-gray-400")

    # Token Budget Gauge (maior)
    with gr.Group(elem_classes="cyber-glass-bright p-4"):
        gauge_html = gr.HTML(
            value=render_gauge(75, "Token Budget", "750,080/1M")
        )

    # Safety Index (bar chart horizontal)
    with gr.Group(elem_classes="cyber-glass p-3"):
        safety_html = gr.HTML(
            value=render_safety_chart(98.5)
        )

    # Latency Chart (sparkline)
    with gr.Group(elem_classes="cyber-glass p-3"):
        latency_html = gr.HTML(
            value=render_latency_chart([12, 45, 23, 67, 34, 45, 28], "45ms")
        )

    # Model + Environment (mini gauges)
    with gr.Group(elem_classes="cyber-glass p-3"):
        status_html = gr.HTML(
            value=render_dual_status("Pro 1.5", "Production")
        )
```

---

## Fase 3: Novos Componentes SVG (components.py)

### 3.1 Progress Bar Real (Conectada ao Backend)

```python
# Em cli_bridge.py - adicionar tracking de progresso
class ProgressTracker:
    """Rastreia progresso de operações longas."""
    def __init__(self):
        self.current_operation = ""
        self.percentage = 0
        self.steps = []

    def start(self, operation: str, total_steps: int = 5):
        self.current_operation = operation
        self.percentage = 0
        self.steps = []

    def update(self, step: str, pct: float):
        self.steps.append(step)
        self.percentage = pct

    def complete(self):
        self.percentage = 100

_progress = ProgressTracker()

def render_progress_bar(tracker: ProgressTracker) -> str:
    """Barra de progresso conectada ao backend real."""
    pct = tracker.percentage
    label = tracker.current_operation or "Ready"
    steps = tracker.steps[-3:] if tracker.steps else []

    steps_html = "".join(
        f'<div style="font-size: 11px; color: #3B82F6;">[INFO] {s}</div>'
        for s in steps
    )

    return f"""
    <div style="background: #0d1117; border: 1px solid #00D9FF30; border-radius: 6px; padding: 12px;">
        {steps_html}
        <div class="docker-progress" style="margin-top: 8px;">
            <div class="docker-progress-bar" style="width: {pct}%;"></div>
            <div class="docker-progress-text">{label} - {pct:.0f}%</div>
        </div>
    </div>
    """
```

### 3.2 Latency Sparkline Chart

```python
def render_latency_chart(values: List[int], current: str) -> str:
    """Sparkline de latência com barras verticais."""
    max_val = max(values) if values else 1
    bars = ""
    for i, v in enumerate(values):
        height = int((v / max_val) * 40)
        color = "#f59e0b" if i == len(values) - 1 else "#00D9FF"
        bars += f'<div class="latency-bar" style="height: {height}px; background: {color};"></div>'

    return f"""
    <div style="text-align: center; color: #6272a4; font-size: 11px; margin-bottom: 4px;">
        Latency (ms)
    </div>
    <div class="latency-chart">{bars}</div>
    <div style="text-align: right; color: #f59e0b; font-size: 14px; font-weight: 600; margin-top: 4px;">
        {current}
    </div>
    """
```

### 3.3 Model/Environment Status (Mini Cards)

```python
def render_dual_status(model: str, env: str) -> str:
    """Cards lado a lado para Model e Environment."""
    return f"""
    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px;">
        <div style="background: rgba(0, 217, 255, 0.1); border: 1px solid #00D9FF40; border-radius: 6px; padding: 8px; text-align: center;">
            <div style="font-size: 10px; color: #6272a4; text-transform: uppercase;">Model</div>
            <div style="font-size: 14px; color: #00D9FF; font-weight: 600; margin-top: 4px;">{model}</div>
        </div>
        <div style="background: rgba(16, 185, 129, 0.1); border: 1px solid #10B98140; border-radius: 6px; padding: 8px; text-align: center;">
            <div style="font-size: 10px; color: #6272a4; text-transform: uppercase;">Environment</div>
            <div style="font-size: 14px; color: #10B981; font-weight: 600; margin-top: 4px;">{env}</div>
        </div>
    </div>
    """
```

---

## Fase 4: Integração Gradio 6

### 4.1 Workarounds Conhecidos

```python
# PROBLEMA: gr.Timer causa ERR_CONNECTION_REFUSED
# SOLUÇÃO: Botão de refresh manual (já implementado)

# PROBLEMA: CSS externo não carrega corretamente
# SOLUÇÃO: Inline CSS no parâmetro css= de gr.Blocks()

# PROBLEMA: Tailwind CDN inconsistente
# SOLUÇÃO: Injetar via gr.HTML() no topo do layout

# PROBLEMA: FileExplorer não aceita ícones customizados via CSS
# SOLUÇÃO: Usar data-path selectors com ::before pseudo-elements
```

### 4.2 Launch Configuration

```python
demo.launch(
    server_name="0.0.0.0",
    server_port=int(os.environ.get("GRADIO_PORT", 7860)),
    share=os.environ.get("GRADIO_SHARE", "false").lower() == "true",
    favicon_path=Path(__file__).parent / "favicon.ico",
    show_error=True,
    quiet=False,
)
```

---

## Fase 5: Refinamentos Finais

### 5.1 Ajustes de Cores Imagem-Perfect

```css
:root {
  /* Cores exatas da imagem de referência */
  --bg-main: #0a0e14;           /* Fundo principal */
  --bg-panel: #151a23;          /* Painéis */
  --bg-sidebar: #0d1117;        /* Sidebar */
  --accent-cyan: #00d4ff;       /* Cyan primário */
  --accent-magenta: #ff79c6;    /* Magenta highlights */
  --accent-purple: #bd93f9;     /* Purple accents */
  --accent-green: #50fa7b;      /* Success */
  --accent-orange: #ffb86c;     /* Warning */
  --accent-red: #ff5555;        /* Error */
  --text-primary: #f8f8f2;      /* Texto principal */
  --text-muted: #6272a4;        /* Texto secundário */
}
```

### 5.2 Animações Sutis

```css
/* Pulse suave no gauge */
@keyframes gauge-pulse {
  0%, 100% { filter: drop-shadow(0 0 15px var(--glow-color)); }
  50% { filter: drop-shadow(0 0 25px var(--glow-color)); }
}

/* Typing cursor no terminal */
@keyframes cursor-blink {
  0%, 50% { opacity: 1; }
  51%, 100% { opacity: 0; }
}

.terminal-cursor::after {
  content: "▋";
  animation: cursor-blink 1s infinite;
  color: #00D9FF;
}
```

---

## Ordem de Implementação

1. **cyber_theme.css** - Adicionar novos estilos (window-header, progress, latency)
2. **components.py** - Novos renders (docker_progress, latency_chart, dual_status)
3. **app.py** - Refatorar layout 3-colunas com novos componentes
4. **app.py** - Aplicar CSS inline no gr.Blocks()
5. **Testar** - Verificar visual no browser
6. **Ajustar** - Fine-tune cores e espaçamentos

---

## Critérios de Sucesso

- [ ] Layout 3-colunas idêntico à imagem de referência
- [ ] Header com window controls (vermelho, amarelo, verde)
- [ ] File tree com ícones por extensão
- [ ] Chat com syntax highlighting
- [ ] Dashboard com gauge circular, safety chart, latency sparkline
- [ ] Progress bar estilo Docker
- [ ] Cores e efeitos glassmorphism consistentes
- [ ] Funciona em Gradio 6.x sem erros

---

## Referências

- **Imagem alvo:** Screenshot GEMINI-CLI-2 futurista
- **Gradio 6 Docs:** https://gradio.app/docs
- **CSS Glassmorphism:** backdrop-filter: blur() + saturate()
- **Dracula Theme Colors:** https://draculatheme.com/contribute
