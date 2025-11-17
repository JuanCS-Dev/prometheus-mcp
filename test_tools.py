#!/usr/bin/env python
"""Comprehensive tool testing suite."""

import asyncio
import tempfile
import shutil
from pathlib import Path

from qwen_dev_cli.tools.file_ops import (
    ReadFileTool, WriteFileTool, EditFileTool,
    ListDirectoryTool, DeleteFileTool
)
from qwen_dev_cli.tools.file_mgmt import (
    MoveFileTool, CopyFileTool, CreateDirectoryTool,
    ReadMultipleFilesTool, InsertLinesTool
)
from qwen_dev_cli.tools.search import SearchFilesTool, GetDirectoryTreeTool
from qwen_dev_cli.tools.exec import BashCommandTool
from qwen_dev_cli.tools.git_ops import GitStatusTool, GitDiffTool


async def test_file_ops():
    """Test file operation tools."""
    print("\n🧪 Testing File Operations...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = Path(tmpdir) / "test.txt"
        
        # Test write_file
        print("  Testing write_file...")
        write_tool = WriteFileTool()
        result = await write_tool.execute(
            path=str(test_file),
            content="Hello World\nLine 2"
        )
        assert result.success, f"write_file failed: {result.error}"
        assert test_file.exists()
        print("    ✓ write_file works")
        
        # Test read_file
        print("  Testing read_file...")
        read_tool = ReadFileTool()
        result = await read_tool.execute(path=str(test_file))
        assert result.success
        assert "Hello World" in result.data
        assert result.metadata['lines'] == 2
        print("    ✓ read_file works")
        
        # Test edit_file
        print("  Testing edit_file...")
        edit_tool = EditFileTool()
        result = await edit_tool.execute(
            path=str(test_file),
            edits=[{"search": "Hello World", "replace": "Hello Python"}]
        )
        assert result.success
        content = test_file.read_text()
        assert "Hello Python" in content
        print("    ✓ edit_file works")
        
        # Test list_directory
        print("  Testing list_directory...")
        list_tool = ListDirectoryTool()
        result = await list_tool.execute(path=tmpdir)
        assert result.success
        assert len(result.data['files']) == 1
        print("    ✓ list_directory works")
        
        # Test insert_lines
        print("  Testing insert_lines...")
        insert_tool = InsertLinesTool()
        result = await insert_tool.execute(
            path=str(test_file),
            line_number=2,
            content="Inserted line"
        )
        assert result.success
        lines = test_file.read_text().split('\n')
        assert "Inserted line" in lines
        print("    ✓ insert_lines works")


async def test_file_mgmt():
    """Test file management tools."""
    print("\n🧪 Testing File Management...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        
        # Create test file
        test_file = tmpdir / "original.txt"
        test_file.write_text("Test content")
        
        # Test copy_file
        print("  Testing copy_file...")
        copy_tool = CopyFileTool()
        result = await copy_tool.execute(
            source=str(test_file),
            destination=str(tmpdir / "copy.txt")
        )
        assert result.success
        assert (tmpdir / "copy.txt").exists()
        print("    ✓ copy_file works")
        
        # Test move_file
        print("  Testing move_file...")
        move_tool = MoveFileTool()
        result = await move_tool.execute(
            source=str(tmpdir / "copy.txt"),
            destination=str(tmpdir / "moved.txt")
        )
        assert result.success
        assert (tmpdir / "moved.txt").exists()
        assert not (tmpdir / "copy.txt").exists()
        print("    ✓ move_file works")
        
        # Test create_directory
        print("  Testing create_directory...")
        mkdir_tool = CreateDirectoryTool()
        result = await mkdir_tool.execute(path=str(tmpdir / "newdir"))
        assert result.success
        assert (tmpdir / "newdir").is_dir()
        print("    ✓ create_directory works")
        
        # Test read_multiple_files
        print("  Testing read_multiple_files...")
        read_multi_tool = ReadMultipleFilesTool()
        result = await read_multi_tool.execute(
            paths=[str(test_file), str(tmpdir / "moved.txt")]
        )
        assert result.success
        assert len(result.data) == 2
        print("    ✓ read_multiple_files works")


async def test_search():
    """Test search tools."""
    print("\n🧪 Testing Search Tools...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        
        # Create test files
        (tmpdir / "file1.py").write_text("def hello():\n    print('Hello')")
        (tmpdir / "file2.py").write_text("def world():\n    print('World')")
        
        # Test search_files
        print("  Testing search_files...")
        search_tool = SearchFilesTool()
        result = await search_tool.execute(
            pattern="def",
            path=str(tmpdir),
            file_pattern="*.py"
        )
        assert result.success
        assert len(result.data) >= 2
        print("    ✓ search_files works")
        
        # Test get_directory_tree
        print("  Testing get_directory_tree...")
        tree_tool = GetDirectoryTreeTool()
        result = await tree_tool.execute(path=str(tmpdir))
        assert result.success
        assert "file1.py" in result.data
        print("    ✓ get_directory_tree works")


async def test_execution():
    """Test execution tools."""
    print("\n🧪 Testing Execution Tools...")
    
    # Test bash_command
    print("  Testing bash_command...")
    bash_tool = BashCommandTool()
    result = await bash_tool.execute(command="echo 'Hello from bash'")
    assert result.success
    assert "Hello from bash" in result.data['stdout']
    print("    ✓ bash_command works")
    
    # Test with timeout
    print("  Testing bash_command timeout...")
    result = await bash_tool.execute(command="sleep 0.1", timeout=1)
    assert result.success
    print("    ✓ bash_command timeout works")
    
    # Test dangerous command blocking
    print("  Testing dangerous command blocking...")
    result = await bash_tool.execute(command="rm -rf /")
    assert not result.success
    assert "Dangerous command blocked" in result.error
    print("    ✓ dangerous command blocking works")


async def test_git():
    """Test git tools."""
    print("\n🧪 Testing Git Tools...")
    
    # Test git_status
    print("  Testing git_status...")
    status_tool = GitStatusTool()
    result = await status_tool.execute()
    # Should work in our git repo
    if result.success:
        assert "branch" in result.data
        print("    ✓ git_status works")
    else:
        print("    ⚠ git_status skipped (not in repo)")
    
    # Test git_diff
    print("  Testing git_diff...")
    diff_tool = GitDiffTool()
    result = await diff_tool.execute()
    if result.success:
        print("    ✓ git_diff works")
    else:
        print("    ⚠ git_diff skipped (not in repo)")


async def run_all_tests():
    """Run all tool tests."""
    print("=" * 60)
    print("🚀 QWEN-DEV-CLI Tool Test Suite")
    print("=" * 60)
    
    try:
        await test_file_ops()
        await test_file_mgmt()
        await test_search()
        await test_execution()
        await test_git()
        
        print("\n" + "=" * 60)
        print("✅ ALL TESTS PASSED!")
        print("=" * 60)
        return True
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        return False
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    exit(0 if success else 1)
