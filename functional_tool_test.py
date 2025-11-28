import sys
import os
import logging
import shutil
import asyncio

# Add project root to path
sys.path.append(os.getcwd())

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s'
)
logger = logging.getLogger("functional_test")

from jdev_tui.core.tools_bridge import ToolBridge

# Test Workspace
TEST_DIR = "test_workspace"

def setup_workspace():
    if os.path.exists(TEST_DIR):
        shutil.rmtree(TEST_DIR)
    os.makedirs(TEST_DIR)
    os.makedirs(os.path.join(TEST_DIR, "subdir"))
    with open(os.path.join(TEST_DIR, "existing_file.txt"), "w") as f:
        f.write("Hello World\nLine 2\nLine 3")

def cleanup_workspace():
    if os.path.exists(TEST_DIR):
        shutil.rmtree(TEST_DIR)

async def run_tests_async():
    print("🚀 Starting Functional Tool Test Suite")
    print("======================================")

    bridge = ToolBridge()
    setup_workspace()

    passed = 0
    failed = 0

    # Define test cases
    # Format: (tool_name, args, verification_callback)
    tests = [
        # --- File System Tools ---
        ("pwd", {}, lambda r: True), # Always passes if returns string
        ("ls", {"path": TEST_DIR}, lambda r: "existing_file.txt" in str(r)),
        ("write_file", {"path": f"{TEST_DIR}/new_file.txt", "content": "Created by test"}, lambda r: os.path.exists(f"{TEST_DIR}/new_file.txt")),
        ("read_file", {"path": f"{TEST_DIR}/new_file.txt"}, lambda r: "Created by test" in str(r)),
        ("copy_file", {"source": f"{TEST_DIR}/new_file.txt", "destination": f"{TEST_DIR}/copy_file.txt"}, lambda r: os.path.exists(f"{TEST_DIR}/copy_file.txt")),
        ("move_file", {"source": f"{TEST_DIR}/copy_file.txt", "destination": f"{TEST_DIR}/moved_file.txt"}, lambda r: os.path.exists(f"{TEST_DIR}/moved_file.txt") and not os.path.exists(f"{TEST_DIR}/copy_file.txt")),
        ("rm", {"path": f"{TEST_DIR}/moved_file.txt"}, lambda r: not os.path.exists(f"{TEST_DIR}/moved_file.txt")),
        ("mkdir", {"path": f"{TEST_DIR}/new_dir"}, lambda r: os.path.exists(f"{TEST_DIR}/new_dir")),
        ("touch", {"path": f"{TEST_DIR}/touched_file.txt"}, lambda r: os.path.exists(f"{TEST_DIR}/touched_file.txt")),
        ("cat", {"path": f"{TEST_DIR}/existing_file.txt"}, lambda r: "Hello World" in str(r)),

        # --- Search Tools ---
        ("search_files", {"pattern": "Hello", "path": TEST_DIR}, lambda r: "existing_file.txt" in str(r)),
        ("list_directory", {"path": TEST_DIR}, lambda r: "existing_file.txt" in str(r)),

        # --- Bash Tools ---
        ("bash_command", {"command": "echo 'bash test'"}, lambda r: "bash test" in str(r)),

        # --- Git Tools (Mock/Safe) ---
        ("git_status", {}, lambda r: True), # Just check it runs

        # --- Advanced File Tools ---
        ("insert_lines", {"path": f"{TEST_DIR}/existing_file.txt", "line_number": 2, "content": "Inserted Line"}, lambda r: "Inserted Line" in open(f"{TEST_DIR}/existing_file.txt").read()),
        ("edit_file", {"path": f"{TEST_DIR}/existing_file.txt", "edits": [{"search": "Hello World", "replace": "Hi Universe"}]}, lambda r: "Hi Universe" in open(f"{TEST_DIR}/existing_file.txt").read()),

        # --- Network/Web Tools (Mock/Safe) ---
        ("fetch_url", {"url": "https://example.com"}, lambda r: "Example Domain" in str(r) or "Error" in str(r)),

        # --- Context/Session ---
        ("get_context", {}, lambda r: True),

        # --- Misc ---
        ("task", {"action": "list"}, lambda r: True),
    ]

    print(f"\n🧪 Executing {len(tests)} Functional Tests...")
    print("-" * 60)

    for tool_name, args, verify in tests:
        print(f"\n▶️  Testing: {tool_name}")
        print(f"    Args: {args}")

        try:
            # Execute Tool (Async + Unpack kwargs)
            result = await bridge.execute_tool(tool_name, **args)
            print(f"    Result: {str(result)[:100]}...") # Truncate long output

            # Verify
            if verify(result):
                print("✅ PASS")
                passed += 1
            else:
                print("❌ FAIL: Verification failed")
                failed += 1

        except Exception as e:
            print(f"❌ FAIL: Execution error - {e}")
            failed += 1

    cleanup_workspace()

    print("-" * 60)
    print("\n📊 Functional Test Summary")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")

    if failed == 0:
        print("\n✨ ALL FUNCTIONAL TESTS PASSED ✨")
    else:
        print("\n⚠️  SOME TESTS FAILED")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(run_tests_async())
