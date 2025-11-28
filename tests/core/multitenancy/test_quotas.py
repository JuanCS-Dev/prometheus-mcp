"""
Tests for quota management.

SCALE & SUSTAIN Phase 3.4 validation.
"""

import pytest

from jdev_core.multitenancy import (
    Tenant,
    TenantTier,
    TenantConfig,
    QuotaManager,
    QuotaUsage,
    QuotaExceededError,
    tenant_context,
)


class TestQuotaUsage:
    """Test QuotaUsage dataclass."""

    def test_usage_percentage(self):
        """Test percentage_used calculation."""
        usage = QuotaUsage(
            quota_name="requests/minute",
            limit=100,
            used=25,
            remaining=75,
            period_start=0,
            period_end=60
        )

        assert usage.percentage_used == 25.0

    def test_usage_is_exceeded(self):
        """Test is_exceeded property."""
        usage_ok = QuotaUsage(
            quota_name="test",
            limit=10,
            used=5,
            remaining=5,
            period_start=0,
            period_end=60
        )
        assert usage_ok.is_exceeded is False

        usage_exceeded = QuotaUsage(
            quota_name="test",
            limit=10,
            used=10,
            remaining=0,
            period_start=0,
            period_end=60
        )
        assert usage_exceeded.is_exceeded is True


class TestQuotaExceededError:
    """Test QuotaExceededError exception."""

    def test_error_attributes(self):
        """Test error contains expected attributes."""
        error = QuotaExceededError(
            "Quota exceeded",
            quota_name="requests/minute",
            limit=100,
            current=150,
            reset_at=12345.0
        )

        assert error.quota_name == "requests/minute"
        assert error.limit == 100
        assert error.current == 150
        assert error.reset_at == 12345.0


class TestQuotaManager:
    """Test QuotaManager class."""

    @pytest.fixture
    def manager(self):
        """Create a test quota manager."""
        return QuotaManager()

    @pytest.fixture
    def tenant(self):
        """Create a test tenant."""
        return Tenant(
            name="TestTenant",
            tier=TenantTier.BASIC,
            config=TenantConfig.for_tier(TenantTier.BASIC)
        )

    @pytest.mark.asyncio
    async def test_check_quota_within_limit(self, manager, tenant):
        """Test check_quota returns True when within limit."""
        result = await manager.check_quota(tenant, "requests", "minute")
        assert result is True

    @pytest.mark.asyncio
    async def test_increment_quota(self, manager, tenant):
        """Test incrementing quota usage."""
        await manager.increment_quota(tenant, "requests", "minute")
        await manager.increment_quota(tenant, "requests", "minute")

        usage = await manager.get_usage(tenant, "requests", "minute")
        assert usage.used == 2

    @pytest.mark.asyncio
    async def test_quota_exceeded(self, manager):
        """Test quota exceeded scenario."""
        # Create tenant with very low limit
        config = TenantConfig(requests_per_minute=2)
        tenant = Tenant(name="Limited", config=config)

        # Use up the quota
        await manager.increment_quota(tenant, "requests", "minute")
        await manager.increment_quota(tenant, "requests", "minute")

        # Next increment should fail
        result = await manager.increment_quota(tenant, "requests", "minute")
        assert result is False

    @pytest.mark.asyncio
    async def test_require_quota_raises(self, manager):
        """Test require_quota raises when exceeded."""
        config = TenantConfig(requests_per_minute=1)
        tenant = Tenant(name="Limited", config=config)

        # Use up quota
        await manager.increment_quota(tenant, "requests", "minute")

        # Next require should raise
        with pytest.raises(QuotaExceededError) as exc_info:
            await manager.require_quota(tenant, "requests", "minute")

        assert exc_info.value.limit == 1

    @pytest.mark.asyncio
    async def test_quota_with_tenant_context(self, manager):
        """Test quota management with tenant context."""
        tenant = Tenant(
            name="ContextTenant",
            config=TenantConfig(requests_per_minute=10)
        )

        with tenant_context(tenant):
            # No need to pass tenant explicitly
            result = await manager.check_quota()
            assert result is True

            await manager.increment_quota()
            usage = await manager.get_usage()
            assert usage.used == 1

    @pytest.mark.asyncio
    async def test_get_all_usage(self, manager, tenant):
        """Test getting all quota usage."""
        await manager.increment_quota(tenant, "requests", "minute", amount=5)
        await manager.increment_quota(tenant, "requests", "hour", amount=10)

        usages = await manager.get_all_usage(tenant)

        # Should have usage entries for quotas with limits > 0
        assert len(usages) > 0

        # Find the minute quota
        minute_usage = next(
            (u for u in usages if u.quota_name == "requests/minute"),
            None
        )
        assert minute_usage is not None
        assert minute_usage.used == 5

    @pytest.mark.asyncio
    async def test_reset_quotas(self, manager, tenant):
        """Test resetting tenant quotas."""
        await manager.increment_quota(tenant, "requests", "minute", amount=10)

        await manager.reset_quotas(tenant.id)

        # After reset, usage should be 0
        usage = await manager.get_usage(tenant, "requests", "minute")
        assert usage.used == 0

    @pytest.mark.asyncio
    async def test_quota_isolation_between_tenants(self, manager):
        """Test quotas are isolated per tenant."""
        tenant1 = Tenant(
            name="Tenant1",
            config=TenantConfig(requests_per_minute=100)
        )
        tenant2 = Tenant(
            name="Tenant2",
            config=TenantConfig(requests_per_minute=100)
        )

        await manager.increment_quota(tenant1, "requests", "minute", amount=50)
        await manager.increment_quota(tenant2, "requests", "minute", amount=20)

        usage1 = await manager.get_usage(tenant1, "requests", "minute")
        usage2 = await manager.get_usage(tenant2, "requests", "minute")

        assert usage1.used == 50
        assert usage2.used == 20

    @pytest.mark.asyncio
    async def test_different_quota_periods(self, manager, tenant):
        """Test different quota periods work independently."""
        await manager.increment_quota(tenant, "requests", "minute", amount=5)
        await manager.increment_quota(tenant, "requests", "hour", amount=100)
        await manager.increment_quota(tenant, "requests", "day", amount=500)

        minute_usage = await manager.get_usage(tenant, "requests", "minute")
        hour_usage = await manager.get_usage(tenant, "requests", "hour")
        day_usage = await manager.get_usage(tenant, "requests", "day")

        assert minute_usage.used == 5
        assert hour_usage.used == 100
        assert day_usage.used == 500
