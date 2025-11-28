#!/usr/bin/env python3
"""
Dogfooding test - Final working version.
Boris Cherny - Week 4 Day 4
"""
import sys, asyncio, tempfile
from pathlib import Path

async def test_lsp_features():
    print("🧪 LSP Features...")
    from jdev_cli.intelligence.lsp_client import Language, LSPClient

    test_file = Path("jdev_cli/intelligence/lsp_client.py")
    assert test_file.exists(), "Test file not found"

    lang = Language.detect(test_file)
    assert lang == Language.PYTHON
    print(f"✅ Language detection: {lang.value}")

    client = LSPClient(root_path=Path.cwd())
    assert client.language == Language.PYTHON
    print(f"✅ LSP client initialized: {client.language.value}")
    return True

async def test_refactoring():
    print("\n🧪 Refactoring Engine...")
    from jdev_cli.refactoring.engine import RefactoringEngine

    engine = RefactoringEngine(project_root=Path.cwd())

    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write('def old_name():\n    return "test"\n\nresult = old_name()\n')
        temp_path = Path(f.name)

    try:
        result = engine.rename_symbol(temp_path, "old_name", "new_name")
        assert result.success, f"Rename failed: {result.error}"

        new_content = temp_path.read_text()
        assert "new_name" in new_content and "old_name" not in new_content
        print(f"✅ Rename: {result.message}")
        return True
    finally:
        temp_path.unlink()

async def test_context_suggestions():
    print("\n🧪 Context Suggestions...")
    from jdev_cli.intelligence.context_suggestions import ContextSuggestionEngine
    from jdev_cli.intelligence.indexer import SemanticIndexer

    indexer = SemanticIndexer(root_path=Path.cwd())
    engine = ContextSuggestionEngine(project_root=Path.cwd(), indexer=indexer)

    test_file = (Path.cwd() / "jdev_cli" / "shell.py").resolve()
    suggestions = engine.suggest_related_files(test_file, max_suggestions=3)

    assert len(suggestions) > 0, "No suggestions returned"
    print(f"✅ Related files: {len(suggestions)} suggestions")
    for rec in suggestions[:3]:
        print(f"   - {rec.file_path.name}: {rec.relevance_score:.2f}")
    return True

async def main():
    print("="*60)
    print("🐕 DOGFOODING - Core Features Test")
    print("="*60)

    results = [
        ("LSP Features", await test_lsp_features()),
        ("Refactoring", await test_refactoring()),
        ("Context Suggestions", await test_context_suggestions()),
    ]

    print("\n" + "="*60)
    print("📊 RESULTS")
    print("="*60)

    passed = sum(1 for _, r in results if r)
    for name, r in results:
        print(f"{'✅ PASS' if r else '❌ FAIL'} - {name}")

    print(f"\nTotal: {passed}/{len(results)} ({passed/len(results)*100:.0f}%)")
    print("\n🎉 ALL FEATURES WORKING!" if passed == len(results) else "\n⚠️ Some issues found")
    return passed == len(results)

if __name__ == "__main__":
    sys.exit(0 if asyncio.run(main()) else 1)
