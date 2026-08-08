from django.db import models

from core.models.base import BaseModel
from core.models.tenant import TenantScopedModel


class Category(TenantScopedModel, BaseModel):
    name = models.CharField(max_length=255, db_index=True)
    parent = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True, related_name="children"
    )
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "categories"
        verbose_name_plural = "categories"
        ordering = ["name"]
        indexes = [
            models.Index(
                fields=["tenant", "is_active", "name"],
                name="idx_cat_tenant_active_name",
            ),
        ]

    def __str__(self):
        return self.name


class Brand(TenantScopedModel, BaseModel):
    name = models.CharField(max_length=255, db_index=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "brands"
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "name"],
                name="uniq_brand_tenant_name",
            ),
        ]

    def __str__(self):
        return self.name


class Unit(TenantScopedModel, BaseModel):
    name = models.CharField(max_length=100)
    abbreviation = models.CharField(max_length=20)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "units"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Product(TenantScopedModel, BaseModel):
    sku = models.CharField(max_length=100, db_index=True)
    barcode = models.CharField(max_length=100, null=True, blank=True, db_index=True)
    name = models.CharField(max_length=255, db_index=True)
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="products")
    brand = models.ForeignKey(Brand, on_delete=models.SET_NULL, null=True, blank=True, related_name="products")
    unit = models.ForeignKey(Unit, on_delete=models.PROTECT, related_name="products")
    cost_price = models.DecimalField(max_digits=18, decimal_places=4)
    selling_price = models.DecimalField(max_digits=18, decimal_places=4)
    minimum_stock = models.PositiveIntegerField(default=5)
    description = models.TextField(blank=True)
    image = models.CharField(max_length=500, blank=True)
    is_active = models.BooleanField(default=True, db_index=True)
    requires_prescription = models.BooleanField(
        default=False,
        db_index=True,
        help_text="When pharmacy module is enabled, POS requires an active Rx covering this product.",
    )

    class Meta:
        db_table = "products"
        ordering = ["name"]
        indexes = [
            models.Index(
                fields=["tenant", "is_active", "name"],
                name="idx_prod_tenant_active_name",
            ),
            models.Index(
                fields=["tenant", "is_active", "barcode"],
                name="idx_prod_tenant_active_barcode",
            ),
            models.Index(
                fields=["tenant", "category", "is_active"],
                name="idx_prod_tenant_cat_active",
            ),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "sku"],
                name="uniq_product_tenant_sku",
            ),
            models.UniqueConstraint(
                fields=["tenant", "barcode"],
                name="uniq_product_tenant_barcode",
                condition=models.Q(barcode__isnull=False),
            ),
        ]

    def __str__(self):
        return self.name
