#!/usr/bin/env python3
"""Simple shell test - non-interactive."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from jdev_cli.tools.exec import BashCommandTool


async def test_manual_scenario():
    """Test: Usuario pede 'listar arquivos grandes'."""

    print("=" * 70)
    print("🎯 CENÁRIO: Usuário quer 'listar arquivos grandes'")
    print("=" * 70)

    bash = BashCommandTool()

    # Simula o que o LLM sugeriria
    print("\n💭 LLM sugeriria: find . -type f -size +10M")
    print("\n🤖 Executando comando...")

    result = await bash.execute(command="find . -type f -size +10M 2>/dev/null | head -5")

    print("\n📊 Resultado:")
    print(f"   Success: {result.success}")

    if result.success:
        stdout = result.data['stdout'].strip()
        if stdout:
            print("   Arquivos encontrados:")
            for line in stdout.split('\n'):
                print(f"     • {line}")
        else:
            print("   ✓ Nenhum arquivo grande encontrado (>10M)")
    else:
        print(f"   ✗ Erro: {result.error}")

    print("\n" + "=" * 70)
    print("✅ CENÁRIO COMPLETO: FUNCIONOU!")
    print("=" * 70)

    return result.success


async def test_suggest_explain_execute():
    """Test the core Copilot CLI flow."""

    print("\n" + "=" * 70)
    print("🎯 FLOW COPILOT CLI: SUGGEST → EXPLAIN → EXECUTE")
    print("=" * 70)

    bash = BashCommandTool()

    # 1. SUGGEST
    user_request = "mostrar processos usando mais memória"
    suggested_command = "ps aux --sort=-%mem | head -10"

    print(f"\n1️⃣ USER REQUEST: '{user_request}'")
    print(f"2️⃣ LLM SUGGESTS: {suggested_command}")

    # 2. EXPLAIN
    explanation = """
Este comando:
- ps aux: lista todos os processos
- --sort=-%mem: ordena por uso de memória (decrescente)
- head -10: mostra os 10 primeiros (maior uso)
"""
    print(f"3️⃣ EXPLANATION:{explanation}")

    # 3. EXECUTE
    print("4️⃣ EXECUTING...")
    result = await bash.execute(command=suggested_command)

    if result.success:
        output = result.data['stdout'].split('\n')
        print("✓ Output (primeiras 3 linhas):")
        for line in output[:3]:
            if line.strip():
                print(f"  {line}")
        print("  ...")
    else:
        print(f"✗ Failed: {result.error}")

    print("\n" + "=" * 70)
    print("✅ FLOW COMPLETO: SUGGEST → EXPLAIN → EXECUTE")
    print("=" * 70)

    return result.success


async def main():
    """Run all tests."""

    print("\n" + "🔥" * 35)
    print("TESTE: SHELL EQUIVALÊNCIA COPILOT CLI")
    print("🔥" * 35)

    # Test 1
    result1 = await test_manual_scenario()

    # Test 2
    result2 = await test_suggest_explain_execute()

    # Summary
    print("\n" + "=" * 70)
    print("📊 RESUMO")
    print("=" * 70)
    print(f"Cenário manual............... {'✅ PASS' if result1 else '❌ FAIL'}")
    print(f"Flow Copilot CLI............. {'✅ PASS' if result2 else '❌ FAIL'}")

    all_passed = result1 and result2

    print("\n" + "=" * 70)
    if all_passed:
        print("🎉 SHELL FUNCIONA! EQUIVALENTE AO COPILOT CLI BÁSICO")
        print("\nO que temos:")
        print("✅ Bash command execution")
        print("✅ Command suggestion (mock)")
        print("✅ Command explanation (mock)")
        print("✅ Execution with output")
        print("\nO que falta:")
        print("⚠️  LLM integration real (precisa API key)")
        print("⚠️  Interactive REPL loop")
        print("⚠️  Confirmation prompt")
    else:
        print("⚠️  ALGUNS COMPONENTES FALHARAM")
    print("=" * 70)

    return 0 if all_passed else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
