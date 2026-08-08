from django.db import models


class TenantScopedModel(models.Model):
    """Abstract mixin for tenant-owned rows (shared-schema Stage A).

    Not applied to live models in STEP 03 — opt-in during STEP 06 backfill.
    Uses nullable FK so additive migrations remain safe.
    """

    tenant = models.ForeignKey(
        "platform.Tenant",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="%(app_label)s_%(class)s_set",
        db_index=True,
    )

    class Meta:
        abstract = True


class TenantAwareQuerySet(models.QuerySet):
    """Optional filtering when tenant enforcement is enabled."""

    def for_tenant(self, tenant):
        if tenant is None:
            return self.none()
        tenant_id = getattr(tenant, "pk", None) or tenant
        return self.filter(tenant_id=tenant_id)

    def for_current_tenant(self):
        from core.tenancy import get_current_tenant, is_tenant_enforcement_enabled

        if not is_tenant_enforcement_enabled():
            return self
        tenant = get_current_tenant()
        if tenant is None:
            return self.none()
        return self.for_tenant(tenant)


class TenantAwareManager(models.Manager):
    def get_queryset(self):
        return TenantAwareQuerySet(self.model, using=self._db).for_current_tenant()

    def all_tenants(self):
        """Bypass request scoping (platform admin / migrations only)."""
        return TenantAwareQuerySet(self.model, using=self._db)

    def for_tenant(self, tenant):
        return self.all_tenants().for_tenant(tenant)
