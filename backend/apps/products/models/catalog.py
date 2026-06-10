from django.db import models

from core.models.base import BaseModel


class Category(BaseModel):
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

    def __str__(self):
        return self.name


class Brand(BaseModel):
    name = models.CharField(max_length=255, unique=True, db_index=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "brands"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Unit(BaseModel):
    name = models.CharField(max_length=100)
    abbreviation = models.CharField(max_length=20)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "units"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Product(BaseModel):
    sku = models.CharField(max_length=100, unique=True, db_index=True)
    barcode = models.CharField(max_length=100, unique=True, null=True, blank=True, db_index=True)
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

    class Meta:
        db_table = "products"
        ordering = ["name"]

    def __str__(self):
        return self.name
