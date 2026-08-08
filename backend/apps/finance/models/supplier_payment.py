from django.db import models
from django.utils import timezone

from core.models.base import BaseModel
from core.models.tenant import TenantScopedModel


class SupplierPayment(TenantScopedModel, BaseModel):
    """Payment voucher applied against a purchase order (settles AP)."""

    METHOD_CASH = "cash"
    METHOD_MOBILE = "mobile"
    METHOD_CARD = "card"
    METHOD_BANK = "bank"
    METHOD_OTHER = "other"
    METHOD_CHOICES = [
        (METHOD_CASH, "Cash"),
        (METHOD_MOBILE, "Mobile money"),
        (METHOD_CARD, "Card"),
        (METHOD_BANK, "Bank"),
        (METHOD_OTHER, "Other"),
    ]

    purchase_order = models.ForeignKey(
        "purchases.PurchaseOrder",
        on_delete=models.PROTECT,
        related_name="supplier_payments",
    )
    branch = models.ForeignKey(
        "settings_app.Branch",
        on_delete=models.PROTECT,
        related_name="supplier_payments",
    )
    method = models.CharField(max_length=30, choices=METHOD_CHOICES, db_index=True)
    amount = models.DecimalField(max_digits=18, decimal_places=4)
    reference = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    paid_at = models.DateTimeField(default=timezone.now, db_index=True)
    paid_by = models.ForeignKey(
        "authentication.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="supplier_payments_made",
    )

    class Meta:
        db_table = "finance_supplier_payments"
        ordering = ["-paid_at", "-created_at"]

    def __str__(self):
        return f"SP:{self.amount}→{self.purchase_order_id}"
