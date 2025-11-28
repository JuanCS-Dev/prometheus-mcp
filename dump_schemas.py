import json
import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

from jdev_tui.core.tools_bridge import ToolBridge

def dump_schemas():
    print("🚀 Initializing ToolBridge...")
    bridge = ToolBridge()
    schemas = bridge.get_schemas_for_llm()

    print(f"📦 Found {len(schemas)} schemas.")

    with open("schemas_dump.json", "w") as f:
        json.dump(schemas, f, indent=2)

    print("✅ Schemas dumped to schemas_dump.json")

if __name__ == "__main__":
    dump_schemas()
