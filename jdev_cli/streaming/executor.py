"""Async command executor with zero UI blocking."""
import logging
logger = logging.getLogger(__name__)

import asyncio
import shlex
import os
from dataclasses import dataclass
from typing import Optional, Dict
from pathlib import Path

from .streams import StreamProcessor, StreamType, LineBufferedStreamReader


@dataclass
class StreamingExecutionResult:
    """Command execution result for streaming executor."""
    exit_code: int
    stdout: str
    stderr: str
    duration: float
    success: bool


class AsyncCommandExecutor:
    """Async command executor with real-time streaming."""

    def __init__(self, cwd: Optional[Path] = None, env: Optional[Dict[str, str]] = None):
        self.cwd = cwd or Path.cwd()
        self.env = env or {}
        self._active_processes: set = set()

    async def execute(
        self,
        command: str,
        shell: bool = True,
        timeout: Optional[float] = None,
        stream_callback: Optional[callable] = None
    ) -> StreamingExecutionResult:
        """Execute command with real-time streaming."""
        import time
        start_time = time.time()

        processor = StreamProcessor()
        if stream_callback:
            processor.add_callback(stream_callback)

        try:
            if shell:
                process = await asyncio.create_subprocess_shell(
                    command,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=str(self.cwd),
                    env={**os.environ, **self.env}
                )
            else:
                cmd_args = shlex.split(command)
                process = await asyncio.create_subprocess_exec(
                    *cmd_args,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=str(self.cwd),
                    env={**os.environ, **self.env}
                )

            self._active_processes.add(process)

            stdout_reader = LineBufferedStreamReader(
                process.stdout, processor, StreamType.STDOUT
            )
            stderr_reader = LineBufferedStreamReader(
                process.stderr, processor, StreamType.STDERR
            )

            stdout_lines = []
            stderr_lines = []

            async def collect_output():
                async for chunk in processor.consume():
                    if chunk.stream_type == StreamType.STDOUT:
                        stdout_lines.append(chunk.content)
                    else:
                        stderr_lines.append(chunk.content)

            reader_tasks = [
                asyncio.create_task(stdout_reader.read_lines()),
                asyncio.create_task(stderr_reader.read_lines()),
            ]
            collector_task = asyncio.create_task(collect_output())

            try:
                if timeout:
                    await asyncio.wait_for(process.wait(), timeout=timeout)
                else:
                    await process.wait()
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()

            await asyncio.gather(*reader_tasks, return_exceptions=True)
            await processor.close()
            await collector_task

            self._active_processes.discard(process)

            duration = time.time() - start_time

            return StreamingExecutionResult(
                exit_code=process.returncode,
                stdout=''.join(stdout_lines),
                stderr=''.join(stderr_lines),
                duration=duration,
                success=process.returncode == 0
            )

        except Exception as e:
            return StreamingExecutionResult(
                exit_code=-1,
                stdout='',
                stderr=str(e),
                duration=time.time() - start_time,
                success=False
            )

    async def execute_parallel(
        self,
        commands: list[str],
        max_concurrent: int = 5
    ) -> list[StreamingExecutionResult]:
        """Execute multiple commands in parallel."""
        semaphore = asyncio.Semaphore(max_concurrent)

        async def execute_with_limit(cmd: str) -> StreamingExecutionResult:
            async with semaphore:
                return await self.execute(cmd)

        tasks = [execute_with_limit(cmd) for cmd in commands]
        return await asyncio.gather(*tasks, return_exceptions=False)

    async def cancel_all(self) -> None:
        """Cancel all active processes."""
        for process in list(self._active_processes):
            try:
                process.kill()
                await process.wait()
            except Exception as e:
                logger.debug(f"Failed to kill process: {e}")
        self._active_processes.clear()
