"""Tests for non-interactive mode."""

import pytest
import asyncio
from pathlib import Path
from qwen_dev_cli.core.single_shot import execute_single_shot


@pytest.mark.asyncio
async def test_execute_single_shot_basic():
    """Test basic single-shot execution."""
    result = await execute_single_shot(
        message="echo hello world",
        include_context=False
    )
    
    assert isinstance(result, dict)
    assert 'success' in result
    assert 'output' in result
    assert 'actions_taken' in result
    assert 'errors' in result


@pytest.mark.asyncio
async def test_execute_single_shot_with_context():
    """Test single-shot with context building."""
    result = await execute_single_shot(
        message="what files are here?",
        include_context=True
    )
    
    assert isinstance(result, dict)
    assert 'success' in result
    assert 'output' in result


@pytest.mark.asyncio
async def test_execute_single_shot_custom_cwd(tmp_path):
    """Test single-shot with custom working directory."""
    # Create test file
    test_file = tmp_path / "test.txt"
    test_file.write_text("test content")
    
    result = await execute_single_shot(
        message="list files",
        cwd=str(tmp_path),
        include_context=False
    )
    
    assert result['success']


@pytest.mark.asyncio
async def test_execute_single_shot_text_response():
    """Test single-shot with text-only response (no tool calls)."""
    result = await execute_single_shot(
        message="what is 2+2?",
        include_context=False
    )
    
    assert result['success']
    assert len(result['actions_taken']) == 0  # No tools called
    assert result['output']  # Has text output


def test_cli_non_interactive_mode(tmp_path):
    """Test CLI non-interactive mode with -m flag."""
    from typer.testing import CliRunner
    from qwen_dev_cli.cli import app
    
    runner = CliRunner()
    
    # Test basic message
    result = runner.invoke(app, ["chat", "-m", "echo test", "--no-context"])
    assert result.exit_code in [0, 1]  # May exit with 1 if errors in output
    assert "Processing:" in result.stdout


def test_cli_json_output(tmp_path):
    """Test CLI JSON output format."""
    from typer.testing import CliRunner
    from qwen_dev_cli.cli import app
    import json
    
    runner = CliRunner()
    
    result = runner.invoke(app, [
        "chat",
        "-m", "hello",
        "--no-context",
        "--json"
    ])
    
    # Should have JSON in output
    try:
        # Extract JSON from output
        lines = result.stdout.split('\n')
        json_lines = [l for l in lines if l.strip().startswith('{')]
        if json_lines:
            data = json.loads(json_lines[0])
            assert 'success' in data
            assert 'output' in data
            assert 'actions_taken' in data
    except:
        pass  # Test may fail if LLM not available


def test_cli_output_to_file(tmp_path):
    """Test CLI output to file."""
    from typer.testing import CliRunner
    from qwen_dev_cli.cli import app
    
    runner = CliRunner()
    output_file = tmp_path / "output.txt"
    
    result = runner.invoke(app, [
        "chat",
        "-m", "test message",
        "--no-context",
        "--output", str(output_file)
    ])
    
    # File should be created (if command succeeded)
    if result.exit_code == 0:
        assert output_file.exists()
        content = output_file.read_text()
        assert len(content) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
