#!/usr/bin/env python3
"""
Quick E2E Test for PROMETHEUS on Blaxel.

Run: python tests/prometheus/test_e2e_quick.py
"""

import subprocess
import json
import sys
import time
from datetime import datetime


def run_prometheus(prompt: str, timeout: int = 120) -> dict:
    """Run PROMETHEUS via Blaxel CLI."""
    cmd = [
        "bl", "run", "agent", "prometheus",
        "--data", json.dumps({"inputs": prompt})
    ]

    start = time.time()
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        duration = time.time() - start

        return {
            "success": result.returncode == 0,
            "output": result.stdout,
            "error": result.stderr,
            "duration": duration
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "output": "",
            "error": f"Timeout after {timeout}s",
            "duration": timeout
        }
    except Exception as e:
        return {
            "success": False,
            "output": "",
            "error": str(e),
            "duration": time.time() - start
        }


def test_basic_math():
    """Test basic math calculation."""
    print("🧪 Test 1: Basic Math...")
    result = run_prometheus("What is 15 * 7? Just give the number.")

    success = result["success"] and "105" in result["output"]
    print(f"   {'✅' if success else '❌'} Math test: {'PASS' if success else 'FAIL'}")
    print(f"   Duration: {result['duration']:.1f}s")
    return success


def test_code_generation():
    """Test code generation."""
    print("🧪 Test 2: Code Generation...")
    result = run_prometheus("Write a one-line Python function to square a number.", timeout=180)

    success = result["success"] and ("def " in result["output"] or "lambda" in result["output"])
    print(f"   {'✅' if success else '❌'} Code gen test: {'PASS' if success else 'FAIL'}")
    print(f"   Duration: {result['duration']:.1f}s")
    return success


def test_memory_retrieval():
    """Test that memory system works."""
    print("🧪 Test 3: Memory System...")
    result = run_prometheus("Remember this: The secret code is PROMETHEUS42. Now tell me the code.")

    # Check if memory-related output is present
    success = result["success"] and "memory" in result["output"].lower()
    print(f"   {'✅' if success else '❌'} Memory test: {'PASS' if success else 'FAIL'}")
    print(f"   Duration: {result['duration']:.1f}s")
    return success


def test_reflection():
    """Test reflection engine."""
    print("🧪 Test 4: Reflection Engine...")
    result = run_prometheus("Explain what 2+2 equals and why.")

    # Check if reflection output is present
    success = result["success"] and "Reflecting" in result["output"]
    print(f"   {'✅' if success else '❌'} Reflection test: {'PASS' if success else 'FAIL'}")
    print(f"   Duration: {result['duration']:.1f}s")
    return success


def main():
    print("\n" + "="*60)
    print("🔥 PROMETHEUS E2E Quick Test Suite")
    print("="*60 + "\n")

    start_time = datetime.now()

    tests = [
        ("Basic Math", test_basic_math),
        ("Code Generation", test_code_generation),
        ("Memory System", test_memory_retrieval),
        ("Reflection Engine", test_reflection),
    ]

    results = []
    for name, test_func in tests:
        try:
            passed = test_func()
            results.append((name, passed))
        except Exception as e:
            print(f"   ❌ {name} EXCEPTION: {e}")
            results.append((name, False))
        print()

    # Summary
    total_time = (datetime.now() - start_time).total_seconds()
    passed = sum(1 for _, p in results if p)
    total = len(results)

    print("="*60)
    print(f"📊 Results: {passed}/{total} tests passed ({passed/total*100:.0f}%)")
    print(f"⏱️  Total time: {total_time:.1f}s")
    print("="*60)

    # Return exit code
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
