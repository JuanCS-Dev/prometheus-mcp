"""
Tenant Isolation.

SCALE & SUSTAIN Phase 3.4 - Multi-Tenant.

Resource isolation and access control.

Author: JuanCS Dev
Date: 2025-11-26
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from .context import get_current_tenant, TenantContext
from .tenant import Tenant


class IsolationLevel(Enum):
    """Level of tenant isolation."""

    NONE = "none"  # No isolation (single tenant)
    LOGICAL = "logical"  # Same infrastructure, logical separation
    PHYSICAL = "physical"  # Separate infrastructure per tenant


class ResourceScope(Enum):
    """Scope of a resource."""

    GLOBAL = "global"  # Shared across all tenants
    TENANT = "tenant"  # Isolated per tenant
    USER = "user"  # Isolated per user within tenant


@dataclass
class TenantIsolation:
    """
    Manages tenant isolation and access control.

    Ensures resources are properly scoped and access is controlled.
    """

    level: IsolationLevel = IsolationLevel.LOGICAL
    _resource_registry: Dict[str, ResourceScope] = field(default_factory=dict)
    _tenant_resources: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    _access_policies: Dict[str, Callable[[TenantContext, str], bool]] = field(default_factory=dict)

    def register_resource(
        self,
        resource_type: str,
        scope: ResourceScope
    ) -> None:
        """
        Register a resource type with its scope.

        Args:
            resource_type: Type of resource (e.g., "sessions", "cache")
            scope: Isolation scope for this resource
        """
        self._resource_registry[resource_type] = scope

    def get_scope(self, resource_type: str) -> ResourceScope:
        """Get the scope for a resource type."""
        return self._resource_registry.get(resource_type, ResourceScope.TENANT)

    def get_resource_key(
        self,
        resource_type: str,
        resource_id: str,
        tenant: Optional[Tenant] = None,
        user_id: Optional[str] = None
    ) -> str:
        """
        Get the scoped key for a resource.

        Args:
            resource_type: Type of resource
            resource_id: Resource identifier
            tenant: Tenant (uses current if not provided)
            user_id: User ID for user-scoped resources

        Returns:
            Scoped resource key
        """
        scope = self.get_scope(resource_type)

        if scope == ResourceScope.GLOBAL:
            return f"global:{resource_type}:{resource_id}"

        # Get tenant from context if not provided
        if tenant is None:
            ctx = get_current_tenant()
            if ctx:
                tenant = ctx.tenant
                user_id = user_id or ctx.user_id

        if tenant is None:
            raise RuntimeError("No tenant context for tenant-scoped resource")

        if scope == ResourceScope.TENANT:
            return f"tenant:{tenant.id}:{resource_type}:{resource_id}"
        elif scope == ResourceScope.USER:
            if user_id is None:
                raise RuntimeError("No user ID for user-scoped resource")
            return f"user:{tenant.id}:{user_id}:{resource_type}:{resource_id}"

        return f"{resource_type}:{resource_id}"

    def store_resource(
        self,
        resource_type: str,
        resource_id: str,
        value: Any,
        tenant: Optional[Tenant] = None,
        user_id: Optional[str] = None
    ) -> str:
        """
        Store a resource with proper scoping.

        Returns:
            Scoped resource key
        """
        key = self.get_resource_key(resource_type, resource_id, tenant, user_id)

        # Get tenant ID for storage
        if tenant:
            tenant_id = tenant.id
        else:
            ctx = get_current_tenant()
            tenant_id = ctx.tenant.id if ctx else "global"

        if tenant_id not in self._tenant_resources:
            self._tenant_resources[tenant_id] = {}

        self._tenant_resources[tenant_id][key] = value
        return key

    def get_resource(
        self,
        resource_type: str,
        resource_id: str,
        tenant: Optional[Tenant] = None,
        user_id: Optional[str] = None
    ) -> Optional[Any]:
        """
        Get a resource with proper scoping.

        Returns:
            Resource value or None if not found
        """
        key = self.get_resource_key(resource_type, resource_id, tenant, user_id)

        # Get tenant ID for lookup
        if tenant:
            tenant_id = tenant.id
        else:
            ctx = get_current_tenant()
            tenant_id = ctx.tenant.id if ctx else "global"

        return self._tenant_resources.get(tenant_id, {}).get(key)

    def delete_resource(
        self,
        resource_type: str,
        resource_id: str,
        tenant: Optional[Tenant] = None,
        user_id: Optional[str] = None
    ) -> bool:
        """
        Delete a resource.

        Returns:
            True if deleted, False if not found
        """
        key = self.get_resource_key(resource_type, resource_id, tenant, user_id)

        if tenant:
            tenant_id = tenant.id
        else:
            ctx = get_current_tenant()
            tenant_id = ctx.tenant.id if ctx else "global"

        if tenant_id in self._tenant_resources:
            if key in self._tenant_resources[tenant_id]:
                del self._tenant_resources[tenant_id][key]
                return True
        return False

    def list_resources(
        self,
        resource_type: str,
        tenant: Optional[Tenant] = None
    ) -> List[str]:
        """
        List all resources of a type for a tenant.

        Returns:
            List of resource keys
        """
        if tenant:
            tenant_id = tenant.id
        else:
            ctx = get_current_tenant()
            tenant_id = ctx.tenant.id if ctx else "global"

        prefix = f"tenant:{tenant_id}:{resource_type}:"
        resources = self._tenant_resources.get(tenant_id, {})
        return [k for k in resources.keys() if k.startswith(prefix)]

    def purge_tenant(self, tenant_id: str) -> int:
        """
        Purge all resources for a tenant.

        Returns:
            Number of resources purged
        """
        if tenant_id in self._tenant_resources:
            count = len(self._tenant_resources[tenant_id])
            del self._tenant_resources[tenant_id]
            return count
        return 0

    def register_access_policy(
        self,
        resource_type: str,
        policy: Callable[[TenantContext, str], bool]
    ) -> None:
        """
        Register an access policy for a resource type.

        Args:
            resource_type: Type of resource
            policy: Function(context, resource_id) -> bool
        """
        self._access_policies[resource_type] = policy

    def check_access(
        self,
        resource_type: str,
        resource_id: str,
        context: Optional[TenantContext] = None
    ) -> bool:
        """
        Check if current context has access to a resource.

        Args:
            resource_type: Type of resource
            resource_id: Resource identifier
            context: Tenant context (uses current if not provided)

        Returns:
            True if access is allowed
        """
        if context is None:
            context = get_current_tenant()

        if context is None:
            # No context, check if resource is global
            scope = self.get_scope(resource_type)
            return scope == ResourceScope.GLOBAL

        # Check custom policy if registered
        if resource_type in self._access_policies:
            return self._access_policies[resource_type](context, resource_id)

        # Default: allow access to own tenant's resources
        return context.is_active


def require_access(resource_type: str, resource_id: str) -> None:
    """
    Decorator helper to require access to a resource.

    Raises:
        PermissionError: If access is denied
    """
    isolation = get_tenant_isolation()
    if not isolation.check_access(resource_type, resource_id):
        raise PermissionError(
            f"Access denied to {resource_type}:{resource_id}"
        )


# Global isolation instance
_global_isolation: Optional[TenantIsolation] = None


def get_tenant_isolation() -> TenantIsolation:
    """Get global tenant isolation manager."""
    global _global_isolation
    if _global_isolation is None:
        _global_isolation = TenantIsolation()
    return _global_isolation


__all__ = [
    'TenantIsolation',
    'IsolationLevel',
    'ResourceScope',
    'require_access',
    'get_tenant_isolation',
]
