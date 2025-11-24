# 🎯 PHASE 5: Maestro Orchestration Integration - Plano Atualizado (V2)

**Data**: 2025-11-24
**Status**: 🔵 PLANEJAMENTO ATUALIZADO COM BEST PRACTICES NOV 2025
**Tempo Estimado**: 2-3 horas

---

## 📚 RESEARCH FINDINGS (Nov 2025)

Pesquisa realizada em documentação oficial da **Anthropic**, **Google Cloud**, e **MCP**:

### 🏆 Anthropic Multi-Agent Best Practices

**Orchestrator-Worker Architecture** ([Anthropic Research System](https://www.anthropic.com/engineering/multi-agent-research-system))
- Lead agent (Opus 4) coordena processo
- Subagents especializados (Sonnet 4) operam em **paralelo**
- **90.2% melhor performance** vs single-agent
- Context isolation: cada subagent tem sua própria janela de contexto

**Delegation Principles** ([Claude Agent SDK](https://www.anthropic.com/engineering/building-agents-with-the-claude-agent-sdk))
- Orchestrator: planning global, delegation, state management
- Permissions: **"read and route"** apenas (narrow scope)
- Subagents: inputs/outputs claros, single goal
- Boundaries explícitos entre agentes

**Enterprise Governance** ([IBM Partnership](https://newsroom.ibm.com/2025-10-07-2025-ibm-and-anthropic-partner-to-advance-enterprise-software-development-with-proven-security-and-governance))
- Security, governance, cost controls no lifecycle completo
- Explicit policies, approvals, human-in-the-loop controls
- Safe deployment, monitoring, operations at scale

### 🌐 Google Vertex AI Best Practices

**Agent Development Kit (ADK)** ([Google Cloud Blog](https://cloud.google.com/blog/products/ai-machine-learning/build-and-manage-multi-system-agents-with-vertex-ai))
- 7M+ downloads desde lançamento
- Framework-agnostic: LangGraph, Crew.ai, ADK
- Model-agnostic: Gemini, Claude, Mistral

**Agent Identities & IAM** ([Vertex AI Documentation](https://docs.cloud.google.com/agent-builder/overview))
- Agents são **first-class IAM principals**
- Least-privilege access via Cloud IAM
- Granular policies, resource boundaries
- Compliance requirements nativos

**Model Armor** ([InfoWorld](https://www.infoworld.com/article/4085736/google-boosts-vertex-ai-agent-builder-with-new-observability-and-deployment-tools.html))
- Protection contra prompt injection
- Screening de tool calls e responses
- Built-in inline protection + REST API

**Observability Dashboard** ([Google Developers Blog](https://developers.googleblog.com/en/agent-development-kit-easy-to-build-multi-agent-applications/))
- Real-time + retrospective debugging
- Agent-level tracing, tool auditing
- Orchestrator visualization
- Token usage, latency, error rates tracking

### 🔗 MCP (Model Context Protocol) Patterns

**Multi-Agent Orchestration** ([arXiv Paper](https://arxiv.org/html/2504.21030v1))
- **Vertical integration**: agents ↔ context/services
- **Horizontal integration**: agents ↔ agents coordination
- Security & governance layer cross-system
- Single audit trail across workflows

**Enterprise Requirements** ([MCP Guide](https://www.keywordsai.co/blog/introduction-to-mcp))
- OAuth 2.1 flows
- Audience-bound tokens
- Explicit consent everywhere
- Audit trails on all data/tool access

**2025 Standards** ([Wikipedia](https://en.wikipedia.org/wiki/Model_Context_Protocol))
- OpenAI adopted MCP (March 2025)
- Independent standards body in formation
- Maturing ecosystem: transport, security, governance

---

## 🎯 UPDATED ARCHITECTURE (Based on Research)

### Orchestrator-Worker Pattern

```
                    ┌─────────────────────┐
                    │   MAESTRO (Lead)    │
                    │  Orchestrator Agent │
                    │  "Read & Route"     │
                    └──────────┬──────────┘
                               │
              ┌────────────────┼────────────────┐
              │                │                │
              ▼                ▼                ▼
    ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
    │  JUSTIÇA        │ │     SOFIA       │ │  WORKER AGENTS  │
    │  (Governance)   │ │  (Counselor)    │ │  (Executor etc) │
    │                 │ │                 │ │                 │
    │  Narrow Scope:  │ │  Narrow Scope:  │ │  Narrow Scope:  │
    │  - Evaluate     │ │  - Counsel      │ │  - Execute      │
    │  - Block/Allow  │ │  - Question     │ │  - Read/Write   │
    │  - Track Trust  │ │  - Deliberate   │ │  - Tools        │
    └─────────────────┘ └─────────────────┘ └─────────────────┘
           │                    │                    │
           └────────────────────┴────────────────────┘
                               │
                    ┌──────────▼──────────┐
                    │   Observability     │
                    │   - Traces (OTel)   │
                    │   - Audit Trail     │
                    │   - Metrics         │
                    └─────────────────────┘
```

### Key Principles (From Research)

1. **Specialization**: Cada agent tem um único propósito claro
2. **Isolation**: Context windows separados, não compartilhados
3. **Narrow Permissions**: Apenas o necessário para sua função
4. **Observability**: Traces OpenTelemetry em todas as interações
5. **IAM Integration**: Agents como first-class principals
6. **Fail-Safe**: Governance bloqueia por padrão em erro

---

## 📋 UPDATED TASKS (Based on Best Practices)

### Task 5.2: Create Governance Pipeline (UPDATED)

**Novo Design**: Orchestrator-Worker com Context Isolation

#### 5.2.1: GovernancePipeline com Observability
```python
# qwen_dev_cli/core/governance_pipeline.py

from typing import Optional, Tuple, Dict, Any
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode
import uuid

tracer = trace.get_tracer(__name__)

class GovernancePipeline:
    """
    Orchestrator-Worker pattern para governança.

    Baseado em:
    - Anthropic multi-agent research system
    - Google Vertex AI Agent Builder
    - MCP governance patterns

    Principles:
    1. Narrow permissions ("read and route")
    2. Context isolation (cada agent tem sua janela)
    3. OpenTelemetry traces
    4. Fail-safe defaults
    """

    def __init__(
        self,
        justica: JusticaIntegratedAgent,
        sofia: SofiaIntegratedAgent,
        enable_governance: bool = True,
        enable_counsel: bool = True,
        enable_observability: bool = True
    ):
        self.justica = justica
        self.sofia = sofia
        self.enable_governance = enable_governance
        self.enable_counsel = enable_counsel
        self.enable_observability = enable_observability

        # Observability: correlation IDs across subagents
        self.correlation_id = None

    @tracer.start_as_current_span("governance_pipeline.pre_execution_check")
    async def pre_execution_check(
        self,
        task: AgentTask,
        agent_id: str,
        risk_level: str = "MEDIUM"
    ) -> Tuple[bool, Optional[str], Dict[str, Any]]:
        """
        Pre-execution governance check com observability.

        Returns:
            (approved: bool, reason: Optional[str], traces: Dict)
        """
        span = trace.get_current_span()
        correlation_id = str(uuid.uuid4())
        self.correlation_id = correlation_id

        span.set_attribute("correlation_id", correlation_id)
        span.set_attribute("agent_id", agent_id)
        span.set_attribute("risk_level", risk_level)

        traces = {
            "correlation_id": correlation_id,
            "governance_checks": [],
            "counsel_checks": []
        }

        try:
            # Phase 1: Governance (Justiça) - PARALLEL with context isolation
            if self.enable_governance:
                with tracer.start_as_current_span("governance.justica_check") as gov_span:
                    gov_span.set_attribute("agent", "justica")

                    # NARROW SCOPE: apenas evaluate_action
                    verdict = await self.justica.evaluate_action(
                        agent_id=agent_id,
                        action_description=task.request,
                        context={
                            **task.context,
                            "correlation_id": correlation_id
                        }
                    )

                    traces["governance_checks"].append({
                        "agent": "justica",
                        "approved": verdict.success,
                        "trust_score": verdict.data.get("trust_score") if verdict.success else 0.0,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    })

                    if not verdict.success:
                        span.set_status(Status(StatusCode.ERROR, "Governance blocked"))
                        return False, verdict.error, traces

            # Phase 2: Ethical Counsel (Sofia) - PARALLEL with context isolation
            if self.enable_counsel:
                with tracer.start_as_current_span("governance.sofia_check") as counsel_span:
                    counsel_span.set_attribute("agent", "sofia")

                    # NARROW SCOPE: apenas should_trigger + pre_execution_counsel
                    should_counsel, reason = self.sofia.should_trigger_counsel(task.request)

                    if should_counsel and risk_level in ["HIGH", "CRITICAL"]:
                        counsel = await self.sofia.pre_execution_counsel(
                            action_description=task.request,
                            risk_level=risk_level,
                            agent_id=agent_id,
                            context={
                                **task.context,
                                "correlation_id": correlation_id
                            }
                        )

                        traces["counsel_checks"].append({
                            "agent": "sofia",
                            "triggered": True,
                            "counsel_type": counsel.counsel_type,
                            "confidence": counsel.confidence,
                            "requires_professional": counsel.requires_professional,
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        })

                        # Human-in-the-loop: requires_professional → escalate
                        if counsel.requires_professional:
                            span.set_status(Status(StatusCode.ERROR, "Professional referral required"))
                            return False, "Professional counseling required - action blocked", traces

            span.set_status(Status(StatusCode.OK))
            return True, None, traces

        except Exception as e:
            span.set_status(Status(StatusCode.ERROR, str(e)))
            span.record_exception(e)

            # FAIL-SAFE: block on error
            return False, f"Governance pipeline error: {str(e)}", traces
```

#### 5.2.2: Agent Identity & IAM (Google Vertex AI Pattern)
```python
# qwen_dev_cli/core/agent_identity.py (NEW)

from enum import Enum
from typing import Set, List

class AgentPermission(str, Enum):
    """
    Permissions baseadas em least-privilege (Google Cloud IAM pattern).
    """
    READ_FILES = "read_files"
    WRITE_FILES = "write_files"
    EXECUTE_COMMANDS = "execute_commands"
    NETWORK_ACCESS = "network_access"
    READ_SECRETS = "read_secrets"
    EVALUATE_GOVERNANCE = "evaluate_governance"  # Justiça only
    PROVIDE_COUNSEL = "provide_counsel"          # Sofia only

class AgentIdentity:
    """
    First-class IAM principal para agents (Google pattern).

    Cada agent tem:
    - Unique ID
    - Role (GOVERNANCE, COUNSELOR, EXECUTOR, etc.)
    - Permissions (least-privilege)
    - Resource boundaries
    """

    def __init__(
        self,
        agent_id: str,
        role: AgentRole,
        permissions: Set[AgentPermission]
    ):
        self.agent_id = agent_id
        self.role = role
        self.permissions = permissions

    def can(self, permission: AgentPermission) -> bool:
        """Check if agent has permission."""
        return permission in self.permissions

    def enforce(self, required: AgentPermission) -> None:
        """Enforce permission or raise exception."""
        if not self.can(required):
            raise PermissionError(
                f"Agent {self.agent_id} ({self.role.value}) lacks permission: {required.value}"
            )

# Agent identity registry
AGENT_IDENTITIES = {
    "governance": AgentIdentity(
        agent_id="governance",
        role=AgentRole.GOVERNANCE,
        permissions={
            AgentPermission.READ_FILES,      # Read contexts
            AgentPermission.EVALUATE_GOVERNANCE  # Evaluate only
        }
    ),
    "counselor": AgentIdentity(
        agent_id="counselor",
        role=AgentRole.COUNSELOR,
        permissions={
            AgentPermission.READ_FILES,      # Read contexts
            AgentPermission.PROVIDE_COUNSEL  # Counsel only
        }
    ),
    "executor": AgentIdentity(
        agent_id="executor",
        role=AgentRole.EXECUTOR,
        permissions={
            AgentPermission.READ_FILES,
            AgentPermission.WRITE_FILES,
            AgentPermission.EXECUTE_COMMANDS,
            AgentPermission.NETWORK_ACCESS
        }
    )
}
```

#### 5.2.3: OpenTelemetry Observability (Anthropic + Google Pattern)
```python
# qwen_dev_cli/core/observability.py (NEW)

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.instrumentation.logging import LoggingInstrumentor
import logging

def setup_observability(service_name: str = "maestro-orchestrator"):
    """
    Setup OpenTelemetry observability.

    Based on:
    - Anthropic: "capturing OpenTelemetry traces for prompts, tool invocations"
    - Google: "agent-level tracing, tool auditing, orchestrator visualization"
    """

    # Create resource
    resource = Resource.create({
        "service.name": service_name,
        "service.version": "1.0.0"
    })

    # Create tracer provider
    provider = TracerProvider(resource=resource)

    # Add console exporter for development
    console_exporter = ConsoleSpanExporter()
    provider.add_span_processor(BatchSpanProcessor(console_exporter))

    # Set global tracer provider
    trace.set_tracer_provider(provider)

    # Instrument logging
    LoggingInstrumentor().instrument(set_logging_format=True)

    logger = logging.getLogger(__name__)
    logger.info(f"✓ Observability initialized: {service_name}")
```

---

### Task 5.3: Pre-Execution Hooks (UPDATED)

**Novo**: Parallel execution, context isolation, fail-safe

#### 5.3.1: Parallel Execution Wrapper
```python
# qwen_dev_cli/core/governance_pipeline.py

import asyncio

async def execute_with_governance_parallel(
    agent: BaseAgent,
    task: AgentTask,
    pipeline: GovernancePipeline,
    risk_level: str = "MEDIUM"
) -> AgentResponse:
    """
    Execute agent com governança PARALELA.

    Based on Anthropic research: "subagents operate in parallel"

    Pipeline (PARALLEL):
    1. Justiça.evaluate_action() ──┐
    2. Sofia.should_trigger()      ├──→ await asyncio.gather()
                                   └──→ Results
    3. If all pass → Agent.execute()
    4. Update metrics (async background task)
    """

    with tracer.start_as_current_span("execute_with_governance") as span:
        span.set_attribute("agent_id", agent.role.value)
        span.set_attribute("risk_level", risk_level)

        # PHASE 1: Pre-execution checks (PARALLEL)
        approved, reason, traces = await pipeline.pre_execution_check(
            task=task,
            agent_id=agent.role.value,
            risk_level=risk_level
        )

        if not approved:
            span.set_status(Status(StatusCode.ERROR, reason))
            return AgentResponse(
                success=False,
                reasoning="Governance pipeline blocked action",
                error=reason,
                data={
                    "governance_traces": traces,
                    "blocked_by": "governance_pipeline"
                }
            )

        # PHASE 2: Execute agent (context isolated)
        try:
            with tracer.start_as_current_span(f"agent.{agent.role.value}.execute"):
                response = await agent.execute(task)

            # PHASE 3: Post-execution metrics (background task, non-blocking)
            asyncio.create_task(
                pipeline._update_metrics_async(
                    agent_id=agent.role.value,
                    success=response.success,
                    correlation_id=traces["correlation_id"]
                )
            )

            return response

        except Exception as e:
            span.set_status(Status(StatusCode.ERROR, str(e)))
            span.record_exception(e)

            return AgentResponse(
                success=False,
                reasoning=f"Agent execution failed: {str(e)}",
                error=str(e)
            )
```

---

### Task 5.4: Sofia Auto-Routing (UPDATED)

**Novo**: MCP-style horizontal integration, audit trails

#### 5.4.1: Sofia Command with Audit Trail
```python
# qwen_dev_cli/maestro.py

@app.command()
async def sofia(
    query: str = typer.Argument(..., help="Question for Sofia"),
    chat_mode: bool = typer.Option(False, "--chat", help="Enable chat mode")
):
    """
    🦉 Ask Sofia for ethical counsel

    Examples:
      maestro sofia "Should I delete user data?"
      maestro sofia "What are the ethical implications?" --chat
    """
    await initialize_system()

    correlation_id = str(uuid.uuid4())

    # Audit trail (MCP pattern)
    audit_entry = {
        "correlation_id": correlation_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "command": "sofia",
        "query": query,
        "user": os.getenv("USER", "unknown"),
        "chat_mode": chat_mode
    }

    with tracer.start_as_current_span("command.sofia") as span:
        span.set_attribute("correlation_id", correlation_id)
        span.set_attribute("chat_mode", chat_mode)

        try:
            if chat_mode:
                # Chat mode: continuous dialogue
                from qwen_dev_cli.agents.sofia_agent import SofiaChatMode

                chat = SofiaChatMode(state.sofia)
                console.print("[cyan]🦉 Sofia Chat Mode (type 'exit' to quit)[/cyan]")

                while True:
                    user_input = console.input("\n[bold cyan]You:[/bold cyan] ")
                    if user_input.lower() in ["exit", "quit"]:
                        break

                    response = await chat.send_message(user_input)
                    console.print(f"\n[bold yellow]Sofia:[/bold yellow] {response.counsel}")

                # Export transcript
                transcript = chat.export_transcript()
                audit_entry["transcript"] = transcript

            else:
                # Single counsel
                response = await state.sofia.provide_counsel_async(
                    query,
                    context={"correlation_id": correlation_id}
                )

                # Display (rich formatting)
                _display_sofia_response(response)

                audit_entry["response"] = {
                    "counsel_type": response.counsel_type,
                    "confidence": response.confidence,
                    "requires_professional": response.requires_professional
                }

            # Write audit trail
            _write_audit_trail("sofia", audit_entry)

            span.set_status(Status(StatusCode.OK))

        except Exception as e:
            span.set_status(Status(StatusCode.ERROR, str(e)))
            console.print(f"[red]❌ Error: {e}[/red]")
            audit_entry["error"] = str(e)
            _write_audit_trail("sofia", audit_entry)

def _write_audit_trail(command: str, entry: Dict[str, Any]):
    """Write audit trail to file (MCP pattern: audit trails everywhere)."""
    import json
    from pathlib import Path

    audit_dir = Path(".maestro/audit")
    audit_dir.mkdir(parents=True, exist_ok=True)

    audit_file = audit_dir / f"{command}_{datetime.now().strftime('%Y%m%d')}.jsonl"

    with open(audit_file, "a") as f:
        f.write(json.dumps(entry) + "\n")
```

---

## 📊 UPDATED SUCCESS CRITERIA (From Research)

### Functional (Anthropic Patterns)

- [ ] Orchestrator-worker architecture implemented
- [ ] Subagents operate in **parallel** when possible
- [ ] **Context isolation**: cada agent tem sua janela
- [ ] Narrow permissions: "read and route" para orchestrator
- [ ] Clear boundaries entre agents

### Security & Governance (Google + MCP Patterns)

- [ ] **Agent identities** como IAM principals
- [ ] **Least-privilege** access enforcement
- [ ] **Model Armor** style protections (input screening)
- [ ] **OAuth 2.1** flows (se external auth)
- [ ] **Audit trails** em todas interações
- [ ] **Fail-safe**: block por padrão em erro

### Observability (Google + Anthropic Patterns)

- [ ] **OpenTelemetry traces** em todas operações
- [ ] **Correlation IDs** across subagents
- [ ] **Agent-level tracing** (tool auditing)
- [ ] **Orchestrator visualization** ready
- [ ] **Token usage**, latency, error rates tracked
- [ ] Real-time + retrospective debugging

### Performance (Research Benchmarks)

- [ ] **Parallel execution**: Justiça + Sofia simultâneos
- [ ] Latency < 20ms (governance overhead)
- [ ] **90%+ improvement** vs sequential (Anthropic benchmark)
- [ ] No throughput degradation
- [ ] Background tasks para metrics (non-blocking)

---

## 🗂️ UPDATED FILES TO CREATE

### New Files (Based on Best Practices)

1. **`qwen_dev_cli/core/governance_pipeline.py`** (~300 lines)
   - `GovernancePipeline` com observability
   - `execute_with_governance_parallel()` (parallel execution)
   - OpenTelemetry instrumentation

2. **`qwen_dev_cli/core/agent_identity.py`** (~150 lines)
   - `AgentIdentity` class (IAM principal)
   - `AgentPermission` enum (least-privilege)
   - `AGENT_IDENTITIES` registry

3. **`qwen_dev_cli/core/observability.py`** (~100 lines)
   - `setup_observability()` (OpenTelemetry)
   - Trace exporters
   - Correlation ID management

4. **`tests/test_governance_pipeline_parallel.py`** (~400 lines)
   - Parallel execution tests
   - Context isolation tests
   - Fail-safe tests
   - Performance benchmarks

---

## ⏱️ UPDATED ESTIMATED TIME

| Task | Time | Complexity | Changes from V1 |
|------|------|------------|------------------|
| 5.1 Analysis | ✅ Done | LOW | - |
| 5.2 Planning + IAM + OTel | **90min** | HIGH | +60min (identity, observability) |
| 5.3 Parallel hooks | **75min** | HIGH | +15min (parallel execution) |
| 5.4 Sofia routing + audit | **45min** | MEDIUM | +15min (audit trails) |
| 5.5 Testing + benchmarks | **60min** | HIGH | +15min (parallel perf tests) |
| **TOTAL** | **~4.5 hours** | - | +1.5 hours vs V1 |

**Justificativa**: Best practices research adicionou requisitos importantes:
- Agent identity & IAM (Google pattern)
- OpenTelemetry observability (Anthropic + Google)
- Parallel execution (Anthropic benchmark: 90% improvement)
- Audit trails (MCP pattern)
- Fail-safe defaults (enterprise requirement)

---

## 📚 SOURCES

### Anthropic Documentation
- [How we built our multi-agent research system](https://www.anthropic.com/engineering/multi-agent-research-system)
- [Building agents with the Claude Agent SDK](https://www.anthropic.com/engineering/building-agents-with-the-claude-agent-sdk)
- [IBM and Anthropic Partnership - Enterprise Governance](https://newsroom.ibm.com/2025-10-07-2025-ibm-and-anthropic-partner-to-advance-enterprise-software-development-with-proven-security-and-governance)

### Google Cloud Documentation
- [Build and manage multi-system agents with Vertex AI](https://cloud.google.com/blog/products/ai-machine-learning/build-and-manage-multi-system-agents-with-vertex-ai)
- [Agent Development Kit Guide](https://developers.googleblog.com/en/agent-development-kit-easy-to-build-multi-agent-applications/)
- [Vertex AI Agent Builder - Observability Tools](https://www.infoworld.com/article/4085736/google-boosts-vertex-ai-agent-builder-with-new-observability-and-deployment-tools.html)

### Model Context Protocol (MCP)
- [Advancing Multi-Agent Systems Through MCP](https://arxiv.org/html/2504.21030v1)
- [Complete Guide to MCP in 2025](https://www.keywordsai.co/blog/introduction-to-mcp)
- [Model Context Protocol - Wikipedia](https://en.wikipedia.org/wiki/Model_Context_Protocol)

### Additional Resources
- [AI Agent Orchestration in 2025 - Best Practices](https://dev.to/nexaitech/ai-agent-orchestration-in-2025-how-to-build-scalable-secure-and-observable-multi-agent-systems-2flc)
- [Claude Agent SDK Best Practices](https://skywork.ai/blog/claude-agent-sdk-best-practices-ai-agents-2025/)

---

## 🚀 KEY IMPROVEMENTS FROM RESEARCH

### 1. **Parallel Execution** (Anthropic)
- Justiça e Sofia executam simultaneamente (não sequencial)
- **90% faster** vs single-threaded
- Context isolation preserva independência

### 2. **Agent Identity & IAM** (Google)
- Agents como first-class IAM principals
- Least-privilege enforcement nativo
- Compliance requirements atendidos

### 3. **OpenTelemetry Observability** (Both)
- Traces completos: prompts, tools, orchestration
- Correlation IDs cross-agent
- Real-time + retrospective debugging

### 4. **MCP Audit Trails** (Standard)
- Single audit trail cross-workflow
- OAuth 2.1, explicit consent
- Governance policies everywhere

### 5. **Fail-Safe Defaults** (Enterprise)
- Block por padrão em erro
- Human-in-the-loop para critical
- Explicit approvals obrigatórios

---

**Status**: Plano atualizado com best practices de Nov 2025.

**Próximo passo**: Iniciar implementação Task 5.2 com novos padrões?
