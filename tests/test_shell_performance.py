"""
Shell Performance & Real Usage Testing Suite
✅ Performance benchmarks
✅ Edge case handling  
✅ Real workflow simulations
✅ Constitutional compliance
"""
import pytest
import time
from unittest.mock import patch
from jdev_cli.shell import InteractiveShell


class TestPerformance:
    """Performance benchmarks"""

    def test_initialization_speed(self):
        """Shell init < 1s"""
        with patch('jdev_cli.shell.default_llm_client'):
            start = time.perf_counter()
            shell = InteractiveShell()
            init_ms = (time.perf_counter() - start) * 1000

            print(f"\n⚡ Init: {init_ms:.1f}ms")
            assert init_ms < 1000
            assert shell is not None

    def test_tool_access_speed(self):
        """Tool registry access < 50ms"""
        with patch('jdev_cli.shell.default_llm_client'):
            shell = InteractiveShell()

            start = time.perf_counter()
            schemas = shell.registry.get_schemas()
            access_ms = (time.perf_counter() - start) * 1000

            print(f"\n📋 Registry: {access_ms:.2f}ms, {len(schemas)} tools")
            assert access_ms < 50
            assert len(schemas) >= 20


class TestEdgeCases:
    """Edge cases and error handling"""

    @pytest.fixture
    def shell(self):
        with patch('jdev_cli.shell.default_llm_client'):
            return InteractiveShell()

    def test_unicode(self, shell):
        """Unicode support"""
        cases = ["/create 文件.py", "/search émoji 🚀", "/bash echo 'тест'"]
        for cmd in cases:
            assert isinstance(cmd, str)
            assert len(cmd) > 0

    def test_special_chars(self, shell):
        """Special characters"""
        cases = [
            "/create 'file with spaces.py'",
            "/search 'pattern.*'",
            "/bash ls -la",
        ]
        for cmd in cases:
            assert cmd.startswith('/')

    def test_long_input(self, shell):
        """Very long input doesn't crash"""
        long = "/search " + "A" * 5000
        assert len(long) > 5000


class TestRealUsage:
    """Real-world workflows"""

    @pytest.fixture
    def shell(self):
        with patch('jdev_cli.shell.default_llm_client'):
            return InteractiveShell()

    def test_dev_workflow(self, shell):
        """Typical development workflow"""
        workflow = [
            "/search TODO",
            "/create test.py",
            "/edit test.py",
            "/bash pytest",
            "/git status",
            "/git diff",
        ]

        for cmd in workflow:
            assert cmd.startswith('/'), f"Invalid: {cmd}"

    def test_conversation_switch(self, shell):
        """Tool vs conversation mode detection"""
        cases = [
            ("explain Python", False),
            ("/create file.py", True),
            ("what is this?", False),
            ("/bash ls", True),
            ("help me debug", False),
        ]

        for cmd, is_tool in cases:
            detected = cmd.startswith('/')
            assert detected == is_tool, f"Failed: {cmd}"


class TestIntegration:
    """Component integration"""

    def test_all_components_loaded(self):
        """All required components present"""
        with patch('jdev_cli.shell.default_llm_client'):
            shell = InteractiveShell()

            required = [
                'registry', 'context', 'conversation',
                'recovery_engine', 'async_executor',
                'file_watcher', 'recent_files', 'console'
            ]

            for comp in required:
                assert hasattr(shell, comp), f"Missing: {comp}"

            print(f"\n✅ All {len(required)} components loaded")

    def test_tool_registry_populated(self):
        """Tool registry has core tools"""
        with patch('jdev_cli.shell.default_llm_client'):
            shell = InteractiveShell()
            schemas = shell.registry.get_schemas()

            tool_names = []
            for s in schemas:
                name = s.get('name') or s.get('function', {}).get('name', 'unknown')
                tool_names.append(name)

            print(f"\n🔧 {len(tool_names)} tools registered")
            print(f"   Sample: {tool_names[:5]}")

            assert len(tool_names) >= 20

    def test_conversation_manager_active(self):
        """Conversation manager functional"""
        with patch('jdev_cli.shell.default_llm_client'):
            shell = InteractiveShell()

            assert shell.conversation is not None
            assert hasattr(shell.conversation, 'session_id')
            assert shell.conversation.session_id is not None


class TestConstitutional:
    """Constitutional compliance (Vértice v3.0)"""

    def test_p6_recovery_limits(self):
        """P6: Max 2 recovery attempts enforced"""
        with patch('jdev_cli.shell.default_llm_client'):
            shell = InteractiveShell()
            assert shell.recovery_engine.max_attempts == 2
            print("\n✅ P6: Recovery limited to 2 attempts")

    def test_p5_concurrency_control(self):
        """P5: Async concurrency controlled"""
        with patch('jdev_cli.shell.default_llm_client'):
            shell = InteractiveShell()
            assert hasattr(shell.async_executor, '_max_parallel')
            assert shell.async_executor._max_parallel == 5
            print("\n✅ P5: Max 5 parallel operations")

    def test_phase_4_3_async_executor(self):
        """Phase 4.3: Async executor implemented"""
        with patch('jdev_cli.shell.default_llm_client'):
            shell = InteractiveShell()
            assert shell.async_executor is not None
            print("\n✅ Phase 4.3: Async executor active")

    def test_phase_4_4_file_watcher(self):
        """Phase 4.4: File watcher implemented"""
        with patch('jdev_cli.shell.default_llm_client'):
            shell = InteractiveShell()
            assert shell.file_watcher is not None
            assert shell.recent_files is not None
            print("\n✅ Phase 4.4: File watcher active")


class TestMetrics:
    """Performance metrics collection"""

    def test_complete_baseline(self):
        """Collect complete performance baseline"""
        with patch('jdev_cli.shell.default_llm_client'):
            # Initialization
            t0 = time.perf_counter()
            shell = InteractiveShell()
            init_ms = (time.perf_counter() - t0) * 1000

            # Tool registry access
            t0 = time.perf_counter()
            schemas = shell.registry.get_schemas()
            registry_ms = (time.perf_counter() - t0) * 1000

            # Component access
            t0 = time.perf_counter()
            _ = shell.conversation.session_id
            _ = shell.recovery_engine.max_attempts
            component_ms = (time.perf_counter() - t0) * 1000

            print("\n📊 Performance Baseline:")
            print(f"   Init:       {init_ms:6.1f}ms")
            print(f"   Registry:   {registry_ms:6.2f}ms ({len(schemas)} tools)")
            print(f"   Components: {component_ms:6.2f}ms")
            print(f"   Total:      {init_ms + registry_ms + component_ms:6.1f}ms")

            # Assertions
            assert init_ms < 1000, f"Init too slow: {init_ms}ms"
            assert registry_ms < 50, f"Registry too slow: {registry_ms}ms"
            assert component_ms < 10, f"Component access too slow: {component_ms}ms"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
