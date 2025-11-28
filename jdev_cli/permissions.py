"""
Permission Management System v2.0

Baseado em:
- Anthropic Claude Code Best Practices (Novembro 2025)
- OWASP Securing Agentic Applications Guide 1.0 (Julho 2025)
- AWS Agentic AI Security Scoping Matrix (2025)

Design Principles:
1. Least Model Privilege (OWASP): Default deny, explicit allow
2. Defense-in-depth: Multiple layers (deny > allow > ask)
3. Auditability: Log todas as decisões
4. Hierarchical config: User < Project < Local
5. Claude Code compatible: Same syntax and patterns

References:
- https://www.anthropic.com/engineering/claude-code-best-practices
- https://genai.owasp.org/resource/securing-agentic-applications-guide-1-0/
- https://aws.amazon.com/blogs/security/the-agentic-ai-security-scoping-matrix/
"""

import json
import logging
import fnmatch
import datetime
from enum import Enum
from typing import Tuple, Dict, Any
from pathlib import Path

logger = logging.getLogger(__name__)


class PermissionLevel(Enum):
    """Permission decision levels (OWASP pattern)"""
    ALLOW = "allow"      # Auto-approved (in allowlist)
    DENY = "deny"        # Blocked (in blocklist or destructive)
    ASK = "ask"          # Requires user approval


class PermissionManager:
    """
    Permission system baseado em Claude Code (Nov 2025) + OWASP best practices.

    Features:
    - Hierarchical config (User > Project > Local)
    - Allow/Deny lists with glob patterns (Claude Code compatible)
    - Audit logging (OWASP requirement)
    - Runtime persistence ("always allow" feature)
    - Pattern matching (wildcards, glob, exact)

    Security Model:
    1. Check DENY list first (workaround para Claude Code bug v1.0.93+)
    2. Check ALLOW list
    3. Auto-approve read-only if configured
    4. Default: ASK (secure by default - OWASP)
    """

    def __init__(self, safe_mode: bool = True):
        """Initialize permission manager.

        Args:
            safe_mode: If False, bypass all checks (--dangerously-skip-permissions)
        """
        self.safe_mode = safe_mode

        # Config file paths (Claude Code hierarchy)
        self.user_config_path = Path.home() / ".maestro" / "settings.json"
        self.project_config_path = Path.cwd() / ".maestro" / "settings.json"
        self.local_config_path = Path.cwd() / ".maestro" / "settings.local.json"

        # Load merged config
        self.config = self._load_config()

        # Initialize audit log
        self._init_audit_log()

    def _load_config(self) -> Dict[str, Any]:
        """Load merged config from hierarchy (User < Project < Local).

        Claude Code pattern: Local overrides Project overrides User.
        """
        # Start with secure defaults (OWASP: Least Privilege)
        config = self._get_default_config()

        # Merge in order: User < Project < Local
        for path in [self.user_config_path, self.project_config_path, self.local_config_path]:
            if path.exists():
                try:
                    with open(path) as f:
                        user_config = json.load(f)
                        config = self._merge_configs(config, user_config)
                    logger.info(f"Loaded config from: {path}")
                except Exception as e:
                    logger.warning(f"Failed to load config from {path}: {e}")

        return config

    def _get_default_config(self) -> Dict[str, Any]:
        """Get secure defaults (OWASP: Deny by default, explicit allow).

        Returns:
            Default configuration with minimal safe permissions
        """
        return {
            "permissions": {
                "version": "1.0",

                # Allowlist: Safe read-only commands (OWASP: Least Privilege)
                "allow": [
                    # Process management (read-only)
                    "Bash(ps *)",
                    "Bash(top)",
                    "Bash(jobs)",
                    "Bash(bg)",
                    "Bash(fg)",

                    # Filesystem (read-only)
                    "Bash(ls *)",
                    "Bash(pwd)",
                    "Bash(find *)",
                    "Bash(tree *)",

                    # System info (read-only)
                    "Bash(whoami)",
                    "Bash(hostname)",
                    "Bash(date)",
                    "Bash(uptime)",
                    "Bash(uname *)",

                    # Git (read-only)
                    "Bash(git status)",
                    "Bash(git log *)",
                    "Bash(git diff *)",
                    "Bash(git show *)",
                    "Bash(git branch *)",

                    # Read files (non-sensitive)
                    "Read(**/*.md)",
                    "Read(**/*.txt)",
                    "Read(**/*.{js,ts,py,java,go,rs})"
                ],

                # Blocklist: Destructive operations (OWASP: Defense-in-depth)
                "deny": [
                    # System destruction
                    "Bash(rm -rf /)",
                    "Bash(rm -rf /*)",
                    "Bash(dd if=*)",
                    "Bash(mkfs.*)",
                    "Bash(:(){ :|:& };:*)",  # Fork bomb
                    "Bash(chmod -R 777 *)",

                    # Network exfiltration
                    "Bash(curl *)",
                    "Bash(wget *)",
                    "Bash(nc *)",
                    "Bash(telnet *)",

                    # Pipe to shell
                    "Bash(*| sh)",
                    "Bash(*| bash)",

                    # Sensitive files
                    "Read(.env)",
                    "Read(.env.*)",
                    "Read(**/.env)",
                    "Read(**/.env.*)",
                    "Read(**/secrets/**)",
                    "Read(**/*.pem)",
                    "Read(**/*.key)",
                    "Read(~/.ssh/**)",
                    "Read(~/.aws/**)",

                    # Write to sensitive files
                    "Write(.env*)",
                    "Write(**/secrets/**)",
                    "Write(**/*.pem)",
                    "Write(~/.ssh/**)",
                    "Edit(.env*)",
                    "Edit(**/secrets/**)"
                ],

                # Auto-approve settings
                "autoApprove": {
                    "readOnlyCommands": True,
                    "safeCommands": ["whoami", "pwd", "date", "hostname", "uname"]
                }
            },

            # Sandbox config (future feature)
            "sandbox": {
                "enabled": False,
                "warnBeforeDisable": True
            },

            # Audit logging (OWASP: Auditability)
            "logging": {
                "auditFile": str(Path.home() / ".maestro" / "audit.log"),
                "logAllDecisions": True,
                "retentionDays": 90
            }
        }

    def _merge_configs(self, base: Dict, override: Dict) -> Dict:
        """Deep merge of configs (override takes precedence).

        Args:
            base: Base configuration
            override: Override configuration

        Returns:
            Merged configuration
        """
        result = base.copy()

        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_configs(result[key], value)
            else:
                result[key] = value

        return result

    def _init_audit_log(self):
        """Initialize audit log file (OWASP: Auditability)."""
        if self.config["logging"]["logAllDecisions"]:
            audit_path = Path(self.config["logging"]["auditFile"])
            audit_path.parent.mkdir(parents=True, exist_ok=True)

            # Create if doesn't exist
            if not audit_path.exists():
                audit_path.touch()
                logger.info(f"Created audit log: {audit_path}")

    def check_permission(self, tool: str, args: Dict[str, Any]) -> Tuple[PermissionLevel, str]:
        """Check permission for tool execution.

        OWASP Pattern: Defense-in-depth
        1. Check DENY list first (highest priority - workaround Claude Code bug)
        2. Check ALLOW list
        3. Auto-approve read-only if configured
        4. Default: ASK (secure by default)

        Args:
            tool: Tool name (e.g., "Bash", "Read", "Write")
            args: Tool arguments (e.g., {"command": "ls -la"})

        Returns:
            (PermissionLevel, reason_string)
        """
        # Bypass if safe_mode disabled (--dangerously-skip-permissions)
        if not self.safe_mode:
            return PermissionLevel.ALLOW, "Safe mode disabled"

        # Format command for pattern matching
        command_str = self._format_command(tool, args)

        # Step 1: Check DENY list (highest priority)
        # Note: Check deny FIRST as workaround for Claude Code bug (v1.0.93+)
        for deny_pattern in self.config["permissions"]["deny"]:
            if self._matches_pattern(command_str, deny_pattern):
                self._audit_log("DENY", command_str, f"Matched deny pattern: {deny_pattern}")
                return PermissionLevel.DENY, f"Blocked by deny rule: {deny_pattern}"

        # Step 2: Check ALLOW list
        for allow_pattern in self.config["permissions"]["allow"]:
            if self._matches_pattern(command_str, allow_pattern):
                self._audit_log("ALLOW", command_str, f"Matched allow pattern: {allow_pattern}")
                return PermissionLevel.ALLOW, f"Approved by allow rule: {allow_pattern}"

        # Step 3: Auto-approve safe read-only operations (OWASP: Least Privilege)
        if self.config["permissions"]["autoApprove"]["readOnlyCommands"]:
            if tool == "Read":
                # Check not in sensitive paths
                path = args.get("path", args.get("file_path", ""))
                if not self._is_sensitive_path(path):
                    self._audit_log("ALLOW", command_str, "Auto-approved: safe read-only")
                    return PermissionLevel.ALLOW, "Auto-approved: safe read operation"

            elif tool == "Bash":
                command = args.get("command", "")
                if self._is_read_only_bash_command(command):
                    self._audit_log("ALLOW", command_str, "Auto-approved: read-only bash")
                    return PermissionLevel.ALLOW, "Auto-approved: read-only bash command"

        # Step 4: Default ASK (OWASP: Secure by default)
        self._audit_log("ASK", command_str, "Not in allow/deny list - requires approval")
        return PermissionLevel.ASK, "Requires user approval"

    def _format_command(self, tool: str, args: Dict[str, Any]) -> str:
        """Format tool call as string (Claude Code compatible format).

        Examples:
            - Bash(ls -la)
            - Read(src/main.py)
            - Write(config.json)

        Args:
            tool: Tool name
            args: Tool arguments

        Returns:
            Formatted command string
        """
        if tool == "Bash":
            return f"Bash({args.get('command', '')})"
        elif tool in ["Read", "Write", "Edit"]:
            path = args.get("path", args.get("file_path", ""))
            return f"{tool}({path})"
        else:
            return f"{tool}(*)"

    def _matches_pattern(self, command: str, pattern: str) -> bool:
        """Match command against pattern (Claude Code compatible).

        Supports:
        - Exact match: Bash(ls)
        - Wildcard suffix: Bash(npm run test:*)
        - Wildcard prefix: Bash(*status)
        - Glob patterns: Read(**/*.js)
        - Tool-level: Edit (matches any Edit operation)

        Args:
            command: Formatted command string
            pattern: Permission pattern

        Returns:
            True if command matches pattern
        """
        # Extract tool and args from pattern
        if "(" in pattern:
            pattern_tool, pattern_args = pattern.split("(", 1)
            pattern_args = pattern_args.rstrip(")")
        else:
            pattern_tool = pattern
            pattern_args = "*"

        # Extract tool and args from command
        if "(" in command:
            cmd_tool, cmd_args = command.split("(", 1)
            cmd_args = cmd_args.rstrip(")")
        else:
            cmd_tool = command
            cmd_args = ""

        # Match tool name
        if not fnmatch.fnmatch(cmd_tool, pattern_tool):
            return False

        # Match args with glob/wildcard
        if pattern_args == "*":
            return True

        # Use fnmatch for glob patterns
        return fnmatch.fnmatch(cmd_args, pattern_args)

    def _is_sensitive_path(self, path: str) -> bool:
        """Check if path is sensitive (credentials, secrets, etc).

        Args:
            path: File path to check

        Returns:
            True if path contains sensitive data
        """
        sensitive_patterns = [
            ".env",
            "secrets/",
            ".pem",
            ".key",
            ".ssh/",
            ".aws/",
            "credentials"
        ]

        path_lower = path.lower()
        return any(pattern in path_lower for pattern in sensitive_patterns)

    def _is_read_only_bash_command(self, command: str) -> bool:
        """Check if bash command is read-only (safe to auto-approve).

        Args:
            command: Bash command string

        Returns:
            True if command is read-only
        """
        safe_commands = self.config["permissions"]["autoApprove"]["safeCommands"]

        # Extract base command (first word)
        base_cmd = command.strip().split()[0] if command.strip() else ""

        return base_cmd in safe_commands

    def add_to_allowlist(self, pattern: str):
        """Add pattern to allowlist and persist (Claude Code "always allow").

        Args:
            pattern: Permission pattern to add (e.g., "Bash(npm run test:*)")
        """
        if pattern not in self.config["permissions"]["allow"]:
            self.config["permissions"]["allow"].append(pattern)
            self._persist_config()
            self._audit_log("CONFIG_CHANGE", pattern, "Added to allowlist via 'always allow'")
            logger.info(f"Added to allowlist: {pattern}")

    def _persist_config(self):
        """Save current config to local file (OWASP: Audit trail).

        Saves to .maestro/settings.local.json (git-ignored, per-user).
        """
        self.local_config_path.parent.mkdir(parents=True, exist_ok=True)

        with open(self.local_config_path, 'w') as f:
            json.dump(self.config, f, indent=2)

        logger.info(f"Persisted config to: {self.local_config_path}")

    def _audit_log(self, decision: str, command: str, reason: str):
        """Log permission decision to audit file (OWASP: Auditability).

        Args:
            decision: Permission decision (ALLOW/DENY/ASK/CONFIG_CHANGE)
            command: Command being evaluated
            reason: Reason for decision
        """
        if not self.config["logging"]["logAllDecisions"]:
            return

        log_entry = {
            "timestamp": datetime.datetime.now().isoformat(),
            "decision": decision,
            "command": command,
            "reason": reason
        }

        try:
            audit_path = Path(self.config["logging"]["auditFile"])
            with open(audit_path, 'a') as f:
                f.write(json.dumps(log_entry) + "\n")
        except Exception as e:
            logger.warning(f"Failed to write audit log: {e}")

    def get_config_summary(self) -> Dict[str, Any]:
        """Get summary of current configuration for display.

        Returns:
            Dict with allow/deny counts and config file locations
        """
        return {
            "allow_count": len(self.config["permissions"]["allow"]),
            "deny_count": len(self.config["permissions"]["deny"]),
            "auto_approve_enabled": self.config["permissions"]["autoApprove"]["readOnlyCommands"],
            "audit_enabled": self.config["logging"]["logAllDecisions"],
            "config_files": {
                "user": {"path": str(self.user_config_path), "exists": self.user_config_path.exists()},
                "project": {"path": str(self.project_config_path), "exists": self.project_config_path.exists()},
                "local": {"path": str(self.local_config_path), "exists": self.local_config_path.exists()}
            }
        }
