"""
Quota Management.

SCALE & SUSTAIN Phase 3.4 - Multi-Tenant.

Rate limiting and quota management per tenant.

Author: JuanCS Dev
Date: 2025-11-26
"""

import asyncio
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional

from .context import get_current_tenant
from .tenant import Tenant, TenantConfig


class QuotaExceededError(Exception):
    """Raised when a quota is exceeded."""

    def __init__(
        self,
        message: str,
        quota_name: str,
        limit: int,
        current: int,
        reset_at: Optional[float] = None
    ):
        super().__init__(message)
        self.quota_name = quota_name
        self.limit = limit
        self.current = current
        self.reset_at = reset_at


class QuotaPeriod(Enum):
    """Quota time period."""

    MINUTE = 60
    HOUR = 3600
    DAY = 86400
    MONTH = 2592000  # 30 days


@dataclass
class Quota:
    """Quota definition."""

    name: str
    limit: int
    period: QuotaPeriod
    description: str = ""


@dataclass
class QuotaUsage:
    """Current quota usage."""

    quota_name: str
    limit: int
    used: int
    remaining: int
    period_start: float
    period_end: float

    @property
    def percentage_used(self) -> float:
        """Get percentage of quota used."""
        if self.limit == 0:
            return 0.0
        return (self.used / self.limit) * 100

    @property
    def is_exceeded(self) -> bool:
        """Check if quota is exceeded."""
        return self.used >= self.limit

    @property
    def seconds_until_reset(self) -> float:
        """Seconds until quota resets."""
        return max(0, self.period_end - time.time())


@dataclass
class QuotaBucket:
    """Time-windowed quota bucket."""

    limit: int
    period: float
    count: int = 0
    window_start: float = field(default_factory=time.time)

    def check(self) -> bool:
        """Check if within quota."""
        self._maybe_reset()
        return self.count < self.limit

    def increment(self, amount: int = 1) -> bool:
        """
        Increment usage and check quota.

        Returns:
            True if within quota, False if exceeded
        """
        self._maybe_reset()
        if self.count + amount > self.limit:
            return False
        self.count += amount
        return True

    def _maybe_reset(self) -> None:
        """Reset bucket if period has elapsed."""
        now = time.time()
        if now - self.window_start >= self.period:
            self.count = 0
            self.window_start = now

    def get_usage(self) -> QuotaUsage:
        """Get current usage stats."""
        self._maybe_reset()
        return QuotaUsage(
            quota_name="",
            limit=self.limit,
            used=self.count,
            remaining=max(0, self.limit - self.count),
            period_start=self.window_start,
            period_end=self.window_start + self.period
        )


class QuotaManager:
    """
    Manages quotas and rate limits for tenants.

    Usage:
        manager = QuotaManager()

        # Check quota before operation
        if await manager.check_quota(tenant, "requests", "minute"):
            # Perform operation
            await manager.increment_quota(tenant, "requests", "minute")
    """

    def __init__(self):
        self._tenant_quotas: Dict[str, Dict[str, QuotaBucket]] = {}
        self._lock = asyncio.Lock()

    def _get_bucket_key(self, quota_name: str, period: str) -> str:
        """Get bucket key for a quota and period."""
        return f"{quota_name}:{period}"

    def _get_tenant_buckets(self, tenant_id: str) -> Dict[str, QuotaBucket]:
        """Get or create quota buckets for a tenant."""
        if tenant_id not in self._tenant_quotas:
            self._tenant_quotas[tenant_id] = {}
        return self._tenant_quotas[tenant_id]

    def _get_limit(
        self,
        config: TenantConfig,
        quota_name: str,
        period: str
    ) -> int:
        """Get limit from tenant config."""
        limits = {
            ("requests", "minute"): config.requests_per_minute,
            ("requests", "hour"): config.requests_per_hour,
            ("requests", "day"): config.requests_per_day,
            ("tokens", "month"): config.monthly_token_quota,
            ("requests", "month"): config.monthly_request_quota,
        }
        return limits.get((quota_name, period), 0)

    def _get_period_seconds(self, period: str) -> float:
        """Get period duration in seconds."""
        periods = {
            "minute": QuotaPeriod.MINUTE.value,
            "hour": QuotaPeriod.HOUR.value,
            "day": QuotaPeriod.DAY.value,
            "month": QuotaPeriod.MONTH.value,
        }
        return periods.get(period, 60)

    async def check_quota(
        self,
        tenant: Optional[Tenant] = None,
        quota_name: str = "requests",
        period: str = "minute"
    ) -> bool:
        """
        Check if tenant is within quota.

        Args:
            tenant: Tenant to check (uses current if not provided)
            quota_name: Name of quota to check
            period: Time period (minute, hour, day, month)

        Returns:
            True if within quota
        """
        if tenant is None:
            ctx = get_current_tenant()
            if ctx is None:
                return True  # No tenant context, allow
            tenant = ctx.tenant

        async with self._lock:
            buckets = self._get_tenant_buckets(tenant.id)
            key = self._get_bucket_key(quota_name, period)

            if key not in buckets:
                limit = self._get_limit(tenant.config, quota_name, period)
                period_seconds = self._get_period_seconds(period)
                buckets[key] = QuotaBucket(limit=limit, period=period_seconds)

            return buckets[key].check()

    async def increment_quota(
        self,
        tenant: Optional[Tenant] = None,
        quota_name: str = "requests",
        period: str = "minute",
        amount: int = 1
    ) -> bool:
        """
        Increment quota usage.

        Args:
            tenant: Tenant to increment (uses current if not provided)
            quota_name: Name of quota
            period: Time period
            amount: Amount to increment

        Returns:
            True if increment succeeded (within quota)
        """
        if tenant is None:
            ctx = get_current_tenant()
            if ctx is None:
                return True
            tenant = ctx.tenant

        async with self._lock:
            buckets = self._get_tenant_buckets(tenant.id)
            key = self._get_bucket_key(quota_name, period)

            if key not in buckets:
                limit = self._get_limit(tenant.config, quota_name, period)
                period_seconds = self._get_period_seconds(period)
                buckets[key] = QuotaBucket(limit=limit, period=period_seconds)

            return buckets[key].increment(amount)

    async def require_quota(
        self,
        tenant: Optional[Tenant] = None,
        quota_name: str = "requests",
        period: str = "minute"
    ) -> None:
        """
        Require quota to be available, raising if exceeded.

        Raises:
            QuotaExceededError: If quota is exceeded
        """
        if not await self.check_quota(tenant, quota_name, period):
            if tenant is None:
                ctx = get_current_tenant()
                if ctx:
                    tenant = ctx.tenant

            usage = await self.get_usage(tenant, quota_name, period)
            raise QuotaExceededError(
                f"Quota exceeded for {quota_name}/{period}",
                quota_name=f"{quota_name}/{period}",
                limit=usage.limit,
                current=usage.used,
                reset_at=usage.period_end
            )

    async def get_usage(
        self,
        tenant: Optional[Tenant] = None,
        quota_name: str = "requests",
        period: str = "minute"
    ) -> QuotaUsage:
        """
        Get current quota usage.

        Returns:
            QuotaUsage with current stats
        """
        if tenant is None:
            ctx = get_current_tenant()
            if ctx is None:
                return QuotaUsage(
                    quota_name=f"{quota_name}/{period}",
                    limit=0,
                    used=0,
                    remaining=0,
                    period_start=time.time(),
                    period_end=time.time()
                )
            tenant = ctx.tenant

        async with self._lock:
            buckets = self._get_tenant_buckets(tenant.id)
            key = self._get_bucket_key(quota_name, period)

            if key not in buckets:
                limit = self._get_limit(tenant.config, quota_name, period)
                period_seconds = self._get_period_seconds(period)
                buckets[key] = QuotaBucket(limit=limit, period=period_seconds)

            usage = buckets[key].get_usage()
            usage.quota_name = f"{quota_name}/{period}"
            return usage

    async def get_all_usage(
        self,
        tenant: Optional[Tenant] = None
    ) -> List[QuotaUsage]:
        """
        Get all quota usage for a tenant.

        Returns:
            List of QuotaUsage for all quotas
        """
        if tenant is None:
            ctx = get_current_tenant()
            if ctx is None:
                return []
            tenant = ctx.tenant

        usages = []
        for quota_name in ["requests", "tokens"]:
            for period in ["minute", "hour", "day", "month"]:
                usage = await self.get_usage(tenant, quota_name, period)
                if usage.limit > 0:
                    usages.append(usage)

        return usages

    async def reset_quotas(self, tenant_id: str) -> None:
        """Reset all quotas for a tenant."""
        async with self._lock:
            if tenant_id in self._tenant_quotas:
                del self._tenant_quotas[tenant_id]


# Global quota manager
_global_quota_manager: Optional[QuotaManager] = None


def get_quota_manager() -> QuotaManager:
    """Get global quota manager."""
    global _global_quota_manager
    if _global_quota_manager is None:
        _global_quota_manager = QuotaManager()
    return _global_quota_manager


__all__ = [
    'QuotaManager',
    'Quota',
    'QuotaUsage',
    'QuotaExceededError',
    'QuotaPeriod',
    'get_quota_manager',
]
