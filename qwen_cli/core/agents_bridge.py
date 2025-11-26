"""
Agents Bridge Module - Agent Registry, Router, and Manager
==========================================================

Extracted from Bridge GOD CLASS (Nov 2025 Refactoring).

Features:
- AgentInfo: Metadata about agents
- AGENT_REGISTRY: 14 specialized agents
- AgentRouter: Intelligent intent-based routing (PT-BR + EN)
- AgentManager: Lazy-loading agent lifecycle management
"""

from __future__ import annotations

import inspect
import re
from dataclasses import dataclass
from typing import Any, AsyncIterator, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .llm_client import GeminiClient


@dataclass
class AgentInfo:
    """Metadata about an agent."""
    name: str
    role: str
    description: str
    capabilities: List[str]
    module_path: str
    class_name: str


# Agent registry - lazy loaded
AGENT_REGISTRY: Dict[str, AgentInfo] = {
    "planner": AgentInfo(
        name="planner",
        role="PLANNER",
        description="Goal-Oriented Action Planning (GOAP)",
        capabilities=["planning", "coordination", "decomposition"],
        module_path="qwen_dev_cli.agents.planner",
        class_name="PlannerAgent",
    ),
    "executor": AgentInfo(
        name="executor",
        role="EXECUTOR",
        description="Secure code execution with sandbox",
        capabilities=["bash", "python", "tools"],
        module_path="qwen_dev_cli.agents.executor_nextgen",
        class_name="ExecutorAgentNextGen",
    ),
    "architect": AgentInfo(
        name="architect",
        role="ARCHITECT",
        description="Architecture analysis and feasibility",
        capabilities=["design", "analysis", "veto"],
        module_path="qwen_dev_cli.agents.architect",
        class_name="ArchitectAgent",
    ),
    "reviewer": AgentInfo(
        name="reviewer",
        role="REVIEWER",
        description="Enterprise code review",
        capabilities=["review", "analysis", "suggestions"],
        module_path="qwen_dev_cli.agents.reviewer",
        class_name="ReviewerAgent",
    ),
    "explorer": AgentInfo(
        name="explorer",
        role="EXPLORER",
        description="Codebase exploration and navigation",
        capabilities=["search", "navigate", "understand"],
        module_path="qwen_dev_cli.agents.explorer",
        class_name="ExplorerAgent",
    ),
    "refactorer": AgentInfo(
        name="refactorer",
        role="REFACTORER",
        description="Code refactoring and improvement",
        capabilities=["refactor", "improve", "transform"],
        module_path="qwen_dev_cli.agents.refactorer",
        class_name="RefactorerAgent",
    ),
    "testing": AgentInfo(
        name="testing",
        role="TESTING",
        description="Test generation and execution",
        capabilities=["generate_tests", "run_tests", "coverage"],
        module_path="qwen_dev_cli.agents.testing",
        class_name="TestingAgent",
    ),
    "security": AgentInfo(
        name="security",
        role="SECURITY",
        description="Security analysis (OWASP)",
        capabilities=["scan", "audit", "vulnerabilities"],
        module_path="qwen_dev_cli.agents.security",
        class_name="SecurityAgent",
    ),
    "documentation": AgentInfo(
        name="documentation",
        role="DOCUMENTATION",
        description="Documentation generation",
        capabilities=["docstrings", "readme", "api_docs"],
        module_path="qwen_dev_cli.agents.documentation",
        class_name="DocumentationAgent",
    ),
    "performance": AgentInfo(
        name="performance",
        role="PERFORMANCE",
        description="Performance profiling and optimization",
        capabilities=["profile", "optimize", "benchmark"],
        module_path="qwen_dev_cli.agents.performance",
        class_name="PerformanceAgent",
    ),
    "devops": AgentInfo(
        name="devops",
        role="DEVOPS",
        description="Infrastructure and deployment",
        capabilities=["docker", "kubernetes", "ci_cd"],
        module_path="qwen_dev_cli.agents.devops_agent",
        class_name="DevOpsAgent",
    ),
    "justica": AgentInfo(
        name="justica",
        role="GOVERNANCE",
        description="Constitutional governance",
        capabilities=["evaluate", "approve", "block"],
        module_path="qwen_dev_cli.agents.justica_agent",
        class_name="JusticaIntegratedAgent",
    ),
    "sofia": AgentInfo(
        name="sofia",
        role="COUNSELOR",
        description="Ethical counsel and wisdom",
        capabilities=["counsel", "ethics", "reflection"],
        module_path="qwen_dev_cli.agents.sofia_agent",
        class_name="SofiaIntegratedAgent",
    ),
    "data": AgentInfo(
        name="data",
        role="DATABASE",
        description="Database optimization and analysis",
        capabilities=["schema_analysis", "query_optimization", "migration"],
        module_path="qwen_dev_cli.agents.data_agent_production",
        class_name="DataAgent",
    ),
}


class AgentRouter:
    """
    Intelligent request router that detects user intent and routes to agents.

    Claude Code Parity: Implements automatic agent invocation like Claude Code's
    subagent system - users can naturally describe tasks and the router decides
    which specialized agent should handle it.

    Philosophy:
        "The user shouldn't need to know which agent does what - just ask."

    Routing Strategy:
        1. Keyword matching (fast, deterministic)
        2. Intent patterns (regex-based)
        3. Confidence scoring (multiple matches = ask user)
    """

    # Intent patterns → agent mapping with confidence weights
    # Enhanced for PT-BR and EN detection
    # v6.1: Added patterns for multi-plan, clarification, and exploration modes
    INTENT_PATTERNS: Dict[str, List[tuple]] = {
        "planner": [
            (r"\b(plan[oe]?|planeja[r]?|planejamento|cri[ae]\s*(um\s*)?plano)\b", 0.9),
            (r"\b(break\s*down|decompo[ns]|roadmap|estratégia)\b", 0.9),
            (r"\b(como\s*(fa[zç]o|implement|começ)|how\s*(to|do\s*i|should)|steps?\s*to)\b", 0.75),
            (r"\b(preciso\s*(de\s*)?(um\s*)?plano|help\s*me\s*(plan|with))\b", 0.8),
            (r"\bimplementa[rç].*passo\b", 0.85),
        ],
        # v6.1: Planner sub-modes (multi-plan, clarification, exploration)
        "planner:multi": [
            (r"\b(multi[- ]?plan|m[uú]ltiplos?\s*planos?|alternativ[ao]s?|3\s*planos?)\b", 0.95),
            (r"\b(compare\s*(multiple\s*)?plans?|compar[ae]\s*planos?|multiple\s*plans?)\b", 0.9),
            (r"\b(options?|op[çc][oõ]es|escolhas?|choices?)\b", 0.85),
            (r"\b(risk.*reward|risco.*recompensa|trade-?offs?)\b", 0.85),
            (r"\b(conservative|agressivo|creative|criativ[ao]|lateral)\b", 0.8),
        ],
        "planner:clarify": [
            (r"\b(clarif[iy]|esclare[çc][ae]|pergunt[ae]s?\s*(antes|primeiro))\b", 0.95),
            (r"\b(fa[çz]a\s*perguntas?|ask\s*(me\s*)?questions?)\b", 0.95),
            (r"\b(before\s*plan|antes\s*de\s*plan[ae]jar)\b", 0.9),
            (r"\b(need\s*more\s*info|preciso\s*mais\s*info)\b", 0.85),
        ],
        "planner:explore": [
            (r"\b(explor[ae]\s*(sem|without)\s*(modific|alter|mudar))\b", 0.95),
            (r"\b(read[- ]?only|somente\s*leitura|apenas\s*an[aá]lise)\b", 0.95),
            (r"\b(analys[ei]s?\s*only|s[oó]\s*an[aá]lise)\b", 0.9),
            (r"\b(don'?t\s*(change|modify)|n[aã]o\s*(mude|altere|modifique))\b", 0.85),
        ],
        "executor": [
            (r"\b(execut[ae]|run|roda[r]?|execute|bash|shell|terminal)\b", 0.9),
            (r"\b(comando?s?|command)\b", 0.75),
            (r"\b(pip\s+install|npm\s+(install|run)|make|cargo|go\s+(run|build))\b", 0.95),
            (r"\b(git\s+(status|diff|add|commit|push|pull|clone|log))\b", 0.9),
            (r"\b(pytest|unittest|jest|npm\s+test|testa[r]?\s+)\b", 0.85),
        ],
        "architect": [
            (r"\b(arquitetur[a]?|architect(ure)?|design\s*(pattern)?)\b", 0.9),
            (r"\b(estrutur[ae]|system\s*design|analisa[r]?\s*(a\s*)?arquitetura)\b", 0.85),
            (r"\b(diagrama?|uml|flowchart|fluxo(grama)?)\b", 0.85),
            (r"\b(clean\s*architect|hexagonal|onion|layered|microservice)\b", 0.95),
            (r"\b(trade-?off|decision|escolh[ae]\s*(entre|de\s*design))\b", 0.7),
        ],
        "reviewer": [
            (r"\b(review|revis[ae]|code\s*review)\b", 0.9),
            (r"\b(analys[ei]s?\s*(de\s*)?(c[oó]digo)?|análise)\b", 0.8),
            (r"\b(qualidade|quality|best\s*practice|boas\s*pr[aá]ticas)\b", 0.8),
            (r"\b(pr\s*review|pull\s*request|merge\s*request)\b", 0.95),
            (r"\b(code\s*smell|technical\s*debt|d[ií]vida\s*t[eé]cnica)\b", 0.85),
        ],
        "explorer": [
            (r"\b(explor[ae]|search|busc[ae]|find|encontr[ae]|localiz[ae])\b", 0.85),
            (r"\b(onde\s*(est[aá]|fica)|where\s*(is|are)|acha[re]?)\b", 0.8),
            (r"\b(naveg[ae]|codebase|estrutura\s*(do\s*)?(projeto|c[oó]digo))\b", 0.75),
            (r"\b(grep|ripgrep|ag\s|search\s*for|procur[ae])\b", 0.9),
        ],
        "refactorer": [
            (r"\b(refactor|refatora|refactoring|melhora[re]?\s*(o\s*)?(c[oó]digo)?)\b", 0.9),
            (r"\b(clean\s*(up)?|limp[ae]|simplif[iy])\b", 0.75),
            (r"\b(extract|extrai|mover?\s*para|move\s*to)\b", 0.7),
            (r"\b(rename|renomea|dry|don'?t\s*repeat)\b", 0.8),
        ],
        "testing": [
            (r"\b(test[aes]?|testa[re]?|unittest|pytest|coverage|cobertura)\b", 0.9),
            (r"\b(tdd|bdd|test\s*driven|behavior\s*driven)\b", 0.95),
            (r"\b(mock|stub|fixture|parametriz[ae])\b", 0.85),
            (r"\b(integration\s*test|unit\s*test|e2e|end.to.end)\b", 0.9),
            (r"\b(unit[aá]rio|cria[r]?\s*testes?|write\s*tests?)\b", 0.9),
        ],
        "security": [
            (r"\b(security|seguran[çc]a|owasp|vulnerabil\w*|cve)\b", 0.95),
            (r"\b(injection|xss|csrf|sqli|auth[nz]?|exploit)\b", 0.9),
            (r"\b(audit|auditoria|pentest|penetration|scan)\b", 0.85),
            (r"\b(sanitiz|escap[ae]|valid[ae]|malware|trojan)\b", 0.75),
            (r"\bquais\s*(vulner|falh|brech)\w*", 0.9),
        ],
        "documentation": [
            (r"\b(document[ae]?|documenta[çc][aã]o|docs?|readme)\b", 0.9),
            (r"\b(docstring|jsdoc|pydoc|api\s*doc)\b", 0.95),
            (r"\b(coment[aá]rio|comment|explain|explic[ae])\b", 0.7),
            (r"\b(changelog|release\s*notes)\b", 0.85),
        ],
        "performance": [
            (r"\b(perform|performance|desempenho|otimiz[ae]|optim[iz])\b", 0.9),
            (r"\b(profil[ae]|profiling|benchmark|cprofile|perf)\b", 0.95),
            (r"\b(lento|slow|fast|r[aá]pido|speed\s*up|acelera)\b", 0.75),
            (r"\b(memory|mem[oó]ria|leak|cpu|io\s*bound)\b", 0.8),
        ],
        "devops": [
            (r"\b(devops|docker|kubernetes|k8s|ci\s*/?\s*cd|pipeline)\b", 0.95),
            (r"\b(deploy|implant[ae]|infra|terraform|ansible)\b", 0.9),
            (r"\b(container|imagem|image|pod|service)\b", 0.8),
            (r"\b(github\s*actions?|gitlab\s*ci|jenkins|circleci)\b", 0.95),
        ],
        "data": [
            (r"\b(database|banco\s*de\s*dados)\b", 0.9),
            (r"\b(sql|query|consulta)\b", 0.92),
            (r"\b(schema|esquema|migration|migra[çc][aã]o)\b", 0.85),
            (r"\b(orm|sqlalchemy|django\s*orm|prisma|sequelize)\b", 0.9),
            (r"\b(index|[ií]ndice|foreign\s*key|constraint)\b", 0.8),
            (r"\botimiza.*\b(query|sql|consulta)\b", 0.95),
        ],
        "justica": [
            (r"\b(justi[çc]a|governance|governan[çc]a|constitu[çi])\b", 0.95),
            (r"\b(compliance|conformidade|regulat[oó]rio)\b", 0.85),
            (r"\b(v[eé]rtice|article|artigo)\b", 0.7),
        ],
        "sofia": [
            (r"\b(sofia|counsel|conselho|[eé]tic[ao]|ethical|sabedoria|wisdom)\b", 0.95),
            (r"\b(filosof|philosophy|moral|virtue|virtude)\b", 0.85),
            (r"\b(socrat|dile[mn]ma|reflection|reflex[aã]o)\b", 0.8),
        ],
    }

    # Keywords that indicate NOT to route (general chat)
    NO_ROUTE_PATTERNS = [
        r"^(oi|ol[aá]|hi|hello|hey|e\s*a[ií])\b",  # Greetings
        r"^(obrigad[oa]|thanks?|valeu|vlw)\b",      # Thanks
        r"^(ok|certo|entend[io]|got\s*it)\b",      # Acknowledgments
    ]

    MIN_CONFIDENCE = 0.7

    def __init__(self):
        self._compiled_patterns: Dict[str, List[tuple]] = {}
        self._no_route_patterns = [re.compile(p, re.IGNORECASE) for p in self.NO_ROUTE_PATTERNS]

        # Pre-compile all patterns
        for agent, patterns in self.INTENT_PATTERNS.items():
            self._compiled_patterns[agent] = [
                (re.compile(pattern, re.IGNORECASE), weight)
                for pattern, weight in patterns
            ]

    def should_route(self, message: str) -> bool:
        """Check if message should be considered for routing."""
        if len(message.strip()) < 5:
            return False

        for pattern in self._no_route_patterns:
            if pattern.search(message):
                return False

        return True

    def detect_intent(self, message: str) -> List[tuple]:
        """
        Detect which agent(s) should handle this message.

        Returns:
            List of (agent_name, confidence) tuples, sorted by confidence desc
        """
        if not self.should_route(message):
            return []

        scores: Dict[str, float] = {}

        for agent, patterns in self._compiled_patterns.items():
            max_score = 0.0
            for compiled_pattern, weight in patterns:
                if compiled_pattern.search(message):
                    max_score = max(max_score, weight)

            if max_score > 0:
                scores[agent] = max_score

        sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return sorted_scores

    def route(self, message: str) -> Optional[tuple]:
        """
        Route message to best agent.

        Returns:
            (agent_name, confidence) if confident routing found
            None if no clear routing (let LLM handle naturally)
        """
        intents = self.detect_intent(message)

        if not intents:
            return None

        best_agent, best_confidence = intents[0]

        if best_confidence >= self.MIN_CONFIDENCE:
            return (best_agent, best_confidence)

        return None

    def get_routing_suggestion(self, message: str) -> Optional[str]:
        """
        Get a suggestion message for ambiguous routing.

        Returns markdown message if multiple agents could handle this.
        """
        intents = self.detect_intent(message)

        high_conf = [(a, c) for a, c in intents if c >= 0.6]

        if len(high_conf) > 1:
            suggestions = [f"- `/{a}` ({int(c*100)}%)" for a, c in high_conf[:3]]
            return (
                "🤔 Multiple agents could help:\n" +
                "\n".join(suggestions) +
                "\n\nType one of the commands or ask naturally."
            )

        return None


class AgentManager:
    """
    Lazy-loading agent manager.

    Only imports agents when first used to keep startup fast.
    """

    def __init__(self, llm_client: Optional['GeminiClient'] = None):
        # Lazy import to avoid circular dependency
        if llm_client is None:
            from .llm_client import GeminiClient
            llm_client = GeminiClient()
        self.llm_client = llm_client
        self._agents: Dict[str, Any] = {}
        self._load_errors: Dict[str, str] = {}
        self.router = AgentRouter()

    @property
    def available_agents(self) -> List[str]:
        """List of available agent names."""
        return list(AGENT_REGISTRY.keys())

    def get_agent_info(self, name: str) -> Optional[AgentInfo]:
        """Get agent metadata."""
        return AGENT_REGISTRY.get(name)

    async def get_agent(self, name: str) -> Optional[Any]:
        """
        Get or create agent instance.

        Lazy loads the agent module on first use.
        Uses inspect.signature() to detect constructor parameters and pass appropriate args.
        """
        if name in self._agents:
            return self._agents[name]

        if name in self._load_errors:
            return None

        info = AGENT_REGISTRY.get(name)
        if not info:
            self._load_errors[name] = f"Unknown agent: {name}"
            return None

        try:
            # Dynamic import
            import importlib
            module = importlib.import_module(info.module_path)
            agent_class = getattr(module, info.class_name)

            # FIX CRÍTICO: Detectar assinatura do __init__ e passar parâmetros corretos
            sig = inspect.signature(agent_class.__init__)
            params = sig.parameters

            init_kwargs: Dict[str, Any] = {}
            if 'llm_client' in params:
                init_kwargs['llm_client'] = self.llm_client
            if 'mcp_client' in params:
                init_kwargs['mcp_client'] = None
            if 'model' in params:
                init_kwargs['model'] = self.llm_client

            agent = agent_class(**init_kwargs)
            self._agents[name] = agent
            return agent

        except ImportError as e:
            self._load_errors[name] = f"Import error: {e}"
            return None
        except Exception as e:
            self._load_errors[name] = f"Init error: {e}"
            return None

    async def invoke_agent(
        self,
        name: str,
        task: str,
        context: Optional[Dict[str, Any]] = None
    ) -> AsyncIterator[str]:
        """
        Invoke an agent and stream response.

        Falls back to LLM if agent unavailable.
        """
        agent = await self.get_agent(name)

        if agent is None:
            # Fallback: use LLM directly with agent-specific prompt
            info = AGENT_REGISTRY.get(name)
            if info:
                system_prompt = f"You are a {info.role}. {info.description}. Capabilities: {', '.join(info.capabilities)}."
                async for chunk in self.llm_client.stream(task, system_prompt):
                    yield chunk
            else:
                yield f"❌ Agent '{name}' not available"
            return

        # FIX CRÍTICO: Criar AgentTask corretamente
        from qwen_dev_cli.agents.base import AgentTask
        agent_task = AgentTask(request=task, context=context or {})

        # Try streaming interface first
        if hasattr(agent, 'execute_streaming'):
            try:
                # Detectar assinatura de execute_streaming
                sig = inspect.signature(agent.execute_streaming)
                param_count = len([p for p in sig.parameters.values()
                                   if p.default == inspect.Parameter.empty])

                if param_count == 1:  # Apenas task (AgentTask)
                    async for chunk in agent.execute_streaming(agent_task):
                        if isinstance(chunk, dict):
                            yield str(chunk.get('content', chunk))
                        else:
                            yield str(chunk)
                else:  # task + context (str, dict)
                    async for chunk in agent.execute_streaming(task, context or {}):
                        yield str(chunk)
                return
            except Exception as e:
                yield f"⚠️ Streaming failed: {e}\n"

        # Fallback to sync execute
        if hasattr(agent, 'execute'):
            try:
                result = await agent.execute(agent_task)
                if hasattr(result, 'data'):
                    yield str(result.data)
                elif hasattr(result, 'result'):
                    yield str(result.result)
                else:
                    yield str(result)
                return
            except Exception as e:
                yield f"❌ Agent error: {e}"
                return

        yield f"❌ Agent '{name}' has no execute method"

    # =========================================================================
    # PLANNER v6.1 SPECIFIC METHODS
    # =========================================================================

    async def invoke_planner_multi(
        self,
        task: str,
        context: Optional[Dict[str, Any]] = None
    ) -> AsyncIterator[str]:
        """
        Invoke planner with Multi-Plan Generation (v6.1).

        Generates 3 alternative plans with different strategies:
        - STANDARD: Conservative, low-risk approach
        - ACCELERATOR: Fast execution, higher risk
        - LATERAL: Creative, unconventional approach

        Each plan includes probability estimates (P(Success), P(Friction), etc.)
        based on Zhang et al. 2025 Verbalized Sampling.
        """
        agent = await self.get_agent("planner")

        if agent is None:
            yield "❌ Planner agent not available"
            return

        if not hasattr(agent, 'generate_multi_plan'):
            yield "⚠️ Planner doesn't support multi-plan (requires v6.1+)\n"
            # Fallback to regular planning
            async for chunk in self.invoke_agent("planner", task, context):
                yield chunk
            return

        try:
            from qwen_dev_cli.agents.base import AgentTask
            agent_task = AgentTask(request=task, context=context or {})

            yield "🎯 **Generating 3 Alternative Plans...**\n\n"

            # Generate multi-plan
            result = await agent.generate_multi_plan(agent_task)

            # Stream the markdown output
            yield result.to_markdown()

        except Exception as e:
            yield f"❌ Multi-plan generation failed: {e}"

    async def invoke_planner_clarify(
        self,
        task: str,
        context: Optional[Dict[str, Any]] = None
    ) -> AsyncIterator[str]:
        """
        Invoke planner with Clarification Mode (v6.1).

        Before planning, the agent asks 2-3 clarifying questions
        to better understand requirements (Cursor 2.1 pattern).
        """
        agent = await self.get_agent("planner")

        if agent is None:
            yield "❌ Planner agent not available"
            return

        if not hasattr(agent, 'generate_clarifying_questions'):
            yield "⚠️ Planner doesn't support clarification (requires v6.1+)\n"
            async for chunk in self.invoke_agent("planner", task, context):
                yield chunk
            return

        try:
            from qwen_dev_cli.agents.base import AgentTask
            agent_task = AgentTask(request=task, context=context or {})

            yield "🤔 **Analyzing your request...**\n\n"

            # Generate clarifying questions
            questions = await agent.generate_clarifying_questions(agent_task)

            if questions:
                yield "Before I create a plan, I have some questions:\n\n"
                for i, q in enumerate(questions, 1):
                    yield f"**{i}.** {q.question}\n"
                    if q.options:
                        for opt in q.options:
                            yield f"   - {opt}\n"
                    yield "\n"
                yield "\n💡 *Answer these questions, then run `/plan` again with the context.*\n"
            else:
                yield "✅ No clarification needed. Proceeding with planning...\n\n"
                # Proceed with regular planning
                async for chunk in self.invoke_agent("planner", task, context):
                    yield chunk

        except Exception as e:
            yield f"❌ Clarification failed: {e}"

    async def invoke_planner_explore(
        self,
        task: str,
        context: Optional[Dict[str, Any]] = None
    ) -> AsyncIterator[str]:
        """
        Invoke planner in Exploration Mode (v6.1).

        Read-only analysis mode - gathers context and analyzes
        without proposing modifications (Claude Plan Mode pattern).
        """
        agent = await self.get_agent("planner")

        if agent is None:
            yield "❌ Planner agent not available"
            return

        if not hasattr(agent, 'explore'):
            yield "⚠️ Planner doesn't support exploration (requires v6.1+)\n"
            async for chunk in self.invoke_agent("planner", task, context):
                yield chunk
            return

        try:
            from qwen_dev_cli.agents.base import AgentTask
            agent_task = AgentTask(request=task, context=context or {})

            yield "🔍 **Exploration Mode (Read-Only)**\n\n"
            yield "_No modifications will be made - analysis only._\n\n"

            # Run exploration
            result = await agent.explore(agent_task)

            if result.success:
                exploration = result.data.get('exploration', {})

                # Format exploration results
                if 'files_analyzed' in exploration:
                    yield f"**📁 Files Analyzed:** {exploration['files_analyzed']}\n\n"

                if 'key_findings' in exploration:
                    yield "**🔑 Key Findings:**\n"
                    for finding in exploration['key_findings']:
                        yield f"- {finding}\n"
                    yield "\n"

                if 'dependencies' in exploration:
                    yield "**🔗 Dependencies:**\n"
                    for dep in exploration['dependencies'][:10]:
                        yield f"- {dep}\n"
                    yield "\n"

                if 'recommendations' in exploration:
                    yield "**💡 Recommendations:**\n"
                    for rec in exploration['recommendations']:
                        yield f"- {rec}\n"
                    yield "\n"

                yield "\n✅ *Exploration complete. Use `/plan` to create an execution plan.*\n"
            else:
                yield f"❌ Exploration failed: {result.error}\n"

        except Exception as e:
            yield f"❌ Exploration failed: {e}"

    def detect_planner_mode(self, message: str) -> Optional[str]:
        """
        Detect which planner mode should be used based on message content.

        Returns:
            "multi" | "clarify" | "explore" | None (regular planning)
        """
        # Check for sub-mode patterns
        for mode in ["planner:multi", "planner:clarify", "planner:explore"]:
            patterns = self.router._compiled_patterns.get(mode, [])
            for compiled_pattern, weight in patterns:
                if compiled_pattern.search(message) and weight >= 0.85:
                    return mode.split(":")[1]  # Return "multi", "clarify", or "explore"

        return None


__all__ = [
    'AgentInfo',
    'AGENT_REGISTRY',
    'AgentRouter',
    'AgentManager',
]
