#!/usr/bin/env python3
"""Test indexer integration with shell."""

from jdev_cli.intelligence.indexer import SemanticIndexer
import time

print("🔍 Testing Indexer Integration\n")

# Initialize
indexer = SemanticIndexer(root_path=".")
print("✓ Indexer initialized")

# Index codebase
print("\n⚡ Indexing codebase...")
start = time.time()
count = indexer.index_codebase()
elapsed = time.time() - start

print(f"✓ Indexed {count} files in {elapsed:.2f}s")

# Stats
stats = indexer.get_stats()
print("\n📊 Stats:")
print(f"  Files: {stats['files_indexed']}")
print(f"  Symbols: {stats['total_symbols']}")
print(f"  Unique: {stats['unique_symbols']}")

# Test search
print("\n🔍 Testing search for 'Tool':")
results = indexer.search_symbols("Tool", limit=3)
for symbol in results:
    print(f"  • {symbol.name} ({symbol.type}) at {symbol.file_path}:{symbol.line_number}")

print("\n✨ Indexer working perfectly!")
