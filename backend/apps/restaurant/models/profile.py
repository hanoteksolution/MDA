"""Cafeteria workspace profile — tenant/branch configuration over restaurant engine."""

from django.db import models

from core.models.base import BaseModel
from core.models.tenant import TenantScopedModel


class CafeteriaProfile(TenantScopedModel, BaseModel):
    """One active cafeteria/café profile per branch."""

    MODE_BOTH = "both"
    MODE_BARISTA = "barista"
    MODE_KITCHEN = "kitchen"
    MODE_CHOICES = [
        (MODE_BOTH, "Barista + Kitchen"),
        (MODE_BARISTA, "Barista only"),
        (MODE_KITCHEN, "Kitchen only"),
    ]

    branch = models.ForeignKey(
        "settings_app.Branch",
        on_delete=models.CASCADE,
        related_name="cafeteria_profiles",
    )
    business_name = models.CharField(max_length=255)
    trading_name = models.CharField(max_length=255, blank=True)
    logo_url = models.CharField(max_length=500, blank=True)
    phone = models.CharField(max_length=50, blank=True)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    currency = models.CharField(max_length=8, default="USD")
    timezone = models.CharField(max_length=64, default="UTC")
    language = models.CharField(max_length=16, default="en")
    receipt_header = models.TextField(blank=True)
    receipt_footer = models.TextField(blank=True)
    order_prefix = models.CharField(max_length=20, default="CF")
    invoice_prefix = models.CharField(max_length=20, default="INV-CF")
    kitchen_barista_mode = models.CharField(
        max_length=20, choices=MODE_CHOICES, default=MODE_BOTH
    )
    table_service_enabled = models.BooleanField(default=True)
    takeaway_enabled = models.BooleanField(default=True)
    delivery_enabled = models.BooleanField(default=False)
    reservations_enabled = models.BooleanField(default=False)
    tips_enabled = models.BooleanField(default=True)
    service_charge_enabled = models.BooleanField(default=False)
    loyalty_enabled = models.BooleanField(default=False)
    recipe_deduction_enabled = models.BooleanField(default=True)
    negative_stock_allowed = models.BooleanField(default=False)
    default_warehouse = models.ForeignKey(
        "inventory.Warehouse",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="cafeteria_profiles",
    )
    default_cash_account_id = models.UUIDField(null=True, blank=True)
    default_sales_account_id = models.UUIDField(null=True, blank=True)
    default_inventory_account_id = models.UUIDField(null=True, blank=True)
    default_cogs_account_id = models.UUIDField(null=True, blank=True)
    settings = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "restaurant_cafeteria_profiles"
        ordering = ["business_name"]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "branch"],
                condition=models.Q(deleted_at__isnull=True, tenant__isnull=False),
                name="uniq_cafeteria_profile_tenant_branch",
            ),
        ]

    def __str__(self):
        return self.business_name or self.trading_name or str(self.branch_id)
