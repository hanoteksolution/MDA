from django.db import models

from core.models.base import BaseModel
from core.models.tenant import TenantScopedModel


class AccountMapping(TenantScopedModel, BaseModel):
    """Semantic account key resolved per tenant (e.g. DEFAULT_CASH → Account)."""

    mapping_key = models.CharField(max_length=50, db_index=True)
    account = models.ForeignKey(
        "finance.Account",
        on_delete=models.PROTECT,
        related_name="mappings",
    )
    business_type_code = models.CharField(max_length=50, blank=True, default="", db_index=True)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        db_table = "finance_account_mappings"
        ordering = ["mapping_key"]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "mapping_key", "business_type_code"],
                condition=models.Q(deleted_at__isnull=True, tenant__isnull=False),
                name="uniq_fin_mapping_tenant_key_bt",
            ),
        ]

    def __str__(self):
        return f"{self.mapping_key} → {self.account.code}"
