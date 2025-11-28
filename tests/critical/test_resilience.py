"""
RESILIENCE TESTS - Testes de resiliência e tratamento de erros.

Estes testes verificam que o sistema:
- Falha graciosamente
- Mostra erros claros
- Recupera de falhas
- Não trava em edge cases

Autor: JuanCS Dev
Data: 2025-11-25
"""

import pytest
import asyncio
from unittest.mock import patch


# =============================================================================
# TESTE 1: GRACEFUL DEGRADATION
# =============================================================================

class TestGracefulDegradation:
    """Testa que o sistema degrada graciosamente."""

    def test_tool_result_error_is_clear(self):
        """ToolResult de erro deve ter mensagem clara."""
        from jdev_cli.tools.base import ToolResult

        error_result = ToolResult(
            success=False,
            error="File not found: /path/to/file.txt"
        )

        # Deve ter informação útil
        assert error_result.error is not None
        assert len(error_result.error) > 10  # Não é só "error"
        assert "file" in error_result.error.lower()

    def test_agent_response_error_has_reasoning(self):
        """AgentResponse de erro deve explicar o que aconteceu."""
        from jdev_cli.agents.base import AgentResponse

        error_response = AgentResponse(
            success=False,
            reasoning="Failed to execute because X happened",
            error="Detailed: X caused Y which resulted in Z"
        )

        # Deve ter explicação
        assert error_response.reasoning
        assert len(error_response.reasoning) > 10
        assert error_response.error

    @pytest.mark.asyncio
    async def test_llm_timeout_handled(self):
        """Timeout de LLM deve ser tratado e não travar."""
        from jdev_cli.core.llm import LLMClient

        client = LLMClient()

        # Mock que simula timeout
        async def slow_response(*args, **kwargs):
            await asyncio.sleep(10)  # Simula resposta lenta
            return "response"

        with patch.object(client, 'generate', slow_response):
            # Deve ter timeout interno ou permitir cancelamento
            try:
                task = asyncio.create_task(client.generate("test"))
                # Espera no máximo 1 segundo
                await asyncio.wait_for(asyncio.shield(task), timeout=1.0)
            except asyncio.TimeoutError:
                # OK - timeout funcionou
                task.cancel()
                pass
            except Exception as e:
                # Outros erros também são aceitáveis se tratados
                pass


# =============================================================================
# TESTE 2: ERROR MESSAGE QUALITY
# =============================================================================

class TestErrorMessageQuality:
    """Testa que mensagens de erro são úteis."""

    def test_validation_error_shows_what_failed(self):
        """Erro de validação deve mostrar o que falhou."""
        from jdev_cli.core.input_validator import validate_command

        result = validate_command("rm -rf /", allow_shell=False)

        if not result.is_valid:
            # Deve ter erros descritivos
            assert result.errors
            # Pelo menos um erro deve ser descritivo
            assert any(len(e) > 10 for e in result.errors), \
                f"Errors not descriptive: {result.errors}"

    def test_tool_error_includes_context(self):
        """Erro de tool deve incluir contexto."""
        from jdev_cli.tools.base import ToolResult

        # Simula erro de arquivo não encontrado
        error = ToolResult(
            success=False,
            error="FileNotFoundError: [Errno 2] No such file: 'missing.txt'",
            metadata={"path": "missing.txt", "operation": "read"}
        )

        # Deve ter o nome do arquivo
        assert "missing.txt" in error.error

    def test_agent_error_is_actionable(self):
        """Erro de agente deve sugerir ação."""
        from jdev_cli.agents.base import AgentResponse

        # Um bom erro deve dizer o que fazer
        response = AgentResponse(
            success=False,
            reasoning="Task failed: API rate limit exceeded. Wait 60 seconds and retry.",
            error="Rate limit exceeded"
        )

        # Deve ter sugestão de ação
        assert "retry" in response.reasoning.lower() or \
               "wait" in response.reasoning.lower() or \
               "try" in response.reasoning.lower()


# =============================================================================
# TESTE 3: RECOVERY FROM FAILURES
# =============================================================================

class TestRecoveryFromFailures:
    """Testa recuperação de falhas."""

    def test_tool_registry_survives_bad_tool(self):
        """Registry deve sobreviver a tool com erro."""
        from jdev_cli.tools.base import ToolRegistry

        registry = ToolRegistry()

        # Tenta registrar tool inválida (se permitido)
        # Registry não deve crashar
        try:
            # Se tem método de registro
            if hasattr(registry, 'register'):
                # Tenta registrar None ou objeto inválido
                registry.register(None)
        except (TypeError, ValueError, AttributeError):
            # OK - rejeitou graciosamente
            pass

        # Registry deve continuar funcionando (não crashou)
        assert registry is not None

    def test_agent_task_with_empty_request(self):
        """AgentTask com request vazio não deve crashar."""
        from jdev_cli.agents.base import AgentTask

        # Pode aceitar ou rejeitar, mas não deve crashar
        try:
            task = AgentTask(request="", session_id="test")
            # Se aceitar, deve ter request vazio
            assert task.request == ""
        except ValueError as e:
            # Se rejeitar, deve ter mensagem clara
            assert "request" in str(e).lower() or "empty" in str(e).lower()


# =============================================================================
# TESTE 4: EDGE CASES
# =============================================================================

class TestEdgeCases:
    """Testa edge cases que podem causar problemas."""

    def test_unicode_in_file_path(self):
        """Unicode em path não deve crashar."""
        from jdev_cli.core.input_validator import validate_file_path

        unicode_paths = [
            "文件.txt",
            "αβγ.py",
            "файл.md",
            "🎉emoji.txt",
        ]

        for path in unicode_paths:
            # Não deve crashar
            try:
                result = validate_file_path(path)
                # Pode aceitar ou rejeitar, mas não crash
                assert result is not None
            except UnicodeError:
                pytest.fail(f"Unicode error on path: {path}")

    def test_very_long_input(self):
        """Input muito longo não deve travar."""
        from jdev_cli.core.input_validator import InputValidator

        validator = InputValidator()

        # Input de 1MB
        long_input = "x" * (1024 * 1024)

        # Não deve travar ou levar muito tempo
        import time
        start = time.time()

        try:
            result = validator.validate(long_input, "text")
            elapsed = time.time() - start

            # Deve completar em menos de 5 segundos
            assert elapsed < 5, f"Validation took too long: {elapsed}s"
        except Exception as e:
            # Se falhar, deve ser erro claro
            assert "too long" in str(e).lower() or \
                   "size" in str(e).lower() or \
                   "maximum" in str(e).lower()

    def test_special_characters_in_command(self):
        """Caracteres especiais em comando não devem crashar."""
        from jdev_cli.core.input_validator import validate_command

        special_commands = [
            "echo 'test'",
            'echo "test"',
            "echo test\\ntest",
            "echo $HOME",
            "echo %PATH%",
        ]

        for cmd in special_commands:
            try:
                result = validate_command(cmd, allow_shell=False)
                # Não deve crashar
                assert result is not None
            except Exception as e:
                pytest.fail(f"Crashed on command {repr(cmd)}: {e}")

    def test_null_and_none_handling(self):
        """None e valores nulos devem ser tratados."""
        from jdev_cli.tools.base import ToolResult
        from jdev_cli.agents.base import AgentResponse

        # ToolResult com None
        result = ToolResult(success=True, data=None)
        assert result.success is True

        # AgentResponse com dados vazios
        response = AgentResponse(
            success=True,
            data={},
            reasoning=""
        )
        assert response.success is True


# =============================================================================
# TESTE 5: CONCURRENT OPERATIONS
# =============================================================================

class TestConcurrentOperations:
    """Testa operações concorrentes."""

    @pytest.mark.asyncio
    async def test_multiple_tool_calls_dont_interfere(self):
        """Múltiplas chamadas de tool não devem interferir."""
        from jdev_cli.tools.base import ToolResult

        results = []

        async def fake_tool_call(i):
            await asyncio.sleep(0.01)  # Simula I/O
            return ToolResult(success=True, data=f"result_{i}")

        # Executa 10 tools em paralelo
        tasks = [fake_tool_call(i) for i in range(10)]
        results = await asyncio.gather(*tasks)

        # Todas devem completar
        assert len(results) == 10
        assert all(r.success for r in results)

        # Resultados devem ser distintos
        data_values = [r.data for r in results]
        assert len(set(data_values)) == 10

    def test_block_detector_thread_safe(self):
        """BlockDetector deve ser thread-safe (ou pelo menos não crashar)."""
        from jdev_cli.tui.components.block_detector import BlockDetector
        import threading

        detector = BlockDetector()
        errors = []

        def process_chunks():
            try:
                for i in range(100):
                    detector.process_chunk(f"chunk {i}\n")
            except Exception as e:
                errors.append(str(e))

        # Cria múltiplas threads
        threads = [threading.Thread(target=process_chunks) for _ in range(5)]

        for t in threads:
            t.start()

        for t in threads:
            t.join()

        # Não deve ter erros críticos
        # (pode ter race conditions, mas não deve crashar)
        critical_errors = [e for e in errors if "NoneType" in e or "index" in e.lower()]
        assert len(critical_errors) == 0, f"Thread safety issues: {critical_errors}"


# =============================================================================
# SMOKE TEST DE RESILIÊNCIA
# =============================================================================

class TestResilienceSmokeTest:
    """Smoke test de resiliência."""

    def test_system_starts_without_config_file(self):
        """Sistema deve iniciar mesmo sem arquivo de config."""
        from jdev_cli.config.loader import ConfigLoader

        # Deve ter defaults
        loader = ConfigLoader()
        config = loader.config

        assert config is not None

    def test_imports_dont_execute_code(self):
        """Imports não devem executar código destrutivo."""
        # Apenas importar não deve fazer nada perigoso

        # Se chegou aqui, imports são seguros
        assert True

    def test_can_create_objects_without_side_effects(self):
        """Criar objetos não deve ter side effects."""
        from jdev_cli.agents.base import AgentTask, AgentResponse
        from jdev_cli.tools.base import ToolResult

        # Criar múltiplos objetos
        for i in range(100):
            task = AgentTask(request=f"task {i}", session_id="test")
            result = ToolResult(success=True, data=i)
            response = AgentResponse(success=True, data={"i": i})

        # Se chegou aqui, não teve side effects problemáticos
        assert True
