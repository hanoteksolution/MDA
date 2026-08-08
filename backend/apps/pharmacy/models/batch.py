from django.db import models

from core.models.base import BaseModel
from core.models.tenant import TenantScopedModel


class ProductBatch(TenantScopedModel, BaseModel):
    """Lot/batch for pharmacy (and other expiry-tracked) stock."""

    product = models.ForeignKey(
        "products.Product",
        on_delete=models.CASCADE,
        related_name="batches",
    )
    warehouse = models.ForeignKey(
        "inventory.Warehouse",
        on_delete=models.CASCADE,
        related_name="product_batches",
    )
    batch_number = models.CharField(max_length=100, db_index=True)
    manufacturing_date = models.DateField(null=True, blank=True)
    expiry_date = models.DateField(null=True, blank=True, db_index=True)
    quantity = models.DecimalField(max_digits=18, decimal_places=4, default=0)
    cost_price = models.DecimalField(max_digits=18, decimal_places=4, null=True, blank=True)
    is_active = models.BooleanField(default=True, db_index=True)
    notes = models.TextField(blank=True)

    class Meta:
        db_table = "product_batches"
        ordering = ["expiry_date", "batch_number"]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "product", "warehouse", "batch_number"],
                condition=models.Q(deleted_at__isnull=True, tenant__isnull=False),
                name="uniq_batch_tenant_product_wh_number",
            ),
        ]

    def __str__(self):
        return f"{self.product_id}:{self.batch_number}"


class BatchDispense(BaseModel):
    """Audit of FEFO allocations against a sale/invoice reference."""

    batch = models.ForeignKey(
        ProductBatch,
        on_delete=models.PROTECT,
        related_name="dispenses",
    )
    quantity = models.DecimalField(max_digits=18, decimal_places=4)
    reference_type = models.CharField(max_length=50, default="invoice", db_index=True)
    reference_id = models.UUIDField(null=True, blank=True, db_index=True)
    notes = models.TextField(blank=True)

    class Meta:
        db_table = "batch_dispenses"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.batch_id}:{self.quantity}"
