"""
PLANNER v6.0/v6.1 "ESPETACULAR" TESTS

Verifica as features v6.0:
1. Clarifying Questions (Cursor 2.1 pattern)
2. plan.md Artifact Generation (Claude Code pattern)
3. Confidence Ratings (Devin pattern)
4. Read-Only Exploration Mode (Claude Plan Mode)

Verifica as features v6.1:
5. Multi-Plan Generation (Verbalized Sampling - Zhang et al. 2025)
6. Verbalized Probabilities (P(Success), P(Friction), P(Quality))
7. Risk/Reward Scoring
8. Automatic Plan Recommendation

Author: JuanCS Dev
Date: 2025-11-25
"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock


# =============================================================================
# TESTE 1: NEW DATA MODELS
# =============================================================================

class TestV6DataModels:
    """Testa os novos modelos de dados v6.0."""

    def test_clarifying_question_model(self):
        """ClarifyingQuestion deve ter campos corretos."""
        from jdev_cli.agents.planner import ClarifyingQuestion

        q = ClarifyingQuestion(
            question="What is the scope?",
            category="scope",
            options=["Single file", "Module", "Project"],
            required=True
        )

        assert q.question == "What is the scope?"
        assert q.category == "scope"
        assert len(q.options) == 3
        assert q.required is True
        assert q.id.startswith("q-")

    def test_clarification_response_model(self):
        """ClarificationResponse deve ter campos corretos."""
        from jdev_cli.agents.planner import ClarificationResponse

        r = ClarificationResponse(
            question_id="q-123",
            answer="Single file",
            skipped=False
        )

        assert r.question_id == "q-123"
        assert r.answer == "Single file"
        assert r.skipped is False

    def test_planning_mode_enum(self):
        """PlanningMode deve ter 3 modos."""
        from jdev_cli.agents.planner import PlanningMode

        assert PlanningMode.EXPLORATION.value == "exploration"
        assert PlanningMode.PLANNING.value == "planning"
        assert PlanningMode.EXECUTION.value == "execution"

    def test_confidence_level_enum(self):
        """ConfidenceLevel deve ter 5 níveis."""
        from jdev_cli.agents.planner import ConfidenceLevel

        assert ConfidenceLevel.CERTAIN.value == "certain"
        assert ConfidenceLevel.CONFIDENT.value == "confident"
        assert ConfidenceLevel.MODERATE.value == "moderate"
        assert ConfidenceLevel.LOW.value == "low"
        assert ConfidenceLevel.SPECULATIVE.value == "speculative"


# =============================================================================
# TESTE 2: STEP CONFIDENCE
# =============================================================================

class TestStepConfidence:
    """Testa o cálculo de confiança por step."""

    def test_step_confidence_from_score_high(self):
        """Score alto deve resultar em CERTAIN."""
        from jdev_cli.agents.planner import StepConfidence, ConfidenceLevel

        conf = StepConfidence.from_score(0.95, "Test reasoning")

        assert conf.score == 0.95
        assert conf.level == ConfidenceLevel.CERTAIN
        assert "Test reasoning" in conf.reasoning

    def test_step_confidence_from_score_low(self):
        """Score baixo deve resultar em SPECULATIVE."""
        from jdev_cli.agents.planner import StepConfidence, ConfidenceLevel

        conf = StepConfidence.from_score(0.2, "Uncertain task")

        assert conf.score == 0.2
        assert conf.level == ConfidenceLevel.SPECULATIVE

    def test_step_confidence_clamping(self):
        """Score deve ser clampado em [0, 1]."""
        from jdev_cli.agents.planner import StepConfidence

        conf_high = StepConfidence.from_score(1.5)
        conf_low = StepConfidence.from_score(-0.5)

        assert conf_high.score == 1.0
        assert conf_low.score == 0.0

    def test_step_confidence_with_risks(self):
        """StepConfidence deve aceitar lista de riscos."""
        from jdev_cli.agents.planner import StepConfidence

        risks = ["Complex dependency", "External API"]
        conf = StepConfidence.from_score(0.6, "Test", risks)

        assert conf.risk_factors == risks


# =============================================================================
# TESTE 3: SOP STEP WITH CONFIDENCE
# =============================================================================

class TestSOPStepConfidence:
    """Testa SOPStep com campos de confidence."""

    def test_sop_step_has_confidence_fields(self):
        """SOPStep deve ter campos de confidence."""
        from jdev_cli.agents.planner import SOPStep

        step = SOPStep(
            id="step-1",
            role="coder",
            action="Implement feature",
            objective="Add new capability",
            definition_of_done="Tests pass",
            confidence_score=0.85,
            confidence_reasoning="Well-understood task",
            risk_factors=["External API dependency"]
        )

        assert step.confidence_score == 0.85
        assert "Well-understood" in step.confidence_reasoning
        assert len(step.risk_factors) == 1

    def test_sop_step_confidence_default(self):
        """SOPStep deve ter confidence padrão de 0.7."""
        from jdev_cli.agents.planner import SOPStep

        step = SOPStep(
            id="step-1",
            role="coder",
            action="Implement feature",
            objective="Add new capability",
            definition_of_done="Tests pass"
        )

        assert step.confidence_score == 0.7

    def test_sop_step_confidence_validation(self):
        """SOPStep deve validar confidence entre 0 e 1."""
        from jdev_cli.agents.planner import SOPStep
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            SOPStep(
                id="step-1",
                role="coder",
                action="test",
                objective="test",
                definition_of_done="test",
                confidence_score=1.5  # Invalid: > 1.0
            )


# =============================================================================
# TESTE 4: EXECUTION PLAN V6.0 FIELDS
# =============================================================================

class TestExecutionPlanV6:
    """Testa ExecutionPlan com campos v6.0."""

    def test_execution_plan_has_v6_fields(self):
        """ExecutionPlan deve ter campos v6.0."""
        from jdev_cli.agents.planner import ExecutionPlan, PlanningMode

        plan = ExecutionPlan(
            plan_id="plan-123",
            goal="Implement feature X",
            strategy_overview="Sequential execution",
            mode=PlanningMode.PLANNING,
            overall_confidence=0.8,
            confidence_summary="Good confidence"
        )

        assert plan.mode == PlanningMode.PLANNING
        assert plan.overall_confidence == 0.8
        assert plan.confidence_summary == "Good confidence"
        assert plan.plan_version == "6.0"

    def test_execution_plan_clarifying_questions(self):
        """ExecutionPlan deve suportar clarifying questions."""
        from jdev_cli.agents.planner import (
            ExecutionPlan,
            ClarifyingQuestion,
            ClarificationResponse
        )

        plan = ExecutionPlan(
            plan_id="plan-123",
            goal="Test",
            strategy_overview="Test",
            clarifying_questions=[
                ClarifyingQuestion(question="Scope?", category="scope")
            ],
            clarification_responses=[
                ClarificationResponse(question_id="q-1", answer="Module")
            ]
        )

        assert len(plan.clarifying_questions) == 1
        assert len(plan.clarification_responses) == 1


# =============================================================================
# TESTE 5: PLANNER AGENT V6.0
# =============================================================================

class TestPlannerAgentV6:
    """Testa PlannerAgent v6.0."""

    def test_planner_agent_init_v6(self):
        """PlannerAgent deve aceitar parâmetros v6.0."""
        from jdev_cli.agents.planner import PlannerAgent, PlanningMode

        mock_llm = MagicMock()
        mock_mcp = MagicMock()

        planner = PlannerAgent(
            llm_client=mock_llm,
            mcp_client=mock_mcp,
            plan_artifact_dir="/tmp/plans",
            ask_clarifying_questions=True
        )

        assert planner.plan_artifact_dir == "/tmp/plans"
        assert planner.ask_clarifying_questions is True
        assert planner.current_mode == PlanningMode.PLANNING

    def test_planner_agent_callbacks(self):
        """PlannerAgent deve aceitar callbacks."""
        from jdev_cli.agents.planner import PlannerAgent

        mock_llm = MagicMock()
        mock_mcp = MagicMock()

        planner = PlannerAgent(mock_llm, mock_mcp)

        # Set callbacks
        question_cb = MagicMock()
        approval_cb = MagicMock()

        planner.set_question_callback(question_cb)
        planner.set_approval_callback(approval_cb)

        assert planner._question_callback == question_cb
        assert planner._approval_callback == approval_cb


# =============================================================================
# TESTE 6: CONFIDENCE CALCULATION
# =============================================================================

class TestConfidenceCalculation:
    """Testa cálculo de confidence."""

    def test_calculate_step_confidence_familiar_role(self):
        """Roles familiares devem aumentar confidence."""
        from jdev_cli.agents.planner import PlannerAgent, SOPStep

        mock_llm = MagicMock()
        mock_mcp = MagicMock()
        planner = PlannerAgent(mock_llm, mock_mcp)

        step = SOPStep(
            id="step-1",
            role="coder",  # Familiar role
            action="Test",
            objective="Test",
            definition_of_done="Test",
            dependencies=[],
            cost=1.0
        )

        score, reasoning, risks = planner._calculate_step_confidence(step, {})

        assert score >= 0.8  # Base + familiar role bonus
        assert "familiar role" in reasoning

    def test_calculate_step_confidence_unfamiliar_role(self):
        """Roles não familiares devem gerar risco."""
        from jdev_cli.agents.planner import PlannerAgent, SOPStep

        mock_llm = MagicMock()
        mock_mcp = MagicMock()
        planner = PlannerAgent(mock_llm, mock_mcp)

        step = SOPStep(
            id="step-1",
            role="exotic_agent",  # Unfamiliar
            action="Test",
            objective="Test",
            definition_of_done="Test"
        )

        score, reasoning, risks = planner._calculate_step_confidence(step, {})

        # Main check: unfamiliar role should generate risk warning
        assert any("Unfamiliar" in r for r in risks)
        # Score should be reasonable (floating point tolerance)
        assert 0.5 <= score <= 0.85

    def test_calculate_step_confidence_high_dependencies(self):
        """Muitas dependências devem diminuir confidence."""
        from jdev_cli.agents.planner import PlannerAgent, SOPStep

        mock_llm = MagicMock()
        mock_mcp = MagicMock()
        planner = PlannerAgent(mock_llm, mock_mcp)

        step = SOPStep(
            id="step-1",
            role="coder",
            action="Test",
            objective="Test",
            definition_of_done="Test",
            dependencies=["step-0", "step-a", "step-b", "step-c"]  # 4 deps
        )

        score, reasoning, risks = planner._calculate_step_confidence(step, {})

        assert any("dependency" in r.lower() for r in risks)


# =============================================================================
# TESTE 7: CONFIDENCE SUMMARY
# =============================================================================

class TestConfidenceSummary:
    """Testa geração de resumo de confidence."""

    def test_confidence_summary_high(self):
        """Confidence alta deve ter emoji verde."""
        from jdev_cli.agents.planner import PlannerAgent

        mock_llm = MagicMock()
        mock_mcp = MagicMock()
        planner = PlannerAgent(mock_llm, mock_mcp)

        summary = planner._generate_confidence_summary(0.95)

        assert "HIGH CONFIDENCE" in summary

    def test_confidence_summary_moderate(self):
        """Confidence moderada deve ter emoji amarelo."""
        from jdev_cli.agents.planner import PlannerAgent

        mock_llm = MagicMock()
        mock_mcp = MagicMock()
        planner = PlannerAgent(mock_llm, mock_mcp)

        summary = planner._generate_confidence_summary(0.55)

        assert "MODERATE" in summary

    def test_confidence_summary_low(self):
        """Confidence baixa deve ter emoji vermelho."""
        from jdev_cli.agents.planner import PlannerAgent

        mock_llm = MagicMock()
        mock_mcp = MagicMock()
        planner = PlannerAgent(mock_llm, mock_mcp)

        summary = planner._generate_confidence_summary(0.35)

        assert "LOW" in summary


# =============================================================================
# TESTE 8: PLAN.MD ARTIFACT
# =============================================================================

class TestPlanArtifact:
    """Testa geração de plan.md."""

    def test_format_plan_as_markdown(self):
        """_format_plan_as_markdown deve gerar markdown válido."""
        from jdev_cli.agents.planner import PlannerAgent, AgentTask

        mock_llm = MagicMock()
        mock_mcp = MagicMock()
        planner = PlannerAgent(mock_llm, mock_mcp)

        task = AgentTask(request="Implement feature X")
        plan_data = {
            "plan_id": "plan-123",
            "goal": "Implement feature X",
            "strategy_overview": "Sequential execution",
            "confidence_summary": "Good confidence",
            "risk_assessment": "MEDIUM",
            "rollback_strategy": "Git revert",
            "estimated_duration": "30 min",
            "token_budget": 5000,
            "max_parallel_agents": 2,
            "sops": [
                {
                    "id": "step-1",
                    "role": "coder",
                    "action": "Write code",
                    "definition_of_done": "Tests pass",
                    "confidence_score": 0.8
                }
            ]
        }

        markdown = planner._format_plan_as_markdown(plan_data, task)

        assert "# " in markdown  # Has headers
        assert "Implement feature X" in markdown
        assert "- [ ]" in markdown  # Has checkboxes
        assert "step-1" in markdown
        assert "v6.0" in markdown

    @pytest.mark.asyncio
    async def test_generate_plan_artifact_creates_file(self):
        """_generate_plan_artifact deve criar arquivo."""
        from jdev_cli.agents.planner import PlannerAgent, AgentTask

        mock_llm = MagicMock()
        mock_mcp = MagicMock()

        with tempfile.TemporaryDirectory() as tmpdir:
            planner = PlannerAgent(
                mock_llm,
                mock_mcp,
                plan_artifact_dir=tmpdir
            )

            task = AgentTask(request="Test task")
            plan_data = {
                "plan_id": "plan-test",
                "goal": "Test",
                "strategy_overview": "Test",
                "sops": []
            }

            path = await planner._generate_plan_artifact(plan_data, task)

            assert path is not None
            assert Path(path).exists()
            assert path.endswith(".md")


# =============================================================================
# TESTE 9: EXPLORATION MODE
# =============================================================================

class TestExplorationMode:
    """Testa modo de exploração."""

    @pytest.mark.asyncio
    async def test_explore_returns_analysis(self):
        """explore() deve retornar análise."""
        from jdev_cli.agents.planner import (
            PlannerAgent,
            AgentTask
        )

        mock_llm = AsyncMock()
        mock_llm.generate = AsyncMock(return_value='{"understanding": "Test task"}')

        mock_mcp = MagicMock()

        planner = PlannerAgent(mock_llm, mock_mcp)

        task = AgentTask(request="Analyze the codebase")
        response = await planner.explore(task)

        assert response.success is True
        assert response.data["mode"] == "exploration"
        assert "analysis" in response.data

    @pytest.mark.asyncio
    async def test_explore_restricts_capabilities(self):
        """explore() deve restringir para READ_ONLY."""
        from jdev_cli.agents.planner import (
            PlannerAgent,
            AgentTask,
            AgentCapability
        )

        mock_llm = AsyncMock()
        mock_llm.generate = AsyncMock(return_value='{}')
        mock_mcp = MagicMock()

        planner = PlannerAgent(mock_llm, mock_mcp)
        original_caps = planner.capabilities.copy()

        # Track capabilities during exploration
        caps_during_explore = []

        original_gather = planner._gather_context

        async def tracking_gather(task):
            caps_during_explore.extend(planner.capabilities)
            return {}

        planner._gather_context = tracking_gather

        task = AgentTask(request="Test")
        await planner.explore(task)

        # During exploration, only READ_ONLY should be available
        assert AgentCapability.READ_ONLY in caps_during_explore
        assert AgentCapability.FILE_EDIT not in caps_during_explore

        # After exploration, original capabilities should be restored
        assert planner.capabilities == original_caps


# =============================================================================
# TESTE 10: CLARIFYING QUESTIONS GENERATION
# =============================================================================

class TestClarifyingQuestionsGeneration:
    """Testa geração de perguntas clarificadoras."""

    @pytest.mark.asyncio
    async def test_generate_clarifying_questions_with_llm(self):
        """_generate_clarifying_questions deve usar LLM."""
        from jdev_cli.agents.planner import PlannerAgent, AgentTask

        mock_llm = AsyncMock()
        mock_llm.generate = AsyncMock(return_value='''
        {
            "questions": [
                {"question": "What scope?", "category": "scope", "options": ["A", "B"]},
                {"question": "Which approach?", "category": "approach", "options": ["X", "Y"]}
            ]
        }
        ''')
        mock_mcp = MagicMock()

        planner = PlannerAgent(mock_llm, mock_mcp)
        task = AgentTask(request="Implement feature")

        questions = await planner._generate_clarifying_questions(task)

        assert len(questions) == 2
        assert questions[0].question == "What scope?"
        assert questions[1].category == "approach"

    @pytest.mark.asyncio
    async def test_generate_clarifying_questions_fallback(self):
        """_generate_clarifying_questions deve ter fallback."""
        from jdev_cli.agents.planner import PlannerAgent, AgentTask

        mock_llm = AsyncMock()
        mock_llm.generate = AsyncMock(side_effect=Exception("LLM error"))
        mock_mcp = MagicMock()

        planner = PlannerAgent(mock_llm, mock_mcp)
        task = AgentTask(request="Implement feature")

        questions = await planner._generate_clarifying_questions(task)

        # Should return default questions
        assert len(questions) >= 1
        assert any("scope" in q.question.lower() for q in questions)


# =============================================================================
# TESTE 11: EXECUTE WITH CLARIFICATION
# =============================================================================

class TestExecuteWithClarification:
    """Testa execute_with_clarification."""

    @pytest.mark.asyncio
    async def test_execute_with_clarification_basic(self):
        """execute_with_clarification deve funcionar."""
        from jdev_cli.agents.planner import (
            PlannerAgent,
            AgentTask
        )

        mock_llm = AsyncMock()
        # Mock for clarifying questions
        mock_llm.generate = AsyncMock(return_value='{"questions": []}')
        mock_mcp = MagicMock()

        planner = PlannerAgent(mock_llm, mock_mcp, ask_clarifying_questions=False)

        # Mock execute to return a basic response
        planner.execute = AsyncMock(return_value=MagicMock(
            success=True,
            data={"plan": {"plan_id": "test", "sops": []}}
        ))

        task = AgentTask(request="Test task")
        response = await planner.execute_with_clarification(task)

        assert planner.execute.called


# =============================================================================
# TESTE 12: BACKWARD COMPATIBILITY
# =============================================================================

class TestBackwardCompatibility:
    """Testa compatibilidade com código existente."""

    def test_planner_agent_works_without_v6_params(self):
        """PlannerAgent deve funcionar sem parâmetros v6."""
        from jdev_cli.agents.planner import PlannerAgent

        mock_llm = MagicMock()
        mock_mcp = MagicMock()

        # Should work exactly like v5
        planner = PlannerAgent(mock_llm, mock_mcp)

        assert planner.llm_client == mock_llm
        assert planner.mcp_client == mock_mcp

    def test_sop_step_works_without_confidence(self):
        """SOPStep deve funcionar sem campos de confidence."""
        from jdev_cli.agents.planner import SOPStep

        # v5 style creation
        step = SOPStep(
            id="step-1",
            role="coder",
            action="Write code",
            objective="Implement feature",
            definition_of_done="Tests pass"
        )

        # Should have defaults
        assert step.confidence_score == 0.7
        assert step.confidence_reasoning == ""
        assert step.risk_factors == []

    def test_execution_plan_works_without_v6_fields(self):
        """ExecutionPlan deve funcionar sem campos v6."""
        from jdev_cli.agents.planner import ExecutionPlan

        # v5 style creation
        plan = ExecutionPlan(
            plan_id="plan-123",
            goal="Test goal",
            strategy_overview="Sequential"
        )

        # Should have defaults
        assert plan.overall_confidence == 0.7
        assert plan.clarifying_questions == []
        assert plan.plan_artifact_path is None


# =============================================================================
# TESTE 13: MULTI-PLAN DATA MODELS (v6.1)
# =============================================================================

class TestMultiPlanDataModels:
    """Testa os novos modelos de dados v6.1 para Multi-Plan."""

    def test_plan_strategy_enum(self):
        """PlanStrategy deve ter 3 estratégias."""
        from jdev_cli.agents.planner import PlanStrategy

        assert PlanStrategy.STANDARD.value == "standard"
        assert PlanStrategy.ACCELERATOR.value == "accelerator"
        assert PlanStrategy.LATERAL.value == "lateral"

    def test_plan_probabilities_dataclass(self):
        """PlanProbabilities deve calcular scores corretamente."""
        from jdev_cli.agents.planner import PlanProbabilities

        probs = PlanProbabilities(
            success=0.8,
            friction=0.2,
            time_overrun=0.3,
            quality=0.7
        )

        assert probs.success == 0.8
        assert probs.friction == 0.2

        # Test overall_score calculation
        # (0.8 * 0.4) + (0.8 * 0.25) + (0.7 * 0.15) + (0.7 * 0.2)
        expected = 0.8 * 0.4 + 0.8 * 0.25 + 0.7 * 0.15 + 0.7 * 0.2
        assert abs(probs.overall_score - expected) < 0.01

    def test_plan_probabilities_risk_reward(self):
        """PlanProbabilities deve calcular risk/reward ratio."""
        from jdev_cli.agents.planner import PlanProbabilities

        probs = PlanProbabilities(
            success=0.9,
            friction=0.1,
            time_overrun=0.1,
            quality=0.8
        )

        # reward = success * quality = 0.9 * 0.8 = 0.72
        # risk = friction + time_overrun = 0.1 + 0.1 = 0.2
        # ratio = 0.72 / 0.2 = 3.6
        expected_ratio = (0.9 * 0.8) / (0.1 + 0.1)
        assert abs(probs.risk_reward_ratio - expected_ratio) < 0.01

    def test_plan_probabilities_display(self):
        """PlanProbabilities deve formatar para display."""
        from jdev_cli.agents.planner import PlanProbabilities

        probs = PlanProbabilities(
            success=0.85,
            friction=0.15,
            time_overrun=0.2,
            quality=0.9
        )

        display = probs.to_display()

        assert "P(Success)=0.85" in display
        assert "P(Friction)=0.15" in display
        assert "P(Quality)=0.90" in display


# =============================================================================
# TESTE 14: ALTERNATIVE PLAN MODEL
# =============================================================================

class TestAlternativePlan:
    """Testa o modelo AlternativePlan."""

    def test_alternative_plan_creation(self):
        """AlternativePlan deve ser criado corretamente."""
        from jdev_cli.agents.planner import AlternativePlan, PlanStrategy

        plan = AlternativePlan(
            strategy=PlanStrategy.STANDARD,
            name="Safe Approach",
            description="Conservative implementation",
            plan={"sops": []},
            p_success=0.85,
            p_friction=0.2,
            pros=["Low risk", "Easy to understand"],
            cons=["May take longer"],
            best_for="Production critical features"
        )

        assert plan.strategy == PlanStrategy.STANDARD
        assert plan.name == "Safe Approach"
        assert plan.p_success == 0.85
        assert len(plan.pros) == 2

    def test_alternative_plan_probabilities_property(self):
        """AlternativePlan deve expor PlanProbabilities."""
        from jdev_cli.agents.planner import AlternativePlan, PlanStrategy

        plan = AlternativePlan(
            strategy=PlanStrategy.ACCELERATOR,
            name="Fast Track",
            description="Parallel execution",
            plan={},
            p_success=0.7,
            p_friction=0.4,
            p_time_overrun=0.2,
            p_quality=0.6
        )

        probs = plan.probabilities
        assert probs.success == 0.7
        assert probs.friction == 0.4

    def test_alternative_plan_overall_score(self):
        """AlternativePlan deve calcular overall_score."""
        from jdev_cli.agents.planner import AlternativePlan, PlanStrategy

        plan = AlternativePlan(
            strategy=PlanStrategy.LATERAL,
            name="Creative Solution",
            description="Unconventional approach",
            plan={},
            p_success=0.6,
            p_friction=0.5,
            p_time_overrun=0.5,
            p_quality=0.8
        )

        assert 0.0 <= plan.overall_score <= 1.0


# =============================================================================
# TESTE 15: MULTI-PLAN RESULT
# =============================================================================

class TestMultiPlanResult:
    """Testa o modelo MultiPlanResult."""

    def test_multi_plan_result_creation(self):
        """MultiPlanResult deve ser criado corretamente."""
        from jdev_cli.agents.planner import (
            MultiPlanResult,
            AlternativePlan,
            PlanStrategy
        )

        plans = [
            AlternativePlan(
                strategy=PlanStrategy.STANDARD,
                name="Standard",
                description="Safe path",
                plan={},
                p_success=0.8,
                p_friction=0.2
            ),
            AlternativePlan(
                strategy=PlanStrategy.ACCELERATOR,
                name="Fast",
                description="Quick path",
                plan={},
                p_success=0.7,
                p_friction=0.4
            )
        ]

        result = MultiPlanResult(
            task_summary="Implement feature X",
            plans=plans,
            recommended_plan=PlanStrategy.STANDARD,
            recommendation_reasoning="Higher success probability"
        )

        assert len(result.plans) == 2
        assert result.recommended_plan == PlanStrategy.STANDARD

    def test_multi_plan_result_get_plan(self):
        """MultiPlanResult.get_plan deve retornar plano correto."""
        from jdev_cli.agents.planner import (
            MultiPlanResult,
            AlternativePlan,
            PlanStrategy
        )

        plans = [
            AlternativePlan(
                strategy=PlanStrategy.STANDARD,
                name="Standard",
                description="",
                plan={},
                p_success=0.8,
                p_friction=0.2
            ),
            AlternativePlan(
                strategy=PlanStrategy.LATERAL,
                name="Creative",
                description="",
                plan={},
                p_success=0.6,
                p_friction=0.3
            )
        ]

        result = MultiPlanResult(
            task_summary="Test",
            plans=plans,
            recommended_plan=PlanStrategy.STANDARD,
            recommendation_reasoning="Test"
        )

        standard = result.get_plan(PlanStrategy.STANDARD)
        lateral = result.get_plan(PlanStrategy.LATERAL)
        accelerator = result.get_plan(PlanStrategy.ACCELERATOR)

        assert standard.name == "Standard"
        assert lateral.name == "Creative"
        assert accelerator is None  # Not in plans

    def test_multi_plan_result_to_markdown(self):
        """MultiPlanResult.to_markdown deve gerar markdown válido."""
        from jdev_cli.agents.planner import (
            MultiPlanResult,
            AlternativePlan,
            PlanStrategy
        )

        plans = [
            AlternativePlan(
                strategy=PlanStrategy.STANDARD,
                name="Safe Path",
                description="Conservative approach",
                plan={},
                p_success=0.85,
                p_friction=0.15,
                pros=["Low risk"],
                cons=["Slower"],
                best_for="Production"
            )
        ]

        result = MultiPlanResult(
            task_summary="Implement feature",
            plans=plans,
            recommended_plan=PlanStrategy.STANDARD,
            recommendation_reasoning="Best risk/reward"
        )

        markdown = result.to_markdown()

        assert "# " in markdown  # Has headers
        assert "Multi-Plan Analysis" in markdown
        assert "Safe Path" in markdown
        assert "RECOMMENDATION" in markdown
        assert "P(Success)" in markdown


# =============================================================================
# TESTE 16: PLANNER AGENT MULTI-PLAN METHODS
# =============================================================================

class TestPlannerMultiPlan:
    """Testa métodos multi-plan do PlannerAgent."""

    def test_create_fallback_plan(self):
        """_create_fallback_plan deve criar plano básico."""
        from jdev_cli.agents.planner import (
            PlannerAgent,
            AgentTask,
            PlanStrategy
        )

        mock_llm = MagicMock()
        mock_mcp = MagicMock()
        planner = PlannerAgent(mock_llm, mock_mcp)

        fallback = planner._create_fallback_plan(
            AgentTask(request="Test"),
            PlanStrategy.STANDARD
        )

        assert fallback.strategy == PlanStrategy.STANDARD
        assert fallback.name == "Basic Sequential Plan"
        assert "sops" in fallback.plan
        assert len(fallback.plan["sops"]) == 3

    def test_select_best_plan_picks_highest_score(self):
        """_select_best_plan deve escolher maior score."""
        from jdev_cli.agents.planner import (
            PlannerAgent,
            AgentTask,
            AlternativePlan,
            PlanStrategy
        )

        mock_llm = MagicMock()
        mock_mcp = MagicMock()
        planner = PlannerAgent(mock_llm, mock_mcp)

        plans = [
            AlternativePlan(
                strategy=PlanStrategy.STANDARD,
                name="Low",
                description="",
                plan={},
                p_success=0.5,
                p_friction=0.5
            ),
            AlternativePlan(
                strategy=PlanStrategy.ACCELERATOR,
                name="High",
                description="",
                plan={},
                p_success=0.9,
                p_friction=0.1
            )
        ]

        task = AgentTask(request="Test")
        strategy, reasoning = planner._select_best_plan(plans, task)

        assert strategy == PlanStrategy.ACCELERATOR  # Higher score

    def test_build_comparison_summary(self):
        """_build_comparison_summary deve gerar resumo."""
        from jdev_cli.agents.planner import (
            PlannerAgent,
            AlternativePlan,
            PlanStrategy
        )

        mock_llm = MagicMock()
        mock_mcp = MagicMock()
        planner = PlannerAgent(mock_llm, mock_mcp)

        plans = [
            AlternativePlan(
                strategy=PlanStrategy.STANDARD,
                name="Standard",
                description="",
                plan={},
                p_success=0.8,
                p_friction=0.2
            ),
            AlternativePlan(
                strategy=PlanStrategy.LATERAL,
                name="Creative",
                description="",
                plan={},
                p_success=0.6,
                p_friction=0.4
            )
        ]

        summary = planner._build_comparison_summary(plans)

        assert "Plan Comparison:" in summary
        assert "STANDARD" in summary
        assert "LATERAL" in summary
        assert "Score=" in summary

    @pytest.mark.asyncio
    async def test_generate_multi_plan_returns_result(self):
        """generate_multi_plan deve retornar MultiPlanResult."""
        from jdev_cli.agents.planner import (
            PlannerAgent,
            AgentTask,
            MultiPlanResult
        )

        mock_llm = AsyncMock()
        mock_llm.generate = AsyncMock(return_value='''
        {
            "name": "Test Plan",
            "description": "Test",
            "p_success": 0.8,
            "p_friction": 0.2,
            "p_time_overrun": 0.3,
            "p_quality": 0.7,
            "pros": ["Good"],
            "cons": ["Bad"],
            "best_for": "Testing",
            "sops": []
        }
        ''')
        mock_mcp = MagicMock()

        planner = PlannerAgent(mock_llm, mock_mcp)

        task = AgentTask(request="Test task")
        result = await planner.generate_multi_plan(task)

        assert isinstance(result, MultiPlanResult)
        assert len(result.plans) >= 1
        assert result.recommended_plan is not None

    @pytest.mark.asyncio
    async def test_execute_with_multi_plan_auto_select(self):
        """execute_with_multi_plan com auto_select=True."""
        from jdev_cli.agents.planner import PlannerAgent, AgentTask

        mock_llm = AsyncMock()
        mock_llm.generate = AsyncMock(return_value='''
        {
            "name": "Auto Selected",
            "description": "Best plan",
            "p_success": 0.9,
            "p_friction": 0.1,
            "sops": [{"id": "step-1", "role": "coder", "action": "Test"}]
        }
        ''')
        mock_mcp = MagicMock()

        planner = PlannerAgent(mock_llm, mock_mcp)

        task = AgentTask(request="Test task")
        response = await planner.execute_with_multi_plan(task, auto_select=True)

        assert response.success is True
        assert "selected_strategy" in response.data

    @pytest.mark.asyncio
    async def test_execute_with_multi_plan_no_auto_select(self):
        """execute_with_multi_plan com auto_select=False retorna opções."""
        from jdev_cli.agents.planner import PlannerAgent, AgentTask

        mock_llm = AsyncMock()
        mock_llm.generate = AsyncMock(return_value='''
        {
            "name": "Option",
            "description": "A plan option",
            "p_success": 0.7,
            "p_friction": 0.3,
            "sops": []
        }
        ''')
        mock_mcp = MagicMock()

        planner = PlannerAgent(mock_llm, mock_mcp)

        task = AgentTask(request="Test task")
        response = await planner.execute_with_multi_plan(task, auto_select=False)

        assert response.success is True
        assert response.data.get("requires_selection") is True
        assert "multi_plan" in response.data
        assert "markdown" in response.data
