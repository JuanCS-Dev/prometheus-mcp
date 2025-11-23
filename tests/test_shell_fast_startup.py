"""Test shell startup performance."""

import time
import pytest
import sys
import asyncio
from unittest.mock import patch, MagicMock

from qwen_dev_cli.shell_fast import FastShell
from qwen_dev_cli.core.shell_core import ShellCore
from qwen_dev_cli.core.lazy_loader import LazyLoader

@pytest.mark.asyncio
async def test_shell_startup_time():
    """Test that shell initializes in under 500ms."""
    start_time = time.time()
    
    shell = FastShell()
    
    # Verify core components are initialized
    assert isinstance(shell.core, ShellCore)
    assert isinstance(shell.lazy, LazyLoader)
    
    # Verify heavy components are NOT loaded
    assert shell._llm is None
    assert shell._tools is None
    
    end_time = time.time()
    duration = end_time - start_time
    
    print(f"\nStartup time: {duration*1000:.2f}ms")
    
    # Strict check: < 100ms for core init (excluding imports which are already cached by test runner)
    # In real usage, imports might take ~200ms, so < 500ms total is the goal
    assert duration < 0.1, f"Startup took too long: {duration:.4f}s"

@pytest.mark.asyncio
async def test_lazy_loader_structure():
    """Test lazy loader configuration."""
    loader = LazyLoader()
    
    # Verify critical components are mapped
    assert 'llm' in loader._LAZY_MODULES
    assert 'tools' in loader._LAZY_MODULES
    assert 'tui' in loader._LAZY_MODULES
    
    # Verify nothing is loaded initially
    assert len(loader._cache) == 0

@pytest.mark.asyncio
async def test_shell_core_no_heavy_imports():
    """Test that ShellCore doesn't trigger heavy imports."""
    with patch.dict(sys.modules):
        # Remove prompt_toolkit if present to test lazy import
        if 'prompt_toolkit' in sys.modules:
            del sys.modules['prompt_toolkit']
            
        core = ShellCore()
        
        # Should not have imported prompt_toolkit yet
        assert 'prompt_toolkit' not in sys.modules
        
        # Mock prompt_toolkit for get_input
        with patch('prompt_toolkit.PromptSession') as mock_session:
            mock_session.return_value.prompt_async = MagicMock(return_value=asyncio.Future())
            mock_session.return_value.prompt_async.return_value.set_result("test")
            
            await core.get_input()
            
            # Now it should be imported (simulated by our mock patch taking effect)
            # In real run, we'd check sys.modules again
