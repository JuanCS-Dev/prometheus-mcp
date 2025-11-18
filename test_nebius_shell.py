#!/usr/bin/env python3
import asyncio
import sys
sys.path.insert(0, '/home/maximus/qwen-dev-cli')

from qwen_dev_cli.core.llm import llm_client

async def test_nebius():
    print("🧪 Testing Nebius...")
    try:
        response = await llm_client.generate(
            prompt="What is 2+2? Just the number.",
            provider="nebius"
        )
        print(f"✅ Response: {response[:100]}")
        return True
    except Exception as e:
        print(f"❌ Failed: {e}")
        return False

asyncio.run(test_nebius())
