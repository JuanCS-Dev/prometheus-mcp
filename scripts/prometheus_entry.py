#!/usr/bin/env python3
"""
PROMETHEUS Entry Point for Blaxel.

This is the main entry point for Blaxel deployment.
Exposes the PrometheusAgent as a FastAPI server.

Deploy: bl deploy
Run: bl run prometheus "your task"
"""

import os
import sys
import uuid
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import PROMETHEUS agent
from prometheus.main import PrometheusAgent

logger = logging.getLogger(__name__)

# Global agent instance
_agent: PrometheusAgent = None


def get_agent() -> PrometheusAgent:
    """Get or create the agent instance."""
    global _agent
    if _agent is None:
        _agent = PrometheusAgent()
    return _agent


async def agent(input: str, user_id: str, session_id: str) -> AsyncGenerator[str, None]:
    """
    Main agent function for Blaxel.

    Args:
        input: User input/task
        user_id: User identifier
        session_id: Session identifier

    Yields:
        Response chunks
    """
    prometheus = get_agent()

    try:
        # Stream the response
        async for chunk in prometheus.run(input):
            yield chunk
    except Exception as e:
        logger.error(f"Error during agent execution: {e}")
        yield f"Error: {str(e)}"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan handler."""
    logger.info(f"PROMETHEUS starting on port {os.getenv('BL_SERVER_PORT', 80)}")
    yield
    logger.info("PROMETHEUS shutting down")


# Create FastAPI app
app = FastAPI(
    title="PROMETHEUS",
    description="Self-Evolving Meta-Agent",
    version="1.0.0",
    lifespan=lifespan,
)


@app.post("/")
async def handle_request(request: Request):
    """Handle incoming requests."""
    user_id = request.headers.get("X-User-Id", str(uuid.uuid4()))
    session_id = request.headers.get("X-Session-Id", str(uuid.uuid4()))

    body = await request.json()
    input_text = body.get("inputs", body.get("input", ""))

    return StreamingResponse(
        agent(input_text, user_id, session_id),
        media_type="text/event-stream"
    )


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy", "agent": "prometheus"}


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("BL_SERVER_PORT", os.getenv("PORT", "80")))
    host = os.getenv("BL_SERVER_HOST", "0.0.0.0")

    uvicorn.run(app, host=host, port=port)
