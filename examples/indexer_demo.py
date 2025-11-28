#!/usr/bin/env python3
"""
Semantic Indexer Demo - Cursor-style intelligence showcase.

Run: python3 examples/indexer_demo.py
"""

import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from jdev_cli.intelligence.indexer import SemanticIndexer
from jdev_cli.tui.theme import COLORS
import time


def print_header(text: str):
    """Print styled header."""
    width = 70
    print(f"\n{COLORS['primary']}{'═' * width}{COLORS['reset']}")
    print(f"{COLORS['primary']}  {text}{COLORS['reset']}")
    print(f"{COLORS['primary']}{'═' * width}{COLORS['reset']}\n")


def print_symbol(symbol, highlight: bool = False):
    """Print symbol info."""
    color = COLORS['success'] if highlight else COLORS['text']
    type_color = COLORS['warning']

    print(f"{color}  {symbol.name}{COLORS['reset']} "
          f"{type_color}[{symbol.type}]{COLORS['reset']} "
          f"{COLORS['dim']}at {symbol.file_path}:{symbol.line_number}{COLORS['reset']}")

    if symbol.signature:
        print(f"    {COLORS['dim']}{symbol.signature}{COLORS['reset']}")

    if symbol.docstring:
        doc_preview = symbol.docstring.split('\n')[0][:60]
        print(f"    {COLORS['dim']}→ {doc_preview}...{COLORS['reset']}")


def main():
    """Run indexer demo."""
    root = Path.cwd()

    print_header("🔍 SEMANTIC INDEXER - Cursor-style Intelligence")

    print(f"{COLORS['dim']}Root: {root}{COLORS['reset']}\n")

    # Initialize indexer
    print(f"{COLORS['info']}⚡ Initializing indexer...{COLORS['reset']}")
    indexer = SemanticIndexer(str(root))

    # Try loading cache
    if indexer.load_cache():
        print(f"{COLORS['success']}✓ Loaded from cache{COLORS['reset']}")
    else:
        print(f"{COLORS['warning']}! No cache found, indexing...{COLORS['reset']}")
        start = time.time()
        count = indexer.index_codebase()
        elapsed = time.time() - start
        print(f"{COLORS['success']}✓ Indexed {count} files in {elapsed:.2f}s{COLORS['reset']}")

    # Show stats
    stats = indexer.get_stats()

    print_header("📊 Index Statistics")
    print(f"  Files indexed: {COLORS['success']}{stats['files_indexed']}{COLORS['reset']}")
    print(f"  Total symbols: {COLORS['success']}{stats['total_symbols']}{COLORS['reset']}")
    print(f"  Unique names:  {COLORS['success']}{stats['unique_symbols']}{COLORS['reset']}")

    print("\n  Symbol breakdown:")
    for sym_type, count in stats['symbol_types'].items():
        print(f"    {COLORS['dim']}{sym_type:12s}{COLORS['reset']} {COLORS['info']}{count:4d}{COLORS['reset']}")

    # Demo 1: Symbol search
    print_header("🔍 Demo 1: Symbol Search")

    queries = ["Tool", "execute", "Shell"]

    for query in queries:
        print(f"\n{COLORS['info']}Searching for: \"{query}\"{COLORS['reset']}")
        results = indexer.search_symbols(query, limit=3)

        if results:
            for symbol in results:
                print_symbol(symbol, highlight=True)
        else:
            print(f"  {COLORS['dim']}No results{COLORS['reset']}")

    # Demo 2: Error tracing
    print_header("🐛 Demo 2: Error → Source Mapping (Cursor Magic)")

    # Simulate error trace
    fake_error = f"""
Traceback (most recent call last):
  File "{root}/jdev_cli/shell.py", line 150, in process_command
    result = await self.execute_tool(cmd)
  File "{root}/jdev_cli/tools/exec.py", line 45, in execute
    raise ValueError("Invalid command")
ValueError: Invalid command
"""

    print(f"{COLORS['dim']}{fake_error}{COLORS['reset']}")

    location = indexer.find_definition(fake_error)

    if location:
        file_path, line_num = location
        print(f"\n{COLORS['success']}✓ Found error source:{COLORS['reset']}")
        print(f"  {COLORS['info']}{file_path}:{line_num}{COLORS['reset']}")

        # Show context
        print(f"\n{COLORS['dim']}Context:{COLORS['reset']}")
        context = indexer.get_file_context(file_path, line_num, context_lines=5)
        if context:
            print(context)

    # Demo 3: Dependency analysis
    print_header("🔗 Demo 3: Dependency Graph")

    test_file = "jdev_cli/shell.py"
    if test_file in indexer.file_index:
        print(f"{COLORS['info']}Analyzing: {test_file}{COLORS['reset']}\n")

        deps = indexer.get_dependencies(test_file)

        if deps:
            print(f"  {COLORS['success']}Found {len(deps)} dependencies:{COLORS['reset']}")
            for dep in sorted(deps)[:5]:
                print(f"    {COLORS['dim']}→ {dep}{COLORS['reset']}")

            if len(deps) > 5:
                print(f"    {COLORS['dim']}... and {len(deps) - 5} more{COLORS['reset']}")
        else:
            print(f"  {COLORS['dim']}No dependencies found{COLORS['reset']}")

    # Summary
    print_header("✨ Demo Complete")
    print(f"{COLORS['success']}The indexer provides:{COLORS['reset']}")
    print(f"  {COLORS['dim']}•{COLORS['reset']} Instant symbol lookup")
    print(f"  {COLORS['dim']}•{COLORS['reset']} Error → Source mapping")
    print(f"  {COLORS['dim']}•{COLORS['reset']} Dependency analysis")
    print(f"  {COLORS['dim']}•{COLORS['reset']} Smart context collection")
    print()


if __name__ == "__main__":
    main()
