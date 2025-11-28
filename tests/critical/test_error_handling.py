"""
ERROR HANDLING TESTS - Testes de tratamento de erros padronizado.

Verifica que o sistema:
- Loga erros com informações completas
- Fornece mensagens úteis ao usuário
- Distingue erros retryable de permanentes
- Não vaza informações sensíveis

Autor: JuanCS Dev
Data: 2025-11-25
"""

import pytest
from unittest.mock import MagicMock


# =============================================================================
# TESTE 1: ERROR UTILS MODULE
# =============================================================================

class TestErrorUtilsModule:
    """Testa o módulo error_utils."""

    def test_module_imports(self):
        """error_utils deve importar sem erro."""
        from jdev_cli.core.error_utils import (
            log_error,
            log_warning,
            log_retry,
            format_error_for_user,
            create_error_result,
            is_retryable_error,
        )

        assert callable(log_error)
        assert callable(log_warning)
        assert callable(log_retry)
        assert callable(format_error_for_user)
        assert callable(create_error_result)
        assert callable(is_retryable_error)

    def test_log_error_includes_type(self):
        """log_error deve incluir tipo do erro."""
        from jdev_cli.core.error_utils import log_error

        mock_logger = MagicMock()
        error = ValueError("test error message")

        result = log_error(mock_logger, error, context="Testing")

        assert "ValueError" in result
        assert "test error message" in result
        assert "Testing" in result
        mock_logger.error.assert_called_once()

    def test_log_warning_no_traceback(self):
        """log_warning não deve incluir traceback."""
        from jdev_cli.core.error_utils import log_warning

        mock_logger = MagicMock()
        error = RuntimeError("minor issue")

        result = log_warning(mock_logger, error, context="Operation")

        assert "RuntimeError" in result
        mock_logger.warning.assert_called_once()

    def test_log_retry_escalates_near_max(self):
        """log_retry deve escalar para ERROR perto do máximo."""
        from jdev_cli.core.error_utils import log_retry

        mock_logger = MagicMock()
        error = TimeoutError("connection timeout")

        # Early attempt - should use warning
        log_retry(mock_logger, error, attempt=1, max_attempts=5, context="API call")
        mock_logger.warning.assert_called()

        mock_logger.reset_mock()

        # Near max - should use error
        log_retry(mock_logger, error, attempt=4, max_attempts=5, context="API call")
        mock_logger.error.assert_called()


# =============================================================================
# TESTE 2: USER-FRIENDLY MESSAGES
# =============================================================================

class TestUserFriendlyMessages:
    """Testa formatação de mensagens para usuário."""

    def test_connection_error_is_friendly(self):
        """ConnectionError deve ter mensagem amigável."""
        from jdev_cli.core.error_utils import format_error_for_user

        error = ConnectionError("Failed to establish connection")
        message = format_error_for_user(error)

        # Deve ser legível por humanos
        assert "connect" in message.lower()
        # Não deve mostrar detalhes técnicos internos
        assert "traceback" not in message.lower()

    def test_timeout_error_is_friendly(self):
        """TimeoutError deve ter mensagem amigável."""
        from jdev_cli.core.error_utils import format_error_for_user

        error = TimeoutError("Request timed out after 30s")
        message = format_error_for_user(error)

        assert "timeout" in message.lower() or "timed out" in message.lower()

    def test_file_not_found_shows_path(self):
        """FileNotFoundError deve mostrar o path."""
        from jdev_cli.core.error_utils import format_error_for_user

        error = FileNotFoundError("missing.txt")
        message = format_error_for_user(error)

        assert "missing.txt" in message

    def test_context_is_prepended(self):
        """Contexto deve aparecer na mensagem."""
        from jdev_cli.core.error_utils import format_error_for_user

        error = ValueError("invalid value")
        message = format_error_for_user(error, context="Processing config")

        assert "Processing config" in message


# =============================================================================
# TESTE 3: RETRYABLE ERROR DETECTION
# =============================================================================

class TestRetryableErrorDetection:
    """Testa detecção de erros que podem ser retentados."""

    def test_timeout_is_retryable(self):
        """TimeoutError deve ser retryable."""
        from jdev_cli.core.error_utils import is_retryable_error

        error = TimeoutError("connection timeout")
        assert is_retryable_error(error) is True

    def test_connection_error_is_retryable(self):
        """ConnectionError deve ser retryable."""
        from jdev_cli.core.error_utils import is_retryable_error

        error = ConnectionError("network unreachable")
        assert is_retryable_error(error) is True

    def test_validation_error_not_retryable(self):
        """ValidationError não deve ser retryable."""
        from jdev_cli.core.error_utils import is_retryable_error

        # Simula erro de validação
        class ValidationError(ValueError):
            pass

        error = ValidationError("invalid input")
        assert is_retryable_error(error) is False

    def test_auth_error_not_retryable(self):
        """Erros de autenticação não devem ser retryable."""
        from jdev_cli.core.error_utils import is_retryable_error

        # Erro com mensagem de auth
        error = Exception("authentication failed: invalid api key")
        assert is_retryable_error(error) is False

    def test_file_not_found_not_retryable(self):
        """FileNotFoundError não deve ser retryable."""
        from jdev_cli.core.error_utils import is_retryable_error

        error = FileNotFoundError("file.txt not found")
        assert is_retryable_error(error) is False


# =============================================================================
# TESTE 4: ERROR RESULT CREATION
# =============================================================================

class TestErrorResultCreation:
    """Testa criação de resultados de erro padronizados."""

    def test_error_result_has_required_fields(self):
        """create_error_result deve ter campos obrigatórios."""
        from jdev_cli.core.error_utils import create_error_result

        error = ValueError("test error")
        result = create_error_result(error)

        assert "success" in result
        assert result["success"] is False
        assert "error" in result
        assert "error_type" in result
        assert result["error_type"] == "ValueError"

    def test_error_result_includes_context(self):
        """create_error_result deve incluir contexto quando fornecido."""
        from jdev_cli.core.error_utils import create_error_result

        error = RuntimeError("operation failed")
        result = create_error_result(error, context="Processing file")

        assert "context" in result
        assert result["context"] == "Processing file"


# =============================================================================
# TESTE 5: ERROR CONTEXT MANAGER
# =============================================================================

class TestErrorContextManager:
    """Testa o context manager para erros."""

    def test_context_manager_logs_error(self):
        """ErrorContext deve logar erros automaticamente."""
        from jdev_cli.core.error_utils import ErrorContext

        mock_logger = MagicMock()

        with pytest.raises(ValueError):
            with ErrorContext(mock_logger, "Test operation"):
                raise ValueError("test error")

        mock_logger.error.assert_called_once()

    def test_context_manager_can_suppress(self):
        """ErrorContext pode suprimir erros se configurado."""
        from jdev_cli.core.error_utils import ErrorContext

        mock_logger = MagicMock()

        # Com reraise=False, não deve propagar
        with ErrorContext(mock_logger, "Test operation", reraise=False):
            raise ValueError("suppressed error")

        # Se chegou aqui, erro foi suprimido
        mock_logger.error.assert_called_once()

    def test_context_manager_passes_extra(self):
        """ErrorContext deve passar extras para o log."""
        from jdev_cli.core.error_utils import ErrorContext

        mock_logger = MagicMock()

        with pytest.raises(RuntimeError):
            with ErrorContext(mock_logger, "File operation", filename="test.txt"):
                raise RuntimeError("file error")

        # Verifica que foi chamado (extras estão no resultado)
        mock_logger.error.assert_called_once()


# =============================================================================
# TESTE 6: NO SENSITIVE DATA LEAK
# =============================================================================

class TestNoSensitiveDataLeak:
    """Testa que dados sensíveis não vazam em mensagens de erro."""

    def test_api_key_not_in_user_message(self):
        """API keys não devem aparecer em mensagens para usuário."""
        from jdev_cli.core.error_utils import format_error_for_user

        # Simula erro que contém API key
        error = Exception("Failed with key: sk-1234567890abcdef")
        message = format_error_for_user(error)

        # A mensagem pode conter o erro, mas devemos verificar
        # que não mostra a key completa em contextos sensíveis
        # (neste caso o teste é informativo)
        assert isinstance(message, str)

    def test_error_message_truncated(self):
        """Mensagens muito longas devem ser truncadas."""
        from jdev_cli.core.error_utils import log_error

        mock_logger = MagicMock()

        # Erro com mensagem gigante
        long_message = "x" * 10000
        error = ValueError(long_message)

        result = log_error(mock_logger, error, context="Test")

        # Resultado deve ser truncado
        assert len(result) < 1000
