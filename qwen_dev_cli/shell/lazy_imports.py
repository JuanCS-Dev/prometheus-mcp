"""
shell/lazy_imports.py: Lazy Import Utilities for Performance.

Provides lazy loading of heavy modules to reduce startup time.
Based on profiling that identified shell_main taking 1000ms+ to import.

Heavy modules identified:
- prompt_toolkit.application (38ms)
- rich.markdown (32ms)
- prompt_toolkit.buffer (24ms)
- tui.input_enhanced (11ms)

Usage:
    from qwen_dev_cli.shell.lazy_imports import lazy_import

    # Instead of: from rich.markdown import Markdown
    Markdown = lazy_import('rich.markdown', 'Markdown')
"""

from __future__ import annotations

import importlib
import sys
from typing import Any, Optional, TYPE_CHECKING


class LazyModule:
    """
    Lazy module loader that defers import until first attribute access.

    This significantly reduces startup time by not loading heavy modules
    until they are actually needed.
    """

    def __init__(self, module_name: str):
        self._module_name = module_name
        self._module: Optional[Any] = None

    def _load(self) -> Any:
        if self._module is None:
            self._module = importlib.import_module(self._module_name)
        return self._module

    def __getattr__(self, name: str) -> Any:
        return getattr(self._load(), name)

    def __repr__(self) -> str:
        if self._module is None:
            return f"<LazyModule '{self._module_name}' (not loaded)>"
        return f"<LazyModule '{self._module_name}' (loaded)>"


class LazyClass:
    """
    Lazy class loader that defers import until instantiation or attribute access.
    """

    def __init__(self, module_name: str, class_name: str):
        self._module_name = module_name
        self._class_name = class_name
        self._class: Optional[type] = None

    def _load(self) -> type:
        if self._class is None:
            module = importlib.import_module(self._module_name)
            self._class = getattr(module, self._class_name)
        return self._class

    def __call__(self, *args, **kwargs) -> Any:
        """Instantiate the class."""
        return self._load()(*args, **kwargs)

    def __getattr__(self, name: str) -> Any:
        """Access class attributes."""
        return getattr(self._load(), name)

    def __repr__(self) -> str:
        if self._class is None:
            return f"<LazyClass '{self._module_name}.{self._class_name}' (not loaded)>"
        return f"<LazyClass '{self._module_name}.{self._class_name}' (loaded)>"


def lazy_import(module_name: str, class_name: Optional[str] = None) -> Any:
    """
    Create a lazy import for a module or class.

    Args:
        module_name: Full module path (e.g., 'rich.markdown')
        class_name: Optional class name to import from module

    Returns:
        LazyModule or LazyClass that loads on first access

    Example:
        # Lazy module
        rich_md = lazy_import('rich.markdown')
        md = rich_md.Markdown("# Hello")  # Loads here

        # Lazy class
        Markdown = lazy_import('rich.markdown', 'Markdown')
        md = Markdown("# Hello")  # Loads here
    """
    if class_name:
        return LazyClass(module_name, class_name)
    return LazyModule(module_name)


def lazy_import_all(imports: dict[str, tuple[str, str]]) -> dict[str, Any]:
    """
    Create multiple lazy imports at once.

    Args:
        imports: Dict mapping local name to (module, class_name) tuple

    Returns:
        Dict of lazy imports

    Example:
        lazy = lazy_import_all({
            'Markdown': ('rich.markdown', 'Markdown'),
            'Panel': ('rich.panel', 'Panel'),
        })
        md = lazy['Markdown']("# Hello")
    """
    return {
        name: lazy_import(module, cls)
        for name, (module, cls) in imports.items()
    }


# Pre-defined lazy imports for common heavy modules
LAZY_RICH = {
    'Markdown': lazy_import('rich.markdown', 'Markdown'),
    'Panel': lazy_import('rich.panel', 'Panel'),
    'Syntax': lazy_import('rich.syntax', 'Syntax'),
    'Table': lazy_import('rich.table', 'Table'),
}

LAZY_PROMPT_TOOLKIT = {
    'PromptSession': lazy_import('prompt_toolkit', 'PromptSession'),
    'FileHistory': lazy_import('prompt_toolkit.history', 'FileHistory'),
    'AutoSuggestFromHistory': lazy_import('prompt_toolkit.auto_suggest', 'AutoSuggestFromHistory'),
}
