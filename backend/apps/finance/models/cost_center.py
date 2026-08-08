from django.db import models

from core.models.base import BaseModel
from core.models.tenant import TenantScopedModel


class CostCenter(TenantScopedModel, BaseModel):
    """Optional dimension for journal lines (department / location / project)."""

    code = models.CharField(max_length=30, db_index=True)
    name = models.CharField(max_length=150)
    parent = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="children",
    )
    is_active = models.BooleanField(default=True, db_index=True)
    description = models.TextField(blank=True)

    class Meta:
        db_table = "finance_cost_centers"
        ordering = ["code"]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "code"],
                condition=models.Q(deleted_at__isnull=True, tenant__isnull=False),
                name="uniq_fin_cost_center_tenant_code",
            ),
        ]

    def __str__(self):
        return f"{self.code} {self.name}"
