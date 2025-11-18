#!/usr/bin/env python
"""Comprehensive Context Awareness Tests - Phase 3.5 Validation."""

import asyncio
import tempfile
import os
from pathlib import Path
import pytest

from qwen_dev_cli.shell import InteractiveShell, SessionContext
from qwen_dev_cli.core.context import ContextBuilder


class TestSessionContext:
    def test_initial_state(self):
        ctx = SessionContext()
        assert ctx.cwd == os.getcwd()
        assert len(ctx.tool_calls) == 0
    
    def test_track_file_modifications(self):
        ctx = SessionContext()
        ctx.track_tool_call(
            "write_file",
            {"path": "test.py"},
            type('obj', (object,), {'success': True})()
        )
        assert "test.py" in ctx.modified_files


class TestContextBuilder:
    def test_read_single_file(self):
        builder = ContextBuilder(max_files=5)
        success, content, error = builder.read_file("README.md")
        assert success, f"Failed: {error}"
        assert len(content) > 0
    
    def test_add_file_to_context(self):
        builder = ContextBuilder(max_files=3)
        success, msg = builder.add_file("README.md")
        assert success
        stats = builder.get_stats()
        assert stats['files'] == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
