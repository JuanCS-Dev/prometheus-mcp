"""MCP Server CLI entry point."""
import sys
import asyncio
import logging
from jdev_cli.integrations.mcp import MCPConfig, run_mcp_server
from jdev_cli.tools.registry_helper import get_default_registry


def main():
    """Run MCP server from command line."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    config = MCPConfig.from_env()
    config.enabled = True

    registry = get_default_registry()

    try:
        asyncio.run(run_mcp_server(registry, config))
    except KeyboardInterrupt:
        print("\nMCP server stopped by user", file=sys.stderr)
        sys.exit(0)
    except Exception as e:
        print(f"MCP server error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
