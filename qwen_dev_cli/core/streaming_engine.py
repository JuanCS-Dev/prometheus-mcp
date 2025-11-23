"""Ultra-fast streaming engine."""

import asyncio
from typing import AsyncGenerator, List, Dict, Any


class StreamingEngine:
    """Optimized streaming for LLM responses."""
    
    def __init__(self, chunk_size: int = 15):
        # 15 chars is a good balance between smoothness and responsiveness
        self.chunk_size = chunk_size
        
    async def stream_with_chunking(
        self, 
        generator: AsyncGenerator[str, None]
    ) -> AsyncGenerator[str, None]:
        """Stream com chunking inteligente."""
        buffer = ""
        
        async for chunk in generator:
            buffer += chunk
            
            # Flush buffer quando atinge tamanho ideal
            # This prevents stuttering by outputting slightly larger chunks
            # but still frequent enough to feel instant
            if len(buffer) >= self.chunk_size:
                yield buffer
                buffer = ""
                
            # Yield immediately to event loop to keep UI responsive
            # This is crucial for allowing other async tasks (like keypress detection)
            await asyncio.sleep(0)
            
        # Flush remaining buffer
        if buffer:
            yield buffer
