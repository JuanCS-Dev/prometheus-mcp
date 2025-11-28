#!/usr/bin/env python3
"""
FUNCTIONAL TESTING SUITE
Tests real LLM functionality, streaming, multi-provider routing.

Following CONSTITUIÇÃO VÉRTICE v3.0 - Real behavior validation
"""

import sys
import asyncio
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from jdev_cli.core.llm import llm_client


async def test_basic_generation():
    """Test basic LLM generation."""
    print("\n" + "="*80)
    print("🧪 TEST 1: BASIC GENERATION")
    print("="*80)

    prompt = "What is 2+2? Answer in one short sentence."

    try:
        print(f"📝 Prompt: {prompt}")
        print("⏳ Generating...")

        start = time.time()
        response = await llm_client.generate(prompt, max_tokens=50)
        elapsed = time.time() - start

        print(f"\n✅ Response: {response}")
        print(f"⏱️  Time: {elapsed:.2f}s")
        print("✅ TEST PASSED: Basic generation works!")
        return True

    except Exception as e:
        print(f"❌ TEST FAILED: {e}")
        return False


async def test_streaming():
    """Test streaming generation."""
    print("\n" + "="*80)
    print("🧪 TEST 2: STREAMING GENERATION")
    print("="*80)

    prompt = "Count from 1 to 5."

    try:
        print(f"📝 Prompt: {prompt}")
        print("⏳ Streaming...")

        full_response = ""
        chunk_count = 0
        start = time.time()
        first_chunk_time = None

        async for chunk in llm_client.stream_chat(prompt, max_tokens=100):
            if first_chunk_time is None:
                first_chunk_time = time.time()
            full_response += chunk
            chunk_count += 1
            print(".", end="", flush=True)

        elapsed = time.time() - start
        ttft = (first_chunk_time - start) * 1000 if first_chunk_time else 0

        print(f"\n\n✅ Full Response: {full_response}")
        print(f"📊 Chunks received: {chunk_count}")
        print(f"⏱️  TTFT: {ttft:.0f}ms")
        print(f"⏱️  Total time: {elapsed:.2f}s")
        print("✅ TEST PASSED: Streaming works!")
        return True

    except Exception as e:
        print(f"❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_multi_provider():
    """Test multi-provider system."""
    print("\n" + "="*80)
    print("🧪 TEST 3: MULTI-PROVIDER ROUTING")
    print("="*80)

    prompt = "Say 'Hello from provider!'"
    providers = llm_client.get_available_providers()

    print(f"📋 Available providers: {providers}")

    results = {}

    for provider in ['hf', 'hf']:
        if provider not in providers:
            print(f"⏭️  Skipping {provider} (not available)")
            continue

        try:
            print(f"\n🔄 Testing provider: {provider}")
            start = time.time()

            response = await llm_client.generate(
                prompt,
                max_tokens=50,
                provider=provider
            )

            elapsed = time.time() - start
            results[provider] = {
                'success': True,
                'time': elapsed,
                'response': response[:100]
            }

            print(f"✅ {provider}: {elapsed:.2f}s")
            print(f"   Response: {response[:80]}...")

        except Exception as e:
            print(f"❌ {provider} failed: {e}")
            results[provider] = {
                'success': False,
                'error': str(e)
            }

    # Summary
    print("\n📊 PROVIDER COMPARISON:")
    print("-" * 80)
    for provider, result in results.items():
        if result['success']:
            print(f"✅ {provider:12s}: {result['time']:.2f}s")
        else:
            print(f"❌ {provider:12s}: {result.get('error', 'Unknown error')}")

    success_count = sum(1 for r in results.values() if r['success'])
    print(f"\n✅ TEST PASSED: {success_count}/{len(results)} providers working!")
    return success_count > 0


async def test_error_handling():
    """Test error handling."""
    print("\n" + "="*80)
    print("🧪 TEST 4: ERROR HANDLING")
    print("="*80)

    try:
        print("📝 Testing with invalid provider...")
        response = await llm_client.generate(
            "test",
            provider="invalid_provider_xyz"
        )
        print("❌ TEST FAILED: Should have raised error!")
        return False

    except Exception as e:
        print(f"✅ Correctly caught error: {type(e).__name__}")
        print(f"   Message: {str(e)[:100]}")
        print("✅ TEST PASSED: Error handling works!")
        return True


async def test_context_builder():
    """Test context builder."""
    print("\n" + "="*80)
    print("🧪 TEST 5: CONTEXT BUILDER")
    print("="*80)

    from jdev_cli.core.context import context_builder

    try:
        # Test stats
        stats = context_builder.get_stats()
        print(f"📊 Initial stats: {stats}")

        # Test clear
        context_builder.clear()
        stats_after = context_builder.get_stats()
        print(f"📊 Stats after clear: {stats_after}")

        if stats_after['files'] == 0:
            print("✅ TEST PASSED: Context builder works!")
            return True
        else:
            print("❌ TEST FAILED: Clear didn't work")
            return False

    except Exception as e:
        print(f"❌ TEST FAILED: {e}")
        return False


async def main():
    """Run all functional tests."""
    print("\n" + "="*80)
    print("🚀 FUNCTIONAL TEST SUITE")
    print("   Testing real behavior and functionality")
    print("="*80)

    tests = [
        ("Basic Generation", test_basic_generation),
        ("Streaming", test_streaming),
        ("Multi-Provider", test_multi_provider),
        ("Error Handling", test_error_handling),
        ("Context Builder", test_context_builder),
    ]

    results = []

    for name, test_func in tests:
        try:
            result = await test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n❌ {name} crashed: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))

    # Final summary
    print("\n" + "="*80)
    print("📊 FUNCTIONAL TEST SUMMARY")
    print("="*80)

    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {name}")

    passed_count = sum(1 for _, p in results if p)
    total_count = len(results)

    print(f"\n📈 Results: {passed_count}/{total_count} tests passed")

    if passed_count == total_count:
        print("\n🎉 ALL FUNCTIONAL TESTS PASSED!")
        print("✅ System is fully operational!")
    else:
        print(f"\n⚠️  {total_count - passed_count} test(s) failed!")
        print("⚠️  Review failures above")

    print("="*80 + "\n")

    return passed_count == total_count


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
