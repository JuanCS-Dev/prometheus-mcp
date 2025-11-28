"""
🔥 TESTE DE PERFORMANCE & CAOS - JusticaIntegratedAgent
=======================================================

Testes de performance sob carga EXTREMA e situações caóticas.

Objetivo: Encontrar limites, gargalos e pontos de falha sob stress máximo.

Categorias:
    1. Load Testing: Alta carga sustentada
    2. Stress Testing: Sobrecarga até falha
    3. Spike Testing: Picos súbitos de carga
    4. Endurance Testing: Longa duração
    5. Scalability Testing: Crescimento de carga
    6. Chaos Engineering: Falhas aleatórias

Author: Claude Code (Sonnet 4.5)
Philosophy: "Quebre em teste, não em produção."
"""

import asyncio
import gc
import os
import psutil
import random
import sys
import time
from dataclasses import dataclass
from typing import List, Dict, Any

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from jdev_cli.agents.justica_agent import JusticaIntegratedAgent
from jdev_governance.justica import EnforcementMode


# ============================================================================
# FIXTURES & UTILITIES
# ============================================================================


@dataclass
class PerformanceMetrics:
    """Métricas de performance."""
    total_requests: int
    successful: int
    failed: int
    total_time: float
    avg_latency: float
    p50_latency: float
    p95_latency: float
    p99_latency: float
    throughput: float  # req/s
    memory_peak_mb: float
    memory_avg_mb: float
    cpu_peak_percent: float
    cpu_avg_percent: float


class MockLLMClient:
    """Mock LLM with configurable delay."""
    def __init__(self, delay_ms: float = 10.0, fail_rate: float = 0.0):
        self.delay_ms = delay_ms
        self.fail_rate = fail_rate
        self.call_count = 0

    async def generate(self, prompt: str, system_prompt: str = "", **kwargs) -> str:
        self.call_count += 1
        if random.random() < self.fail_rate:
            raise Exception("Simulated LLM failure")
        await asyncio.sleep(self.delay_ms / 1000.0)
        return "Mock response"


class MockMCPClient:
    """Mock MCP client."""
    def __init__(self):
        self.call_count = 0

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        self.call_count += 1
        return {"success": True}


def measure_performance(start_time: float, end_time: float, latencies: List[float],
                       memory_samples: List[float], cpu_samples: List[float],
                       successful: int, failed: int) -> PerformanceMetrics:
    """Calculate performance metrics."""
    total_time = end_time - start_time
    total_requests = successful + failed
    latencies_sorted = sorted(latencies)

    return PerformanceMetrics(
        total_requests=total_requests,
        successful=successful,
        failed=failed,
        total_time=total_time,
        avg_latency=sum(latencies) / len(latencies) if latencies else 0,
        p50_latency=latencies_sorted[len(latencies_sorted) // 2] if latencies else 0,
        p95_latency=latencies_sorted[int(len(latencies_sorted) * 0.95)] if latencies else 0,
        p99_latency=latencies_sorted[int(len(latencies_sorted) * 0.99)] if latencies else 0,
        throughput=total_requests / total_time if total_time > 0 else 0,
        memory_peak_mb=max(memory_samples) if memory_samples else 0,
        memory_avg_mb=sum(memory_samples) / len(memory_samples) if memory_samples else 0,
        cpu_peak_percent=max(cpu_samples) if cpu_samples else 0,
        cpu_avg_percent=sum(cpu_samples) / len(cpu_samples) if cpu_samples else 0,
    )


async def monitor_resources(interval: float = 0.1) -> tuple:
    """Monitor memory and CPU usage."""
    process = psutil.Process()
    memory_samples = []
    cpu_samples = []

    while True:
        try:
            mem_mb = process.memory_info().rss / 1024 / 1024
            cpu_percent = process.cpu_percent()
            memory_samples.append(mem_mb)
            cpu_samples.append(cpu_percent)
            await asyncio.sleep(interval)
        except asyncio.CancelledError:
            break

    return memory_samples, cpu_samples


# ============================================================================
# CATEGORIA 1: LOAD TESTING (Alta carga sustentada)
# ============================================================================


class TestLoadTesting:
    """Testes de carga sustentada."""

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_sustained_load_1000_requests(self):
        """TEST PERF 001: 1000 requests sequenciais."""
        llm = MockLLMClient(delay_ms=5.0)
        mcp = MockMCPClient()
        agent = JusticaIntegratedAgent(
            llm_client=llm,
            mcp_client=mcp,
            enforcement_mode=EnforcementMode.NORMATIVE,
        )

        # Start monitoring
        monitor_task = asyncio.create_task(monitor_resources())

        latencies = []
        successful = 0
        failed = 0

        start_time = time.time()

        for i in range(1000):
            req_start = time.time()
            try:
                await agent.evaluate_action(
                    agent_id=f"agent-{i % 100}",  # 100 unique agents
                    action_type="bash_exec",
                    content=f"ls {i}",
                )
                successful += 1
            except Exception:
                failed += 1

            latencies.append(time.time() - req_start)

        end_time = time.time()

        # Stop monitoring
        monitor_task.cancel()
        try:
            memory_samples, cpu_samples = await monitor_task
        except asyncio.CancelledError:
            memory_samples, cpu_samples = [], []

        metrics = measure_performance(start_time, end_time, latencies, memory_samples,
                                     cpu_samples, successful, failed)

        print("\n=== Sustained Load 1000 Requests ===")
        print(f"Throughput: {metrics.throughput:.2f} req/s")
        print(f"Avg Latency: {metrics.avg_latency*1000:.2f} ms")
        print(f"P95 Latency: {metrics.p95_latency*1000:.2f} ms")
        print(f"Success Rate: {metrics.successful}/{metrics.total_requests} ({metrics.successful/metrics.total_requests*100:.1f}%)")
        print(f"Memory Peak: {metrics.memory_peak_mb:.2f} MB")
        print(f"CPU Peak: {metrics.cpu_peak_percent:.1f}%")

        # Assertions
        assert metrics.successful > 990, f"Too many failures: {failed}"
        assert metrics.avg_latency < 0.1, f"Latency too high: {metrics.avg_latency*1000:.2f}ms"

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_concurrent_load_100_parallel(self):
        """TEST PERF 002: 100 requests em paralelo simultâneos."""
        llm = MockLLMClient(delay_ms=10.0)
        mcp = MockMCPClient()
        agent = JusticaIntegratedAgent(
            llm_client=llm,
            mcp_client=mcp,
        )

        async def single_request(idx: int):
            req_start = time.time()
            try:
                await agent.evaluate_action(
                    agent_id=f"agent-{idx}",
                    action_type="bash_exec",
                    content=f"ls {idx}",
                )
                return True, time.time() - req_start
            except Exception:
                return False, time.time() - req_start

        start_time = time.time()
        results = await asyncio.gather(*[single_request(i) for i in range(100)])
        end_time = time.time()

        successful = sum(1 for success, _ in results if success)
        latencies = [latency for _, latency in results]

        total_time = end_time - start_time
        throughput = 100 / total_time

        print("\n=== Concurrent Load 100 Parallel ===")
        print(f"Total Time: {total_time:.2f} s")
        print(f"Throughput: {throughput:.2f} req/s")
        print(f"Success Rate: {successful}/100")
        print(f"Avg Latency: {sum(latencies)/len(latencies)*1000:.2f} ms")

        assert successful >= 95, f"Too many failures: {100 - successful}"
        assert total_time < 2.0, f"Too slow: {total_time:.2f}s"


# ============================================================================
# CATEGORIA 2: STRESS TESTING (Sobrecarga até falha)
# ============================================================================


class TestStressTesting:
    """Testes de stress até o limite."""

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_stress_10000_requests(self):
        """TEST PERF 003: 10000 requests - encontrar limite."""
        llm = MockLLMClient(delay_ms=1.0)  # Fast LLM
        mcp = MockMCPClient()
        agent = JusticaIntegratedAgent(
            llm_client=llm,
            mcp_client=mcp,
        )

        successful = 0
        failed = 0
        latencies = []

        start_time = time.time()

        for i in range(10000):
            req_start = time.time()
            try:
                await agent.evaluate_action(
                    agent_id=f"agent-{i % 500}",  # 500 agents
                    action_type="bash_exec",
                    content="ls",
                )
                successful += 1
            except Exception:
                failed += 1

            latencies.append(time.time() - req_start)

            # Report progress
            if (i + 1) % 1000 == 0:
                elapsed = time.time() - start_time
                print(f"Progress: {i+1}/10000 ({elapsed:.1f}s, {(i+1)/elapsed:.1f} req/s)")

        end_time = time.time()
        total_time = end_time - start_time

        print("\n=== Stress 10000 Requests ===")
        print(f"Total Time: {total_time:.2f} s")
        print(f"Throughput: {10000/total_time:.2f} req/s")
        print(f"Success Rate: {successful}/10000 ({successful/100:.1f}%)")
        print(f"Failed: {failed}")

        assert successful > 9500, f"Too many failures: {failed}"

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_stress_1000_concurrent(self):
        """TEST PERF 004: 1000 requests simultâneos."""
        llm = MockLLMClient(delay_ms=50.0)
        mcp = MockMCPClient()
        agent = JusticaIntegratedAgent(
            llm_client=llm,
            mcp_client=mcp,
        )

        async def single_request(idx: int):
            try:
                await agent.evaluate_action(
                    agent_id=f"agent-{idx}",
                    action_type="bash_exec",
                    content=f"ls {idx}",
                )
                return True
            except Exception:
                return False

        start_time = time.time()
        results = await asyncio.gather(*[single_request(i) for i in range(1000)], return_exceptions=True)
        end_time = time.time()

        successful = sum(1 for r in results if r is True)
        failed = 1000 - successful

        print("\n=== Stress 1000 Concurrent ===")
        print(f"Total Time: {end_time - start_time:.2f} s")
        print(f"Success Rate: {successful}/1000")
        print(f"Failed: {failed}")

        assert successful > 900, f"Too many failures: {failed}"


# ============================================================================
# CATEGORIA 3: SPIKE TESTING (Picos súbitos)
# ============================================================================


class TestSpikeTesting:
    """Testes de picos súbitos de carga."""

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_spike_sudden_burst(self):
        """TEST PERF 005: Pico súbito de 500 requests."""
        llm = MockLLMClient(delay_ms=10.0)
        mcp = MockMCPClient()
        agent = JusticaIntegratedAgent(
            llm_client=llm,
            mcp_client=mcp,
        )

        # Warm-up: 10 requests
        for i in range(10):
            await agent.evaluate_action(
                agent_id="agent-warmup",
                action_type="bash_exec",
                content="ls",
            )

        # Sudden spike: 500 concurrent
        start_time = time.time()
        results = await asyncio.gather(*[
            agent.evaluate_action(
                agent_id=f"agent-{i}",
                action_type="bash_exec",
                content=f"ls {i}",
            )
            for i in range(500)
        ], return_exceptions=True)
        end_time = time.time()

        successful = sum(1 for r in results if not isinstance(r, Exception))

        print("\n=== Spike Sudden Burst ===")
        print(f"Spike Duration: {end_time - start_time:.2f} s")
        print(f"Success Rate: {successful}/500")

        assert successful > 450, f"Spike failed: {500 - successful} failures"


# ============================================================================
# CATEGORIA 4: ENDURANCE TESTING (Longa duração)
# ============================================================================


class TestEnduranceTesting:
    """Testes de longa duração."""

    @pytest.mark.asyncio
    @pytest.mark.slow
    @pytest.mark.timeout(600)  # 10 min timeout
    async def test_endurance_5_minutes(self):
        """TEST PERF 006: 5 minutos de carga contínua."""
        llm = MockLLMClient(delay_ms=5.0)
        mcp = MockMCPClient()
        agent = JusticaIntegratedAgent(
            llm_client=llm,
            mcp_client=mcp,
        )

        duration_seconds = 300  # 5 minutes
        start_time = time.time()
        successful = 0
        failed = 0
        memory_samples = []

        process = psutil.Process()

        while time.time() - start_time < duration_seconds:
            try:
                await agent.evaluate_action(
                    agent_id=f"agent-{successful % 100}",
                    action_type="bash_exec",
                    content="ls",
                )
                successful += 1
            except Exception:
                failed += 1

            # Sample memory every 100 requests
            if successful % 100 == 0:
                mem_mb = process.memory_info().rss / 1024 / 1024
                memory_samples.append(mem_mb)
                elapsed = time.time() - start_time
                print(f"Endurance: {elapsed:.0f}s, {successful} requests, {mem_mb:.1f}MB")

        end_time = time.time()
        total_time = end_time - start_time

        print("\n=== Endurance 5 Minutes ===")
        print(f"Duration: {total_time:.2f} s")
        print(f"Total Requests: {successful + failed}")
        print(f"Throughput: {(successful + failed)/total_time:.2f} req/s")
        print(f"Memory Growth: {memory_samples[-1] - memory_samples[0]:.2f} MB")

        # Check for memory leaks
        if len(memory_samples) > 10:
            memory_growth = memory_samples[-1] - memory_samples[0]
            assert memory_growth < 500, f"Memory leak detected: {memory_growth:.2f}MB growth"


# ============================================================================
# CATEGORIA 5: SCALABILITY TESTING
# ============================================================================


class TestScalabilityTesting:
    """Testes de escalabilidade."""

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_scalability_increasing_load(self):
        """TEST PERF 007: Carga crescente: 10 → 100 → 1000 agents."""
        llm = MockLLMClient(delay_ms=5.0)
        mcp = MockMCPClient()
        agent = JusticaIntegratedAgent(
            llm_client=llm,
            mcp_client=mcp,
        )

        results = {}

        for num_agents in [10, 100, 1000]:
            start_time = time.time()

            tasks = [
                agent.evaluate_action(
                    agent_id=f"agent-{i}",
                    action_type="bash_exec",
                    content="ls",
                )
                for i in range(num_agents)
            ]

            await asyncio.gather(*tasks, return_exceptions=True)

            end_time = time.time()
            total_time = end_time - start_time
            throughput = num_agents / total_time

            results[num_agents] = {
                "time": total_time,
                "throughput": throughput,
            }

            print(f"\n{num_agents} agents: {total_time:.2f}s, {throughput:.2f} req/s")

        # Check linear scalability (within 2x tolerance)
        ratio_10_to_100 = results[100]["time"] / results[10]["time"]
        ratio_100_to_1000 = results[1000]["time"] / results[100]["time"]

        print("\nScalability Ratios:")
        print(f"  10→100: {ratio_10_to_100:.2f}x")
        print(f"  100→1000: {ratio_100_to_1000:.2f}x")

        assert ratio_10_to_100 < 20, f"Non-linear scaling detected: {ratio_10_to_100:.2f}x"


# ============================================================================
# CATEGORIA 6: CHAOS ENGINEERING
# ============================================================================


class TestChaosEngineering:
    """Testes de engenharia do caos."""

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_chaos_random_llm_failures(self):
        """TEST PERF 008: LLM com 10% de falhas aleatórias."""
        llm = MockLLMClient(delay_ms=10.0, fail_rate=0.1)  # 10% failure rate
        mcp = MockMCPClient()
        agent = JusticaIntegratedAgent(
            llm_client=llm,
            mcp_client=mcp,
        )

        successful = 0
        failed = 0

        for i in range(1000):
            try:
                await agent.evaluate_action(
                    agent_id=f"agent-{i}",
                    action_type="bash_exec",
                    content="ls",
                )
                successful += 1
            except Exception:
                failed += 1

        print("\n=== Chaos Random LLM Failures ===")
        print(f"Success: {successful}/1000")
        print(f"Failed: {failed}/1000")

        # Should handle failures gracefully
        assert successful > 800, f"Too many failures: {failed}"

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_chaos_memory_pressure(self):
        """TEST PERF 009: Pressão de memória (contexts grandes)."""
        llm = MockLLMClient(delay_ms=5.0)
        mcp = MockMCPClient()
        agent = JusticaIntegratedAgent(
            llm_client=llm,
            mcp_client=mcp,
        )

        # Create huge contexts
        huge_context = {"data": "X" * 1024 * 1024}  # 1MB context

        successful = 0
        failed = 0

        for i in range(100):
            try:
                await agent.evaluate_action(
                    agent_id=f"agent-{i}",
                    action_type="bash_exec",
                    content="ls",
                    context=huge_context,
                )
                successful += 1
            except Exception:
                failed += 1

        print("\n=== Chaos Memory Pressure ===")
        print(f"Success: {successful}/100")

        assert successful > 90, f"Failed under memory pressure: {failed}"

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_chaos_rapid_agent_creation(self):
        """TEST PERF 010: Criação e destruição rápida de agents."""
        llm = MockLLMClient(delay_ms=5.0)
        mcp = MockMCPClient()

        for i in range(50):
            agent = JusticaIntegratedAgent(
                llm_client=llm,
                mcp_client=mcp,
            )

            await agent.evaluate_action(
                agent_id="test",
                action_type="bash_exec",
                content="ls",
            )

            del agent

        gc.collect()

        print("\n=== Chaos Rapid Agent Creation ===")
        print("Created and destroyed 50 agents successfully")


# ============================================================================
# RUN PERFORMANCE REPORT
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short", "-m", "slow"])
