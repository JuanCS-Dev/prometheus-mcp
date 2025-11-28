"""Helper to create default registry instance."""
from jdev_cli.tools.base import ToolRegistry
from jdev_cli.tools.file_ops import (
    ReadFileTool, WriteFileTool, EditFileTool,
    ListDirectoryTool, DeleteFileTool
)
from jdev_cli.tools.file_mgmt import (
    MoveFileTool, CopyFileTool, CreateDirectoryTool,
    ReadMultipleFilesTool, InsertLinesTool
)
from jdev_cli.tools.search import SearchFilesTool, GetDirectoryTreeTool
from jdev_cli.tools.exec_hardened import BashCommandTool
from jdev_cli.tools.git_ops import GitStatusTool, GitDiffTool
from jdev_cli.tools.context import GetContextTool, SaveSessionTool, RestoreBackupTool
from jdev_cli.tools.terminal import (
    CdTool, LsTool, PwdTool, MkdirTool, RmTool,
    CpTool, MvTool, TouchTool, CatTool
)
from jdev_cli.tools.prometheus_tools import (
    PrometheusExecuteTool, PrometheusMemoryQueryTool, PrometheusSimulateTool,
    PrometheusEvolveTool, PrometheusReflectTool, PrometheusCreateToolTool,
    PrometheusGetStatusTool, PrometheusBenchmarkTool
)
from jdev_cli.core.providers.prometheus_provider import PrometheusProvider


def get_default_registry() -> ToolRegistry:
    """Create and populate default tool registry."""
    registry = ToolRegistry()

    # Initialize Prometheus provider
    try:
        prom_provider = PrometheusProvider()
        prom_tools = [
            PrometheusExecuteTool(prom_provider),
            PrometheusMemoryQueryTool(prom_provider),
            PrometheusSimulateTool(prom_provider),
            PrometheusEvolveTool(prom_provider),
            PrometheusReflectTool(prom_provider),
            PrometheusCreateToolTool(prom_provider),
            PrometheusGetStatusTool(prom_provider),
            PrometheusBenchmarkTool(prom_provider)
        ]
    except Exception:
        prom_tools = []

    tools = [
        ReadFileTool(), WriteFileTool(), EditFileTool(),
        ListDirectoryTool(), DeleteFileTool(),
        MoveFileTool(), CopyFileTool(), CreateDirectoryTool(),
        ReadMultipleFilesTool(), InsertLinesTool(),
        SearchFilesTool(), GetDirectoryTreeTool(),
        BashCommandTool(),
        GitStatusTool(), GitDiffTool(),
        GetContextTool(), SaveSessionTool(), RestoreBackupTool(),
        CdTool(), LsTool(), PwdTool(), MkdirTool(), RmTool(),
        CpTool(), MvTool(), TouchTool(), CatTool(),
    ] + prom_tools

    for tool in tools:
        registry.register(tool)

    return registry
