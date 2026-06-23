from django.db import models

from core.models.base import BaseModel


class ShopGroup(BaseModel):
    """Organization that owns multiple shop tenants (e.g. cafeteria chain)."""

    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=100, unique=True)
    contact_email = models.EmailField(blank=True)
    contact_phone = models.CharField(max_length=50, blank=True)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        db_table = "shop_groups"
        ordering = ["name"]

    def __str__(self):
        return self.name
