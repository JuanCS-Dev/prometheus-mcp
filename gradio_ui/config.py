"""
Lightweight settings loader for the Gradio UI.

Reads environment variables so the UI can talk to the FastAPI bridge when
available without hardcoding URLs or credentials.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import os
from typing import Optional


@dataclass(frozen=True)
class APISettings:
    """Configuration for the bridge layer (FastAPI)."""

    base_url: Optional[str]
    api_token: Optional[str]
    request_timeout: float


@lru_cache(maxsize=1)
def load_api_settings() -> APISettings:
    """Load API settings from environment variables (cached)."""
    base = (
        os.getenv("QWEN_DEV_API_BASE")
        or os.getenv("GRADIO_API_BASE")
        or os.getenv("FASTAPI_BRIDGE_BASE")
    )
    token = (
        os.getenv("QWEN_DEV_API_TOKEN")
        or os.getenv("GRADIO_API_TOKEN")
        or os.getenv("FASTAPI_BRIDGE_TOKEN")
    )
    try:
        timeout = float(os.getenv("QWEN_DEV_API_TIMEOUT", "120"))
    except ValueError:
        timeout = 120.0

    if base:
        base = base.rstrip("/")

    return APISettings(base_url=base, api_token=token, request_timeout=timeout)

