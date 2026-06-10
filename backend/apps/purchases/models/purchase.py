from decimal import Decimal

from django.db import models
from django.utils import timezone

from core.models.base import BaseModel


class PurchaseOrder(BaseModel):
    STATUS_DRAFT = "draft"
    STATUS_ORDERED = "ordered"
    STATUS_RECEIVED = "received"
    STATUS_CANCELLED = "cancelled"

    STATUS_CHOICES = [
        (STATUS_DRAFT, "Draft"),
        (STATUS_ORDERED, "Ordered"),
        (STATUS_RECEIVED, "Received"),
        (STATUS_CANCELLED, "Cancelled"),
    ]

    order_number = models.CharField(max_length=50, db_index=True)
    supplier = models.ForeignKey("suppliers.Supplier", on_delete=models.PROTECT, related_name="purchase_orders")
    branch = models.ForeignKey("settings_app.Branch", on_delete=models.PROTECT, related_name="purchase_orders")
    ordered_by = models.ForeignKey(
        "authentication.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="purchase_orders"
    )
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default=STATUS_DRAFT, db_index=True)
    order_date = models.DateField(default=timezone.localdate)
    expected_date = models.DateField(null=True, blank=True)
    subtotal = models.DecimalField(max_digits=18, decimal_places=4, default=0)
    tax_amount = models.DecimalField(max_digits=18, decimal_places=4, default=0)
    total_amount = models.DecimalField(max_digits=18, decimal_places=4, default=0)
    notes = models.TextField(blank=True)

    class Meta:
        db_table = "purchase_orders"
        ordering = ["-order_date", "-created_at"]
        unique_together = [["branch", "order_number"]]

    def __str__(self):
        return self.order_number


class PurchaseOrderItem(BaseModel):
    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey("products.Product", on_delete=models.PROTECT, related_name="purchase_order_items")
    quantity_ordered = models.DecimalField(max_digits=18, decimal_places=4)
    quantity_received = models.DecimalField(max_digits=18, decimal_places=4, default=0)
    unit_cost = models.DecimalField(max_digits=18, decimal_places=4)
    line_total = models.DecimalField(max_digits=18, decimal_places=4, default=0)

    class Meta:
        db_table = "purchase_order_items"

    def save(self, *args, **kwargs):
        self.line_total = Decimal(str(self.quantity_ordered)) * Decimal(str(self.unit_cost))
        super().save(*args, **kwargs)
