#!/usr/bin/env python
"""Test terminal navigation tools."""

import asyncio
import tempfile
import os
from pathlib import Path

from jdev_cli.tools.terminal import (
    CdTool, LsTool, PwdTool, MkdirTool, RmTool,
    CpTool, MvTool, TouchTool, CatTool
)


async def test_pwd_tool():
    """Test pwd command."""
    print("Testing pwd...")
    pwd = PwdTool()
    result = await pwd.execute()
    assert result.success
    assert result.data
    print(f"  ✓ pwd works: {result.data}")


async def test_cd_tool():
    """Test cd command."""
    print("Testing cd...")
    cd = CdTool()
    original_dir = os.getcwd()

    try:
        # Test cd to parent
        result = await cd.execute("..")
        assert result.success
        print("  ✓ cd .. works")

        # Test cd to home
        result = await cd.execute("~")
        assert result.success
        print("  ✓ cd ~ works")

        # Test cd back
        os.chdir(original_dir)
        print("  ✓ cd restored")
    finally:
        os.chdir(original_dir)


async def test_ls_tool():
    """Test ls command."""
    print("Testing ls...")
    ls = LsTool()

    # Basic ls
    result = await ls.execute(".")
    assert result.success
    assert len(result.data) > 0
    print(f"  ✓ ls works ({result.metadata['count']} items)")

    # ls -a
    result = await ls.execute(".", all=True)
    assert result.success
    print(f"  ✓ ls -a works ({result.metadata['count']} items)")

    # ls -l
    result = await ls.execute(".", long=True)
    assert result.success
    assert 'size' in result.data[0]
    print("  ✓ ls -l works")


async def test_mkdir_tool():
    """Test mkdir command."""
    print("Testing mkdir...")
    mkdir = MkdirTool()

    with tempfile.TemporaryDirectory() as tmpdir:
        test_dir = Path(tmpdir) / "testdir"

        result = await mkdir.execute(str(test_dir))
        assert result.success
        assert test_dir.exists()
        print("  ✓ mkdir works")

        # Test mkdir -p
        nested = Path(tmpdir) / "a" / "b" / "c"
        result = await mkdir.execute(str(nested), parents=True)
        assert result.success
        assert nested.exists()
        print("  ✓ mkdir -p works")


async def test_touch_tool():
    """Test touch command."""
    print("Testing touch...")
    touch = TouchTool()

    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = Path(tmpdir) / "test.txt"

        result = await touch.execute(str(test_file))
        assert result.success
        assert test_file.exists()
        print("  ✓ touch works")


async def test_cat_tool():
    """Test cat command."""
    print("Testing cat...")
    cat = CatTool()

    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = Path(tmpdir) / "test.txt"
        test_file.write_text("Line 1\nLine 2\nLine 3")

        result = await cat.execute(str(test_file))
        assert result.success
        assert "Line 1" in result.data
        print("  ✓ cat works")

        # Test head -n
        result = await cat.execute(str(test_file), lines=2)
        assert result.success
        assert result.data.count('\n') <= 2
        print("  ✓ cat with lines works")


async def test_cp_tool():
    """Test cp command."""
    print("Testing cp...")
    cp = CpTool()

    with tempfile.TemporaryDirectory() as tmpdir:
        src = Path(tmpdir) / "source.txt"
        dst = Path(tmpdir) / "dest.txt"
        src.write_text("test content")

        result = await cp.execute(str(src), str(dst))
        assert result.success
        assert dst.exists()
        assert dst.read_text() == "test content"
        print("  ✓ cp works")

        # Test cp -r
        src_dir = Path(tmpdir) / "srcdir"
        src_dir.mkdir()
        (src_dir / "file.txt").write_text("content")
        dst_dir = Path(tmpdir) / "dstdir"

        result = await cp.execute(str(src_dir), str(dst_dir), recursive=True)
        assert result.success
        assert (dst_dir / "file.txt").exists()
        print("  ✓ cp -r works")


async def test_mv_tool():
    """Test mv command."""
    print("Testing mv...")
    mv = MvTool()

    with tempfile.TemporaryDirectory() as tmpdir:
        src = Path(tmpdir) / "old.txt"
        dst = Path(tmpdir) / "new.txt"
        src.write_text("content")

        result = await mv.execute(str(src), str(dst))
        assert result.success
        assert not src.exists()
        assert dst.exists()
        print("  ✓ mv works")


async def test_rm_tool():
    """Test rm command."""
    print("Testing rm...")
    rm = RmTool()

    with tempfile.TemporaryDirectory() as tmpdir:
        # Test rm file
        test_file = Path(tmpdir) / "test.txt"
        test_file.write_text("content")

        result = await rm.execute(str(test_file))
        assert result.success
        assert not test_file.exists()
        print("  ✓ rm works")

        # Test rm -r
        test_dir = Path(tmpdir) / "testdir"
        test_dir.mkdir()
        (test_dir / "file.txt").write_text("content")

        result = await rm.execute(str(test_dir), recursive=True)
        assert result.success
        assert not test_dir.exists()
        print("  ✓ rm -r works")

        # Test safety check
        result = await rm.execute("/", recursive=True)
        assert not result.success
        assert "protected" in result.error.lower()
        print("  ✓ rm safety works")


async def run_tests():
    """Run all terminal tool tests."""
    print("\n" + "=" * 60)
    print("🧪 TERMINAL TOOLS TEST SUITE")
    print("=" * 60 + "\n")

    tests = [
        test_pwd_tool,
        test_cd_tool,
        test_ls_tool,
        test_mkdir_tool,
        test_touch_tool,
        test_cat_tool,
        test_cp_tool,
        test_mv_tool,
        test_rm_tool,
    ]

    for test in tests:
        try:
            await test()
        except AssertionError as e:
            print(f"  ❌ FAILED: {e}")
            return False
        except Exception as e:
            print(f"  ❌ ERROR: {e}")
            import traceback
            traceback.print_exc()
            return False

    print("\n" + "=" * 60)
    print("✅ ALL TERMINAL TOOLS TESTS PASSED!")
    print("=" * 60)
    return True


if __name__ == "__main__":
    success = asyncio.run(run_tests())
    exit(0 if success else 1)
