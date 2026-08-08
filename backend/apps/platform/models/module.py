from django.db import models

from core.models.base import BaseModel


class Module(BaseModel):
    """Catalog of SaaS capability modules (POS, inventory, pharmacy, …)."""

    CATEGORY_CORE = "core"
    CATEGORY_INDUSTRY = "industry"
    CATEGORY_ADDON = "addon"
    CATEGORY_CHOICES = [
        (CATEGORY_CORE, "Core"),
        (CATEGORY_INDUSTRY, "Industry"),
        (CATEGORY_ADDON, "Add-on"),
    ]

    code = models.SlugField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    category = models.CharField(
        max_length=20, choices=CATEGORY_CHOICES, default=CATEGORY_CORE, db_index=True
    )
    is_active = models.BooleanField(default=True, db_index=True)
    sort_order = models.PositiveSmallIntegerField(default=100)
    # Metadata (PHASE 03)
    route = models.CharField(max_length=100, blank=True, default="")
    dashboard_route = models.CharField(max_length=100, blank=True, default="")
    icon = models.CharField(max_length=50, blank=True, default="")
    dependencies = models.JSONField(default=list, blank=True)
    optional_dependencies = models.JSONField(default=list, blank=True)
    is_core = models.BooleanField(default=False)
    supports_mobile = models.BooleanField(default=False)
    supports_pos = models.BooleanField(default=False)
    supports_inventory = models.BooleanField(default=False)
    supports_finance = models.BooleanField(default=True)

    class Meta:
        db_table = "modules"
        ordering = ["sort_order", "name"]

    def __str__(self):
        return self.code

    def required_dependency_codes(self) -> list[str]:
        return [str(c).strip().lower() for c in (self.dependencies or []) if c]


class TenantModule(BaseModel):
    """Per-tenant enablement of a catalog Module."""

    tenant = models.ForeignKey(
        "platform.Tenant",
        on_delete=models.CASCADE,
        related_name="tenant_modules",
    )
    module = models.ForeignKey(
        Module,
        on_delete=models.CASCADE,
        related_name="tenant_links",
    )
    enabled = models.BooleanField(default=True, db_index=True)
    configuration = models.JSONField(default=dict, blank=True)
    enabled_at = models.DateTimeField(null=True, blank=True)
    enabled_by = models.ForeignKey(
        "authentication.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tenant_modules_enabled",
    )
    disabled_at = models.DateTimeField(null=True, blank=True)
    disabled_by = models.ForeignKey(
        "authentication.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tenant_modules_disabled",
    )

    class Meta:
        db_table = "tenant_modules"
        ordering = ["module__sort_order", "module__code"]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "module"],
                name="uniq_tenant_module",
            ),
        ]

    def __str__(self):
        state = "on" if self.enabled else "off"
        return f"{self.tenant_id}:{self.module.code}={state}"
