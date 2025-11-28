#!/usr/bin/env python3
"""
Custom Plugin Example.

SCALE & SUSTAIN Phase 2.3 - SDK Example.

Demonstrates how to create a custom plugin using the juan-dev-sdk.

Author: JuanCS Dev
Date: 2025-11-26
"""

import asyncio
import sys
from pathlib import Path
from typing import Any, Dict, Optional

# Add SDK to path for development
sdk_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(sdk_path))

from juan_dev_sdk.plugins import PluginBuilder, create_plugin


# Example 1: Simple plugin using builder pattern
def create_metrics_plugin():
    """Create a metrics collection plugin using the builder pattern."""

    # State for the plugin
    metrics_state = {
        "requests": 0,
        "tokens_used": 0,
        "errors": 0,
    }

    async def on_activate(context):
        """Called when plugin is activated."""
        print(f"[Metrics] Plugin activated for session: {context.get('session_id')}")
        metrics_state["requests"] = 0
        metrics_state["tokens_used"] = 0
        metrics_state["errors"] = 0

    async def on_deactivate():
        """Called when plugin is deactivated."""
        print(f"[Metrics] Final stats - Requests: {metrics_state['requests']}, "
              f"Tokens: {metrics_state['tokens_used']}, Errors: {metrics_state['errors']}")

    def on_command(command: str, args: str) -> Optional[Any]:
        """Handle custom commands."""
        if command == "/metrics":
            return {
                "requests": metrics_state["requests"],
                "tokens_used": metrics_state["tokens_used"],
                "errors": metrics_state["errors"],
            }
        elif command == "/metrics-reset":
            metrics_state["requests"] = 0
            metrics_state["tokens_used"] = 0
            metrics_state["errors"] = 0
            return "Metrics reset"
        return None

    def on_before_request(request: Dict) -> Dict:
        """Called before each request."""
        metrics_state["requests"] += 1
        return request

    def on_after_response(response: Dict) -> Dict:
        """Called after each response."""
        tokens = response.get("usage", {}).get("total_tokens", 0)
        metrics_state["tokens_used"] += tokens
        return response

    def on_error(error: Exception) -> None:
        """Called on errors."""
        metrics_state["errors"] += 1

    plugin = (
        PluginBuilder("metrics-collector")
        .with_version("1.0.0")
        .with_description("Collects usage metrics for monitoring")
        .with_author("JuanCS Dev")
        .on_activate(on_activate)
        .on_deactivate(on_deactivate)
        .on_command(on_command)
        .with_hook("before_request", on_before_request)
        .with_hook("after_response", on_after_response)
        .with_hook("on_error", on_error)
        .with_config({
            "log_to_file": False,
            "metrics_endpoint": None,
        })
        .build()
    )

    return plugin


# Example 2: Using the convenience function
def create_logger_plugin():
    """Create a logging plugin using the convenience function."""

    log_entries = []

    def log_handler(event_type: str, data: Any) -> None:
        """Log events."""
        log_entries.append({
            "type": event_type,
            "data": str(data)[:100],
            "timestamp": asyncio.get_event_loop().time() if asyncio.get_event_loop().is_running() else 0,
        })

    plugin = create_plugin(
        name="request-logger",
        version="1.0.0",
        description="Logs all requests and responses",
        author="JuanCS Dev",
        hooks={
            "before_request": lambda r: (log_handler("request", r), r)[1],
            "after_response": lambda r: (log_handler("response", r), r)[1],
        },
        commands={
            "/logs": lambda args: log_entries[-10:],  # Last 10 entries
            "/logs-clear": lambda args: log_entries.clear() or "Logs cleared",
        },
    )

    return plugin


# Example 3: Full-featured plugin class
class NotificationPlugin:
    """
    Custom notification plugin.

    Sends notifications on specific events like errors or long-running operations.
    This example shows how to create a more complex plugin with state.
    """

    def __init__(self, webhook_url: Optional[str] = None):
        self.webhook_url = webhook_url
        self.notifications_sent = 0
        self.pending_notifications = []

        self.plugin = (
            PluginBuilder("notifications")
            .with_version("1.0.0")
            .with_description("Sends notifications for important events")
            .with_author("JuanCS Dev")
            .with_dependencies(["metrics-collector"])  # Depends on metrics
            .with_provides(["notifications", "alerts"])
            .on_activate(self._on_activate)
            .on_deactivate(self._on_deactivate)
            .on_command(self._handle_command)
            .with_hook("on_error", self._on_error)
            .with_hook("on_long_operation", self._on_long_operation)
            .with_config({
                "webhook_url": webhook_url,
                "notify_on_errors": True,
                "notify_on_long_ops": True,
                "long_op_threshold_seconds": 30,
            })
            .build()
        )

    async def _on_activate(self, context: Dict) -> None:
        """Initialize the plugin."""
        print(f"[Notifications] Activated with webhook: {self.webhook_url or 'None (dry run)'}")
        self.notifications_sent = 0

    async def _on_deactivate(self) -> None:
        """Cleanup on deactivation."""
        print(f"[Notifications] Deactivated. Sent {self.notifications_sent} notifications.")
        # Flush pending notifications
        await self._flush_pending()

    def _handle_command(self, command: str, args: str) -> Optional[Any]:
        """Handle plugin commands."""
        if command == "/notify":
            return self._send_notification("manual", args)
        elif command == "/notify-status":
            return {
                "sent": self.notifications_sent,
                "pending": len(self.pending_notifications),
                "webhook_configured": self.webhook_url is not None,
            }
        elif command == "/notify-test":
            return self._send_notification("test", "Test notification from juan-dev-code")
        return None

    def _on_error(self, error: Exception) -> None:
        """Handle errors by sending notification."""
        self._send_notification(
            "error",
            f"Error occurred: {type(error).__name__}: {str(error)}"
        )

    def _on_long_operation(self, operation: Dict) -> None:
        """Handle long-running operations."""
        duration = operation.get("duration", 0)
        name = operation.get("name", "unknown")
        self._send_notification(
            "long_operation",
            f"Operation '{name}' took {duration:.2f}s"
        )

    def _send_notification(self, event_type: str, message: str) -> Dict:
        """Send a notification."""
        notification = {
            "type": event_type,
            "message": message,
            "sent": False,
        }

        if self.webhook_url:
            # In real implementation, would send HTTP request
            notification["sent"] = True
            self.notifications_sent += 1
            print(f"[Notifications] Sent: {event_type} - {message[:50]}...")
        else:
            # Queue for later or just log
            self.pending_notifications.append(notification)
            print(f"[Notifications] Queued: {event_type} - {message[:50]}...")

        return notification

    async def _flush_pending(self) -> int:
        """Flush pending notifications."""
        count = len(self.pending_notifications)
        self.pending_notifications.clear()
        return count


# Example 4: Plugin with tool interception
class SecurityFilterPlugin:
    """
    Security filter plugin.

    Intercepts tool executions to check for dangerous operations.
    """

    DANGEROUS_PATTERNS = [
        "rm -rf /",
        "sudo rm",
        ":(){:|:&};:",
        "dd if=",
        "mkfs",
    ]

    def __init__(self, strict_mode: bool = False):
        self.strict_mode = strict_mode
        self.blocked_count = 0

        self.plugin = (
            PluginBuilder("security-filter")
            .with_version("1.0.0")
            .with_description("Filters dangerous tool executions")
            .with_author("Security Team")
            .with_priority("high")
            .on_tool_execute(self._check_tool)
            .on_command(self._handle_command)
            .with_config({
                "strict_mode": strict_mode,
                "blocked_patterns": self.DANGEROUS_PATTERNS,
            })
            .build()
        )

    def _check_tool(self, tool_name: str, params: Dict) -> Optional[Any]:
        """Intercept and check tool execution."""
        if tool_name in ("bash", "shell", "execute"):
            command = params.get("command", "")
            for pattern in self.DANGEROUS_PATTERNS:
                if pattern in command:
                    self.blocked_count += 1
                    return {
                        "blocked": True,
                        "reason": f"Dangerous pattern detected: {pattern}",
                        "tool": tool_name,
                    }

        # Return None to allow execution to continue
        return None

    def _handle_command(self, command: str, args: str) -> Optional[Any]:
        """Handle plugin commands."""
        if command == "/security-status":
            return {
                "blocked_operations": self.blocked_count,
                "strict_mode": self.strict_mode,
                "patterns": len(self.DANGEROUS_PATTERNS),
            }
        return None


# Example usage
async def run_plugin_examples():
    """Demonstrate creating custom plugins."""

    print("=== Juan Dev SDK - Custom Plugin Examples ===\n")

    # Create plugins
    metrics = create_metrics_plugin()
    logger = create_logger_plugin()
    notifications = NotificationPlugin(webhook_url=None)
    security = SecurityFilterPlugin(strict_mode=True)

    print("Created plugins:")
    print(f"  - {metrics.name} v{metrics.version}: {metrics.description}")
    print(f"  - {logger.name} v{logger.version}: {logger.description}")
    print(f"  - {notifications.plugin.name}: {notifications.plugin.description}")
    print(f"  - {security.plugin.name}: {security.plugin.description}")

    # Show dependencies
    print("\n--- Plugin Dependencies ---")
    print(f"Notifications depends on: {notifications.plugin.dependencies}")
    print(f"Notifications provides: {notifications.plugin.provides}")

    # Simulate plugin lifecycle
    print("\n--- Simulated Lifecycle ---")

    # Activate
    context = {"session_id": "example-123"}
    await metrics.activate(context)
    await logger.activate(context)
    await notifications._on_activate(context)

    # Simulate some events
    print("\n--- Simulated Events ---")

    # Command handling
    print(f"Metrics: {metrics.on_command('/metrics', '')}")

    # Tool interception
    dangerous_result = security._check_tool("bash", {"command": "rm -rf /"})
    print(f"Security blocked: {dangerous_result}")

    safe_result = security._check_tool("bash", {"command": "ls -la"})
    print(f"Security allowed: {safe_result is None}")

    # Deactivate
    await metrics.deactivate()
    await notifications._on_deactivate()

    print("\n--- Integration Example ---")
    print("""
    # Register plugins with client
    client = JuanDevClient()

    client.register_plugin(metrics)
    client.register_plugin(logger)
    client.register_plugin(notifications.plugin)
    client.register_plugin(security.plugin)

    # Plugins automatically intercept requests/responses
    async for chunk in client.chat("Hello"):
        print(chunk, end="")

    # Use plugin commands
    print(client.execute_command("/metrics"))
    print(client.execute_command("/security-status"))
    """)


def main():
    """Main entry point."""
    asyncio.run(run_plugin_examples())


if __name__ == "__main__":
    main()
