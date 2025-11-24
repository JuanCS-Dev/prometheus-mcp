# 🎯 PHASE 5: Maestro Orchestration Integration - Plano de Execução

**Data**: 2025-11-24
**Status**: 🔵 EM PLANEJAMENTO
**Tempo Estimado**: 2-3 horas

---

## 📊 OBJETIVOS

Integrar Justiça e Sofia no pipeline de orquestração do Maestro para criar um sistema completo de governança e aconselhamento ético.

### Deliverables

1. ✅ **Pipeline de Governança Completo**: Justiça → Sofia → Agent
2. ✅ **Pre-Execution Hooks**: Chamadas automáticas antes de ações de risco
3. ✅ **Auto-Routing de Sofia**: Detecção automática de dilemas éticos
4. ✅ **Agent Registry**: Registro de Justiça e Sofia no Maestro
5. ✅ **Slash Commands**: `/sofia` e `/governance` integrados

---

## 🔍 ANÁLISE DO ESTADO ATUAL

### Arquitetura Maestro Atual

**Arquivo Principal**: `qwen_dev_cli/maestro.py`

**Estrutura**:
```
maestro.py (v7.0)
├── GlobalState (agents, context, llm_client, mcp_client)
├── Main app (AsyncTyper)
├── Sub-apps (agent_app, config_app)
└── Commands (explore, plan, review, etc.)
```

**Agents Registrados**:
- PlannerAgent
- ExplorerAgent
- ReviewerAgent

**Pipeline Atual**:
```
User Request → Maestro → Agent → Response → User
```

**Gaps Identificados**:
- ❌ Nenhuma governança antes de execução
- ❌ Nenhum aconselhamento ético
- ❌ Justiça e Sofia não registrados
- ❌ Nenhum hook de pre-execution
- ❌ Slash commands `/sofia` e `/governance` ausentes

---

## 🎯 PIPELINE DESEJADO (Phase 5)

```
User Request
    ↓
Maestro Receives Request
    ↓
[GOVERNANCE LAYER - Phase 5.3]
    ↓
Justiça.evaluate_action()
    ├─ APPROVED → Continue
    ├─ WARNING → Log + Continue
    └─ BLOCKED → Return Error to User
    ↓
[ETHICAL COUNSEL LAYER - Phase 5.4]
    ↓
Check if ethical dilemma (Sofia.should_trigger_counsel())
    ├─ YES → Sofia.provide_counsel_async()
    │         Present counsel to user
    │         Ask confirmation
    └─ NO → Skip
    ↓
[EXECUTION LAYER]
    ↓
Route to appropriate agent (Planner, Explorer, etc.)
    ↓
Agent.execute()
    ↓
[POST-EXECUTION]
    ↓
Update trust scores (Justiça)
    ↓
Return Response to User
```

---

## 📋 TASKS DETALHADAS

### Task 5.1: Analyze Maestro Architecture ✅ (CONCLUÍDO)

**Objetivo**: Entender estrutura atual do Maestro

**Descobertas**:
- Maestro usa AsyncTyper (async-first)
- GlobalState gerencia agents e clients
- Agents registrados em `state.agents`
- Commands são funções async decoradas com `@app.command()`

**Arquivos-chave**:
- `qwen_dev_cli/maestro.py` - Main orchestrator
- `qwen_dev_cli/agents/base.py` - BaseAgent interface
- `qwen_dev_cli/agents/planner.py` - Example agent

---

### Task 5.2: Create Governance Pipeline Integration Plan ⏳

**Objetivo**: Projetar como Justiça e Sofia se integram ao Maestro

**Subtasks**:

#### 5.2.1: Define Governance Hook Interface
```python
# qwen_dev_cli/core/governance_pipeline.py (NEW FILE)

from typing import Optional, Tuple
from qwen_dev_cli.agents.justica_agent import JusticaIntegratedAgent
from qwen_dev_cli.agents.sofia_agent import SofiaIntegratedAgent
from qwen_dev_cli.agents.base import AgentTask, AgentResponse

class GovernancePipeline:
    """
    Pipeline de governança para Maestro.

    Executa Justiça (governança) e Sofia (aconselhamento ético)
    antes de qualquer execução de agente.
    """

    def __init__(
        self,
        justica: JusticaIntegratedAgent,
        sofia: SofiaIntegratedAgent,
        enable_governance: bool = True,
        enable_counsel: bool = True
    ):
        self.justica = justica
        self.sofia = sofia
        self.enable_governance = enable_governance
        self.enable_counsel = enable_counsel

    async def pre_execution_check(
        self,
        task: AgentTask,
        agent_id: str,
        risk_level: str = "MEDIUM"
    ) -> Tuple[bool, Optional[str]]:
        """
        Executa governança e aconselhamento antes de uma ação.

        Returns:
            (approved: bool, reason: Optional[str])
        """
        # Phase 1: Governance (Justiça)
        if self.enable_governance:
            verdict = await self.justica.evaluate_action(
                agent_id=agent_id,
                action_description=task.request,
                context=task.context
            )

            if not verdict.success:
                return False, verdict.error

        # Phase 2: Ethical Counsel (Sofia)
        if self.enable_counsel:
            should_counsel, reason = self.sofia.should_trigger_counsel(task.request)

            if should_counsel:
                counsel = await self.sofia.pre_execution_counsel(
                    action_description=task.request,
                    risk_level=risk_level,
                    agent_id=agent_id
                )

                # TODO: Present counsel to user, ask confirmation
                # For now, just log
                print(f"⚠️  Sofia Counsel: {counsel.counsel}")

        return True, None
```

#### 5.2.2: Update GlobalState to Include Governance
```python
# qwen_dev_cli/maestro.py

class GlobalState:
    def __init__(self):
        self.agents = {}
        self.context = {}
        self.initialized = False
        self.llm_client = None
        self.mcp_client = None

        # NEW: Governance components
        self.justica = None
        self.sofia = None
        self.governance_pipeline = None
```

#### 5.2.3: Initialize Governance in Maestro
```python
# qwen_dev_cli/maestro.py

async def initialize_system():
    """Initialize LLM, MCP, and agents"""
    global state

    if state.initialized:
        return

    try:
        # Existing initialization
        state.llm_client = LLMClient()
        state.mcp_client = MCPClient()

        # NEW: Initialize governance agents
        from qwen_dev_cli.agents.justica_agent import JusticaIntegratedAgent
        from qwen_dev_cli.agents.sofia_agent import SofiaIntegratedAgent
        from qwen_dev_cli.core.governance_pipeline import GovernancePipeline
        from qwen_dev_cli.agents.base import AgentCapability

        state.justica = JusticaIntegratedAgent(
            llm_client=state.llm_client,
            mcp_client=state.mcp_client,
            capabilities=[AgentCapability.READ_ONLY],
            verbose_ui=True
        )

        state.sofia = SofiaIntegratedAgent(
            llm_client=state.llm_client,
            mcp_client=state.mcp_client,
            auto_detect_ethical_dilemmas=True
        )

        state.governance_pipeline = GovernancePipeline(
            justica=state.justica,
            sofia=state.sofia
        )

        # Register in agents dict
        state.agents['governance'] = state.justica
        state.agents['counselor'] = state.sofia

        state.initialized = True
        console.print("✅ System initialized with governance", style="green")

    except Exception as e:
        console.print(f"❌ Initialization failed: {e}", style="red")
        raise
```

---

### Task 5.3: Implement Pre-Execution Hooks ⏳

**Objetivo**: Adicionar chamadas de governança antes de cada execução de agente

**Subtasks**:

#### 5.3.1: Create Pre-Execution Wrapper
```python
# qwen_dev_cli/core/governance_pipeline.py

async def execute_with_governance(
    agent: BaseAgent,
    task: AgentTask,
    pipeline: GovernancePipeline,
    risk_level: str = "MEDIUM"
) -> AgentResponse:
    """
    Executa agente com governança completa.

    Pipeline:
    1. Justiça evaluate_action
    2. Sofia pre_execution_counsel (if needed)
    3. Agent.execute
    4. Update trust scores
    """

    # Phase 1: Pre-execution checks
    approved, reason = await pipeline.pre_execution_check(
        task=task,
        agent_id=agent.role.value,
        risk_level=risk_level
    )

    if not approved:
        return AgentResponse(
            success=False,
            reasoning="Governance check failed",
            error=reason
        )

    # Phase 2: Execute agent
    try:
        response = await agent.execute(task)
        return response
    except Exception as e:
        return AgentResponse(
            success=False,
            reasoning=f"Execution failed: {str(e)}",
            error=str(e)
        )
```

#### 5.3.2: Update Agent Commands to Use Governance
```python
# qwen_dev_cli/maestro.py

@app.command()
async def explore(
    path: str = typer.Argument(..., help="Path to explore"),
    depth: int = typer.Option(2, help="Exploration depth")
):
    """🔍 Explore codebase structure"""
    await initialize_system()

    explorer = ExplorerAgent(state.llm_client, state.mcp_client)

    task = AgentTask(
        task_id=str(uuid.uuid4()),
        request=f"Explore {path} with depth {depth}",
        context={"path": path, "depth": depth}
    )

    # NEW: Execute with governance
    response = await execute_with_governance(
        agent=explorer,
        task=task,
        pipeline=state.governance_pipeline,
        risk_level="LOW"  # Exploration is low risk
    )

    if not response.success:
        console.print(f"❌ {response.error}", style="red")
        return

    # Display results
    console.print(response.data)
```

---

### Task 5.4: Add Sofia Auto-Routing ⏳

**Objetivo**: Rotear automaticamente dilemas éticos para Sofia

**Subtasks**:

#### 5.4.1: Create Ethical Dilemma Detector
```python
# qwen_dev_cli/core/governance_pipeline.py

def is_ethical_dilemma(request: str) -> bool:
    """
    Detecta se uma requisição é um dilema ético.

    Usa Sofia.should_trigger_counsel() como base.
    """
    # Keywords que indicam dilema ético
    ethical_keywords = [
        "should i", "is it okay", "right or wrong",
        "ethical", "moral", "conscience",
        "devo fazer", "é certo", "correto fazer"
    ]

    request_lower = request.lower()
    return any(keyword in request_lower for keyword in ethical_keywords)
```

#### 5.4.2: Add Sofia Command
```python
# qwen_dev_cli/maestro.py

@app.command()
async def sofia(
    query: str = typer.Argument(..., help="Question for Sofia")
):
    """🦉 Ask Sofia for ethical counsel"""
    await initialize_system()

    from rich.panel import Panel

    console.print(Panel.fit(
        "🦉 Sofia - Conselheiro Sábio",
        style="cyan"
    ))

    # Provide counsel
    response = await state.sofia.provide_counsel_async(query)

    # Display
    console.print(f"\n[bold cyan]Query:[/bold cyan] {response.original_query}")
    console.print(f"[bold cyan]Counsel Type:[/bold cyan] {response.counsel_type}")
    console.print(f"[bold cyan]Thinking Mode:[/bold cyan] {response.thinking_mode}")

    if response.questions_asked:
        console.print(f"\n[bold cyan]Questions Asked ({len(response.questions_asked)}):[/bold cyan]")
        for i, q in enumerate(response.questions_asked, 1):
            console.print(f"  {i}. {q}")

    console.print(f"\n[bold yellow]Counsel:[/bold yellow]")
    console.print(response.counsel)

    if response.requires_professional:
        console.print("\n[bold red]⚠️  URGENT: This situation requires professional help.[/bold red]")

    console.print(f"\n[dim]Confidence: {response.confidence:.0%} | Processing: {response.processing_time_ms:.1f}ms[/dim]")
```

#### 5.4.3: Add Governance Command
```python
# qwen_dev_cli/maestro.py

@app.command()
async def governance(
    agent_id: str = typer.Argument(..., help="Agent ID to check")
):
    """🛡️ Check governance metrics for an agent"""
    await initialize_system()

    metrics = state.justica.get_metrics(agent_id)

    # Display metrics table
    table = Table(title=f"Governance Metrics: {agent_id}")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Trust Score", f"{metrics.trust_score:.2f}")
    table.add_row("Trust Level", metrics.trust_level)
    table.add_row("Violations", str(metrics.violations_count))
    table.add_row("Actions", str(metrics.actions_count))
    table.add_row("Status", metrics.current_status)

    console.print(table)
```

---

### Task 5.5: Test Integration ⏳

**Objetivo**: Validar que toda a pipeline funciona end-to-end

**Subtasks**:

#### 5.5.1: Create Integration Tests
```python
# tests/test_maestro_governance_integration.py (NEW)

import pytest
from qwen_dev_cli.core.governance_pipeline import GovernancePipeline
from qwen_dev_cli.agents.justica_agent import JusticaIntegratedAgent
from qwen_dev_cli.agents.sofia_agent import SofiaIntegratedAgent

@pytest.mark.asyncio
async def test_governance_pipeline_approves_safe_action():
    """Test que ação segura é aprovada"""
    # Setup
    justica = create_mock_justica()
    sofia = create_mock_sofia()
    pipeline = GovernancePipeline(justica, sofia)

    task = AgentTask(
        task_id="test-1",
        request="Read file contents",
        context={}
    )

    # Execute
    approved, reason = await pipeline.pre_execution_check(
        task, agent_id="test-agent", risk_level="LOW"
    )

    # Assert
    assert approved is True
    assert reason is None

@pytest.mark.asyncio
async def test_governance_pipeline_blocks_violation():
    """Test que violação é bloqueada"""
    # Similar test, expect approved=False
    pass

# TODO: 10+ integration tests
```

#### 5.5.2: Manual Testing Checklist
```
[ ] maestro explore ./src (should pass governance)
[ ] maestro sofia "Should I delete user data?" (should provide counsel)
[ ] maestro governance executor-1 (should show metrics)
[ ] High-risk command triggers Sofia pre-execution counsel
[ ] Violation triggers Justiça block
[ ] Trust scores update after actions
```

---

## 📊 SUCCESS CRITERIA

### Functional

- [ ] Justiça registrado em `state.agents['governance']`
- [ ] Sofia registrado em `state.agents['counselor']`
- [ ] `GovernancePipeline` criado e funcional
- [ ] Pre-execution hooks executam antes de cada comando
- [ ] `/sofia` comando funciona
- [ ] `/governance` comando funciona
- [ ] Dilemas éticos auto-roteados para Sofia

### Performance

- [ ] Governança adiciona < 20ms latency
- [ ] Nenhum impacto em throughput
- [ ] UI permanece responsiva

### Quality

- [ ] 10+ integration tests passando
- [ ] Manual checklist 100% complete
- [ ] Nenhum crash durante operação normal

---

## 🗂️ FILES TO CREATE/MODIFY

### New Files

1. **`qwen_dev_cli/core/governance_pipeline.py`** (~200 lines)
   - `GovernancePipeline` class
   - `execute_with_governance()` function
   - `is_ethical_dilemma()` detector

2. **`tests/test_maestro_governance_integration.py`** (~300 lines)
   - 10+ integration tests

### Files to Modify

1. **`qwen_dev_cli/maestro.py`**
   - Add imports (Justiça, Sofia, GovernancePipeline)
   - Update `GlobalState` class
   - Update `initialize_system()` function
   - Add `/sofia` command
   - Add `/governance` command
   - Update existing commands (explore, plan, etc.) to use governance

---

## ⏱️ ESTIMATED TIME

| Task | Time | Complexity |
|------|------|------------|
| 5.1 Analysis | ✅ Done | LOW |
| 5.2 Planning | 30min | MEDIUM |
| 5.3 Pre-execution hooks | 60min | HIGH |
| 5.4 Sofia auto-routing | 30min | MEDIUM |
| 5.5 Testing | 45min | MEDIUM |
| **TOTAL** | **~3 hours** | - |

---

## 🚨 RISKS

### Risk 1: Performance Impact
**Mitigation**: Async throughout, caching, parallel execution

### Risk 2: False Positives (Blocking Valid Actions)
**Mitigation**: NORMATIVE mode (balanced), human review escalation

### Risk 3: Sofia Over-Questioning
**Mitigation**: Only trigger on HIGH/CRITICAL risk, user can disable

---

## 📝 NEXT STEPS

Após confirmar este plano:

1. ⏳ Implementar Task 5.2 (Planning & Design)
2. ⏳ Implementar Task 5.3 (Pre-execution Hooks)
3. ⏳ Implementar Task 5.4 (Sofia Routing)
4. ⏳ Implementar Task 5.5 (Testing)
5. ✅ Phase 5 Complete!

---

**Aguardando aprovação do usuário para iniciar implementação.**
