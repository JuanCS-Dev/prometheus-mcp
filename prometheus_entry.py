#!/usr/bin/env python3
"""
🔥 PROMETHEUS Entry Point for Blaxel

This is the main entry point for Blaxel deployment.
It exposes the PrometheusAgent to the Blaxel runtime.

Deploy: bl deploy
Run: bl run prometheus "your task"
"""

import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import and expose the agent
from prometheus.main import PrometheusAgent, agent

# The 'agent' singleton is what Blaxel will use
__all__ = ['agent', 'PrometheusAgent']

if __name__ == "__main__":
    import asyncio
    from prometheus.main import main
    asyncio.run(main())
