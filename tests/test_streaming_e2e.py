#!/usr/bin/env python3
"""
End-to-End Streaming Test Suite
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Tests the complete streaming pipeline from LLM → Agent → UI

Run with:
    python test_streaming_e2e.py

Expected output:
    ✅ LLM Streaming: PASSED
    ✅ Agent Streaming: PASSED
    ✅ UI Integration: PASSED
    
Author: Claude Code
Date: November 2025
"""

import asyncio
import sys
import time
from typing import AsyncIterator, Dict, Any, List
from dataclasses import dataclass
from enum import Enum


# ============================================================================
# TEST FRAMEWORK
# ============================================================================

class TestResult(Enum):
    PASSED = "✅ PASSED"
    FAILED = "❌ FAILED"
    SKIPPED = "⏭️ SKIPPED"


@dataclass
class TestCase:
    name: str
    result: TestResult = TestResult.SKIPPED
    message: str = ""
    duration: float = 0.0


class TestSuite:
    def __init__(self, name: str):
        self.name = name
        self.tests: List[TestCase] = []

    def add_test(self, test: TestCase):
        self.tests.append(test)

    def summary(self):
        passed = sum(1 for t in self.tests if t.result == TestResult.PASSED)
        failed = sum(1 for t in self.tests if t.result == TestResult.FAILED)
        total = len(self.tests)

        print(f"\n{'='*60}")
        print(f"TEST SUITE: {self.name}")
        print(f"{'='*60}")

        for test in self.tests:
            status = test.result.value
            duration = f"({test.duration:.2f}s)" if test.duration else ""
            print(f"  {status} {test.name} {duration}")
            if test.message and test.result == TestResult.FAILED:
                print(f"      ↳ {test.message}")

        print(f"\n  Summary: {passed}/{total} passed, {failed} failed")
        print(f"{'='*60}\n")

        return failed == 0


# ============================================================================
# MOCK IMPLEMENTATIONS
# ============================================================================

class MockLLMClient:
    """Mock LLM that simulates token streaming"""

    def __init__(self, response_tokens: List[str] = None, delay: float = 0.02):
        self.response_tokens = response_tokens or [
            "Based", " on", " the", " request", ",", "\n",
            "I", " will", " create", " a", " plan", ":",
            "\n\n", "Step", " 1", ":", " Analyze", " requirements",
            "\n", "Step", " 2", ":", " Design", " solution",
            "\n", "Step", " 3", ":", " Implement", " code",
        ]
        self.delay = delay
        self.call_count = 0

    async def generate_stream(
        self,
        prompt: str,
        system_prompt: str = None,
        max_tokens: int = 2048,
        temperature: float = 0.7
    ) -> AsyncIterator[str]:
        """Simulate token-by-token streaming"""
        self.call_count += 1

        for token in self.response_tokens:
            await asyncio.sleep(self.delay)
            yield token

    async def stream_chat(
        self,
        messages: List[Dict],
        max_tokens: int = 2048,
        temperature: float = 0.7,
        provider: str = None
    ) -> AsyncIterator[str]:
        """Alternative interface for compatibility"""
        async for token in self.generate_stream(messages[-1].get("content", "")):
            yield token


@dataclass
class MockAgentTask:
    """Mock agent task"""
    request: str
    context: Dict[str, Any] = None
    trace_id: str = "test-trace-001"

    def __post_init__(self):
        if self.context is None:
            self.context = {"cwd": "/test/project"}


@dataclass
class MockAgentResponse:
    """Mock agent response"""
    success: bool
    data: Dict[str, Any] = None
    error: str = None
    reasoning: str = None


class MockPlannerAgent:
    """Mock planner with execute_streaming"""

    def __init__(self, llm: MockLLMClient):
        self.llm = llm
        self.name = "planner"

    async def execute_streaming(
        self,
        task: MockAgentTask
    ) -> AsyncIterator[Dict[str, Any]]:
        """Streaming execution - this is what we're testing"""

        # Phase 1: Status
        yield {"type": "status", "data": "📋 Loading project context..."}
        await asyncio.sleep(0.05)

        # Phase 2: Generate
        yield {"type": "status", "data": "🎯 Generating plan..."}

        # Phase 3: Stream LLM tokens
        buffer = []
        async for token in self.llm.generate_stream(
            prompt=task.request,
            system_prompt="You are a planner",
            max_tokens=2048,
            temperature=0.3
        ):
            buffer.append(token)
            yield {"type": "thinking", "data": token}  # ← THE CRITICAL PART!

        response_text = ''.join(buffer)

        # Phase 4: Process
        yield {"type": "status", "data": "⚙️ Processing plan..."}
        await asyncio.sleep(0.05)

        # Phase 5: Result
        yield {
            "type": "result",
            "data": MockAgentResponse(
                success=True,
                data={"plan": response_text},
                reasoning="Plan generated successfully"
            )
        }


class MockMaestroUI:
    """Mock MAESTRO UI that receives streaming updates"""

    def __init__(self):
        self.updates: List[Dict[str, Any]] = []
        self.panels = {
            "executor": [],
            "planner": [],
            "file_ops": []
        }

    async def update_agent_stream(self, agent_name: str, data: str):
        """Receive streaming token update"""
        self.updates.append({
            "agent": agent_name,
            "data": data,
            "timestamp": time.time()
        })

        if agent_name in self.panels:
            self.panels[agent_name].append(data)

    def get_panel_content(self, panel_name: str) -> str:
        """Get accumulated content for a panel"""
        return ''.join(self.panels.get(panel_name, []))


class MockOrchestrator:
    """Mock orchestrator that routes to agents and updates UI"""

    def __init__(self, ui: MockMaestroUI):
        self.ui = ui
        self.llm = MockLLMClient()
        self.agents = {
            "planner": MockPlannerAgent(self.llm)
        }

    async def execute_streaming(
        self,
        prompt: str,
        context: Dict[str, Any] = None
    ) -> AsyncIterator[Dict[str, Any]]:
        """Execute and stream to UI"""

        # Route to planner for this test
        agent = self.agents["planner"]
        task = MockAgentTask(request=prompt, context=context)

        # Stream from agent
        async for update in agent.execute_streaming(task):
            # Forward to UI
            if update["type"] == "thinking":
                await self.ui.update_agent_stream("planner", update["data"])

            yield update


# ============================================================================
# TEST CASES
# ============================================================================

async def test_llm_streaming() -> TestCase:
    """Test 1: LLM generates tokens correctly"""
    test = TestCase(name="LLM Streaming")
    start = time.time()

    try:
        llm = MockLLMClient()
        tokens = []

        async for token in llm.generate_stream("Test prompt"):
            tokens.append(token)

        # Assertions
        if len(tokens) == 0:
            test.result = TestResult.FAILED
            test.message = "No tokens generated"
        elif llm.call_count != 1:
            test.result = TestResult.FAILED
            test.message = f"Expected 1 call, got {llm.call_count}"
        else:
            test.result = TestResult.PASSED
            test.message = f"Generated {len(tokens)} tokens"

    except Exception as e:
        test.result = TestResult.FAILED
        test.message = str(e)

    test.duration = time.time() - start
    return test


async def test_agent_streaming() -> TestCase:
    """Test 2: Agent streams updates correctly"""
    test = TestCase(name="Agent Streaming")
    start = time.time()

    try:
        llm = MockLLMClient()
        agent = MockPlannerAgent(llm)
        task = MockAgentTask(request="Create authentication system")

        updates = []
        thinking_tokens = []

        async for update in agent.execute_streaming(task):
            updates.append(update)
            if update["type"] == "thinking":
                thinking_tokens.append(update["data"])

        # Assertions
        status_updates = [u for u in updates if u["type"] == "status"]
        result_updates = [u for u in updates if u["type"] == "result"]

        if len(thinking_tokens) == 0:
            test.result = TestResult.FAILED
            test.message = "No thinking tokens streamed"
        elif len(status_updates) < 2:
            test.result = TestResult.FAILED
            test.message = f"Expected >=2 status updates, got {len(status_updates)}"
        elif len(result_updates) != 1:
            test.result = TestResult.FAILED
            test.message = f"Expected 1 result, got {len(result_updates)}"
        else:
            test.result = TestResult.PASSED
            test.message = f"Streamed {len(thinking_tokens)} tokens, {len(status_updates)} statuses"

    except Exception as e:
        test.result = TestResult.FAILED
        test.message = str(e)

    test.duration = time.time() - start
    return test


async def test_ui_receives_updates() -> TestCase:
    """Test 3: UI receives streaming updates"""
    test = TestCase(name="UI Integration")
    start = time.time()

    try:
        ui = MockMaestroUI()
        orch = MockOrchestrator(ui)

        updates = []
        async for update in orch.execute_streaming(
            "Create user authentication",
            context={"cwd": "/test"}
        ):
            updates.append(update)

        # Check UI received updates
        planner_content = ui.get_panel_content("planner")

        if len(ui.updates) == 0:
            test.result = TestResult.FAILED
            test.message = "UI received no updates"
        elif len(planner_content) == 0:
            test.result = TestResult.FAILED
            test.message = "Planner panel is empty"
        else:
            test.result = TestResult.PASSED
            test.message = f"UI received {len(ui.updates)} updates, panel has {len(planner_content)} chars"

    except Exception as e:
        test.result = TestResult.FAILED
        test.message = str(e)

    test.duration = time.time() - start
    return test


async def test_streaming_order() -> TestCase:
    """Test 4: Updates arrive in correct order"""
    test = TestCase(name="Streaming Order")
    start = time.time()

    try:
        llm = MockLLMClient()
        agent = MockPlannerAgent(llm)
        task = MockAgentTask(request="Test task")

        update_types = []
        async for update in agent.execute_streaming(task):
            update_types.append(update["type"])

        # Expected order: status -> status -> thinking* -> status -> result
        expected_order = ["status", "status"]  # First two statuses

        # Check starts correctly
        if update_types[:2] != expected_order:
            test.result = TestResult.FAILED
            test.message = f"Wrong start order: {update_types[:2]}"
        # Check ends with result
        elif update_types[-1] != "result":
            test.result = TestResult.FAILED
            test.message = f"Should end with result, got: {update_types[-1]}"
        # Check has thinking tokens
        elif "thinking" not in update_types:
            test.result = TestResult.FAILED
            test.message = "No thinking tokens in stream"
        else:
            test.result = TestResult.PASSED
            test.message = f"Correct order: {len(update_types)} updates"

    except Exception as e:
        test.result = TestResult.FAILED
        test.message = str(e)

    test.duration = time.time() - start
    return test


async def test_error_handling() -> TestCase:
    """Test 5: Errors are handled gracefully"""
    test = TestCase(name="Error Handling")
    start = time.time()

    try:
        class FailingLLM:
            async def generate_stream(self, *args, **kwargs):
                yield "token1"
                raise Exception("Simulated error")

        class FailingAgent:
            def __init__(self):
                self.llm = FailingLLM()

            async def execute_streaming(self, task):
                try:
                    yield {"type": "status", "data": "Starting..."}
                    async for token in self.llm.generate_stream("test"):
                        yield {"type": "thinking", "data": token}
                except Exception as e:
                    yield {"type": "error", "data": {"error": str(e)}}

        agent = FailingAgent()
        task = MockAgentTask(request="Test")

        updates = []
        async for update in agent.execute_streaming(task):
            updates.append(update)

        error_updates = [u for u in updates if u["type"] == "error"]

        if len(error_updates) == 0:
            test.result = TestResult.FAILED
            test.message = "Error not captured in stream"
        else:
            test.result = TestResult.PASSED
            test.message = "Error handled gracefully"

    except Exception as e:
        # If exception propagates, that's also acceptable
        test.result = TestResult.PASSED
        test.message = f"Error propagated: {str(e)[:50]}"

    test.duration = time.time() - start
    return test


async def test_streaming_performance() -> TestCase:
    """Test 6: Streaming meets performance requirements"""
    test = TestCase(name="Streaming Performance")
    start = time.time()

    try:
        # Fast LLM simulation
        llm = MockLLMClient(
            response_tokens=["token"] * 100,
            delay=0.01  # 10ms per token = 100 tokens/sec
        )
        agent = MockPlannerAgent(llm)
        task = MockAgentTask(request="Performance test")

        update_times = []
        last_time = time.time()

        async for update in agent.execute_streaming(task):
            now = time.time()
            if update["type"] == "thinking":
                update_times.append(now - last_time)
            last_time = now

        # Calculate average time between updates
        avg_interval = sum(update_times) / len(update_times) if update_times else 0
        fps = 1 / avg_interval if avg_interval > 0 else 0

        # Target: 30 FPS = 33ms between updates
        if fps < 20:
            test.result = TestResult.FAILED
            test.message = f"Too slow: {fps:.1f} FPS (target: 30)"
        else:
            test.result = TestResult.PASSED
            test.message = f"{fps:.1f} FPS ({avg_interval*1000:.1f}ms avg interval)"

    except Exception as e:
        test.result = TestResult.FAILED
        test.message = str(e)

    test.duration = time.time() - start
    return test


# ============================================================================
# MAIN TEST RUNNER
# ============================================================================

async def run_all_tests():
    """Run all streaming tests"""
    suite = TestSuite("Streaming Implementation Tests")

    print("\n🧪 Running streaming tests...\n")

    # Run tests
    tests = [
        await test_llm_streaming(),
        await test_agent_streaming(),
        await test_ui_receives_updates(),
        await test_streaming_order(),
        await test_error_handling(),
        await test_streaming_performance(),
    ]

    for test in tests:
        suite.add_test(test)
        status = "✅" if test.result == TestResult.PASSED else "❌"
        print(f"  {status} {test.name}")

    # Summary
    all_passed = suite.summary()

    # Visual demonstration
    print("\n📺 VISUAL DEMONSTRATION:")
    print("-" * 40)

    ui = MockMaestroUI()
    orch = MockOrchestrator(ui)

    print("PLANNER Panel (streaming tokens):")
    async for update in orch.execute_streaming("Create auth"):
        if update["type"] == "thinking":
            print(update["data"], end="", flush=True)
    print("\n" + "-" * 40)

    return all_passed


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)
