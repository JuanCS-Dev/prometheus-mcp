# 🚨 ANÁLISE: Loop Infinito e Tela Piscando

**Data**: 2025-11-24 11:38
**Severidade**: 🔴 **CRÍTICA**
**Status**: Identificado - Aguardando Fix

---

## 📸 Evidência dos Screenshots

### Sequência de Eventos

1. **11:38:17** - CODE EXECUTOR mostrando "🤔 Thinking..."
2. **11:38:24** - Output do comando echo começando a aparecer
3. **11:38:31** - Output completo visível
4. **11:38:40** - "🔒 Validating security..." aparecem
5. **11:38:47** - **⏳ Awaiting approval...** → **TRAVAMENTO**

### Observações Críticas

- ✅ PLANNER panel vazio (ESPERADO - comando foi para EXECUTOR)
- ❌ Tela piscando violentamente
- ❌ Não retornou ao prompt
- ❌ Usuário não conseguiu interagir

---

## 🔍 PROBLEMA 1: PLANNER Vazio (Não é Bug!)

### Por que o PLANNER ficou vazio?

**Comando do usuário**: `"gere uma receita premium de miojo"`

**Roteamento do Orchestrator** (maestro_v10_integrated.py:130-193):

```python
def route(self, prompt: str) -> str:
    p = prompt.lower()

    # PRIORITY 1: Explicit routing
    # ...

    # PRIORITY 5: Planning
    if any(w in p for w in ['break down', 'strategy', 'roadmap', 'sop', 'how to']):
        return 'planner'

    if 'plan' in p and 'deploy' not in p:
        return 'planner'

    # Default: Executor
    return 'executor'  # ← "gere" cai aqui!
```

**Resultado**:
- Comando roteado para `EXECUTOR` (NextGenExecutorAgent)
- PLANNER nunca foi chamado
- Por isso o panel ficou vazio

**Isto NÃO é um bug do streaming** - o streaming do PlannerAgent está funcionando, apenas não foi testado!

### Como Testar o PLANNER Corretamente

Use comandos que ativam o roteamento para planner:

```bash
# ✅ Estes comandos vão para PLANNER
"create a plan for user authentication"
"break down this task into steps"
"what's the strategy for this feature?"
"generate a roadmap for migration"
"how to implement authentication?"

# ❌ Estes comandos vão para EXECUTOR
"gere uma receita de miojo"
"execute ls"
"run this command"
"show me files"
```

---

## 🔴 PROBLEMA 2: Loop Infinito / Tela Piscando (BUG CRÍTICO!)

### Causa Raiz

**Conflito entre duas operações síncronas**:

1. **Live Display** rodando em background (30 FPS)
   - `MaestroShellUI` atualizando constantemente
   - `StreamingResponseDisplay` renderizando
   - Loop em `asyncio` atualizando a cada 33ms

2. **Approval Input** tentando ler do terminal
   - `console.input()` chamado (BLOQUEANTE)
   - Esperando resposta do usuário (y/n/a)
   - Mas o Live display continua redesenhando a tela!

**Resultado**:
- Tela é redesenhada 30x por segundo **enquanto aguarda input**
- Input fica "perdido" ou invisível
- Usuário não vê o prompt de aprovação
- Sistema trava esperando input que nunca chega

### Código Problemático

**maestro_v10_integrated.py:745-780** (aproximado):

```python
async def _request_approval(self, command: str) -> bool:
    """Request approval - PROBLEMA AQUI!"""

    # Mostra o painel de aprovação
    self.c.print(panel)

    loop = asyncio.get_event_loop()

    while True:
        # ❌ PROBLEMA: Live display continua rodando!
        response = await loop.run_in_executor(
            None,
            lambda: self.c.input("Allow? [y/n/a]: ")  # BLOQUEIA
        )
        # ...
```

**Enquanto isso, em paralelo**:

```python
# Linha ~1299
async for update in self.orch.execute_streaming(q, ...):
    # ❌ PROBLEMA: Continua atualizando UI em 30 FPS!
    await self.maestro_ui.update_agent_stream(agent_name, token)
    await asyncio.sleep(0.01)  # Smooth 100 tokens/s
```

### Por que Causa Tela Piscando?

1. `console.input()` espera input
2. Live display redesenha tela (30 FPS)
3. Prompt de input é sobrescrito
4. Terminal fica em estado inconsistente
5. Tela "pisca" com cada redesenho
6. Input nunca é visível para o usuário

---

## 🔧 SOLUÇÕES

### Solução Imediata (Workaround)

**Desabilitar streaming durante approval**:

```python
async def _request_approval(self, command: str) -> bool:
    """Request approval with Live display paused"""

    # 1. PAUSE live display
    if hasattr(self, 'maestro_ui') and self.maestro_ui:
        self.maestro_ui.pause()  # Implementar este método

    # 2. Limpar terminal
    self.c.clear()

    # 3. Mostrar painel de aprovação
    self.c.print(panel)

    # 4. Obter resposta
    response = await loop.run_in_executor(...)

    # 5. RESUME live display
    if hasattr(self, 'maestro_ui') and self.maestro_ui:
        self.maestro_ui.resume()

    return approved
```

### Solução Definitiva (Arquitetural)

**Usar Modal Pattern**:

```python
class ApprovalModal:
    """Modal que pausa TUDO e pede aprovação"""

    async def show(self, command: str) -> bool:
        # 1. Salvar estado atual da UI
        # 2. Limpar terminal
        # 3. Mostrar APENAS o modal
        # 4. Aguardar resposta
        # 5. Restaurar UI
        pass
```

### Solução Alternativa (Non-Blocking UI)

**Usar TUI library com input não-bloqueante**:

- `prompt_toolkit` com custom key bindings
- `textual` framework
- `urwid` com main loop próprio

---

## 📊 Impacto

### Severidade: 🔴 CRÍTICA

**Motivo**: Usuário não consegue aprovar comandos → Sistema inutilizável

**Afeta**:
- ✅ Todos os comandos que requerem aprovação
- ✅ Qualquer operação "perigosa" (rm, git push, etc)
- ✅ 100% dos usuários em modo STANDARD security

**Não afeta**:
- ❌ Comandos que não requerem aprovação
- ❌ Modo PERMISSIVE (se existir)

### Frequência

- **100%** dos comandos que requerem aprovação
- **Reproduzível**: Sempre que approval é solicitado durante streaming

---

## 🎯 Ação Requerida

### Prioridade 1 (URGENTE)

1. **Implementar pause/resume no MaestroShellUI**
   ```python
   class MaestroShellUI:
       def pause(self):
           """Stop all live updates"""
           self._paused = True

       def resume(self):
           """Resume live updates"""
           self._paused = False
   ```

2. **Modificar _request_approval para usar pause/resume**

### Prioridade 2 (Médio Prazo)

3. **Implementar ApprovalModal dedicado**
4. **Migrar para TUI framework não-bloqueante**

### Prioridade 3 (Longo Prazo)

5. **Redesign: Approval como evento assíncrono**
   - Mostrar botões na UI
   - Capturar teclas sem bloquear
   - Manter streaming rodando

---

## 🧪 Como Reproduzir

```bash
./maestro

# Digite qualquer comando que requer aprovação:
> gere uma receita premium de miojo
> rm -rf /tmp/test
> git push --force

# Resultado:
# - Tela pisca violentamente
# - "⏳ Awaiting approval..." aparece
# - Prompt de input NÃO aparece ou fica invisível
# - Sistema trava
# - Ctrl+C necessário para sair
```

---

## 📝 Notas Técnicas

### Por que Live Display Não Para?

O `asyncio` task do Live display está em um loop separado:

```python
async def _update_loop(self):
    while self.running:
        self.render()
        await asyncio.sleep(1/30)  # 30 FPS
```

Quando `_request_approval()` é chamado:
1. É um `await` que bloqueia aquela coroutine
2. MAS o event loop do asyncio continua rodando
3. `_update_loop()` continua executando
4. Tela continua sendo redesenhada

### Por que console.input() Não Funciona?

`rich.Console.input()` usa `input()` do Python:
- **Bloqueante**: Para o thread até receber \n
- **Não é async-aware**: Não coopera com asyncio
- **Não tem controle sobre terminal**: Live display sobrescreve

---

## ✅ Confirmação

- [x] Problema reproduzível
- [x] Causa raiz identificada
- [x] Soluções propostas
- [ ] Fix implementado
- [ ] Testado e validado

---

**Próximo passo**: Implementar pause/resume no MaestroShellUI URGENTEMENTE
