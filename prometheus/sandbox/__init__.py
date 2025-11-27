"""
PROMETHEUS Sandbox Module.

Secure code execution environment inspired by E2B (e2b.dev):
- Isolated Python execution
- Timeout protection
- Resource limits
- Output capture
"""

from .executor import SandboxExecutor, SandboxResult

__all__ = [
    "SandboxExecutor",
    "SandboxResult",
]
