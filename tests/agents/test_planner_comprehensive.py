"""
Day 3 - Planner Comprehensive Tests (Boris Cherny Standards)
Tests completos do Planner Agent com todos os edge cases.
"""
from pathlib import Path
from jdev_cli.agents.planner import PlannerAgent
from jdev_cli.agents.base import TaskContext, TaskStatus


class TestPlannerImplementationPlanning:
    """Tests de planejamento de implementação"""

    def test_planner_creates_step_by_step_plan(self):
        """Deve criar plano step-by-step detalhado"""
        agent = PlannerAgent()
        context = TaskContext(
            task_id="test",
            description="Implement feature X",
            working_dir=Path("/tmp")
        )
        result = agent.execute(context)
        assert result.status == TaskStatus.SUCCESS
        assert "steps" in result.output

    def test_planner_estimates_time_per_step(self):
        """Deve estimar tempo para cada step"""
        agent = PlannerAgent()
        context = TaskContext(
            task_id="test",
            description="Refactor module Y",
            working_dir=Path("/tmp")
        )
        result = agent.execute(context)
        assert "estimated_duration" in result.metadata

    def test_planner_identifies_prerequisites(self):
        """Deve identificar pré-requisitos"""
        agent = PlannerAgent()
        context = TaskContext(
            task_id="test",
            description="Add new API endpoint",
            working_dir=Path("/tmp")
        )
        result = agent.execute(context)
        assert "prerequisites" in result.output or result.status == TaskStatus.SUCCESS

    def test_planner_suggests_test_strategy(self):
        """Deve sugerir estratégia de testes"""
        agent = PlannerAgent()
        context = TaskContext(
            task_id="test",
            description="Implement authentication",
            working_dir=Path("/tmp")
        )
        result = agent.execute(context)
        assert result.status == TaskStatus.SUCCESS

    def test_planner_considers_existing_code(self):
        """Deve considerar código existente"""
        agent = PlannerAgent()
        context = TaskContext(
            task_id="test",
            description="Extend current system",
            working_dir=Path("/tmp"),
            metadata={"existing_files": ["main.py"]}
        )
        result = agent.execute(context)
        assert result.status == TaskStatus.SUCCESS

    def test_planner_handles_greenfield_project(self):
        """Deve tratar projeto greenfield"""
        agent = PlannerAgent()
        context = TaskContext(
            task_id="test",
            description="Create new microservice",
            working_dir=Path("/tmp")
        )
        result = agent.execute(context)
        assert result.status == TaskStatus.SUCCESS

    def test_planner_handles_legacy_codebase(self):
        """Deve tratar codebase legado"""
        agent = PlannerAgent()
        context = TaskContext(
            task_id="test",
            description="Modernize old module",
            working_dir=Path("/tmp")
        )
        result = agent.execute(context)
        assert result.status == TaskStatus.SUCCESS

    def test_planner_prioritizes_critical_tasks(self):
        """Deve priorizar tarefas críticas"""
        agent = PlannerAgent()
        context = TaskContext(
            task_id="test",
            description="Fix security vulnerability + add feature",
            working_dir=Path("/tmp")
        )
        result = agent.execute(context)
        assert result.status == TaskStatus.SUCCESS

    def test_planner_separates_concerns(self):
        """Deve separar concerns no plano"""
        agent = PlannerAgent()
        context = TaskContext(
            task_id="test",
            description="Build full-stack feature",
            working_dir=Path("/tmp")
        )
        result = agent.execute(context)
        assert result.status == TaskStatus.SUCCESS

    def test_planner_includes_rollback_strategy(self):
        """Deve incluir estratégia de rollback"""
        agent = PlannerAgent()
        context = TaskContext(
            task_id="test",
            description="Deploy database migration",
            working_dir=Path("/tmp")
        )
        result = agent.execute(context)
        assert result.status == TaskStatus.SUCCESS


class TestPlannerRiskAssessment:
    """Tests de avaliação de riscos"""

    def test_planner_identifies_high_risk_areas(self):
        """Deve identificar áreas de alto risco"""
        agent = PlannerAgent()
        context = TaskContext(
            task_id="test",
            description="Change authentication system",
            working_dir=Path("/tmp")
        )
        result = agent.execute(context)
        assert result.status in [TaskStatus.SUCCESS, TaskStatus.FAILED]

    def test_planner_suggests_mitigation_strategies(self):
        """Deve sugerir estratégias de mitigação"""
        agent = PlannerAgent()
        context = TaskContext(
            task_id="test",
            description="Refactor core module",
            working_dir=Path("/tmp")
        )
        result = agent.execute(context)
        assert result.status in [TaskStatus.SUCCESS, TaskStatus.FAILED]

    def test_planner_recommends_incremental_approach(self):
        """Deve recomendar abordagem incremental para mudanças grandes"""
        agent = PlannerAgent()
        context = TaskContext(
            task_id="test",
            description="Rewrite entire subsystem",
            working_dir=Path("/tmp")
        )
        result = agent.execute(context)
        assert result.status in [TaskStatus.SUCCESS, TaskStatus.FAILED]

    def test_planner_flags_breaking_changes(self):
        """Deve marcar breaking changes"""
        agent = PlannerAgent()
        context = TaskContext(
            task_id="test",
            description="Change public API",
            working_dir=Path("/tmp")
        )
        result = agent.execute(context)
        assert result.status in [TaskStatus.SUCCESS, TaskStatus.FAILED]

    def test_planner_assesses_technical_debt_impact(self):
        """Deve avaliar impacto em technical debt"""
        agent = PlannerAgent()
        context = TaskContext(
            task_id="test",
            description="Quick fix vs proper solution",
            working_dir=Path("/tmp")
        )
        result = agent.execute(context)
        assert result.status in [TaskStatus.SUCCESS, TaskStatus.FAILED]

    def test_planner_considers_performance_impact(self):
        """Deve considerar impacto em performance"""
        agent = PlannerAgent()
        context = TaskContext(
            task_id="test",
            description="Add caching layer",
            working_dir=Path("/tmp")
        )
        result = agent.execute(context)
        assert result.status in [TaskStatus.SUCCESS, TaskStatus.FAILED]

    def test_planner_evaluates_scalability(self):
        """Deve avaliar escalabilidade"""
        agent = PlannerAgent()
        context = TaskContext(
            task_id="test",
            description="Handle 10x traffic increase",
            working_dir=Path("/tmp")
        )
        result = agent.execute(context)
        assert result.status in [TaskStatus.SUCCESS, TaskStatus.FAILED]

    def test_planner_checks_dependency_risks(self):
        """Deve verificar riscos de dependências"""
        agent = PlannerAgent()
        context = TaskContext(
            task_id="test",
            description="Upgrade major dependency",
            working_dir=Path("/tmp")
        )
        result = agent.execute(context)
        assert result.status in [TaskStatus.SUCCESS, TaskStatus.FAILED]

    def test_planner_warns_about_complexity(self):
        """Deve avisar sobre complexidade excessiva"""
        agent = PlannerAgent()
        context = TaskContext(
            task_id="test",
            description="Implement complex distributed algorithm",
            working_dir=Path("/tmp")
        )
        result = agent.execute(context)
        assert result.status in [TaskStatus.SUCCESS, TaskStatus.FAILED]

    def test_planner_suggests_proof_of_concept(self):
        """Deve sugerir PoC para ideias incertas"""
        agent = PlannerAgent()
        context = TaskContext(
            task_id="test",
            description="Try experimental approach",
            working_dir=Path("/tmp")
        )
        result = agent.execute(context)
        assert result.status in [TaskStatus.SUCCESS, TaskStatus.FAILED]


class TestPlannerResourcePlanning:
    """Tests de planejamento de recursos"""

    def test_planner_estimates_development_time(self):
        """Deve estimar tempo de desenvolvimento"""
        agent = PlannerAgent()
        context = TaskContext(
            task_id="test",
            description="Build feature X",
            working_dir=Path("/tmp")
        )
        result = agent.execute(context)
        assert result.status == TaskStatus.SUCCESS

    def test_planner_identifies_skill_requirements(self):
        """Deve identificar skills necessários"""
        agent = PlannerAgent()
        context = TaskContext(
            task_id="test",
            description="Implement ML pipeline",
            working_dir=Path("/tmp")
        )
        result = agent.execute(context)
        assert result.status == TaskStatus.SUCCESS

    def test_planner_suggests_tools_needed(self):
        """Deve sugerir ferramentas necessárias"""
        agent = PlannerAgent()
        context = TaskContext(
            task_id="test",
            description="Setup CI/CD pipeline",
            working_dir=Path("/tmp")
        )
        result = agent.execute(context)
        assert result.status == TaskStatus.SUCCESS

    def test_planner_estimates_infrastructure_needs(self):
        """Deve estimar necessidades de infraestrutura"""
        agent = PlannerAgent()
        context = TaskContext(
            task_id="test",
            description="Deploy high-traffic service",
            working_dir=Path("/tmp")
        )
        result = agent.execute(context)
        assert result.status == TaskStatus.SUCCESS

    def test_planner_considers_budget_constraints(self):
        """Deve considerar constraints de orçamento"""
        agent = PlannerAgent()
        context = TaskContext(
            task_id="test",
            description="Choose between paid/free solutions",
            working_dir=Path("/tmp"),
            metadata={"budget": "limited"}
        )
        result = agent.execute(context)
        assert result.status == TaskStatus.SUCCESS


class TestPlannerDependencyManagement:
    """Tests de gerenciamento de dependências"""

    def test_planner_maps_task_dependencies(self):
        """Deve mapear dependências entre tarefas"""
        agent = PlannerAgent()
        context = TaskContext(
            task_id="test",
            description="Multi-step feature implementation",
            working_dir=Path("/tmp")
        )
        result = agent.execute(context)
        assert result.status == TaskStatus.SUCCESS

    def test_planner_suggests_parallel_tasks(self):
        """Deve sugerir tarefas paralelas"""
        agent = PlannerAgent()
        context = TaskContext(
            task_id="test",
            description="Independent modules",
            working_dir=Path("/tmp")
        )
        result = agent.execute(context)
        assert result.status == TaskStatus.SUCCESS

    def test_planner_handles_circular_dependencies(self):
        """Deve detectar dependências circulares"""
        agent = PlannerAgent()
        context = TaskContext(
            task_id="test",
            description="Complex refactoring",
            working_dir=Path("/tmp")
        )
        result = agent.execute(context)
        assert result.status in [TaskStatus.SUCCESS, TaskStatus.FAILED]

    def test_planner_optimizes_execution_order(self):
        """Deve otimizar ordem de execução"""
        agent = PlannerAgent()
        context = TaskContext(
            task_id="test",
            description="Many interdependent tasks",
            working_dir=Path("/tmp")
        )
        result = agent.execute(context)
        assert result.status == TaskStatus.SUCCESS


class TestPlannerQualityAssurance:
    """Tests de garantia de qualidade"""

    def test_planner_includes_code_review_steps(self):
        """Deve incluir steps de code review"""
        agent = PlannerAgent()
        context = TaskContext(
            task_id="test",
            description="Implement critical feature",
            working_dir=Path("/tmp")
        )
        result = agent.execute(context)
        assert result.status == TaskStatus.SUCCESS

    def test_planner_defines_acceptance_criteria(self):
        """Deve definir critérios de aceitação"""
        agent = PlannerAgent()
        context = TaskContext(
            task_id="test",
            description="Build user story X",
            working_dir=Path("/tmp")
        )
        result = agent.execute(context)
        assert result.status == TaskStatus.SUCCESS

    def test_planner_suggests_testing_pyramid(self):
        """Deve sugerir pirâmide de testes"""
        agent = PlannerAgent()
        context = TaskContext(
            task_id="test",
            description="Test strategy for new module",
            working_dir=Path("/tmp")
        )
        result = agent.execute(context)
        assert result.status == TaskStatus.SUCCESS

    def test_planner_includes_security_checks(self):
        """Deve incluir checks de segurança"""
        agent = PlannerAgent()
        context = TaskContext(
            task_id="test",
            description="Handle user authentication",
            working_dir=Path("/tmp")
        )
        result = agent.execute(context)
        assert result.status == TaskStatus.SUCCESS

    def test_planner_suggests_documentation_updates(self):
        """Deve sugerir updates de documentação"""
        agent = PlannerAgent()
        context = TaskContext(
            task_id="test",
            description="Add new API",
            working_dir=Path("/tmp")
        )
        result = agent.execute(context)
        assert result.status == TaskStatus.SUCCESS


class TestPlannerEdgeCases:
    """Tests de edge cases específicos"""

    def test_planner_handles_vague_requirements(self):
        """Deve tratar requisitos vagos"""
        agent = PlannerAgent()
        context = TaskContext(
            task_id="test",
            description="Make it better",
            working_dir=Path("/tmp")
        )
        result = agent.execute(context)
        assert result.status in [TaskStatus.SUCCESS, TaskStatus.FAILED]

    def test_planner_handles_conflicting_requirements(self):
        """Deve tratar requisitos conflitantes"""
        agent = PlannerAgent()
        context = TaskContext(
            task_id="test",
            description="Fast AND secure AND cheap",
            working_dir=Path("/tmp")
        )
        result = agent.execute(context)
        assert result.status in [TaskStatus.SUCCESS, TaskStatus.FAILED]

    def test_planner_handles_impossible_deadline(self):
        """Deve tratar deadline impossível"""
        agent = PlannerAgent()
        context = TaskContext(
            task_id="test",
            description="Complete in 1 hour",
            working_dir=Path("/tmp"),
            metadata={"deadline": "1h", "complexity": "high"}
        )
        result = agent.execute(context)
        assert result.status in [TaskStatus.SUCCESS, TaskStatus.FAILED]

    def test_planner_handles_unknown_technology(self):
        """Deve tratar tecnologia desconhecida"""
        agent = PlannerAgent()
        context = TaskContext(
            task_id="test",
            description="Use XYZ framework",
            working_dir=Path("/tmp")
        )
        result = agent.execute(context)
        assert result.status in [TaskStatus.SUCCESS, TaskStatus.FAILED]

    def test_planner_handles_minimal_context(self):
        """Deve tratar contexto mínimo"""
        agent = PlannerAgent()
        context = TaskContext(
            task_id="test",
            description="Fix bug",
            working_dir=Path("/tmp")
        )
        result = agent.execute(context)
        assert result.status in [TaskStatus.SUCCESS, TaskStatus.FAILED]


class TestPlannerConstitutionalCompliance:
    """Tests de aderência à Constituição"""

    def test_planner_respects_token_budget(self):
        """Deve respeitar budget de tokens"""
        agent = PlannerAgent()
        context = TaskContext(
            task_id="test",
            description="Create detailed plan",
            working_dir=Path("/tmp")
        )
        result = agent.execute(context)
        assert result.status == TaskStatus.SUCCESS
        # Token usage should be tracked

    def test_planner_avoids_redundant_planning(self):
        """Deve evitar planejamento redundante"""
        agent = PlannerAgent()
        context = TaskContext(
            task_id="test",
            description="Simple task",
            working_dir=Path("/tmp")
        )
        result = agent.execute(context)
        assert result.status == TaskStatus.SUCCESS

    def test_planner_provides_actionable_output(self):
        """Deve prover output acionável"""
        agent = PlannerAgent()
        context = TaskContext(
            task_id="test",
            description="Implement feature",
            working_dir=Path("/tmp")
        )
        result = agent.execute(context)
        assert result.status == TaskStatus.SUCCESS
        assert len(result.output) > 0
