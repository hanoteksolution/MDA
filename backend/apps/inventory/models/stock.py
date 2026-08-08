from django.db import models

from core.models.base import BaseModel
from core.models.tenant import TenantScopedModel


class Warehouse(TenantScopedModel, BaseModel):
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=50, db_index=True)
    branch = models.ForeignKey(
        "settings_app.Branch", on_delete=models.CASCADE, related_name="warehouses"
    )
    address = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    is_default = models.BooleanField(default=False)

    class Meta:
        db_table = "warehouses"
        unique_together = ["branch", "code"]
        ordering = ["name"]

    def __str__(self):
        return self.name


class Inventory(TenantScopedModel, BaseModel):
    product = models.ForeignKey(
        "products.Product", on_delete=models.CASCADE, related_name="inventory_items"
    )
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name="inventory_items")
    quantity = models.DecimalField(max_digits=18, decimal_places=4, default=0)
    reserved_quantity = models.DecimalField(max_digits=18, decimal_places=4, default=0)
    damaged_quantity = models.DecimalField(max_digits=18, decimal_places=4, default=0)
    returned_quantity = models.DecimalField(max_digits=18, decimal_places=4, default=0)

    class Meta:
        db_table = "inventory"
        unique_together = ["product", "warehouse"]
        verbose_name_plural = "inventory"

    @property
    def available_quantity(self):
        return self.quantity - self.reserved_quantity

    def __str__(self):
        return f"{self.product.sku} @ {self.warehouse.code}: {self.quantity}"


class StockMovement(TenantScopedModel, BaseModel):
    MOVEMENT_TYPES = [
        ("adjustment", "Adjustment"),
        ("purchase", "Purchase"),
        ("sale", "Sale"),
        ("transfer_in", "Transfer In"),
        ("transfer_out", "Transfer Out"),
        ("return", "Return"),
    ]

    product = models.ForeignKey("products.Product", on_delete=models.CASCADE, related_name="stock_movements")
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name="stock_movements")
    movement_type = models.CharField(max_length=50, choices=MOVEMENT_TYPES, db_index=True)
    quantity = models.DecimalField(max_digits=18, decimal_places=4)
    reference_type = models.CharField(max_length=50, blank=True)
    reference_id = models.UUIDField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        db_table = "stock_movements"
        ordering = ["-created_at"]


class InventoryTransaction(TenantScopedModel, BaseModel):
    TRANSACTION_TYPES = [
        ("in", "In"),
        ("out", "Out"),
        ("reserve", "Reserve"),
        ("unreserve", "Unreserve"),
        ("damage", "Damage"),
        ("return", "Return"),
    ]

    inventory = models.ForeignKey(Inventory, on_delete=models.CASCADE, related_name="transactions")
    transaction_type = models.CharField(max_length=50, choices=TRANSACTION_TYPES, db_index=True)
    quantity_before = models.DecimalField(max_digits=18, decimal_places=4)
    quantity_after = models.DecimalField(max_digits=18, decimal_places=4)
    quantity_change = models.DecimalField(max_digits=18, decimal_places=4)
    reference_type = models.CharField(max_length=50, blank=True)
    reference_id = models.UUIDField(null=True, blank=True)

    class Meta:
        db_table = "inventory_transactions"
        ordering = ["-created_at"]


class InventoryAdjustment(TenantScopedModel, BaseModel):
    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("confirmed", "Confirmed"),
        ("cancelled", "Cancelled"),
    ]

    adjustment_number = models.CharField(max_length=50, unique=True, db_index=True)
    warehouse = models.ForeignKey(Warehouse, on_delete=models.PROTECT, related_name="adjustments")
    branch = models.ForeignKey("settings_app.Branch", on_delete=models.PROTECT, related_name="adjustments")
    reason = models.TextField(blank=True)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default="draft", db_index=True)

    class Meta:
        db_table = "inventory_adjustments"
        ordering = ["-created_at"]


class InventoryAdjustmentItem(BaseModel):
    adjustment = models.ForeignKey(
        InventoryAdjustment, on_delete=models.CASCADE, related_name="items"
    )
    product = models.ForeignKey("products.Product", on_delete=models.PROTECT)
    quantity_before = models.DecimalField(max_digits=18, decimal_places=4)
    quantity_after = models.DecimalField(max_digits=18, decimal_places=4)
    quantity_change = models.DecimalField(max_digits=18, decimal_places=4)

    class Meta:
        db_table = "inventory_adjustment_items"


class StockTransfer(TenantScopedModel, BaseModel):
    STATUS_DRAFT = "draft"
    STATUS_CONFIRMED = "confirmed"
    STATUS_CANCELLED = "cancelled"
    STATUS_CHOICES = [
        (STATUS_DRAFT, "Draft"),
        (STATUS_CONFIRMED, "Confirmed"),
        (STATUS_CANCELLED, "Cancelled"),
    ]

    transfer_number = models.CharField(max_length=50, db_index=True)
    source_warehouse = models.ForeignKey(
        Warehouse, on_delete=models.PROTECT, related_name="transfers_out"
    )
    destination_warehouse = models.ForeignKey(
        Warehouse, on_delete=models.PROTECT, related_name="transfers_in"
    )
    branch = models.ForeignKey(
        "settings_app.Branch", on_delete=models.PROTECT, related_name="stock_transfers"
    )
    status = models.CharField(
        max_length=50, choices=STATUS_CHOICES, default=STATUS_DRAFT, db_index=True
    )
    notes = models.TextField(blank=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    confirmed_by = models.ForeignKey(
        "authentication.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="confirmed_stock_transfers",
    )

    class Meta:
        db_table = "stock_transfers"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "transfer_number"],
                name="uniq_stock_transfer_tenant_number",
            ),
        ]

    def __str__(self):
        return self.transfer_number


class StockTransferLine(BaseModel):
    transfer = models.ForeignKey(StockTransfer, on_delete=models.CASCADE, related_name="lines")
    product = models.ForeignKey("products.Product", on_delete=models.PROTECT, related_name="transfer_lines")
    quantity = models.DecimalField(max_digits=18, decimal_places=4)

    class Meta:
        db_table = "stock_transfer_lines"
        constraints = [
            models.UniqueConstraint(
                fields=["transfer", "product"],
                name="uniq_stock_transfer_line_product",
            ),
        ]
