"""
Async File Operations.

SCALE & SUSTAIN Phase 3.1 - Async Everywhere.

Async wrappers for file I/O operations using aiofiles.
Falls back to sync operations in thread pool if aiofiles not available.

Author: JuanCS Dev
Date: 2025-11-26
"""

import asyncio
import json
from pathlib import Path
from typing import Any, List, Union

# Try to import aiofiles, fallback to thread pool
try:
    import aiofiles
    import aiofiles.os
    AIOFILES_AVAILABLE = True
except ImportError:
    AIOFILES_AVAILABLE = False


async def read_file(
    path: Union[str, Path],
    encoding: str = 'utf-8'
) -> str:
    """
    Read file contents asynchronously.

    Args:
        path: File path
        encoding: File encoding

    Returns:
        File contents as string
    """
    path = Path(path)

    if AIOFILES_AVAILABLE:
        async with aiofiles.open(path, 'r', encoding=encoding) as f:
            return await f.read()
    else:
        # Fallback to thread pool
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: path.read_text(encoding=encoding)
        )


async def write_file(
    path: Union[str, Path],
    content: str,
    encoding: str = 'utf-8',
    create_dirs: bool = True
) -> None:
    """
    Write content to file asynchronously.

    Args:
        path: File path
        content: Content to write
        encoding: File encoding
        create_dirs: Create parent directories if needed
    """
    path = Path(path)

    if create_dirs:
        path.parent.mkdir(parents=True, exist_ok=True)

    if AIOFILES_AVAILABLE:
        async with aiofiles.open(path, 'w', encoding=encoding) as f:
            await f.write(content)
    else:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            lambda: path.write_text(content, encoding=encoding)
        )


async def read_json(path: Union[str, Path]) -> Any:
    """
    Read JSON file asynchronously.

    Args:
        path: File path

    Returns:
        Parsed JSON data
    """
    content = await read_file(path)
    return json.loads(content)


async def write_json(
    path: Union[str, Path],
    data: Any,
    indent: int = 2
) -> None:
    """
    Write data to JSON file asynchronously.

    Args:
        path: File path
        data: Data to serialize
        indent: JSON indentation
    """
    content = json.dumps(data, indent=indent, ensure_ascii=False)
    await write_file(path, content)


async def file_exists(path: Union[str, Path]) -> bool:
    """
    Check if file exists asynchronously.

    Args:
        path: File path

    Returns:
        True if file exists
    """
    path = Path(path)

    if AIOFILES_AVAILABLE:
        return await aiofiles.os.path.exists(path)
    else:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, path.exists)


async def list_dir(
    path: Union[str, Path],
    pattern: str = '*'
) -> List[Path]:
    """
    List directory contents asynchronously.

    Args:
        path: Directory path
        pattern: Glob pattern

    Returns:
        List of paths
    """
    path = Path(path)
    loop = asyncio.get_event_loop()

    return await loop.run_in_executor(
        None,
        lambda: list(path.glob(pattern))
    )


async def read_bytes(path: Union[str, Path]) -> bytes:
    """
    Read file as bytes asynchronously.

    Args:
        path: File path

    Returns:
        File contents as bytes
    """
    path = Path(path)

    if AIOFILES_AVAILABLE:
        async with aiofiles.open(path, 'rb') as f:
            return await f.read()
    else:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, path.read_bytes)


async def write_bytes(
    path: Union[str, Path],
    data: bytes,
    create_dirs: bool = True
) -> None:
    """
    Write bytes to file asynchronously.

    Args:
        path: File path
        data: Bytes to write
        create_dirs: Create parent directories if needed
    """
    path = Path(path)

    if create_dirs:
        path.parent.mkdir(parents=True, exist_ok=True)

    if AIOFILES_AVAILABLE:
        async with aiofiles.open(path, 'wb') as f:
            await f.write(data)
    else:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, lambda: path.write_bytes(data))


# Sync wrappers for compatibility
def read_file_sync(path: Union[str, Path], encoding: str = 'utf-8') -> str:
    """Sync wrapper for read_file."""
    return asyncio.run(read_file(path, encoding))


def write_file_sync(path: Union[str, Path], content: str) -> None:
    """Sync wrapper for write_file."""
    asyncio.run(write_file(path, content))


__all__ = [
    'read_file',
    'write_file',
    'read_json',
    'write_json',
    'file_exists',
    'list_dir',
    'read_bytes',
    'write_bytes',
    'read_file_sync',
    'write_file_sync',
    'AIOFILES_AVAILABLE',
]
