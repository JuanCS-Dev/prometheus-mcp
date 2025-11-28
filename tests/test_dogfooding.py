#!/usr/bin/env python3
"""
Dogfooding test script - Test real-world usage scenarios.
Boris Cherny - Week 4 Day 4
"""
import sys
import asyncio
from pathlib import Path
import tempfile

async def test_lsp_features():
    """Test LSP features."""
    print("🧪 Testing LSP features...")

    # Test file
    test_file = Path("jdev_cli/intelligence/lsp_client.py")

    if not test_file.exists():
        print(f"❌ Test file not found: {test_file}")
        return False

    print(f"✅ Test file exists: {test_file}")
    print(f"   Lines: {len(test_file.read_text().splitlines())}")

    # Test language detection
    from jdev_cli.intelligence.lsp_client import Language
    lang = Language.detect(test_file)
    print(f"✅ Language detected: {lang.value}")

    # Test LSP client initialization
    from jdev_cli.intelligence.lsp_client import LSPClient
    client = LSPClient(root_path=Path.cwd())
    print(f"✅ LSP client created for language: {client.language.value}")

    return True

async def test_refactoring():
    """Test refactoring engine."""
    print("\n🧪 Testing refactoring engine...")

    from jdev_cli.refactoring.engine import RefactoringEngine
    engine = RefactoringEngine(project_root=Path.cwd())

    # Create temp file for testing
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        test_code = '''def old_name():
    return "test"

result = old_name()
'''
        f.write(test_code)
        temp_path = Path(f.name)

    try:
        # Test rename
        result = engine.rename_symbol(temp_path, "old_name", "new_name")

        if result.success:
            new_content = temp_path.read_text()
            if "new_name" in new_content and "old_name" not in new_content:
                print(f"✅ Rename symbol works: {result.message}")
                return True
            else:
                print("❌ Rename didn't work correctly")
                return False
        else:
            print(f"❌ Rename failed: {result.error}")
            return False
    finally:
        temp_path.unlink()

async def test_context_suggestions():
    """Test context suggestions."""
    print("\n🧪 Testing context suggestions...")

    from jdev_cli.intelligence.context_suggestions import ContextSuggestionEngine
    from jdev_cli.intelligence.indexer import SemanticIndexer

    indexer = SemanticIndexer(root_path=Path.cwd())
    engine = ContextSuggestionEngine(project_root=Path.cwd(), indexer=indexer)

    # Use absolute path
    test_file = (Path.cwd() / "jdev_cli" / "shell.py").resolve()
    if test_file.exists():
        suggestions = engine.suggest_related_files(test_file, max_suggestions=3)
        print(f"✅ Got {len(suggestions)} related file suggestions")
        for rec in suggestions[:3]:
            print(f"   - {rec.file_path.name}: {rec.relevance_score:.2f}")
        return len(suggestions) > 0
    else:
        print(f"❌ Test file not found: {test_file}")
        return False

async def test_indexer():
    """Test semantic indexer."""
    print("\n🧪 Testing semantic indexer...")

    from jdev_cli.intelligence.indexer import SemanticIndexer

    indexer = SemanticIndexer(root_path=Path.cwd())

    # Test search
    results = indexer.search_symbols("LSPClient", limit=3)
    print(f"✅ Search returned {len(results)} results")

    for result in results[:3]:
        print(f"   - {result.name} ({result.type})")

    return len(results) > 0

async def test_consolidated_context():
    """Test consolidated context manager."""
    print("\n🧪 Testing consolidated context manager...")

    from jdev_cli.core.context_manager_consolidated import ConsolidatedContextManager

    manager = ConsolidatedContextManager(max_tokens=100_000)

    # Add some context
    manager.add_item("test_file.py", "print('hello')", relevance=0.9)
    manager.add_item("another.py", "import sys", relevance=0.7)

    context = manager.get_context()

    if len(context) == 2:
        print(f"✅ Context manager works: {len(context)} items")

        # Test token tracking
        usage = manager.get_token_usage()
        print(f"✅ Token tracking: {usage['current_tokens']} tokens used")
        return True
    else:
        print(f"❌ Expected 2 items, got {len(context)}")
        return False

async def main():
    """Run all dogfooding tests."""
    print("=" * 60)
    print("🐕 DOGFOODING TEST SUITE - Week 4 Day 4")
    print("=" * 60)

    results = []

    # Test LSP
    results.append(("LSP Features", await test_lsp_features()))

    # Test Refactoring
    results.append(("Refactoring", await test_refactoring()))

    # Test Context Suggestions
    results.append(("Context Suggestions", await test_context_suggestions()))

    # Test Indexer
    results.append(("Semantic Indexer", await test_indexer()))

    # Test Context Manager
    results.append(("Context Manager", await test_consolidated_context()))

    # Summary
    print("\n" + "=" * 60)
    print("📊 RESULTS")
    print("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {name}")

    pct = passed/total*100
    print(f"\nTotal: {passed}/{total} ({pct:.0f}%)")

    if passed == total:
        print("\n🎉 ALL CORE FEATURES WORKING!")
    else:
        print(f"\n⚠️ {total-passed} features need attention")

    return passed == total

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
