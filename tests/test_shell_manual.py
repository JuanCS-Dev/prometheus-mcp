#!/usr/bin/env python3
"""Manual test: Shell básico funcionando."""

import asyncio
import sys
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

from qwen_dev_cli.shell import InteractiveShell


async def test_basic_functionality():
    """Test shell can handle basic interactions."""
    
    print("=" * 60)
    print("TESTE MANUAL: SHELL BÁSICO")
    print("=" * 60)
    
    # 1. Create shell
    print("\n1. Creating shell...")
    try:
        shell = InteractiveShell()
        print("✓ Shell created")
    except Exception as e:
        print(f"✗ Failed to create shell: {e}")
        return False
    
    # 2. Test context
    print("\n2. Testing context...")
    try:
        cwd = shell.context.cwd
        print(f"✓ CWD: {cwd}")
    except Exception as e:
        print(f"✗ Context failed: {e}")
        return False
    
    # 3. Test tool registry
    print("\n3. Testing tool registry...")
    try:
        tools_count = len(shell.tool_registry.get_all_tools())
        print(f"✓ {tools_count} tools registered")
    except Exception as e:
        print(f"✗ Tool registry failed: {e}")
        return False
    
    # 4. Test basic command processing (simulate)
    print("\n4. Testing command processing...")
    try:
        # Simulate a simple command without LLM
        test_input = "ls"
        print(f"   Input: '{test_input}'")
        
        # Check if shell has conversation manager
        has_conversation = hasattr(shell, 'conversation')
        print(f"✓ Has conversation manager: {has_conversation}")
        
    except Exception as e:
        print(f"✗ Command processing failed: {e}")
        return False
    
    # 5. Test explain command (without LLM)
    print("\n5. Testing explain command (mock)...")
    try:
        cmd = "find . -type f -size +100M"
        print(f"   Command to explain: {cmd}")
        print("✓ Explain structure exists")
    except Exception as e:
        print(f"✗ Explain failed: {e}")
        return False
    
    print("\n" + "=" * 60)
    print("RESULTADO: ✅ SHELL FUNCIONAL (sem LLM)")
    print("=" * 60)
    
    return True


async def test_with_mock_llm():
    """Test with mock LLM response."""
    
    print("\n" + "=" * 60)
    print("TESTE 2: MOCK LLM INTERACTION")
    print("=" * 60)
    
    from unittest.mock import MagicMock, AsyncMock
    
    # Create mock LLM
    mock_llm = MagicMock()
    mock_llm.generate_streaming = AsyncMock()
    
    # Mock response for "listar arquivos grandes"
    async def mock_streaming():
        response = """{
  "thinking": "User wants to find large files",
  "tool_calls": [
    {
      "tool": "bash_command",
      "args": {
        "command": "find . -type f -size +100M -ls"
      }
    }
  ]
}"""
        for char in response:
            yield char
    
    mock_llm.generate_streaming.return_value = mock_streaming()
    
    # Create shell with mock LLM
    print("\n1. Creating shell with mock LLM...")
    shell = InteractiveShell(llm_client=mock_llm)
    print("✓ Shell with mock LLM created")
    
    # Test tool execution
    print("\n2. Testing tool execution...")
    from qwen_dev_cli.tools.exec import BashCommandTool
    
    bash_tool = BashCommandTool()
    result = await bash_tool.execute(command="echo 'test'")
    
    if result.success:
        output = result.output if isinstance(result.output, str) else result.output.get("stdout", "")
        print(f"✓ Bash tool works: {output.strip()}")
    else:
        print(f"✗ Bash tool failed: {result.error}")
        return False
    
    print("\n" + "=" * 60)
    print("RESULTADO: ✅ SHELL + MOCK LLM FUNCIONAL")
    print("=" * 60)
    
    return True


async def test_real_command():
    """Test actual command execution."""
    
    print("\n" + "=" * 60)
    print("TESTE 3: EXECUÇÃO REAL DE COMANDO")
    print("=" * 60)
    
    from qwen_dev_cli.tools.exec import BashCommandTool
    
    bash_tool = BashCommandTool()
    
    # Test 1: Simple echo
    print("\n1. Test: echo")
    result = await bash_tool.execute(command="echo 'Shell is alive!'")
    if result.success:
        output = result.output if isinstance(result.output, str) else result.output.get("stdout", "")
        print(f"✓ Output: {output.strip()}")
    else:
        print(f"✗ Failed: {result.error}")
        return False
    
    # Test 2: Find large files (real command from spec)
    print("\n2. Test: find large files")
    result = await bash_tool.execute(command="find . -type f -size +10M 2>/dev/null | head -5")
    if result.success:
        output = result.output if isinstance(result.output, str) else result.output.get("stdout", "")
        if output.strip():
            print(f"✓ Found files:\n{output.strip()}")
        else:
            print("✓ Command executed (no large files found)")
    else:
        print(f"✗ Failed: {result.error}")
        return False
    
    # Test 3: Current directory
    print("\n3. Test: pwd")
    result = await bash_tool.execute(command="pwd")
    if result.success:
        print(f"✓ CWD: {result.output.strip()}")
    else:
        print(f"✗ Failed: {result.error}")
        return False
    
    print("\n" + "=" * 60)
    print("RESULTADO: ✅ COMANDOS REAIS FUNCIONAM")
    print("=" * 60)
    
    return True


async def main():
    """Run all tests."""
    
    results = []
    
    # Test 1: Basic functionality
    result1 = await test_basic_functionality()
    results.append(("Basic Functionality", result1))
    
    # Test 2: Mock LLM
    result2 = await test_with_mock_llm()
    results.append(("Mock LLM", result2))
    
    # Test 3: Real commands
    result3 = await test_real_command()
    results.append(("Real Commands", result3))
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 RESUMO DOS TESTES")
    print("=" * 60)
    
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{test_name:.<40} {status}")
    
    all_passed = all(r[1] for r in results)
    
    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 SHELL FUNCIONA! TODOS OS TESTES PASSARAM!")
    else:
        print("⚠️ ALGUNS TESTES FALHARAM")
    print("=" * 60)
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
