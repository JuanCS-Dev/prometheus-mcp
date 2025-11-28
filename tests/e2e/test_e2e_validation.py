#!/usr/bin/env python3
"""
End-to-End Validation Test
Boris Cherny - Week 4 Day 4 Scientific Validation
"""
import sys
import tempfile
from pathlib import Path

# Test 1: Shell can initialize
def test_shell_initialization():
    print("🧪 Test 1: Shell Initialization...")
    from jdev_cli.shell import InteractiveShell

    try:
        shell = InteractiveShell()
        assert shell.indexer is not None, "Indexer not initialized"
        assert shell.lsp_client is not None, "LSP client not initialized"
        assert shell.suggestion_engine is not None, "Suggestion engine not initialized"
        assert shell.refactoring_engine is not None, "Refactoring engine not initialized"
        assert shell.context_manager is not None, "Context manager not initialized"
        print("✅ PASS: Shell initialized with all components")
        return True
    except Exception as e:
        print(f"❌ FAIL: {e}")
        return False

# Test 2: LSP multi-language detection
def test_lsp_language_detection():
    print("\n🧪 Test 2: LSP Language Detection...")
    from jdev_cli.intelligence.lsp_client import Language

    tests = [
        (Path("test.py"), Language.PYTHON),
        (Path("test.ts"), Language.TYPESCRIPT),
        (Path("test.tsx"), Language.TYPESCRIPT),
        (Path("test.js"), Language.JAVASCRIPT),
        (Path("test.go"), Language.GO),
        (Path("test.txt"), Language.UNKNOWN),
    ]

    passed = 0
    for file_path, expected in tests:
        detected = Language.detect(file_path)
        if detected == expected:
            passed += 1
        else:
            print(f"  ❌ {file_path.suffix}: Expected {expected}, got {detected}")

    if passed == len(tests):
        print(f"✅ PASS: All {len(tests)} language detections correct")
        return True
    else:
        print(f"❌ FAIL: {passed}/{len(tests)} correct")
        return False

# Test 3: Refactoring engine
def test_refactoring_engine():
    print("\n🧪 Test 3: Refactoring Engine...")
    from jdev_cli.refactoring.engine import RefactoringEngine

    engine = RefactoringEngine(project_root=Path.cwd())

    # Create temp file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write('def old_func():\n    pass\n\nresult = old_func()\n')
        temp_file = Path(f.name)

    try:
        # Test rename
        result = engine.rename_symbol(temp_file, "old_func", "new_func")

        if not result.success:
            print(f"❌ FAIL: Rename failed: {result.error}")
            return False

        content = temp_file.read_text()

        if "new_func" not in content:
            print("❌ FAIL: new_func not in file")
            return False

        if "old_func" in content:
            print("❌ FAIL: old_func still in file")
            return False

        print("✅ PASS: Refactoring engine works correctly")
        return True

    finally:
        temp_file.unlink()

# Test 4: LSP completion data structures
def test_lsp_completion_structures():
    print("\n🧪 Test 4: LSP Completion Structures...")
    from jdev_cli.intelligence.lsp_client import CompletionItem, SignatureHelp, SignatureInformation, ParameterInformation

    try:
        # Test CompletionItem
        item_data = {
            "label": "test_func",
            "kind": 3,
            "detail": "() -> None",
            "documentation": "Test function"
        }
        item = CompletionItem.from_lsp(item_data)
        assert item.label == "test_func"
        assert item.kind_name == "Function"

        # Test ParameterInformation
        param_data = {"label": "x: int", "documentation": "Parameter x"}
        param = ParameterInformation.from_lsp(param_data)
        assert param.label == "x: int"

        # Test SignatureInformation
        sig_data = {
            "label": "func(x: int) -> str",
            "parameters": [{"label": "x: int"}]
        }
        sig = SignatureInformation.from_lsp(sig_data)
        assert sig.label == "func(x: int) -> str"
        assert len(sig.parameters) == 1

        # Test SignatureHelp
        help_data = {
            "signatures": [sig_data],
            "activeSignature": 0,
            "activeParameter": 0
        }
        help_obj = SignatureHelp.from_lsp(help_data)
        assert len(help_obj.signatures) == 1

        print("✅ PASS: All LSP data structures parse correctly")
        return True

    except Exception as e:
        print(f"❌ FAIL: {e}")
        return False

# Test 5: Edge cases
def test_edge_cases():
    print("\n🧪 Test 5: Edge Cases...")
    from jdev_cli.refactoring.engine import RefactoringEngine

    engine = RefactoringEngine(project_root=Path.cwd())

    # Test 5.1: Empty file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write('')
        temp_file = Path(f.name)

    try:
        result = engine.organize_imports(temp_file)
        if result.success:
            print("  ❌ Empty file should fail gracefully")
            return False
        print("  ✅ Empty file handled correctly")

        # Test 5.2: Rename nonexistent symbol
        temp_file.write_text('def func():\n    pass\n')
        result = engine.rename_symbol(temp_file, "nonexistent", "new_name")

        if result.success and result.message == "Renamed 0 occurrences":
            print("  ✅ Nonexistent symbol handled correctly")
        else:
            print(f"  ❌ Expected 0 occurrences: {result.message}")
            return False

        print("✅ PASS: Edge cases handled correctly")
        return True

    finally:
        temp_file.unlink()

# Test 6: Constitutional compliance (P3 - Ceticismo)
def test_constitutional_compliance():
    print("\n🧪 Test 6: Constitutional Compliance (P3 - Ceticismo)...")

    # Test error handling exists
    from jdev_cli.refactoring.engine import RefactoringEngine

    engine = RefactoringEngine(project_root=Path.cwd())

    # Test with nonexistent file
    fake_file = Path("/tmp/nonexistent_file_123456789.py")

    try:
        result = engine.rename_symbol(fake_file, "old", "new")

        if not result.success and result.error:
            print("  ✅ Error handling present (nonexistent file)")
        else:
            print("  ❌ Should have failed with error")
            return False

        print("✅ PASS: Constitutional compliance verified")
        return True

    except Exception as e:
        print(f"  ❌ Unhandled exception (should be caught): {e}")
        return False

def main():
    print("="*70)
    print("🔬 END-TO-END SCIENTIFIC VALIDATION")
    print("="*70)

    tests = [
        ("Shell Initialization", test_shell_initialization),
        ("LSP Language Detection", test_lsp_language_detection),
        ("Refactoring Engine", test_refactoring_engine),
        ("LSP Data Structures", test_lsp_completion_structures),
        ("Edge Cases", test_edge_cases),
        ("Constitutional Compliance", test_constitutional_compliance),
    ]

    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n❌ CRASH in {name}: {e}")
            results.append((name, False))

    print("\n" + "="*70)
    print("📊 FINAL RESULTS")
    print("="*70)

    passed = sum(1 for _, r in results if r)
    total = len(results)

    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {name}")

    pct = passed/total*100
    print(f"\nTotal: {passed}/{total} ({pct:.0f}%)")

    if passed == total:
        print("\n🎉 ALL E2E TESTS PASSED - PRODUCTION READY!")
        return 0
    else:
        print(f"\n⚠️ {total-passed} tests failed - needs attention")
        return 1

if __name__ == "__main__":
    sys.exit(main())
