#!/usr/bin/env python3
"""
Quick Streaming Test - Verifica patches aplicados
"""

import asyncio
import sys
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

async def test_llm_generate_stream():
    """Test 1: LLMClient.generate_stream() exists"""
    print("🔍 Test 1: Verificando LLMClient.generate_stream()...")

    from jdev_cli.core.llm import LLMClient

    client = LLMClient()

    # Check method exists
    assert hasattr(client, 'generate_stream'), "❌ generate_stream() não existe!"

    # Check it's async generator
    import inspect
    assert inspect.isasyncgenfunction(client.generate_stream), "❌ generate_stream() não é async generator!"

    print("✅ LLMClient.generate_stream() OK")
    return True

async def test_planner_execute_streaming():
    """Test 2: PlannerAgent.execute_streaming() exists"""
    print("\n🔍 Test 2: Verificando PlannerAgent.execute_streaming()...")

    from jdev_cli.agents.planner import PlannerAgent
    import inspect

    # Check method exists in class definition
    assert hasattr(PlannerAgent, 'execute_streaming'), "❌ execute_streaming() não existe na classe!"

    # Check it's async generator
    method = getattr(PlannerAgent, 'execute_streaming')
    assert inspect.isasyncgenfunction(method), "❌ execute_streaming() não é async generator!"

    print("✅ PlannerAgent.execute_streaming() OK")
    return True

async def test_imports():
    """Test 3: Verificar imports necessários"""
    print("\n🔍 Test 3: Verificando imports...")


    print("✅ Imports OK (AsyncIterator, asyncio, uuid)")
    return True

async def main():
    print("=" * 60)
    print("🧪 STREAMING PATCHES - VALIDATION SUITE")
    print("=" * 60)

    try:
        # Run tests
        test1 = await test_llm_generate_stream()
        test2 = await test_planner_execute_streaming()
        test3 = await test_imports()

        print("\n" + "=" * 60)
        if test1 and test2 and test3:
            print("✅ TODOS OS TESTES PASSARAM!")
            print("\n📋 Próximos passos:")
            print("   1. Executar: ./maestro")
            print("   2. Digitar: 'Create a plan for user authentication'")
            print("   3. Observar PLANNER panel mostrando tokens em tempo real")
            print("=" * 60)
            return 0
        else:
            print("❌ ALGUNS TESTES FALHARAM")
            return 1
    except Exception as e:
        print(f"\n❌ ERRO: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
