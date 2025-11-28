"""
Example: Custom Tool.

Shows how to create a custom tool using the SDK.
"""

import asyncio
import sys
from pathlib import Path

# Add src to path for development
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from juan_dev_sdk import create_tool, ToolBuilder
from juan_dev_sdk.tools import ToolCategory


# Simple function-based tool
def word_count(text: str) -> dict:
    """Count words in text."""
    words = text.split()
    return {
        "word_count": len(words),
        "char_count": len(text),
        "words": words[:10]  # First 10 words
    }


# Create tool using shorthand
simple_tool = create_tool(
    name="word_count",
    description="Count words in text",
    execute_fn=word_count
)


# Create tool using builder (more options)
advanced_tool = (ToolBuilder("text_analyzer")
    .description("Analyze text for various metrics")
    .category(ToolCategory.CUSTOM)
    .param("text", "string", "Text to analyze", required=True)
    .param("include_stats", "boolean", "Include detailed stats", default=False)
    .on_execute(lambda text, include_stats=False: {
        "length": len(text),
        "words": len(text.split()),
        "lines": text.count('\n') + 1,
        "stats": {
            "avg_word_length": sum(len(w) for w in text.split()) / max(len(text.split()), 1)
        } if include_stats else None
    })
    .build())


async def main():
    print("=== Custom Tool Example ===\n")

    # Test simple tool
    print("1. Simple word_count tool:")
    result = await simple_tool.execute(text="Hello world from Juan Dev SDK!")
    print(f"   Result: {result.data}\n")

    # Test advanced tool
    print("2. Advanced text_analyzer tool:")
    result = await advanced_tool.execute(
        text="This is a test.\nWith multiple lines.\nAnd some content.",
        include_stats=True
    )
    print(f"   Result: {result.data}\n")

    # Show schema
    print("3. Tool schema (for LLM function calling):")
    schema = advanced_tool.get_schema()
    print(f"   {schema}\n")


if __name__ == "__main__":
    asyncio.run(main())
