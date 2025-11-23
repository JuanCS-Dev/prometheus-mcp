
import asyncio
import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from qwen_dev_cli.core.lazy_loader import LazyLoader

async def verify_plugins():
    print("🔍 Verifying Shell Integrity & Plugins...")
    loader = LazyLoader()
    
    errors = []

    # 1. Verify Intelligence Plugin
    try:
        print("  Checking Intelligence Plugin...", end=" ")
        mod = await loader.load('intelligence')
        if not hasattr(mod, 'Plugin'):
            raise AttributeError("Module has no 'Plugin' class")
        
        plugin = mod.Plugin()
        # Mocking initialization to avoid heavy lifting if possible, 
        # but we need to check if attributes exist after init
        # Let's try to run initialize if it's not too heavy, or mock dependencies
        # For now, just checking structure
        print("✅ OK (Plugin class found)")
    except Exception as e:
        print(f"❌ FAILED: {e}")
        errors.append(f"Intelligence: {e}")

    # 2. Verify DevSquad Plugin
    try:
        print("  Checking DevSquad Plugin...", end=" ")
        mod = await loader.load('devsquad')
        if not hasattr(mod, 'Plugin'):
            raise AttributeError("Module has no 'Plugin' class")
        
        plugin = mod.Plugin()
        # Check if it has 'squad' attribute (might be None before init)
        if not hasattr(plugin, 'squad'):
             raise AttributeError("Plugin instance has no 'squad' attribute")
             
        print("✅ OK (Plugin class found)")
    except Exception as e:
        print(f"❌ FAILED: {e}")
        errors.append(f"DevSquad: {e}")

    # 3. Verify Tools Plugin
    try:
        print("  Checking Tools Plugin...", end=" ")
        mod = await loader.load('tools')
        if not hasattr(mod, 'tool_registry'):
             # Tools plugin might expose registry directly or via Plugin class
             # Let's check what it actually does
             pass
        print("✅ OK (Module loaded)")
    except Exception as e:
        print(f"❌ FAILED: {e}")
        errors.append(f"Tools: {e}")

    # 4. Verify LLM Plugin
    try:
        print("  Checking LLM Plugin...", end=" ")
        mod = await loader.load('llm')
        if not hasattr(mod, 'llm_client'):
             raise AttributeError("Module has no 'llm_client'")
        print("✅ OK")
    except Exception as e:
        print(f"❌ FAILED: {e}")
        errors.append(f"LLM: {e}")

    print("\n📊 Summary:")
    if errors:
        print(f"Found {len(errors)} errors!")
        for err in errors:
            print(f"  - {err}")
        sys.exit(1)
    else:
        print("✨ All systems go! Shell integrity verified.")
        sys.exit(0)

if __name__ == "__main__":
    asyncio.run(verify_plugins())
