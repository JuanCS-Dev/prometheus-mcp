"""Test script for ContextBuilder."""

from jdev_cli.core.context import ContextBuilder

def test_context_builder():
    """Test context builder functionality."""
    print("🔍 Testing ContextBuilder...\n")

    # Create instance
    builder = ContextBuilder(max_files=3, max_file_size_kb=100)
    print("✅ ContextBuilder created")
    print(f"   Max files: {builder.max_files}")
    print(f"   Max size: {builder.max_file_size_kb}KB\n")

    # Test 1: Read existing file
    print("📖 Test 1: Reading test_llm.py...")
    success, content, error = builder.read_file("test_llm.py")

    if success:
        print("✅ File read successfully!")
        print(f"   Length: {len(content)} chars")
        print(f"   Lines: {content.count(chr(10)) + 1}")
    else:
        print(f"❌ Failed: {error}")

    print()

    # Test 2: Add file to context
    print("📥 Test 2: Adding file to context...")
    success, message = builder.add_file("test_llm.py")
    print(f"   {message}")

    if success:
        stats = builder.get_stats()
        print("✅ Context stats:")
        print(f"   Files: {stats['files']}/{stats['max_files']}")
        print(f"   Total chars: {stats['total_chars']}")
        print(f"   Total lines: {stats['total_lines']}")
        print(f"   Approx tokens: {stats['approx_tokens']}")

    print()

    # Test 3: Add multiple files
    print("📥 Test 3: Adding multiple files...")
    results = builder.add_files(["benchmark_llm.py", "README.md"])

    for file_path, result in results.items():
        print(f"   {file_path}: {result}")

    stats = builder.get_stats()
    print("\n✅ Final context stats:")
    print(f"   Files: {stats['files']}/{stats['max_files']}")
    print(f"   Total chars: {stats['total_chars']}")
    print(f"   Approx tokens: {stats['approx_tokens']}")

    print()

    # Test 4: Get formatted context
    print("📄 Test 4: Getting formatted context...")
    context = builder.get_context()
    print(f"✅ Context generated ({len(context)} chars)")
    print("\nPreview (first 500 chars):")
    print("-" * 60)
    print(context[:500])
    print("...")
    print("-" * 60)

    print()

    # Test 5: Inject to prompt
    print("💉 Test 5: Injecting context to prompt...")
    prompt = "Explain how these test files work together"
    full_prompt = builder.inject_to_prompt(prompt)

    print(f"✅ Prompt with context ({len(full_prompt)} chars)")
    print(f"\nOriginal prompt: '{prompt}'")
    print(f"Context added: {len(full_prompt) - len(prompt)} chars")

    print()

    # Test 6: Error handling
    print("🚫 Test 6: Testing error handling...")

    # Non-existent file
    success, content, error = builder.read_file("nonexistent.py")
    print(f"   Non-existent file: {'✅ Error caught' if not success else '❌ Should fail'}")
    print(f"   Error: {error}")

    # Try to exceed max files
    builder.add_file("pyproject.toml")  # This should fail (already have 3)
    stats = builder.get_stats()
    print(f"   Max files enforced: {'✅ Correct' if stats['files'] == 3 else '❌ Failed'}")

    print()

    # Test 7: Clear context
    print("🧹 Test 7: Clearing context...")
    builder.clear()
    stats = builder.get_stats()
    print(f"✅ Context cleared: {stats['files']} files")

    print("\n" + "="*60)
    print("🎉 All ContextBuilder tests complete!")


if __name__ == "__main__":
    test_context_builder()
