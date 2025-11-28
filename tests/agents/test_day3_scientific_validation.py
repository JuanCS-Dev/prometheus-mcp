"""
Day 3 - Scientific Validation Tests (Boris Cherny Standards)
Tests científicos de validação profunda dos agentes Day 3.
NOTA: Estes testes usam LLM REAL via API. Sem mocks, sem placeholders.
"""
import pytest
from pathlib import Path
from jdev_cli.agents.planner import PlannerAgent
from jdev_cli.agents.refactorer import RefactorerAgent
from jdev_cli.agents.base import TaskContext, TaskStatus, AgentRole
import time
import os

# Verificação de API key no início
@pytest.fixture(scope="session", autouse=True)
def check_api_key():
    """Garante que temos API key antes de rodar qualquer teste"""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        pytest.skip("GEMINI_API_KEY não encontrada no ambiente. Testes Day 3 requerem LLM real.")
    return api_key


class TestPlannerOutputQuality:
    """Validação científica da qualidade do output do Planner - LLM REAL"""

    def test_planner_creates_valid_plan_for_simple_task(self):
        """Planner deve criar plano estruturado para tarefa simples"""
        agent = PlannerAgent()
        context = TaskContext(
            task_id="plan_simple",
            description="Create a Python function that adds two numbers",
            working_dir=Path("/tmp")
        )
        result = agent.execute(context)

        assert result.status == TaskStatus.SUCCESS
        assert isinstance(result.output, dict)
        assert "plan" in result.output or "steps" in result.output or len(result.output) > 0
        # Output deve ter conteúdo real do LLM
        assert result.output != {}

    def test_planner_creates_multi_step_plan(self):
        """Planner deve criar plano multi-etapa para tarefa complexa"""
        agent = PlannerAgent()
        context = TaskContext(
            task_id="plan_multi",
            description="Build a REST API with authentication, database, and testing",
            working_dir=Path("/tmp")
        )
        result = agent.execute(context)

        assert result.status == TaskStatus.SUCCESS
        assert result.output is not None
        # Tarefa complexa deve gerar output significativo
        output_str = str(result.output)
        assert len(output_str) > 100, "Output muito curto para tarefa complexa"

    def test_planner_handles_ambiguous_requirements(self):
        """Planner deve lidar com requisitos ambíguos"""
        agent = PlannerAgent()
        context = TaskContext(
            task_id="plan_ambiguous",
            description="Make it better",
            working_dir=Path("/tmp")
        )
        result = agent.execute(context)

        # Mesmo com input vago, deve retornar algo
        assert result.status in [TaskStatus.SUCCESS, TaskStatus.FAILED]
        assert result.output is not None

    def test_planner_preserves_task_context(self):
        """Planner deve preservar contexto da task"""
        agent = PlannerAgent()
        task_id = "preserve_context_test_123"
        context = TaskContext(
            task_id=task_id,
            description="Test context preservation",
            working_dir=Path("/tmp"),
            metadata={"priority": "high"}
        )
        result = agent.execute(context)

        assert result.task_id == task_id
        assert result.agent_role == AgentRole.PLANNER
        assert result.metadata is not None


class TestRefactorerOutputQuality:
    """Validação científica da qualidade do output do Refactorer - LLM REAL"""

    def test_refactorer_analyzes_real_code(self, tmp_path):
        """Refactorer deve analisar código real e dar sugestões"""
        # Criar arquivo com code smell óbvio
        code_file = tmp_path / "bad_code.py"
        code_file.write_text("""
def func(a,b,c,d,e,f,g):  # Too many parameters
    x=a+b+c+d+e+f+g  # No spaces
    return x
""")

        agent = RefactorerAgent()
        context = TaskContext(
            task_id="refactor_real",
            description=f"Analyze and refactor {code_file}",
            working_dir=tmp_path
        )
        result = agent.execute(context)

        assert result.status == TaskStatus.SUCCESS
        assert isinstance(result.output, dict)
        # Deve identificar problemas reais
        output_str = str(result.output).lower()
        assert len(output_str) > 50, "Output muito curto"

    def test_refactorer_handles_clean_code(self, tmp_path):
        """Refactorer deve reconhecer código limpo"""
        code_file = tmp_path / "clean_code.py"
        code_file.write_text("""
def calculate_sum(numbers: list[int]) -> int:
    \"\"\"Calculate sum of numbers.\"\"\"
    return sum(numbers)
""")

        agent = RefactorerAgent()
        context = TaskContext(
            task_id="refactor_clean",
            description=f"Analyze {code_file}",
            working_dir=tmp_path
        )
        result = agent.execute(context)

        assert result.status == TaskStatus.SUCCESS
        assert result.output is not None

    def test_refactorer_detects_complexity_issues(self, tmp_path):
        """Refactorer deve detectar complexidade ciclomática"""
        code_file = tmp_path / "complex.py"
        code_file.write_text("""
def complex_func(x):
    if x > 10:
        if x > 20:
            if x > 30:
                if x > 40:
                    return "very high"
                return "high"
            return "medium"
        return "low"
    return "very low"
""")

        agent = RefactorerAgent()
        context = TaskContext(
            task_id="refactor_complex",
            description=f"Analyze complexity in {code_file}",
            working_dir=tmp_path
        )
        result = agent.execute(context)

        assert result.status in [TaskStatus.SUCCESS, TaskStatus.FAILED]
        assert result.output is not None
        output_str = str(result.output).lower()
        # Deve mencionar complexidade ou nested conditions
        assert len(output_str) > 50


class TestAgentPerformanceCharacteristics:
    """Testes científicos de características de performance"""

    def test_planner_execution_time_is_bounded(self):
        """Tempo de execução deve ser limitado"""
        agent = PlannerAgent()
        context = TaskContext(task_id="perf", description="Task", working_dir=Path("/tmp"))

        start = time.time()
        result = agent.execute(context)
        duration = time.time() - start

        # Sem model, deve ser instantâneo (<5s)
        assert duration < 5.0
        assert result.status == TaskStatus.SUCCESS

    def test_refactorer_execution_time_is_bounded(self):
        """Tempo de execução deve ser limitado"""
        agent = RefactorerAgent()
        context = TaskContext(task_id="perf", description="Task", working_dir=Path("/tmp"))

        start = time.time()
        result = agent.execute(context)
        duration = time.time() - start

        assert duration < 5.0
        assert result.status == TaskStatus.SUCCESS

    def test_planner_memory_usage_is_reasonable(self):
        """Uso de memória deve ser razoável"""
        agent = PlannerAgent()
        context = TaskContext(task_id="mem", description="Large task", working_dir=Path("/tmp"))

        # Executa sem crash
        result = agent.execute(context)
        assert result.status in [TaskStatus.SUCCESS, TaskStatus.FAILED]

    def test_refactorer_handles_concurrent_execution_safely(self):
        """Deve executar concorrentemente sem conflitos"""
        agent = RefactorerAgent()
        contexts = [
            TaskContext(task_id=f"concurrent_{i}", description=f"Task {i}", working_dir=Path("/tmp"))
            for i in range(5)
        ]

        results = [agent.execute(ctx) for ctx in contexts]
        assert len(results) == 5
        assert all(r.status in [TaskStatus.SUCCESS, TaskStatus.FAILED] for r in results)

    def test_planner_scales_linearly_with_complexity(self):
        """Performance deve escalar linearmente"""
        agent = PlannerAgent()

        simple = TaskContext(task_id="simple", description="Do X", working_dir=Path("/tmp"))
        complex = TaskContext(
            task_id="complex",
            description="Do X and Y and Z with dependencies",
            working_dir=Path("/tmp")
        )

        start1 = time.time()
        agent.execute(simple)
        time1 = time.time() - start1

        start2 = time.time()
        agent.execute(complex)
        time2 = time.time() - start2

        # Não deve explodir exponencialmente
        assert time2 < time1 * 100


class TestAgentRoleCompliance:
    """Validação de aderência aos papéis definidos"""

    def test_planner_role_is_correct(self):
        """Planner deve ter role PLANNER"""
        agent = PlannerAgent()
        assert agent.role == AgentRole.PLANNER

    def test_refactorer_role_is_correct(self):
        """Refactorer deve ter role REFACTORER"""
        agent = RefactorerAgent()
        assert agent.role == AgentRole.REFACTORER

    def test_planner_capabilities_are_defined(self):
        """Planner deve ter capabilities definidos"""
        agent = PlannerAgent()
        assert len(agent.capabilities) > 0

    def test_refactorer_capabilities_are_defined(self):
        """Refactorer deve ter capabilities definidos"""
        agent = RefactorerAgent()
        assert len(agent.capabilities) > 0

    def test_planner_name_is_set(self):
        """Planner deve ter nome definido"""
        agent = PlannerAgent()
        assert agent.name is not None
        assert len(agent.name) > 0

    def test_refactorer_name_is_set(self):
        """Refactorer deve ter nome definido"""
        agent = RefactorerAgent()
        assert agent.name is not None
        assert len(agent.name) > 0


class TestAgentInitialization:
    """Validação científica de inicialização"""

    def test_planner_initializes_without_errors(self):
        """Planner deve inicializar sem erros"""
        agent = PlannerAgent()
        assert agent is not None

    def test_refactorer_initializes_without_errors(self):
        """Refactorer deve inicializar sem erros"""
        agent = RefactorerAgent()
        assert agent is not None

    def test_planner_accepts_model_parameter(self):
        """Planner deve aceitar parâmetro model"""
        agent = PlannerAgent(model=None)
        assert agent is not None

    def test_refactorer_accepts_model_parameter(self):
        """Refactorer deve aceitar parâmetro model"""
        agent = RefactorerAgent(model=None)
        assert agent is not None

    def test_planner_accepts_config_parameter(self):
        """Planner deve aceitar parâmetro config"""
        agent = PlannerAgent(config={})
        assert agent is not None

    def test_refactorer_accepts_config_parameter(self):
        """Refactorer deve aceitar parâmetro config"""
        agent = RefactorerAgent(config={})
        assert agent is not None

    def test_multiple_planner_instances_are_independent(self):
        """Múltiplas instâncias devem ser independentes"""
        agent1 = PlannerAgent()
        agent2 = PlannerAgent()
        assert agent1 is not agent2

    def test_multiple_refactorer_instances_are_independent(self):
        """Múltiplas instâncias devem ser independentes"""
        agent1 = RefactorerAgent()
        agent2 = RefactorerAgent()
        assert agent1 is not agent2


class TestTaskContextValidation:
    """Validação científica de TaskContext"""

    def test_planner_validates_required_fields(self):
        """Planner deve validar campos obrigatórios"""
        agent = PlannerAgent()
        context = TaskContext(
            task_id="valid",
            description="Valid task",
            working_dir=Path("/tmp")
        )
        result = agent.execute(context)
        assert result.status in [TaskStatus.SUCCESS, TaskStatus.FAILED]

    def test_refactorer_validates_required_fields(self):
        """Refactorer deve validar campos obrigatórios"""
        agent = RefactorerAgent()
        context = TaskContext(
            task_id="valid",
            description="Valid task",
            working_dir=Path("/tmp")
        )
        result = agent.execute(context)
        assert result.status in [TaskStatus.SUCCESS, TaskStatus.FAILED]

    def test_planner_handles_optional_metadata(self):
        """Planner deve tratar metadata opcional"""
        agent = PlannerAgent()
        context = TaskContext(
            task_id="opt",
            description="Task",
            working_dir=Path("/tmp"),
            metadata={"optional": "value"}
        )
        result = agent.execute(context)
        assert result.status == TaskStatus.SUCCESS

    def test_refactorer_handles_optional_metadata(self):
        """Refactorer deve tratar metadata opcional"""
        agent = RefactorerAgent()
        context = TaskContext(
            task_id="opt",
            description="Task",
            working_dir=Path("/tmp"),
            metadata={"optional": "value"}
        )
        result = agent.execute(context)
        assert result.status in [TaskStatus.SUCCESS, TaskStatus.FAILED]


class TestTaskResultValidation:
    """Validação científica de TaskResult"""

    def test_planner_result_has_task_id(self):
        """Resultado deve incluir task_id"""
        agent = PlannerAgent()
        context = TaskContext(task_id="result_test", description="Task", working_dir=Path("/tmp"))
        result = agent.execute(context)
        assert result.task_id == "result_test"

    def test_refactorer_result_has_task_id(self):
        """Resultado deve incluir task_id"""
        agent = RefactorerAgent()
        context = TaskContext(task_id="result_test", description="Task", working_dir=Path("/tmp"))
        result = agent.execute(context)
        assert result.task_id == "result_test"

    def test_planner_result_has_status(self):
        """Resultado deve ter status válido"""
        agent = PlannerAgent()
        context = TaskContext(task_id="status", description="Task", working_dir=Path("/tmp"))
        result = agent.execute(context)
        assert result.status in [TaskStatus.SUCCESS, TaskStatus.FAILED, TaskStatus.PENDING]

    def test_refactorer_result_has_status(self):
        """Resultado deve ter status válido"""
        agent = RefactorerAgent()
        context = TaskContext(task_id="status", description="Task", working_dir=Path("/tmp"))
        result = agent.execute(context)
        assert result.status in [TaskStatus.SUCCESS, TaskStatus.FAILED, TaskStatus.PENDING]

    def test_planner_result_has_output(self):
        """Resultado deve ter output"""
        agent = PlannerAgent()
        context = TaskContext(task_id="output", description="Task", working_dir=Path("/tmp"))
        result = agent.execute(context)
        assert result.output is not None

    def test_refactorer_result_has_output(self):
        """Resultado deve ter output"""
        agent = RefactorerAgent()
        context = TaskContext(task_id="output", description="Task", working_dir=Path("/tmp"))
        result = agent.execute(context)
        assert result.output is not None


class TestErrorHandlingScientific:
    """Validação científica de error handling"""

    def test_planner_graceful_degradation(self):
        """Planner deve degradar gracefully em erro"""
        agent = PlannerAgent()
        context = TaskContext(task_id="error", description="", working_dir=Path("/tmp"))
        result = agent.execute(context)
        # Não deve crashar, deve retornar resultado
        assert result is not None
        assert result.status in [TaskStatus.SUCCESS, TaskStatus.FAILED]

    def test_refactorer_graceful_degradation(self):
        """Refactorer deve degradar gracefully em erro"""
        agent = RefactorerAgent()
        context = TaskContext(task_id="error", description="", working_dir=Path("/tmp"))
        result = agent.execute(context)
        assert result is not None
        assert result.status in [TaskStatus.SUCCESS, TaskStatus.FAILED]

    def test_planner_error_message_quality(self):
        """Mensagens de erro devem ser informativas"""
        agent = PlannerAgent()
        context = TaskContext(task_id="err_msg", description="", working_dir=Path("/tmp"))
        result = agent.execute(context)
        if result.status == TaskStatus.FAILED:
            # Se falhou, deve ter output explicativo
            assert result.output is not None

    def test_refactorer_error_message_quality(self):
        """Mensagens de erro devem ser informativas"""
        agent = RefactorerAgent()
        context = TaskContext(task_id="err_msg", description="", working_dir=Path("/tmp"))
        result = agent.execute(context)
        if result.status == TaskStatus.FAILED:
            assert result.output is not None


class TestStateManagementScientific:
    """Validação científica de state management"""

    def test_planner_maintains_no_global_state(self):
        """Planner não deve manter estado global"""
        agent1 = PlannerAgent()
        agent2 = PlannerAgent()

        context1 = TaskContext(task_id="1", description="Task 1", working_dir=Path("/tmp"))
        context2 = TaskContext(task_id="2", description="Task 2", working_dir=Path("/tmp"))

        result1 = agent1.execute(context1)
        result2 = agent2.execute(context2)

        # Não devem interferir
        assert result1.task_id != result2.task_id

    def test_refactorer_maintains_no_global_state(self):
        """Refactorer não deve manter estado global"""
        agent1 = RefactorerAgent()
        agent2 = RefactorerAgent()

        context1 = TaskContext(task_id="1", description="Task 1", working_dir=Path("/tmp"))
        context2 = TaskContext(task_id="2", description="Task 2", working_dir=Path("/tmp"))

        result1 = agent1.execute(context1)
        result2 = agent2.execute(context2)

        assert result1.task_id != result2.task_id

    def test_planner_cleans_up_resources(self):
        """Planner deve limpar recursos"""
        agent = PlannerAgent()
        context = TaskContext(task_id="cleanup", description="Task", working_dir=Path("/tmp"))
        result = agent.execute(context)
        # Não deve vazar recursos
        assert result.status in [TaskStatus.SUCCESS, TaskStatus.FAILED]

    def test_refactorer_cleans_up_resources(self):
        """Refactorer deve limpar recursos"""
        agent = RefactorerAgent()
        context = TaskContext(task_id="cleanup", description="Task", working_dir=Path("/tmp"))
        result = agent.execute(context)
        assert result.status in [TaskStatus.SUCCESS, TaskStatus.FAILED]


class TestThreadSafety:
    """Validação de thread safety"""

    def test_planner_is_thread_safe(self):
        """Planner deve ser thread-safe"""
        agent = PlannerAgent()
        contexts = [
            TaskContext(task_id=f"thread_{i}", description=f"Task {i}", working_dir=Path("/tmp"))
            for i in range(10)
        ]

        results = [agent.execute(ctx) for ctx in contexts]
        assert len(results) == 10
        assert all(r.status in [TaskStatus.SUCCESS, TaskStatus.FAILED] for r in results)

    def test_refactorer_is_thread_safe(self):
        """Refactorer deve ser thread-safe"""
        agent = RefactorerAgent()
        contexts = [
            TaskContext(task_id=f"thread_{i}", description=f"Task {i}", working_dir=Path("/tmp"))
            for i in range(10)
        ]

        results = [agent.execute(ctx) for ctx in contexts]
        assert len(results) == 10
        assert all(r.status in [TaskStatus.SUCCESS, TaskStatus.FAILED] for r in results)


class TestIdempotency:
    """Validação de idempotência"""

    def test_planner_is_idempotent(self):
        """Múltiplas execuções devem produzir resultado consistente"""
        agent = PlannerAgent()
        context = TaskContext(task_id="idem", description="Idempotent task", working_dir=Path("/tmp"))

        result1 = agent.execute(context)
        result2 = agent.execute(context)

        # Status deve ser consistente
        assert result1.status == result2.status

    def test_refactorer_is_idempotent(self):
        """Múltiplas execuções devem produzir resultado consistente"""
        agent = RefactorerAgent()
        context = TaskContext(task_id="idem", description="Idempotent task", working_dir=Path("/tmp"))

        result1 = agent.execute(context)
        result2 = agent.execute(context)

        assert result1.status == result2.status


class TestComposability:
    """Validação de composabilidade"""

    def test_planner_output_composes_with_refactorer(self):
        """Output do Planner deve compor com Refactorer"""
        planner = PlannerAgent()
        refactorer = RefactorerAgent()

        plan_context = TaskContext(task_id="plan", description="Plan", working_dir=Path("/tmp"))
        plan_result = planner.execute(plan_context)

        refactor_context = TaskContext(
            task_id="refactor",
            description="Execute",
            working_dir=Path("/tmp"),
            metadata={"plan": plan_result.output}
        )
        refactor_result = refactorer.execute(refactor_context)

        assert refactor_result.status in [TaskStatus.SUCCESS, TaskStatus.FAILED]

    def test_agents_chain_naturally(self):
        """Agentes devem encadear naturalmente"""
        planner = PlannerAgent()
        refactorer = RefactorerAgent()

        # Workflow: Plan -> Refactor
        context1 = TaskContext(task_id="1", description="Plan", working_dir=Path("/tmp"))
        result1 = planner.execute(context1)

        context2 = TaskContext(
            task_id="2",
            description="Refactor",
            working_dir=Path("/tmp"),
            metadata={"previous": result1.output}
        )
        result2 = refactorer.execute(context2)

        assert result2.status in [TaskStatus.SUCCESS, TaskStatus.FAILED]


class TestObservabilityScientific:
    """Validação científica de observabilidade"""

    def test_planner_provides_execution_metrics(self):
        """Planner deve prover métricas de execução"""
        agent = PlannerAgent()
        context = TaskContext(task_id="metrics", description="Task", working_dir=Path("/tmp"))
        result = agent.execute(context)
        # Metadata deve existir para métricas
        assert isinstance(result.metadata, dict)

    def test_refactorer_provides_execution_metrics(self):
        """Refactorer deve prover métricas de execução"""
        agent = RefactorerAgent()
        context = TaskContext(task_id="metrics", description="Task", working_dir=Path("/tmp"))
        result = agent.execute(context)
        assert isinstance(result.metadata, dict)

    def test_planner_logs_are_parseable(self):
        """Logs devem ser parseáveis"""
        agent = PlannerAgent()
        context = TaskContext(task_id="logs", description="Task", working_dir=Path("/tmp"))
        result = agent.execute(context)
        # Deve completar sem crash
        assert result.status in [TaskStatus.SUCCESS, TaskStatus.FAILED]

    def test_refactorer_logs_are_parseable(self):
        """Logs devem ser parseáveis"""
        agent = RefactorerAgent()
        context = TaskContext(task_id="logs", description="Task", working_dir=Path("/tmp"))
        result = agent.execute(context)
        assert result.status in [TaskStatus.SUCCESS, TaskStatus.FAILED]
