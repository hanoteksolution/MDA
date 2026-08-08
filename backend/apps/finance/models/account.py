from django.db import models

from apps.finance.domain.account_behavior import AccountClass, is_debit_normal
from core.models.base import BaseModel
from core.models.tenant import TenantScopedModel


class Account(TenantScopedModel, BaseModel):
    """Chart of accounts row."""

    # Back-compat aliases for existing callers
    TYPE_ASSET = AccountClass.ASSET
    TYPE_LIABILITY = AccountClass.LIABILITY
    TYPE_EQUITY = AccountClass.EQUITY
    TYPE_REVENUE = AccountClass.REVENUE
    TYPE_EXPENSE = AccountClass.EXPENSE
    TYPE_CHOICES = AccountClass.choices

    code = models.CharField(max_length=20, db_index=True)
    name = models.CharField(max_length=150, db_index=True)
    account_type = models.CharField(
        max_length=20, choices=AccountClass.choices, db_index=True
    )
    parent = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="children",
    )
    is_system = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True, db_index=True)
    is_control_account = models.BooleanField(default=False, db_index=True)
    allow_manual_posting = models.BooleanField(default=True)
    description = models.TextField(blank=True)

    class Meta:
        db_table = "finance_accounts"
        ordering = ["code"]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "code"],
                condition=models.Q(deleted_at__isnull=True, tenant__isnull=False),
                name="uniq_fin_account_tenant_code",
            ),
        ]

    def __str__(self):
        return f"{self.code} {self.name}"

    @property
    def account_class(self) -> str:
        """Alias for account_type (prompt Phase 2 naming)."""
        return self.account_type

    @property
    def normal_debit(self) -> bool:
        return is_debit_normal(self.account_type)

    @property
    def normal_balance(self) -> str:
        from apps.finance.domain.account_behavior import normal_balance_for

        return normal_balance_for(self.account_type)
