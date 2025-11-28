"""Pytest configuration and fixtures for Textual async testing (2025 best practices)."""
import pytest
import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture(scope="session")
def event_loop():
    """Create session-scoped event loop for all async tests.
    
    Based on 2025 best practices for pytest-asyncio + Textual.
    Prevents 'Event loop is closed' errors.
    """
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
def mock_config():
    """Mock configuration for testing."""
    from jdev_cli.core.config import Config

    config = Config()
    config.model_name = "test-model"
    config.api_key = "test-key"
    config.max_tokens = 1000
    return config


@pytest.fixture(scope="function")
def temp_workspace(tmp_path):
    """Create temporary workspace for file operations."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    return workspace
