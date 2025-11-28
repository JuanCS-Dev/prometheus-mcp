#!/usr/bin/env python3
"""Test Interactive REPL - Non-interactive mode for CI."""

import asyncio
import sys
from unittest.mock import AsyncMock, MagicMock

sys.path.insert(0, '.')

from jdev_cli.shell import InteractiveShell


async def test_repl_flow():
    """Test complete REPL flow with mocked inputs."""

    print("=" * 70)
    print("🧪 TEST: Interactive REPL Flow")
    print("=" * 70)

    # Create shell with mocked LLM
    mock_llm = MagicMock()
    mock_llm.generate = AsyncMock(return_value="find . -type f -size +100M")

    shell = InteractiveShell(llm_client=mock_llm)

    # Test 1: Command suggestion
    print("\n1. Testing command suggestion...")
    rich_ctx = {'working_dir': '.', 'os': 'Linux'}
    suggestion = await shell._get_command_suggestion("list large files", rich_ctx)
    print(f"   Suggestion: {suggestion}")
    assert "find" in suggestion, "Should suggest find command"
    print("   ✅ PASS")

    # Test 2: Safety levels
    print("\n2. Testing safety levels...")
    assert shell._get_safety_level("ls -la") == 0, "ls should be safe"
    assert shell._get_safety_level("cp file1 file2") == 1, "cp should need confirm"
    assert shell._get_safety_level("rm -rf /") == 2, "rm -rf should be dangerous"
    print("   ✅ PASS")

    # Test 3: Command extraction
    print("\n3. Testing command extraction...")
    extracted = shell._extract_command("```bash\nls -la\n```")
    assert extracted == "ls -la", "Should extract from code block"
    print(f"   Extracted: {extracted}")
    print("   ✅ PASS")

    # Test 4: Fallback suggestions (no LLM)
    print("\n4. Testing fallback suggestions...")
    shell_no_llm = InteractiveShell(llm_client=None)
    fallback = shell_no_llm._fallback_suggest("list large files")
    print(f"   Fallback: {fallback}")
    assert "find" in fallback, "Fallback should work"
    print("   ✅ PASS")

    # Test 5: Execute command
    print("\n5. Testing command execution...")
    result = await shell._execute_command("echo 'test'")
    print(f"   Result: {result}")
    assert result['success'], "Should execute successfully"
    assert "test" in result['output'], "Should contain output"
    print("   ✅ PASS")

    # Test 6: Error handling
    print("\n6. Testing error handling...")
    error = FileNotFoundError("test.txt not found")
    await shell._handle_error(error, "cat test.txt")
    print("   ✅ PASS (error handled gracefully)")

    print("\n" + "=" * 70)
    print("✅ ALL TESTS PASSED")
    print("=" * 70)
    print()
    print("REPL Features validated:")
    print("  ✓ LLM integration")
    print("  ✓ Command suggestion")
    print("  ✓ Safety levels (0/1/2)")
    print("  ✓ Command extraction")
    print("  ✓ Fallback mode")
    print("  ✓ Command execution")
    print("  ✓ Error handling")
    print()
    print("Ready for interactive testing!")
    print("Run: qwen  (or python -m jdev_cli)")
    print("=" * 70)


async def test_manual_flow_simulation():
    """Simulate manual user flow."""

    print("\n" + "=" * 70)
    print("🎯 SIMULATED USER FLOW")
    print("=" * 70)

    mock_llm = MagicMock()
    mock_llm.generate = AsyncMock(return_value="find . -type f -size +100M")

    shell = InteractiveShell(llm_client=mock_llm)

    # Simulate: User asks for large files
    print("\nUser: list large files")
    print()

    print("[THINKING] Step 1/3: Analyzing request...")
    suggestion = await shell._get_command_suggestion("list large files", {'working_dir': '.'})
    print("[THINKING] Step 2/3: Command ready (0.1s) ✓")
    print()

    print("You: list large files")
    print()
    print("💡 Suggested action:")
    print(f"   {suggestion}")
    print()

    safety = shell._get_safety_level(suggestion)
    if safety == 0:
        print("✓ Safe command")
        print("Execute? [Y/n] y")

    print()
    print("[EXECUTING] Running command...")
    print()

    result = await shell._execute_command(suggestion)
    if result['success']:
        print("✓ Success")
        # Show some output
        output_lines = result['output'].strip().split('\n')[:3]
        for line in output_lines:
            if line.strip():
                print(line)
        if len(result['output'].split('\n')) > 3:
            print("...")

    print()
    print("=" * 70)
    print("✅ FLOW SIMULATION COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(test_repl_flow())
    asyncio.run(test_manual_flow_simulation())
