# 📦 Arquivos Necessários para Fix do Loop Infinito

## 🎯 Problema a Resolver

**Loop infinito com tela piscando** quando sistema solicita aprovação durante streaming.

---

## 📁 Arquivos que Devem Ser Anexados

### 1. **Documentação e Análise**

#### `LOOP_INFINITO_ANALYSIS.md` ⭐ **COMECE AQUI**
- Análise completa do problema
- Causa raiz identificada
- 3 soluções propostas com código
- Como reproduzir

#### `STREAMING_FIX_APPLIED.md`
- Contexto do streaming implementado
- O que já foi feito (PlannerAgent)
- Estado atual do sistema

---

### 2. **Arquivos de Código (Para Referência)**

#### `maestro_v10_integrated.py` ⚠️ **CRÍTICO**
- **Linhas críticas**: 745-780 (`_request_approval`)
- **Linhas críticas**: 680-810 (MaestroShell.__init__)
- **Linhas críticas**: 1299+ (loop de streaming)
- **O que fazer**: Implementar pause/resume

#### `qwen_dev_cli/tui/components/maestro_shell_ui.py` ⚠️ **CRÍTICO**
- **Componente**: `MaestroShellUI`
- **O que fazer**: Adicionar métodos `pause()` e `resume()`
- **Onde**: Classe principal que gerencia Live display

#### `qwen_dev_cli/agents/executor_nextgen.py` (Referência)
- **Linhas**: 600-620 (onde chama approval)
- **Não precisa modificar** - apenas entender o fluxo

---

### 3. **Arquivos de Teste**

#### `test_streaming_e2e.py`
- Testes que validam streaming
- Pode ser adaptado para testar approval

---

## 🔧 Modificações Necessárias

### Arquivo 1: `qwen_dev_cli/tui/components/maestro_shell_ui.py`

**Adicionar métodos**:

```python
class MaestroShellUI:
    def __init__(self, ...):
        # ...
        self._paused = False
        self._pause_event = asyncio.Event()
        self._pause_event.set()  # Not paused initially

    def pause(self):
        """Pause all live updates (for modal interactions)"""
        self._paused = True
        self._pause_event.clear()

    def resume(self):
        """Resume live updates"""
        self._paused = False
        self._pause_event.set()

    async def _update_loop(self):
        """Main update loop"""
        while self.running:
            # Wait if paused
            await self._pause_event.wait()

            if not self._paused:
                self.render()
                await asyncio.sleep(1/30)  # 30 FPS
```

---

### Arquivo 2: `maestro_v10_integrated.py`

**Modificar `_request_approval` method**:

```python
async def _request_approval(self, command: str) -> bool:
    """Request user approval for command execution (async).

    FIXED: Now pauses Live display to prevent screen flickering.
    """
    # 1. PAUSE live display
    if hasattr(self, 'maestro_ui') and self.maestro_ui:
        self.maestro_ui.pause()
        await asyncio.sleep(0.1)  # Let it settle

    # 2. Clear and show approval panel
    self.c.clear()
    self.c.print()
    panel = Panel(
        Text(command, style="bright_yellow"),
        title="[bold bright_red]⚠️  APPROVAL REQUIRED[/bold bright_red]",
        border_style="bright_red",
        padding=(1, 2)
    )
    self.c.print(panel)
    self.c.print()
    self.c.print("[dim]This command requires your approval to execute.[/dim]")
    self.c.print("[dim]Options: [bright_green][y]es[/bright_green] | [bright_red][n]o[/bright_red] | [bright_cyan][a]lways allow this command[/bright_cyan][/dim]")
    self.c.print()

    loop = asyncio.get_event_loop()

    try:
        while True:
            # Non-blocking input
            response = await loop.run_in_executor(
                None,
                lambda: self.c.input("[bold bright_yellow]Allow this command? [y/n/a]:[/bold bright_yellow] ")
            )
            response = response.strip().lower()

            if response in ['y', 'yes']:
                self._last_approval_always = False
                self.c.print("[green]✅ Approved (this time only)[/green]\n")
                return True
            elif response in ['n', 'no']:
                self._last_approval_always = False
                self.c.print("[red]❌ Denied[/red]\n")
                return False
            elif response in ['a', 'always']:
                self._last_approval_always = True
                self.c.print("[cyan]✅ Always allowed[/cyan]\n")
                return True
            else:
                self.c.print("[yellow]Invalid input. Please enter y, n, or a.[/yellow]")

    finally:
        # 3. ALWAYS resume live display (even on exception)
        if hasattr(self, 'maestro_ui') and self.maestro_ui:
            self.maestro_ui.resume()
```

---

## ✅ Checklist de Implementação

### Fase 1: Preparação (5 min)
- [ ] Ler `LOOP_INFINITO_ANALYSIS.md` completamente
- [ ] Fazer backup dos arquivos que serão modificados
- [ ] Confirmar estrutura de `MaestroShellUI`

### Fase 2: Implementação (15 min)
- [ ] Adicionar `pause()` e `resume()` em `MaestroShellUI`
- [ ] Adicionar `_paused` e `_pause_event` no `__init__`
- [ ] Modificar `_update_loop()` para respeitar pause
- [ ] Modificar `_request_approval()` para usar pause/resume
- [ ] Adicionar `try/finally` para garantir resume

### Fase 3: Teste (10 min)
- [ ] Executar `./maestro`
- [ ] Testar comando: `"gere uma receita de miojo"`
- [ ] Verificar que approval aparece **SEM piscar**
- [ ] Testar resposta "y" (aprovar)
- [ ] Testar resposta "n" (negar)
- [ ] Testar resposta "a" (always allow)
- [ ] Verificar que streaming resume após aprovação

### Fase 4: Validação (5 min)
- [ ] Tela NÃO pisca durante approval
- [ ] Prompt de input é visível
- [ ] Sistema retorna ao prompt após aprovação/negação
- [ ] Streaming continua normalmente após approval

---

## 🧪 Como Testar

### Teste 1: Approval Básico
```bash
./maestro

# Digite comando que requer aprovação
> gere uma receita de miojo

# Resultado esperado:
# 1. Streaming aparece (thinking...)
# 2. Tela PARA (não pisca)
# 3. Painel de approval aparece claramente
# 4. Prompt "Allow? [y/n/a]:" está visível
# 5. Resposta é lida corretamente
# 6. Streaming resume (se aprovado)
# 7. Sistema retorna ao prompt
```

### Teste 2: Sempre Permitir
```bash
> gere outra receita

# Responda: a (always)

# Resultado esperado:
# - Comando salvo em allowlist
# - Próximas execuções não pedem approval
```

### Teste 3: Negar
```bash
> rm -rf /tmp/test

# Responda: n (no)

# Resultado esperado:
# - Comando não executado
# - Mensagem "❌ Denied"
# - Sistema retorna ao prompt
```

---

## 📊 Arquivos no Pacote (Resumo)

```
fix-loop-infinito/
├── LOOP_INFINITO_ANALYSIS.md          ← ⭐ LEIA PRIMEIRO
├── ARQUIVOS_PARA_FIX_LOOP.md          ← ESTE ARQUIVO
├── STREAMING_FIX_APPLIED.md           ← Contexto
├── maestro_v10_integrated.py          ← MODIFICAR (_request_approval)
├── qwen_dev_cli/
│   ├── tui/
│   │   └── components/
│   │       └── maestro_shell_ui.py    ← MODIFICAR (pause/resume)
│   └── agents/
│       └── executor_nextgen.py        ← REFERÊNCIA (não modificar)
└── test_streaming_e2e.py              ← TESTE

Total: 7 arquivos
Modificações: 2 arquivos
Tempo estimado: 35 minutos
```

---

## 🎯 Ordem de Leitura

1. **`LOOP_INFINITO_ANALYSIS.md`** - Entender o problema
2. **`ARQUIVOS_PARA_FIX_LOOP.md`** (este arquivo) - Entender a solução
3. **`maestro_shell_ui.py`** - Ver onde adicionar pause/resume
4. **`maestro_v10_integrated.py`** - Ver onde modificar approval

---

## 🚀 Resultado Esperado

**ANTES** (Bug):
```
🤔 Thinking...
⏳ Awaiting approval...
[TELA PISCANDO VIOLENTAMENTE]
[SISTEMA TRAVADO]
[CTRL+C NECESSÁRIO]
```

**DEPOIS** (Corrigido):
```
🤔 Thinking...
⏳ Awaiting approval...

⚠️  APPROVAL REQUIRED
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃  echo "receita de miojo"  ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

Allow this command? [y/n/a]: y
✅ Approved

[STREAMING CONTINUA]
[RETORNA AO PROMPT]
```

---

**Implementado por**: Claude Code (Sonnet 4.5)
**Data de Análise**: 2025-11-24
**Prioridade**: 🔴 CRÍTICA
**Tempo estimado de fix**: 35 minutos
