# 🚀 Plano de Migração: Gradio 5.49.1 → 6.0

**Status:** 📋 Planejamento  
**Versão Atual:** 5.49.1  
**Versão Alvo:** 6.0  
**Data:** 2025-01-21

---

## 📊 Resumo Executivo

O Gradio 6.0 traz mudanças significativas, especialmente no formato de mensagens do chat, alinhando-se com o padrão OpenAI. Esta migração nos permitirá:

- ✅ Suporte nativo para conteúdo multimodal (texto, imagens, arquivos)
- ✅ Exibição de tool usage e pensamentos intermediários
- ✅ Melhor compatibilidade com APIs de LLM (OpenAI, HuggingFace)
- ✅ Interface mobile aprimorada
- ✅ Componentes JavaScript standalone

---

## 🔍 Principais Mudanças

### 1. **Formato de History - BREAKING CHANGE**

#### Antes (Gradio 5.x):
```python
history = [
    {"role": "user", "content": "Read README.md"},
    {"role": "assistant", "content": "Here's the content..."}
]
```

#### Depois (Gradio 6.x):
```python
history = [
    {"role": "user", "content": [{"type": "text", "text": "Read README.md"}]},
    {"role": "assistant", "content": [{"type": "text", "text": "Here's the content..."}]}
]
```

**Impacto:** 🔴 **ALTO** - Requer mudanças em `gradio_ui/app.py` na função `stream_conversation()`

---

### 2. **gr.Chatbot com `type='messages'`**

#### Antes (Gradio 5.x):
```python
chatbot = gr.Chatbot(
    label="Dev Session",
    type="messages",  # Já estamos usando!
    height=400,
)
```

#### Depois (Gradio 6.x):
```python
from gradio import ChatMessage

chatbot = gr.Chatbot(
    label="Dev Session",
    type="messages",  # Mantém
    height=400,
)

# Usar ChatMessage para type hints
def stream_conversation(message: str, history: list[ChatMessage]):
    ...
```

**Impacto:** 🟡 **MÉDIO** - Adicionar type hints, mas sintaxe similar

---

### 3. **Tool Usage Display (NOVO!)**

Agora podemos mostrar o uso de ferramentas MCP de forma nativa:

```python
from gradio import ChatMessage

# Mostrar tool execution
history.append(ChatMessage(
    role="assistant",
    content="Executing read_file tool...",
    metadata={
        "title": "🔧 Tool Usage",
        "value": "read_file(path='README.md')"
    }
))
```

**Impacto:** 🟢 **BAIXO** - Feature opcional, mas MUITO útil para MCP!

---

### 4. **Multimodal Content**

Suporte nativo para imagens, arquivos, etc:

```python
history.append(ChatMessage(
    role="assistant",
    content=[
        {"type": "text", "text": "Here's the diagram:"},
        {"type": "image", "image": "path/to/image.png"}
    ]
))
```

**Impacto:** 🟢 **BAIXO** - Feature futura, não crítica agora

---

## 📝 Checklist de Migração

### Fase 1: Preparação (15 min)
- [ ] Backup do código atual
- [ ] Criar branch `feature/gradio-6-migration`
- [ ] Atualizar requirements.txt
- [ ] Atualizar Gradio: `pip install --upgrade gradio`

### Fase 2: Código Core (30 min)
- [ ] **app.py**: Atualizar `stream_conversation()` para novo formato
- [ ] **app.py**: Adicionar `from gradio import ChatMessage`
- [ ] **app.py**: Atualizar type hints
- [ ] **cli_bridge.py**: Verificar compatibilidade com novo formato

### Fase 3: Features Novas (20 min)
- [ ] Implementar tool usage display com metadata
- [ ] Adicionar indicadores visuais para MCP tools
- [ ] Testar pensamentos intermediários

### Fase 4: CSS & Themes (15 min)
- [ ] Validar que CSS customizado ainda funciona
- [ ] Testar heroic_theme.py
- [ ] Verificar responsividade mobile

### Fase 5: Testes (20 min)
- [ ] Testar streaming de mensagens
- [ ] Testar hero state
- [ ] Testar MCP tools display
- [ ] Testar em mobile (responsive)
- [ ] Validar terminal output

### Fase 6: Deploy (10 min)
- [ ] Commit e push
- [ ] Merge para main
- [ ] Atualizar documentação

**Tempo Total Estimado:** ~2 horas

---

## 🔧 Mudanças Necessárias no Código

### 1. `gradio_ui/app.py` - Função `stream_conversation()`

**ANTES:**
```python
def stream_conversation(
    message: str,
    history: List[Dict[str, str]],
    session_value: str
) -> Generator:
    # ...
    history.append({"role": "user", "content": message})
    history.append({"role": "assistant", "content": ""})
    
    for chunk in _bridge.stream(message):
        live_text += chunk
        history[-1]["content"] = live_text + " ▌"
        yield history, terminal_output, session_value, metrics, gr.update(visible=False)
    
    history[-1]["content"] = live_text
    yield history, terminal_output, session_value, final_metrics, gr.update(visible=False)
```

**DEPOIS:**
```python
from gradio import ChatMessage

def stream_conversation(
    message: str,
    history: List[ChatMessage],
    session_value: str
) -> Generator:
    # ...
    history.append(ChatMessage(
        role="user",
        content=[{"type": "text", "text": message}]
    ))
    history.append(ChatMessage(
        role="assistant",
        content=[{"type": "text", "text": ""}],
        metadata={"title": "🤖 Processing", "value": "Analyzing request..."}
    ))
    
    for chunk in _bridge.stream(message):
        live_text += chunk
        history[-1].content = [{"type": "text", "text": live_text + " ▌"}]
        yield history, terminal_output, session_value, metrics, gr.update(visible=False)
    
    history[-1].content = [{"type": "text", "text": live_text}]
    history[-1].metadata = None  # Remove processing indicator
    yield history, terminal_output, session_value, final_metrics, gr.update(visible=False)
```

---

### 2. `gradio_ui/app.py` - Adicionar Tool Usage Display

**NOVO:**
```python
def stream_conversation_with_tools(
    message: str,
    history: List[ChatMessage],
    session_value: str
) -> Generator:
    # ...
    
    # Mostrar quando uma tool MCP é executada
    if tool_name:
        history.append(ChatMessage(
            role="assistant",
            content=[{"type": "text", "text": f"Executing {tool_name}..."}],
            metadata={
                "title": f"🔧 MCP Tool: {tool_name}",
                "value": f"Parameters: {tool_params}"
            }
        ))
        yield history, ...
    
    # Resultado da tool
    history.append(ChatMessage(
        role="assistant",
        content=[{"type": "text", "text": tool_result}]
    ))
    yield history, ...
```

---

## 🎨 CSS & Themes

### Compatibilidade

✅ **CSS customizado:** Deve funcionar sem mudanças  
✅ **heroic_theme.py:** Compatível com Gradio 6  
✅ **polished.css:** Mantém funcionalidade  

### Novos Seletores CSS (Gradio 6)

```css
/* Tool usage metadata display */
.chatbot .metadata-container {
    background: var(--color-bg-subtle) !important;
    border-left: 3px solid var(--color-accent) !important;
    padding: var(--space-md) !important;
    border-radius: var(--radius-md) !important;
    margin: var(--space-sm) 0 !important;
}

.chatbot .metadata-title {
    font-weight: 600 !important;
    font-size: 12px !important;
    color: var(--color-text) !important;
    margin-bottom: var(--space-xs) !important;
}

.chatbot .metadata-value {
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 11px !important;
    color: var(--color-text-muted) !important;
}
```

---

## 🚨 Riscos & Mitigações

| Risco | Probabilidade | Impacto | Mitigação |
|-------|---------------|---------|-----------|
| Breaking changes não documentados | Média | Alto | Testar extensivamente antes de merge |
| CSS quebrado | Baixa | Médio | Validar todos os componentes visualmente |
| Streaming não funcionar | Baixa | Alto | Testar com diferentes tipos de mensagens |
| Performance degradada | Baixa | Médio | Benchmark antes e depois |

---

## 📚 Recursos

- [Gradio 6 Migration Guide](https://www.gradio.app/main/guides/gradio-6-migration-guide)
- [Gradio 6 Changelog](https://www.gradio.app/changelog)
- [Gradio 6 Docs](https://www.gradio.app/docs)
- [GitHub Milestone](https://github.com/gradio-app/gradio/milestone/29)

---

## ✅ Critérios de Sucesso

1. ✅ Servidor inicia sem erros
2. ✅ Chat funciona com streaming
3. ✅ Hero state renderiza corretamente
4. ✅ MCP tools table visível
5. ✅ Terminal output funciona
6. ✅ CSS aplicado corretamente
7. ✅ Responsivo em mobile
8. ✅ Tool usage display funciona (novo!)

---

## 🎯 Próximos Passos

1. **AGORA:** Estudar documentação Gradio 6
2. **Depois:** Criar branch e começar migração
3. **Então:** Testar extensivamente
4. **Finalmente:** Deploy e validação

---

**Pronto para começar a migração?** 🚀




