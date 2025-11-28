#!/usr/bin/env python3
"""
🔥 PROMETHEUS MEGA STRESS TEST SUITE 🔥
Operação Terra Arrasada - Drain the Budget & Stress the Grid

Usa bl run para autenticação automática via Blaxel CLI.

Run: python tests/prometheus/stress_test.py
"""

import subprocess
import json
import time
import os
from datetime import datetime
from dataclasses import dataclass, field
from typing import List, Dict, Any
from concurrent.futures import ThreadPoolExecutor, as_completed

# ============================================================================
# CONFIGURAÇÕES
# ============================================================================

CONCURRENCY = 5  # Workers simultâneos (bl run é síncrono)
TOTAL_REQUESTS = 30  # Total de requests
TIMEOUT_PER_REQUEST = 180  # 3 minutos por request

# ============================================================================
# BATERIA DE TESTES - Projetada para ativar TODOS os subsistemas
# ============================================================================

TEST_SCENARIOS = [
    # =========================================================================
    # 🔧 CATEGORIA 1: Tool Factory & Sandbox (Código Pesado)
    # =========================================================================
    {
        "category": "Tool Factory",
        "name": "Mandelbrot Generator",
        "prompt": "Write a Python script to generate a Mandelbrot fractal using only stdlib. Output the first 10 characters of the result."
    },
    {
        "category": "Tool Factory",
        "name": "CSV Analyzer",
        "prompt": "Create a Python function to calculate mean and std deviation of a list of numbers. Test with [10, 20, 30, 40, 50]."
    },
    {
        "category": "Sandbox",
        "name": "Prime Sieve",
        "prompt": "Implement Sieve of Eratosthenes to find primes up to 100. How many primes are there?"
    },
    {
        "category": "Tool Factory",
        "name": "JSON Validator",
        "prompt": "Create a function to validate if a string is valid JSON. Test with '{\"name\": \"test\"}' and 'invalid{'."
    },
    {
        "category": "Sandbox",
        "name": "Binary Search",
        "prompt": "Implement binary search in Python. Search for 7 in [1,3,5,7,9,11]. Return the index."
    },

    # =========================================================================
    # 🌍 CATEGORIA 2: World Model & Reasoning (Simulação Complexa)
    # =========================================================================
    {
        "category": "World Model",
        "name": "Disaster Recovery",
        "prompt": "Plan a 3-step database recovery strategy for a crashed production server. Be concise."
    },
    {
        "category": "World Model",
        "name": "Security Analysis",
        "prompt": "What are the top 2 security risks for a REST API? Suggest mitigations in one sentence each."
    },
    {
        "category": "Reasoning",
        "name": "Algorithm Compare",
        "prompt": "Compare QuickSort vs MergeSort in 2 sentences. Which is better for large datasets?"
    },
    {
        "category": "World Model",
        "name": "Architecture Design",
        "prompt": "Design a simple microservice for user authentication. List 3 components needed."
    },
    {
        "category": "Reasoning",
        "name": "SQL vs NoSQL",
        "prompt": "When should you use NoSQL over SQL? Give 2 specific use cases."
    },

    # =========================================================================
    # 🧠 CATEGORIA 3: Memory & Reflection (Contexto e Auto-Análise)
    # =========================================================================
    {
        "category": "Memory",
        "name": "Quantum Basics",
        "prompt": "Explain quantum entanglement in 2 sentences for a programmer."
    },
    {
        "category": "Reflection",
        "name": "Self-Analysis",
        "prompt": "As PROMETHEUS, what is your main capability? Answer in one sentence."
    },
    {
        "category": "Memory",
        "name": "Store Fact",
        "prompt": "Remember: PROMETHEUS version is 1.0.0. Now tell me what version you are."
    },
    {
        "category": "Reflection",
        "name": "Code Review",
        "prompt": "Review this code: 'def fib(n): return fib(n-1)+fib(n-2) if n>1 else n'. What's the main issue?"
    },
    {
        "category": "Memory",
        "name": "Pattern Recognition",
        "prompt": "What pattern do you see in: 2, 4, 8, 16, 32? What comes next?"
    },

    # =========================================================================
    # ⚡ CATEGORIA 4: Evolution & Benchmarking (Auto-Melhoria)
    # =========================================================================
    {
        "category": "Evolution",
        "name": "Self-Challenge",
        "prompt": "Generate a simple coding challenge about string manipulation. Then solve it."
    },
    {
        "category": "Benchmark",
        "name": "Math Problem",
        "prompt": "Two trains are 300km apart. One goes 60km/h, other 90km/h toward each other. When do they meet?"
    },
    {
        "category": "Evolution",
        "name": "Tool Design",
        "prompt": "Design a simple calculator tool interface. What 4 functions would it have?"
    },
    {
        "category": "Benchmark",
        "name": "Logic Puzzle",
        "prompt": "I have 3 boxes labeled wrong. How many boxes do I need to open to fix all labels? Explain."
    },
    {
        "category": "Evolution",
        "name": "Learning Path",
        "prompt": "Create 3 progressively harder Python challenges for learning loops."
    },

    # =========================================================================
    # 🎯 CATEGORIA 5: Integration & Complex Workflows
    # =========================================================================
    {
        "category": "Integration",
        "name": "Data Pipeline",
        "prompt": "Convert this JSON to CSV format: {'name': 'Alice', 'age': 30}. Show the output."
    },
    {
        "category": "Integration",
        "name": "API Endpoint",
        "prompt": "Write a Python function that returns HTTP 200 with {'status': 'ok'} as JSON."
    },
    {
        "category": "Integration",
        "name": "Bug Fix",
        "prompt": "Fix this bug: 'def avg(nums): return sum(nums)/len(nums)' crashes on empty list. Show fixed code."
    },
    {
        "category": "Integration",
        "name": "Documentation",
        "prompt": "Write a one-line docstring for: 'def add(a, b): return a + b'"
    },
    {
        "category": "Integration",
        "name": "Refactoring",
        "prompt": "Refactor to list comprehension: 'result = []; for x in items: if x > 0: result.append(x)'"
    },
]


# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class TestResult:
    """Result of a single test."""
    id: int
    category: str
    name: str
    prompt: str
    status: str
    duration: float
    response: str = ""
    error: str = ""
    success: bool = False
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class TestReport:
    """Complete test report."""
    start_time: datetime
    end_time: datetime = None
    total_requests: int = 0
    successful: int = 0
    failed: int = 0
    total_duration: float = 0.0
    avg_duration: float = 0.0
    results: List[TestResult] = field(default_factory=list)
    by_category: Dict[str, Dict[str, Any]] = field(default_factory=dict)


# ============================================================================
# TEST RUNNER
# ============================================================================

def run_single_test(scenario: dict, req_id: int) -> TestResult:
    """Run a single test using bl CLI."""
    category = scenario.get("category", "Unknown")
    name = scenario.get("name", f"Test-{req_id}")
    prompt = scenario["prompt"]

    print(f"🚀 [REQ-{req_id:03d}] [{category}] {name[:25]}...")

    start = time.time()

    try:
        cmd = [
            "bl", "run", "agent", "prometheus",
            "--data", json.dumps({"inputs": prompt})
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=TIMEOUT_PER_REQUEST
        )

        duration = time.time() - start
        success = result.returncode == 0 and "PROMETHEUS" in result.stdout

        status_icon = "✅" if success else "❌"
        print(f"{status_icon} [REQ-{req_id:03d}] [{category}] {name[:20]} - {duration:.1f}s")

        return TestResult(
            id=req_id,
            category=category,
            name=name,
            prompt=prompt[:80] + "...",
            status="OK" if success else f"EXIT-{result.returncode}",
            duration=duration,
            response=result.stdout[:500] if result.stdout else "",
            error=result.stderr[:200] if result.stderr else "",
            success=success
        )

    except subprocess.TimeoutExpired:
        duration = time.time() - start
        print(f"⏰ [REQ-{req_id:03d}] [{category}] {name[:20]} - TIMEOUT {duration:.1f}s")
        return TestResult(
            id=req_id,
            category=category,
            name=name,
            prompt=prompt[:80] + "...",
            status="TIMEOUT",
            duration=duration,
            error=f"Timeout after {TIMEOUT_PER_REQUEST}s",
            success=False
        )

    except Exception as e:
        duration = time.time() - start
        print(f"🔥 [REQ-{req_id:03d}] [{category}] {name[:20]} - ERROR: {str(e)[:30]}")
        return TestResult(
            id=req_id,
            category=category,
            name=name,
            prompt=prompt[:80] + "...",
            status="EXCEPTION",
            duration=duration,
            error=str(e),
            success=False
        )


def run_stress_test() -> TestReport:
    """Run the complete stress test."""
    report = TestReport(start_time=datetime.now())

    print("\n" + "="*70)
    print("🔥 PROMETHEUS MEGA STRESS TEST - OPERAÇÃO TERRA ARRASADA 🔥")
    print("="*70)
    print(f"⚡ Concurrency: {CONCURRENCY} workers")
    print(f"📊 Total Requests: {TOTAL_REQUESTS}")
    print(f"🧪 Test Scenarios: {len(TEST_SCENARIOS)}")
    print(f"⏱️  Timeout per request: {TIMEOUT_PER_REQUEST}s")
    print("💰 Objective: DRAIN THE BUDGET & BUILD KNOWLEDGE")
    print("="*70 + "\n")

    results = []

    # Usar ThreadPoolExecutor para concorrência
    with ThreadPoolExecutor(max_workers=CONCURRENCY) as executor:
        futures = {}

        for i in range(TOTAL_REQUESTS):
            scenario = TEST_SCENARIOS[i % len(TEST_SCENARIOS)]
            future = executor.submit(run_single_test, scenario, i + 1)
            futures[future] = i + 1

        for future in as_completed(futures):
            result = future.result()
            results.append(result)

    # Processar resultados
    report.end_time = datetime.now()
    report.results = sorted(results, key=lambda x: x.id)
    report.total_requests = len(results)
    report.successful = sum(1 for r in results if r.success)
    report.failed = report.total_requests - report.successful
    report.total_duration = (report.end_time - report.start_time).total_seconds()

    if report.successful > 0:
        successful_durations = [r.duration for r in results if r.success]
        report.avg_duration = sum(successful_durations) / len(successful_durations)

    # Agrupar por categoria
    categories = {}
    for r in results:
        if r.category not in categories:
            categories[r.category] = {"total": 0, "success": 0, "failed": 0, "durations": []}
        categories[r.category]["total"] += 1
        if r.success:
            categories[r.category]["success"] += 1
            categories[r.category]["durations"].append(r.duration)
        else:
            categories[r.category]["failed"] += 1

    for cat, data in categories.items():
        if data["durations"]:
            data["avg_duration"] = sum(data["durations"]) / len(data["durations"])
        else:
            data["avg_duration"] = 0
        del data["durations"]

    report.by_category = categories

    return report


def generate_markdown_report(report: TestReport) -> str:
    """Generate markdown report."""
    success_rate = (report.successful / report.total_requests * 100) if report.total_requests > 0 else 0

    md = f"""# 🔥 PROMETHEUS Stress Test Report

> **Operação Terra Arrasada** - Mega Suite de Testes
>
> *Blaxel MCP Hackathon - Nov 2025*

## 📊 Executive Summary

| Metric | Value |
|--------|-------|
| **Start Time** | {report.start_time.strftime('%Y-%m-%d %H:%M:%S')} |
| **End Time** | {report.end_time.strftime('%Y-%m-%d %H:%M:%S')} |
| **Total Duration** | {report.total_duration:.1f}s ({report.total_duration/60:.1f} min) |
| **Total Requests** | {report.total_requests} |
| **Successful** | {report.successful} ✅ |
| **Failed** | {report.failed} ❌ |
| **Success Rate** | **{success_rate:.1f}%** |
| **Avg Response Time** | {report.avg_duration:.2f}s |

## 📈 Results by Category

| Category | Total | Success | Failed | Avg Time | Success Rate |
|----------|-------|---------|--------|----------|--------------|
"""

    for cat, data in sorted(report.by_category.items()):
        rate = (data["success"] / data["total"] * 100) if data["total"] > 0 else 0
        status = "✅" if rate >= 80 else "⚠️" if rate >= 50 else "❌"
        md += f"| {cat} | {data['total']} | {data['success']} | {data['failed']} | {data['avg_duration']:.1f}s | {status} **{rate:.0f}%** |\n"

    md += """
## 🧪 Test Scenarios

| # | Category | Test Name | Description |
|---|----------|-----------|-------------|
"""
    for i, scenario in enumerate(TEST_SCENARIOS, 1):
        md += f"| {i} | {scenario['category']} | {scenario['name']} | {scenario['prompt'][:50]}... |\n"

    md += """
## 📋 Detailed Results

| ID | Category | Test Name | Status | Duration | Output Preview |
|----|----------|-----------|--------|----------|----------------|
"""

    for r in report.results:
        status_icon = "✅" if r.success else "❌"
        output = r.response[:30].replace("\n", " ").replace("|", "/") if r.response else r.error[:30]
        md += f"| {r.id:03d} | {r.category} | {r.name[:20]} | {status_icon} {r.status} | {r.duration:.1f}s | {output}... |\n"

    # Sample outputs section
    md += """
## 📝 Sample Outputs

"""
    successful_results = [r for r in report.results if r.success][:5]
    for r in successful_results:
        md += f"""### {r.category}: {r.name}

**Prompt:** {r.prompt}

**Response Preview:**
```
{r.response[:300]}...
```

---

"""

    md += f"""
## 🎯 Configuration Used

```yaml
concurrency: {CONCURRENCY}
total_requests: {TOTAL_REQUESTS}
timeout_per_request: {TIMEOUT_PER_REQUEST}s
scenarios_count: {len(TEST_SCENARIOS)}
```

## 📊 Performance Analysis

- **Throughput**: {report.total_requests / report.total_duration * 60:.1f} requests/minute
- **Reliability**: {success_rate:.1f}% uptime
- **Latency (avg)**: {report.avg_duration:.2f}s

## 🏆 Conclusions

| Aspect | Status | Notes |
|--------|--------|-------|
| Performance | {'🟢 Excellent' if success_rate >= 90 else '🟡 Good' if success_rate >= 70 else '🟠 Fair' if success_rate >= 50 else '🔴 Needs Work'} | {success_rate:.0f}% success rate |
| Reliability | {'🟢' if report.failed < report.total_requests * 0.1 else '🟡' if report.failed < report.total_requests * 0.3 else '🔴'} | {report.failed} failures out of {report.total_requests} |
| Speed | {'🟢' if report.avg_duration < 30 else '🟡' if report.avg_duration < 60 else '🔴'} | Avg {report.avg_duration:.1f}s per request |

---

*Generated by PROMETHEUS Stress Test Suite*
*{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
*Blaxel MCP Hackathon - November 2025*
"""

    return md


def main():
    """Main entry point."""
    # Run stress test
    report = run_stress_test()

    # Print summary
    print("\n" + "="*70)
    print("📊 RELATÓRIO FINAL - OPERAÇÃO TERRA ARRASADA")
    print("="*70)
    print(f"⏱️  Duração Total: {report.total_duration:.1f}s ({report.total_duration/60:.1f} min)")
    print(f"📨 Total Requests: {report.total_requests}")
    print(f"✅ Sucesso: {report.successful}")
    print(f"❌ Falhas: {report.failed}")
    success_rate = (report.successful / report.total_requests * 100) if report.total_requests > 0 else 0
    print(f"📈 Taxa de Sucesso: {success_rate:.1f}%")
    print(f"⚡ Tempo Médio: {report.avg_duration:.2f}s")
    print("="*70)

    # Print by category
    print("\n📊 Por Categoria:")
    for cat, data in sorted(report.by_category.items()):
        rate = (data["success"] / data["total"] * 100) if data["total"] > 0 else 0
        status = "✅" if rate >= 80 else "⚠️" if rate >= 50 else "❌"
        print(f"   {status} {cat}: {data['success']}/{data['total']} ({rate:.0f}%) - avg {data['avg_duration']:.1f}s")

    # Generate and save markdown report
    md_report = generate_markdown_report(report)
    report_path = "tests/prometheus/STRESS_TEST_REPORT.md"
    os.makedirs(os.path.dirname(report_path), exist_ok=True)

    with open(report_path, "w") as f:
        f.write(md_report)

    print(f"\n📄 Relatório MD salvo em: {report_path}")

    # Also save JSON for analysis
    json_path = "tests/prometheus/stress_test_results.json"
    with open(json_path, "w") as f:
        json.dump({
            "summary": {
                "start_time": report.start_time.isoformat(),
                "end_time": report.end_time.isoformat(),
                "total_duration": report.total_duration,
                "total_requests": report.total_requests,
                "successful": report.successful,
                "failed": report.failed,
                "success_rate": success_rate,
                "avg_duration": report.avg_duration,
            },
            "by_category": report.by_category,
            "results": [
                {
                    "id": r.id,
                    "category": r.category,
                    "name": r.name,
                    "prompt": r.prompt,
                    "status": r.status,
                    "duration": r.duration,
                    "success": r.success,
                    "error": r.error,
                    "response_preview": r.response[:200] if r.response else "",
                }
                for r in report.results
            ]
        }, f, indent=2)

    print(f"📊 JSON salvo em: {json_path}")

    # Return exit code based on success rate
    if success_rate >= 70:
        print("\n🏆 STRESS TEST PASSED!")
        return 0
    elif success_rate >= 50:
        print("\n⚠️ STRESS TEST PARTIAL SUCCESS")
        return 0
    else:
        print("\n❌ STRESS TEST NEEDS ATTENTION")
        return 1


if __name__ == "__main__":
    exit(main())
