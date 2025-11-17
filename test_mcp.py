"""Test script for MCP manager."""

from qwen_dev_cli.core.mcp import MCPManager

def test_mcp_manager():
    """Test MCP manager functionality."""
    print("🔍 Testing MCPManager...\n")
    
    # Create instance
    mcp = MCPManager()
    print(f"✅ MCPManager created")
    print(f"   Root dir: {mcp.root_dir}")
    print(f"   Enabled: {mcp.enabled}\n")
    
    # Test 1: List Python files
    print("📂 Test 1: Listing Python files...")
    files = mcp.list_files("*.py", recursive=False)
    print(f"✅ Found {len(files)} Python files in root:")
    for f in files[:5]:  # Show first 5
        print(f"   - {f}")
    if len(files) > 5:
        print(f"   ... and {len(files) - 5} more")
    
    print()
    
    # Test 2: Get file info
    print("�� Test 2: Getting file info...")
    if files:
        info = mcp.get_file_info(files[0])
        print(f"✅ File: {info.get('name')}")
        print(f"   Size: {info.get('size_kb', 0):.2f} KB")
        print(f"   Type: {info.get('suffix')}")
    
    print()
    
    # Test 3: Inject files to context
    print("💉 Test 3: Injecting files to context...")
    test_files = ["test_llm.py", "test_context.py"]
    results = mcp.inject_files_to_context(test_files)
    
    for file_path, result in results.items():
        print(f"   {file_path}: {result}")
    
    stats = mcp.get_stats()
    print(f"\n✅ Context stats:")
    print(f"   Files: {stats['files']}")
    print(f"   Chars: {stats['total_chars']}")
    print(f"   Approx tokens: {stats['approx_tokens']}")
    
    print()
    
    # Test 4: Inject pattern
    print("🔍 Test 4: Injecting by pattern...")
    mcp.clear()  # Clear previous context
    results = mcp.inject_pattern_to_context("benchmark_*.py")
    
    for file_path, result in results.items():
        status = "✅" if "Added" in result else "❌"
        print(f"   {status} {result}")
    
    print()
    
    # Test 5: Get formatted context
    print("📄 Test 5: Getting formatted context...")
    context = mcp.get_context()
    print(f"✅ Context: {len(context)} chars")
    print(f"\nPreview (first 300 chars):")
    print("-" * 60)
    print(context[:300])
    print("...")
    print("-" * 60)
    
    print()
    
    # Test 6: Tool description
    print("🔧 Test 6: Getting tool description...")
    tool = mcp.as_tool_description()
    print(f"✅ Tool: {tool['name']}")
    print(f"   Description: {tool['description']}")
    print(f"   Parameters: {list(tool['parameters']['properties'].keys())}")
    
    print()
    
    # Test 7: Toggle enable/disable
    print("🔀 Test 7: Toggle MCP...")
    mcp.toggle(False)
    print(f"   Disabled: {not mcp.enabled}")
    
    mcp.toggle(True)
    print(f"   Enabled: {mcp.enabled}")
    
    print()
    
    # Test 8: Clear context
    print("🧹 Test 8: Clearing context...")
    mcp.clear()
    stats = mcp.get_stats()
    print(f"✅ Context cleared: {stats['files']} files")
    
    print("\n" + "="*60)
    print("🎉 All MCPManager tests complete!")


if __name__ == "__main__":
    test_mcp_manager()
