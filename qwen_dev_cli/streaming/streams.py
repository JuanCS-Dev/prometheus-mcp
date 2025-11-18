"""Real-time stream processing (Producer-Consumer pattern)."""

import asyncio
from dataclasses import dataclass
from enum import Enum
from typing import AsyncIterator, Optional, Callable


class StreamType(Enum):
    """Stream types."""
    STDOUT = "stdout"
    STDERR = "stderr"
    SYSTEM = "system"


@dataclass
class OutputChunk:
    """Single output chunk from stream."""
    content: str
    stream_type: StreamType
    timestamp: float
    sequence: int


class StreamProcessor:
    """
    Real-time stream processor with zero-buffering.
    
    Implements Cursor-style streaming: line-by-line emission as produced.
    """
    
    def __init__(self, max_buffer: int = 1000):
        self.max_buffer = max_buffer
        self._queue: asyncio.Queue[Optional[OutputChunk]] = asyncio.Queue()
        self._sequence = 0
        self._callbacks: list[Callable[[OutputChunk], None]] = []
    
    def add_callback(self, callback: Callable[[OutputChunk], None]) -> None:
        """Register callback for each chunk."""
        self._callbacks.append(callback)
    
    async def feed(self, content: str, stream_type: StreamType) -> None:
        """Feed content to stream (producer side)."""
        import time
        
        chunk = OutputChunk(
            content=content,
            stream_type=stream_type,
            timestamp=time.time(),
            sequence=self._sequence
        )
        self._sequence += 1
        
        # Notify callbacks immediately
        for cb in self._callbacks:
            try:
                if asyncio.iscoroutinefunction(cb):
                    asyncio.create_task(cb(chunk))
                else:
                    cb(chunk)
            except Exception:
                pass
        
        await self._queue.put(chunk)
    
    async def consume(self) -> AsyncIterator[OutputChunk]:
        """Consume stream (consumer side)."""
        while True:
            chunk = await self._queue.get()
            if chunk is None:
                break
            yield chunk
    
    async def close(self) -> None:
        """Signal end of stream."""
        await self._queue.put(None)
    
    def is_empty(self) -> bool:
        """Check if queue is empty."""
        return self._queue.empty()


class LineBufferedStreamReader:
    """
    Line-buffered async reader for subprocess pipes.
    
    Yields complete lines immediately (Claude Code pattern).
    """
    
    def __init__(self, stream: asyncio.StreamReader, processor: StreamProcessor, stream_type: StreamType):
        self.stream = stream
        self.processor = processor
        self.stream_type = stream_type
        self._buffer = ""
    
    async def read_lines(self) -> None:
        """Read and emit lines as they arrive."""
        try:
            while True:
                chunk = await self.stream.read(1024)
                if not chunk:
                    if self._buffer:
                        await self.processor.feed(self._buffer, self.stream_type)
                    break
                
                text = chunk.decode('utf-8', errors='replace')
                self._buffer += text
                
                while '\n' in self._buffer:
                    line, self._buffer = self._buffer.split('\n', 1)
                    await self.processor.feed(line + '\n', self.stream_type)
        
        except asyncio.CancelledError:
            raise
        except Exception:
            pass
