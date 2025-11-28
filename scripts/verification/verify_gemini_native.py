#!/usr/bin/env python3
"""
Verify Gemini Native Capabilities (Code Execution, Token Counting).
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from jdev_cli.core.providers.gemini import GeminiProvider
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def verify_native_capabilities():
    print("🚀 Verifying Gemini Native Capabilities...")

    # 1. Initialize Provider with Code Execution
    print("\n[1] Initializing Provider...")
    provider = GeminiProvider(
        enable_code_execution=True,
        enable_search=False,
        enable_caching=True
    )

    if not provider.is_available():
        print("❌ Gemini API key not found or provider unavailable.")
        return

    print(f"✅ Provider Initialized: {provider.model_name}")

    # 2. Verify Token Counting
    print("\n[2] Verifying Native Token Counting...")
    text = "Hello Gemini 3 Pro! " * 100
    naive_count = len(text) // 4
    try:
        native_count = provider.count_tokens(text)
        print(f"   Text Length: {len(text)}")
        print(f"   Naive Count: {naive_count}")
        print(f"   Native Count: {native_count}")

        if native_count != naive_count:
            print("✅ Native Token Counting is ACTIVE (Different from naive)")
        else:
            print("⚠️ Counts match exactly (Suspicious but possible)")

    except Exception as e:
        print(f"❌ Token Counting Failed: {e}")

    # 3. Verify Code Execution
    print("\n[3] Verifying Native Code Execution...")
    print("   Prompt: 'Calculate the 50th Fibonacci number using Python code.'")

    messages = [
        {"role": "user", "content": "Calculate the 50th Fibonacci number using Python code. Show me the code and the result."}
    ]

    print("   Streaming Response:")
    print("   " + "-" * 40)

    full_response = ""
    try:
        async for chunk in provider.stream_chat(messages):
            print(chunk, end="", flush=True)
            full_response += chunk

        print("\n   " + "-" * 40)

        if "12586269025" in full_response:
             print("✅ Correct Result Found (12586269025)")
        else:
             print("⚠️ Result not explicitly found (Check output)")

    except Exception as e:
        print(f"❌ Streaming Failed: {e}")

if __name__ == "__main__":
    asyncio.run(verify_native_capabilities())
