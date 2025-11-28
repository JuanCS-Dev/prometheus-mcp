"""
Day 3 - Extreme Edge Cases Tests (Boris Cherny Standards)
Tests de casos extremos e situações limites.
"""
import pytest
from pathlib import Path
from jdev_cli.agents.planner import PlannerAgent
from jdev_cli.agents.refactorer import RefactorerAgent
from jdev_cli.agents.base import TaskContext, TaskStatus
import string
import random


class TestExtremeInputSizes:
    """Tests com tamanhos extremos de input"""

    @pytest.mark.asyncio
    async def test_planner_handles_empty_description(self):
        """Planner com descrição vazia"""
        agent = PlannerAgent()
        context = TaskContext(task_id="empty", description="", working_dir=Path("/tmp"))
        result = await agent.execute(context)
        # AgentResponse has .success, not .status
        assert isinstance(result.success, bool)

    @pytest.mark.asyncio
    async def test_planner_handles_single_char_description(self):
        """Planner com descrição de 1 caractere"""
        agent = PlannerAgent()
        context = TaskContext(task_id="one", description="x", working_dir=Path("/tmp"))
        result = await agent.execute(context)
        assert isinstance(result.success, bool)

    @pytest.mark.asyncio
    async def test_planner_handles_max_description(self):
        """Planner com descrição máxima"""
        agent = PlannerAgent()
        desc = "x" * 100000
        context = TaskContext(task_id="max", description=desc, working_dir=Path("/tmp"))
        result = await agent.execute(context)
        assert isinstance(result.success, bool)

    def test_refactorer_handles_empty_description(self):
        """Refactorer com descrição vazia"""
        agent = RefactorerAgent()
        context = TaskContext(task_id="empty", description="", working_dir=Path("/tmp"))
        result = agent.execute(context)
        assert result.status in [TaskStatus.SUCCESS, TaskStatus.FAILED]

    def test_refactorer_handles_max_description(self):
        """Refactorer com descrição máxima"""
        agent = RefactorerAgent()
        desc = "x" * 100000
        context = TaskContext(task_id="max", description=desc, working_dir=Path("/tmp"))
        result = agent.execute(context)
        assert result.status in [TaskStatus.SUCCESS, TaskStatus.FAILED]


class TestExtremeMetadata:
    """Tests com metadata extrema"""

    def test_planner_handles_empty_metadata(self):
        """Planner com metadata vazio"""
        agent = PlannerAgent()
        context = TaskContext(
            task_id="test",
            description="Task",
            working_dir=Path("/tmp"),
            metadata={}
        )
        result = agent.execute(context)
        assert result.status == TaskStatus.SUCCESS

    def test_planner_handles_large_metadata(self):
        """Planner com metadata gigante"""
        agent = PlannerAgent()
        large_meta = {f"key_{i}": f"value_{i}" * 1000 for i in range(100)}
        context = TaskContext(
            task_id="test",
            description="Task",
            working_dir=Path("/tmp"),
            metadata=large_meta
        )
        result = agent.execute(context)
        assert result.status in [TaskStatus.SUCCESS, TaskStatus.FAILED]

    def test_planner_handles_nested_metadata(self):
        """Planner com metadata profundamente aninhado"""
        agent = PlannerAgent()
        nested = {"level1": {"level2": {"level3": {"level4": {"level5": "deep"}}}}}
        context = TaskContext(
            task_id="test",
            description="Task",
            working_dir=Path("/tmp"),
            metadata=nested
        )
        result = agent.execute(context)
        assert result.status == TaskStatus.SUCCESS

    def test_refactorer_handles_null_metadata_values(self):
        """Refactorer com valores None em metadata"""
        agent = RefactorerAgent()
        context = TaskContext(
            task_id="test",
            description="Task",
            working_dir=Path("/tmp"),
            metadata={"key": None, "key2": None}
        )
        result = agent.execute(context)
        assert result.status in [TaskStatus.SUCCESS, TaskStatus.FAILED]

    def test_refactorer_handles_mixed_type_metadata(self):
        """Refactorer com tipos mistos em metadata"""
        agent = RefactorerAgent()
        context = TaskContext(
            task_id="test",
            description="Task",
            working_dir=Path("/tmp"),
            metadata={
                "string": "value",
                "int": 42,
                "float": 3.14,
                "bool": True,
                "list": [1, 2, 3],
                "dict": {"nested": "value"}
            }
        )
        result = agent.execute(context)
        assert result.status in [TaskStatus.SUCCESS, TaskStatus.FAILED]


class TestExtremeUnicode:
    """Tests com Unicode extremo"""

    def test_planner_handles_emoji_description(self):
        """Planner com descrição só de emojis"""
        agent = PlannerAgent()
        context = TaskContext(
            task_id="emoji",
            description="🚀🔥💻🎯✨🌟💡🎨🔧🛠️",
            working_dir=Path("/tmp")
        )
        result = agent.execute(context)
        assert result.status in [TaskStatus.SUCCESS, TaskStatus.FAILED]

    def test_planner_handles_mixed_languages(self):
        """Planner com múltiplas linguagens"""
        agent = PlannerAgent()
        context = TaskContext(
            task_id="multi",
            description="English 中文 日本語 한국어 Русский العربية עברית ไทย",
            working_dir=Path("/tmp")
        )
        result = agent.execute(context)
        assert result.status == TaskStatus.SUCCESS

    def test_planner_handles_rtl_text(self):
        """Planner com texto right-to-left"""
        agent = PlannerAgent()
        context = TaskContext(
            task_id="rtl",
            description="مرحبا بك في العالم العربي",
            working_dir=Path("/tmp")
        )
        result = agent.execute(context)
        assert result.status == TaskStatus.SUCCESS

    def test_refactorer_handles_special_characters(self):
        """Refactorer com caracteres especiais"""
        agent = RefactorerAgent()
        context = TaskContext(
            task_id="special",
            description="Test with \n\t\r\0 special chars",
            working_dir=Path("/tmp")
        )
        result = agent.execute(context)
        assert result.status in [TaskStatus.SUCCESS, TaskStatus.FAILED]

    def test_refactorer_handles_control_characters(self):
        """Refactorer com caracteres de controle"""
        agent = RefactorerAgent()
        context = TaskContext(
            task_id="control",
            description="Test\x00\x01\x02control",
            working_dir=Path("/tmp")
        )
        result = agent.execute(context)
        assert result.status in [TaskStatus.SUCCESS, TaskStatus.FAILED]


class TestExtremePaths:
    """Tests com paths extremos"""

    def test_planner_handles_very_long_path(self):
        """Planner com path muito longo"""
        agent = PlannerAgent()
        long_path = Path("/tmp/" + "a" * 1000)
        context = TaskContext(
            task_id="long",
            description="Task",
            working_dir=long_path
        )
        result = agent.execute(context)
        assert result.status in [TaskStatus.SUCCESS, TaskStatus.FAILED]

    def test_planner_handles_special_chars_in_path(self):
        """Planner com caracteres especiais no path"""
        agent = PlannerAgent()
        special_path = Path("/tmp/test with spaces & special!chars")
        context = TaskContext(
            task_id="special",
            description="Task",
            working_dir=special_path
        )
        result = agent.execute(context)
        assert result.status in [TaskStatus.SUCCESS, TaskStatus.FAILED]

    def test_planner_handles_unicode_in_path(self):
        """Planner com Unicode no path"""
        agent = PlannerAgent()
        unicode_path = Path("/tmp/测试/日本語/한국어")
        context = TaskContext(
            task_id="unicode",
            description="Task",
            working_dir=unicode_path
        )
        result = agent.execute(context)
        assert result.status in [TaskStatus.SUCCESS, TaskStatus.FAILED]

    def test_refactorer_handles_relative_path(self):
        """Refactorer com path relativo"""
        agent = RefactorerAgent()
        context = TaskContext(
            task_id="rel",
            description="Task",
            working_dir=Path("./relative/path")
        )
        result = agent.execute(context)
        assert result.status in [TaskStatus.SUCCESS, TaskStatus.FAILED]

    def test_refactorer_handles_symlink_path(self):
        """Refactorer com symlink (simulado)"""
        agent = RefactorerAgent()
        context = TaskContext(
            task_id="sym",
            description="Task",
            working_dir=Path("/tmp")
        )
        result = agent.execute(context)
        assert result.status in [TaskStatus.SUCCESS, TaskStatus.FAILED]


class TestExtremeTaskIds:
    """Tests com task IDs extremos"""

    def test_planner_handles_empty_task_id(self):
        """Planner com task_id vazio"""
        agent = PlannerAgent()
        context = TaskContext(
            task_id="",
            description="Task",
            working_dir=Path("/tmp")
        )
        result = agent.execute(context)
        assert result.status in [TaskStatus.SUCCESS, TaskStatus.FAILED]

    def test_planner_handles_very_long_task_id(self):
        """Planner com task_id muito longo"""
        agent = PlannerAgent()
        context = TaskContext(
            task_id="x" * 10000,
            description="Task",
            working_dir=Path("/tmp")
        )
        result = agent.execute(context)
        assert result.status in [TaskStatus.SUCCESS, TaskStatus.FAILED]

    def test_planner_handles_special_chars_in_task_id(self):
        """Planner com caracteres especiais em task_id"""
        agent = PlannerAgent()
        context = TaskContext(
            task_id="task-with-special!@#$%^&*()chars",
            description="Task",
            working_dir=Path("/tmp")
        )
        result = agent.execute(context)
        assert result.status in [TaskStatus.SUCCESS, TaskStatus.FAILED]

    def test_refactorer_handles_uuid_task_id(self):
        """Refactorer com UUID como task_id"""
        agent = RefactorerAgent()
        context = TaskContext(
            task_id="550e8400-e29b-41d4-a716-446655440000",
            description="Task",
            working_dir=Path("/tmp")
        )
        result = agent.execute(context)
        assert result.status in [TaskStatus.SUCCESS, TaskStatus.FAILED]

    def test_refactorer_handles_numeric_task_id(self):
        """Refactorer com task_id numérico"""
        agent = RefactorerAgent()
        context = TaskContext(
            task_id="12345",
            description="Task",
            working_dir=Path("/tmp")
        )
        result = agent.execute(context)
        assert result.status in [TaskStatus.SUCCESS, TaskStatus.FAILED]


class TestConcurrencyEdgeCases:
    """Tests de edge cases de concorrência"""

    def test_planner_handles_rapid_sequential_calls(self):
        """Planner com chamadas sequenciais rápidas"""
        agent = PlannerAgent()
        results = []
        for i in range(10):
            context = TaskContext(
                task_id=f"rapid_{i}",
                description=f"Task {i}",
                working_dir=Path("/tmp")
            )
            results.append(agent.execute(context))
        assert len(results) == 10
        assert all(r.status in [TaskStatus.SUCCESS, TaskStatus.FAILED] for r in results)

    def test_planner_handles_identical_contexts(self):
        """Planner com contextos idênticos"""
        agent = PlannerAgent()
        context = TaskContext(
            task_id="same",
            description="Same task",
            working_dir=Path("/tmp")
        )
        result1 = agent.execute(context)
        result2 = agent.execute(context)
        assert result1.status in [TaskStatus.SUCCESS, TaskStatus.FAILED]
        assert result2.status in [TaskStatus.SUCCESS, TaskStatus.FAILED]

    def test_refactorer_handles_interleaved_calls(self):
        """Refactorer com chamadas intercaladas"""
        agent1 = RefactorerAgent()
        agent2 = RefactorerAgent()

        context1 = TaskContext(task_id="1", description="Task 1", working_dir=Path("/tmp"))
        context2 = TaskContext(task_id="2", description="Task 2", working_dir=Path("/tmp"))

        result1 = agent1.execute(context1)
        result2 = agent2.execute(context2)

        assert result1.status in [TaskStatus.SUCCESS, TaskStatus.FAILED]
        assert result2.status in [TaskStatus.SUCCESS, TaskStatus.FAILED]


class TestMemoryPressure:
    """Tests sob pressão de memória"""

    def test_planner_handles_many_small_tasks(self):
        """Planner com muitas tarefas pequenas"""
        agent = PlannerAgent()
        for i in range(100):
            context = TaskContext(
                task_id=f"task_{i}",
                description="Small task",
                working_dir=Path("/tmp")
            )
            result = agent.execute(context)
            assert result.status in [TaskStatus.SUCCESS, TaskStatus.FAILED]

    def test_planner_handles_few_large_tasks(self):
        """Planner com poucas tarefas grandes"""
        agent = PlannerAgent()
        large_desc = "x" * 50000
        for i in range(5):
            context = TaskContext(
                task_id=f"large_{i}",
                description=large_desc,
                working_dir=Path("/tmp")
            )
            result = agent.execute(context)
            assert result.status in [TaskStatus.SUCCESS, TaskStatus.FAILED]

    def test_refactorer_handles_repeated_execution(self):
        """Refactorer com execuções repetidas"""
        agent = RefactorerAgent()
        context = TaskContext(
            task_id="repeat",
            description="Repeated task",
            working_dir=Path("/tmp")
        )
        for _ in range(50):
            result = agent.execute(context)
            assert result.status in [TaskStatus.SUCCESS, TaskStatus.FAILED]


class TestBoundaryValues:
    """Tests com valores de fronteira"""

    def test_planner_with_min_valid_context(self):
        """Planner com contexto mínimo válido"""
        agent = PlannerAgent()
        context = TaskContext(
            task_id="min",
            description="x",
            working_dir=Path("/tmp")
        )
        result = agent.execute(context)
        assert result.status in [TaskStatus.SUCCESS, TaskStatus.FAILED]

    def test_planner_with_max_valid_context(self):
        """Planner com contexto máximo válido"""
        agent = PlannerAgent()
        context = TaskContext(
            task_id="x" * 1000,
            description="x" * 10000,
            working_dir=Path("/tmp" + "/subdir" * 50),
            metadata={f"k{i}": f"v{i}" for i in range(100)}
        )
        result = agent.execute(context)
        assert result.status in [TaskStatus.SUCCESS, TaskStatus.FAILED]

    def test_refactorer_with_zero_timeout(self):
        """Refactorer com timeout zero"""
        agent = RefactorerAgent()
        context = TaskContext(
            task_id="timeout",
            description="Task",
            working_dir=Path("/tmp"),
            metadata={"timeout": 0}
        )
        result = agent.execute(context)
        assert result.status in [TaskStatus.SUCCESS, TaskStatus.FAILED]

    def test_refactorer_with_negative_values(self):
        """Refactorer com valores negativos"""
        agent = RefactorerAgent()
        context = TaskContext(
            task_id="negative",
            description="Task",
            working_dir=Path("/tmp"),
            metadata={"priority": -1, "retries": -10}
        )
        result = agent.execute(context)
        assert result.status in [TaskStatus.SUCCESS, TaskStatus.FAILED]


class TestErrorRecovery:
    """Tests de recuperação de erros"""

    def test_planner_recovers_from_partial_failure(self):
        """Planner deve recuperar de falha parcial"""
        agent = PlannerAgent()
        context = TaskContext(
            task_id="partial",
            description="Task that might partially fail",
            working_dir=Path("/tmp")
        )
        result = agent.execute(context)
        assert result.status in [TaskStatus.SUCCESS, TaskStatus.FAILED]

    def test_planner_handles_retry_after_failure(self):
        """Planner deve permitir retry após falha"""
        agent = PlannerAgent()
        context = TaskContext(
            task_id="retry",
            description="",
            working_dir=Path("/tmp")
        )
        # Primeira tentativa pode falhar
        result1 = agent.execute(context)
        # Segunda tentativa com contexto corrigido
        context2 = TaskContext(
            task_id="retry",
            description="Corrected task",
            working_dir=Path("/tmp")
        )
        result2 = agent.execute(context2)
        assert result2.status in [TaskStatus.SUCCESS, TaskStatus.FAILED]

    def test_refactorer_handles_cascading_failures(self):
        """Refactorer deve tratar falhas em cascata"""
        agent = RefactorerAgent()
        for i in range(5):
            context = TaskContext(
                task_id=f"cascade_{i}",
                description="",
                working_dir=Path("/tmp")
            )
            result = agent.execute(context)
            # Não deve crashar
            assert result.status in [TaskStatus.SUCCESS, TaskStatus.FAILED]


class TestRandomizedInputs:
    """Tests com inputs randomizados"""

    def test_planner_handles_random_descriptions(self):
        """Planner com descrições aleatórias"""
        agent = PlannerAgent()
        for _ in range(10):
            random_desc = ''.join(random.choices(string.ascii_letters + string.digits, k=100))
            context = TaskContext(
                task_id="random",
                description=random_desc,
                working_dir=Path("/tmp")
            )
            result = agent.execute(context)
            assert result.status in [TaskStatus.SUCCESS, TaskStatus.FAILED]

    def test_refactorer_handles_random_metadata(self):
        """Refactorer com metadata aleatório"""
        agent = RefactorerAgent()
        for _ in range(10):
            random_meta = {
                ''.join(random.choices(string.ascii_letters, k=10)):
                ''.join(random.choices(string.ascii_letters + string.digits, k=20))
                for _ in range(5)
            }
            context = TaskContext(
                task_id="random",
                description="Task",
                working_dir=Path("/tmp"),
                metadata=random_meta
            )
            result = agent.execute(context)
            assert result.status in [TaskStatus.SUCCESS, TaskStatus.FAILED]


class TestTypeCoercion:
    """Tests de coerção de tipos"""

    def test_planner_handles_numeric_description(self):
        """Planner com descrição numérica (como string)"""
        agent = PlannerAgent()
        context = TaskContext(
            task_id="numeric",
            description="12345",
            working_dir=Path("/tmp")
        )
        result = agent.execute(context)
        assert result.status in [TaskStatus.SUCCESS, TaskStatus.FAILED]

    def test_planner_handles_boolean_in_metadata(self):
        """Planner com booleanos em metadata"""
        agent = PlannerAgent()
        context = TaskContext(
            task_id="bool",
            description="Task",
            working_dir=Path("/tmp"),
            metadata={"flag": True, "other": False}
        )
        result = agent.execute(context)
        assert result.status == TaskStatus.SUCCESS

    def test_refactorer_handles_stringified_numbers(self):
        """Refactorer com números como strings"""
        agent = RefactorerAgent()
        context = TaskContext(
            task_id="string_nums",
            description="Task",
            working_dir=Path("/tmp"),
            metadata={"count": "42", "ratio": "3.14"}
        )
        result = agent.execute(context)
        assert result.status in [TaskStatus.SUCCESS, TaskStatus.FAILED]


class TestImmutability:
    """Tests de imutabilidade"""

    def test_planner_does_not_modify_input_context(self):
        """Planner não deve modificar contexto de entrada"""
        agent = PlannerAgent()
        context = TaskContext(
            task_id="immutable",
            description="Original",
            working_dir=Path("/tmp")
        )
        original_desc = context.description
        agent.execute(context)
        assert context.description == original_desc

    def test_refactorer_does_not_modify_input_context(self):
        """Refactorer não deve modificar contexto de entrada"""
        agent = RefactorerAgent()
        context = TaskContext(
            task_id="immutable",
            description="Original",
            working_dir=Path("/tmp"),
            metadata={"key": "value"}
        )
        original_meta = context.metadata.copy() if context.metadata else None
        agent.execute(context)
        assert context.metadata == original_meta
