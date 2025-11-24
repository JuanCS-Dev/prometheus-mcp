"""
╔══════════════════════════════════════════════════════════════════════════════════╗
║                                                                                  ║
║                        AGENT IDENTITY & IAM                                      ║
║                                                                                  ║
║  First-class IAM principals for agents (Google Vertex AI pattern)              ║
║                                                                                  ║
║  Based on Nov 2025 best practices:                                              ║
║  - Google: "Agent identities are native identities within Google Cloud.        ║
║            As first-class IAM principals, agent identities allow you to         ║
║            enforce true least-privilege access"                                 ║
║                                                                                  ║
║  Features:                                                                       ║
║  - Least-privilege access enforcement                                            ║
║  - Granular permission model                                                     ║
║  - Resource boundaries                                                           ║
║  - Compliance-ready                                                              ║
║                                                                                  ║
╚══════════════════════════════════════════════════════════════════════════════════╝
"""

from enum import Enum
from typing import Set, Dict, Optional
from dataclasses import dataclass, field
from types import MappingProxyType

from qwen_dev_cli.agents.base import AgentRole


class AgentPermission(str, Enum):
    """
    Granular permissions for agents (least-privilege model).

    Based on Google Cloud IAM pattern: each agent has minimal permissions
    required for its specific function.
    """

    # File operations
    READ_FILES = "read_files"
    WRITE_FILES = "write_files"
    DELETE_FILES = "delete_files"

    # Execution
    EXECUTE_COMMANDS = "execute_commands"
    SPAWN_PROCESSES = "spawn_processes"

    # Network
    NETWORK_ACCESS = "network_access"
    EXTERNAL_API_CALLS = "external_api_calls"

    # Security
    READ_SECRETS = "read_secrets"
    MANAGE_SECRETS = "manage_secrets"

    # Governance (Justiça only)
    EVALUATE_GOVERNANCE = "evaluate_governance"
    BLOCK_ACTIONS = "block_actions"
    MANAGE_TRUST_SCORES = "manage_trust_scores"

    # Counsel (Sofia only)
    PROVIDE_COUNSEL = "provide_counsel"
    ACCESS_ETHICAL_KNOWLEDGE = "access_ethical_knowledge"

    # Orchestration (Maestro only)
    ROUTE_REQUESTS = "route_requests"
    DELEGATE_TASKS = "delegate_tasks"
    READ_AGENT_STATE = "read_agent_state"


@dataclass
class AgentIdentity:
    """
    First-class IAM principal for an agent.

    Represents agent as a security principal with:
    - Unique identity
    - Role (defines purpose)
    - Permissions (least-privilege)
    - Resource boundaries

    Example:
        >>> identity = AgentIdentity(
        ...     agent_id="governance",
        ...     role=AgentRole.GOVERNANCE,
        ...     permissions={AgentPermission.EVALUATE_GOVERNANCE}
        ... )
        >>> identity.can(AgentPermission.WRITE_FILES)  # False
        >>> identity.enforce(AgentPermission.EVALUATE_GOVERNANCE)  # OK
    """

    agent_id: str
    role: AgentRole
    permissions: Set[AgentPermission]
    description: str = ""
    resource_boundaries: Dict[str, str] = field(default_factory=dict)

    def can(self, permission: AgentPermission) -> bool:
        """
        Check if agent has a specific permission.

        Args:
            permission: The permission to check

        Returns:
            bool: True if agent has permission

        Example:
            >>> if identity.can(AgentPermission.WRITE_FILES):
            ...     write_file()
        """
        return permission in self.permissions

    def enforce(self, permission: AgentPermission) -> None:
        """
        Enforce that agent has permission (raise if not).

        Args:
            permission: Required permission

        Raises:
            PermissionError: If agent lacks permission

        Example:
            >>> identity.enforce(AgentPermission.WRITE_FILES)
            PermissionError: Agent governance (GOVERNANCE) lacks permission: write_files
        """
        if not self.can(permission):
            raise PermissionError(
                f"Agent {self.agent_id} ({self.role.value}) lacks permission: {permission.value}"
            )

    def add_permission(self, permission: AgentPermission) -> None:
        """Add a permission to this agent (runtime elevation)."""
        self.permissions.add(permission)

    def remove_permission(self, permission: AgentPermission) -> None:
        """Remove a permission from this agent."""
        self.permissions.discard(permission)

    def get_permissions_list(self) -> list[str]:
        """Get list of permission strings."""
        return [p.value for p in self.permissions]


# ════════════════════════════════════════════════════════════════════════════════
# PREDEFINED AGENT IDENTITIES (Based on Research)
# ════════════════════════════════════════════════════════════════════════════════

# 🔒 SECURITY FIX (AIR GAP #38): Make AGENT_IDENTITIES immutable
# Using MappingProxyType to prevent mutation attacks like:
#   AGENT_IDENTITIES.clear()
#   AGENT_IDENTITIES["executor"] = malicious_identity
#
# Internal mutable dict (private, not exported)
_AGENT_IDENTITIES_INTERNAL: Dict[str, AgentIdentity] = {
    # Maestro: Orchestrator with "read and route" permissions (Anthropic pattern)
    "maestro": AgentIdentity(
        agent_id="maestro",
        role=AgentRole.PLANNER,  # Using PLANNER as orchestrator role
        permissions={
            AgentPermission.READ_FILES,
            AgentPermission.ROUTE_REQUESTS,
            AgentPermission.DELEGATE_TASKS,
            AgentPermission.READ_AGENT_STATE,
        },
        description="Lead orchestrator agent - read and route only",
        resource_boundaries={"scope": "orchestration"}
    ),

    # Justiça: Governance with evaluation permissions only
    "governance": AgentIdentity(
        agent_id="governance",
        role=AgentRole.GOVERNANCE,
        permissions={
            AgentPermission.READ_FILES,
            AgentPermission.EVALUATE_GOVERNANCE,
            AgentPermission.BLOCK_ACTIONS,
            AgentPermission.MANAGE_TRUST_SCORES,
        },
        description="Constitutional governance agent - evaluation and blocking",
        resource_boundaries={"scope": "governance"}
    ),

    # Sofia: Counselor with counsel permissions only
    "counselor": AgentIdentity(
        agent_id="counselor",
        role=AgentRole.COUNSELOR,
        permissions={
            AgentPermission.READ_FILES,
            AgentPermission.PROVIDE_COUNSEL,
            AgentPermission.ACCESS_ETHICAL_KNOWLEDGE,
        },
        description="Wise counselor agent - guidance and deliberation",
        resource_boundaries={"scope": "counsel"}
    ),

    # Executor: Command execution agent with bash/shell permissions
    "executor": AgentIdentity(
        agent_id="executor",
        role=AgentRole.EXECUTOR,
        permissions={
            AgentPermission.READ_FILES,
            AgentPermission.EXECUTE_COMMANDS,
            AgentPermission.SPAWN_PROCESSES,
            AgentPermission.NETWORK_ACCESS,
        },
        description="Command execution agent - bash and shell operations",
        resource_boundaries={"scope": "execution", "timeout": "30s", "max_retries": "3"}
    ),

    # Architect: Architecture and design agent
    "architect": AgentIdentity(
        agent_id="architect",
        role=AgentRole.ARCHITECT,
        permissions={
            AgentPermission.READ_FILES,
            AgentPermission.WRITE_FILES,
            AgentPermission.NETWORK_ACCESS,
        },
        description="Architecture agent - design and implementation",
        resource_boundaries={"scope": "architecture", "max_file_size": "10MB"}
    ),

    # Explorer: Read-only discovery agent
    "explorer": AgentIdentity(
        agent_id="explorer",
        role=AgentRole.EXPLORER,
        permissions={
            AgentPermission.READ_FILES,
        },
        description="Codebase explorer - read-only access",
        resource_boundaries={"scope": "read-only"}
    ),

    # Reviewer: Code review agent
    "reviewer": AgentIdentity(
        agent_id="reviewer",
        role=AgentRole.REVIEWER,
        permissions={
            AgentPermission.READ_FILES,
            AgentPermission.WRITE_FILES,  # For review comments
        },
        description="Code reviewer - read and comment",
        resource_boundaries={"scope": "review"}
    ),
}

# 🔒 Public immutable proxy (read-only access)
# This prevents mutation attacks while allowing read access
AGENT_IDENTITIES: MappingProxyType = MappingProxyType(_AGENT_IDENTITIES_INTERNAL)


def get_agent_identity(agent_id: str) -> Optional[AgentIdentity]:
    """
    Get identity for an agent.

    Args:
        agent_id: Agent identifier

    Returns:
        AgentIdentity or None if not found

    Example:
        >>> identity = get_agent_identity("governance")
        >>> identity.can(AgentPermission.EVALUATE_GOVERNANCE)
        True
    """
    # 🔒 SECURITY FIX (AIR GAP #35): Validate agent_id type
    if not isinstance(agent_id, str):
        raise TypeError(f"agent_id must be str, got {type(agent_id).__name__}")

    return AGENT_IDENTITIES.get(agent_id)


def register_agent_identity(identity: AgentIdentity) -> None:
    """
    Register a new agent identity at runtime.

    Args:
        identity: The AgentIdentity to register

    Example:
        >>> custom = AgentIdentity(
        ...     agent_id="custom-agent",
        ...     role=AgentRole.EXECUTOR,
        ...     permissions={AgentPermission.READ_FILES}
        ... )
        >>> register_agent_identity(custom)
    """
    # 🔒 SECURITY FIX (AIR GAP #38): Register to internal dict
    # AGENT_IDENTITIES is immutable, so we modify the internal dict
    _AGENT_IDENTITIES_INTERNAL[identity.agent_id] = identity


def list_agent_identities() -> Dict[str, AgentIdentity]:
    """Get all registered agent identities."""
    # 🔒 SECURITY FIX (AIR GAP #38): Return copy of internal dict
    return _AGENT_IDENTITIES_INTERNAL.copy()


def check_permission(agent_id: str, permission: AgentPermission) -> bool:
    """
    Check if agent has permission (convenience function).

    Args:
        agent_id: Agent to check
        permission: Permission to verify

    Returns:
        bool: True if agent has permission, False otherwise

    Example:
        >>> if check_permission("governance", AgentPermission.WRITE_FILES):
        ...     # This will be False
        ...     write_file()
    """
    identity = get_agent_identity(agent_id)
    if identity is None:
        return False
    return identity.can(permission)


def enforce_permission(agent_id: str, permission: AgentPermission) -> None:
    """
    Enforce permission (raise if agent lacks it).

    Args:
        agent_id: Agent to check
        permission: Required permission

    Raises:
        PermissionError: If agent lacks permission
        ValueError: If agent not found

    Example:
        >>> enforce_permission("governance", AgentPermission.EVALUATE_GOVERNANCE)
        # OK
        >>> enforce_permission("governance", AgentPermission.WRITE_FILES)
        PermissionError: Agent governance (GOVERNANCE) lacks permission: write_files
    """
    identity = get_agent_identity(agent_id)
    if identity is None:
        raise ValueError(f"Agent identity not found: {agent_id}")
    identity.enforce(permission)
