
import os
import sys
import unittest
from unittest.mock import MagicMock, patch

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

class TestFinalAirgap(unittest.IsolatedAsyncioTestCase):
    """
    Operation 'Final Airgap' - Deep System Audit
    
    Targeting 5 Dimensions of Failure:
    1. Physical Airgap (Local vs Remote Filesystem)
    2. State Airgap (Provider Switching Amnesia)
    3. Visual Airgap (Streaming Desync)
    4. Protocol Airgap (MCP Timeout)
    5. Authentication Airgap (Environment Leaks)
    """

    async def test_1_physical_airgap_remote_file_access(self):
        """
        Vector: User asks Prometheus (Remote) to 'Analyze ./data/logs.txt'.
        Risk: Prometheus receives path string, not content.
        """
        print("\n🧪 Testing Physical Airgap (Remote File Access)...")

        from jdev_cli.core.providers.prometheus_provider import PrometheusProvider

        # Mock the orchestrator
        provider = PrometheusProvider()
        provider._orchestrator = MagicMock()
        provider._initialized = True

        # Simulate user prompt with local file path
        prompt = "Analyze this file: ./test_data/secret.txt"
        context = [{"role": "user", "content": prompt}]

        # Call build_prompt
        full_prompt = provider._build_prompt(prompt, None, context)

        # Check if file content is injected (It SHOULD be for a fix, but we expect it NOT to be for the audit)
        if "./test_data/secret.txt" in full_prompt and "SECRET_CONTENT" not in full_prompt:
            print("🔴 VULNERABILITY CONFIRMED: Local file path sent to remote agent without content injection.")
        else:
            print("🟢 SAFE: File content appears to be injected (or test setup is wrong).")

    async def test_2_state_airgap_provider_switching(self):
        """
        Vector: Switch provider mid-conversation.
        Risk: History loss.
        """
        print("\n🧪 Testing State Airgap (Provider Switching)...")

        from jdev_cli.core.providers.prometheus_provider import PrometheusProvider

        provider = PrometheusProvider()

        # Simulate rich history
        context = [
            {"role": "user", "content": "My name is Juan."},
            {"role": "assistant", "content": "Hello Juan."},
            {"role": "user", "content": "Who am I?"}
        ]

        full_prompt = provider._build_prompt("Who am I?", None, context)

        if "My name is Juan" in full_prompt:
            print("🟢 SAFE: History is preserved in prompt construction.")
        else:
            print("🔴 VULNERABILITY CONFIRMED: History lost during prompt construction.")

    async def test_3_visual_airgap_streaming_desync(self):
        """
        Vector: Split token streaming '[TOOL_' + 'CALL]'.
        Risk: Regex failure / Raw JSON leak.
        """
        print("\n🧪 Testing Visual Airgap (Streaming Desync)...")

        from jdev_cli.tui.components.block_detector import BlockDetector, BlockType

        detector = BlockDetector()

        # Simulate split chunks
        chunk1 = "[TOOL_"
        chunk2 = "CALL:read_file:{}]"

        detector.process_chunk(chunk1)
        current = detector.get_current_block()

        print(f"  State after chunk 1: {current.block_type if current else 'None'}")

        detector.process_chunk(chunk2)
        current = detector.get_current_block()

        print(f"  State after chunk 2: {current.block_type if current else 'None'}")

        if current and current.block_type == BlockType.TOOL_CALL:
             print("🟢 SAFE: BlockDetector handled split tokens correctly.")
        else:
             print("🟡 UX GLITCH: BlockDetector failed to identify split TOOL_CALL tag.")

    async def test_4_protocol_airgap_mcp_timeout(self):
        """
        Vector: Prometheus takes 45s.
        Risk: MCP Client defaults to 30s.
        """
        print("\n🧪 Testing Protocol Airgap (MCP Timeout)...")

        from jdev_cli.core.mcp import MCPClient

        # Check constants
        print(f"  Default Timeout: {MCPClient.TOOL_TIMEOUT}s")
        print(f"  Dangerous Timeout: {MCPClient.DANGEROUS_TOOL_TIMEOUT}s")
        print(f"  Long Running Tools: {MCPClient.LONG_RUNNING_TOOLS}")

        if "prometheus_simulate" not in MCPClient.LONG_RUNNING_TOOLS:
            print("🔴 VULNERABILITY CONFIRMED: 'prometheus_simulate' missing from LONG_RUNNING_TOOLS.")
        else:
             print("🟢 SAFE: 'prometheus_simulate' is marked as long-running.")

    async def test_5_auth_airgap_env_check(self):
        """
        Vector: Missing env vars.
        Risk: Crash vs Graceful degradation.
        """
        print("\n🧪 Testing Authentication Airgap...")

        # Simulate missing env
        with patch.dict(os.environ, {}, clear=True):
            from jdev_cli.core.providers.prometheus_provider import PrometheusProvider
            provider = PrometheusProvider()

            if not provider.is_available():
                 print("🟢 SAFE: Provider reports unavailable without API key.")
            else:
                 print("🔴 VULNERABILITY: Provider claims availability without API key!")

if __name__ == "__main__":
    unittest.main()
