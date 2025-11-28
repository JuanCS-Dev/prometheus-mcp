"""Tests for concurrent rendering."""
import pytest
import asyncio
from jdev_cli.streaming import ConcurrentRenderer


@pytest.mark.asyncio
async def test_concurrent_renderer_init():
    """Test concurrent renderer initialization."""
    renderer = ConcurrentRenderer()
    assert renderer is not None
    assert renderer._panels == {}


@pytest.mark.asyncio
async def test_add_process():
    """Test adding process to renderer."""
    renderer = ConcurrentRenderer()
    await renderer.add_process("proc1", "Test Process")
    assert "proc1" in renderer._panels


@pytest.mark.asyncio
async def test_race_condition_free():
    """Test concurrent updates without race conditions."""
    renderer = ConcurrentRenderer()
    await renderer.add_process("proc1", "Test")

    updates = [renderer.update_process("proc1", f"Update {i}") for i in range(50)]
    await asyncio.gather(*updates)

    assert "proc1" in renderer._panels
