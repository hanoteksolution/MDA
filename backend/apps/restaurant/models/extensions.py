"""Cafeteria/barista domain extensions on the restaurant engine."""

from decimal import Decimal

from django.db import models

from core.models.base import BaseModel
from core.models.tenant import TenantScopedModel


class MenuItemVariant(TenantScopedModel, BaseModel):
    menu_item = models.ForeignKey(
        "restaurant.MenuItem",
        on_delete=models.CASCADE,
        related_name="variants",
    )
    name = models.CharField(max_length=120)
    sku = models.CharField(max_length=50, blank=True, db_index=True)
    barcode = models.CharField(max_length=64, blank=True, db_index=True)
    price_adjustment = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    recipe_qty_multiplier = models.DecimalField(max_digits=8, decimal_places=3, default=1)
    is_default = models.BooleanField(default=False)
    is_available = models.BooleanField(default=True, db_index=True)
    sort_order = models.PositiveIntegerField(default=100)

    class Meta:
        db_table = "restaurant_menu_item_variants"
        ordering = ["sort_order", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "menu_item", "name"],
                condition=models.Q(deleted_at__isnull=True),
                name="uniq_rest_variant_tenant_item_name",
            ),
        ]

    def __str__(self):
        return f"{self.menu_item_id}:{self.name}"

    @property
    def final_price(self) -> Decimal:
        base = Decimal(str(getattr(self.menu_item, "unit_price", 0) or 0))
        return base + Decimal(str(self.price_adjustment or 0))


class MenuItemModifierGroup(TenantScopedModel, BaseModel):
    menu_item = models.ForeignKey(
        "restaurant.MenuItem",
        on_delete=models.CASCADE,
        related_name="modifier_group_links",
    )
    modifier_group = models.ForeignKey(
        "restaurant.ModifierGroup",
        on_delete=models.CASCADE,
        related_name="menu_item_links",
    )
    sort_order = models.PositiveIntegerField(default=100)

    class Meta:
        db_table = "restaurant_menu_item_modifier_groups"
        ordering = ["sort_order"]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "menu_item", "modifier_group"],
                name="uniq_rest_item_modifier_group",
            ),
        ]


class OrderLineModifier(TenantScopedModel, BaseModel):
    order_line = models.ForeignKey(
        "restaurant.OrderLine",
        on_delete=models.CASCADE,
        related_name="modifiers",
    )
    modifier = models.ForeignKey(
        "restaurant.Modifier",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="order_line_uses",
    )
    name = models.CharField(max_length=120)
    price_delta = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    quantity = models.DecimalField(max_digits=12, decimal_places=3, default=1)

    class Meta:
        db_table = "restaurant_order_line_modifiers"
        ordering = ["created_at"]
