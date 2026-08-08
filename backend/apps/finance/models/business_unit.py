from django.db import models

from core.models.base import BaseModel
from core.models.tenant import TenantScopedModel


class BusinessUnit(TenantScopedModel, BaseModel):
    """P&L slice dimension (Gym vs Hotel vs Retail) — not a separate ledger."""

    code = models.CharField(max_length=30, db_index=True)
    name = models.CharField(max_length=150)
    module_code = models.CharField(
        max_length=60,
        blank=True,
        db_index=True,
        help_text="Optional platform module this unit represents (gym, hotel, …).",
    )
    is_active = models.BooleanField(default=True, db_index=True)
    description = models.TextField(blank=True)
    sort_order = models.PositiveIntegerField(default=100)

    class Meta:
        db_table = "finance_business_units"
        ordering = ["sort_order", "code"]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "code"],
                condition=models.Q(deleted_at__isnull=True, tenant__isnull=False),
                name="uniq_fin_bu_tenant_code",
            ),
        ]

    def __str__(self):
        return f"{self.code} {self.name}"
