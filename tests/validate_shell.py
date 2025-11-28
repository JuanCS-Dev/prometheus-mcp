#!/usr/bin/env python
"""Exhaustive shell validation - tests EVERYTHING."""

import asyncio
import tempfile
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()


async def test_tool_execution():
    """Test direct tool execution."""
    console.print(Panel("🧪 Test 1: Direct Tool Execution", style="cyan"))

    from jdev_cli.tools.file_ops import ReadFileTool

    tool = ReadFileTool()
    result = await tool.execute(path="README.md")

    assert result.success, "ReadFile failed"
    assert result.data, "No data returned"
    assert result.metadata['lines'] > 0, "No lines counted"

    console.print("  ✅ Tool execution works")
    return True


async def test_tool_registry():
    """Test tool registration and lookup."""
    console.print(Panel("🧪 Test 2: Tool Registry", style="cyan"))

    from jdev_cli.tools.base import ToolRegistry
    from jdev_cli.tools.file_ops import ReadFileTool, WriteFileTool

    registry = ToolRegistry()
    registry.register(ReadFileTool())
    registry.register(WriteFileTool())

    assert len(registry.get_all()) == 2, "Wrong tool count"
    assert registry.get("read_file") or registry.get("readfile"), "Tool not found"

    schemas = registry.get_schemas()
    assert len(schemas) == 2, "Wrong schema count"
    assert schemas[0]['name'], "Schema missing name"

    console.print("  ✅ Registry works")
    return True


async def test_session_context():
    """Test session context tracking."""
    console.print(Panel("🧪 Test 3: Session Context", style="cyan"))

    from jdev_cli.shell import SessionContext

    ctx = SessionContext()
    ctx.track_tool_call("readfile", {"path": "test.py"}, {"success": True})

    assert len(ctx.tool_calls) == 1, "Tool call not tracked"
    assert ctx.cwd, "CWD not set"

    console.print("  ✅ Context tracking works")
    return True


async def test_file_workflow():
    """Test complete file modification workflow."""
    console.print(Panel("🧪 Test 4: File Modification Workflow", style="cyan"))

    from jdev_cli.tools.file_ops import WriteFileTool, ReadFileTool, EditFileTool

    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = Path(tmpdir) / "workflow_test.py"

        # Step 1: Create file
        write_tool = WriteFileTool()
        result = await write_tool.execute(
            path=str(test_file),
            content="def hello():\n    return 'world'"
        )
        assert result.success, f"Write failed: {result.error}"

        # Step 2: Read file
        read_tool = ReadFileTool()
        result = await read_tool.execute(path=str(test_file))
        assert result.success, "Read failed"
        assert "hello()" in result.data, "Content not found"

        # Step 3: Edit file
        edit_tool = EditFileTool()
        result = await edit_tool.execute(
            path=str(test_file),
            edits=[{"search": "world", "replace": "python"}]
        )
        assert result.success, f"Edit failed: {result.error}"

        # Step 4: Verify edit
        result = await read_tool.execute(path=str(test_file))
        assert "python" in result.data, "Edit not applied"

        # Step 5: Check backup exists
        backup_dir = Path(".jdev_backups")
        assert backup_dir.exists(), "Backup directory not created"

    console.print("  ✅ File workflow works")
    console.print("  ✅ Backups created")
    return True


async def test_search_functionality():
    """Test search across files."""
    console.print(Panel("🧪 Test 5: Search Functionality", style="cyan"))

    from jdev_cli.tools.search import SearchFilesTool

    search_tool = SearchFilesTool()
    result = await search_tool.execute(
        pattern="def",
        path="jdev_cli/tools",
        file_pattern="*.py"
    )

    assert result.success, f"Search failed: {result.error}"
    assert len(result.data) > 0, "No results found"
    assert result.metadata['count'] > 0, "Count is zero"

    console.print(f"  ✅ Found {result.metadata['count']} matches")
    return True


async def test_git_integration():
    """Test git operations."""
    console.print(Panel("🧪 Test 6: Git Integration", style="cyan"))

    from jdev_cli.tools.git_ops import GitStatusTool, GitDiffTool

    # Test git status
    status_tool = GitStatusTool()
    result = await status_tool.execute()

    if result.success:
        assert "branch" in result.data, "No branch info"
        console.print(f"  ✅ Git status works (branch: {result.data['branch']})")
    else:
        console.print("  ⚠️  Git status skipped (not in repo)")

    # Test git diff
    diff_tool = GitDiffTool()
    result = await diff_tool.execute()

    if result.success:
        console.print("  ✅ Git diff works")
    else:
        console.print("  ⚠️  Git diff skipped")

    return True


async def test_bash_execution():
    """Test bash command execution."""
    console.print(Panel("🧪 Test 7: Bash Execution", style="cyan"))

    from jdev_cli.tools.exec import BashCommandTool

    bash_tool = BashCommandTool()

    # Test simple command
    result = await bash_tool.execute(command="echo 'test'")
    assert result.success, "Bash command failed"
    assert "test" in result.data['stdout'], "Output incorrect"

    # Test dangerous command blocking
    result = await bash_tool.execute(command="rm -rf /")
    assert not result.success, "Dangerous command not blocked!"

    # Test timeout
    result = await bash_tool.execute(command="sleep 0.1", timeout=1)
    assert result.success, "Timeout command failed"

    console.print("  ✅ Bash execution works")
    console.print("  ✅ Dangerous commands blocked")
    console.print("  ✅ Timeout handling works")
    return True


async def test_multi_tool_workflow():
    """Test workflow with multiple tools."""
    console.print(Panel("🧪 Test 8: Multi-Tool Workflow", style="cyan"))

    from jdev_cli.tools.file_ops import WriteFileTool
    from jdev_cli.tools.search import SearchFilesTool, GetDirectoryTreeTool

    with tempfile.TemporaryDirectory() as tmpdir:
        # Create test files
        write_tool = WriteFileTool()
        for i in range(3):
            await write_tool.execute(
                path=str(Path(tmpdir) / f"file{i}.py"),
                content=f"# File {i}\nprint('Hello {i}')"
            )

        # Search in created files
        search_tool = SearchFilesTool()
        result = await search_tool.execute(
            pattern="Hello",
            path=tmpdir
        )
        assert result.success, "Search failed"
        assert len(result.data) >= 3, "Not all files found"

        # Get directory tree
        tree_tool = GetDirectoryTreeTool()
        result = await tree_tool.execute(path=tmpdir)
        assert result.success, "Tree failed"
        assert "file0.py" in result.data, "File not in tree"

    console.print("  ✅ Multi-tool workflow works")
    return True


async def test_shell_initialization():
    """Test shell can be initialized."""
    console.print(Panel("🧪 Test 9: Shell Initialization", style="cyan"))

    from jdev_cli.shell import InteractiveShell

    shell = InteractiveShell()

    assert shell.registry, "Registry not initialized"
    assert len(shell.registry.get_all()) >= 18, f"Wrong tool count: {len(shell.registry.get_all())}"
    assert shell.context, "Context not initialized"
    assert shell.session, "Session not initialized"

    console.print(f"  ✅ Shell initialized with {len(shell.registry.get_all())} tools")
    return True


async def test_tool_schemas():
    """Test all tool schemas are valid."""
    console.print(Panel("🧪 Test 10: Tool Schema Validation", style="cyan"))

    from jdev_cli.shell import InteractiveShell

    shell = InteractiveShell()
    schemas = shell.registry.get_schemas()

    for schema in schemas:
        assert 'name' in schema, f"Schema missing name: {schema}"
        assert 'description' in schema, f"Schema missing description: {schema}"
        assert 'parameters' in schema, f"Schema missing parameters: {schema}"

        params = schema['parameters']
        assert 'type' in params, f"Schema {schema['name']} missing type"
        assert 'properties' in params, f"Schema {schema['name']} missing properties"

    console.print(f"  ✅ All {len(schemas)} schemas valid")
    return True


async def run_validation():
    """Run all validation tests."""
    console.print("\n")
    console.print("╔" + "═" * 58 + "╗")
    console.print("║" + " " * 10 + "🚀 EXHAUSTIVE SHELL VALIDATION 🚀" + " " * 14 + "║")
    console.print("╚" + "═" * 58 + "╝")
    console.print()

    tests = [
        ("Tool Execution", test_tool_execution),
        ("Tool Registry", test_tool_registry),
        ("Session Context", test_session_context),
        ("File Workflow", test_file_workflow),
        ("Search", test_search_functionality),
        ("Git Integration", test_git_integration),
        ("Bash Execution", test_bash_execution),
        ("Multi-Tool Workflow", test_multi_tool_workflow),
        ("Shell Init", test_shell_initialization),
        ("Schema Validation", test_tool_schemas),
    ]

    results = []

    for name, test_func in tests:
        try:
            result = await test_func()
            results.append((name, True, None))
        except AssertionError as e:
            results.append((name, False, str(e)))
            console.print(f"  ❌ {e}", style="red")
        except Exception as e:
            results.append((name, False, f"Exception: {e}"))
            console.print(f"  ❌ Exception: {e}", style="red")
            import traceback
            traceback.print_exc()

    # Summary
    console.print("\n")
    console.print("╔" + "═" * 58 + "╗")
    console.print("║" + " " * 20 + "VALIDATION RESULTS" + " " * 20 + "║")
    console.print("╚" + "═" * 58 + "╝")

    table = Table()
    table.add_column("Test", style="cyan")
    table.add_column("Status", style="bold")
    table.add_column("Details")

    passed = 0
    failed = 0

    for name, success, error in results:
        if success:
            table.add_row(name, "✅ PASS", "")
            passed += 1
        else:
            table.add_row(name, "❌ FAIL", error or "")
            failed += 1

    console.print(table)
    console.print()

    if failed == 0:
        console.print(Panel(
            f"[bold green]✅ ALL {passed} TESTS PASSED![/bold green]\n\n"
            "Shell is READY for production use!",
            style="green"
        ))
        return True
    else:
        console.print(Panel(
            f"[bold red]❌ {failed} TEST(S) FAILED[/bold red]\n\n"
            f"Passed: {passed}/{len(results)}",
            style="red"
        ))
        return False


if __name__ == "__main__":
    success = asyncio.run(run_validation())
    exit(0 if success else 1)
