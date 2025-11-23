"""Bootstrap uvloop for maximum performance."""

import asyncio
import sys
import os


def install_uvloop() -> bool:
    """Install uvloop if available."""
    # Allow disabling via env var for debugging
    if os.environ.get("QWEN_NO_UVLOOP"):
        return False
        
    try:
        import uvloop
        asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
        return True
    except ImportError:
        return False


def get_loop_info() -> dict:
    """Get event loop info."""
    loop = asyncio.get_event_loop()
    loop_type = type(loop).__name__
    module = type(loop).__module__
    
    return {
        'type': loop_type,
        'module': module,
        'using_uvloop': 'uvloop' in module or 'uvloop' in loop_type
    }
