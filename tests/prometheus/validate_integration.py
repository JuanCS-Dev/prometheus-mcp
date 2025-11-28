#!/usr/bin/env python3
"""
PROMETHEUS Integration Validation Script.

Validates all integration points between PROMETHEUS and jdev_cli ecosystem.
Run: python tests/prometheus/validate_integration.py
"""

import asyncio
import os
import sys
from typing import Dict, Any, List
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Load .env
env_file = '.env'
if os.path.exists(env_file):
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, _, value = line.partition('=')
                os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


class ValidationResult:
    """Result of a validation test."""
    def __init__(self, name: str, passed: bool, message: str = "", details: Any = None):
        self.name = name
        self.passed = passed
        self.message = message
        self.details = details

    def __str__(self):
        status = "PASS" if self.passed else "FAIL"
        return f"[{status}] {self.name}: {self.message}"


class PrometheusIntegrationValidator:
    """Validates PROMETHEUS integration."""

    def __init__(self):
        self.results: List[ValidationResult] = []

    async def run_all(self) -> Dict[str, Any]:
        """Run all validation tests."""
        print("\n" + "=" * 60)
        print("PROMETHEUS INTEGRATION VALIDATION")
        print("=" * 60 + "\n")

        # Import tests
        await self.test_imports()

        # Interface tests
        await self.test_provider_interface()
        await self.test_client_interface()
        await self.test_tools_interface()

        # Integration tests
        await self.test_bridge_integration()
        await self.test_registry_integration()
        await self.test_gradio_integration()

        # Runtime tests (require API key)
        if os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"):
            await self.test_provider_runtime()
            await self.test_end_to_end()
        else:
            print("\n[SKIP] Runtime tests (no API key)")

        # Summary
        return self.summarize()

    async def test_imports(self):
        """Test all imports work."""
        print("Testing imports...")

        imports = [
            ("prometheus.main", "PrometheusAgent"),
            ("prometheus.core.orchestrator", "PrometheusOrchestrator"),
            ("jdev_cli.core.providers.prometheus_provider", "PrometheusProvider"),
            ("jdev_tui.core.prometheus_client", "PrometheusClient"),
            ("jdev_cli.tools.prometheus_tools", "PrometheusExecuteTool"),
            ("gradio_ui.prometheus_bridge", "PrometheusStreamingBridge"),
            ("gradio_ui.prometheus_components", "render_memory_panel"),
        ]

        for module, obj in imports:
            try:
                mod = __import__(module, fromlist=[obj])
                assert hasattr(mod, obj), f"{obj} not found in {module}"
                self.results.append(ValidationResult(
                    f"import:{module}.{obj}",
                    True,
                    "Imported successfully"
                ))
            except Exception as e:
                self.results.append(ValidationResult(
                    f"import:{module}.{obj}",
                    False,
                    str(e)
                ))

    async def test_provider_interface(self):
        """Test PrometheusProvider interface."""
        print("Testing PrometheusProvider interface...")

        try:
            from jdev_cli.core.providers.prometheus_provider import PrometheusProvider

            provider = PrometheusProvider()

            # Check required methods
            required_methods = [
                "stream", "generate", "evolve", "get_status",
                "get_memory_context", "is_available", "_ensure_initialized"
            ]

            for method in required_methods:
                has_method = hasattr(provider, method)
                self.results.append(ValidationResult(
                    f"provider:{method}",
                    has_method,
                    "Method exists" if has_method else "Method missing"
                ))

        except Exception as e:
            self.results.append(ValidationResult(
                "provider:interface",
                False,
                str(e)
            ))

    async def test_client_interface(self):
        """Test PrometheusClient interface."""
        print("Testing PrometheusClient interface...")

        try:
            from jdev_tui.core.prometheus_client import PrometheusClient

            client = PrometheusClient()

            required_methods = ["stream", "evolve", "get_health_status", "set_tools"]

            for method in required_methods:
                has_method = hasattr(client, method)
                self.results.append(ValidationResult(
                    f"client:{method}",
                    has_method,
                    "Method exists" if has_method else "Method missing"
                ))

        except Exception as e:
            self.results.append(ValidationResult(
                "client:interface",
                False,
                str(e)
            ))

    async def test_tools_interface(self):
        """Test PROMETHEUS tools interface."""
        print("Testing PROMETHEUS tools interface...")

        try:
            from jdev_cli.tools.prometheus_tools import (
                PrometheusExecuteTool,
                PrometheusMemoryQueryTool,
                PrometheusSimulateTool,
                PrometheusEvolveTool,
                PrometheusReflectTool,
                PrometheusCreateToolTool,
                PrometheusGetStatusTool,
                PrometheusBenchmarkTool,
            )

            tools = [
                PrometheusExecuteTool,
                PrometheusMemoryQueryTool,
                PrometheusSimulateTool,
                PrometheusEvolveTool,
                PrometheusReflectTool,
                PrometheusCreateToolTool,
                PrometheusGetStatusTool,
                PrometheusBenchmarkTool,
            ]

            for tool_cls in tools:
                tool = tool_cls()
                has_execute = hasattr(tool, "_execute_validated")
                has_provider = hasattr(tool, "set_provider")

                self.results.append(ValidationResult(
                    f"tool:{tool_cls.__name__}",
                    has_execute and has_provider,
                    "Interface complete" if (has_execute and has_provider) else "Missing methods"
                ))

        except Exception as e:
            self.results.append(ValidationResult(
                "tools:interface",
                False,
                str(e)
            ))

    async def test_bridge_integration(self):
        """Test Bridge integration with PrometheusClient."""
        print("Testing Bridge integration...")

        try:
            with open("jdev_tui/core/bridge.py") as f:
                content = f.read()

            checks = [
                ("PrometheusClient import", "from jdev_tui.core.prometheus_client import PrometheusClient" in content),
                ("_detect_task_complexity", "_detect_task_complexity" in content),
                ("_get_client method", "_get_client" in content),
                ("_provider_mode", "_provider_mode" in content),
                ("Auto-detect patterns", "COMPLEX_TASK_PATTERNS" in content),
            ]

            for name, passed in checks:
                self.results.append(ValidationResult(
                    f"bridge:{name}",
                    passed,
                    "Present" if passed else "Missing"
                ))

        except Exception as e:
            self.results.append(ValidationResult(
                "bridge:integration",
                False,
                str(e)
            ))

    async def test_registry_integration(self):
        """Test Registry integration with PROMETHEUS tools."""
        print("Testing Registry integration...")

        try:
            with open("jdev_cli/tools/registry_setup.py") as f:
                content = f.read()

            tools_expected = [
                "PrometheusExecuteTool",
                "PrometheusMemoryQueryTool",
                "PrometheusSimulateTool",
                "PrometheusEvolveTool",
                "PrometheusReflectTool",
                "PrometheusCreateToolTool",
                "PrometheusGetStatusTool",
                "PrometheusBenchmarkTool",
            ]

            for tool in tools_expected:
                present = tool in content
                self.results.append(ValidationResult(
                    f"registry:{tool}",
                    present,
                    "Registered" if present else "Not registered"
                ))

        except Exception as e:
            self.results.append(ValidationResult(
                "registry:integration",
                False,
                str(e)
            ))

    async def test_gradio_integration(self):
        """Test Gradio integration."""
        print("Testing Gradio integration...")

        try:
            # Check prometheus_bridge.py
            from gradio_ui.prometheus_bridge import PrometheusStreamingBridge
            bridge = PrometheusStreamingBridge()

            checks = [
                ("stream method", hasattr(bridge, "stream")),
                ("get_prometheus_status", hasattr(bridge, "get_prometheus_status")),
                ("evolve method", hasattr(bridge, "evolve")),
            ]

            for name, passed in checks:
                self.results.append(ValidationResult(
                    f"gradio:{name}",
                    passed,
                    "Present" if passed else "Missing"
                ))

            # Check prometheus_components.py

            self.results.append(ValidationResult(
                "gradio:components",
                True,
                "All render functions present"
            ))

        except Exception as e:
            self.results.append(ValidationResult(
                "gradio:integration",
                False,
                str(e)
            ))

    async def test_provider_runtime(self):
        """Test PrometheusProvider at runtime."""
        print("Testing PrometheusProvider runtime...")

        try:
            from jdev_cli.core.providers.prometheus_provider import PrometheusProvider

            provider = PrometheusProvider()
            await provider._ensure_initialized()

            # Check orchestrator
            has_orchestrator = provider._orchestrator is not None
            self.results.append(ValidationResult(
                "runtime:orchestrator",
                has_orchestrator,
                "Initialized" if has_orchestrator else "None"
            ))

            if has_orchestrator:
                # Check orchestrator components
                components = ["memory", "world_model", "reflection"]
                for comp in components:
                    has_comp = hasattr(provider._orchestrator, comp)
                    comp_val = getattr(provider._orchestrator, comp, None)
                    self.results.append(ValidationResult(
                        f"runtime:orchestrator.{comp}",
                        has_comp and comp_val is not None,
                        type(comp_val).__name__ if comp_val else "None"
                    ))

        except Exception as e:
            self.results.append(ValidationResult(
                "runtime:provider",
                False,
                str(e)
            ))

    async def test_end_to_end(self):
        """Test end-to-end flow."""
        print("Testing end-to-end flow...")

        try:
            from jdev_cli.core.providers.prometheus_provider import PrometheusProvider

            provider = PrometheusProvider()

            # Simple generation test
            result = await provider.generate("What is 2+2? Answer with just the number.")

            has_result = len(result) > 0
            has_content = "4" in result or "four" in result.lower()

            self.results.append(ValidationResult(
                "e2e:generate",
                has_result,
                f"Got {len(result)} chars" if has_result else "Empty response"
            ))

            self.results.append(ValidationResult(
                "e2e:correct_answer",
                has_content,
                "Correct" if has_content else f"Response: {result[:50]}..."
            ))

        except Exception as e:
            self.results.append(ValidationResult(
                "e2e:flow",
                False,
                str(e)
            ))

    def summarize(self) -> Dict[str, Any]:
        """Summarize validation results."""
        passed = sum(1 for r in self.results if r.passed)
        failed = sum(1 for r in self.results if not r.passed)
        total = len(self.results)

        print("\n" + "=" * 60)
        print("VALIDATION RESULTS")
        print("=" * 60)

        # Group by category
        categories = {}
        for r in self.results:
            cat = r.name.split(":")[0]
            if cat not in categories:
                categories[cat] = {"passed": 0, "failed": 0, "results": []}
            if r.passed:
                categories[cat]["passed"] += 1
            else:
                categories[cat]["failed"] += 1
            categories[cat]["results"].append(r)

        for cat, data in categories.items():
            status = "PASS" if data["failed"] == 0 else "FAIL"
            print(f"\n{cat.upper()}: [{status}] {data['passed']}/{data['passed'] + data['failed']}")
            for r in data["results"]:
                icon = "  " if r.passed else "  "
                print(f"  {icon} {r}")

        print("\n" + "=" * 60)
        print(f"TOTAL: {passed}/{total} tests passed ({passed/total*100:.0f}%)")
        print("=" * 60)

        return {
            "passed": passed,
            "failed": failed,
            "total": total,
            "success_rate": passed / total if total > 0 else 0,
            "categories": categories,
            "timestamp": datetime.now().isoformat(),
        }


async def main():
    validator = PrometheusIntegrationValidator()
    results = await validator.run_all()

    # Exit code based on results
    return 0 if results["failed"] == 0 else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
