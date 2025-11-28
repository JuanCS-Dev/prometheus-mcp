"""Test script for LLM client."""

import asyncio
from dotenv import load_dotenv
from jdev_cli.core.llm import llm_client
from jdev_cli.core.config import config

# Load environment variables
load_dotenv()


async def test_streaming():
    """Test streaming chat."""
    print("🔍 Testing LLM Client Streaming...\n")

    # Validate client
    is_valid, message = llm_client.validate()
    print(f"Client Status: {message}")

    if not is_valid:
        print("❌ Client validation failed!")
        return

    print(f"\nModel: {config.hf_model}")
    print(f"Max Tokens: {config.max_tokens}")
    print(f"Temperature: {config.temperature}")
    print("\n" + "="*60)

    # Test prompt
    prompt = "Write a simple hello world function in Python with docstring"

    print(f"\n📤 Prompt: {prompt}\n")
    print("📥 Response (streaming):\n")

    # Stream response
    full_response = []
    async for chunk in llm_client.stream_chat(prompt):
        print(chunk, end="", flush=True)
        full_response.append(chunk)

    print("\n\n" + "="*60)
    print("✅ Streaming complete!")
    print(f"Total length: {len(''.join(full_response))} chars")


async def test_with_context():
    """Test with context injection."""
    print("\n\n🔍 Testing with Context...\n")

    context = """
# Sample Python module
def existing_function():
    return "Hello from existing code"
"""

    prompt = "Add a new function that calls existing_function()"

    print(f"📄 Context provided:\n{context}")
    print(f"\n📤 Prompt: {prompt}\n")
    print("📥 Response:\n")

    response = await llm_client.generate(prompt, context=context)
    print(response)
    print("\n✅ Context test complete!")


async def main():
    """Run all tests."""
    try:
        await test_streaming()
        await test_with_context()
        print("\n\n🎉 All tests passed!")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
