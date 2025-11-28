"""Example of using the enhanced response parser in production.

Demonstrates:
- Multiple parsing strategies
- Retry with secondary LLM pass
- Security sanitization
- Statistics tracking
"""

import asyncio
from jdev_cli.core.parser import ResponseParser
from jdev_cli.core.llm import LLMClient


async def main():
    """Demonstrate parser usage."""

    # Create LLM client
    llm_client = LLMClient()

    # Create parser with retry enabled
    parser = ResponseParser(
        strict_mode=False,       # Enable fallback strategies
        enable_retry=True,       # Enable secondary LLM pass
        max_retries=2,          # Max 2 retry attempts
        enable_logging=True,     # Log responses for debugging
        sanitize_args=True      # Enable security sanitization
    )

    # Define retry callback for secondary LLM pass (sync version for demo)
    def retry_callback(invalid_response: str, error: str) -> str:
        """Ask LLM to fix invalid response (mock for demo)."""
        print(f"\n🔄 Retry triggered for: {error}")
        print(f"   Original: {invalid_response[:50]}...")

        # Mock fix: just return valid JSON
        # In production, this would call LLM asynchronously
        fixed = '[{"tool": "read_file", "args": {"path": "fixed.py"}}]'
        print(f"   Fixed: {fixed}")
        return fixed

    # Set retry callback
    parser.set_retry_callback(retry_callback)

    print("=" * 80)
    print("🔥 QWEN-DEV-CLI PARSER DEMONSTRATION")
    print("=" * 80)

    # Example 1: Perfect JSON (Strict JSON strategy)
    print("\n📊 Example 1: Perfect JSON")
    print("-" * 80)

    response1 = '[{"tool": "read_file", "args": {"path": "main.py"}}]'
    result1 = parser.parse(response1)

    print(f"Response: {response1}")
    print(f"Strategy: {result1.strategy.value}")
    print(f"Success: {result1.success}")
    print(f"Tool Calls: {len(result1.tool_calls)}")
    for i, call in enumerate(result1.tool_calls):
        print(f"  {i+1}. {call['tool']} with args {call['args']}")

    # Example 2: JSON in Markdown (Markdown JSON strategy)
    print("\n📊 Example 2: JSON in Markdown Code Block")
    print("-" * 80)

    response2 = """
Let me help you with that!

```json
[
    {"tool": "ls", "args": {"flags": "-la"}},
    {"tool": "pwd", "args": {}}
]
```

These commands will list files and show current directory.
"""

    result2 = parser.parse(response2)

    print(f"Response: {response2[:100]}...")
    print(f"Strategy: {result2.strategy.value}")
    print(f"Success: {result2.success}")
    print(f"Tool Calls: {len(result2.tool_calls)}")
    for i, call in enumerate(result2.tool_calls):
        print(f"  {i+1}. {call['tool']} with args {call['args']}")

    # Example 3: Malformed JSON (Regex extraction)
    print("\n📊 Example 3: Malformed JSON (Single Quotes)")
    print("-" * 80)

    response3 = "{'tool': 'read_file', 'args': {'path': 'test.py'}}"
    result3 = parser.parse(response3)

    print(f"Response: {response3}")
    print(f"Strategy: {result3.strategy.value}")
    print(f"Success: {result3.success}")
    print(f"Tool Calls: {len(result3.tool_calls)}")

    # Example 4: Plain text (Plain text fallback)
    print("\n📊 Example 4: Plain Text Response")
    print("-" * 80)

    response4 = "I understand. Let me analyze the codebase first before making changes."
    result4 = parser.parse(response4)

    print(f"Response: {response4}")
    print(f"Strategy: {result4.strategy.value}")
    print(f"Success: {result4.success}")
    print(f"Is Text: {result4.is_text_response()}")
    print(f"Text: {result4.text_response}")

    # Example 5: Security sanitization (Blocked)
    print("\n📊 Example 5: Security Sanitization")
    print("-" * 80)

    response5 = '[{"tool": "read_file", "args": {"path": "../../etc/passwd"}}]'
    result5 = parser.parse(response5)

    print(f"Response: {response5}")
    print(f"Strategy: {result5.strategy.value}")
    print(f"Success: {result5.success}")
    print(f"Tool Calls: {len(result5.tool_calls)} (should be 0, blocked by security)")
    print(f"Security Blocks: {parser.stats['security_blocks']}")

    # Example 6: Command injection (Blocked)
    print("\n📊 Example 6: Command Injection Prevention")
    print("-" * 80)

    response6 = '[{"tool": "bash_command", "args": {"command": "ls; rm -rf /"}}]'
    result6 = parser.parse(response6)

    print(f"Response: {response6}")
    print(f"Strategy: {result6.strategy.value}")
    print(f"Success: {result6.success}")
    print(f"Tool Calls: {len(result6.tool_calls)} (should be 0, blocked)")
    print(f"Security Blocks: {parser.stats['security_blocks']}")

    # Example 7: Tool call validation
    print("\n📊 Example 7: Tool Call Validation")
    print("-" * 80)

    tool_schemas = [
        {
            "name": "read_file",
            "parameters": {
                "required": ["path"],
                "properties": {
                    "path": {"type": "string"},
                    "encoding": {"type": "string"}
                }
            }
        }
    ]

    response7 = '[{"tool": "read_file", "args": {"path": "main.py"}}]'
    result7 = parser.parse(response7)

    print(f"Response: {response7}")

    for tool_call in result7.tool_calls:
        is_valid, error = parser.validate_tool_call(tool_call, tool_schemas)
        print(f"Tool: {tool_call['tool']}")
        print(f"Valid: {is_valid}")
        if error:
            print(f"Error: {error}")

    # Statistics
    print("\n📊 Parsing Statistics")
    print("=" * 80)

    stats = parser.get_statistics()

    print(f"Total Parses: {stats['total']}")
    print(f"Strict JSON: {stats['strict_json']}")
    print(f"Markdown JSON: {stats['markdown_json']}")
    print(f"Regex Extraction: {stats['regex_extraction']}")
    print(f"Partial JSON: {stats['partial_json']}")
    print(f"Plain Text: {stats['plain_text']}")
    print(f"Failures: {stats['failures']}")
    print(f"Retries: {stats['retries']}")
    print(f"Security Blocks: {stats['security_blocks']}")

    if stats['total'] > 0:
        success_rate = (stats['total'] - stats['failures']) / stats['total'] * 100
        print(f"\nSuccess Rate: {success_rate:.1f}%")

    print("\n✅ Demonstration complete!")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
