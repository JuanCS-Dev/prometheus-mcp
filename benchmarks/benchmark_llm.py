"""Benchmark script for LLM performance metrics."""

import asyncio
import time
from jdev_cli.core.llm import llm_client


async def benchmark_performance():
    """Benchmark TTFT and throughput."""
    print("⚡ LLM Performance Benchmark\n")
    print("="*60)

    prompt = "Write a Python function to calculate fibonacci numbers"

    print(f"\n📤 Prompt: {prompt}\n")
    print("⏱️  Measuring performance...\n")

    start_time = time.time()
    first_token_time = None
    chunks_received = 0
    total_chars = 0

    async for chunk in llm_client.stream_chat(prompt):
        chunks_received += 1
        total_chars += len(chunk)

        # Measure TTFT (Time to First Token)
        if first_token_time is None:
            first_token_time = time.time()
            ttft = (first_token_time - start_time) * 1000
            print(f"⚡ TTFT: {ttft:.0f}ms")
            print("\n📥 Response:\n")

        print(chunk, end="", flush=True)

    end_time = time.time()
    total_time = end_time - start_time
    generation_time = end_time - first_token_time if first_token_time else total_time

    # Calculate metrics
    tokens_approx = total_chars // 4  # Rough estimate
    throughput = tokens_approx / generation_time if generation_time > 0 else 0

    print("\n\n" + "="*60)
    print("\n📊 Performance Metrics:\n")
    print(f"⚡ TTFT (Time to First Token): {ttft:.0f}ms")
    print(f"⏱️  Total Time: {total_time:.2f}s")
    print(f"📝 Total Characters: {total_chars}")
    print(f"🎯 Chunks Received: {chunks_received}")
    print(f"📊 Approx Tokens: {tokens_approx}")
    print(f"🚀 Throughput: {throughput:.1f} tokens/sec")

    # Validate targets
    print("\n🎯 Target Validation:\n")
    print(f"TTFT Target: <2000ms → {'✅ PASS' if ttft < 2000 else '❌ FAIL'} ({ttft:.0f}ms)")
    print(f"Throughput Target: >10 t/s → {'✅ PASS' if throughput > 10 else '❌ FAIL'} ({throughput:.1f} t/s)")


async def main():
    """Run benchmark."""
    try:
        await benchmark_performance()
        print("\n\n🎉 Benchmark complete!")
    except Exception as e:
        print(f"\n❌ Benchmark failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
