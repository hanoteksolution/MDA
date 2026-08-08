from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils import timezone

from core.models.base import BaseModel
from core.models.tenant import TenantScopedModel


class MenuCategory(TenantScopedModel, BaseModel):
    name = models.CharField(max_length=120, db_index=True)
    branch = models.ForeignKey(
        "settings_app.Branch",
        on_delete=models.CASCADE,
        related_name="restaurant_menu_categories",
    )
    sort_order = models.PositiveIntegerField(default=100)
    is_active = models.BooleanField(default=True, db_index=True)
    notes = models.TextField(blank=True)

    class Meta:
        db_table = "restaurant_menu_categories"
        ordering = ["sort_order", "name"]
        indexes = [
            models.Index(fields=["tenant", "is_active", "sort_order"], name="idx_rest_cat_tenant"),
        ]

    def __str__(self):
        return self.name


class MenuItem(TenantScopedModel, BaseModel):
    category = models.ForeignKey(
        MenuCategory, on_delete=models.CASCADE, related_name="items"
    )
    branch = models.ForeignKey(
        "settings_app.Branch",
        on_delete=models.CASCADE,
        related_name="restaurant_menu_items",
    )
    product = models.ForeignKey(
        "products.Product",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="restaurant_menu_items",
    )
    name = models.CharField(max_length=200, db_index=True)
    sku = models.CharField(max_length=50, blank=True, db_index=True)
    description = models.TextField(blank=True)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    is_available = models.BooleanField(default=True, db_index=True)
    sort_order = models.PositiveIntegerField(default=100)

    class Meta:
        db_table = "restaurant_menu_items"
        ordering = ["sort_order", "name"]
        indexes = [
            models.Index(fields=["tenant", "is_available", "name"], name="idx_rest_item_tenant"),
        ]

    def __str__(self):
        return self.name


class DiningTable(TenantScopedModel, BaseModel):
    STATUS_FREE = "free"
    STATUS_OCCUPIED = "occupied"
    STATUS_RESERVED = "reserved"
    STATUS_CHOICES = [
        (STATUS_FREE, "Free"),
        (STATUS_OCCUPIED, "Occupied"),
        (STATUS_RESERVED, "Reserved"),
    ]

    branch = models.ForeignKey(
        "settings_app.Branch",
        on_delete=models.CASCADE,
        related_name="restaurant_tables",
    )
    code = models.CharField(max_length=30, db_index=True)
    label = models.CharField(max_length=120, blank=True)
    capacity = models.PositiveSmallIntegerField(default=4)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=STATUS_FREE, db_index=True
    )
    is_active = models.BooleanField(default=True, db_index=True)
    notes = models.TextField(blank=True)

    class Meta:
        db_table = "restaurant_dining_tables"
        ordering = ["code"]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "branch", "code"],
                name="uniq_rest_table_tenant_branch_code",
            ),
        ]

    def __str__(self):
        return self.label or self.code


class RestaurantOrder(TenantScopedModel, BaseModel):
    """Open floor ticket — payment via Universal POS later (not Invoice yet)."""

    STATUS_OPEN = "open"
    STATUS_SENT = "sent"
    STATUS_READY = "ready"
    STATUS_SERVED = "served"
    STATUS_PAID = "paid"
    STATUS_CANCELLED = "cancelled"
    STATUS_CHOICES = [
        (STATUS_OPEN, "Open"),
        (STATUS_SENT, "Sent to kitchen"),
        (STATUS_READY, "Ready"),
        (STATUS_SERVED, "Served"),
        (STATUS_PAID, "Paid"),
        (STATUS_CANCELLED, "Cancelled"),
    ]

    SERVICE_DINE_IN = "dine_in"
    SERVICE_TAKEAWAY = "takeaway"
    SERVICE_CHOICES = [
        (SERVICE_DINE_IN, "Dine in"),
        (SERVICE_TAKEAWAY, "Takeaway"),
    ]

    branch = models.ForeignKey(
        "settings_app.Branch",
        on_delete=models.CASCADE,
        related_name="restaurant_orders",
    )
    table = models.ForeignKey(
        DiningTable,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="orders",
    )
    order_number = models.CharField(max_length=40, db_index=True)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=STATUS_OPEN, db_index=True
    )
    service_type = models.CharField(
        max_length=20, choices=SERVICE_CHOICES, default=SERVICE_DINE_IN
    )
    waiter_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="restaurant_orders",
    )
    waiter_name = models.CharField(max_length=120, blank=True)
    guest_count = models.PositiveSmallIntegerField(default=1)
    subtotal = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    notes = models.TextField(blank=True)
    opened_at = models.DateTimeField(default=timezone.now, db_index=True)
    closed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "restaurant_orders"
        ordering = ["-opened_at"]
        indexes = [
            models.Index(fields=["tenant", "status", "opened_at"], name="idx_rest_ord_tenant"),
        ]

    def __str__(self):
        return self.order_number

    def recalc_subtotal(self):
        total = Decimal("0")
        for line in self.lines.filter(deleted_at__isnull=True):
            total += Decimal(str(line.line_total or 0))
        self.subtotal = total
        self.save(update_fields=["subtotal", "updated_at"])


class OrderLine(TenantScopedModel, BaseModel):
    STATUS_QUEUED = "queued"
    STATUS_PREP = "prep"
    STATUS_DONE = "done"
    STATUS_CANCELLED = "cancelled"
    STATUS_CHOICES = [
        (STATUS_QUEUED, "Queued"),
        (STATUS_PREP, "Preparing"),
        (STATUS_DONE, "Done"),
        (STATUS_CANCELLED, "Cancelled"),
    ]

    order = models.ForeignKey(RestaurantOrder, on_delete=models.CASCADE, related_name="lines")
    menu_item = models.ForeignKey(
        MenuItem, on_delete=models.PROTECT, related_name="order_lines"
    )
    product = models.ForeignKey(
        "products.Product",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="restaurant_order_lines",
    )
    name = models.CharField(max_length=200)
    quantity = models.DecimalField(max_digits=12, decimal_places=3, default=1)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    line_total = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=STATUS_QUEUED, db_index=True
    )
    notes = models.TextField(blank=True)

    class Meta:
        db_table = "restaurant_order_lines"
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.name} x{self.quantity}"
