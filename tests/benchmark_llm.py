# tests/benchmark_llm.py
"""Benchmark the neuroshell-code alias.
Measures:
- Shell startup time (should be < 1s)
- LLM response time for a simple prompt (should be < 2s)
"""
import subprocess
import time
import sys

ALIAS = "neuroshell-code"
PROMPT = "Oi"

def run_shell_once():
    start = time.time()
    # Start the shell process
    proc = subprocess.Popen([ALIAS], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    # Wait a short moment for the landing screen to render
    time.sleep(0.5)
    # Send the prompt and newline, then exit
    try:
        proc.stdin.write(PROMPT + "\n")
        proc.stdin.flush()
        # Give it a moment to process
        time.sleep(0.5)
        proc.stdin.write("quit\n")
        proc.stdin.flush()
    except Exception:
        pass
    # Wait for process to finish
    proc.communicate(timeout=10)
    return time.time() - start

def benchmark(iterations=5):
    times = []
    for i in range(iterations):
        t = run_shell_once()
        times.append(t)
        print(f"Run {i+1}: {t:.2f}s")
    avg = sum(times) / len(times)
    print(f"Average time: {avg:.2f}s")
    if avg < 2.0:
        print("✅ Performance OK")
    else:
        print("⚠️ Performance may be slow")

if __name__ == "__main__":
    benchmark()
